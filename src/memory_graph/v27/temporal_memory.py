"""Single causal episode/event store underlying both memory graph views."""
from __future__ import annotations

from copy import deepcopy

from .models import Config, EntityObservation, MemoryEvent, RelationCandidate, RelationEpisode, record
from .observation_graph import image_relations
from .relation_promotion import promote, valid_assertions
from .relevance import LOCATORS, SUPPORT, context_order, eligible, supported


class TemporalMemory:
    def __init__(self, config: Config | None = None, size: tuple[int, int] = (1280, 720)):
        self.config = config or Config()
        self.size = size
        self.target = {"entity_id": self.config.target_id, "state": "NOT_YET_OBSERVED",
                       "last_seen_frame": None, "last_seen_time": None, "last_trusted_snapshot": None,
                       "last_trusted_relations": [], "last_trusted_anchors": [],
                       "visibility_assessment": "UNKNOWN", "possible_occluders": []}
        self.entities = {self.config.target_id: {"entity_id": self.config.target_id, "label": "target phone",
                                               "admission_reason": "query target"}}
        self.episodes: list[RelationEpisode] = []
        self.events: list[MemoryEvent] = []
        self.snapshots: list[dict] = []
        self.observations: list[dict] = []
        self.relation_observations: list[dict] = []
        self.identity_audit: list[dict] = []
        self.admission_audit: list[dict] = []
        self.candidates: dict[tuple, RelationCandidate] = {}
        self.missing_support: dict[str, int] = {}
        self.last_bbox = None
        self.last_overlap = set()
        self.current_frame = -1

    def _event(self, event_type: str, frame: int, time: float, **details) -> None:
        self.events.append(MemoryEvent(f"EV{len(self.events)+1:04d}", event_type, frame, time, details))

    def _candidate(self, relation: str, anchor: EntityObservation, target: EntityObservation,
                   evidence: list[dict]) -> RelationCandidate:
        key = (relation, anchor.entity_id)
        candidate = self.candidates.get(key)
        if candidate is None or candidate.state == "ENDED" or target.time - candidate.support_times[-1] > self.config.maximum_support_gap_seconds:
            candidate = RelationCandidate(self.config.target_id, relation, anchor.entity_id)
            self.candidates[key] = candidate
        if target.frame not in candidate.support_frames:
            candidate.support_frames.append(target.frame)
            candidate.support_times.append(target.time)
            candidate.evidence.extend(deepcopy(evidence))
        return candidate

    def _start_or_extend(self, candidate: RelationCandidate, anchor: EntityObservation,
                         target: EntityObservation, kind: str) -> None:
        episode = next((e for e in reversed(self.episodes) if e.status == "ACTIVE"
                        and e.relation == candidate.relation and e.object == anchor.entity_id), None)
        evidence = candidate.evidence[-1:]
        if episode is None:
            # Explicit new physical support can contradict an earlier support relation.
            if kind == "PHYSICAL":
                for old in self.episodes:
                    incompatible = (old.relation == candidate.relation and old.object != anchor.entity_id)
                    incompatible |= candidate.relation == "HELD_BY" and old.relation in {"ON", "INSIDE"}
                    if old.status == "ACTIVE" and old.kind == "PHYSICAL" and incompatible:
                        self._end(old, target.frame, target.time, "new supported physical relation")
            self.entities[anchor.entity_id] = {"entity_id": anchor.entity_id, "label": anchor.label,
                                             "admission_reason": "supported physical relation" if kind == "PHYSICAL"
                                             else "stable, close, useful image localization anchor",
                                             "identity_scope": "upstream persistent entity; no new cross-track merge"}
            episode = RelationEpisode(f"R{len(self.episodes)+1:04d}", self.config.target_id,
                                      candidate.relation, anchor.entity_id, kind,
                                      candidate.support_frames[0], target.frame, candidate.support_times[0], target.time,
                                      "ACTIVE", "TRUSTED_PHYSICAL_SUPPORT" if kind == "PHYSICAL" else "TRUSTED_IMAGE_CONTEXT",
                                      list(candidate.support_frames), deepcopy(candidate.evidence),
                                      sorted({ref for e in candidate.evidence for ref in e.get("source_refs", [e.get("source_ref")]) if ref}))
            self.episodes.append(episode)
            self._event("IMPORTANT_RELATION_STARTED", target.frame, target.time, episode=episode.episode_id)
            self._event("IMPORTANT_ANCHOR_CHANGED", target.frame, target.time, anchor=anchor.entity_id)
            if kind == "PHYSICAL" and candidate.relation in {"HELD_BY", "ON", "OCCLUDED_BY"}:
                kind_event = {"HELD_BY": "PICKUP_EVENT", "ON": "PUTDOWN_EVENT", "OCCLUDED_BY": "OCCLUSION_EVENT"}
                if any(e.get("event_type") == kind_event[candidate.relation] for e in candidate.evidence):
                    self._event(kind_event[candidate.relation], target.frame, target.time, episode=episode.episode_id)
        else:
            if target.frame not in episode.support_frames:
                episode.support_frames.append(target.frame)
                episode.evidence.extend(deepcopy(evidence))
                episode.source = sorted(set(episode.source) | {ref for e in evidence
                                         for ref in e.get("source_refs", [e.get("source_ref")]) if ref})
            episode.end_frame = target.frame
            episode.last_confirmed_time = target.time
        candidate.state = "PROMOTED"  # CONTEXT promotion never changes the relation into a physical predicate.
        self.missing_support[episode.episode_id] = 0

    def _end(self, episode: RelationEpisode, frame: int, time: float, reason: str) -> None:
        episode.status = "ENDED"
        episode.ended_at_frame = frame
        candidate = self.candidates.get((episode.relation, episode.object))
        if candidate is not None:
            candidate.state = "ENDED"
        self._event("IMPORTANT_RELATION_ENDED", frame, time, episode=episode.episode_id, reason=reason)

    def _refresh_last(self) -> None:
        recent = [e for e in self.episodes if e.status in {"ACTIVE", "LAST_TRUSTED"}]
        self.target["last_trusted_relations"] = [e.episode_id for e in recent]
        self.target["last_trusted_anchors"] = sorted({e.object for e in recent})

    def _snapshot(self, frame: int, time: float, first_event: int) -> None:
        if len(self.events) == first_event:
            return
        snapshot_id = f"G{len(self.snapshots)+1:03d}"
        recent = [e for e in self.episodes if e.status in {"ACTIVE", "LAST_TRUSTED"}]
        for e in recent:
            e.graph_snapshot_ids.append(snapshot_id)
        if self.target["state"] == "VISIBLE_TRUSTED":
            self.target["last_trusted_snapshot"] = snapshot_id
        nodes = {self.config.target_id} | {e.object for e in recent}
        self.snapshots.append({"snapshot_id": snapshot_id, "frame": frame, "time": time,
                               "target": deepcopy(self.target),
                               "entities": {key: deepcopy(self.entities[key]) for key in sorted(nodes)},
                               "relations": [record(e) for e in recent],
                               "trigger_events": [record(e) for e in self.events[first_event:]],
                               "meaning": "Remembered state" if self.target["state"] == "UNOBSERVED" else "Current trusted image evidence"})

    def step(self, frame: int, time: float, observations: list[EntityObservation],
             anchors: list[EntityObservation], upstream_state: str | None = None,
             physical_evidence: list[dict] | None = None) -> None:
        if frame <= self.current_frame:
            raise ValueError("Frames must arrive once in strictly increasing order")
        self.current_frame = frame
        if any(o.frame != frame or abs(o.time - time) > 1e-4 for o in observations + anchors):
            raise ValueError("Observation must be available at the current frame and time")
        first_event = len(self.events)
        self.observations.extend(record(o) for o in observations)
        valid = [o for o in observations if o.entity_id == self.config.target_id and o.trusted]
        for o in observations:
            self.identity_audit.append({"frame": frame, "observation_id": o.observation_id, "identity": o.identity,
                                        "memory_update_authorized": o in valid,
                                        "reason": "trusted target identity" if o in valid else "observation only"})
        if valid:
            # Duplicate raw/track detections in one frame count as one temporal support.
            target = max(valid, key=lambda o: (o.identity == "CONFIRMED_MATCH", o.confidence or 0))
            if self.target["state"] in {"NOT_YET_OBSERVED", "UNOBSERVED"}:
                reconnect = self.target["state"] == "UNOBSERVED"
                self._event("TARGET_RECONFIRMED" if reconnect else "TARGET_APPEARED", frame, time,
                            observation=target.observation_id)
                if reconnect:
                    for episode in self.episodes:
                        if episode.status == "LAST_TRUSTED":
                            episode.status = "STALE"
                            episode.ended_at_frame = frame
                    self.candidates.clear()
            self.target.update(state="VISIBLE_TRUSTED", last_seen_frame=frame, last_seen_time=time,
                               visibility_assessment="VISIBLE", possible_occluders=[])
            self.last_bbox = list(target.bbox)
            options = []
            current_support = set()
            self.last_overlap = set()
            for anchor in anchors:
                if anchor.entity_id == self.config.target_id or not anchor.trusted:
                    continue
                relations = image_relations(target, anchor, self.size, self.config.image_near_gap_fraction)
                self.relation_observations.extend(record(r) for r in relations)
                assertions = valid_assertions(target, anchor, physical_evidence or [], self.config)
                admitted = eligible(anchor, relations, bool(assertions))
                self.admission_audit.append({"frame": frame, "entity_id": anchor.entity_id, "label": anchor.label,
                                             "eligible": admitted, "reason": "useful nearby anchor or physical evidence" if admitted
                                             else "irrelevant, unsupported, or untrusted"})
                if not admitted:
                    continue
                context = self._candidate("ANCHOR_CONTEXT", anchor, target,
                                          [{"frame": frame, "time": time, "source_refs": relations[0].source,
                                            "image_relations": [r.relation for r in relations],
                                            "metrics": relations[0].metrics, "physical_verification": False}])
                if anchor.label in SUPPORT | LOCATORS and supported(context, self.config):
                    options.append((context_order(anchor, relations), context, anchor))
                for relation in sorted({a["relation"] for a in assertions}):
                    candidate = self._candidate(relation, anchor, target, [a for a in assertions if a["relation"] == relation])
                    if promote(candidate, target, self.config):
                        options.append(((-1, 0, 0, anchor.entity_id), candidate, anchor))
                if any(r.relation == "IMAGE_OVERLAP" for r in relations):
                    self.last_overlap.add(anchor.entity_id)
            selected_ids = []
            for _, candidate, anchor in sorted(options, key=lambda x: x[0]):
                if anchor.entity_id not in selected_ids:
                    if len(selected_ids) >= self.config.maximum_current_anchors:
                        continue
                    selected_ids.append(anchor.entity_id)
                kind = "CONTEXT" if candidate.relation == "ANCHOR_CONTEXT" else "PHYSICAL"
                self._start_or_extend(candidate, anchor, target, kind)
                current_support.add((candidate.relation, anchor.entity_id))
            for episode in self.episodes:
                if episode.status == "ACTIVE" and episode.kind == "CONTEXT" and (episode.relation, episode.object) not in current_support:
                    self.missing_support[episode.episode_id] = self.missing_support.get(episode.episode_id, 0) + 1
                    if self.missing_support[episode.episode_id] >= self.config.relation_end_confirmed_frames:
                        self._end(episode, frame, time, "context not supported in consecutive trusted target observations")
            # The active view has a hard cap; displaced contexts become historical, never deleted.
            active_ids = {e.object for e in self.episodes if e.status == "ACTIVE"}
            if len(active_ids) > self.config.maximum_current_anchors:
                for episode in self.episodes:
                    if episode.status == "ACTIVE" and episode.kind == "CONTEXT" and episode.object not in selected_ids:
                        self._end(episode, frame, time, "sparse context view replaced by better supported current anchors")
        elif upstream_state == "UNOBSERVED" and self.target["state"] == "VISIBLE_TRUSTED":
            self.target["state"] = "UNOBSERVED"
            for episode in self.episodes:
                if episode.status == "ACTIVE":
                    episode.status = "LAST_TRUSTED"
            still_present = {a.entity_id for a in anchors if a.trusted}
            recent_memory = {e.object for e in self.episodes if e.status == "LAST_TRUSTED"}
            possible = sorted(self.last_overlap & still_present & recent_memory)
            self.target["possible_occluders"] = [{"entity_id": entity, "status": "CANDIDATE",
                                                 "reason": "prior image overlap plus continued anchor visibility; physical occlusion unverified"}
                                                for entity in possible]
            edge = self.last_bbox and (self.last_bbox[0] <= 2 or self.last_bbox[1] <= 2
                                      or self.last_bbox[2] >= self.size[0] - 2 or self.last_bbox[3] >= self.size[1] - 2)
            self.target["visibility_assessment"] = "OCCLUSION_CANDIDATE" if possible else ("OUT_OF_VIEW_CANDIDATE" if edge else "UNOBSERVED_UNCERTAIN")
            self._event("TARGET_DISAPPEARED", frame, time, last_seen=self.target["last_seen_time"],
                        evidence="frozen upstream UNOBSERVED; no physical movement inferred")
        self._refresh_last()
        self._snapshot(frame, time, first_event)

    def build_object_memory(self, entity_id: str = "phone_01") -> dict:
        if entity_id != self.config.target_id:
            raise KeyError(entity_id)
        return {"schema": "v27_object_memory_1", "target": deepcopy(self.target), "entities": deepcopy(self.entities),
                "episodes": [record(e) for e in self.episodes], "events": [record(e) for e in self.events],
                "lifecycle": [{"frame": e.frame, "time": e.time, "event": e.event_type, "details": deepcopy(e.details)} for e in self.events],
                "last_trusted_memory": {"frame": self.target["last_seen_frame"], "time": self.target["last_seen_time"],
                                        "snapshot": self.target["last_trusted_snapshot"],
                                        "relations": [record(e) for e in self.episodes if e.status in {"ACTIVE", "LAST_TRUSTED"}]},
                "interpretation": "Historical anchor-relative evidence, not a current-world location assertion"}

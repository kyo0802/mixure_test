"""Candidate-scoped observable facts, with no relation label in prompt or output."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from memory_graph.v27.pipeline import ROOT, write

OBSERVABLE_PROMPT = """Inspect these BEFORE, DURING, AFTER frames. The green overlay is the known target phone_01. The magenta box is anchor {anchor_id} ({anchor_label}); do not identify objects outside that box. Report visible observations only. Do not infer target identity, hidden objects, or a physical relation. For every yes/no field choose YES, NO, or UNCERTAIN. Return only JSON with keys: target_visible_before, target_moves_toward_anchor, target_contacts_or_crosses_anchor_boundary, target_visible_area_decreases, anchor_remains_visible, target_visible_after, hand_or_person_releases_target, target_stays_after_release, evidence_summary, uncertainty."""
FACT_KEYS = ("target_visible_before", "target_moves_toward_anchor", "target_contacts_or_crosses_anchor_boundary",
             "target_visible_area_decreases", "anchor_remains_visible", "target_visible_after",
             "hand_or_person_releases_target", "target_stays_after_release")
VALUES = {"YES", "NO", "UNCERTAIN"}


def parse_observable(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object")
    value = json.loads(match.group())
    if any(value.get(k) not in VALUES for k in FACT_KEYS):
        raise ValueError("Observable fact missing or outside YES/NO/UNCERTAIN")
    value["evidence_summary"] = str(value.get("evidence_summary", ""))
    value["uncertainty"] = str(value.get("uncertainty", ""))
    if any(r in value for r in ("relation", "candidate_relation", "physical_relation")):
        raise ValueError("VLM relation labels are not accepted")
    return value


class ObservableVLM:
    def __init__(self):
        from memory_graph.vlm.local_backend import LocalBackend
        model = ROOT/".models/Qwen2.5-VL-3B-Instruct"
        config = SimpleNamespace(device="cuda", cpu_threads=4, cache_dir=str(ROOT/"outputs_v291/vlm_cache"),
                                 revision="main", local_files_only=True, model=str(model), load_in_4bit=False,
                                 max_new_tokens=220, image_longest_edge=800, max_inference_seconds=120,
                                 ground_entities_individually=False)
        self.backend = LocalBackend(config)

    def run(self, images: list[Path], event: dict, anchor: dict) -> dict:
        prompt = OBSERVABLE_PROMPT.format(anchor_id=anchor["anchor_id"], anchor_label=anchor["normalized_label"])
        start = time.monotonic()
        raw = None
        try:
            loaded = [Image.open(path).convert("RGB") for path in images]
            raw = self.backend._generate(loaded, prompt, 220)
            facts = parse_observable(raw)
            status, error = "VALID", None
        except Exception as exc:
            facts, status, error = None, "FAILED", f"{type(exc).__name__}: {exc}"
        return {"event_id": event["event_id"], "anchor_id": anchor["anchor_id"],
                "model": self.backend.identity, "images": [str(p) for p in images],
                "prompt": prompt, "status": status, "observable_facts": facts,
                "raw_output": raw, "error": error, "inference_seconds": time.monotonic()-start,
                "relation_label_requested": False}

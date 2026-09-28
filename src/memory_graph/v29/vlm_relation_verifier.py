"""Forced-choice local Qwen verification for eligible target-anchor candidates."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace
import json
import re
import time

import cv2
import numpy as np
from PIL import Image

from memory_graph.v27.pipeline import ROOT, write
from memory_graph.v22.sam_tracking import decode_mask

PROMPT = """You are verifying the physical relation between a KNOWN target and a KNOWN anchor across BEFORE, DURING, AFTER frames. The green box is TARGET phone_01. The purple box labelled ANCHOR {anchor} is the only anchor to judge. Other objects are irrelevant. Choose exactly one: ON, INSIDE, BEHIND, OCCLUDED_BY, HELD_BY, NEAR, NONE, UNCERTAIN. Do not infer identity. Do not invent unseen objects. Do not infer a physical relation from proximity alone. Return only JSON with keys relation, confidence (0 to 1), temporal_evidence, visual_evidence, counterevidence, uncertainty. If the anchor is not clearly visible or target identity cannot be followed, answer UNCERTAIN."""
ALLOWED = {"ON", "INSIDE", "BEHIND", "OCCLUDED_BY", "HELD_BY", "NEAR", "NONE", "UNCERTAIN"}


def _parse(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object")
    result = json.loads(match.group())
    if result.get("relation") not in ALLOWED:
        raise ValueError("Unrecognized relation")
    confidence = float(result.get("confidence", -1))
    if not 0 <= confidence <= 1:
        raise ValueError("Confidence outside [0,1]")
    result["confidence"] = confidence
    for key in ("temporal_evidence", "visual_evidence", "counterevidence", "uncertainty"):
        result[key] = str(result.get(key, ""))
    return result


def _scoped_images(task: str, event_id: str, anchor: str, output: Path) -> tuple[list[Path], list[int]]:
    dense = json.loads((output/"dense_windows"/event_id/"dense_observations.json").read_text(encoding="utf-8"))
    masks = json.loads((output/"dense_windows"/event_id/"target_masks.json").read_text(encoding="utf-8"))
    rows = dense["rows"]
    covisible = [i for i, r in enumerate(rows) if r["identity_authorized"] and
                 any(a["entity_id"] == anchor for a in r["anchors"])]
    if not covisible:
        raise ValueError("No authorized target-anchor co-visibility")
    before, during = covisible[0], covisible[-1]
    after = next((i for i in range(during+1, len(rows))
                  if any(a["entity_id"] == anchor for a in rows[i]["anchors"])), len(rows)-1)
    chosen = [before, during, after]
    cap = cv2.VideoCapture(str(ROOT/f"{task}.mp4"))
    image_dir = output/"vlm_inputs"/f"{event_id}_{anchor}"
    image_dir.mkdir(parents=True, exist_ok=True)
    paths, frames = [], []
    try:
        for name, index in zip(("before", "during", "after"), chosen):
            row = rows[index]
            frame = row["frame"]
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            if not ok:
                raise OSError(f"Could not decode {task} frame {frame}")
            target = row["sam_phone"] if row["identity_authorized"] else None
            known = next((a for a in row["anchors"] if a["entity_id"] == anchor), None)
            boxes = [x["bbox"] for x in (target, known) if x]
            if boxes:
                x1 = max(0, int(min(b[0] for b in boxes)-130))
                y1 = max(0, int(min(b[1] for b in boxes)-110))
                x2 = min(image.shape[1], int(max(b[2] for b in boxes)+130))
                y2 = min(image.shape[0], int(max(b[3] for b in boxes)+110))
            else:
                x1, y1, x2, y2 = 0, 0, image.shape[1], image.shape[0]
            if target and str(frame) in masks:
                mask = decode_mask(masks[str(frame)])
                overlay = image.copy()
                overlay[mask] = (0, 180, 0)
                image = cv2.addWeighted(image, .72, overlay, .28, 0)
            image = image[y1:y2, x1:x2]
            scale = min(800/max(1, image.shape[1]), 600/max(1, image.shape[0]))
            image = cv2.resize(image, None, fx=scale, fy=scale)
            def draw(box, color):
                a = (int((box[0]-x1)*scale), int((box[1]-y1)*scale))
                b = (int((box[2]-x1)*scale), int((box[3]-y1)*scale))
                cv2.rectangle(image, a, b, color, 4)
            if target:
                draw(target["bbox"], (0, 255, 0))
            if known:
                draw(known["bbox"], (255, 0, 255))
            header = np.zeros((95, image.shape[1], 3), dtype=np.uint8)
            cv2.putText(header, f"{name.upper()} f{frame} | TARGET phone_01: {'GREEN' if target else 'NOT AUTHORIZED'}",
                        (8, 36), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(header, f"ANCHOR {anchor}: {'MAGENTA' if known else 'NOT DETECTED'}",
                        (8, 72), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 2, cv2.LINE_AA)
            path = image_dir/f"{name}.png"
            cv2.imwrite(str(path), np.vstack((header, image)))
            paths.append(path)
            frames.append(frame)
    finally:
        cap.release()
    return paths, frames


class CandidateVLM:
    def __init__(self):
        from memory_graph.vlm.local_backend import LocalBackend
        model = ROOT/".models/Qwen2.5-VL-3B-Instruct"
        config = SimpleNamespace(device="cuda", cpu_threads=4, cache_dir=str(ROOT/"outputs_v29/vlm_cache"),
                                 revision="main", local_files_only=True, trust_remote_code=False,
                                 model=str(model), load_in_4bit=False, max_new_tokens=220,
                                 image_longest_edge=800, max_inference_seconds=120,
                                 ground_entities_individually=False)
        self.backend = LocalBackend(config)

    def verify(self, task: str, candidates: list[dict], output: Path) -> list[dict]:
        groups = defaultdict(list)
        for candidate in candidates:
            if candidate["vlm_verification_required"]:
                groups[(candidate["event_id"], candidate["anchor"])].append(candidate)
        results = []
        for (event_id, anchor), scoped in sorted(groups.items()):
            sheet_path = output/"dense_windows"/event_id/f"placement_event_{event_id}_contact_sheet.png"
            prompt = PROMPT.format(anchor=anchor)
            started = time.monotonic()
            raw, paths, source_frames = None, [], []
            try:
                paths, source_frames = _scoped_images(task, event_id, anchor, output)
                loaded = [Image.open(path).convert("RGB") for path in paths]
                raw = self.backend._generate(loaded, prompt, 220)
                structured = _parse(raw)
                status, error = "VALID", None
            except Exception as exc:
                structured = None
                status, error = "FAILED", f"{type(exc).__name__}: {exc}"
            elapsed = time.monotonic()-started
            result = {"task": task, "event_id": event_id, "anchor": anchor,
                      "candidate_ids": [c["candidate_id"] for c in scoped],
                      "candidate_relations": [c["candidate_relation"] for c in scoped],
                      "model": self.backend.identity, "frames_used": [str(p.relative_to(ROOT)) for p in paths],
                      "source_frame_indices": source_frames,
                      "prompt": PROMPT.format(anchor=anchor), "status": status,
                      "raw_output": raw, "structured_output": structured,
                      "error": error, "inference_seconds": elapsed,
                      "provenance": [str(sheet_path.relative_to(ROOT))]}
            results.append(result)
            write(output/"vlm_cache"/f"{event_id}_{anchor}.json", result)
            print(task, event_id, anchor, status, structured.get("relation") if structured else error, flush=True)
        write(output/"vlm_relation_verification.json", results)
        return results

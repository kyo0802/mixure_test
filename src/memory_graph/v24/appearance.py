"""Deterministic, cached crop embeddings and trusted appearance memory."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from memory_graph.v22.sam_tracking import ROOT, box_iou, decode_mask, read_json, sha256


WEIGHTS = ROOT / "outputs_v24" / "cache" / "mobilenet_v3_small-047dcff4.pth"
MODEL_NAME = "torchvision MobileNetV3 Small ImageNet-1K features+avgpool"
MAX_PROTOTYPES = 4


class AppearanceBank:
    def __init__(self, entity_id, max_prototypes=MAX_PROTOTYPES):
        self.entity_id = entity_id
        self.max_prototypes = max_prototypes
        self.prototypes = []

    def add(self, record, *, trusted, reason):
        if not trusted or reason in {"AMBIGUOUS", "CONFLICT", "REJECT_PROPAGATION"}:
            return False
        if len(self.prototypes) >= self.max_prototypes:
            return False
        entry = dict(record)
        entry["trust_reason"] = reason
        self.prototypes.append(entry)
        return True

    def on_unobserved(self):
        return len(self.prototypes)


def compatible_semantics(query, candidate):
    return query == candidate or query in {"phone", "cell phone", "smartphone"} and candidate in {"phone", "cell phone", "smartphone"}


def normalize(vector):
    x = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(x)
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError("Invalid appearance vector")
    return x / norm


def cosine(a, b):
    return float(np.dot(normalize(a), normalize(b)))


def frame_image(task, frame):
    video = ROOT / ("test1.mp4" if task == "task1" else "test2.mp4")
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
    ok, image = cap.read()
    cap.release()
    if not ok:
        raise OSError(f"Cannot reconstruct {task} frame {frame}")
    return image


def crop_rgb(image, bbox, mask=None):
    """Use original RGB pixels; optional trusted mask paints background neutral gray."""
    h, w = image.shape[:2]
    x1, y1, x2, y2 = [float(v) for v in bbox]
    pad_x, pad_y = .05 * (x2 - x1), .05 * (y2 - y1)
    x1, y1 = max(0, int(x1 - pad_x)), max(0, int(y1 - pad_y))
    x2, y2 = min(w, int(np.ceil(x2 + pad_x))), min(h, int(np.ceil(y2 + pad_y)))
    if x2 <= x1 or y2 <= y1:
        raise ValueError("Invalid crop box")
    crop = cv2.cvtColor(image[y1:y2, x1:x2], cv2.COLOR_BGR2RGB)
    if mask is not None:
        region = np.asarray(mask[y1:y2, x1:x2], dtype=bool)
        if region.shape != crop.shape[:2] or region.sum() < 32:
            raise ValueError("Missing/invalid foreground mask")
        crop = crop.copy()
        crop[~region] = 128
    return crop


class MobileNetEmbedder:
    def __init__(self):
        import torch
        from torchvision.models import mobilenet_v3_small
        from torchvision.transforms import Compose, CenterCrop, Normalize, Resize, ToTensor
        from PIL import Image

        if not WEIGHTS.is_file():
            raise FileNotFoundError(WEIGHTS)
        self.torch = torch
        self.Image = Image
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = mobilenet_v3_small(weights=None)
        state = torch.load(WEIGHTS, map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        model.eval().to(self.device)
        self.model = model
        self.transform = Compose([Resize(256), CenterCrop(224), ToTensor(),
                                  Normalize(mean=[.485, .456, .406], std=[.229, .224, .225])])
        self.weight_sha256 = sha256(WEIGHTS)
        self.cache_dir = ROOT / "outputs_v24" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def embed_crop(self, crop):
        digest = hashlib.sha256(self.weight_sha256.encode() + crop.tobytes()).hexdigest()
        path = self.cache_dir / f"embedding_{digest}.npy"
        if path.exists():
            return normalize(np.load(path)), digest
        tensor = self.transform(self.Image.fromarray(crop)).unsqueeze(0).to(self.device)
        with self.torch.inference_mode():
            feature = self.model.features(tensor)
            feature = self.model.avgpool(feature).flatten(1)
        vector = normalize(feature[0].cpu().numpy())
        np.save(path, vector)
        return vector, digest

    def embed(self, task, frame, bbox, mask=None):
        image = frame_image(task, frame)
        return self.embed_crop(crop_rgb(image, bbox, mask))


def sam_obs_by_frame(task, target):
    log = read_json(ROOT / "outputs_v22" / task / "tracking_ab" / "sam_propagation_log.json")
    result = {}
    for segment in log["segments"]:
        for obs in segment["observations"]:
            if obs["object_id"] == target:
                result[obs["frame_index"]] = (obs, segment["masks_rle"].get(f"{obs['frame_index']}:{target}"))
    return result


def eligible_trusted_views(task, target, registry):
    """Select only V2.3 trusted phone frames with matching YOLO+SAM evidence."""
    phone = next(e for e in registry["entities"] if e["entity_id"] == "phone_01")
    sam = sam_obs_by_frame(task, target)
    rows = []
    for obs in phone["observation_history"]:
        frame = obs["frame_index"]
        if obs["source"] != "yolo_track" or obs["detector_confidence"] < .5 or frame not in sam:
            continue
        mask_obs, rle = sam[frame]
        if mask_obs["diagnostics"]["possible_mask_drift"] or rle is None:
            continue
        if box_iou(obs["bbox"], mask_obs["bbox"]) < .5:
            continue
        rows.append({"frame_index": frame, "timestamp": obs["timestamp"], "bbox": obs["bbox"],
                     "source": obs["source_object_id"], "detector_confidence": obs["detector_confidence"],
                     "mask": rle, "sam_target": target})
    return rows


def choose_diverse_views(rows, limit=MAX_PROTOTYPES):
    """Highest-confidence view per temporal bin, with at least one per YOLO track when possible."""
    if not rows:
        return []
    by_source = {}
    for row in rows:
        by_source.setdefault(row["source"], []).append(row)
    chosen = []
    for source in sorted(by_source):
        group = sorted(by_source[source], key=lambda r: (-r["detector_confidence"], r["frame_index"]))
        chosen.extend(group[: min(2, max(1, limit // len(by_source)))])
    chosen = sorted(chosen, key=lambda r: (-r["detector_confidence"], r["frame_index"]))[:limit]
    return sorted(chosen, key=lambda r: r["frame_index"])


def make_bank(task, embedder, registry):
    target = "phone_track17" if task == "task1" else "phone_track22"
    rows = choose_diverse_views(eligible_trusted_views(task, target, registry))
    if not rows:
        raise ValueError(f"No trusted source crops: {task}")
    bank = AppearanceBank("phone_01")
    for row in rows:
        vector, key = embedder.embed(task, row["frame_index"], row["bbox"], decode_mask(row["mask"]))
        bank.add({"entity_id": "phone_01", "frame_index": row["frame_index"],
                  "timestamp": row["timestamp"], "source": row["source"],
                  "crop_reference": f"{task}:frame{row['frame_index']}:{row['source']}",
                  "mask_used": True, "embedding_model": MODEL_NAME,
                  "embedding_cache_key": key, "embedding": vector.tolist()},
                 trusted=True, reason="YOLO local observation agrees with accepted SAM mask")
    return bank


def bank_summary(bank):
    return {"entity_id": bank.entity_id, "max_prototypes": bank.max_prototypes,
            "prototypes": [{k: v for k, v in p.items() if k != "embedding"} for p in bank.prototypes]}


def similarity_details(bank, candidate_vectors):
    matrix = [[cosine(v, p["embedding"]) for p in bank.prototypes] for v in candidate_vectors]
    best = max(((score, i, j) for i, row in enumerate(matrix) for j, score in enumerate(row)), default=None)
    return {"matrix": matrix, "max_similarity": best[0] if best else None,
            "mean_top2": float(np.mean(sorted((x for row in matrix for x in row), reverse=True)[:2])) if best else None,
            "best_candidate_view": best[1] if best else None,
            "best_prototype_frame": bank.prototypes[best[2]]["frame_index"] if best else None}

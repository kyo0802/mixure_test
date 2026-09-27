"""V2.6.2 normalized SAM observation and identity-safe binding helpers."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class SAMObservation:
    frame_index: int
    timestamp: float
    source_model: str
    source_object_id: str | None
    target_persistent_entity: str
    mask: str
    bbox: list[int] | None
    area: int
    confidence_if_available: float | None
    initialization_frame: int
    initialized_from: str
    accepted_by_guard: bool
    rejection_reason: str | None

    def record(self) -> dict:
        return asdict(self)


def normalized_xywh(box: list[float], width: int, height: int) -> list[float]:
    x1, y1, x2, y2 = map(float, box)
    return [x1 / width, y1 / height, (x2 - x1) / width, (y2 - y1) / height]


def choose_box_overlap_id(ids: list[int], boxes: list[list[float]], frozen: list[float]) -> int | None:
    from memory_graph.v262.smoke import choose_object_id
    return choose_object_id(ids, boxes, frozen)


def mask_bbox(mask: np.ndarray) -> list[int] | None:
    ys, xs = np.nonzero(mask)
    return [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)] if len(xs) else None


def can_reinitialize(authorization: str) -> bool:
    return authorization == "CONFIRMED_MATCH"


def counts_as_correct_target(observation: dict, physical_label: str) -> bool:
    return bool(observation["accepted_by_guard"] and physical_label == "CORRECT_TARGET")

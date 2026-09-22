from math import hypot


def normalized(box, width: int, height: int) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = box
    return x1/width, y1/height, x2/width, y2/height


def pair_signals(subject, anchor, width: int, height: int) -> dict[str, float]:
    x1, y1, x2, y2 = normalized(subject, width, height)
    a1, b1, a2, b2 = normalized(anchor, width, height)
    area = (x2-x1)*(y2-y1)
    anchor_area = (a2-a1)*(b2-b1)
    iw, ih = max(0, min(x2, a2)-max(x1, a1)), max(0, min(y2, b2)-max(y1, b1))
    intersection = iw*ih
    return {"dx": (x1+x2-a1-a2)/2, "dy": (y1+y2-b1-b2)/2,
        "bbox_distance": hypot(max(a1-x2, x1-a2, 0), max(b1-y2, y1-b2, 0)),
        "iou": intersection/max(area+anchor_area-intersection, 1e-12),
        "overlap_fraction": intersection/max(min(area, anchor_area), 1e-12),
        "subject_containment": intersection/max(area, 1e-12),
        "horizontal_overlap": iw/max(min(x2-x1, a2-a1), 1e-12),
        "top_gap": b1-y2, "relative_size": area/max(anchor_area, 1e-12)}

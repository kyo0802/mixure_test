"""Record manual visual judgments for frozen V2.6.2 review frames.

Judgments were made from the saved four-column full-frame panels and candidate
zooms, after prediction_manifest.json froze all mask predictions.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / "outputs_v262"
OK = "CORRECT_TARGET"
PART = "PARTIAL_TARGET"
LOST = "EMPTY_OR_LOST"
DRIFT = "DRIFT_TO_OTHER_OBJECT"
NR = "NOT_REVIEWABLE"

# frame: (physical target visible, frozen YOLO target absent, SAM2.1,
#         SAM3 box, SAM3 point, visual note)
REVIEW = {
    "test3": {
        228: (True, False, OK, LOST, OK, "Frozen target phone on table; both nonempty masks align."),
        540: (False, None, LOST, LOST, LOST, "Target not visible in this checkpoint."),
        852: (False, None, LOST, LOST, LOST, "Target not visible in this checkpoint."),
        1164: (False, None, LOST, LOST, LOST, "Target not visible in this checkpoint."),
    },
    "test4": {
        216: (True, False, PART, LOST, PART, "Frozen phone is under hand; both masks include hand pixels."),
        534: (False, None, LOST, LOST, LOST, "Target not visible."),
        852: (False, None, LOST, LOST, LOST, "Target not visible."),
        1038: (True, False, LOST, LOST, LOST, "Frozen reviewed target phone is plainly on table; all masks empty."),
        1164: (False, None, LOST, LOST, LOST, "Target not visible."),
    },
    "test5": {
        96: (True, False, OK, LOST, OK, "Frozen target phone in hand at lower edge; masks align."),
        438: (None, None, NR, NR, NR, "Thin masks on box rim; phone/physical identity cannot be verified from this frame."),
        780: (False, None, LOST, LOST, LOST, "Target not visible."),
        1116: (False, None, LOST, LOST, LOST, "Target not visible."),
    },
    "test6": {
        204: (True, False, OK, LOST, OK, "Frozen target phone on table; masks align."),
        468: (False, None, LOST, LOST, LOST, "Target not visible."),
        732: (False, None, LOST, LOST, DRIFT, "167-pixel point mask on hand edge; no target phone visible; guard accepted."),
        990: (False, None, LOST, LOST, LOST, "Target not visible."),
    },
    "test7": {
        210: (True, False, OK, LOST, OK, "Frozen target phone on table; masks align."),
        576: (False, None, LOST, LOST, LOST, "Target not visible."),
        636: (False, None, LOST, LOST, LOST, "Visible landline is frozen PROVISIONAL_MATCH distractor; all target masks empty."),
        708: (True, False, LOST, LOST, OK, "Frozen reviewed target smartphone in hand; point mask recovers it."),
        834: (True, False, LOST, LOST, OK, "Frozen reviewed target smartphone in hand; point mask continues it."),
        948: (False, None, LOST, LOST, DRIFT, "Point mask on hand/toy edge after target leaves; guard accepted."),
        1314: (False, None, LOST, LOST, LOST, "Target not visible."),
    },
    "test8": {
        204: (True, False, OK, LOST, OK, "Frozen target smartphone on table; masks align."),
        504: (False, None, LOST, LOST, LOST, "Target not visible."),
        804: (True, False, OK, LOST, PART, "Confirmed same smartphone in hand; point mask includes substantial hand spill."),
        840: (True, False, OK, LOST, PART, "Same smartphone in hand near landlines; point mask includes hand spill."),
        852: (True, False, OK, LOST, OK, "Red reviewed DISTRACTOR box is landline; both masks remain on original smartphone at left."),
        864: (True, False, OK, LOST, PART, "Red reviewed DISTRACTOR box is landline; point mask is only sliver of original smartphone."),
        900: (True, False, PART, LOST, PART, "Original smartphone on ledge is mostly under hand; masks include hand."),
        1002: (None, None, NR, NR, NR, "Distant person holds a phone; cannot establish physical identity from this frame."),
        1098: (False, None, LOST, LOST, LOST, "Target not visible."),
    },
    "test9": {
        546: (True, False, OK, LOST, OK, "Frozen target smartphone on table; masks align."),
        762: (None, None, NR, NR, NR, "Small point mask under table; possible held phone cannot be identified with confidence."),
        978: (False, None, DRIFT, LOST, DRIFT, "Both masks on object at toy base; target smartphone absent; guards accepted."),
        1194: (False, None, LOST, LOST, LOST, "Target not visible."),
    },
}


def main() -> None:
    freeze = OUT / "prediction_manifest.json"
    if not freeze.is_file():
        raise RuntimeError("Predictions must be frozen before physical review")
    for task, labels in REVIEW.items():
        path = OUT / task / "physical_review.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        found = {row["frame_index"] for row in data["reviewed_frames"]}
        if found != set(labels):
            raise RuntimeError(f"Review frame mismatch: {task}")
        for row in data["reviewed_frames"]:
            visible, yolo_absent, sam21, sam3, point, note = labels[row["frame_index"]]
            row.update(target_visible=visible, yolo_target_absent=yolo_absent,
                       model_labels={"sam21": sam21, "sam3": sam3, "sam3point": point}, note=note)
        data["visually_confirmed"] = True
        data["review_basis"] = "Saved full-frame four-column panels; candidate zooms for reviewed V2.6 candidates"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Recorded 37 manually inspected checkpoints across seven videos")


if __name__ == "__main__":
    main()

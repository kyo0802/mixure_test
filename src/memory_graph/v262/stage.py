"""Apply the predeclared Stage A runtime gate before seven-video work."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v262"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    sam3 = read(OUT / "smoke" / "sam3" / "result.json")
    sam21 = read(OUT / "smoke" / "sam21" / "result.json")
    same = sam3["frames"] == sam21["frames"] == list(range(804, 847, 6)) and sam3["frozen_box_xyxy"] == sam21["frozen_box_xyxy"]
    selected = sum(row.get("selected_area", 0) > 0 for row in sam3["outputs"])
    checks = {
        "official_sam3_checkpoint_loaded": sam3["status"] == "COMPLETE" and sam3["checkpoint"].replace("\\", "/").endswith("sam3/sam3.pt"),
        "matched_frozen_frames_and_box": same,
        "actual_attention_path_executed": sam3["attention_backend"] not in ("UNKNOWN", "MATH_SDPA") and bool(sam3["attention_ops"]),
        "propagation_reliable": len(sam3["outputs"]) == 8,
        "selected_target_masks_sufficient": selected >= 6,
        "propagation_runtime_practical": sam3["timing_seconds"]["propagation"] <= 30.0,
        "peak_memory_practical": sam3["peak_reserved_bytes"] <= 14 * 1024**3,
    }
    decision = "PASS" if all(checks.values()) else "FAIL"
    result = {
        "schema": "v262_stage_a_1", "decision": decision, "checks": checks,
        "criteria": {"minimum_selected_nonempty_frames": 6, "maximum_propagation_seconds": 30.0, "maximum_reserved_gib": 14.0},
        "same_frames": sam3["frames"], "same_frozen_box": sam3["frozen_box_xyxy"],
        "sam21": {"nonempty_frames": sum(any(a > 0 for a in row["areas"]) for row in sam21["outputs"]),
                  "propagation_seconds": sam21["timing_seconds"]["propagation"],
                  "peak_allocated_bytes": sam21["peak_gpu_bytes"], "peak_reserved_bytes": sam21["peak_reserved_bytes"]},
        "sam3": {"nonempty_frames_any_id": sam3["nonempty_frames"], "selected_id": sam3["selected_object_id"],
                 "selected_id_nonempty_frames": selected, "prompt_object_ids": sam3["prompt_object_ids"],
                 "propagation_seconds": sam3["timing_seconds"]["propagation"],
                 "peak_allocated_bytes": sam3["peak_allocated_bytes"], "peak_reserved_bytes": sam3["peak_reserved_bytes"],
                 "attention_backend": sam3["attention_backend"]},
        "quality_claim": "No physical-target correctness conclusion from Stage A; box may produce multiple SAM-local objects.",
    }
    (OUT / "stage_a_feasibility.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (OUT / "smoke" / "comparison.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Stage A:", decision)
    if decision != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

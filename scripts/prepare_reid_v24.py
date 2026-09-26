"""Build trusted banks and allowed development controls; never access late Task2 candidates or GT."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v22.sam_tracking import ROOT, frozen_inputs, read_json
from memory_graph.v24.appearance import MobileNetEmbedder, bank_summary, make_bank, similarity_details


def main():
    embedder = MobileNetEmbedder()
    banks = {}
    for task in ("task1", "task2"):
        registry = read_json(ROOT / "outputs_v23" / task / "entity_registry.json")
        bank = make_bank(task, embedder, registry)
        banks[task] = bank
        output = ROOT / "outputs_v24" / task
        output.mkdir(parents=True, exist_ok=True)
        (output / "appearance_bank.json").write_text(json.dumps(bank_summary(bank), indent=2), encoding="utf-8")
        print(task, "trusted frames", [p["frame_index"] for p in bank.prototypes])
    early = [p for p in banks["task2"].prototypes if p["source"] == "track:22"]
    later = [p for p in banks["task2"].prototypes if p["source"] == "track:43"]
    if not early or not later:
        raise ValueError("Task2 short-gap positive control lacks trusted views")
    from memory_graph.v24.appearance import AppearanceBank
    early_bank = AppearanceBank("phone_01")
    early_bank.prototypes = early
    positive = similarity_details(early_bank, [p["embedding"] for p in later])
    inputs, _ = frozen_inputs("task1")
    desk = next(t for t in inputs["track_timelines.json"] if t["track_id"] == 70)
    desk_obs = max(desk["observations"], key=lambda o: o["confidence"])
    desk_vector, desk_key = embedder.embed("task1", desk_obs["frame_index"], desk_obs["bbox"], mask=None)
    negative = similarity_details(banks["task1"], [desk_vector])
    controls = {"model": "torchvision MobileNetV3 Small ImageNet-1K features+avgpool",
                "weights_sha256": embedder.weight_sha256, "device": str(embedder.device),
                "task2_short_gap_positive": {"query_track": 22, "candidate_track": 43,
                                              "query_frames": [p["frame_index"] for p in early],
                                              "candidate_frames": [p["frame_index"] for p in later], **positive},
                "task1_later_desk_negative": {"query_track": 17, "candidate_track": 70,
                                             "candidate_frame": desk_obs["frame_index"],
                                             "candidate_embedding_cache_key": desk_key, **negative},
                "heldout_task2_late_candidates_accessed": False}
    cache = ROOT / "outputs_v24" / "cache"
    (cache / "development_controls.json").write_text(json.dumps(controls, indent=2), encoding="utf-8")
    print(json.dumps({"positive_max": positive["max_similarity"], "negative_max": negative["max_similarity"],
                      "positive_mean_top2": positive["mean_top2"], "negative_mean_top2": negative["mean_top2"]}))


if __name__ == "__main__":
    main()

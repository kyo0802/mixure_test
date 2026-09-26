"""Focused, synthetic tests for the parameter-locked V2.4 Re-ID gates."""
from pathlib import Path

import numpy as np
import memory_graph

local_package = str(Path(__file__).resolve().parents[1] / "src" / "memory_graph")
if local_package not in memory_graph.__path__:
    memory_graph.__path__.insert(0, local_package)

from memory_graph.v24.appearance import AppearanceBank, crop_rgb
from memory_graph.v24.reid import decide, registry_update


PARAMS = {"minimum_match_similarity": .6, "minimum_uniqueness_margin": .1,
          "minimum_evidence_prototypes": 2}


def entity(eid="phone_01", label="cell phone", observations=None):
    return {"entity_id": eid, "semantic_label": label, "last_trusted_seen": 1.0,
            "latest_trusted_observation": {"frame_index": 5},
            "observation_history": observations or [], "association_history": [],
            "yolo_sources": [], "sam_sources": [], "last_seen": 1.0, "state": "UNOBSERVED"}


def bank():
    b = AppearanceBank("phone_01")
    for frame in (1, 5):
        assert b.add({"frame_index": frame, "embedding": [1., 0., 0.]},
                     trusted=True, reason="YOLO and SAM agree")
    return b


def candidate(eid="candidate_1", vector=(1., 0., 0.), label="cell phone",
              observations=None, quality="frozen_yolo_seed_and_nonempty_sam_mask"):
    return {"entity_id": eid, "source_id": eid, "frame_index": 20,
            "timestamp": 4.0, "semantic_label": label,
            "vector": np.asarray(vector, dtype=np.float32), "quality": quality, "mask_used": True,
            "embedding_cache_key": eid, "registry_entity": entity(eid, label, observations)}


def observation(frame, bbox):
    return {"frame_index": frame, "bbox": bbox, "trusted": True}


def test_unobserved_entity_keeps_appearance_memory():
    b = bank()
    assert b.on_unobserved() == 2
    assert len(b.prototypes) == 2


def test_only_trusted_observations_update_appearance_memory():
    b = AppearanceBank("phone_01")
    assert not b.add({"frame_index": 1}, trusted=False, reason="YOLO only")
    assert b.add({"frame_index": 2}, trusted=True, reason="YOLO and SAM agree")
    assert len(b.prototypes) == 1


def test_rejected_sam_drift_cannot_poison_appearance_memory():
    b = bank()
    assert not b.add({"frame_index": 312}, trusted=True, reason="REJECT_PROPAGATION")
    assert 312 not in [p["frame_index"] for p in b.prototypes]


def test_candidate_embeddings_use_same_preprocessing():
    image = np.full((32, 32, 3), [10, 20, 30], dtype=np.uint8)
    mask = np.ones((32, 32), dtype=np.uint8)
    first = crop_rgb(image, [4, 4, 20, 20], mask)
    second = crop_rgb(image, [4, 4, 20, 20], mask)
    assert np.array_equal(first, second)
    assert np.array_equal(first[0, 0], [30, 20, 10])


def test_semantic_contradiction_blocks_match():
    result = decide(entity(), bank(), [candidate(label="book")], PARAMS)
    assert result[0]["decision"] == "REJECT"


def test_simultaneous_distinct_entities_block_match():
    query = entity(observations=[observation(20, [0, 0, 10, 10])])
    other = candidate(observations=[observation(20, [100, 100, 110, 110])])
    assert decide(query, bank(), [other], PARAMS)[0]["decision"] == "REJECT"


def test_highest_similarity_alone_does_not_force_match():
    result = decide(entity(), bank(), [candidate(vector=(.5, .866, 0.))], PARAMS)
    assert result[0]["decision"] == "AMBIGUOUS"


def test_uniqueness_margin_required_for_match():
    candidates = [candidate("a", (1., 0., 0.)), candidate("b", (.99, .14, 0.))]
    assert all(row["decision"] == "AMBIGUOUS" for row in decide(entity(), bank(), candidates, PARAMS))


def test_ambiguous_candidate_does_not_merge_entity():
    result = registry_update("phone_01", candidate(), "AMBIGUOUS")
    assert not result["merge_executed"]


def test_only_match_can_authorize_sam_reinitialization():
    result = decide(entity(), bank(), [candidate()], PARAMS)
    assert result[0]["sam_reinitialization_authorized"]
    assert not registry_update("phone_01", candidate(), "AMBIGUOUS")["sam_reinitialization_authorized"]
    merged = registry_update("phone_01", candidate(), "MATCH", entity(), bank())
    assert merged["sam_reinitialization_authorized"]
    assert not merged["sam_reinitialization_executed"]


def test_late_candidate_gt_not_available_to_reid_inference():
    root = Path(__file__).resolve().parents[1]
    for name in ("appearance.py", "reid.py"):
        source = (root / "src" / "memory_graph" / "v24" / name).read_text(encoding="utf-8").lower()
        assert "ground_truth" not in source
        assert "gt_annotations" not in source
    assert "ground_truth" not in (root / "scripts" / "prepare_reid_v24.py").read_text(encoding="utf-8").lower()


def test_graph_context_cannot_be_sole_match_reason():
    contexts = {"candidate_1": {"shared_image_plane_neighbor_ids": ["desk"], "match_sufficient": False}}
    result = decide(entity(), bank(), [candidate(vector=(0., 1., 0.))], PARAMS, contexts)
    assert result[0]["decision"] == "AMBIGUOUS"

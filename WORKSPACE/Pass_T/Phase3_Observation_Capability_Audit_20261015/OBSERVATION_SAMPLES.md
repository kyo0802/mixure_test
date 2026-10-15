# Stored Observation Samples

所有數字來自既有檔案的 CPU-only parsing；沒有重新 detector/tracker/SAM 推論或 pixels decode。`record_count` 是該檔案所列型別的列數，不是獨立物件或事件真值。完整短摘要見 [OBSERVATION_SAMPLE_SUMMARY.json](OBSERVATION_SAMPLE_SUMMARY.json)。

## A01 — [A01: outputs_v292/test5/perception/yolo_detections.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test5/perception/yolo_detections.json)

Origin: **Real runtime artifact**；format: `.json`；records: **1672**。

實際欄位：`frame_index, timestamp, class_id, class_name, confidence, bbox, center`。

```json
{
  "frame_index": 72,
  "timestamp": 2.4,
  "class_id": 67,
  "class_name": "cell phone",
  "confidence": 0.5650636553764343,
  "bbox": [
    589.2750244140625,
    643.1273803710938,
    729.909423828125,
    719.3783569335938
  ],
  "center": [
    659.5922241210938,
    681.2528686523438
  ]
}
```

Real detector output, no independent state, no per-row source SHA/native PTS/detection ID; confidence is uncalibrated detector score.

## A03 — [A03: outputs_v292/test5/perception/tracks.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test5/perception/tracks.json)

Origin: **Real runtime artifact**；format: `.json`；records: **103**。

實際欄位：`track_id, source_track_key, detector_class, first_seen, last_seen, mean_detector_confidence, observations, visibility, is_anchor, anchor_score`。

```json
{
  "track_id": 21,
  "source_track_key": "cell_phone_01",
  "observations": 4,
  "observation_fields": [
    "frame_index",
    "timestamp",
    "class_id",
    "class_name",
    "confidence",
    "bbox",
    "track_id",
    "detector_class",
    "raw_tracker_id",
    "episode_id",
    "area_fraction",
    "normalized_center",
    "velocity",
    "speed",
    "nearest_tracks",
    "distance_to_person",
    "center"
  ],
  "first_observation": {
    "frame_index": 78,
    "timestamp": 2.6,
    "confidence": 0.5113096237182617,
    "bbox": [
      598.669921875,
      631.1551513671875,
      773.4716796875,
      719.9818115234375
    ],
    "raw_tracker_id": 65,
    "episode_id": "ep_0001",
    "distance_to_person": null
  }
}
```

Track confidence is mean detector confidence, not association probability; visibility is sample-presence boolean, not physical visibility classification.

## A11 — [A11: outputs/identity_rebuild/development/runs_final/test5/authorized_rows.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs/identity_rebuild/development/runs_final/test5/authorized_rows.json)

Origin: **Real runtime artifact**；format: `.json`；records: **187**。

實際欄位：`frame, time, image_size, anchors, candidate_present, scene_ok, identity_authorized, target_bbox, chain_id, mask_reference, upstream_identity_state, source, target_authorization_provenance`。

```json
{
  "frame": 0,
  "time": 0.0,
  "identity_authorized": false,
  "target_bbox": null,
  "source": "final_revocation_filtered_ledger"
}
```

Current final ledger adapter. No authorized target in W05; identity exclusion is not object absence. scene_ok is set True in replay adapter, not measured camera reliability.

## A02 — [A02: outputs_v292/test7/perception/yolo_detections.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test7/perception/yolo_detections.json)

Origin: **Real runtime artifact**；format: `.json`；records: **1791**。

實際欄位：`frame_index, timestamp, class_id, class_name, confidence, bbox, center`。

```json
{
  "frame_index": 84,
  "timestamp": 2.800851063829787,
  "class_id": 67,
  "class_name": "cell phone",
  "confidence": 0.38330355286598206,
  "bbox": [
    617.4537963867188,
    696.3766479492188,
    690.8114624023438,
    720.0
  ],
  "center": [
    654.1326293945312,
    708.1883239746094
  ]
}
```

Real detector output, no independent state, no per-row source SHA/native PTS/detection ID; confidence is uncalibrated detector score.

## A04 — [A04: outputs_v292/test7/perception/tracks.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test7/perception/tracks.json)

Origin: **Real runtime artifact**；format: `.json`；records: **88**。

實際欄位：`track_id, source_track_key, detector_class, first_seen, last_seen, mean_detector_confidence, observations, visibility, is_anchor, anchor_score`。

```json
{
  "track_id": 29,
  "source_track_key": "cell_phone_01",
  "observations": 6,
  "observation_fields": [
    "frame_index",
    "timestamp",
    "class_id",
    "class_name",
    "confidence",
    "bbox",
    "track_id",
    "detector_class",
    "raw_tracker_id",
    "episode_id",
    "area_fraction",
    "normalized_center",
    "velocity",
    "speed",
    "nearest_tracks",
    "distance_to_person",
    "center"
  ],
  "first_observation": {
    "frame_index": 186,
    "timestamp": 6.201884498480243,
    "confidence": 0.3569963872432709,
    "bbox": [
      530.7330322265625,
      559.9616088867188,
      773.8463745117188,
      720.0
    ],
    "raw_tracker_id": 98,
    "episode_id": "ep_0001",
    "distance_to_person": null
  }
}
```

Track confidence is mean detector confidence, not association probability; visibility is sample-presence boolean, not physical visibility classification.

## A12 — [A12: outputs/identity_rebuild/development/runs_final/test7/authorized_rows.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs/identity_rebuild/development/runs_final/test7/authorized_rows.json)

Origin: **Real runtime artifact**；format: `.json`；records: **221**。

實際欄位：`frame, time, image_size, anchors, candidate_present, scene_ok, identity_authorized, target_bbox, chain_id, mask_reference, upstream_identity_state, source, target_authorization_provenance`。

```json
{
  "frame": 0,
  "time": 0.0,
  "identity_authorized": false,
  "target_bbox": null,
  "source": "final_revocation_filtered_ledger"
}
```

Current final ledger adapter. No authorized target in W05; identity exclusion is not object absence. scene_ok is set True in replay adapter, not measured camera reliability.

## A17 — [A17: outputs_v292/test5/sam/sam_continuity_log.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test5/sam/sam_continuity_log.json)

Origin: **Real runtime artifact**；format: `.json`；records: **61**。

實際欄位：`frame_index, timestamp, bbox, center, mask_area, source, segment, object_id, confidence, diagnostics`。

```json
{
  "propagated_frame_slots": 171,
  "nonempty_observations": 61,
  "null_confidence": 61,
  "possible_mask_drift_flags": 0,
  "RLE_masks": 61,
  "mask_frames_in_frame_bounds": [
    342,
    348,
    354,
    360,
    366,
    372,
    378,
    384,
    390,
    396,
    402,
    408,
    414,
    420,
    426,
    432,
    438
  ],
  "first_mask_observation": {
    "frame_index": 96,
    "timestamp": 3.2,
    "bbox": [
      646,
      610,
      768,
      720
    ],
    "center": [
      707.2403925741988,
      668.0708288991368
    ],
    "mask_area": 8457,
    "source": "sam2.1_propagation",
    "segment": "target_full",
    "object_id": "phone_target",
    "confidence": null,
    "diagnostics": {
      "mask_area_ratio": null,
      "bbox_area_ratio": null,
      "centroid_displacement": null,
      "max_yolo_iou": 0.9577880217305282,
      "possible_mask_drift": false,
      "reasons": []
    }
  }
}
```

Real SAM model masks, thresholded logits; no calibrated mask score. No drift flag is not proof of a correct mask. SAM local object_id is not persistent identity.

## A18 — [A18: outputs_v292/test7/sam/sam_continuity_log.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test7/sam/sam_continuity_log.json)

Origin: **Real runtime artifact**；format: `.json`；records: **38**。

實際欄位：`frame_index, timestamp, bbox, center, mask_area, source, segment, object_id, confidence, diagnostics`。

```json
{
  "propagated_frame_slots": 185,
  "nonempty_observations": 38,
  "null_confidence": 38,
  "possible_mask_drift_flags": 0,
  "RLE_masks": 38,
  "mask_frames_in_frame_bounds": [
    372,
    378,
    384,
    390,
    396,
    402,
    408,
    414,
    420,
    426,
    432
  ],
  "first_mask_observation": {
    "frame_index": 210,
    "timestamp": 7.002127659574468,
    "bbox": [
      516,
      532,
      745,
      678
    ],
    "center": [
      634.168780086885,
      601.9775742632382
    ],
    "mask_area": 17034,
    "source": "sam2.1_propagation",
    "segment": "target_full",
    "object_id": "phone_target",
    "confidence": null,
    "diagnostics": {
      "mask_area_ratio": null,
      "bbox_area_ratio": null,
      "centroid_displacement": null,
      "max_yolo_iou": 0.971228741839021,
      "possible_mask_drift": false,
      "reasons": []
    }
  }
}
```

Real SAM model masks, thresholded logits; no calibrated mask score. No drift flag is not proof of a correct mask. SAM local object_id is not persistent identity.

## A09 — [A09: outputs/identity_rebuild/smoke_raw_test2_final/raw/perception/detections.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs/identity_rebuild/smoke_raw_test2_final/raw/perception/detections.json)

Origin: **Real runtime artifact**；format: `.json`；records: **1511**。

實際欄位：`frame_index, timestamp, class_id, class_name, confidence, bbox, center`。

```json
{
  "frame_index": 66,
  "timestamp": 2.200833333333333,
  "class_id": 67,
  "class_name": "cell phone",
  "confidence": 0.7093394994735718,
  "bbox": [
    574.0157470703125,
    561.5201416015625,
    684.2110595703125,
    715.96533203125
  ],
  "center": [
    629.1134033203125,
    638.7427368164062
  ]
}
```

No physical-state validation follows from these stored rows.

## A20 — [A20: outputs_v292/test5/memory/observations.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test5/memory/observations.json)

Origin: **Real runtime artifact**；format: `.json`；records: **916**。

實際欄位：`observation_id, entity_id, frame, time, status, provenance, bbox, raw_detector_label, video_id`。

```json
{
  "observation_id": "test5:entity_0001:0:0",
  "entity_id": "entity_0001",
  "frame": 0,
  "time": 0.0,
  "status": "TRUSTED",
  "provenance": [
    "test5:entity_0001:0:0",
    "yolo_track"
  ],
  "bbox": [
    1021.2396240234375,
    245.57005310058594,
    1279.478271484375,
    714.2877197265625
  ],
  "raw_detector_label": "person",
  "video_id": "test5"
}
```

Real stored output; derived/aggregated or unknown states do not establish physical fact.

## A21 — [A21: outputs_v292/test5/memory/relation_episodes.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test5/memory/relation_episodes.json)

Origin: **Real runtime artifact**；format: `.json`；records: **8**。

實際欄位：`episode_id, memory_event_id, video_id, start_frame, end_frame, start_time, last_confirmed_time, last_supported_frame, last_supported_time, source_event_id, supporting_observation_ids, status, decision, kind, subject, relation, object, source, source_snapshots, provenance`。

```json
{
  "episode_id": "ME0001",
  "kind": "IMAGE_CONTEXT",
  "relation": "IMAGE_NEAR_CONTEXT",
  "status": "STALE",
  "start_time": 5.2,
  "last_supported_time": 5.6
}
```

Real stored output; derived/aggregated or unknown states do not establish physical fact.

## A22 — [A22: outputs_v292/test5/memory/memory_events.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test5/memory/memory_events.json)

Origin: **Real runtime artifact**；format: `.json`；records: **195**。

實際欄位：`event_id, event_type, frame, time, end_frame, end_time, status, trusted, provenance, source_event_id, video_id`。

```json
{
  "event_id": "STATE-0000000",
  "event_type": "IDENTITY_UNOBSERVED",
  "frame": 0,
  "time": 0.0,
  "end_frame": 0,
  "end_time": 0.0,
  "status": "UNOBSERVED",
  "trusted": false,
  "provenance": [
    "fresh_v2.6_identity_timeline"
  ],
  "source_event_id": "ID-0000000",
  "video_id": "test5"
}
```

Real stored output; derived/aggregated or unknown states do not establish physical fact.

## A25 — [A25: outputs/v297_physical_identity/development/runs/test5/camera_compensation.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs/v297_physical_identity/development/runs/test5/camera_compensation.json)

Origin: **Real runtime artifact**；format: `.json`；records: **187**。

實際欄位：`frame, time, reliable, translation, raw_anchor_offsets, anchor_keys, residual_p75, cumulative_translation, camera_segment, normalized_units, limitation`。

```json
{
  "frame": 0,
  "time": 0.0,
  "reliable": false,
  "translation": null,
  "raw_anchor_offsets": [],
  "anchor_keys": [],
  "residual_p75": null,
  "cumulative_translation": null,
  "camera_segment": 0,
  "normalized_units": "image_diagonal",
  "limitation": "partial median translation only; unsupported rotation/scale/scene change yields UNKNOWN"
}
```

Real stored output; derived/aggregated or unknown states do not establish physical fact.

## A26 — [A26: outputs/v297_physical_identity/development/runs/test5/physical_evidence.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs/v297_physical_identity/development/runs/test5/physical_evidence.json)

Origin: **Real runtime artifact**；format: `.json`；records: **68**。

實際欄位：`candidate_epoch, frame, time, reachability, physical_continuity, interaction, reappearance_context, PersonEpoch, person_proximity_history, motion_coupling, occlusion_hypothesis, known_distinct, known_distinct_entity_result, preexistence_contradiction, candidate_preexistence_result, candidate_continuity_valid, competing_plausible_epochs, unique_physical_support, single_phone_state, camera_compensation, anchor_context, evidence_provider_grants_identity`。

```json
{
  "frame": 72,
  "time": 2.4,
  "physical_continuity": {
    "state": "PHYSICAL_UNKNOWN",
    "reason": "No trusted target history",
    "gap": null,
    "candidate_continuity_valid": false
  },
  "interaction": "INTERACTION_CONTINUITY_UNKNOWN",
  "motion_coupling": "MOTION_UNKNOWN",
  "evidence_provider_grants_identity": false
}
```

Real stored output; derived/aggregated or unknown states do not establish physical fact.

## A38 — [A38: outputs_v292/test5/physical/relation_decisions.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test5/physical/relation_decisions.json)

Origin: **Real runtime artifact**；format: `.json`；records: **0**。

實際欄位：``。

```json
null
```

No physical-state validation follows from these stored rows.

## A39 — [A39: outputs_v292/test7/physical/relation_decisions.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test7/physical/relation_decisions.json)

Origin: **Real runtime artifact**；format: `.json`；records: **0**。

實際欄位：``。

```json
null
```

No physical-state validation follows from these stored rows.

## A23 — [A23: outputs_v292/test5/graphs/local_subgraph.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test5/graphs/local_subgraph.json)

Origin: **Real runtime artifact**；format: `.json`；records: **1**。

實際欄位：`nodes, edges, connected, schema, target`。

```json
{
  "schema": "v292_sparse_local_subgraph_1",
  "nodes": 1,
  "edges": 0,
  "first_node": {
    "entity_id": "phone_01",
    "raw_label": "cell phone",
    "semantic_roles": [
      "TARGET"
    ],
    "hop": 0,
    "via_primary": null
  },
  "first_edge": null
}
```

Node count is reported; graph beliefs/context are aggregated legacy results, not current live observations.

## A24 — [A24: outputs_v292/test8/graphs/local_subgraph.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs_v292/test8/graphs/local_subgraph.json)

Origin: **Real runtime artifact**；format: `.json`；records: **4**。

實際欄位：`nodes, edges, connected, schema, target`。

```json
{
  "schema": "v292_sparse_local_subgraph_1",
  "nodes": 4,
  "edges": 3,
  "first_node": {
    "entity_id": "phone_01",
    "raw_label": "cell phone",
    "semantic_roles": [
      "TARGET"
    ],
    "hop": 0,
    "via_primary": null
  },
  "first_edge": {
    "source": "phone_01",
    "relation": "TRUSTED_ANCHOR_CONTEXT",
    "target": "entity_0061",
    "kind": "IMAGE_CONTEXT",
    "segment_id": "P0007",
    "status": "LAST_TRUSTED",
    "physical_verification": false
  }
}
```

Node count is reported; graph beliefs/context are aggregated legacy results, not current live observations.

## A27 — [A27: outputs/v297_physical_identity/development/runs/test5/candidate_epochs.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs/v297_physical_identity/development/runs/test5/candidate_epochs.json)

Origin: **Real runtime artifact**；format: `.json`；records: **29**。

實際欄位：`candidate_epoch_id, start_time, start_frame, local_track_ids, observation_ids, end_reason, end_time, creation_reason`。

```json
{
  "candidate_epoch_id": "ce:test5:0001",
  "start_time": 2.4,
  "start_frame": 72,
  "local_track_ids": [
    "raw:172"
  ],
  "observation_ids": [
    "raw:172@72"
  ],
  "end_reason": null,
  "end_time": null,
  "creation_reason": "NEW_LOCAL_CANDIDATE"
}
```

44 epoch events; short-gap STITCH is a rule, not identity truth.

## A28 — [A28: artifacts/pass_i/manifests/candidate_epoch_inventory.jsonl](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_i/manifests/candidate_epoch_inventory.jsonl)

Origin: **Real runtime artifact**；format: `.jsonl`；records: **690**。

實際欄位：`epoch_id, video_id, start_frame, end_frame, start_time, end_time, end_time_semantics, candidate_class, source_observations, source_paths, hidden_provenance, selected_observation_ids, clean_crops, context_images, session_id, split`。

```json
{
  "epoch_id": "ce:test1:0001",
  "video_id": "test1",
  "start_frame": 84,
  "end_frame": 84,
  "end_time_semantics": "last observed time, not builder discontinuity time"
}
```

Offline dataset assembly; inventory metadata only. No frozen pixels, labels or inference examined.

## A35 — [A35: artifacts/pass_i/evidence_qc/human_qc.sqlite3](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_i/evidence_qc/human_qc.sqlite3)

Origin: **Human annotation**；format: `.sqlite3`；records: **120**。

實際欄位：`schema, epoch_id, split, crop_states, epoch_state, human_note, updated_utc, inventory_sha256`。

```json
{
  "table": "epoch_reviews",
  "epoch_counts": {
    "VALID": 63,
    "NO_USABLE_TARGET": 53,
    "MIXED_IDENTITY": 4
  },
  "crop_counts": {
    "KEEP_WEAK": 52,
    "KEEP_PRIMARY": 92,
    "DROP_WRONG_TARGET": 119,
    "DROP_NOT_PHONE": 1
  },
  "concrete_DEV_mixed_epoch": "ce:test7:0001"
}
```

Opened sqlite mode=ro&immutable=1. Confirms evidence contamination labels, not calibrated tracker ID-switch rate; no DB updates.

## A34 — [A34: artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/HUMAN_ADJUDICATED_CALLS.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/HUMAN_ADJUDICATED_CALLS.json)

Origin: **Human annotation**；format: `.json`；records: **5**。

實際欄位：`call_id, window, representation, human_submission_original_path, preserved_submission_path, submission_sha256, human_record_unchanged, resolved_reviewer_id, reviewer_identity_resolution, model_claim_unchanged, raw_output_path, raw_output_sha256, strict_validation_unchanged, structural_errors_unchanged, authoritative_structured_matching_eligible, human_evidence_alias_provenance, report_author_secondary_themes, human_form_consistency_warnings`。

```json
{
  "WRONG_TARGET": 2,
  "SUPPORTED_BY_OBSERVED_EVIDENCE": 3
}
```

Existing completed review only; unchanged. Human judgement is evaluation context, not automatic runtime state producer.

## A44 — [A44: outputs/current_development/event_windows/target_timelines/test5.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs/current_development/event_windows/target_timelines/test5.json)

Origin: **Real runtime artifact**；format: `.json`；records: **272**。

實際欄位：`actor_associations, anchors, camera_translation_estimate, candidate_present, carried_like, chain_id, frame, identity_authorized, image_size, mask_reference, motion_speed, motion_state, scene_ok, source, target_authorization_provenance, target_bbox, time, upstream_identity_state, visibility`。

```json
{
  "motion_state_counts": {
    "UNKNOWN": 246,
    "MOVING": 21,
    "STATIONARY": 5
  },
  "non_null_camera_translation_estimates": 13,
  "carried_like_true": 4,
  "provenance": {
    "video_id": "test5",
    "fps": 30.0,
    "image_size": [
      1280,
      720
    ],
    "source_manifests": [
      "outputs_v292/test5/run_manifest.json",
      "outputs_v293/test5/prepared_events.json"
    ],
    "source_sha256": [
      "957ec1ba91632281f578e3f01d8be8d992fa0c768d34f4315c9d02ef61071243",
      "b5c2e06e9655f23e494e18e46a5098cff6a4a5de1bc90fb10df419890eb2b407"
    ],
    "dense_events_used": [
      "test5-V292E01",
      "test5-V292E02",
      "test5-V292E03"
    ],
    "fresh_YOLO_SAM_calls": 0,
    "identity_logic_changed": false
  }
}
```

Historical real-data builder output from legacy-identity inputs, not current guard W05 authority. The same unchanged builder is called by current prepare. MOVING/STATIONARY/carried_like are image heuristics, not HELD or ON_SURFACE observations.

## A45 — [A45: outputs/identity_rebuild/development/runs_final/test2/prepared/events.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs/identity_rebuild/development/runs_final/test2/prepared/events.json)

Origin: **Real runtime artifact**；format: `.json`；records: **5**。

實際欄位：`category, trigger, transition_frame, transition_time, start_frame, end_frame, start_time, end_time, duration_seconds, HAS_PRE_STATE, HAS_TRANSITION, HAS_POST_STATE, pre_state, post_state, completeness, failure_categories, identity_authorized_fraction, identity_write_authorized, row_indices, semantic_action_assigned, pack_id, video_id, target_id, representation, contexts, markers, actor_markers, location_markers, physical_reasoning_eligible, frames`。

```json
{
  "physical_reasoning_eligible": 1,
  "events": [
    {
      "pack_id": "identity_W01",
      "trigger": "OBSERVATION_RECOVERY",
      "completeness": "INCOMPLETE_EVENT_WINDOW",
      "physical_reasoning_eligible": false
    },
    {
      "pack_id": "identity_W02",
      "trigger": "VISIBILITY_CHANGE",
      "completeness": "INCOMPLETE_EVENT_WINDOW",
      "physical_reasoning_eligible": false
    },
    {
      "pack_id": "identity_W03",
      "trigger": "VISIBILITY_CHANGE",
      "completeness": "INCOMPLETE_EVENT_WINDOW",
      "physical_reasoning_eligible": false
    },
    {
      "pack_id": "identity_W04",
      "trigger": "MOVING_TO_STATIONARY",
      "completeness": "COMPLETE_EVENT_WINDOW",
      "physical_reasoning_eligible": true
    },
    {
      "pack_id": "identity_W05",
      "trigger": "OBSERVATION_GAP_START",
      "completeness": "COMPLETE_EVENT_WINDOW",
      "physical_reasoning_eligible": false
    }
  ]
}
```

Actual current-guard downstream prepare output; motion/lifecycle proposals, not confirmed physical events.

## A46 — [A46: outputs/identity_rebuild/development/runs_final/test2/prepared/qwen/responses.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/outputs/identity_rebuild/development/runs_final/test2/prepared/qwen/responses.json)

Origin: **Real runtime artifact**；format: `.json`；records: **1**。

實際欄位：`pack_id, raw_output, answer, validation, trace`。

```json
{
  "pack_id": "identity_W04",
  "validation": {
    "pack_id": "identity_W04",
    "schema_valid": true,
    "valid": true,
    "status": "VALID_MODEL_REASONING_OUTPUT",
    "errors": []
  },
  "ended_with_EOS": true
}
```

Existing actual dense-Qwen current-path response, under a different reasoning contract from Phase2b V1D. Its validator result is not independent physical truth and does not reclassify any Phase2b output.

## test5/test7 W05 exact-frame linkage

| Video | Stored detections | cell phone detections (whole video) | Phone track fragments | CV sampled frames in frame bounds | Phone detections in those bounds | Uniform8 exact sampled-frame overlap | Current authorized targets in bounds |
|---|---|---|---|---|---|---|---|
| test5 | 1672 | 68 | 4 | 18 | 9 | 1/8 | 0 |
| test7 | 1791 | 226 | 12 | 18 | 10 | 0/8 | 0 |

The legacy run video_sha256 and current replay video_sha256 agree with the frozen cohort source IDs; current detector/track files also match the current replay source_hashes. **Actual video file bytes were not rehashed/decoded in this audit.** Counts above use half-open frame-index bounds; source native-PTS authorization is an additional constraint.

test5 W05 has nine phone detections over 18 sampled frames, test7 ten phone detection records over 18 frames (not necessarily ten distinct frames). Detector class list alone therefore does not settle manipulated-target detectability. Missing row != physical disappearance, and NOT_SAMPLED != missed detection. No recall/identity accuracy is inferred.

CV rows timestamp=index/FPS; exact native PTS lives separately in Pass T source manifests. Do not interpolate absent detections onto Uniform8 aliases. For test7 the first authorized Uniform8 source frame is373 while CV sampling begins372; numeric closeness cannot override bounds/native-PTS authorization.

For independent hand/contact/held/surface observation samples: **NO_VERIFIED_REAL_OBSERVATION_SAMPLE_FOUND** in the audited scope. Human QC confirms mixed evidence (e.g. `ce:test7:0001`) but does not identify which internal tracker step caused the contamination.

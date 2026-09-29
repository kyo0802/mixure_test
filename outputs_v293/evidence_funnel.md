# Evidence funnel

| Stage | Count |
|---|---:|
| pair_requests_total | 54 |
| before_target_usable | 12 |
| before_anchor_usable | 54 |
| during_target_usable | 11 |
| during_anchor_usable | 54 |
| transition_evidence_usable | 11 |
| after_anchor_usable | 11 |
| pair_evidence_eligible | 11 |
| vlm_called | 11 |
| vlm_schema_valid | 11 |
| vlm_grounding_valid | 5 |
| physical_gate_called | 15 |
| vlm_new_inference_calls | 0 |
| physical_promoted | 0 |
| physical_candidate | 1 |
| physical_uncertain | 6 |
| physical_rejected | 8 |

Rejection reasons:
```json
{
  "NO_TARGET_BEFORE": 42,
  "PAIR_NEVER_COVISIBLE": 1
}
```

# Phase 2b GT Eligibility and Limitations

Authority dataset: `ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c`.

| Window | Item | Final use | Additional visual review | Critical limitation |
|---|---|---|---|---|
| test1 W03/W05 | `PT2A_9d15d2a6b56b56d0` | Strict-negative case alert | ASSISTANT_SPOT_CHECK | Only 7/107 frames received the added spot check; no independent full-window quality release |
| test2 W01 | `PT2A_b35d807b28b92101` | Strict-negative case alert | NONE | No added independent full-window visual review |
| test5 W01 | `PT2A_fe0910d66f4c5614` | Strict-negative case alert | NONE | No added independent full-window visual review |
| test5 W05 | `PT2A_eb60192e6986cb4f` | Known PICKUP matching only | HUMAN_PARTIAL | Last frame does not support exhaustive coverage; extra predictions are UNEVALUATED |
| test7 W05 | `PT2A_c58b4df88a2f6801` | Known PICKUP matching only | HUMAN_PARTIAL | Last frame does not support exhaustive coverage; extra predictions are UNEVALUATED |
| test8 W07 | `PT2A_5dbb180e8ff88762` | Descriptive uncertainty only | NONE | INSUFFICIENT_EVIDENCE; no event-list completeness claim |
| test3 W07 | `PT2A_0bfb99c324769681` | Audit only; no model run | NONE | Original exposure and identity/persistence exclusions remain binding |

`original_v2_full_window_eligible`, `v2_full_window_evidence_supported`, `additional_visual_quality_verified`, `pilot_scoring_permission`, and `formal_benchmark_permission` are stored as separate fields in `eligibility.json`. No item has formal benchmark permission and binding causality remains `CAUSALITY_UNVERIFIED`.


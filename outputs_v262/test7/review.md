# test7 V2.6.2 physical-target review

Predictions were frozen before V2.6.2 mask review.

| Frame | Target visible | YOLO target absent | SAM 2.1 | SAM 3 box | SAM 3 point | Note |
|---:|---|---|---|---|---|---|
| 210 | True | False | CORRECT_TARGET | EMPTY_OR_LOST | CORRECT_TARGET | Frozen target phone on table; masks align. |
| 576 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible. |
| 636 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Visible landline is frozen PROVISIONAL_MATCH distractor; all target masks empty. |
| 708 | True | False | EMPTY_OR_LOST | EMPTY_OR_LOST | CORRECT_TARGET | Frozen reviewed target smartphone in hand; point mask recovers it. |
| 834 | True | False | EMPTY_OR_LOST | EMPTY_OR_LOST | CORRECT_TARGET | Frozen reviewed target smartphone in hand; point mask continues it. |
| 948 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | DRIFT_TO_OTHER_OBJECT | Point mask on hand/toy edge after target leaves; guard accepted. |
| 1314 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible. |

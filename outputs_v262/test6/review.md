# test6 V2.6.2 physical-target review

Predictions were frozen before V2.6.2 mask review.

| Frame | Target visible | YOLO target absent | SAM 2.1 | SAM 3 box | SAM 3 point | Note |
|---:|---|---|---|---|---|---|
| 204 | True | False | CORRECT_TARGET | EMPTY_OR_LOST | CORRECT_TARGET | Frozen target phone on table; masks align. |
| 468 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible. |
| 732 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | DRIFT_TO_OTHER_OBJECT | 167-pixel point mask on hand edge; no target phone visible; guard accepted. |
| 990 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible. |

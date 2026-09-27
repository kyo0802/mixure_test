# test4 V2.6.2 physical-target review

Predictions were frozen before V2.6.2 mask review.

| Frame | Target visible | YOLO target absent | SAM 2.1 | SAM 3 box | SAM 3 point | Note |
|---:|---|---|---|---|---|---|
| 216 | True | False | PARTIAL_TARGET | EMPTY_OR_LOST | PARTIAL_TARGET | Frozen phone is under hand; both masks include hand pixels. |
| 534 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible. |
| 852 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible. |
| 1038 | True | False | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Frozen reviewed target phone is plainly on table; all masks empty. |
| 1164 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible. |

# test3 V2.6.2 physical-target review

Predictions were frozen before V2.6.2 mask review.

| Frame | Target visible | YOLO target absent | SAM 2.1 | SAM 3 box | SAM 3 point | Note |
|---:|---|---|---|---|---|---|
| 228 | True | False | CORRECT_TARGET | EMPTY_OR_LOST | CORRECT_TARGET | Frozen target phone on table; both nonempty masks align. |
| 540 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible in this checkpoint. |
| 852 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible in this checkpoint. |
| 1164 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible in this checkpoint. |

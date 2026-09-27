# test9 V2.6.2 physical-target review

Predictions were frozen before V2.6.2 mask review.

| Frame | Target visible | YOLO target absent | SAM 2.1 | SAM 3 box | SAM 3 point | Note |
|---:|---|---|---|---|---|---|
| 546 | True | False | CORRECT_TARGET | EMPTY_OR_LOST | CORRECT_TARGET | Frozen target smartphone on table; masks align. |
| 762 | None | None | NOT_REVIEWABLE | NOT_REVIEWABLE | NOT_REVIEWABLE | Small point mask under table; possible held phone cannot be identified with confidence. |
| 978 | False | None | DRIFT_TO_OTHER_OBJECT | EMPTY_OR_LOST | DRIFT_TO_OTHER_OBJECT | Both masks on object at toy base; target smartphone absent; guards accepted. |
| 1194 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible. |

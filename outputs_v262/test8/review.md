# test8 V2.6.2 physical-target review

Predictions were frozen before V2.6.2 mask review.

| Frame | Target visible | YOLO target absent | SAM 2.1 | SAM 3 box | SAM 3 point | Note |
|---:|---|---|---|---|---|---|
| 204 | True | False | CORRECT_TARGET | EMPTY_OR_LOST | CORRECT_TARGET | Frozen target smartphone on table; masks align. |
| 504 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible. |
| 804 | True | False | CORRECT_TARGET | EMPTY_OR_LOST | PARTIAL_TARGET | Confirmed same smartphone in hand; point mask includes substantial hand spill. |
| 840 | True | False | CORRECT_TARGET | EMPTY_OR_LOST | PARTIAL_TARGET | Same smartphone in hand near landlines; point mask includes hand spill. |
| 852 | True | False | CORRECT_TARGET | EMPTY_OR_LOST | CORRECT_TARGET | Red reviewed DISTRACTOR box is landline; both masks remain on original smartphone at left. |
| 864 | True | False | CORRECT_TARGET | EMPTY_OR_LOST | PARTIAL_TARGET | Red reviewed DISTRACTOR box is landline; point mask is only sliver of original smartphone. |
| 900 | True | False | PARTIAL_TARGET | EMPTY_OR_LOST | PARTIAL_TARGET | Original smartphone on ledge is mostly under hand; masks include hand. |
| 1002 | None | None | NOT_REVIEWABLE | NOT_REVIEWABLE | NOT_REVIEWABLE | Distant person holds a phone; cannot establish physical identity from this frame. |
| 1098 | False | None | EMPTY_OR_LOST | EMPTY_OR_LOST | EMPTY_OR_LOST | Target not visible. |

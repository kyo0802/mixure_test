# Pass I Evidence QC Report

Status: **PASS_I_PILOT1_READY_FOR_HUMAN_REVIEW**

DEV CandidateEpochs queued: 120; human-QC reviewed: 120.
Source inventory SHA-256: `2e6218682f8d9bce88fbece7ec887a8c9c3c7837aa1978f5d8e49cac94fff844`.
Pilot 0 designation: `DEV_PILOT_0_DATA_QUALITY_DISCOVERY`. Its inputs, GPT responses, annotations, and audit are preserved separately. Frozen data is outside this queue.

## Crop QC

| State | Count |
|---|---:|
| KEEP_PRIMARY | 92 |
| KEEP_WEAK | 52 |
| DROP_WRONG_TARGET | 119 |
| DROP_NOT_PHONE | 1 |
| DROP_TOO_CORRUPTED | 0 |
| DROP_DUPLICATE | 0 |

## CandidateEpoch QC

| State | Count |
|---|---:|
| VALID | 63 |
| MIXED_IDENTITY | 4 |
| NO_USABLE_TARGET | 53 |

## Observed quality rates among reviewed epochs

- Wrong-target crop incidence: 53/120 (44.2%).
- Confirmed wrong-target crops: 119/264 (45.1%) of selected crops.
- Non-phone crop incidence: 1/120 (0.8%).
- Mixed-identity epoch rate: 4/120 (3.3%).
- No-usable-target epoch rate: 53/120 (44.2%).

KEEP_WEAK is retained as legitimate target evidence. Blur, occlusion, difficult views, visual similarity, and identity ambiguity alone are not treated as upstream QC errors.

## DEV pool readiness

- QC-valid CandidateEpochs currently available: 63.
- Kept target crops in VALID epochs: 137; model-primary selections (1–3 per epoch): 104.
- Original DEV pairs with two reviewed VALID sides: 168.
- Original DEV pairs with at least one reviewed invalid side: 375.
- Fresh QC-valid DEV pairs excluding Pilot 0: 390.
- PRIMARY_VALID pairs: 159.
- HARD_VALID pairs: 231.
- INVALID_PAIR original DEV pairs with known reviewed invalid side: 375.
- Pilot 1 selection and GPT inference: see independent Pilot 1 manifest/report.

## Per-CandidateEpoch crop accounting

“Original crops” counts selected evidence crops before QC; “source observations” includes unselected raw observations from the CandidateEpoch.

| CandidateEpoch | Video | Epoch QC | Source observations | Original crops | Retained | Primary | Weak | Dropped |
|---|---|---|---:|---:|---:|---:|---:|
| `ce:val_6:0020` | val_6 | VALID | 18 | 6 | 6 | 1 | 5 | 0 |
| `ce:test8:0016` | test8 | NO_USABLE_TARGET | 19 | 6 | 0 | 0 | 0 | 6 |
| `ce:val_5:0009` | val_5 | VALID | 17 | 6 | 6 | 5 | 1 | 0 |
| `ce:test7:0028` | test7 | NO_USABLE_TARGET | 60 | 6 | 0 | 0 | 0 | 6 |
| `ce:test4:0011` | test4 | VALID | 4 | 2 | 2 | 2 | 0 | 0 |
| `ce:val_7:0012` | val_7 | VALID | 14 | 6 | 6 | 0 | 6 | 0 |
| `ce:val_6:0014` | val_6 | MIXED_IDENTITY | 2 | 1 | 1 | 0 | 1 | 0 |
| `ce:test8:0027` | test8 | NO_USABLE_TARGET | 2 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_5:0001` | val_5 | MIXED_IDENTITY | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:test7:0001` | test7 | MIXED_IDENTITY | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:test4:0012` | test4 | VALID | 2 | 1 | 1 | 1 | 0 | 0 |
| `ce:val_7:0089` | val_7 | VALID | 2 | 1 | 1 | 0 | 1 | 0 |
| `ce:val_6:0013` | val_6 | VALID | 7 | 2 | 2 | 0 | 2 | 0 |
| `ce:test8:0029` | test8 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_5:0017` | val_5 | MIXED_IDENTITY | 9 | 5 | 4 | 4 | 0 | 1 |
| `ce:test7:0017` | test7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test4:0026` | test4 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_7:0036` | val_7 | NO_USABLE_TARGET | 39 | 6 | 0 | 0 | 0 | 6 |
| `ce:val_6:0022` | val_6 | VALID | 3 | 1 | 1 | 1 | 0 | 0 |
| `ce:test8:0023` | test8 | NO_USABLE_TARGET | 14 | 6 | 0 | 0 | 0 | 6 |
| `ce:val_5:0005` | val_5 | VALID | 22 | 6 | 6 | 6 | 0 | 0 |
| `ce:test7:0037` | test7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test4:0018` | test4 | VALID | 5 | 3 | 3 | 3 | 0 | 0 |
| `ce:val_7:0017` | val_7 | NO_USABLE_TARGET | 71 | 6 | 0 | 0 | 0 | 6 |
| `ce:val_6:0018` | val_6 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test8:0010` | test8 | VALID | 6 | 3 | 3 | 0 | 3 | 0 |
| `ce:val_5:0003` | val_5 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:test7:0019` | test7 | VALID | 7 | 4 | 4 | 3 | 1 | 0 |
| `ce:test4:0022` | test4 | NO_USABLE_TARGET | 2 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_7:0032` | val_7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_6:0003` | val_6 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:test8:0019` | test8 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:val_5:0010` | val_5 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:test7:0040` | test7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test4:0013` | test4 | VALID | 2 | 1 | 1 | 1 | 0 | 0 |
| `ce:val_7:0024` | val_7 | NO_USABLE_TARGET | 65 | 6 | 0 | 0 | 0 | 6 |
| `ce:val_6:0008` | val_6 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:test8:0025` | test8 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:val_5:0015` | val_5 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:test7:0021` | test7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test4:0027` | test4 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_7:0050` | val_7 | NO_USABLE_TARGET | 14 | 6 | 0 | 0 | 0 | 6 |
| `ce:val_6:0012` | val_6 | VALID | 2 | 1 | 1 | 1 | 0 | 0 |
| `ce:test8:0015` | test8 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_5:0022` | val_5 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test7:0054` | test7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test4:0007` | test4 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:val_7:0052` | val_7 | NO_USABLE_TARGET | 8 | 4 | 0 | 0 | 0 | 4 |
| `ce:val_6:0009` | val_6 | VALID | 19 | 6 | 6 | 5 | 1 | 0 |
| `ce:test8:0004` | test8 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_5:0012` | val_5 | VALID | 5 | 3 | 3 | 0 | 3 | 0 |
| `ce:test7:0009` | test7 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:test4:0015` | test4 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:val_7:0097` | val_7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_6:0007` | val_6 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:test8:0026` | test8 | VALID | 8 | 3 | 3 | 3 | 0 | 0 |
| `ce:val_5:0011` | val_5 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:test7:0030` | test7 | NO_USABLE_TARGET | 37 | 6 | 0 | 0 | 0 | 6 |
| `ce:test4:0020` | test4 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:val_7:0042` | val_7 | VALID | 4 | 2 | 2 | 2 | 0 | 0 |
| `ce:val_6:0017` | val_6 | VALID | 18 | 6 | 6 | 6 | 0 | 0 |
| `ce:test8:0024` | test8 | VALID | 7 | 4 | 4 | 0 | 4 | 0 |
| `ce:val_5:0019` | val_5 | VALID | 18 | 6 | 6 | 6 | 0 | 0 |
| `ce:test7:0033` | test7 | NO_USABLE_TARGET | 19 | 6 | 0 | 0 | 0 | 6 |
| `ce:test4:0025` | test4 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_7:0037` | val_7 | NO_USABLE_TARGET | 41 | 6 | 0 | 0 | 0 | 6 |
| `ce:val_6:0001` | val_6 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:test8:0001` | test8 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:val_5:0023` | val_5 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:test7:0020` | test7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test4:0005` | test4 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:val_7:0087` | val_7 | NO_USABLE_TARGET | 13 | 6 | 0 | 0 | 0 | 6 |
| `ce:val_6:0023` | val_6 | VALID | 3 | 1 | 1 | 1 | 0 | 0 |
| `ce:test8:0011` | test8 | NO_USABLE_TARGET | 2 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_5:0002` | val_5 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:test7:0022` | test7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test4:0021` | test4 | NO_USABLE_TARGET | 4 | 3 | 0 | 0 | 0 | 3 |
| `ce:val_7:0039` | val_7 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:val_6:0010` | val_6 | VALID | 2 | 1 | 1 | 0 | 1 | 0 |
| `ce:test8:0014` | test8 | NO_USABLE_TARGET | 5 | 3 | 0 | 0 | 0 | 3 |
| `ce:val_5:0018` | val_5 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:test7:0045` | test7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test4:0030` | test4 | VALID | 6 | 4 | 4 | 3 | 1 | 0 |
| `ce:val_7:0088` | val_7 | NO_USABLE_TARGET | 10 | 4 | 0 | 0 | 0 | 4 |
| `ce:val_6:0004` | val_6 | VALID | 29 | 6 | 6 | 5 | 1 | 0 |
| `ce:test8:0028` | test8 | NO_USABLE_TARGET | 2 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_5:0008` | val_5 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:test7:0024` | test7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test4:0029` | test4 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:val_7:0057` | val_7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_6:0011` | val_6 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:test8:0003` | test8 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_5:0021` | val_5 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:test7:0006` | test7 | VALID | 6 | 3 | 3 | 3 | 0 | 0 |
| `ce:test4:0010` | test4 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:val_7:0086` | val_7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_6:0021` | val_6 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:test8:0006` | test8 | NO_USABLE_TARGET | 2 | 2 | 0 | 0 | 0 | 2 |
| `ce:val_5:0007` | val_5 | VALID | 17 | 6 | 6 | 6 | 0 | 0 |
| `ce:test7:0025` | test7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test4:0016` | test4 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:val_7:0064` | val_7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_6:0015` | val_6 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:test8:0031` | test8 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_5:0014` | val_5 | VALID | 6 | 3 | 3 | 3 | 0 | 0 |
| `ce:test7:0011` | test7 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |
| `ce:test4:0028` | test4 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_7:0030` | val_7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_6:0016` | val_6 | VALID | 2 | 1 | 1 | 1 | 0 | 0 |
| `ce:test8:0021` | test8 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_5:0020` | val_5 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:test7:0035` | test7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test4:0002` | test4 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_7:0093` | val_7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_6:0019` | val_6 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:test8:0008` | test8 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:val_5:0013` | val_5 | VALID | 18 | 6 | 6 | 4 | 2 | 0 |
| `ce:test7:0042` | test7 | NO_USABLE_TARGET | 1 | 1 | 0 | 0 | 0 | 1 |
| `ce:test4:0008` | test4 | VALID | 1 | 1 | 1 | 0 | 1 | 0 |
| `ce:val_7:0041` | val_7 | VALID | 1 | 1 | 1 | 1 | 0 | 0 |

These are observed rates in the selected DEV QC queue, not estimates for all 690 CandidateEpochs. No human QC state was inferred automatically.

# Pass I DEV Pilot — GPT vs Human Audit

Scope: fixed 40-item DEV pilot; 39 reviewed, 1 excluded, 0 unreviewed.
Human labels are visual annotations; this audit does not establish physical identity ground truth.
No frozen items or new model runs are included. The prompt is unchanged.

## 3×3 label table

| GPT \ Human | SAME | DIFFERENT | AMBIGUOUS | Total |
|---|---:|---:|---:|---:|
| SAME | 3 | 0 | 0 | 3 |
| DIFFERENT | 0 | 8 | 0 | 8 |
| AMBIGUOUS | 8 | 4 | 16 | 28 |
| Total | 11 | 12 | 16 | 39 |

Agreement: 27/39 (69.2%).
Label disagreements: 12/39 (30.8%).

## GPT AMBIGUOUS transitions

- GPT AMBIGUOUS → human SAME: **8/28 (28.6%)** of reviewed GPT AMBIGUOUS; 8/39 (20.5%) of all reviewed.
- GPT AMBIGUOUS → human DIFFERENT: **4/28 (14.3%)** of reviewed GPT AMBIGUOUS; 4/39 (10.3%) of all reviewed.

## False SAME

Confirmed GPT SAME → human DIFFERENT: 0 case(s). None.
An AMBIGUOUS human label would be reported separately as an unsupported SAME, not a confirmed false SAME.

## Challenge tag strata

Both GPT and human challenge tags are shown separately. A pair with multiple tags appears in multiple rows; “untagged” means no tag was selected. These rows must not be summed.

### Human tags

| Human challenge tag | Reviewed | Agree | Disagree | GPT AMBIGUOUS → human SAME | GPT AMBIGUOUS → human DIFFERENT |
|---|---:|---:|---:|---:|---:|
| (untagged) | 14 | 3 (21.4%) | 11 (78.6%) | 8 | 3 |
| distractor_present | 9 | 8 (88.9%) | 1 (11.1%) | 0 | 1 |
| front_vs_back | 5 | 5 (100.0%) | 0 (0.0%) | 0 | 0 |
| large_viewpoint_change | 2 | 2 (100.0%) | 0 (0.0%) | 0 | 0 |
| motion_blur | 1 | 1 (100.0%) | 0 (0.0%) | 0 | 0 |
| near_identical_appearance | 8 | 8 (100.0%) | 0 (0.0%) | 0 | 0 |
| partial_occlusion | 5 | 5 (100.0%) | 0 (0.0%) | 0 | 0 |
| poor_image_quality | 5 | 4 (80.0%) | 1 (20.0%) | 0 | 1 |

### GPT tags

| GPT challenge tag | Reviewed | Agree | Disagree | GPT AMBIGUOUS → human SAME | GPT AMBIGUOUS → human DIFFERENT |
|---|---:|---:|---:|---:|---:|
| distractor_present | 19 | 13 (68.4%) | 6 (31.6%) | 6 | 0 |
| front_vs_back | 9 | 8 (88.9%) | 1 (11.1%) | 0 | 1 |
| large_viewpoint_change | 5 | 4 (80.0%) | 1 (20.0%) | 0 | 1 |
| motion_blur | 7 | 6 (85.7%) | 1 (14.3%) | 0 | 1 |
| near_identical_appearance | 12 | 5 (41.7%) | 7 (58.3%) | 7 | 0 |
| none | 1 | 1 (100.0%) | 0 (0.0%) | 0 | 0 |
| partial_occlusion | 22 | 16 (72.7%) | 6 (27.3%) | 2 | 4 |
| poor_image_quality | 29 | 18 (62.1%) | 11 (37.9%) | 7 | 4 |


## GPT AMBIGUOUS → human DIFFERENT item details

### PI_000361

- GPT ambiguity cause: `LOW_QUALITY`; human label: `DIFFERENT`; human challenge tags: `(untagged)`.
- Q/R phone crop counts: 1/1.
- Q-1: `artifacts/pass_i/items/evidence/464d2b50cdbae8fcf9eb/crop_01.png` — 49×34 px.
- R-1: `artifacts/pass_i/items/evidence/c0d31e24b19521555fa0/crop_01.png` — 224×153 px.

### PI_000365

- GPT ambiguity cause: `VIEW_MISMATCH`; human label: `DIFFERENT`; human challenge tags: `(untagged)`.
- Q/R phone crop counts: 1/1.
- Q-1: `artifacts/pass_i/items/evidence/3188384c48dba492cd9e/crop_01.png` — 48×40 px.
- R-1: `artifacts/pass_i/items/evidence/09aaed23c055d379b6f2/crop_01.png` — 144×348 px.

### PI_000439

- GPT ambiguity cause: `LOW_QUALITY`; human label: `DIFFERENT`; human challenge tags: `(untagged)`.
- Q/R phone crop counts: 1/1.
- Q-1: `artifacts/pass_i/items/evidence/d0da7ad7b29a2e2d4744/crop_01.png` — 350×193 px.
- R-1: `artifacts/pass_i/items/evidence/2dc93dc59b3d2e09556c/crop_01.png` — 36×20 px.

### PI_000460

- GPT ambiguity cause: `LOW_QUALITY`; human label: `DIFFERENT`; human challenge tags: `distractor_present, poor_image_quality`.
- Q/R phone crop counts: 1/1.
- Q-1: `artifacts/pass_i/items/evidence/250c069a23928e17ba8e/crop_01.png` — 70×71 px.
- R-1: `artifacts/pass_i/items/evidence/26eb1710a5964a6a3dc1/crop_01.png` — 24×23 px.

## Manual disagreement inspection

The flags below are human review states. `UNREVIEWED` means no visual error attribution has been selected. Choose a flag in Streamlit → DEV pilot → Disagreement Review. Saving a flag does not change the human label or GPT draft.

| Item | GPT | Human | Flag | Note |
|---|---|---|---|---|
| PI_000361 | AMBIGUOUS | DIFFERENT | UNREVIEWED |  |
| PI_000365 | AMBIGUOUS | DIFFERENT | UNREVIEWED |  |
| PI_000424 | AMBIGUOUS | SAME | UNREVIEWED |  |
| PI_000439 | AMBIGUOUS | DIFFERENT | UNREVIEWED |  |
| PI_000460 | AMBIGUOUS | DIFFERENT | UNREVIEWED |  |
| PI_000820 | AMBIGUOUS | SAME | UNREVIEWED |  |
| PI_002025 | AMBIGUOUS | SAME | UNREVIEWED |  |
| PI_002091 | AMBIGUOUS | SAME | UNREVIEWED |  |
| PI_002107 | AMBIGUOUS | SAME | UNREVIEWED |  |
| PI_002108 | AMBIGUOUS | SAME | UNREVIEWED |  |
| PI_002126 | AMBIGUOUS | SAME | UNREVIEWED |  |
| PI_002137 | AMBIGUOUS | SAME | UNREVIEWED |  |

## Excluded from 3×3 table

| Item | GPT | Human status | Reason |
|---|---|---|---|
| PI_002016 | AMBIGUOUS | EXCLUDED | not_phone |

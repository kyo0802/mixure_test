# Pass I DEV Pilot 1 — Post-Human Audit

Status: **PASS_I_PILOT1_POST_HUMAN_AUDIT_COMPLETE**

Scope: fixed 40-item DEV Pilot 1 only. This audit reads existing annotations and GPT responses; it does not rerun inference or modify the prompt, evidence, selection, V297, or Frozen split.

## 1. Human completion

- Annotated: 40/40; reviewed: **40**; excluded: **0**; usable reviewed pairs: **40**.
- Human labels: SAME **2**, DIFFERENT **4**, AMBIGUOUS **34**.
- Human AMBIGUOUS causes: NO_DISCRIMINATIVE_FEATURE 19, VIEW_MISMATCH 15, LOW_QUALITY 0, CONFLICTING_EVIDENCE 0.
- Human challenge tags are multi-label; counts must not be summed: near_identical_appearance 25, front_vs_back 15, different_lighting 1, motion_blur 0, partial_occlusion 9, poor_image_quality 5, distractor_present 0, large_viewpoint_change 8, none 0.

## 2. GPT versus human

- GPT labels (all 40): SAME **0**, DIFFERENT **0**, AMBIGUOUS **40**.
- Human labels (usable 40): SAME **2**, DIFFERENT **4**, AMBIGUOUS **34**.
- Exact agreement: **34/40 (85.0%)**. Disagreement: **6/40 (15.0%)**.

### Full GPT × human matrix

| GPT \ Human | SAME | DIFFERENT | AMBIGUOUS | Total |
|---|---:|---:|---:|---:|
| SAME | 0 | 0 | 0 | 0 |
| DIFFERENT | 0 | 0 | 0 | 0 |
| AMBIGUOUS | 2 | 4 | 34 | 40 |
| Total | 2 | 4 | 34 | 40 |

### Directed disagreements

| Direction | Count | Item IDs |
|---|---:|---|
| GPT AMBIGUOUS → Human SAME | 2 | PI_100011, PI_100019 |
| GPT AMBIGUOUS → Human DIFFERENT | 4 | PI_100004, PI_100006, PI_100007, PI_100020 |
| GPT SAME → Human DIFFERENT | 0 | — |
| GPT SAME → Human AMBIGUOUS | 0 | — |
| GPT DIFFERENT → Human SAME | 0 | — |
| GPT DIFFERENT → Human AMBIGUOUS | 0 | — |

### Every disagreement

| Item | Pair quality | GPT label / cause | Human label | Human challenge tags | GPT challenge tags |
|---|---|---|---|---|---|
| PI_100004 | PRIMARY_VALID | AMBIGUOUS / LOW_QUALITY | DIFFERENT | near_identical_appearance, partial_occlusion, poor_image_quality | poor_image_quality, partial_occlusion, large_viewpoint_change |
| PI_100006 | PRIMARY_VALID | AMBIGUOUS / LOW_QUALITY | DIFFERENT | near_identical_appearance, partial_occlusion, poor_image_quality | poor_image_quality, partial_occlusion, different_lighting |
| PI_100007 | PRIMARY_VALID | AMBIGUOUS / LOW_QUALITY | DIFFERENT | near_identical_appearance, poor_image_quality | near_identical_appearance, poor_image_quality |
| PI_100011 | PRIMARY_VALID | AMBIGUOUS / LOW_QUALITY | SAME | near_identical_appearance | motion_blur, partial_occlusion, large_viewpoint_change, poor_image_quality |
| PI_100019 | HARD_VALID | AMBIGUOUS / LOW_QUALITY | SAME | near_identical_appearance, partial_occlusion, poor_image_quality | partial_occlusion, poor_image_quality |
| PI_100020 | PRIMARY_VALID | AMBIGUOUS / LOW_QUALITY | DIFFERENT | near_identical_appearance, large_viewpoint_change | large_viewpoint_change, different_lighting, partial_occlusion, poor_image_quality |

## 3. Stratification

Challenge-tag strata below are multi-label and overlap; each percentage uses the size of that row. They are descriptive and do not establish error cause.

### Pair quality

| Pair quality | Usable | Human SAME | Human DIFFERENT | Human AMBIGUOUS | Agree | Disagree |
|---|---:|---:|---:|---:|---:|---:|
| PRIMARY_VALID | 30 | 1 | 4 | 25 | 25 (83.3%) | 5 (16.7%) |
| HARD_VALID | 10 | 1 | 0 | 9 | 9 (90.0%) | 1 (10.0%) |

### GPT ambiguity cause versus human label

| GPT AMBIGUOUS cause | Pairs | Human SAME | Human DIFFERENT | Human AMBIGUOUS | Disagree |
|---|---:|---:|---:|---:|---:|
| NO_DISCRIMINATIVE_FEATURE | 7 | 0 | 0 | 7 | 0 (0.0%) |
| VIEW_MISMATCH | 14 | 0 | 0 | 14 | 0 (0.0%) |
| LOW_QUALITY | 19 | 2 | 4 | 13 | 6 (31.6%) |
| CONFLICTING_EVIDENCE | 0 | 0 | 0 | 0 | 0 (n/a) |

### Human ambiguity cause

| Human AMBIGUOUS cause | Pairs | GPT SAME | GPT DIFFERENT | GPT AMBIGUOUS |
|---|---:|---:|---:|---:|
| NO_DISCRIMINATIVE_FEATURE | 19 | 0 | 0 | 19 |
| VIEW_MISMATCH | 15 | 0 | 0 | 15 |
| LOW_QUALITY | 0 | 0 | 0 | 0 |
| CONFLICTING_EVIDENCE | 0 | 0 | 0 | 0 |

### Human challenge tags

| Human tag | Pairs | Human SAME | Human DIFFERENT | Human AMBIGUOUS | Agree | Disagree |
|---|---:|---:|---:|---:|---:|---:|
| near_identical_appearance | 25 | 2 | 4 | 19 | 19 (76.0%) | 6 (24.0%) |
| front_vs_back | 15 | 0 | 0 | 15 | 15 (100.0%) | 0 (0.0%) |
| different_lighting | 1 | 0 | 0 | 1 | 1 (100.0%) | 0 (0.0%) |
| motion_blur | 0 | 0 | 0 | 0 | 0 (n/a) | 0 (n/a) |
| partial_occlusion | 9 | 1 | 2 | 6 | 6 (66.7%) | 3 (33.3%) |
| poor_image_quality | 5 | 1 | 3 | 1 | 1 (20.0%) | 4 (80.0%) |
| distractor_present | 0 | 0 | 0 | 0 | 0 (n/a) | 0 (n/a) |
| large_viewpoint_change | 8 | 0 | 1 | 7 | 7 (87.5%) | 1 (12.5%) |
| none | 0 | 0 | 0 | 0 | 0 (n/a) | 0 (n/a) |
| untagged | 0 | 0 | 0 | 0 | 0 (n/a) | 0 (n/a) |

### GPT challenge tags

| GPT tag | Pairs | Human SAME | Human DIFFERENT | Human AMBIGUOUS | Agree | Disagree |
|---|---:|---:|---:|---:|---:|---:|
| near_identical_appearance | 15 | 0 | 1 | 14 | 14 (93.3%) | 1 (6.7%) |
| front_vs_back | 14 | 0 | 0 | 14 | 14 (100.0%) | 0 (0.0%) |
| different_lighting | 6 | 0 | 2 | 4 | 4 (66.7%) | 2 (33.3%) |
| motion_blur | 5 | 1 | 0 | 4 | 4 (80.0%) | 1 (20.0%) |
| partial_occlusion | 38 | 2 | 3 | 33 | 33 (86.8%) | 5 (13.2%) |
| poor_image_quality | 23 | 2 | 4 | 17 | 17 (73.9%) | 6 (26.1%) |
| distractor_present | 0 | 0 | 0 | 0 | 0 (n/a) | 0 (n/a) |
| large_viewpoint_change | 12 | 1 | 2 | 9 | 9 (75.0%) | 3 (25.0%) |
| none | 0 | 0 | 0 | 0 | 0 (n/a) | 0 (n/a) |
| untagged | 0 | 0 | 0 | 0 | 0 (n/a) | 0 (n/a) |

## 4. Pilot 0 versus Pilot 1 — descriptive only

Pilot 0 was selected before human Evidence QC; Pilot 1 uses a cleaned, different pair set. These are not matched samples and the differences are not a formal statistical estimate of a QC effect.

| Measure | Pilot 0 | Pilot 1 |
|---|---:|---:|
| Excluded / selected | 1/40 (2.5%) | 0/40 (0.0%) |
| GPT AMBIGUOUS / selected | 29/40 (72.5%) | 40/40 (100.0%) |
| GPT AMBIGUOUS / usable | 28/39 (71.8%) | 40/40 (100.0%) |
| Human AMBIGUOUS / usable | 16/39 (41.0%) | 34/40 (85.0%) |
| GPT–human disagreement / usable | 12/39 (30.8%) | 6/40 (15.0%) |
| GPT AMBIGUOUS → Human SAME / usable | 8/39 (20.5%) | 2/40 (5.0%) |
| GPT AMBIGUOUS → Human DIFFERENT / usable | 4/39 (10.3%) | 4/40 (10.0%) |
| GPT abstained on human-decisive pairs | 12/23 (52.2%) | 6/6 (100.0%) |

The excluded-item rate fell to zero, consistent with removing confirmed upstream evidence errors. GPT over-abstention did not fall: it rose to 40/40, while human ambiguity rose to 34/40. The lower disagreement rate mainly reflects more GPT–human agreement on AMBIGUOUS; GPT abstained on every human-decisive Pilot 1 pair. This does not show improved instance discrimination.

## 5. Conservative interpretation and next step

- Current bottleneck classification: **B. INSUFFICIENT_IDENTITY_INFORMATION** for most cleaned pairs (34/40 human AMBIGUOUS), plus **E. INCONCLUSIVE** for why GPT abstained on six human-decisive pairs. Upstream evidence quality was a confirmed Pilot 0 issue, but the cleaned Pilot 1 still leaves substantial identity uncertainty. The available data cannot distinguish prompt calibration from VLM capability.
- All six disagreements have GPT ambiguity cause LOW_QUALITY, and all six carry the human near_identical_appearance tag. This is an association in this small, selected pilot; it is not proof that either property caused the disagreement.
- **Exactly one next experimental step:** conduct a blinded, crop-cited human adjudication of the six disagreement pairs, recording the specific Q/R image numbers and instance-specific visual feature supporting each SAME or DIFFERENT decision. Do not change the prompt or run another model during that adjudication.

Prompt SHA-256 verified unchanged: `b6057e19de893514fabba7842dbd3a91957fc17e7255c2e9bfb2a3b16dd7b53d`. No Cohen’s kappa was calculated.

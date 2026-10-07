# FindMind Pass I phase closeout

**Status: PASS_I_CLOSED_ACQUISITION_LIMITED**

**Next phase: PASS T**

## 1. Scope and frozen baseline

This closes the current Pass I investigation. The diagnostic reads only the 12 sampled ambiguous DEV Pilot 1 pairs, their existing model-visible packages, and the two authorized CandidateEpoch source timelines per pair. It makes no new SAME/DIFFERENT judgments. V2.9.7 / V297 remains the frozen safety baseline. No VLM inference, prompt rerun, selector change, threshold change, Frozen split operation, or Pass T implementation was performed.

The project sequence remains: Freeze → non-Chinese VLM deployment → Stage 0 Smoke → Pass I / Pass T implementation and annotation → Qwen baseline comparison → Shadow Mode → End-to-End → trusted Memory Graph.

## 2. Completed Pass I findings

### Pilot 0

Pilot 0 is preserved as `DEV_PILOT_0_DATA_QUALITY_DISCOVERY`, not a formal benchmark. Of 40 selected pairs, 39 were reviewed and one excluded. Among 39 usable pairs, GPT labeled 28 AMBIGUOUS, humans labeled 16 AMBIGUOUS, and 12 GPT–human labels disagreed. It exposed evidence contamination and abstention, motivating the completed QC.

### Human Evidence QC

All 120 DEV CandidateEpochs were reviewed: VALID 63, MIXED_IDENTITY 4, NO_USABLE_TARGET 53. Among 264 originally selected crops: KEEP_PRIMARY 92, KEEP_WEAK 52, DROP_WRONG_TARGET 119, DROP_NOT_PHONE 1, DROP_TOO_CORRUPTED 0, DROP_DUPLICATE 0. Wrong-target drops were 119/264 (45.1%); 53/120 epochs (44.2%) had no usable target. Blur, occlusion, hard viewpoint, similar phones, and identity uncertainty by themselves were not QC failures. QC was not repeated here.

### Clean Pilot 1

Pilot 1 contains 40 fresh pairs disjoint from Pilot 0: 30 PRIMARY_VALID and 10 HARD_VALID. All 40 were human reviewed; none were excluded. GPT-6.1 Sol labeled all 40 AMBIGUOUS. Humans labeled SAME 2, DIFFERENT 4, AMBIGUOUS 34. Among the 34 human ambiguous pairs, 19 cite NO_DISCRIMINATIVE_FEATURE and 15 cite VIEW_MISMATCH. Exact GPT–human label agreement was 34/40, reflecting agreement on abstention rather than improved identity discrimination. The unchanged prompt is `pass_i_visual_annotator_v1`, SHA-256 `b6057e19de893514fabba7842dbd3a91957fc17e7255c2e9bfb2a3b16dd7b53d`.

### Six disagreement adjudications

The six fixed GPT AMBIGUOUS / human decisive cases were adjudicated blind at feature level. All six original human decisions were sustained: SAME 2, DIFFERENT 4, AMBIGUOUS 0. Five cite matching or incompatible distinctive tags/markings. PI_100020 relies mainly on color incompatibility and remains a weaker justification. GPT abstained on all six adjudicated human-decisive cases. These are visual judgments, not independent physical ground truth.

## 3. Minimal evidence coverage diagnostic

### Deterministic sample and method

From the 34 final human AMBIGUOUS Pilot 1 pairs, split by human ambiguity cause. In each group, sort item IDs ascending and select zero-based indices `floor((2*i+1)*n/12)` for `i=0..5`. This yields six of 15 VIEW_MISMATCH and six of 19 NO_DISCRIMINATIVE_FEATURE cases. The rule and IDs were fixed before inspecting any images. The VIEW_MISMATCH stratum includes front_vs_back; the NO_DISCRIMINATIVE_FEATURE stratum includes near_identical_appearance. The diagnostic did not use GT, future frames, tracker/alias decisions, or observations outside each authorized epoch.

For each pair side, the selected images were read from `pilot1/items/<item_id>/evidence.json`; available observations were read from `manifests/candidate_epoch_inventory.jsonl` and their raw crop paths. Selected image paths were matched exactly to source observations. The visual comparison asked whether an *unselected* valid view exposed materially more identity-discriminative physical detail than selected evidence. It did not relabel identity or assume that a back/side/larger image is inherently better.

Legend: `NOT_OBSERVED` = DISTINCTIVE_VIEW_NOT_OBSERVED; `BEST_SELECTED` = BEST_AVAILABLE_EVIDENCE_ALREADY_SELECTED. A single-observation side is recorded as NOT_OBSERVED; where multiple views existed but none was materially better than selected evidence, the best available is recorded as BEST_SELECTED. The other two epoch categories had zero cases. Counts below are pair-side appearances; four CandidateEpochs recur across pairs.

| Item | Human cause | Q epoch: available / selected, class | R epoch: available / selected, class | Evidence observation |
|---|---|---|---|---|
| PI_100002 | VIEW_MISMATCH | `ce:test4:0005`: 1/1, NOT_OBSERVED | `ce:test4:0030`: 6/3, BEST_SELECTED | Single Q front/edge view; R has six small similar back views. |
| PI_100005 | VIEW_MISMATCH | `ce:test4:0012`: 2/1, BEST_SELECTED | `ce:test4:0018`: 5/3, BEST_SELECTED | Q back tag is already selected; R contains only repeated dark fronts. |
| PI_100012 | VIEW_MISMATCH | `ce:test7:0006`: 6/3, BEST_SELECTED | `ce:test7:0011`: 1/1, NOT_OBSERVED | Q back tag already selected; R has one front view. |
| PI_100014 | VIEW_MISMATCH | `ce:test7:0009`: 1/1, NOT_OBSERVED | `ce:test7:0019`: 7/3, BEST_SELECTED | Q back/camera/side view selected; R repeated fronts without back detail. |
| PI_100024 | VIEW_MISMATCH | `ce:val_5:0008`: 1/1, NOT_OBSERVED | `ce:val_5:0019`: 18/3, BEST_SELECTED | Q has one front; R has repeated tagged backs and selected examples span that run. |
| PI_100026 | VIEW_MISMATCH | `ce:val_5:0013`: 18/3, BEST_SELECTED | `ce:val_5:0019`: 18/3, BEST_SELECTED | Q repeats dark fronts; R tagged back is selected across the epoch. |
| PI_100015 | NO_DISCRIMINATIVE_FEATURE | `ce:test8:0010`: 6/3, BEST_SELECTED | `ce:test8:0026`: 8/3, BEST_SELECTED | Both epochs remain front-facing; later unselected views do not expose a distinct mark. |
| PI_100018 | NO_DISCRIMINATIVE_FEATURE | `ce:test8:0001`: 1/1, NOT_OBSERVED | `ce:test8:0026`: 8/3, BEST_SELECTED | Q is a single partial front; R is repeated front view without new mark. |
| PI_100028 | NO_DISCRIMINATIVE_FEATURE | `ce:val_6:0007`: 1/1, NOT_OBSERVED | `ce:val_6:0020`: 18/3, BEST_SELECTED | Q has one dark front; R changes reflection/angle but still shows no persistent mark. |
| PI_100033 | NO_DISCRIMINATIVE_FEATURE | `ce:val_6:0007`: 1/1, NOT_OBSERVED | `ce:val_6:0022`: 3/1, BEST_SELECTED | Q has one dark front; R three near-identical dark fronts. |
| PI_100036 | NO_DISCRIMINATIVE_FEATURE | `ce:val_7:0042`: 4/2, BEST_SELECTED | `ce:val_7:0089`: 2/1, BEST_SELECTED | Q repeats a dark front; R has two similar front/profile views, including the selected one. |
| PI_100039 | NO_DISCRIMINATIVE_FEATURE | `ce:val_7:0039`: 1/1, NOT_OBSERVED | `ce:val_7:0042`: 4/2, BEST_SELECTED | Q is a front/edge view; R repeats the dark front already selected. |

Selected frames and source frame ranges are recorded for every Q/R side in [the machine-readable closeout](PASS_I_PHASE_CLOSEOUT.json). No sampled epoch had a defensible unselected view with materially more identity information. Thus there are no category-A replacement crops to list.

### Classification totals

| Level | Result | Count |
|---|---|---:|
| Pair-side CandidateEpoch appearances | DISTINCTIVE_VIEW_AVAILABLE_BUT_NOT_SELECTED | 0 |
| Pair-side CandidateEpoch appearances | DISTINCTIVE_VIEW_NOT_OBSERVED | 8 |
| Pair-side CandidateEpoch appearances | BEST_AVAILABLE_EVIDENCE_ALREADY_SELECTED | 16 |
| Pair-side CandidateEpoch appearances | INSUFFICIENT_TO_AUDIT | 0 |
| Pair | Q missed useful evidence only | 0 |
| Pair | R missed useful evidence only | 0 |
| Pair | BOTH missed useful evidence | 0 |
| Pair | NEITHER had better evidence available | 12 |
| Pair | INSUFFICIENT_TO_AUDIT | 0 |

The sample has 24 pair-side appearances representing 20 unique CandidateEpochs. The 12 pair outcomes are descriptive, not an estimate for all 34 ambiguous pairs.

Among the 13 unique multi-observation CandidateEpochs inspected, no materially better unselected identity view was observed (0/13). This bounded result supports that no systematic missed-view pattern was observed in this sample; it does not establish that the selector is error-free or globally optimal. Using the rule of three, the approximate 95% upper bound for an unobserved selector miss rate is 3/13 ≈ 23%. This is a heuristic requiring independent, representative observations; the small deterministic sample and shared source videos limit a population-level interpretation.

The eight NOT_OBSERVED pair-side appearances were single-observation CandidateEpochs. The observed acquisition limitation is therefore more specifically a temporal/view-coverage limitation: some sampled epochs are too short or contain too few observations to provide complementary identity views. This statement applies to this diagnostic, not the full dataset.

### Selected versus available view coverage

Manual conservative labels count each pair-side appearance once per property; categories overlap, and the same epoch can appear in two pairs. `Front-dominant` and `back-visible` describe dominant/visible surfaces, not identity certainty. `Side/profile-visible` requires a visible side/edge profile, not merely a one-pixel rim. `Distinctive marking` includes a visible sticker/tag; the same tagged R epoch occurs twice.

| Property | Model-selected evidence | Full available epoch timeline |
|---|---:|---:|
| Front-dominant | 18/24 | 18/24 |
| Back-visible | 6/24 | 6/24 |
| Side/profile-visible | 4/24 | 4/24 |
| Distinctive marking visible | 4/24 | 4/24 |

Because selected and full-epoch coverage counts are identical for all four reported properties in this bounded sample, this table supports the absence of an observed missed-view pattern; it should not be interpreted as a general comparison of viewpoint coverage or proof of selector optimality.

Repeated near-duplicate selected views occurred in 13/24 pair-side appearances. These repetitions did not hide a materially stronger authorized view in this sample. For example, the repeated tagged backs in PI_100024/PI_100026 and repeated dark fronts in PI_100015/PI_100018 were already represented by selected images. A visible camera module alone was not counted as a distinctive physical mark.

**Qualitative observation:** Some audited ambiguous examples contain dark or visually feature-poor front-facing phone views. Such views may contain little instance-specific appearance information, so an AMBIGUOUS decision can be appropriate. Existing pair-level observation text does not consistently assign this description to each Q/R side; no reliable pair-side count is reported and no images were relabeled for this patch.

## 4. Bottlenecks and bounded recommendation

**Primary: INSUFFICIENT_IDENTITY_INFORMATION.** The cleaned Pilot 1 has 34/40 human ambiguous pairs, and this bounded sample found no clear case where the selector omitted a materially more discriminative view already present in its CandidateEpoch. The observed limitation in this sample is evidence acquisition/view coverage, including one-sided front/back visibility or repeated feature-poor views. This does not imply that all ambiguous pairs are inherently undecidable or that the selector is globally optimal.

**Secondary: VLM_OVER_ABSTENTION_ON_SOME_HUMAN_DECIDABLE_CASES.** Six feature-cited human decisive judgments were sustained while GPT returned AMBIGUOUS. That is a separate observation; this diagnostic did not test its cause, recalibrate the prompt, or run another model.

Recommendation: **EVIDENCE_ACQUISITION_IS_PRIMARY_LIMITATION** for the small diagnostic. Preserve the current selector and safety boundary. Future work can seek more complementary authorized views when the upstream observation process naturally captures them; this report does not authorize a new Re-ID model, VLM, threshold change, or identity authority. There is no repeated missed-view pattern here to justify implementing a selector fix now.

## 5. Stop decision and next phase

Stop the Pass I investigation. Further large-scale manual Evidence QC is **not currently recommended**. Preserve AMBIGUOUS/UNCERTAIN when instance evidence is insufficient. Proceed to **Pass T** under the frozen V297 safety baseline.

## Carry-forward backlog

1. **TEMPORAL / VIEW COVERAGE:** Some CandidateEpochs contain only a single observation, limiting access to complementary identity views.
2. **VLM OVER-ABSTENTION:** GPT abstained on all six feature-cited human-decidable Pilot 1 cases. Future work may test a Pass I prompt v2 and candidate VLMs; `pass_i_visual_annotator_v1` remains frozen and unchanged.
3. **APPEARANCE-LIMITED IDENTITY:** Dark/feature-poor fronts and front-vs-back comparisons may be underdetermined from appearance alone. Future system-level reasoning may require temporal continuity, trajectory, spatial context, or other non-appearance evidence.

This backlog records future work and does not authorize implementation in this patch.

## 6. Preservation and regression checks

The diagnostic wrote only this report and `PASS_I_PHASE_CLOSEOUT.json`. Protected source/manifest/prompt, Pilot 0/Pilot 1 annotation, evidence-package, adjudication, and V297 source hashes were checked before and after. No new model inference was executed; no prompt or selector behavior was changed. The exact prompt SHA remains `b6057e19de893514fabba7842dbd3a91957fc17e7255c2e9bfb2a3b16dd7b53d`. Existing Pass I regression test result is recorded at closeout time below.
Regression: `tests/test_pass_i.py` and `tests/test_pass_i_pilot.py` passed **25/25** with the local Streamlit vendor path and a writable repo-local pytest temporary directory. The pytest directory was removed after the run.

Preservation references: the existing repository manifest `artifacts/pass_i/manifests/protected_before.json` (4,186 entries) and the prior closeout snapshot `C:/Users/smile/AppData/Local/Temp/findmind_pass_i_closeout/protected_hashes_before.json` (74 entries). The latter is a local temporary file. Pilot 1 model identity was verified from `artifacts/pass_i/prelabels/dev_pilot_1/transport_configuration.json`: `gpt-6.1-sol` (reported as GPT-6.1 Sol).

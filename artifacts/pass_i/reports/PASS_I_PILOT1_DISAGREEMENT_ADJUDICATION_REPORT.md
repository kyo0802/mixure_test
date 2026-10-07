# Pilot 1 Disagreement Adjudication — Final Report

Status: **PASS_I_PILOT1_DISAGREEMENT_ADJUDICATION_COMPLETE**

Scope: the six fixed DEV Pilot 1 disagreements only. The report reads saved blinded decisions, original human labels, and existing GPT pre-labels. It does not modify those sources or run inference.

## Case results

| Item | Original human | Adjudicated | Original decision | Q image number(s) | R image number(s) | Specific visible physical feature(s) | Physical-instance justification |
|---|---|---|---|---|---|---|---|
| PI_100004 | DIFFERENT | DIFFERENT | SUSTAINED | 1, 2 | 1, 2, 3 | Q1–Q2's color is different from R1-R3, tag on the phones  are different | The consistent differences in both color and the visible phone tag across multiple Q and R images indicate that they are different physical phones. |
| PI_100006 | DIFFERENT | DIFFERENT | SUSTAINED | 1 | 1, 2, 3 | Q1 shows a different phone color and different tag/marking from R1–R3. | The consistent differences in both color and the visible phone tag across multiple Q and R images indicate that they are different physical phones. |
| PI_100007 | DIFFERENT | DIFFERENT | SUSTAINED | 1 | 1, 2, 3 | Q1 shows a different phone color and different tag/marking from R1–R3. | The consistent differences in both color and the visible phone tag across multiple Q and R images indicate that they are different physical phones. |
| PI_100011 | SAME | SAME | SUSTAINED | 1, 2, 3 | 1 | Q1–Q3show a same phone color and same tag/marking  from R1 | The matching distinctive tag/marking is consistently visible in the same location across Q and R images, providing instance-specific evidence that they are the same physical phone. |
| PI_100019 | SAME | SAME | SUSTAINED | 1, 3 | 1 | Q1、Q3 and R show the same distinctive tag/marking with the same appearance and in the same position on the phone. | The matching appearance and location of the distinctive tag across Q and R provide instance-specific evidence that they are the same physical phone. |
| PI_100020 | DIFFERENT | DIFFERENT | SUSTAINED | 1, 2, 3 | 1 | Q1–Q3 show a different phone color from R1. | The consistent differences in both color across multiple Q and R images indicate that they are different physical phones. |

## Summary

- Adjudicated labels: **SAME 2**, **DIFFERENT 4**, **AMBIGUOUS 0**.
- Original decisive human judgments sustained: **6/6**; changed to AMBIGUOUS: **0/6**.
- Sustained SAME: PI_100011 and PI_100019 cite a distinctive tag/marking with matching appearance and placement in their referenced Q/R images. The adjudicator explicitly treated the matching marking, rather than generic phone appearance, as instance-specific evidence.
- Sustained DIFFERENT: PI_100004, PI_100006, and PI_100007 cite different visible tags/markings together with color differences. PI_100020 cites a consistent color difference across Q and R images, without a separate marking or damage cue in the saved explanation. That last justification is narrower and more sensitive to illumination or imaging conditions; this report preserves the adjudicated label without independently upgrading its certainty.
- GPT-6.1 Sol labeled all six AMBIGUOUS. Under the blinded adjudication record, it therefore still abstained on **6/6 sustained human-decisive cases**. Five cite a distinctive marking match or mismatch; the remaining case relies on color incompatibility. These are adjudicated visual judgments, not external physical-identity ground truth.

## Relationship to the Pilot 1 finding

The full Pilot 1 had 34/40 human AMBIGUOUS labels (19 NO_DISCRIMINATIVE_FEATURE and 15 VIEW_MISMATCH), so insufficient discriminative identity information remains common even after Evidence QC. These six cases show that some cleaned pairs can support a human decisive judgment while GPT still abstains. The two observations coexist; six sustained decisions do not make the other 34 pairs resolvable.

Original Pilot 1 annotations remain separate from these adjudications. No prompt, evidence, GPT output, V297 code, evidence selector, or Frozen data was changed.

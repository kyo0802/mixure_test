# Evaluation-only ground truth

This directory is never imported/read by `memory_graph.v21` inference. The inference CLI does not accept an annotation argument. Evaluation runs only after `prediction_manifest.json` is written and checks every frozen prediction hash.

The user narrative identifies the original black smartphone, physically different desk phones, basketball, distant green trash bin and distinct chairs. Task1 smartphone moves behind the basketball and never reappears; task2 smartphone moves behind the teddy bear and never reappears. Neither trajectory requires later reassociation. The green bin is not physically near the smartphone/basketball. These narrative statements are **not exact visibility intervals**.

`task*_annotations.json` separately records assistant visual review of exact raw frame indices, approximate visible-extent xyxy boxes, explicit excluded visibility states, reviewed track-crop mappings and manually judged usable fragment pairs. No algorithm generates GT from predicted class/identity. Detection overlays were inspected after raw pixels to attribute failures. This is a sparse, non-random diagnostic sample, not human-expert dense annotation or a benchmark.

Metrics use class-agnostic box IoU >= 0.3, then evaluate classification independently. Fully occluded, out-of-view and uncertain samples are excluded from recall. No GT is interpolated into unreviewed frames. Purity values apply only to matched reviewed observations. Fragment counts are lower bounds; full-video switch counts remain unmeasurable.

Task2's narrative detector-failure description is refined by the observations: several intermittent raw phone detections occur near the teddy bear, but none become a smartphone local track there. Other manually visible frames have no matching detection. Both detector and local-tracker failures therefore contribute; this evidence must not be mislabeled solely as persistent-association failure.

The two run histories use identical identity thresholds. A generic regression fixed before-visible context retention independently of these GT labels; required historical crops are capped at384px for GPU memory, not removed. No GT classes, destinations, temporal expectations or merge instructions occur in inference prompts.

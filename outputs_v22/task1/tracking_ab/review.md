# Task1 smartphone mask review

The single SAM 2.1 object was initialized at frame 240 from the frozen YOLO cell-phone box matching V2.1 track17. No GT box or corrective prompt entered inference. The object remained the black smartphone on all eight reviewed visible frames (270, 300, 348, 360, 372, 384, 396, 408). The mask at frame 348 covers the phone's visible portion and its bounding box includes nearby hand/background; this is a box-quality limitation, not confirmed object drift. Automatic area-change flags at frames 276 and 288 warrant inspection outside the scored samples.

At frame 420 the mask became empty and a `LOST` event was logged. GT marks frame 420 occluded, so this is not counted as a visible-frame miss. No reinitialization was used. The contact sheet's red rectangle is the evaluation-only GT box; green is the SAM mask. GT was never supplied to the predictor.

On the eight visible reviewed samples, A had 3 local hits and B had 8. On the six samples with raw YOLO evidence, A retained 3 and B retained 6. Sparse samples cannot establish full-video purity or the exact number of ID switches.

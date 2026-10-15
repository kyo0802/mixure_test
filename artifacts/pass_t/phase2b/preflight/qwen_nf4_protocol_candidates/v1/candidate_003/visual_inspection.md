# Direct visual spot inspection — six uniform8 storyboards

Inspected actual generated PNGs using the image viewer. Offline input QC only: no new event annotation, identity adjudication, GT changes or GT-driven parameter tuning. Frame selection remains fixed.

| Opaque window | Observation |
|---|---|
| W_db55b29f820c2b3e3afb | Multiple phone-like devices and camera movement; designated-target association cannot be certified under NONE. Later views change scene coverage. |
| W_5597d9b003977e053d70 | Table, phone, hand and background visible; full rectangular context preserved. |
| W_ec4751640324779435e6 | Table/phone and room context preserved; printed packaging is original scene content. |
| W_b8a53fea6aa8b92dc94f | Phone/hand, box and camera motion visible; later room context changes. No persistent state inferred. |
| W_f1d4f821d33515975293 | Box, phone and hand appear with later occlusion; full context retained. No placement/persistence conclusion added. |
| W_aef405003cc72cef0044 | Phone, table and box/room context; visible camera motion and original scene text. |

All six: three-column canvas, eight chronological full-context tiles and one blank cell; neutral F aliases/native PTS headers only. No GT bbox, event-role labels, human answers, reviewer ID or scores observed in these sheets. Header text is legible in unprocessed PNG; processor resizing reduces detail. No GT-derived overlay added.

Artificial-overlay inspection: PASS for these six sheets. Complete pixel semantic blinding: UNABLE_TO_DETERMINE across all 620 frames, other sheets and video metadata. Natural event evidence and original scene text are not answer annotations. This spot check cannot certify local identity or every contextual cue.

# V1 validation — 2026-09-22

Both supplied videos were processed from first to last frame. Results come from real YOLO11s detections, class-specific ByteTrack associations and the deterministic spatial/temporal pipeline. The initial missing-input condition was resolved when the videos appeared in the workspace.

| Measurement | task1.mp4 | task2.mp4 |
| --- | ---: | ---: |
| Source duration | 32.248 s | 30.812 s |
| Frames fully decoded | 967 / 967 | 924 / 924 |
| Sampled frames (including final endpoint) | 162 | 155 |
| Episodes | 1 | 1 |
| Raw detections | 1123 | 1512 |
| Track IDs, including anchors | 77 | 96 |
| Selected anchors | 8 | 4 |
| Relation observations | 347 | 405 |
| Stable relation intervals | 29 | 31 |
| Accepted anchor transitions | 0 | 0 |

Environment: Python 3.12.14, PyTorch 2.14.0+cpu, OpenCV 4.14.0, Ultralytics 8.4.158. CUDA unavailable; inference used CPU. Final configuration: YOLO11s, 960px inference, 5 sampled FPS. Each full pipeline run took approximately 56 seconds before the final visualization refinements.

`uv run pytest`: **19 passed**. These include relation geometry and resolution invariance, temporal noise rejection, a sustained anchor change producing a transition, simultaneous anchors producing no transition, gap/episode separation, graph multiedges, tracker continuity across a miss, scene-cut resets, video endpoints, and end-to-end JSON/PNG/MP4 creation.

Both `inspect_graph.py` commands succeeded. Main graph images and sampled annotated frames were visually inspected. `uv run python scripts/validate_outputs.py` audits every required artifact, metadata/decode counts, first/last sampled frames, episode coverage, JSON model validation, graph endpoints/counts, temporal support counts, PNG decoding, and annotated-video length/FPS/final-frame decoding. Its machine-readable report is `outputs/validation_report.json`.

## Interpretation and limitations found in these videos

- One episode per video is expected with this conservative histogram threshold: viewpoint changes were not forced into activity segments.
- **77 and 96 are track fragments, not counts of unique physical objects.** Fast camera motion and missed detections split identities. This is local tracking, not solved ReID.
- Zero transitions were investigated. In task1, objects with several stable anchor associations had overlapping intervals; conservative transition logic rejects those as ambiguous. In task2, each subject with stable memory predicates had only one anchor. No transfers were invented.
- The observed phone class includes cordless desk phones. A graph node labeled `cell_phone` is a detector label, not proof that it is the hand-carried phone shown earlier. Mirror/reflection content can produce extra person/laptop detections. The basketball was missed in a checked frame by nano, small and medium checkpoints.
- The nano baseline produced only 2 anchors and 3 stable intervals on task1. YOLO11s improved coverage without reducing temporal thresholds. A medium-checkpoint frame comparison did not recover the basketball or confidently resolve the table; the final baseline remains YOLO11s.
- `ON_OR_ABOVE` around the plush toy and microwave is useful projected evidence. `INSIDE` from overlapping boxes is **not** physical containment; the annotated images expose such detector/geometry limitations.
- Synthetic artifacts under `_synthetic_validation` and `_yolo_smoke` are explicitly labeled diagnostic fixtures. They are separate from task1/task2 and excluded from the results above.

The next upgrade should address camera-motion-aware identity continuity and evaluated object ReID before attempting lost-object reasoning or ranking. No V2 modules were implemented.

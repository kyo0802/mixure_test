# Actual V1 / V2 measurements

| Measurement | test1.mp4 | test2.mp4 |
| --- | ---: | ---: |
| Decoded frames | 967 | 924 |
| Sampled frames | 162 | 155 |
| V1 tracks | 77 | 96 |
| V1 anchors | 8 | 4 |
| V1 stable relation intervals | 29 | 31 |
| V2 tracks | 77 | 96 |
| V2 raw signals / merged / selected | 124 / 45 / 8 | 138 / 53 / 8 |
| VLM valid / partial / failed events | 8 / 1 / 0 | 8 / 1 / 0 |
| Recorded model generations | 56 | 55 |
| VLM component failures | 1 | 1 |
| Admitted VLM labels / unknown | 22 / 22 | 19 / 23 |
| Rejected tracks | 33 | 54 |
| VLM / geometry-only relation intervals | 4 / 86 | 2 / 78 |
| Rejected VLM relation claims | 11 | 5 |
| Interaction relation intervals | 0 | 0 |
| Observed relation transitions | 0 | 0 |
| Unique selected full-scene frames | 21 | 23 |

Partial events are included in valid events: independently validated components survive, with failed components excluded. Relation counts include sparse intervals and are not precision/recall or physical object counts. V1 is a regenerated local baseline; original historical outputs were not present.

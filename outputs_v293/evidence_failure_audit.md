# V2.9.2 unavailable evidence audit

Audited 54 unavailable requests before eligibility changes.

## Primary causes

- DENSE_MASK_ARTIFACT_LOST: 6
- WINDOW_HAS_NO_TRUSTED_TARGET: 44
- TRUSTED_REINIT_SEED_OMITTED: 4

## Per video

| Video | Primary failure counts |
|---|---|
| test1 | {"DENSE_MASK_ARTIFACT_LOST": 2, "WINDOW_HAS_NO_TRUSTED_TARGET": 4} |
| test2 | {"DENSE_MASK_ARTIFACT_LOST": 4, "WINDOW_HAS_NO_TRUSTED_TARGET": 2} |
| test3 | {"WINDOW_HAS_NO_TRUSTED_TARGET": 6} |
| test4 | {"WINDOW_HAS_NO_TRUSTED_TARGET": 6} |
| test5 | {"WINDOW_HAS_NO_TRUSTED_TARGET": 6} |
| test6 | {"WINDOW_HAS_NO_TRUSTED_TARGET": 6} |
| test7 | {"WINDOW_HAS_NO_TRUSTED_TARGET": 6} |
| test8 | {"TRUSTED_REINIT_SEED_OMITTED": 4, "WINDOW_HAS_NO_TRUSTED_TARGET": 2} |
| test9 | {"WINDOW_HAS_NO_TRUSTED_TARGET": 6} |

## Independent phase / mask findings

- NO_TARGET_BEFORE: 54
- NO_TARGET_DURING: 54
- NO_ANCHOR_DURING: 23
- TARGET_AFTER_REQUIRED_BUT_NOT_VISIBLE: 54
- NO_ANCHOR_AFTER: 26
- MASK_UNAVAILABLE: 54
- PAIR_NEVER_COVISIBLE: 54
- NO_ANCHOR_BEFORE: 1

Secondary counts overlap. Missing target authorization does not establish physical absence. Scene continuity was not measured by V292.

V292 _authorize_dense_rows reads video_root/target_masks.json instead of events/dense/event/target_masks.json, then overwrites the event RLE with an empty mapping.
V292 accepted_masks includes only target_full; authorized reinitialized masks are omitted.
V292 pair rows discard all non-authorized target frames before anchor/AFTER assessment.
V292 fixed peak +/-3 phase partition and both-visible requirement hide independent anchor coverage.
# task2 fusion review



Persistent entities: 95. Fusion decisions: {'NEW_ENTITY': 95, 'MATCH': 827, 'AMBIGUOUS': 5, 'CONFLICT': 1}.

Reviewed same-phone YOLO/SAM joint frames: 7. SAM-only accepted phone frames: 2.

Reviewed false merges: 0 / 4 distinct pairs.

Reviewed duplicate phone hypotheses: 1. Max unobserved remembered nodes in snapshots: 72.



V2.1 tracks22 and43 both map to phone_01 by local SAM continuity. Frame312 SAM is CONFLICT; it was not written to trusted phone history. Late candidates stay separate: {'late_candidate_1': 'candidate_phone_01', 'late_candidate_2': 'candidate_phone_02', 'late_candidate_3': 'candidate_phone_03'}. Candidate 1 corresponds to the reviewed original phone, so one conservative duplicate hypothesis remains; this is unresolved re-identification, not a false merge. Distinct desk phones remain distinct.



GT is sparse and non-random; this review cannot certify all unreviewed frames, all false merges, or full-video identity purity.

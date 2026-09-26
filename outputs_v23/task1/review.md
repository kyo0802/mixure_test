# task1 fusion review



Persistent entities: 75. Fusion decisions: {'NEW_ENTITY': 75, 'MATCH': 597, 'AMBIGUOUS': 2}.

Reviewed same-phone YOLO/SAM joint frames: 6. SAM-only accepted phone frames: 6.

Reviewed false merges: 0 / 2 distinct pairs.

Reviewed duplicate phone hypotheses: 0. Max unobserved remembered nodes in snapshots: 65.



The V2.1 phone track17 and SAM phone_track17 both support phone_01. After track17 ends, accepted SAM observations keep phone_01 visible until the mask vanishes at frame420; phone_01 remains UNOBSERVED. The later desk-phone track70 maps to a different entity. Static scene nodes remain in snapshots.



GT is sparse and non-random; this review cannot certify all unreviewed frames, all false merges, or full-video identity purity.

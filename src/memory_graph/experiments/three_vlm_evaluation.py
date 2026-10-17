"""CPU evaluator; reviewed identity/coverage required, never inferred from predictions."""
from .three_vlm_contract import interval_distance
def match_one_to_one(predictions,truth,tolerance):
    """Maximum-cardinality matching. Only explicit reviewed object IDs can match.

    Brackets may bound evidence without defining physical duration. Caller must
    supply evaluated time supports; missing timing/identity never matches.
    """
    adjacency=[]
    for p in predictions:
        edges=[]
        for j,g in enumerate(truth):
            if not p.get('reviewed_object_id') or p.get('time_interval') is None or g.get('time_interval') is None:continue
            if p['reviewed_object_id']!=g.get('reviewed_object_id') or p.get('type')!=g.get('type') or p.get('video_sha256')!=g.get('video_sha256'):continue
            if interval_distance(p['time_interval'],g['time_interval'])<=tolerance+1e-9:edges.append(j)
        adjacency.append(edges)
    assigned={}
    def visit(i,seen):
        for j in adjacency[i]:
            if j in seen:continue
            seen.add(j)
            if j not in assigned or visit(assigned[j],seen):assigned[j]=i;return True
        return False
    for i in range(len(predictions)):visit(i,set())
    return [{'prediction_index':i,'truth_index':j} for j,i in sorted(assigned.items())]
def eligible_coverage(row):
    return row.get('review_status')=='HUMAN_REVIEWED' and bool(row.get('reviewer_id')) and row.get('coverage')=='EXHAUSTIVE_ATTESTED' and row.get('entire_interval_reviewed') is True and row.get('all_pickup_placement_annotated') is True and row.get('no_unobservable_gap') is True and row.get('target_association_resolved') is True and row.get('ontology')=='PICKUP_PLACEMENT_ONLY' and not row.get('excluded',False)
def event_metrics(predictions,truth,coverage,tolerance):
    """No eligible coverage => unavailable metrics, not zero or implicit negatives."""
    if not any(eligible_coverage(c) for c in coverage):return {'eligible_intervals':0,'metrics':None,'reason':'NO_HUMAN_EXHAUSTIVE_ELIGIBLE_COVERAGE'}
    def within(e):
        interval=e.get('time_interval')
        return interval is not None and any(eligible_coverage(c) and c['video_sha256']==e.get('video_sha256') and c['start_s']<=interval[0]<=interval[1]<=c['end_s'] for c in coverage)
    # Explicit identity and final reviewed proposal grouping prevent automatic
    # collapse of two distinct real transitions with overlapping evidence brackets.
    ps=[p for p in predictions if within(p) and p.get('strict_accepted') and p.get('physical_review_status') in ('HUMAN_SUPPORTED','HUMAN_UNSUPPORTED') and p.get('reviewed_object_id') and p.get('reviewed_event_group')]
    grouped={}
    for p in ps:grouped.setdefault((p['video_sha256'],p['reviewed_object_id'],p['type'],p['reviewed_event_group']),p)
    ps=list(grouped.values());gs=[g for g in truth if within(g) and g.get('review_status')=='HUMAN_REVIEWED' and g.get('reviewed_object_id')]
    metrics={}
    for kind in ('PICKUP','PLACEMENT'):
        pp=[p for p in ps if p['type']==kind];gg=[g for g in gs if g['type']==kind];matches=match_one_to_one(pp,gg,tolerance);tp=len(matches);precision=tp/len(pp) if pp else None;recall=tp/len(gg) if gg else None
        metrics[kind]={'tp':tp,'fp':len(pp)-tp,'fn':len(gg)-tp,'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision is not None and recall is not None and precision+recall else (0.0 if gg and precision is not None else None)}
    return {'eligible_intervals':sum(eligible_coverage(c) for c in coverage),'metrics':metrics,'tolerance_seconds':tolerance}

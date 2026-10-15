"""Pure half-open interval and correlation bookkeeping; never deletes packs."""
from .sampling import digest


def interval_metrics(a, b):
    intersection = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = a[1] - a[0] + b[1] - b[0] - intersection
    shorter = min(a[1] - a[0], b[1] - b[0])
    return {'intersection': intersection, 'union': union,
            'iou': intersection / union if union else 0,
            'overlap_over_shorter': intersection / shorter if shorter else 0}


def relationships(windows):
    ordered = sorted(windows, key=lambda w: w['pack_id'])
    parents = {w['pack_id']: w['pack_id'] for w in ordered}
    def find(x):
        while parents[x] != x:
            x = parents[x]
        return x
    result = {w['pack_id']: {'duplicate_of': None, 'media_duplicate_of': None} for w in ordered}
    pairs = []
    for i, a in enumerate(ordered):
        for b in ordered[i+1:]:
            if (a['source_video_hash'], a['target_scope']) != (b['source_video_hash'], b['target_scope']):
                continue
            fm = interval_metrics(a['authorized_half_open_frames'], b['authorized_half_open_frames'])
            tm = interval_metrics([a['window_start_s'], a['window_end_s']], [b['window_start_s'], b['window_end_s']])
            if not fm['intersection'] or not tm['intersection']:
                continue
            parents[find(b['pack_id'])] = find(a['pack_id'])
            same_media = (a['authorized_half_open_frames'] == b['authorized_half_open_frames'] and
                          a['window_start_s'] == b['window_start_s'] and a['window_end_s'] == b['window_end_s'])
            same_task = same_media and a['task_context'] == b['task_context']
            if same_media:
                result[b['pack_id']]['media_duplicate_of'] = result[a['pack_id']]['media_duplicate_of'] or a['pack_id']
            if same_task:
                result[b['pack_id']]['duplicate_of'] = result[a['pack_id']]['duplicate_of'] or a['pack_id']
            original = interval_metrics(a['inclusive_half_open_equivalent'], b['inclusive_half_open_equivalent'])
            pairs.append({'a': a['pack_id'], 'b': b['pack_id'], 'operational_half_open': fm,
                          'inclusive_and_half_open_equivalent': original, 'time_overlap_s': tm['intersection'],
                          'same_source_evidence': True, 'media_duplicate': same_media,
                          'evaluation_duplicate': same_task,
                          'reason': 'SAME_MEDIA_DIFFERENT_CONTEXT_CORRELATED' if same_media and not same_task else
                                    'EQUIVALENT_TASK_DUPLICATE' if same_task else 'OVERLAPPING_SOURCE_EVIDENCE'})
    groups = {}
    for w in ordered:
        groups.setdefault(find(w['pack_id']), []).append(w['pack_id'])
    for ids in groups.values():
        group = 'OG_' + digest(sorted(ids))[:12]
        for id_ in ids:
            result[id_]['overlap_group_id'] = group
    return {'packs': result, 'pairs': pairs,
            'unique_media_windows': sum(x['media_duplicate_of'] is None for x in result.values()),
            'unique_evaluation_items': sum(x['duplicate_of'] is None for x in result.values()),
            'nonoverlapping_evidence_groups': len(groups),
            'split_policy': 'Same recording session and overlapping evidence groups must stay in one split; no split created.'}

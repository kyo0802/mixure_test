"""Read-only reuse of 552 outputs; owner-approved identity and temporal scope gates."""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
from consolidate_findmind_gt import (ROOT, EXP, OUT, PHYSICAL, affirmative, category,
    csv_read, csv_write, digest, file_sha, load_json, merge_intervals, overlap, require, save, verify)
from memory_graph.experiments.three_vlm_evaluation import match_one_to_one
from memory_graph.experiments.three_vlm_contract import interval_distance


def proposal_id(p):
    return f"{p['model']}:{p['window_id']}:{p['event_index']}"


def prepare_review(out):
    proposals = load_json(EXP / 'event_proposals.json')['proposals']
    dataset = load_json(EXP / 'dataset.json')
    windows = {w['window_id']: w for w in dataset['windows']}
    originals = {(m, r['window_id']): r for m, data in load_json(EXP / 'model_results.json').items() for r in data['rows']}
    rows = []
    for p in proposals:
        window = windows[p['window_id']]; frames = {f['alias']: f for f in window['frames']}
        raw_row = originals[(p['model'], p['window_id'])]
        original_event = raw_row['descriptive_content']['events'][p['event_index']]
        require(all(p[k] == original_event[k] for k in ('type', 'before_frames', 'after_frames')) and p['object_description'] == original_event['object'], 'Proposal differs from stored output')
        require(p['strict_accepted'] == raw_row['validation']['raw']['full_valid'] and p['video_sha256'] == window['source_video_sha256'], 'Proposal contract/source mismatch')
        known = all(a in frames for a in p['before_frames'] + p['after_frames']) and bool(p['before_frames']) and bool(p['after_frames'])
        expected = [max(frames[a]['native_pts_s'] for a in p['before_frames']), min(frames[a]['native_pts_s'] for a in p['after_frames'])] if known else None
        require(expected == p['evidence_bracket_native_pts'], 'Native PTS bracket mismatch')
        citations = {k: [frames.get(a, {'invalid_alias': a}) for a in p[k]] for k in ('before_frames', 'after_frames')}
        signature = digest({'video': p['video_sha256'], 'type': p['type'], 'description': p['object_description'],
                            'before': [f.get('source_frame_index') for f in citations['before_frames']],
                            'after': [f.get('source_frame_index') for f in citations['after_frames']]})[:16]
        rows.append({'proposal_id': proposal_id(p), 'model': p['model'], 'video_id': p['video_id'], 'window_id': p['window_id'],
                     'event_type': p['type'], 'object_description': p['object_description'], 'strict_valid': p['strict_accepted'],
                     'origin': p['origin'], 'source_time_bracket': json.dumps(p['evidence_bracket_native_pts']),
                     'bracket_is_not_event_duration': True, 'exact_claim_signature_candidate_only': signature,
                     'evidence_references': json.dumps(citations, ensure_ascii=False), 'raw_path': str((EXP / 'runs' / p['model'] / p['window_id'] / 'raw.txt').relative_to(ROOT)),
                     'owner_reviewer_id': '', 'physical_review': '', 'reviewed_object_category': '', 'reviewed_object_id': '',
                     'reviewed_event_group': '', 'same_event_group_confirmed': '', 'time_support_verified': '',
                     'wrong_target': '', 'state_evidence_consistency': '', 'decision_notes': ''})
    csv_write(out / 'prediction_review.csv', rows)
    return len(rows)


def read_predictions(out):
    originals = {proposal_id(p): p for p in load_json(EXP / 'event_proposals.json')['proposals']}
    rows = csv_read(out / 'prediction_review.csv'); seen = set(); result = []
    for row in rows:
        key = row['proposal_id']; require(key in originals and key not in seen, 'Unknown/duplicate proposal_id'); seen.add(key)
        p = dict(originals[key]); p['proposal_id'] = key
        # All prediction fields come from the immutable model artifact, not editable CSV cells.
        status = row['physical_review'].strip().upper()
        require(status in ('', 'SUPPORTED', 'UNSUPPORTED', 'UNCERTAIN'), 'Invalid physical_review')
        if status:
            require(row['owner_reviewer_id'].strip() and row['decision_notes'].strip(), 'Prediction review requires reviewer/notes')
        require(row['wrong_target'].upper() in ('', 'YES', 'NO', 'UNKNOWN'), 'Invalid wrong_target')
        require(row['state_evidence_consistency'].upper() in ('', 'SUPPORTED', 'CONTRADICTED', 'UNKNOWN'), 'Invalid state evidence review')
        bracket = p['evidence_bracket_native_pts']
        has_time = isinstance(bracket, list) and len(bracket) == 2 and all(isinstance(t, (int, float)) for t in bracket) and bracket[0] <= bracket[1]
        eligible = status in ('SUPPORTED', 'UNSUPPORTED') and row['reviewed_object_id'].strip() and row['reviewed_object_id'].upper() != 'UNKNOWN' and row['reviewed_object_category'].strip() and row['reviewed_event_group'].strip() and affirmative(row['same_event_group_confirmed']) and affirmative(row['time_support_verified']) and has_time
        p.update(physical_review_status={'SUPPORTED': 'HUMAN_SUPPORTED', 'UNSUPPORTED': 'HUMAN_UNSUPPORTED'}.get(status, 'UNREVIEWED'),
                 reviewed_object_id=row['reviewed_object_id'].strip() or None, reviewed_object_category=category(row['reviewed_object_category']),
                 reviewed_event_group=row['reviewed_event_group'].strip() or None, time_interval=bracket if has_time else None,
                 review_eligible=bool(eligible), review=row)
        result.append(p)
    require(seen == set(originals), 'Missing proposals: retain unreviewed rows rather than deleting')
    return result


def scope_applies(p, scope, truth=False):
    if p['video_id'] != scope['video_id']:
        return False
    cat = category(p['object_category']) if truth else p['reviewed_object_category']
    ids = scope['object_ids']; cats = scope['object_categories']
    return ('all' in cats or cat in cats) and ('ALL' in ids or p['reviewed_object_id'] in ids)


def within(p, scope):
    t = p.get('time_interval')
    return t is not None and scope['start_s'] <= t[0] <= t[1] <= scope['end_s']


def deduplicate(predictions):
    groups = defaultdict(list)
    for p in predictions:
        require(p['review_eligible'], 'Unreviewed prediction cannot be deduplicated as a real event')
        groups[(p['model'], p['video_id'], p['reviewed_event_group'])].append(p)
    result = []
    for key, members in groups.items():
        require(len({(p['reviewed_object_id'], p['type'], p['reviewed_object_category'], p['physical_review_status'], p['review']['wrong_target']) for p in members}) == 1,
                'Conflicting human event group: ' + str(key))
        # Do not optimize representative timing against GT or union citation brackets.
        selected = dict(sorted(members, key=lambda p: (p['window_id'], p['event_index']))[0])
        selected['deduplicated_proposal_ids'] = [p['proposal_id'] for p in members]
        result.append(selected)
    return result


def score(predictions, truth, tolerances):
    result = {}
    for tolerance in tolerances:
        kinds = {}
        for kind in PHYSICAL:
            pp, gg = [p for p in predictions if p['type'] == kind], [g for g in truth if g['type'] == kind]
            # Human-confirmed unsupported hypotheses can be FP but never TP even if timestamps coincide.
            supported = [p for p in pp if p['physical_review_status'] == 'HUMAN_SUPPORTED' and p['review']['wrong_target'].upper() != 'YES']
            matches = match_one_to_one(supported, gg, tolerance)
            tp, fp, fn = len(matches), len(pp) - len(matches), len(gg) - len(matches)
            kinds[kind] = {'tp': tp, 'fp': fp, 'fn': fn, 'predictions': len(pp), 'truth': len(gg),
                           'precision': tp / len(pp) if pp else None, 'recall': tp / len(gg) if gg else None,
                           'f1': 2 * tp / (len(pp) + len(gg)) if pp or gg else None,
                           'matches': [{'proposal_id': supported[m['prediction_index']]['proposal_id'], 'final_event_id': gg[m['truth_index']]['final_event_id'],
                                        'temporal_support_distance_s': interval_distance(supported[m['prediction_index']]['time_interval'], gg[m['truth_index']]['time_interval'])} for m in matches]}
        result[str(tolerance)] = kinds
    return result


def metric_view(ps, gt, windows, mode, tolerances, raw_invalid_intervals):
    """Local exhaustive scopes only. Unknown candidate identity blocks just its possible scopes."""
    eligible, blocked = [], []
    for scope in gt['coverage']:
        reasons = []
        model_windows = [w for w in windows if w['video_id'] == scope['video_id'] and (mode != 'strict_valid' or w['strict'])]
        allocation = merge_intervals([w['interval'] for w in model_windows])
        if not any(a <= scope['start_s'] and b >= scope['end_s'] for a, b in allocation):
            reasons.append('NO_COMPLETE_VALID_WINDOW_ALLOCATION_FOR_THIS_VIEW')
        # Unparseable output is missing evidence, never an empty event list.
        if mode == 'physical_candidates' and any(v == scope['video_id'] and overlap(interval, [scope['start_s'], scope['end_s']]) for v, interval in raw_invalid_intervals):
            reasons.append('UNPARSEABLE_OUTPUT_INTERSECTS_SCOPE')
        for p in ps:
            if p['video_id'] != scope['video_id'] or (mode == 'strict_valid' and not p['strict_accepted']):
                continue
            t = p['time_interval'] or next(w['interval'] for w in windows if w['window_id'] == p['window_id'])
            if not overlap(t, [scope['start_s'], scope['end_s']]):
                continue
            # Only a human-reviewed category can exclude another object class.
            if p['review'].get('owner_reviewer_id') and p['review'].get('physical_review', '').upper() in ('SUPPORTED', 'UNSUPPORTED', 'UNCERTAIN') and p['reviewed_object_category'] and 'all' not in scope['object_categories'] and p['reviewed_object_category'] not in scope['object_categories']:
                continue
            if not p['review_eligible']:
                reasons.append('UNREVIEWED_IDENTITY_TIME_OR_EVENT_GROUP'); continue
            if scope_applies(p, scope) and not within(p, scope):
                reasons.append('PREDICTION_BOUND_STRADDLES_SCOPE')
        # Do not turn a boundary-crossing known positive into an implicit negative.
        if any(scope_applies(g, scope, True) and overlap(g['time_interval'], [scope['start_s'], scope['end_s']]) and not within(g, scope) for g in gt['truth']):
            reasons.append('GT_EVENT_STRADDLES_SCOPE')
        if reasons: blocked.append({'scope_id': scope['scope_id'], 'reasons': sorted(set(reasons))})
        else: eligible.append(scope)
    selected = [p for p in ps if p['review_eligible'] and (mode != 'strict_valid' or p['strict_accepted']) and any(scope_applies(p, s) and within(p, s) for s in eligible)]
    # Check all reviewed group members before filtering to avoid accidental split groups.
    deduplicate([p for p in ps if p['review_eligible'] and (mode != 'strict_valid' or p['strict_accepted'])])
    pp = deduplicate(selected)
    gg = [g for g in gt['truth'] if any(scope_applies(g, s, True) and within(g, s) for s in eligible)]
    return {'eligible_scope_ids': [s['scope_id'] for s in eligible], 'blocked_scopes': blocked,
            'deduplicated_predictions': pp, 'gt_event_ids': [g['final_event_id'] for g in gg],
            'metrics_by_tolerance': score(pp, gg, tolerances) if eligible else None,
            'overall_full_dataset_f1': None, 'overall_reason': 'NO_FULL_DATASET_ALL_OBJECTS_EXHAUSTIVE_GROUND_TRUTH',
            'scope_only_metrics': True, 'excluded_proposals': len(ps) - len(selected)}


def evaluate(out, destination, gt_path=None):
    verify(out)
    gt = load_json(gt_path) if gt_path else {'truth': [], 'coverage': []}
    if gt_path:
        require(gt.get('schema_version') == 'findmind_consolidated_gt_v1', 'Use generated final_gt.json')
        require(gt['adjudication_sha256'] == file_sha(out / 'adjudication.csv') and gt['coverage_adjudication_sha256'] == file_sha(out / 'coverage_adjudication.csv'), 'GT is stale relative to owner CSVs; finalize again')
        receipt = load_json(gt_path.with_name('finalization_receipt.json'))
        require(file_sha(gt_path) == receipt['final_gt_sha256'], 'Final GT changed after finalization')
    results = load_json(EXP / 'model_results.json'); dataset = load_json(EXP / 'dataset.json')
    config = load_json(EXP / 'configuration.json'); tolerances = config['evaluation']['interval_tolerances_seconds']
    require(tolerances == [0, .2, .5], 'Unexpected historical temporal tolerances')
    ps = read_predictions(out); states = load_json(EXP / 'state_claims.json')
    wd = {w['window_id']: w for w in dataset['windows']}; output = {}
    for name, result in results.items():
        rows = result['rows']; model_ps = [p for p in ps if p['model'] == name]
        windows = [{'window_id': r['window_id'], 'video_id': r['video_id'], 'interval': wd[r['window_id']]['presentation_interval_half_open'],
                    'strict': r['validation']['raw']['full_valid']} for r in rows]
        unparseable = [(r['video_id'], wd[r['window_id']]['presentation_interval_half_open']) for r in rows if not isinstance(r.get('descriptive_content'), dict)]
        checks = {key: {'pass': sum(r['validation']['raw'].get(key) is True for r in rows), 'fail': sum(r['validation']['raw'].get(key) is False for r in rows),
                        'not_assessable': sum(r['validation']['raw'].get(key) is None for r in rows)} for key in ('json_valid', 'schema_valid', 'semantic_valid', 'citation_valid', 'full_valid')}
        views = {mode: metric_view(model_ps, gt, windows, mode, tolerances, unparseable) for mode in ('physical_candidates', 'strict_valid')}
        timing = []
        for p in model_ps:
            if p['time_interval'] is None: continue
            for g in gt['truth']:
                if p['review_eligible'] and p['video_id'] == g['video_id'] and p['type'] == g['type'] and p['reviewed_object_id'] == g['reviewed_object_id']:
                    timing.append({'proposal_id': p['proposal_id'], 'final_event_id': g['final_event_id'], 'citation_bound_distance_s': interval_distance(p['time_interval'], g['time_interval']), 'localization_not_event_duration': True})
        output[name] = {'completed_calls': result['completed'], 'contract': checks, 'event_proposals': len(model_ps),
                        'strict_event_proposals': sum(p['strict_accepted'] for p in model_ps), 'unreviewed_or_unusable_proposals': sum(not p['review_eligible'] for p in model_ps),
                        'state_claim_count': sum(s['model'] == name for s in states), 'views': views, 'temporal_grounding_pairs_descriptive': timing,
                        'wrong_target_review': dict(Counter(p['review']['wrong_target'].upper() or 'UNREVIEWED' for p in model_ps)),
                        'state_evidence_review': dict(Counter(p['review']['state_evidence_consistency'].upper() or 'UNREVIEWED' for p in model_ps)),
                        'internal_state_consistency': {'raw_calls_flagged_event_state_citations_inconsistent': sum('EVENT_STATE_CITATIONS_INCONSISTENT' in r['validation']['raw']['errors'] for r in rows),
                            'fence_body_calls_flagged_event_state_citations_inconsistent': sum('EVENT_STATE_CITATIONS_INCONSISTENT' in (r['validation'].get('normalized_body') or {}).get('validation', {}).get('errors', []) for r in rows),
                            'physical_correctness_not_inferred': True},
                        'native_citation_bounds': {'ordered': sum(p['time_interval'] is not None for p in model_ps), 'missing_or_reversed': sum(p['time_interval'] is None for p in model_ps), 'not_physical_duration': True},
                        'state_accuracy': None, 'state_accuracy_reason': '33 original reviewer state records are evidence, not owner-adjudicated exhaustive states; event evidence review reported separately.',
                        'normalized_body_full_valid_historical': result['normalized_body_full_valid_count'], 'unparseable_calls': len(unparseable)}
    destination.mkdir(parents=True, exist_ok=False)
    save(destination / 'evaluation.json', {'ground_truth_supplied': bool(gt_path), 'final_gt_sha256': file_sha(gt_path) if gt_path else None,
        'prediction_review_sha256': file_sha(out / 'prediction_review.csv'), 'temporal_tolerances_seconds': tolerances,
        'input_preservation_verified': True, 'new_generations': 0, 'models': output})
    report = ['# 三模型人工 GT 評估進度', '', '更新：2026-10-19。沿用既有 552 次生成，沒有新推論。', '',
              '| 模型 | 已完成 | Raw JSON | Raw schema | Raw full-strict | 事件假說 | 其中 strict | 待審／不可用 |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name, r in output.items():
        report.append(f"| {name} | {r['completed_calls']} | {r['contract']['json_valid']['pass']} | {r['contract']['schema_valid']['pass']} | {r['contract']['full_valid']['pass']} | {r['event_proposals']} | {r['strict_event_proposals']} | {r['unreviewed_or_unusable_proposals']} |")
    report += ['', f"人工 final GT：{'已提供' if gt_path else '尚待裁決'}。PICKUP／PLACEMENT 的局部 precision、recall、F1 只會在核准 scope、模型物件身分與事件去重已解決時產生；詳見 evaluation.json。", '',
               '目前未建立全資料集 exhaustive GT，所以 overall F1 保持 null。未審時間、未知身分、無法解析輸出不計為無事件或 TN。strict-invalid 假說只留在獨立 physical_candidates 分析，不能進 strict_valid 匹配。', '',
               '物件名稱相同與 citation 時間重疊不能證明同一實物或同一事件。跨視窗去重依人工 reviewed_event_group，選字典序最早視窗作代表，不看 GT 選最佳時間。兩個真正事件即使區間重疊仍保留不同 group。', '',
               '時間比較採既有 closed-interval distance 與 one-to-one maximum-cardinality，tolerance=0、0.2、0.5 秒。模型原生 before/after PTS 是引用界限，不是物理動作持續時間；只有人工確認該界限可定位轉變時才納入匹配。', '',
               'Wrong-target 與物理 state 支持需人工驗證；JSON/schema/semantic 合格不等於物理正確。33 筆原始 state 暫作證據，未自動變成人工裁決 state GT。', '',
               '先獨立完成 adjudication.csv 與 coverage_adjudication.csv，不用模型答案解決人工分歧。prediction_review.csv 為既有模型假說的獨立證據審閱表；可只處理欲評估的局部範圍，未審範圍透明保留 null。']
    for name, r in output.items():
        for mode, view in r['views'].items():
            report += ['', f"## {name} / {mode}", '', f"可評分 scopes：{len(view['eligible_scope_ids'])}；被門檻阻擋：{len(view['blocked_scopes'])}。"]
            if view['metrics_by_tolerance']:
                report += ['', '| tolerance | type | TP | FP | FN | precision | recall | F1 |', '|---|---|---:|---:|---:|---:|---:|---:|']
                for tol, kinds in view['metrics_by_tolerance'].items():
                    for typ, m in kinds.items():
                        report.append('| ' + ' | '.join(map(str, [tol, typ, m['tp'], m['fp'], m['fn'], m['precision'], m['recall'], m['f1']])) + ' |')
    (destination / 'THREE_VLM_COMPARATIVE_REPORT.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    return {name: {'calls': r['completed_calls'], 'proposals': r['event_proposals'], 'strict_proposals': r['strict_event_proposals'], 'unreviewed': r['unreviewed_or_unusable_proposals']} for name, r in output.items()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare-review', 'evaluate'])
    p.add_argument('--collection', type=Path, default=OUT); p.add_argument('--gt', type=Path); p.add_argument('--output', type=Path)
    args = p.parse_args()
    if args.action == 'prepare-review':
        verify(args.collection); result = {'review_rows': prepare_review(args.collection)}
    else:
        require(args.output is not None, 'Fresh --output directory required')
        result = evaluate(args.collection, args.output, args.gt)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__': main()

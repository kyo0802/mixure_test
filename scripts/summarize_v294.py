"""Summarize measured V294 calls and an explicit post-inference engineering review."""
import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.v294_strata.runner import ROOT, OUT, read, save, sha


def main(status):
    config = read(OUT/'final/selected_config.json')
    runs = [read(p) for p in sorted((OUT/'coder/runs').glob('*.json'))]
    if not runs and (OUT/'smoke/findmind_pack_test.json').exists():
        runs = [read(OUT/'smoke/findmind_pack_test.json')]
    physical = [r for r in runs if not r['diagnostic_only']]
    diagnostics = [r for r in runs if r['diagnostic_only']]
    review_path = OUT/'metrics/post_inference_review.json'
    review = read(review_path) if review_path.exists() else {'events': [], 'scope': 'No visual review completed'}
    reviews = {r['pack_id']: r for r in review['events']}
    def answer(r):
        return (r.get('response') or {}).get('answer') or {}
    field_metrics = {}
    for field in ['event_type', 'interaction_anchor', 'released', 'target_visible_after', 'final_relation', 'final_relation_anchor']:
        eligible = [r for r in runs if field in reviews.get(r['pack_id'], {}).get('admissible_values', {})
                    and field not in reviews.get(r['pack_id'], {}).get('ambiguity_not_confirmed_correct', [])]
        field_metrics[field] = {'reviewable': len(eligible), 'correct': sum(answer(r).get(field) in reviews[r['pack_id']]['admissible_values'][field] for r in eligible)}
    metrics = {'actual_unique_event_pack_calls': len(runs), 'complete_physical_packs': len(physical),
               'incomplete_diagnostic_packs': len(diagnostics),
               'event_type_distribution': dict(Counter(answer(r).get('event_type', 'ERROR') for r in runs)),
               'STATIC_count': sum(answer(r).get('event_type') == 'STATIC' for r in runs),
               'STATIC_rate': sum(answer(r).get('event_type') == 'STATIC' for r in runs)/len(runs) if runs else None,
               'release_distribution': dict(Counter(answer(r).get('released', 'ERROR') for r in runs)),
               'visibility_distribution': dict(Counter(answer(r).get('target_visible_after', 'ERROR') for r in runs)),
               'relation_distribution': dict(Counter(answer(r).get('final_relation', 'ERROR') for r in runs)),
               'schema_valid': sum(r['validation']['schema_valid'] for r in runs),
               'validator_valid': sum(r['validation']['valid'] for r in runs),
               'schema_valid_complete': sum(r['validation']['schema_valid'] for r in physical),
               'validator_valid_complete': sum(r['validation']['valid'] for r in physical),
               'runtime_errors': sum(bool(r['error']) for r in runs),
               'review_scope': review.get('scope'), 'field_quality': field_metrics,
               'unsupported_physical_claims': sum(r.get('unsupported_physical_claim', False) for r in review['events']) if review['events'] else None,
               'reviewed_packs': len(review['events']),
               'obvious_action_correct': sum(r.get('obvious_action_correct', False) for r in review['events']),
               'obvious_action_reviewable': sum(r.get('obvious_action_reviewable', False) for r in review['events']),
               'confirmed_release_reviewable': sum(r.get('confirmed_release_reviewable', False) for r in review['events']),
               'release_correct': sum(r.get('release_correct', False) for r in review['events']),
               'abstention_quality': review.get('abstention_quality'),
               'coverage_limits': review.get('coverage_limits', []),
               'operational_graph_writes': 0, 'identity_writes': 0, 'bank_writes': 0,
               'opened_validation_status': 'KNOWN_REGRESSION_NOT_NEW_HELD_OUT'}
    historical = [read(p) for p in (OUT/'coder/iterations').glob('*/runs/*.json')]
    metrics['execution_history'] = {
        'total_actual_findmind_calls': len(historical)+len(runs),
        'unique_packs': len({r['pack_id'] for r in historical+runs}),
        'historical_failed_calls': sum(bool(r['error']) for r in historical),
        'prompt_iterations': read(OUT/'prompts/prompt_iterations.json'),
        'per_iteration': {directory.name: {
            'calls': len(items := [read(p) for p in (directory/'runs').glob('*.json')]),
            'errors': sum(bool(r['error']) for r in items),
            'event_types': dict(Counter(answer(r).get('event_type', 'ERROR') for r in items))}
            for directory in sorted((OUT/'coder/iterations').iterdir()) if directory.is_dir()},
        'selected_iteration': 'v03',
        'scope': 'Smoke calls excluded; first real pack counted once in each prompt iteration. Prior failures retained.'}
    save(OUT/'metrics/reasoning_metrics.json', metrics); save(OUT/'coder/metrics.json', metrics)
    load = read(OUT/'setup/load_metrics.json') if (OUT/'setup/load_metrics.json').exists() else {}
    smoke = [read(p) for p in (OUT/'smoke').glob('*_test.json') if p.name != 'findmind_pack_test.json']
    samples = [r['resources'] for r in runs+smoke if 'resources' in r]
    inference_samples = list(samples)
    if load.get('resources'):
        samples.append(load['resources'])
    latency = [r['wall_seconds'] for r in runs]
    resource = {'selected_configuration': config, 'model_load_seconds': load.get('elapsed_seconds'),
                'RAM_before_load_bytes': load.get('resources', {}).get('ram_before_bytes'),
                'peak_system_RAM_bytes': max((s['peak_system_ram_used_bytes'] for s in samples), default=None),
                'min_available_RAM_bytes': min((s['min_system_ram_available_bytes'] for s in samples), default=None),
                'peak_global_VRAM_bytes': max((s['peak_global_vram_used_bytes'] for s in samples), default=None),
                'peak_commit_bytes': max((s['peak_system_commit_bytes'] for s in samples), default=None),
                'event_latency_median_seconds': statistics.median(latency) if latency else None,
                'event_latency_min_seconds': min(latency) if latency else None, 'event_latency_max_seconds': max(latency) if latency else None,
                'complete_event_latency_median_seconds': statistics.median(r['wall_seconds'] for r in physical) if physical else None,
                'diagnostic_event_latency_median_seconds': statistics.median(r['wall_seconds'] for r in diagnostics) if diagnostics else None,
                'per_event': [{'pack_id': r['pack_id'], 'seconds': r['wall_seconds'], 'images': len(r['request']['images']),
                               'server_timings': r.get('server_timings')} for r in runs],
                'image_dimensions': [800, 600], 'image_preprocessing': 'Frozen same-frame annotated renderer; separate ordered PNG images',
                'paging_measurement': 'Available RAM/commit sampled every ~2s; direct page-in/out rate counters unavailable. Inspect pagefile snapshots and load log as coarse evidence.',
                'model_disk_bytes': sum(p.stat().st_size for p in (ROOT/'tools/Strata-data').rglob('*') if p.is_file() and not p.name.endswith('.ranges')),
                'runtime_errors': metrics['runtime_errors']}
    resource['inference_only'] = {
        'peak_system_RAM_bytes': max((s['peak_system_ram_used_bytes'] for s in inference_samples), default=None),
        'min_available_RAM_bytes': min((s['min_system_ram_available_bytes'] for s in inference_samples), default=None),
        'peak_global_VRAM_bytes': max((s['peak_global_vram_used_bytes'] for s in inference_samples), default=None)}
    resource['selected_findmind_events_only'] = {
        'peak_system_RAM_bytes': max((r['resources']['peak_system_ram_used_bytes'] for r in runs), default=None),
        'min_available_RAM_bytes': min((r['resources']['min_system_ram_available_bytes'] for r in runs), default=None),
        'peak_global_VRAM_bytes': max((r['resources']['peak_global_vram_used_bytes'] for r in runs), default=None)}
    resource['cold_load_resources'] = {k: v for k, v in load.get('resources', {}).items() if k != 'timeline'}
    resource['resource_scope'] = 'Whole-system RAM/commit and global GPU usage, not isolated model allocation. Nonstreaming TTFT not measured.'
    resource['pagefile_snapshots'] = {p.name: json.loads(p.read_text(encoding='utf-8-sig'))
                                      for p in (OUT/'setup').glob('pagefile_*.json')}
    resource['default_configuration_rejected'] = 'Default pinned resident load caused CUDA host allocation refusal and 0 MiB engine VRAM headroom; retained in setup/load_metrics_default.json, excluded from selected configuration.'
    save(OUT/'metrics/resource_metrics.json', resource)
    for r in runs:
        save(OUT/f'runs/selected_final_runs/{r["pack_id"]}.json', r)
    source_paths = [p for p in (ROOT/'src/memory_graph/v294_strata').glob('*.py')]
    source_paths += list((ROOT/'scripts').glob('*v294*.*'))
    source_paths += [ROOT/'tests/test_v294_strata.py']
    source_paths += [ROOT/rel for rel in read(OUT/'setup/preserved_state.json')['files']
                    if rel.startswith(('src/', 'scripts/', 'configs/'))]
    source_paths += [ROOT/'src/memory_graph'/x for x in ['identity/guard.py', 'identity/pipeline.py', 'events/window_builder.py',
                                                                       'reasoning/pipeline.py', 'reasoning/contract.py', 'reasoning/json_contract.py', 'reasoning/validator.py']]
    save(OUT/'final/source_hashes.json', {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths})
    save(OUT/'final/status.json', {'status': status, 'updated_unix': time.time()})
    manifest_paths = [p for p in OUT.rglob('*') if p.is_file() and p.name != 'integrity_manifest.json' and p.suffix != '.log']
    save(OUT/'final/integrity_manifest.json', {'files': {p.relative_to(OUT).as_posix(): sha(p) for p in manifest_paths},
                                             'sources': read(OUT/'final/source_hashes.json'), 'status': status})
    print(json.dumps({'reasoning': metrics, 'resources': {k: v for k, v in resource.items() if k != 'per_event'}}, indent=2), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--status', required=True, choices=['V294_QWEN38_CODER_SUCCESS', 'V294_QWEN38_ORIGINAL_SUCCESS',
                    'V294_QWEN38_SUCCESS_WITH_HARDWARE_LIMITS', 'V294_QWEN38_NOT_PRACTICALLY_USABLE', 'V294_QWEN38_FAILED'])
    main(ap.parse_args().status)

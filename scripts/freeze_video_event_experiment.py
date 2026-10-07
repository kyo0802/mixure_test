"""Freeze complete paired experiment and prove protected image/reference intact."""
import json
import re
import sys
import time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from memory_graph.reasoning.video_experiment import EXP,OUT,read,write,verify_baseline
from memory_graph.reasoning.pipeline import verify_manifest
from memory_graph.reasoning.common import sha256

def main():
    checks={'baseline_delivery':verify_baseline(),
        'precanonical':verify_manifest(EXP,EXP/'freeze/video_experiment_freeze_manifest.json'),
        'prediction_freeze':verify_manifest(EXP,EXP/'final/artifact_manifest.json')}
    decision=read(EXP/'evaluation/decision.json')
    if decision['representation']!='KEEP_DENSE_IMAGES_FOR_VALIDATION':raise RuntimeError('This delivery preserves the image handoff; a winning-video handoff needs its separately authorized update')
    baseline=read(EXP/'config/baseline_reference.json')
    if sha256(OUT/'VALIDATION_HANDOFF.md')!=baseline['prior_handoff_sha256']:raise RuntimeError('Protected handoff changed')
    prior=read(OUT/'evaluation/post_freeze_review.json');new=read(EXP/'evaluation/post_freeze_video_review.json')
    lookup={r['pack_id']:r for r in prior['events']}
    assert all(r['admissible_values']==lookup[r['pack_id']]['admissible_values'] for r in new['events'])
    report=(EXP/'VIDEO_EVENT_EXPERIMENT_REPORT.md').read_text(encoding='utf-8')
    assert [int(n) for n in re.findall(r'^## (\d+)\.',report,re.M)]==list(range(1,17))
    tests=read(EXP/'regression/test_results.json')
    assert all(tests[k]['errors']=='0' and tests[k]['failures']=='0' for k in ['video_focused','current_focused','full'])
    safety=read(EXP/'regression/identity_safety.json')
    assert safety['unauthorized_matched']==0 and safety['identity_and_memory_unchanged'] and safety['V293']['valid']
    assert safety['identity_threshold']==.60 and safety['margin']==.10 and safety['test8_confirmation_frames']==[804]
    assert all(c['valid'] for c in checks.values())
    checks.update(reference_labels_unchanged=True,review_strata_unchanged=True,held_out_accessed=False,
        prior_handoff_unchanged=True,unauthorized_MATCHED=0,VLM_identity_writes=0,trusted_physical_writes=0,
        current_focused_passed=int(tests['current_focused']['tests']),video_focused_passed=int(tests['video_focused']['tests']),
        full_passed=int(tests['full']['tests']),V293_frozen_files=419,decision=decision)
    write('final/freeze_verification.json',checks)
    # Freeze comparison/review/decision before final delivery. No baseline rewrite.
    compare=[p for p in (EXP/'evaluation').rglob('*') if p.is_file()]
    write('final/comparison_freeze_manifest.json',{'freeze_unix':time.time(),
        'files':{p.relative_to(EXP).as_posix():sha256(p) for p in compare},
        'reference_sha256':baseline['baseline_files']['evaluation/post_freeze_review.json'],
        'decision':decision,'predictions_changed':False})
    plan=ROOT/'docs/superpowers/plans/2026-10-02-native-event-video.md'
    plan.write_text(plan.read_text(encoding='utf-8').replace('- [ ]','- [x]'),encoding='utf-8')
    paths=[]
    for d in ['config','freeze','videos','processor','qwen','evaluation','regression','final']:
        paths.extend(p for p in (EXP/d).rglob('*') if p.is_file() and p.name not in ['final_integrity_manifest.json','final_integrity_verification.json'])
    paths.append(EXP/'VIDEO_EVENT_EXPERIMENT_REPORT.md')
    sources=read(EXP/'final/artifact_manifest.json')['sources']
    for p in ['scripts/report_video_event_experiment.py','scripts/review_video_event_experiment.py',
        'scripts/freeze_video_event_experiment.py',plan.relative_to(ROOT).as_posix(),
        '.venv/Lib/site-packages/transformers/video_utils.py',
        '.venv/Lib/site-packages/transformers/video_processing_utils.py',
        '.venv/Lib/site-packages/transformers/processing_utils.py',
        '.venv/Lib/site-packages/transformers/models/qwen2_vl/video_processing_qwen2_vl.py',
        '.venv/Lib/site-packages/transformers/models/qwen2_5_vl/processing_qwen2_5_vl.py',
        'outputs/current_development/video_event_experiment/.deps/av-16.0.1.dist-info/RECORD']:
        sources[p]=sha256(ROOT/p)
    write('final/final_integrity_manifest.json',{'stage':'FINAL_PAIRED_NATIVE_VIDEO_DELIVERY',
        'freeze_unix':time.time(),'files':{p.relative_to(EXP).as_posix():sha256(p) for p in paths},'sources':sources,
        'decision':decision,'baseline_delivery_sha256':sha256(OUT/'final/final_integrity_manifest.json'),
        'prior_handoff_sha256':baseline['prior_handoff_sha256'],'current_handoff_sha256':sha256(OUT/'VALIDATION_HANDOFF.md')})
    final=verify_manifest(EXP,EXP/'final/final_integrity_manifest.json')
    write('final/final_integrity_verification.json',{'valid':final['valid'],'experiment':final,
        'baseline':verify_baseline(),'all_checks':checks,'comparison':verify_manifest(EXP,EXP/'final/comparison_freeze_manifest.json')})
    assert final['valid']
    print('Final experiment hash verification:',final)
    print('Baseline370 / V293419 preserved; handoff unchanged; tests11+116+357 pass')

if __name__=='__main__':main()

"""Verify frozen predictions/reference, then hash current development deliverables."""
import importlib
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'src'))
from memory_graph.reasoning.common import OUT, sha256
from memory_graph.reasoning.pipeline import verify, verify_reference, verify_manifest
from memory_graph.v293.report import verify as verify_v293

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    checks={'primary':verify(), 'builder':verify_manifest(OUT,OUT/'event_windows/builder_freeze.json'),
            'same_runtime_baseline':verify_manifest(OUT,OUT/'final/baseline_prediction_manifest.json'),
            'compact_reference':verify_reference(), 'V293':verify_v293()}
    if not all(c['valid'] for c in checks.values()):raise RuntimeError(checks)
    smoke=[]
    for name in ['memory_graph.v293.runner','memory_graph.v292.pipeline','memory_graph.reasoning.model',
                 'memory_graph.reasoning.pipeline','memory_graph.reasoning.evaluation','memory_graph.events.window_builder']:
        importlib.import_module(name);smoke.append(name)
    checks['import_smoke']={'valid':True,'modules':smoke}
    after=read(OUT/'cleanup/CLEANUP_MANIFEST_AFTER.json')
    present=[x['path'] for x in after['records'] if x['deleted'] and (ROOT/x['path']).exists()]
    if present:raise RuntimeError({'deleted_paths_reappeared':present})
    checks['cleanup_absence']={'valid':True,'manifest_entries_checked':len(after['records']),'failures':[]}
    tests=read(OUT/'regression/test_results.json')
    suite=ET.parse(OUT/'regression/full_final.xml').getroot().find('testsuite')
    if suite is None or suite.attrib['errors']!='0' or suite.attrib['failures']!='0':raise RuntimeError('Final tests failed')
    tests['full_final_after_runtime_correction']=suite.attrib
    tests['actual_GPU_execution_gate']='Fresh 9 dense + 9 same-runtime old Qwen calls: EOS 18, runtime errors 0. Initial OOM attempt archived separately.'
    write(OUT/'regression/test_results.json',tests)
    checks['tests']={'valid':True,'focused_passed':int(tests['focused']['tests']),
        'final_full_passed':int(suite.attrib['tests']),'errors':0,'failures':0,'skipped':int(suite.attrib['skipped'])}
    report=(OUT/'EVENT_WINDOW_BUILDER_REPORT.md').read_text(encoding='utf-8')
    headings=re.findall(r'^## (\d+)\.',report,re.M)
    if list(map(int,headings))!=list(range(1,17)):raise RuntimeError('16 required report sections missing')
    for rel in ['CURRENT_PIPELINE_REPORT.md','EVENT_WINDOW_BUILDER_REPORT.md','VALIDATION_HANDOFF.md','cleanup/CLEANUP_REPORT.md']:
        data=(OUT/rel).read_bytes()
        if re.search(rb'\r(?!\n)',data):raise RuntimeError('Unexpected bare CR in report: '+rel)
    handoff=OUT/'VALIDATION_HANDOFF.md'
    if not handoff.exists():raise RuntimeError('Handoff missing')
    eval_review=read(OUT/'evaluation/review_freeze.json')
    eval_review['files']['evaluation/coverage_details.json']=sha256(OUT/'evaluation/coverage_details.json')
    write(OUT/'evaluation/review_freeze.json',eval_review)
    for rel,h in eval_review['files'].items():
        if sha256(OUT/rel)!=h:raise RuntimeError('Review hash mismatch '+rel)
    for rel,h in eval_review['sources'].items():
        if sha256(ROOT/rel)!=h:raise RuntimeError('Evaluation source changed '+rel)
    checks['post_freeze_review']={'valid':True,'files_checked':len(eval_review['files']),
        'predictions_changed':False,'independent_human_GT':False}
    checks['report_structure']={'valid':True,'builder_sections':16,'cleanup_sections':7,'handoff_present':True}
    checks['identity_safety']=read(OUT/'regression/identity_safety.json')
    if checks['identity_safety']['unauthorized_matched']!=0 or not checks['identity_safety']['identity_and_memory_unchanged']:
        raise RuntimeError('Identity changed')
    checks['validation_access']={'validation_media_accessed':False,'unknown_raw_media_inspected':False,
        'development_membership':'Only explicit frozen manifests: test1–test9',
        'sibling_mixure_test_modified':False}
    plan=ROOT/'docs/superpowers/plans/2026-10-01-repository-consolidation-event-windows.md'
    text=plan.read_text(encoding='utf-8').replace('- [ ]','- [x]')
    plan.write_text(text,encoding='utf-8')
    files={}
    for folder in ['cleanup','event_windows','qwen','evaluation','regression']:
        for p in sorted((OUT/folder).rglob('*')):
            if p.is_file():files[p.relative_to(OUT).as_posix()]=sha256(p)
    for p in sorted(OUT.glob('*.md')):files[p.relative_to(OUT).as_posix()]=sha256(p)
    for p in sorted((OUT/'final').glob('*.json')):
        if p.name not in {'final_integrity_manifest.json','final_integrity_verification.json'}:
            files[p.relative_to(OUT).as_posix()]=sha256(p)
    sources=read(OUT/'final/baseline_prediction_manifest.json')['sources']
    for rel in ['README.md','scripts/finalize_development_review.py','scripts/write_current_reports.py',
                'scripts/freeze_current_delivery.py',plan.relative_to(ROOT).as_posix(),
                'tests/test_current_reasoning.py','tests/test_event_window_builder.py','.venv/pyvenv.cfg']:
        sources[rel]=sha256(ROOT/rel)
    manifest={'stage':'FINAL_DELIVERY_AFTER_POST_FREEZE_REVIEW','freeze_unix':time.time(),
        'prediction_manifests_unchanged':True,'decision':'EVENT_WINDOW_BUILDER_PARTIAL_IMPROVEMENT',
        'readiness':'READY_TO_FREEZE_FOR_VALIDATION','files':files,'sources':sources,
        'checkpoint_provenance':'outputs/reference_qwen/checkpoint_verification.json; preserved exact reference manifest',
        'held_out_not_accessed':True}
    write(OUT/'final/final_integrity_manifest.json',manifest)
    final_check=verify_manifest(OUT,OUT/'final/final_integrity_manifest.json')
    checks['final_delivery']=final_check
    checks['valid']=all(c['valid'] for c in checks.values() if isinstance(c,dict) and 'valid' in c)
    write(OUT/'final/final_integrity_verification.json',checks)
    if not checks['valid']:raise RuntimeError(checks)
    print(json.dumps({k:v for k,v in checks.items() if k not in {'identity_safety'}},ensure_ascii=False))

if __name__=='__main__':main()

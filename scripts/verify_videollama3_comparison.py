"""CPU provenance cross-check; no model imports or historical writes."""
from __future__ import annotations
import json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'artifacts/pass_i/runtime/vendor')]
from run_phase3_observation_ablation import validation
OUT=ROOT/'artifacts/pass_t/phase3/videollama3_full_v1'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    inv=read(OUT/'dataset_inventory.json');checks=[];derived=[]
    for c in read(OUT/'qwen_comparison.json'):
        w=next(w for w in inv['windows'] if w['pack_id']==c['window']);letter='A' if c['window']=='test5__W05' else 'B'
        folder=(ROOT/c['raw_path']).parent
        ip=folder/f'call_{letter}_input.json' if c['condition']!='A' else folder/f'call_{letter}_input_receipt.json'
        data=read(ip);frames=data.get('frames',data.get('frame_mapping'))
        # Historical A names differ from B/C; require the actual fields, never fill missing.
        expected=[(f['supplied_alias'],f['source_frame_index'],f['native_source_pts_s'],f['recorded_source_png_sha256']) for f in frames]
        actual=[(f['alias'],f['source_frame_index'],f['native_pts_s'],f['sha256']) for f in w['frames']]
        checks.append({'condition':c['condition'],'window':w['pack_id'],'same_ordered_alias_index_native_pts_png_hashes':expected==actual,'source_input_receipt_sha256':sha(ip),'same_task_schema':c['condition']=='C','same_model_specific_transport_text':False,'same_preprocessing':False})
        assert expected==actual,(c['condition'],w['pack_id'])
        ex=c['validation']['qualitative_extraction'];body_check=None
        if ex:
            schema=read(folder/('schema_v3.json' if c['condition']=='A' else 'schema.json'))
            body_check=validation(json.dumps(ex['claims']),schema,[f['alias'] for f in w['frames']],c['condition'])['strict']
        derived.append({'condition':c['condition'],'window':w['pack_id'],'raw_strict':c['validation']['strict'],'exact_single_outer_fence_body_check':body_check,'descriptive_only':True,'original_raw_changed':False,'invalid_promoted_to_authoritative':False})
    historical=read(ROOT/'artifacts/pass_t/phase3/observation_ablation_v1/preservation_before.json')
    changed=[p for p,h in historical.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
    result={'input_comparability':checks,'common_parsing_diagnostics':derived,'prior_563_file_preservation_baseline_checked':len(historical),'changed_prior_protected_files':changed}
    assert not changed
    with (OUT/'comparison_verification.json').open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print('Comparison provenance checks:',len(checks),'passed; historical preservation:',len(historical),'unchanged')
if __name__=='__main__':main()

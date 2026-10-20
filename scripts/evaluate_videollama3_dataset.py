"""Read-only CPU analysis of completed predictions; never imports a model.

Writes derived summaries/contact sheets only inside the new experiment directory.
No automatic physical correctness labels and no interpretation of missing as NO_EVENT.
"""
from __future__ import annotations
import json,hashlib,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'artifacts/pass_i/runtime/vendor')]
from run_phase3_observation_ablation import validation
OUT=ROOT/'artifacts/pass_t/phase3/videollama3_full_v1'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def write(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)

def describe(raw,schema,aliases):
    checked=validation(raw,schema,aliases,'C');ex=checked['qualitative_extraction']
    body=checked['strict_parsed'] if checked['strict']['json_valid'] else ex['claims'] if ex else None
    derived=validation(json.dumps(body,ensure_ascii=False),schema,aliases,'C') if ex else None
    # This does not grant authoritative status to extracted or invalid output.
    unknown=[];reversed_pairs=[]
    def scan(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k in ('frames','before_frames','after_frames') and isinstance(v,list):unknown.extend(a for a in v if a not in aliases)
                else:scan(v)
        elif isinstance(x,list):
            for v in x:scan(v)
    if body is not None:scan(body)
    if isinstance(body,dict):
        for e in body.get('events',[]):
            before=e.get('before_frames',[]);after=e.get('after_frames',[])
            if before and after and all(a in aliases for a in before+after) and max(map(aliases.index,before))>=min(map(aliases.index,after)):reversed_pairs.append(e)
    return {'strict':checked['strict'],'outer_fence_extraction':ex,'extracted_body_full_validation':derived['strict'] if derived else None,'descriptive_claims':body,'alias_membership_diagnostic':{'unknown_aliases':unknown,'temporal_order_violations':reversed_pairs,'physical_support_verified':False},'structured_validity_is_not_physical_correctness':True}

def main():
    inv=read(OUT/'dataset_inventory.json');schema=read(OUT/'schema.json');results=[]
    for w in inv['windows']:
        base={k:w[k] for k in ('pack_id','video_id','availability')}
        if w['availability']!='ELIGIBLE':results.append(base);continue
        dest=OUT/'calls'/w['pack_id']
        assert (dest/'receipt.json').exists() or (dest/'failure.json').exists(),('INCOMPLETE_EXECUTION',w['pack_id'])
        if (dest/'failure.json').exists():results.append({**base,'execution':'FAILED','failure':read(dest/'failure.json')});continue
        receipt=read(dest/'receipt.json');actual=w['duplicate_of'] or w['pack_id'];source=OUT/'calls'/actual
        r=describe((source/'raw.txt').read_text(encoding='utf8'),schema,[f['alias'] for f in w['frames']])
        results.append({**base,'execution':receipt['classification'],'generation_source':actual,'independent':not bool(w['duplicate_of']),'frames':len(w['frames']),'sampling':w['sampling'],'receipt':read(source/'receipt.json'),'generation':read(source/'generation.json'),'diagnostics':r,'physical_review':'UNREVIEWED_PENDING_SEPARATE_EVIDENCE_REVIEW'})
    pertest={}
    for i in range(1,10):
        rows=[x for x in results if x['video_id']==f'test{i}'];usable=[x for x in rows if 'diagnostics' in x];unique=[x for x in usable if x['independent']]
        pertest[f'test{i}']={'discovered':len(rows),'eligible':sum(x['availability']=='ELIGIBLE' for x in rows),'successful_window_records':len(usable),'unique_generations':len(unique),'unavailable':sum(x['availability']!='ELIGIBLE' for x in rows),'failed':sum(x.get('execution')=='FAILED' for x in rows),'strict_valid_unique':sum(x['diagnostics']['strict']['full_valid'] for x in unique),'descriptive_statuses':{s:sum((x['diagnostics']['descriptive_claims'] or {}).get('status')==s for x in unique) for s in ('EVENTS','NO_CONFIRMED_EVENT','UNCERTAIN')}}
    write(OUT/'results_summary.json',{'results':results,'per_test':pertest,'formal_accuracy_metrics':None,'reason':'EXPLORATORY_DEV; LIMITED_TARGET_SPECIFIC_GT; NON_EXHAUSTIVE_POSITIVES; OVERLAPPING_WINDOWS'})
    # Same parser and strict/extraction rules on existing Qwen raw; old files remain untouched.
    comparison=[];qbase=ROOT/'artifacts/pass_t/phase3/vlm_physical_state_pilot_v1';abc=ROOT/'artifacts/pass_t/phase3/observation_ablation_v1'
    for model_condition,folder in [('A',qbase),('B',abc/'condition_b_higher_detail'),('C',abc/'condition_c_state_first')]:
        prompt_path=folder/('prompt_v3.json' if model_condition=='A' else 'prompt.json')
        schema_path=folder/('schema_v3.json' if model_condition=='A' else 'schema.json')
        qs=read(schema_path)
        for letter,win in [('A','test5__W05'),('B','test7__W05')]:
            # Historical output names are discovered, never rerun.
            rawpath=folder/f'call_{letter}_raw.txt'
            if not rawpath.exists():
                candidates=[p for p in folder.glob('*raw*') if f'call_{letter}' in p.name]
                if len(candidates)!=1:raise ValueError(('QWEN_RAW_PATH_UNRESOLVED',str(folder),letter,[p.name for p in candidates]))
                rawpath=candidates[0]
            aliases=[f['alias'] for w in inv['windows'] if w['pack_id']==win for f in w['frames']]
            checked=validation(rawpath.read_text(encoding='utf8'),qs,aliases,model_condition)
            comparison.append({'model':'Qwen2.5-VL-7B-Instruct NF4','condition':model_condition,'window':win,'raw_path':str(rawpath.relative_to(ROOT)),'raw_sha256':sha(rawpath),'prompt_sha256':sha(prompt_path),'schema_sha256':sha(schema_path),'validation':checked,'direct_task_and_schema_comparison_with_videollama':model_condition=='C','image_preprocessing_matched':False,'physical_correctness':'REQUIRES_SEPARATE_EVIDENCE_REVIEW'})
    write(OUT/'qwen_comparison.json',comparison)
    # Contact sheets are actual selected source pixels, not synthetic fixtures.
    from PIL import Image,ImageDraw
    folder=OUT/'contact_sheets';folder.mkdir(exist_ok=True)
    for w in inv['windows']:
        if w['availability']!='ELIGIBLE' or w['duplicate_of']:continue
        width,height=420,260;frames=w['frames'];canvas=Image.new('RGB',(width*4,height*math.ceil(len(frames)/4)),(242,242,242));draw=ImageDraw.Draw(canvas)
        for i,f in enumerate(frames):
            im=Image.open(ROOT/f['path']).convert('RGB');im.thumbnail((420,236));x=(i%4)*width;y=(i//4)*height;canvas.paste(im,(x,y+24));draw.text((x+4,y+4),f"{f['alias']} S{f['source_frame_index']:06d} PTS={f['native_pts_s']:.3f}",fill='black')
        canvas.save(folder/(w['pack_id']+'.jpg'),quality=92)
    protected=read(OUT/'preservation_before.json');changed=[p for p,h in protected.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
    frozen=read(OUT/'input_freeze.json');component_changes=[p for p,h in frozen['components'].items() if sha(ROOT/p)!=h]
    model_changes=[p for p,h in frozen['model_files'].items() if sha(ROOT/p)!=h]
    write(OUT/'verification.json',{'protected_file_count':len(protected),'changed_protected_paths':changed,'changed_frozen_components':component_changes,'changed_model_paths':model_changes,'prompt_same_as_qwen_c':sha(OUT/'prompt.json')==sha(abc/'condition_c_state_first/prompt.json'),'schema_same_as_qwen_c':sha(OUT/'schema.json')==sha(abc/'condition_c_state_first/schema.json'),'graph_writes':0,'all_terminal':True,'unique_completed_generations':sum(x.get('independent',False) for x in results),'nonempty_raw_outputs':sum(bool((OUT/'calls'/x['generation_source']/'raw.txt').stat().st_size) for x in results if x.get('independent'))})
    assert not changed and not component_changes and not model_changes
    print(json.dumps(pertest,ensure_ascii=False))

if __name__=='__main__':main()

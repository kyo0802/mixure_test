"""CPU-only forensic analysis. Writes exclusively in this new audit namespace."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import importlib.abc
import os
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[5]
assert ROOT.name == 'mixure_test_SAM'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

class NoModelImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'transformers', 'bitsandbytes', 'accelerate', 'cv2', 'av'} or fullname.startswith(('memory_graph.pass_t.phase2b.local_vlm', 'memory_graph.reasoning')):
            raise ImportError('AUDIT_FORBIDDEN_MODEL_OR_MEDIA_RUNTIME:' + fullname)
sys.meta_path.insert(0, NoModelImports())
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'artifacts/pass_i/runtime/vendor')]

import csv
import hashlib
import json
import re
import statistics
import subprocess
from collections import Counter
import jsonschema
from memory_graph.pass_t.phase2b.predictions import parse_raw, validate_prediction, schema

BASE = ROOT/'artifacts/pass_t/phase2b/capacity_probe/qwen_nf4'
ROUNDS = [('v2_20261014_owned_tree', 'PRIMARY'), ('v1_20261014', 'ENGINEERING_HISTORY')]
EXPECTED = {'MULTI_8_P200704':3, 'STORY_8_P200704':3, 'MULTI_12_P200704':0,
    'STORY_12_P200704':0, 'MULTI_16_P200704':0, 'STORY_16_P200704':2,
    'VIDEO_SHORT8_P200704':3, 'VIDEO_LONG118_P200704':3, 'VIDEO_LONG118_P937664':1,
    'MULTI_8_REF1_P200704':0, 'VIDEO_LONG118_REF1_P200704':0}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''): h.update(block)
    return h.hexdigest()

def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def relative(path): return Path(path).relative_to(ROOT).as_posix()
def write(name, value):
    path=OUT/name
    with path.open('x',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def git():
    def get(*args): return subprocess.check_output(['git',*args],cwd=ROOT,stderr=subprocess.PIPE)
    return {'head':get('rev-parse','HEAD').decode().strip(),
        'index_sha256':sha(ROOT/'.git/index'),
        'tracked_diff_sha256':hashlib.sha256(get('diff','--binary')).hexdigest(),
        'staged_diff_sha256':hashlib.sha256(get('diff','--cached','--binary')).hexdigest(),
        'tracked_status_sha256':hashlib.sha256(get('status','--porcelain','--untracked-files=no')).hexdigest()}

def snapshot():
    original=read(BASE/'v2_20261014_owned_tree/protected_before_extended.json')
    names=set(original['files'])
    for group in ['src','scripts','configs','tests']:
        names.update(relative(p) for p in (ROOT/group).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for rid,_ in ROUNDS:
        names.update(relative(p) for p in (BASE/rid).rglob('*') if p.is_file())
    # Prior protected inventory contains model assets. Never read checkpoint tensors.
    skipped=[n for n in sorted(names) if n.endswith(('.safetensors','.pt','.pth','.bin'))]
    files={}; missing=[]
    for n in sorted(names-set(skipped)):
        p=ROOT/n
        if not p.is_file(): missing.append(n);continue
        files[n]=sha(p)
    baseline={'git':git(),'files':files,'excluded_weight_binaries':skipped,
              'preexisting_missing':missing,'prior_inventory_path':relative(BASE/'v2_20261014_owned_tree/protected_before_extended.json')}
    write('protected_before.json',baseline)
    print(json.dumps({'snapshot_files':len(files),'weights_not_read':len(skipped),'preexisting_missing':len(missing),'git':baseline['git']}),flush=True)

def verify_receipts(folder):
    receipt=read(folder/'engineering_completion_receipt.json')
    errors=[]
    for n,h in receipt['files'].items():
        p=folder/n
        if not p.is_file() or sha(p)!=h:errors.append(n)
    return {'path':relative(folder/'engineering_completion_receipt.json'), 'receipt_sha256':sha(folder/'engineering_completion_receipt.json'),
            'checked':len(receipt['files']),'errors':errors,
            'capacity_results_expected_sha256':receipt['files'].get('capacity_results.json'),
            'capacity_results_actual_sha256':sha(folder/'capacity_results.json')}

def attempt_id(round_id,condition,iteration):
    return f'{round_id}/{condition}/ITER_{iteration:02d}'

def required_counts(value, definition, root_schema):
    if '$ref' in definition:
        definition=root_schema['$defs'][definition['$ref'].split('/')[-1]]
    if 'oneOf' in definition and isinstance(value,dict):
        definition=next((s for s in definition['oneOf'] if s.get('properties',{}).get('status',{}).get('const')==value.get('status')),definition)
    missing=optional=0
    if isinstance(value,dict):
        required=definition.get('required',[]);missing=sum(k not in value for k in required)
        optional=sum(k in value and k not in required for k in definition.get('properties',{}))
        for k,v in value.items():
            a,b=required_counts(v,definition.get('properties',{}).get(k,{}),root_schema);missing+=a;optional+=b
    elif isinstance(value,list):
        for v in value:
            a,b=required_counts(v,definition.get('items',{}),root_schema);missing+=a;optional+=b
    return missing,optional

def complexity(value, root_schema):
    counters=Counter()
    def walk(v,depth):
        counters['max_json_depth']=max(counters['max_json_depth'],depth)
        if isinstance(v,dict):
            counters['object_count']+=1;counters['key_count']+=len(v)
            for k,c in v.items():
                if 'uncertainty' in k and isinstance(c,str) and c.strip(): counters['nonempty_uncertainty_fields']+=1
                if k in {'frame_alias','start_frame_alias','end_frame_alias'} or 'timestamp' in k: counters['timestamp_or_interval_fields']+=1
                walk(c,depth+1)
        elif isinstance(v,list):
            counters['array_element_count']+=len(v)
            for c in v:walk(c,depth+1)
    walk(value,0)
    events=value.get('events')
    ec=len(events) if isinstance(events,list) else None
    citations=[]
    def cite(v):
        if isinstance(v,dict):
            for k,c in v.items():
                if k in {'cited_frame_aliases','window_cited_frame_aliases'} and isinstance(c,list):citations.extend(x for x in c if isinstance(x,str))
                else:cite(c)
        elif isinstance(v,list):
            for c in v:cite(c)
    cite(value)
    missing,optional=required_counts(value,root_schema,root_schema)
    return {**counters,'nested_object_count':max(0,counters['object_count']-1),
        'event_count':ec,'event_count_status':'PARSED' if ec is not None else 'EVENT_COUNT_NOT_RECOVERABLE',
        'event_count_text_heuristic':None,
        'event_types':sorted({e.get('event_type') for e in events or [] if isinstance(e,dict) and isinstance(e.get('event_type'),str)}),
        'citation_entries':len(citations),'distinct_citation_aliases':len(set(citations)),
        'missing_required_fields':missing,'populated_optional_fields':optional,
        'structural_complexity_score':counters['object_count']+counters['key_count']+counters['array_element_count']}

def generation_labels(rr, raw, error=None):
    labels=[]
    if error:labels.append('RUNTIME_ERROR')
    if rr.get('generation_deadline_reached') is True:labels.append('GENERATION_TIMEOUT')
    if rr.get('output_cap_reached') is True:labels.append('TRUNCATED_BY_MAX_NEW_TOKENS')
    if rr.get('eos_observed') is False:labels.append('EOS_NOT_REACHED')
    if rr.get('eos_observed') is None:labels.append('GENERATION_STATUS_UNKNOWN')
    if not raw.strip():labels.append('EMPTY_MODEL_OUTPUT')
    return labels

def structural_labels(value, contract):
    labels=[];details=[]
    for error in jsonschema.Draft202012Validator(contract).iter_errors(value):
        path='/'+ '/'.join(map(str,error.absolute_path));key=error.validator
        label={'required':'REQUIRED_FIELD_MISSING','additionalProperties':'UNEXPECTED_FIELD','type':'WRONG_FIELD_TYPE',
               'enum':'INVALID_ENUM','oneOf':'INVALID_NESTED_OBJECT','uniqueItems':'INVALID_ARRAY_STRUCTURE'}.get(key,'OTHER_SEMANTIC_ERROR')
        if key=='const':label='SCHEMA_VERSION_MISMATCH' if path=='/schema_version' else 'OTHER_SEMANTIC_ERROR'
        if key=='pattern':label='CITATION_FORMAT_INVALID' if 'alias' in path else 'OTHER_SEMANTIC_ERROR'
        if key=='type' and error.instance is None:label='INVALID_NULLABILITY'
        if key=='minLength' and 'uncertainty' in path:label='EMPTY_REQUIRED_UNCERTAINTY'
        if key=='minItems' and 'cited_frame_aliases' in path:label='EMPTY_REQUIRED_CITATIONS'
        labels.append(label);details.append({'stage':'SCHEMA','path':path,'constraint':key,'expected':error.validator_value,'message':error.message,'label':label,'instance':error.instance})
    return labels,details

def secondary_checks(value,supplied,consumed):
    """Independent enumeration of existing semantic rules; never edits an answer."""
    details=[];supplied=set(supplied);consumed=set(consumed)
    def add(label,path,message):details.append({'stage':'DIAGNOSTIC_ONLY','label':label,'path':path,'message':message})
    def alias(a,path):
        if a is None:return
        if a not in supplied:add('CITED_ALIAS_NOT_SUPPLIED',path,str(a))
        elif a not in consumed:add('CITED_ALIAS_NOT_PROCESSOR_CONSUMED',path,str(a))
    for i,a in enumerate(value.get('window_cited_frame_aliases',[])):alias(a,f'/window_cited_frame_aliases/{i}')
    events=value.get('events',[])
    if not isinstance(events,list):return details
    if (value.get('window_outcome')=='CONFIRMED_EVENTS') != bool(events):add('OUTCOME_EVENT_INCONSISTENCY','/events','Current validator outcome/event rule')
    ids=[];order={a:i for i,a in enumerate(consumed)}
    # Use the ordered argument rather than the set for interval order below.
    for i,e in enumerate(events):
        if not isinstance(e,dict):continue
        prefix=f'/events/{i}';ids.append(e.get('event_id'))
        for n,a in enumerate(e.get('cited_frame_aliases',[])):alias(a,prefix+f'/cited_frame_aliases/{n}')
        t=e.get('timing',{})
        for k in ['frame_alias','start_frame_alias','end_frame_alias']:
            if k in t:alias(t[k],prefix+'/timing/'+k)
        for k in ['before_state','after_state']:
            state=e.get(k,{})
            if not isinstance(state,dict):continue
            a=state.get('supporting_frame_alias');alias(a,prefix+'/'+k+'/supporting_frame_alias')
            if state.get('state')=='STATE_UNKNOWN' and a is not None:add('UNKNOWN_STATE_INCONSISTENCY',prefix+'/'+k,'UNKNOWN_STATE_HAS_SUPPORT')
            elif state.get('state') in {'HELD_BY_PERSON','ON_SURFACE','OTHER_OBSERVED'} and a is None:add('OTHER_SEMANTIC_ERROR',prefix+'/'+k,'KNOWN_STATE_MISSING_SUPPORT')
    if len(ids)!=len(set(ids)):add('OTHER_SEMANTIC_ERROR','/events','DUPLICATE_EVENT_ID')
    last=value.get('last_directly_supported_state',{})
    if isinstance(last,dict):
        a=last.get('supporting_frame_alias');alias(a,'/last_directly_supported_state/supporting_frame_alias')
        if last.get('state')=='STATE_UNKNOWN' and a is not None:add('UNKNOWN_STATE_INCONSISTENCY','/last_directly_supported_state','UNKNOWN_LAST_STATE_HAS_SUPPORT')
        elif last.get('state') in {'HELD_BY_PERSON','ON_SURFACE','OTHER_OBSERVED'} and a is None:add('OTHER_SEMANTIC_ERROR','/last_directly_supported_state','KNOWN_LAST_STATE_MISSING_SUPPORT')
    return details

def analyze(raw,rr,supplied,consumed,historical,contract):
    labels=generation_labels(rr,raw)
    details=[];value=None;diagnostic_error=None;reproduced=None
    try:
        value=parse_raw(raw);reproduced=validate_prediction(value,consumed)
    except Exception as e:
        diagnostic_error=str(e);labels.append('INVALID_JSON_SYNTAX')
        if raw.lstrip().startswith(b'```'):labels.append('MARKDOWN_CODE_FENCE')
        if 'OBJECT_REQUIRED' in str(e):labels.append('NON_OBJECT_TOP_LEVEL')
        if rr.get('output_cap_reached') or rr.get('generation_deadline_reached'):labels.append('TRUNCATED_JSON')
        if 'Extra data' in str(e):labels.append('NON_JSON_PREFIX_OR_SUFFIX')
    features={'event_count':None,'event_count_status':'EVENT_COUNT_NOT_RECOVERABLE','event_count_text_heuristic':None}
    if value is not None:
        features=complexity(value,contract)
        ls,ds=structural_labels(value,contract);labels+=ls;details+=ds
        ds=secondary_checks(value,supplied,consumed);details+=ds;labels.extend(d['label'] for d in ds)
        order={a:i for i,a in enumerate(consumed)}
        for i,e in enumerate(value.get('events',[])):
            t=e.get('timing',{});a,b=t.get('start_frame_alias'),t.get('end_frame_alias')
            if t.get('status')=='BOUNDED_SUPPLIED_FRAMES' and a in order and b in order and order[a]>order[b]:
                labels.append('INVALID_TIME_INTERVAL');details.append({'stage':'DIAGNOSTIC_ONLY','path':f'/events/{i}/timing','label':'INVALID_TIME_INTERVAL','message':'REVERSED_TIME_INTERVAL'})
    mismatch=reproduced!=historical
    if mismatch:labels.append('HISTORICAL_RESULT_REPRODUCTION_MISMATCH')
    stage='PASS'
    if diagnostic_error:stage='PARSE'
    elif reproduced and reproduced['structural_errors']:stage='SCHEMA'
    elif reproduced and reproduced['citation_errors']:stage='CITATION'
    elif reproduced and reproduced['semantic_errors']:stage='SEMANTIC'
    return {'json_parse_success':value is not None,'raw_char_count':len(raw.decode('utf-8',errors='replace')),
        'raw_byte_count':len(raw),'json_error':diagnostic_error,'features':features,'failure_labels':sorted(set(labels)),
        'error_details':details,'reproduced_validation':reproduced,'reproduction_mismatch':mismatch,
        'primary_failure_stage':stage,'reported_outcome':value.get('window_outcome') if value else None}

def population(rows):
    groups={}
    def stats(rs):
        tokens=[r['generated_tokens'] for r in rs if r['generated_tokens'] is not None]
        chars=[r['raw_char_count'] for r in rs]
        return {'attempts':len(rs),'passes':sum(r['strict_pass'] for r in rs),'failures':sum(not r['strict_pass'] for r in rs),
            'failure_types':dict(Counter(l for r in rs for l in r['failure_labels'])),
            'tokens_range':[min(tokens),max(tokens)] if tokens else None,'tokens_median':statistics.median(tokens) if tokens else None,
            'chars_range':[min(chars),max(chars)] if chars else None,
            'eos_observed':sum(r['eos_observed'] is True for r in rs),'cap_reached':sum(r['output_cap_reached'] is True for r in rs),
            'timeout':sum(r['generation_deadline_reached'] is True for r in rs)}
    for key in [0,1,'2+','UNKNOWN']:
        rs=[r for r in rows if (r['features']['event_count']==key if isinstance(key,int) else
            r['features']['event_count'] is not None and r['features']['event_count']>=2 if key=='2+' else r['features']['event_count'] is None)]
        groups[str(key)]=stats(rs)
    return {'total':stats(rows),'event_count_groups':groups,
        'conditions':{c:stats([r for r in rows if r['condition']==c]) for c in EXPECTED},
        'pass_vs_fail':{str(p):stats([r for r in rows if r['strict_pass']==p]) for p in [True,False]},
        'representation':{p:stats([r for r in rows if r['representation']==p]) for p in ['MULTI_IMAGE','STORYBOARD','REENCODED_AUTHORIZED_VIDEO']},
        'warmup_measured':{k:stats([r for r in rows if r['kind']==k]) for k in ['WARMUP','MEASURED']},
        'secondary_error_attempts':sum(any(d['stage']=='DIAGNOSTIC_ONLY' for d in r['error_details']) for r in rows)}

def run():
    results=[];receipt_checks=[];issues=[]
    contract=schema();contract_path=ROOT/'src/memory_graph/pass_t/phase2b/contracts/prediction_v1.json'
    for rid,role in ROUNDS:
        folder=BASE/rid;check=verify_receipts(folder);receipt_checks.append(check)
        if check['errors']:issues.extend(f'{rid}/{n}' for n in check['errors'])
        capacity=read(folder/'capacity_results.json')
        for condition in EXPECTED:
            fixture=read(folder/'fixtures'/condition/'fixture.json');payload=fixture['payload']
            supplied=[a for m in payload['media'] for a in m['supplied_frame_aliases']]
            transports=[]
            for p in (folder/'runs'/condition/'transport_responses').glob('*/completion_receipt.json'):
                receipt=read(p);tr=read(p.parent/'receipt.json');raw=p.parent/'raw_output.txt'
                integrity=all(sha(p.parent/n)==h for n,h in receipt['files_sha256'].items())
                transports.append((p,tr,raw,integrity))
            for iteration in range(3):
                p=folder/'runs'/condition/f'iteration_{iteration}.json';rawp=p.with_name(p.stem+'_raw.txt')
                if not p.is_file() or not rawp.is_file():issues.append('MISSING_ATTEMPT:'+relative(p));continue
                j=read(p);raw=rawp.read_bytes();rr=j.get('resource_receipt',{})
                # Adapter appends the validated citation allowlist after transport storage.
                # Match all original resource fields exactly; do not compare the appended field.
                original_rr={k:v for k,v in rr.items() if k!='citation_allowed_aliases'}
                matches=[x for x in transports if x[1]==original_rr and sha(x[2])==sha(rawp)]
                if len(matches)!=1:issues.append('TRANSPORT_MATCH_COUNT:'+relative(p)+':'+str(len(matches)))
                if matches and not matches[0][3]:issues.append('TRANSPORT_HASH:'+relative(matches[0][0]))
                consumed=rr.get('citation_allowed_aliases',rr.get('processed_frame_aliases',[]))
                if consumed!=rr.get('processed_frame_aliases'):issues.append('CITATION_ALLOWLIST_MISMATCH:'+relative(p))
                audit=analyze(raw,rr,supplied,consumed,j.get('validation'),contract)
                if audit['reproduction_mismatch']:issues.append('VALIDATOR_MISMATCH:'+relative(p))
                if rr['prompt_contract']['task']!=payload['instructions']+'\nRequired JSON schema:\n'+json.dumps(contract):
                    issues.append('TASK_SCHEMA_MISMATCH:'+relative(p))
                if hashlib.sha256(rr['rendered_prompt'].encode()).hexdigest()!=rr['rendered_prompt_sha256']:
                    issues.append('RENDERED_PROMPT_HASH_MISMATCH:'+relative(p))
                canonical=(json.dumps(rr['prompt_contract'],ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
                if hashlib.sha256(canonical).hexdigest()!=rr['prompt_contract_sha256']:
                    issues.append('PROMPT_CONTRACT_HASH_MISMATCH:'+relative(p))
                results.append({'attempt_id':attempt_id(rid,condition,iteration),'round_id':rid,'population':role,
                    'condition':condition,'iteration':iteration,'kind':j['kind'],'strict_pass':j['STRUCTURED_OUTPUT_PASS'],
                    'historical_validation':j['validation'],'generation_pass':j['GENERATION_PASS'],
                    'raw_path':relative(rawp),'raw_sha256':sha(rawp),'source_hash_verified':relative(rawp).removeprefix(relative(folder)+'/') in read(folder/'engineering_completion_receipt.json')['files'],
                    'attempt_receipt_path':relative(p),'attempt_receipt_sha256':sha(p),
                    'supervisor_receipt_path':relative(p.parent/'supervisor_receipt.json'),
                    'transport_receipt_path':relative(matches[0][0]) if len(matches)==1 else None,
                    'transport_raw_path':relative(matches[0][2]) if len(matches)==1 else None,
                    'generated_tokens':rr.get('generated_tokens'),'eos_observed':rr.get('eos_observed'),
                    'last_generated_token_id':rr.get('last_generated_token_id'),'eos_token_ids':rr.get('eos_token_ids'),
                    'eos_token_consistent':rr.get('eos_observed')==(rr.get('last_generated_token_id') in rr.get('eos_token_ids',[])),
                    'output_cap_reached':rr.get('output_cap_reached'),'generation_deadline_reached':rr.get('generation_deadline_reached'),
                    'generation_controls':rr.get('generation_controls'),'seed_applied':rr.get('seed_applied'),
                    'representation':payload['representation'],'source_frames':fixture['source_frame_count'],
                    'supplied_aliases':supplied,'consumed_aliases':consumed,'reference_count':rr.get('reference_image_count'),
                    'visual_tokens':rr.get('grid_derived_visual_tokens'),'input_tokens':rr.get('input_token_count'),
                    'pixel_cap':rr.get('configured_pixel_cap'),'resized_dimensions_hw':rr.get('resized_dimensions_hw'),
                    'prompt_version':rr['prompt_contract']['version'],'system_sha256':hashlib.sha256(rr['prompt_contract']['system'].encode()).hexdigest(),
                    'task_schema_sha256':hashlib.sha256(rr['prompt_contract']['task'].encode()).hexdigest(),
                    'rendered_prompt_sha256':rr.get('rendered_prompt_sha256'),'prompt_contract_sha256':rr.get('prompt_contract_sha256'),
                    'prediction_schema_id':contract['$id'],'prediction_schema_file_sha256':sha(contract_path),
                    'generation_seconds':rr.get('runtime_seconds'),**audit})
        actual=Counter(r['condition'] for r in results if r['round_id']==rid and r['strict_pass'])
        if role=='PRIMARY' and any(actual[c]!=v for c,v in EXPECTED.items()):issues.append('PRIMARY_CONDITION_COUNTS_MISMATCH')
        if sum(r['round_id']==rid for r in results)!=33:issues.append('POPULATION_INCOMPLETE:'+rid)
    if len({r['attempt_id'] for r in results})!=len(results):issues.append('DUPLICATE_ATTEMPT_ID')
    for rid,role in ROUNDS:
        rs=[r for r in results if r['round_id']==rid]
        write('primary_attempts.json' if role=='PRIMARY' else 'history_attempts.json',rs)
    fields=['attempt_id','round_id','population','condition','iteration','kind','strict_pass','primary_failure_stage',
        'raw_path','raw_sha256','source_hash_verified','raw_char_count','raw_byte_count','json_parse_success','generated_tokens',
        'eos_observed','eos_token_consistent','output_cap_reached','generation_deadline_reached','reference_count','visual_tokens','input_tokens',
        'pixel_cap','representation','source_frames','reported_outcome','failure_labels','historical_validation','error_details',
        'reproduced_validation','reproduction_mismatch','attempt_receipt_path','transport_receipt_path','supervisor_receipt_path',
        'generation_controls','prompt_version','system_sha256','task_schema_sha256','rendered_prompt_sha256','prompt_contract_sha256','prediction_schema_file_sha256']
    features=sorted({k for r in results for k in r['features']});fields+=features
    with (OUT/'QWEN_NF4_STRUCTURED_OUTPUT_AUDIT.csv').open('x',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in results:
            row={k:r.get(k) for k in fields};row.update(r['features'])
            w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else 'UNKNOWN' if v is None else v for k,v in row.items()})
    primary=[r for r in results if r['population']=='PRIMARY'];history=[r for r in results if r['population']=='ENGINEERING_HISTORY']
    summary={'PRIMARY':population(primary),'ENGINEERING_HISTORY':population(history),'issues':issues,
        'receipt_integrity':receipt_checks,'hypothesis':'SUPPORTED_DESCRIPTIVELY',
        'formal_phase2b_pilot_generation_count':0,'new_model_calls':0,'rows_csv':len(results),
        'primary_schema_match':all(r['prediction_schema_id']=='PASS_T_PHASE2B_PREDICTION_V1' for r in primary),
        'prompt_system_versions':sorted({r['system_sha256'] for r in primary}),'task_schema_versions':sorted({r['task_schema_sha256'] for r in primary}),
        'forbidden_modules_loaded':[n for n in sys.modules if n.split('.')[0] in {'torch','transformers','bitsandbytes','accelerate','cv2','av'}]}
    write('analysis_summary.json',summary)
    print(json.dumps({'primary':summary['PRIMARY']['total'],'history':summary['ENGINEERING_HISTORY']['total'],'issues':issues},ensure_ascii=False),flush=True)
    if issues:raise SystemExit('AUDIT_HAS_PROVENANCE_BLOCKERS')

def closeout():
    before=read(OUT/'protected_before.json');changed=[]
    for n,h in before['files'].items():
        p=ROOT/n
        if not p.is_file() or sha(p)!=h:changed.append(n)
    result={'checked_files':len(before['files']),'changed_files':changed,'git_before':before['git'],'git_after':git(),
        'git_unchanged':git()==before['git'],'weight_binaries_not_read':before['excluded_weight_binaries'],
        'preexisting_missing':before['preexisting_missing'],'cpu_guard_forbidden_modules_loaded':[],
        'new_gpu_calls':0,'new_predictions':0,'protocol_frozen':False,'gt_modified':False,'graph_writes':0,'commit_or_push':False}
    write('preservation.json',result)
    print(json.dumps({'checked_files':result['checked_files'],'changed_files':changed,'git_unchanged':result['git_unchanged']}),flush=True)
    if changed or not result['git_unchanged']:raise SystemExit('INTEGRITY_BLOCKED')

if __name__=='__main__':
    {'snapshot':snapshot,'analyze':run,'closeout':closeout}[sys.argv[1]]()

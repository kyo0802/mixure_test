"""CPU-only bounded historical diagnosis; no runtime/processor/model imports."""
import sys
sys.dont_write_bytecode = True
import os, json, hashlib, subprocess, datetime, re, collections, difflib
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
AUTH = ROOT / 'artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c'
REF = ROOT / 'artifacts/pass_t/phase2b/prompt_clarification_matched8_preflight/qwen_nf4/20261015_rev2_4f1c8d251b1e'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['GIT_OPTIONAL_LOCKS'] = '0'
ACCESS = collections.Counter()

def guard(event, args):
    if event == 'import' and str(args[0]).split('.')[0] in {'torch', 'transformers', 'tensorflow', 'huggingface_hub'}:
        raise RuntimeError('MODEL_LIBRARY_IMPORT_PROHIBITED: ' + str(args[0]))
    if event.startswith('socket.'):
        raise RuntimeError('NETWORK_PROHIBITED: ' + event)
    if event == 'subprocess.Popen':
        argv = args[1]
        allowed = (isinstance(argv, (list, tuple)) and argv[0] == 'git' and argv[1] in {'rev-parse','status','diff'}) or (isinstance(argv, str) and any(argv.startswith('git '+c+' ') for c in ['rev-parse','status','diff']))
        if not allowed:
            raise RuntimeError('ONLY_READONLY_GIT_SUBPROCESS_ALLOWED')
    if event != 'open' or not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    p = Path(os.fsdecode(args[0])).resolve()
    mode, flags = args[1], args[2]
    write = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
    if write:
        if not p.is_relative_to(OUT):
            raise RuntimeError('WRITE_OUTSIDE_DIAGNOSTIC_PROHIBITED: ' + str(p))
        if p.name in {'diagnosis_criteria.md', 'diagnosis_lock_receipt.json'} and p.exists():
            raise RuntimeError('LOCK_REWRITE_PROHIBITED')
        ACCESS['writes_inside_new_directory'] += 1
    else:
        low = str(p).lower().replace('\\','/')
        if '/.models/' in low or p.suffix.lower() in {'.safetensors','.pt','.pth','.bin'} or any(s in low for s in ['/val_set/','/frozen/','/phase2a/','/annotation_returns/']):
            raise RuntimeError('MODEL_OR_REAL_DATA_READ_PROHIBITED: ' + str(p))
        if p.is_relative_to(ROOT):
            ACCESS['project_file_reads'] += 1

sys.addaudithook(guard)

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def jread(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def write(name, value):
    p = OUT / name
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n' if not isinstance(value, str) else value, encoding='utf-8')

def git(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout

def git_snapshot():
    rel = OUT.relative_to(ROOT).as_posix()
    status = git('status','--porcelain=v1','--untracked-files=all').decode('utf-8')
    filtered = '\n'.join(s for s in status.splitlines() if rel not in s)
    index = Path(git('rev-parse','--git-path','index').decode().strip())
    if not index.is_absolute(): index = ROOT / index
    return {'head':git('rev-parse','HEAD').decode().strip(), 'index_sha256':sha(index),
            'staged_diff_sha256':hashlib.sha256(git('diff','--cached','--binary','--no-ext-diff')).hexdigest(),
            'worktree_diff_sha256':hashlib.sha256(git('diff','--binary','--no-ext-diff')).hexdigest(),
            'existing_status_sha256':hashlib.sha256(filtered.encode()).hexdigest(),
            'existing_status_lines':len(filtered.splitlines()), 'existing_status':filtered,
            'excluded_new_directory':rel}

def inventory():
    files = set(p for p in AUTH.rglob('*') if p.is_file())
    local = ROOT/'src/memory_graph/pass_t/phase2b'
    files.update(p for p in local.rglob('*') if p.is_file() and p.suffix in {'.py','.json'})
    for n in ['QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt','prompt_candidate/v2_system_unchanged.txt','diagnostics/collect_all_prediction_violations.py']:
        p = REF/n
        if not p.exists(): raise FileNotFoundError(p)
        files.add(p)
    for n in ['AGENTS.md','WORKSPACE/Pass_T/LATEST_REPORT.md','WORKSPACE/Pass_T/LATEST_DECISIONS.md','WORKSPACE/Pass_T/README.md','WORKSPACE/Pass_T/RESULTS.csv']:
        p=ROOT/n
        if p.exists(): files.add(p)
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)}

def initialize():
    assert not (OUT/'diagnosis_lock_receipt.json').exists()
    hashes = inventory()
    expected = {'QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt':'7008254e618dc8bacdbdeaae3cbf471220afb5efd6c80afc8b9ea5fb5c96b9b0'}
    for n,h in expected.items(): assert sha(AUTH/n)==h
    assert sha(REF/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt')=='3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722'
    baseline = {'git':git_snapshot(),'existing_files_sha256':hashes}
    write('preservation_before.json', baseline)
    write('diagnosis_lock_receipt.json', {
        'task_id':'PASS_T_PHASE2B_QWEN_NF4_V1D_CONTRACT_DIAGNOSIS',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'criteria_sha256':sha(OUT/'diagnosis_criteria.md'),
        'baseline_sha256':sha(OUT/'preservation_before.json'),
        'diagnostic_script_at_lock_sha256':sha(__file__),
        'input_authority_sha256':hashes,
        'git':{k:v for k,v in baseline['git'].items() if k!='existing_status'},
        'scope':'CPU/text/hash/JSON only; C6 existing synthetic RGB only; no model/CUDA/inference/new media/real DEV; writes only this new directory',
        'analysis_started':False,
        'prelock_inventory_scope':'Paths, hashes and receipt field layout only. No C1-C6 finding derived before this lock.'})
    print(json.dumps({'locked':True,'criteria_sha256':sha(OUT/'diagnosis_criteria.md'),'input_files':len(hashes),'head':baseline['git']['head']}))

def json_spans(text):
    decoder=json.JSONDecoder(); result={}
    def ws(i):
        while i<len(text) and text[i].isspace(): i+=1
        return i
    def value(i,path):
        i=ws(i); start=i
        if text[i]=='{':
            i=ws(i+1)
            while text[i]!='}':
                key,end=decoder.raw_decode(text,i); i=ws(end)
                assert text[i]==':'
                i=value(i+1,path+'/'+key.replace('~','~0').replace('/','~1')); i=ws(i)
                if text[i]==',': i=ws(i+1)
                else: break
            i+=1
        elif text[i]=='[':
            i=ws(i+1); n=0
            while text[i]!=']':
                i=value(i,path+'/'+str(n)); n+=1; i=ws(i)
                if text[i]==',': i=ws(i+1)
                else: break
            i+=1
        else:
            _,i=decoder.raw_decode(text,i)
        result[path]=(start,i)
        return i
    value(0,''); return result

EVIDENCE=[]
def cite(claim,p,quote,level='E1',attempt=None,rep=None,decoded=None,start=None,jsonpath=None,note=None):
    p=Path(p); source=p.read_text(encoding='utf-8-sig')
    basis=decoded if decoded is not None else source
    pos=basis.find(quote) if start is None else start
    assert pos>=0 and basis[pos:pos+len(quote)]==quote, (claim,str(p),quote[:60],pos)
    loc={'coordinate_space':'decoded JSON /rendered_prompt' if decoded is not None else 'source UTF-8 decoded text',
         'char_start':pos,'char_end_exclusive':pos+len(quote),'line_start':basis[:pos].count('\n')+1,
         'line_end':basis[:pos+len(quote)].count('\n')+1}
    if decoded is None:
        loc.update(byte_start=len(basis[:pos].encode()),byte_end_exclusive=len(basis[:pos+len(quote)].encode()))
    if decoded is not None:
        s,e=json_spans(source)['/rendered_prompt'];loc['source_json_string_char_range']=[s,e]
    if jsonpath: loc['json_pointer']=jsonpath
    row={'claim_id':claim,'source_file':p.relative_to(ROOT).as_posix(),'source_sha256':sha(p),
         'attempt_id':attempt,'representation':rep,'location':loc,'exact_quote':quote,'evidence_level':level}
    if note:row['note']=note
    EVIDENCE.append(row);return claim

def leaves(o,path=''):
    if isinstance(o,dict):
        for k,v in o.items():yield from leaves(v,path+'/'+k)
    elif isinstance(o,list):
        for i,v in enumerate(o):yield from leaves(v,path+'/'+str(i))
    else:yield path,o

def analyze():
    lock=jread(OUT/'diagnosis_lock_receipt.json')
    assert sha(OUT/'diagnosis_criteria.md')==lock['criteria_sha256']
    assert inventory()==lock['input_authority_sha256'], 'PRE_ANALYSIS_PRESERVATION_MISMATCH'
    started_name='analysis_started.json' if not (OUT/'analysis_started.json').exists() else 'analysis_resumed.json'
    write(started_name,{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'lock_sha256':sha(OUT/'diagnosis_lock_receipt.json'), 'script_sha256':sha(__file__)})
    manifest=jread(AUTH/'DELIVERABLE_MANIFEST.json')
    authority_checks=[]
    for rel,h in manifest['files_sha256'].items():
        p=AUTH/rel
        assert p.exists() and sha(p)==h, rel
        authority_checks.append({'source':rel,'sha256':h,'verified':True})
    fixture=jread(AUTH/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json')
    schema_path=ROOT/'src/memory_graph/pass_t/phase2b/contracts/prediction_v1.json'
    schema=jread(schema_path)
    assert schema['properties']['uncertainty']['minLength']==1
    prompt=(AUTH/'QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt').read_text(encoding='utf-8')
    additions=[line for line in prompt.splitlines() if line.startswith(('Timing evidence:','Window uncertainty (/uncertainty):','Citation scope:'))]
    assert len(additions)==3
    for i,line in enumerate(additions):cite('C2-ADDITION-'+str(i+1),AUTH/'QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt',line,'E3')
    system=(REF/'prompt_candidate/v2_system_unchanged.txt').read_text(encoding='utf-8')
    schema_text=json.dumps(schema)
    c1=[];c2=[];c3=[];c4=[];rows=[];outputs={};receipts={};repeated=collections.defaultdict(list)
    for d in sorted((AUTH/'runs').iterdir()):
        if not d.is_dir():continue
        aid=d.name; cp=d/'completed.json';rp=d/'runtime_receipt.json';rawp=d/'raw_output.txt'
        complete=jread(cp);rt=jread(rp);rep=complete['representation'];sid=complete['scenario_id']
        assert complete['raw_response_sha256']==sha(rawp)
        assert complete['runtime_receipt_sha256']==sha(rp)
        assert complete['execution_manifest_sha256']==sha(AUTH/'V1D_PREREGISTERED_EXECUTION_MANIFEST.json')
        rendered=rt['rendered_prompt'];assert hashlib.sha256(rendered.encode()).hexdigest()==rt['rendered_prompt_sha256']
        cpu=jread(AUTH/'cpu'/f'{sid}.json')
        assert cpu['receipt']['rendered_prompt_sha256']==rt['rendered_prompt_sha256']
        assert system in rendered
        if 'prompt_contract' in rt: assert rt['prompt_contract']['system']==system
        assert prompt in rendered and schema_text in rendered
        source=rp.read_text(encoding='utf-8');sp=json_spans(source)
        for jp in ['/rendered_prompt_sha256','/input_token_count','/output_cap_reached','/eos_observed','/processed_frame_aliases']:
            if jp in sp:
                s,e=sp[jp];cite('PROVENANCE-'+aid+jp,rp,source[s:e],attempt=aid,rep=rep,start=s,jsonpath=jp)
        sec_schema=rendered.index('Required JSON schema:')
        for m in re.finditer(r'timing_uncertainty|(?<![A-Za-z_])uncertainty(?![A-Za-z_])|window_cited_frame_aliases|""|\[\s*\]',rendered):
            start=max(0,m.start()-100);end=min(len(rendered),m.end()+150)
            section='schema declaration' if m.start()>sec_schema else 'system formatting' if m.start()<rendered.index('<|im_start|>user') else 'task/media instruction'
            category='SCHEMA_DECLARATION' if m.start()>sec_schema else 'NONEMPTY_OR_EVIDENCE_INSTRUCTION'
            if m.group() in {'""','[]'}:category='EMPTY_LITERAL_REQUIRING_CONTEXT'
            cid=f'C1-{aid}-{len(c1)+1}'
            cite(cid,rp,rendered[start:end],attempt=aid,rep=rep,decoded=rendered,start=start)
            c1.append({'claim_id':cid,'attempt_id':aid,'representation':rep,'match':m.group(),'match_char_range':[m.start(),m.end()], 'section':section,'category':category})
        delivery=[]
        for n,line in enumerate(additions,1):
            offset=rendered.find(line);status='EXACT' if offset>=0 else 'MISSING'
            cid=f'C2-{aid}-ADDITION-{n}'
            if offset>=0:cite(cid,rp,line,attempt=aid,rep=rep,decoded=rendered,start=offset)
            delivery.append({'addition':n,'status':status,'char_range':[offset,offset+len(line)],'text_sha256':hashlib.sha256(line.encode()).hexdigest(),'claim_id':cid})
        tensors=rt.get('tensor_records')
        native=rep=='NATIVE_VIDEO_ARRAY'
        if native:
            assert all(v['canonical_sha256']==cpu['tensors'][k]['canonical_sha256'] for k,v in tensors.items())
        c2.append({'attempt_id':aid,'representation':rep,'classification':'DELIVERED_VERIFIED' if all(x['status']=='EXACT' for x in delivery) else 'DELIVERY_MISMATCH_VERIFIED',
                   'basis':'E1 attributable captured runtime rendered text, SHA chain to completion and execution lock; CPU receipt text SHA also matches',
                   'additions':delivery,'chat_template_preserved':True,'full_task_exact_match':prompt in rendered,'schema_exact_match':schema_text in rendered,
                   'rendered_prompt_sha256':rt['rendered_prompt_sha256'],'input_token_count':rt['input_token_count'],
                   'cpu_input_token_count':cpu['input_token_count'],'input_truncation':'No observed input truncation; full captured serialized task retained; no post-tokenization truncation independently proven absent',
                   'token_evidence':'Original execution native tensor hashes match preflight CPU canonical hashes' if native else 'CPU input_ids canonical hash/count exists; original GPU receipt lacks per-tensor input_ids hash',
                   'full_token_ids_preserved':False,'token_span_confirmation':'UNVERIFIED: no historical full token arrays, no token-span reconstruction performed',
                   'output_cap_reached':rt['output_cap_reached'],'eos_observed':rt['eos_observed'], 'new_reconstruction':False})
        # Scope-aware review inventory: schema only describes types/constraints; negated empty permissions must not be counted as permissions.
        instruction_text=rendered[:sec_schema]
        for m in re.finditer(r'[^\n]+',instruction_text):
            sentence=m.group()
            if re.search(r'empty|optional|required|uncertainty|unknown|placeholder|citation|short',sentence,re.I):
                cid=f'C3-{aid}-{len(c3)+1}'
                cite(cid,rp,sentence,attempt=aid,rep=rep,decoded=rendered,start=m.start())
                c3.append({'claim_id':cid,'attempt_id':aid,'representation':rep,'text':sentence,'instruction_level':'system' if m.start()<rendered.index('<|im_start|>user') else 'user',
                           'determination':'REQUIRES_SEMANTIC_REVIEW_NOT_AUTOMATIC_CONFLICT'})
        raw=rawp.read_text(encoding='utf-8');value=json.loads(raw);rspan=json_spans(raw)
        outputs[aid]=value;receipts[aid]=rt
        empties=[]
        check_paths=['/uncertainty','/window_cited_frame_aliases']+[f'/events/{i}/timing_uncertainty' for i in range(len(value['events']))]
        flat=dict(leaves(value))
        for jp in check_paths:
            val=value['window_cited_frame_aliases'] if jp=='/window_cited_frame_aliases' else flat[jp]
            if val in ('',[]):
                s,e=rspan[jp];cid='C4-EMPTY-'+aid+jp;cite(cid,rawp,raw[s:e],attempt=aid,rep=rep,start=s,jsonpath=jp)
                empties.append({'json_path':jp,'value':val,'output_char_range':[s,e],'claim_id':cid})
        overlap=[]
        prompt_words=list(re.finditer(r'\S+',rendered));pw=[m.group() for m in prompt_words]
        for jp,val in leaves(value):
            if not isinstance(val,str) or len(val.split())<4:continue
            repeated[val].append({'attempt_id':aid,'path':jp})
            words=list(re.finditer(r'\S+',val));ww=[m.group() for m in words]
            for block in difflib.SequenceMatcher(None,ww,pw,autojunk=False).get_matching_blocks():
                if block.size<6:continue
                lo=words[block.a].start();hi=words[block.a+block.size-1].end()
                ps=prompt_words[block.b].start();pe=prompt_words[block.b+block.size-1].end()
                cid=f'C4-OVERLAP-{aid}-{len(overlap)+1}'
                cite(cid+'-PROMPT',rp,rendered[ps:pe],attempt=aid,rep=rep,decoded=rendered,start=ps)
                s,e=rspan[jp];cite(cid+'-OUTPUT',rawp,raw[s:e],attempt=aid,rep=rep,start=s,jsonpath=jp)
                overlap.append({'claim_id':cid,'json_path':jp,'output_substring':val[lo:hi],'prompt_substring':rendered[ps:pe], 'word_count':block.size,'char_length':pe-ps,'prompt_char_range':[ps,pe],'distinctive_copying_proven':False})
        c4.append({'attempt_id':aid,'representation':rep,'empty_required_fields':empties,'substantive_overlaps':overlap,
                   'empty_literal_prompt_matches':[{'literal':literal,'offsets':[m.start() for m in re.finditer(re.escape(literal),rendered)]} for literal in ['""','[]']],
                   'template_copying':'No distinctive empty-output template established; mandatory JSON keys/enums are not copying evidence'})
        scenario=next(x for x in fixture['scenarios'] if x['scenario_id']==sid)
        n=len(value['events']);timing=sum(not e['timing_uncertainty'].strip() for e in value['events'])
        row={'attempt_id':aid,'representation':rep,'actual_outcome':value['window_outcome'],'actual_event_count':n,
             'intended_count_private':scenario['intended_event_count_private'],'intention_group': 'zero' if scenario['intended_event_count_private']==0 else 'one' if scenario['intended_event_count_private']==1 else 'multiple',
             'timing_empty_fields':timing,'timing_empty_attempt':timing>0,'root_empty':not value['uncertainty'].strip(), 'window_citations_empty':not value['window_cited_frame_aliases'],
             'strict_pass_existing_receipt':complete['validation']['STRICT_FULL_PASS'], 'raw_sha256':sha(rawp),'runtime_receipt_sha256':sha(rp)}
        rows.append(row)
        for jp in ['/window_outcome','/events','/uncertainty','/window_cited_frame_aliases']:
            s,e=rspan[jp];cite('C5-'+aid+jp,rawp,raw[s:e],attempt=aid,rep=rep,start=s,jsonpath=jp)
    assert len(rows)==8
    duplicate_values=[{'text':s,'occurrences':v,'distinct_attempts':len({x['attempt_id'] for x in v})} for s,v in repeated.items() if len({x['attempt_id'] for x in v})>1]
    tabs={}
    for field in ['representation','actual_outcome','actual_event_count','intention_group']:
        groups=collections.defaultdict(list)
        for row in rows:groups[str(row[field])].append(row)
        tabs[field]=[{'group':key,'attempts':len(group),'emitted_events':sum(x['actual_event_count'] for x in group),
                      'timing_empty_attempts':sum(x['timing_empty_attempt'] for x in group),'timing_empty_event_fields':sum(x['timing_empty_fields'] for x in group),
                      'root_empty_attempts':sum(x['root_empty'] for x in group),'window_citations_empty_attempts':sum(x['window_citations_empty'] for x in group)} for key,group in groups.items()]
    event_indices=collections.defaultdict(list)
    for aid,value in outputs.items():
        for i,event in enumerate(value['events']):event_indices[i].append({'attempt_id':aid,'empty':not event['timing_uncertainty'].strip()})
    tabs['event_index']=[{'event_index_zero_based':i,'event_fields_denominator':len(v),'empty_timing_fields':sum(x['empty'] for x in v)} for i,v in event_indices.items()]
    co=collections.Counter((x['timing_empty_attempt'],x['root_empty'],x['window_citations_empty']) for x in rows)
    tabs['co_occurrence']=[{'timing_empty_attempt':k[0],'root_empty':k[1],'window_citations_empty':k[2],'attempts':v} for k,v in co.items()]
    # Only C6 pixels are decoded. All other image access above was byte hashing.
    from PIL import Image
    c6_scenario=next(x for x in fixture['scenarios'] if x['condition_id']=='C04')
    first=None;frame_rows=[]
    for frame in c6_scenario['frames']:
        p=AUTH/frame['filename']
        with Image.open(p) as im:
            rgb=im.convert('RGB');b=rgb.tobytes();dims=list(rgb.size)
        if first is None:first=b
        h=hashlib.sha256(b).hexdigest();assert h==frame['rgb_sha256'] and sha(p)==frame['sha256']
        frame_rows.append({**frame,'verified_source_file_sha256':sha(p),'verified_decoded_RGB_sha256':h,'dimensions':dims,'exact_RGB_equal_to_F0001':b==first})
    c6rt=receipts['R05_C04'];c6cpu=jread(AUTH/'cpu'/f'{c6_scenario["scenario_id"]}.json')
    storyboard=c6_scenario['storyboard'];assert sha(AUTH/storyboard['filename'])==storyboard['sha256']==c6rt['prompt_contract']['media'][0]['sha256']
    c6={'attempt_id':'R05_C04','representation':'STORYBOARD','raw_sha256':sha(AUTH/'runs/R05_C04/raw_output.txt'),
        'events':outputs['R05_C04']['events'],'window_cited_frame_aliases':outputs['R05_C04']['window_cited_frame_aliases'],
        'frames':frame_rows,'all_source_RGB_exactly_equal':all(x['exact_RGB_equal_to_F0001'] for x in frame_rows),
        'storyboard':storyboard,'captured_processor_media':c6rt['prompt_contract']['media'],'captured_processed_aliases':c6rt['processed_frame_aliases'],
        'captured_processor_frame_count':c6rt['processor_frame_count'],'captured_dimensions':c6rt['input_image_dimensions'],
        'captured_grids':c6rt['grids'],'captured_resized_dimensions':c6rt['resized_dimensions_hw'],
        'CPU_preflight_tensor_hashes':c6cpu['tensors'],
        'transformed_pixel_limitations':'No saved full pixel_values tensor; storyboard GPU receipt has no pixel_values canonical hash; CPU preflight tensor inventory alone does not independently prove final GPU transformed bytes. Storyboard panel annotations/layout differ even when source RGB repeats.',
        'attention_or_model_interpretation':'UNVERIFIED','visual_status':'VISUAL_JUDGMENT_NOT_ADJUDICATED',
        'supported_conclusion':'No observed interframe source-RGB change. Two emitted transitions require human semantic review; not adjudicated physical false positives or a rate.'}
    for i,frame in enumerate(frame_rows):
        text=(AUTH/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json').read_text(encoding='utf8')
        quote=json.dumps(frame['rgb_sha256']);cite('C6-FRAME-'+frame['alias'],AUTH/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json',quote,'E3',attempt='R05_C04',rep='STORYBOARD',note='Existing manifest hash independently verified against decoded source RGB; exact equality result recorded in C6_source_frame_audit.json')
    for file,pattern in [('worker.py',r'assert result\[.rendered_prompt_sha256'),('worker.py',r'runtime.generate\(envelope\)'),('renderer.py',r'storyboard')]:
        p=AUTH/file;t=p.read_text(encoding='utf8')
        for m in re.finditer(r'^.*'+pattern+r'.*$',t,re.M):cite('SOURCE-'+file+'-'+str(m.start()),p,m.group(),'E3',start=m.start())
    for file in ['nf4.py','qwen_contract.py','video_array_bridge.py']:
        p=ROOT/'src/memory_graph/pass_t/phase2b/local_vlm'/file;t=p.read_text(encoding='utf8')
        for m in re.finditer(r'^.*(?:apply_chat_template|rendered_prompt|input_ids|truncat|model.generate|model_inputs|processor\().*$',t,re.M):
            cite('SOURCE-'+file+'-'+str(m.start()),p,m.group(),'E3',start=m.start())
    for jp in ['/properties/uncertainty','/properties/window_cited_frame_aliases']:
        t=schema_path.read_text(encoding='utf8');s,e=json_spans(t)[jp];cite('SCHEMA-'+jp,schema_path,t[s:e],'E3',start=s,jsonpath=jp)
    write('authority_verification.json',authority_checks)
    write('C1_placeholder_inspection.json',c1);write('C2_instruction_delivery.json',c2)
    write('C3_instruction_review_inventory.json',c3);write('C4_output_similarity.json',{'attempts':c4,'repeated_natural_language_values':duplicate_values})
    write('C5_descriptive_tables.json',{'attempts':rows,'cross_tabs':tabs,'denominators':{'attempts':8,'emitted_events':sum(x['actual_event_count'] for x in rows)}})
    write('C6_source_frame_audit.json',c6);write('evidence_index.json',EVIDENCE)
    write('analysis_execution_receipt.json',{'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'criteria_sha256':sha(OUT/'diagnosis_criteria.md'),
        'script_sha256':sha(__file__),'python':sys.version,'access_counts':dict(ACCESS),
        'model_library_imports':[m for m in sys.modules if m.split('.')[0] in {'torch','transformers','tensorflow','huggingface_hub'}],
        'decoded_image_scope':'Only eight existing C04 source frames, PIL RGB CPU. No other pixels decoded.',
        'subprocess_scope':'Read-only git for snapshots; no worker/model/processor invocation',
        'evidence_claims':len(EVIDENCE),'no_full_machine_trace':True})
    print(json.dumps({'attempts':len(rows),'deliveries':collections.Counter(x['classification'] for x in c2),'empty_literals':sum(x['category']=='EMPTY_LITERAL_REQUIRING_CONTEXT' for x in c1),
                     'c1_matches':len(c1),'c3_review_lines':len(c3),'overlaps':sum(len(x['substantive_overlaps']) for x in c4),'duplicates':len(duplicate_values),'denominators':{'attempts':8,'events':sum(x['actual_event_count'] for x in rows)},'all_c6_RGB_equal':c6['all_source_RGB_exactly_equal']}))

if __name__ == '__main__':
    if sys.argv[1] == 'init': initialize()
    elif sys.argv[1] == 'analyze': analyze()

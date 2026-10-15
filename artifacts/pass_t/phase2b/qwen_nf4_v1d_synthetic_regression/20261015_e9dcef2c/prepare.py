"""Prospective steps; no prompt is authored until fixture-lock completion."""
import support as s
import sys,hashlib,ast,traceback

def audit():
    from memory_graph.pass_t.phase2b.predictions import schema,parse_raw,validate_prediction
    expected={s.PRIOR/'DELIVERABLE_MANIFEST.json':'a581ff7b6c27f404508fdd44b651b62ab1456e0bace7f25e23b5df4d021a8226',
      s.REF/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt':'3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722',
      s.ROOT/'src/memory_graph/pass_t/phase2b/predictions.py':'c4b077374d50fc478c29d0009180d488c60a463fa8bffa183a179c5f736f1d37',
      s.ROOT/'src/memory_graph/pass_t/phase2b/contracts/prediction_v1.json':'f8b0dfb6c62301baabff5e1adfddf14dc6be9381aa84c884fc70f5318abcedc3',
      s.REF/'prompt_candidate/v2_system_unchanged.txt':'9b76b7e320dfb677a1cb8566c16dff15785759bc4915375123bc12dd118fd08e',
      s.ROOT/'src/memory_graph/pass_t/phase2b/local_vlm/nf4.py':'fc15d9012a3a992e4dcb9e66a3b458b242c319b1efe5f4d30dae19b81364547b',
      s.ROOT/'src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py':'318febec583338626203d15f64fac55190e4a8133e0120b5dbea23d6d148db6f'}
    for p,h in expected.items():
        if s.sha(p)!=h:raise RuntimeError('SOURCE_AUTHORITY_MISMATCH:'+str(p))
    protected={str(p.relative_to(s.ROOT)):h for p,h in expected.items()}
    for name,h in s.read(s.PRIOR/'DELIVERABLE_MANIFEST.json')['files_sha256'].items():
        p=s.PRIOR/name
        if p.suffix.lower() in {'.png','.jpg','.jpeg','.mp4','.avi'}:continue
        if s.sha(p)!=h:raise RuntimeError('PRIOR_DELIVERABLE_CHANGED:'+name)
        protected[p.relative_to(s.ROOT).as_posix()]=h
    for p in (s.ROOT/'src/memory_graph/pass_t/phase2b').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:protected[p.relative_to(s.ROOT).as_posix()]=s.sha(p)
    for n,h in s.read(s.REF/'processor_source_inventory.json').items():
        assert s.sha(s.ROOT/n)==h;protected[n]=h
    assets=s.read(s.PRIOR/'model_assets.json')
    for n,h in assets['files_sha256'].items():
        if s.sha(s.MODEL/n)!=h:raise RuntimeError('MODEL_ASSET_MISMATCH:'+n)
    s.save('model_assets.json',assets)
    sch=schema();props=sch['properties'];historical=[];global_failures=[]
    for i in range(1,13):
        p=s.PRIOR/f'runs/B_{i:02d}/raw_output.txt';raw=p.read_bytes();value=parse_raw(raw)
        receipt=s.read(s.PRIOR/f'runs/B_{i:02d}/completed.json')
        assert s.sha(p)==receipt['raw_output_sha256']
        strict=validate_prediction(value,[f'F{i:04d}' for i in range(1,9)])
        assert strict==receipt['validation']['strict_result']
        if any(x.startswith('/uncertainty:') for x in strict['structural_errors']):
            global_failures.append({'attempt':f'B_{i:02d}','json_path':'/uncertainty','raw_value':value['uncertainty'],
              'raw_sha256':s.sha(p),'schema_errors':[x for x in strict['structural_errors'] if x.startswith('/uncertainty:')]})
        historical.append({'attempt':f'B_{i:02d}','strict_valid':strict['valid']})
    assert len(global_failures)==6 and sum(x['strict_valid'] for x in historical)==2
    assert props['uncertainty']=={'type':'string','minLength':1} and 'uncertainty' in sch['required']
    assert props['window_cited_frame_aliases']['minItems']==1
    assert props['events']['items']['properties']['timing_uncertainty']=={'type':'string','minLength':1}
    source=(s.ROOT/'src/memory_graph/pass_t/phase2b/predictions.py').read_text(encoding='utf8');tree=ast.parse(source)
    parser=ast.get_source_segment(source,next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='parse_raw'))
    s.save('SCHEMA_AUDIT.json',{'exact_global_field':'uncertainty','exact_global_json_path':'/uncertainty','global_parent':'root prediction object',
      'global_schema':props['uncertainty'],'global_required':True,'global_nullable':False,'global_applies_to_all_outcomes':True,
      'event_path':'/events/*/timing_uncertainty','event_schema':props['events']['items']['properties']['timing_uncertainty'],
      'event_required_if_event_exists':True,'zero_event_event_field_status':'NOT_APPLICABLE','citations_path':'/window_cited_frame_aliases',
      'citations_schema':props['window_cited_frame_aliases'],'citation_outcome_exceptions':[],
      'historical_global_failures':global_failures,'historical_strict_replay':historical,'parser_function_sha256':hashlib.sha256(parser.encode()).hexdigest(),
      'semantic_precheck':'CONSISTENT: truthful evidence-relative temporal limits or absence of further observed limitations can be described, without inventing a different transition interval or limitation.'})
    s.save('V1D_SCHEMA_FIELD_AUDIT.md','''# V1D schema field audit

已從12份舊raw JSON、schema error paths、原schema與Validator核對，global欄位是根物件的 **`uncertainty`，JSON path `/uncertainty`**；required string、non-null、minLength1，四種outcome皆適用。舊6份SCHEMA_MINLENGTH確實來自這個path，不是target_association_uncertainty(enum)，也不是event timing_uncertainty。

Event：`/events/*/timing_uncertainty`，每個實際存在event required string/non-null/minLength1；零event時不適用。Timing可EXACT_SUPPLIED_FRAME、BOUNDED_SUPPLIED_FRAMES或TIMING_UNKNOWN，非一律兩個bounding frames。Schema只檢查字串長度，描述是否有意義／有視覺支持需另審，不能用無意義文字充數。

Window citations：`/window_cited_frame_aliases` required array/minItems1/uniqueItems，item pattern `^F[0-9]{4}$`。CONFIRMED_EVENTS、NO_CONFIRMED_EVENT、INSUFFICIENT_EVIDENCE、TARGET_NOT_OBSERVABLE全部都要求，沒有conditional exception。Validator再核對processor-consumed alias membership；event cited_frame_aliases另有minItems1。靜態reference非event證據，未處理clip frames／private IDs不能引用。Citation不是連續assessability證明。

Semantic precheck通過：可描述真正直接觀察的取樣解析度、真實前後觀察缺口、未知時間或實際遮擋；沒有額外觀察到的限制也可在現有observations範圍說明。不可捏造遮擋／interval／midpoint；before/after bracket不是物理動作duration。沒有內部矛盾要求停工。Strict Validator/schema/parser均不修改；歷史raw只用於本稽核，未搬入新prompt。
''')
    bridge=s.ROOT/'src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py'
    s.save('bridge_before.txt',bridge.read_text(encoding='utf8'))
    s.save('BEFORE.json',{'git':s.git(),'protected_files':protected,'hardware':s.hardware(),
      'model_assets_verified':len(assets['files_sha256']),'scope':'prior non-image receipts/source plus model assets; no old or real image opened'})
    print('SCHEMA_AND_AUTHORITY_PASS /uncertainty; historical6 verified; protected',len(protected),flush=True)

if __name__=='__main__':
    try:
        if sys.argv[1]=='audit':audit()
        else:raise RuntimeError('UNKNOWN_PREPARATION_STEP')
    except Exception:
        error=traceback.format_exc();i=1
        while (s.OUT/f'errors/prepare_{i:03d}.json').exists():i+=1
        s.save(f'errors/prepare_{i:03d}.json',{'error':error,'argv':sys.argv[1:],'denied':s.DENIED})
        print(error,file=sys.stderr);sys.exit(1)

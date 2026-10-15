"""Phase1c bounded review checks. All answer fixtures are synthetic and local."""
import ast
import copy
import json
from pathlib import Path
import tkinter as tk
import pytest
from jsonschema import Draft202012Validator
from memory_graph.pass_t import phase1c_common as common
from memory_graph.pass_t import phase1c_responses as responses
from memory_graph.pass_t.phase1c_policy import policy_definition, wrapper_schema, verify_freeze, NAME
from memory_graph.pass_t.phase1c_review import EXPECTED, candidate_inventory, projected_inventory
from memory_graph.pass_t.sampling import validate_bundle, validate_manifest, bundle_from_manifest

ROOT=common.ROOT
OUT=common.OUT


@pytest.fixture
def synthetic():
    provenance='metadata/raw_observations.json'
    item={'pack_id':'SYNTHETIC_ONLY','binding_causality':'CAUSALITY_UNVERIFIED',
          'window_start_s':10.,'window_end_s':12.,
          'frames':[{'frame_id':'S000001','source_frame_index':1,'source_timestamp_s':10.},
                    {'frame_id':'S000002','source_frame_index':2,'source_timestamp_s':11.}],
          'references':[{'reference_id':'R000000'}],
          'candidates':[{'candidate_id':'7','evidence_frame_ids':['S000001'],'recorded_provenance_edges':[]}],
          'observations':[{'candidate_id':'7','observation_id':'raw:0@1','source_frame_index':1,
                           'provenance_reference':provenance}],
          'source_provenance_references':[provenance]}
    receipt={'created_at_utc':'2020-01-01T00:00:00+00:00','policy_md_sha256':'synthetic-md',
             'policy_json_sha256':'synthetic-json'}
    value={'schema_version':'HUMAN_SEED_REVIEW_WRAPPER_V1',
           'primary_response':{'pack_id':'SYNTHETIC_ONLY','selected_local_track_id':'7',
               'answer_type':'SELECTED_CANDIDATE','annotator_id':'SYNTHETIC_TEST_NOT_HUMAN',
               'timestamp':'2020-01-02T00:00:00+00:00','frames_reviewed':[1],
               'notes':'Synthetic evidence rationale','confidence':'LOW','provenance':'HUMAN_SEEDED',
               'global_identity_authority':False},
           'details':{'review_decision':'SELECT_LOCAL_CANDIDATE','selected_local_candidate_id':'7',
               'reviewed_frame_ids':['S000001'],'supporting_observation_ids':['raw:0@1'],
               'source_provenance_references':[provenance],
               'provenance_support':'HUMAN_VISUAL_LOCALIZATION_ONLY','rationale':'Synthetic evidence rationale',
               'uncertainty_status':'LOCAL_SELECTION_ONLY','reference_material_used':['R000000'],
               'contradictory_candidate_evidence':False},
           'attestations':{'human_attestation':True,'event_labels_viewed_for_this_pack':False,
               'selection_depends_on_event_interpretation':False,'claims_global_identity':False},
           'submission':{'submitted_via':'human_seed_review_viewer',
               'automatic_timestamp_utc':'2020-01-02T00:00:00+00:00','timestamp_recorded_automatically':True,
               'submission_id':'synthetic-test-only','policy_md_sha256':'synthetic-md',
               'policy_json_sha256':'synthetic-json','review_item_sha256':'synthetic-item'}}
    primary=common.read(OUT/'contracts/PASS_T_HUMAN_SEED_RESPONSE_SCHEMA_V1.json')
    def validate(record=None):
        return responses.validate_response(value if record is None else record,item,receipt,primary,wrapper_schema(),'synthetic-item')
    return item,receipt,value,primary,validate


def test_policy_valid_frozen_before_review_no_self_hash():
    receipt=verify_freeze();policy=common.read(OUT/'contracts'/f'{NAME}.json')
    assert policy==policy_definition()
    assert receipt['prospective_pre_registration'] and not receipt['human_responses_existed_before_creation']
    assert receipt['allow_pre_window_seed_reference'] is True
    for suffix,key in [('md','policy_md_sha256'),('json','policy_json_sha256')]:
        text=(OUT/'contracts'/f'{NAME}.{suffix}').read_text(encoding='utf-8')
        assert receipt[key]==common.sha(OUT/'contracts'/f'{NAME}.{suffix}')
        assert receipt[key] not in text
    Draft202012Validator.check_schema(wrapper_schema())


def test_source_unverified_dev_only():
    p=policy_definition()
    assert p['uses']['SOURCE_RESOLVED']['dev_preparation'] is True
    assert p['source_unverified_dev_eligible'] is True
    assert p['source_unverified_formal_eligible'] is False
    assert p['formal_evaluation_eligible_phase1c'] is False


def test_valid_seed_own_stratum_never_global_formal_causal(synthetic):
    result=synthetic[-1]()
    assert result['valid'] and result['review_completed'] and result['dev_eligible']
    assert result['target_source']=='HUMAN_SEEDED'
    assert result['binding_causality']=='CAUSALITY_UNVERIFIED'
    assert not result['global_identity_authority'] and not result['trusted_graph_write']
    assert not result['formal_evaluation_eligible']


@pytest.mark.parametrize('decision',['UNRESOLVED','NO_VISIBLE_TARGET','MULTIPLE_PLAUSIBLE_TARGETS'])
def test_nonselect_decisions_complete_not_promoted(synthetic,decision):
    item,receipt,value,primary,validate=synthetic
    value['details'].update(review_decision=decision,selected_local_candidate_id=None,
                           supporting_observation_ids=[],provenance_support='NONE',reference_material_used=[],uncertainty_status='UNRESOLVED')
    value['primary_response'].update(answer_type=decision,selected_local_track_id=None)
    assert validate()['valid'] and validate()['review_completed']
    assert not validate()['dev_eligible'] and validate()['target_source']=='UNRESOLVED'


@pytest.mark.parametrize('section,key,replacement',[
    ('primary_response','annotator_id',' '),('details','rationale',' '),
    ('details','reviewed_frame_ids',[]),('details','reviewed_frame_ids',['S999999']),
    ('details','supporting_observation_ids',[]),('details','supporting_observation_ids',['raw:999@1']),
    ('details','selected_local_candidate_id','999'),('details','source_provenance_references',[]),
    ('details','reference_material_used',['R999999']),('attestations','human_attestation',False),
    ('submission','submitted_via','agent'),('submission','automatic_timestamp_utc','invalid'),
    ('submission','timestamp_recorded_automatically',False),('submission','review_item_sha256','changed'),
    ('submission','policy_json_sha256','changed')])
def test_missing_or_invalid_required_evidence_rejected(synthetic,section,key,replacement):
    synthetic[2][section][key]=replacement
    assert not synthetic[-1]()['valid']


@pytest.mark.parametrize('flag',['event_labels_viewed_for_this_pack','selection_depends_on_event_interpretation','claims_global_identity'])
def test_contamination_record_valid_but_ineligible(synthetic,flag):
    synthetic[2]['attestations'][flag]=True;result=synthetic[-1]()
    assert result['valid'] and result['review_completed'] and not result['human_seed_eligible']
    assert result['ineligibility_reasons']


@pytest.mark.parametrize('key,value',[('contradictory_candidate_evidence',True),('uncertainty_status','UNCERTAIN'),
                                    ('uncertainty_status','UNRESOLVED'),('provenance_support','NONE'),('reference_material_used',[])])
def test_unresolved_evidence_not_eligible(synthetic,key,value):
    synthetic[2]['details'][key]=value;result=synthetic[-1]()
    # Reference reliance with NONE is an inconsistent record, or a valid but
    # insufficient record when no reference is claimed. Neither can promote.
    assert not result['human_seed_eligible']


def test_future_reference_not_in_window_evidence(synthetic):
    synthetic[2]['details']['reviewed_frame_ids']=['R000000']
    assert not synthetic[-1]()['valid']
    synthetic[2]['details']['reviewed_frame_ids']=['S000001']
    synthetic[0]['frames'][0]['source_timestamp_s']=12.
    assert not synthetic[-1]()['valid']


def test_human_cannot_invent_machine_edge(synthetic):
    synthetic[2]['details'].update(provenance_support='RECORDED_PROVENANCE_EDGE',reference_material_used=[])
    assert not synthetic[-1]()['valid']


def test_recorded_edge_with_complete_support_can_seed(synthetic):
    synthetic[0]['candidates'][0]['recorded_provenance_edges']=['synthetic-recorded-edge']
    synthetic[2]['details'].update(provenance_support='RECORDED_PROVENANCE_EDGE',reference_material_used=[])
    assert synthetic[-1]()['human_seed_eligible']


def test_no_authorized_seed_reference_allows_unresolved(synthetic):
    item,receipt,value,primary,validate=synthetic;item['references']=[]
    value['details'].update(review_decision='UNRESOLVED',selected_local_candidate_id=None,reference_material_used=[],
                           supporting_observation_ids=[],provenance_support='NONE',uncertainty_status='UNRESOLVED')
    value['primary_response'].update(answer_type='UNRESOLVED',selected_local_track_id=None)
    assert validate()['valid'] and validate()['review_completed'] and not validate()['dev_eligible']


def fixture_collection(tmp_path,monkeypatch,synthetic,answer_count=0):
    item,receipt,value,primary,validate=synthetic
    base=tmp_path/'human_seed_review';base.mkdir()
    def put(path,obj):path.write_text(json.dumps(obj),encoding='utf-8')
    put(base/'item.json',item)
    manifest={'items':[{'pack_id':item['pack_id'],'item_path':'item.json','item_sha256':common.sha(base/'item.json'),
                       'original_resolution':'NEEDS_HUMAN_SEED','overlap_group_id':'SYNTHETIC_GROUP'}]}
    put(base/'review_manifest.json',manifest)
    contracts=tmp_path/'contracts';contracts.mkdir()
    put(contracts/'PASS_T_HUMAN_SEED_RESPONSE_SCHEMA_V1.json',primary)
    put(contracts/'PASS_T_HUMAN_SEED_REVIEW_WRAPPER_SCHEMA_V1.json',wrapper_schema())
    value['submission']['review_item_sha256']=manifest['items'][0]['item_sha256']
    answers=[]
    for n in range(answer_count):
        path=base/f'synthetic_record_{n}.json';put(path,value);answers.append(path)
    # No fixture is written to any responses directory, including temp dirs.
    original_glob=Path.glob
    monkeypatch.setattr(Path,'glob',lambda p,pattern:iter(answers) if p==base/'responses' else original_glob(p,pattern))
    monkeypatch.setattr(responses,'OUT',tmp_path)
    monkeypatch.setattr(responses,'verify_freeze',lambda:receipt)
    return base,answers


def test_missing_response_is_pending(tmp_path,monkeypatch,synthetic):
    fixture_collection(tmp_path,monkeypatch,synthetic)
    result=responses.load_reviews()
    assert result['completed']==result['human_seeded_valid']==0
    assert result['items'][0]['human_review_status']=='UNREVIEWED'


def test_duplicate_response_explicit_no_winner_and_originals_unchanged(tmp_path,monkeypatch,synthetic):
    base,answers=fixture_collection(tmp_path,monkeypatch,synthetic,2)
    before=[common.sha(p) for p in answers];result=responses.load_reviews()
    assert result['completed']==0 and result['items'][0]['human_review_status']=='DUPLICATE_RESPONSES_BLOCKED'
    assert before==[common.sha(p) for p in answers]


def test_readonly_validator_does_not_change_submitted_record(tmp_path,monkeypatch,synthetic):
    base,answers=fixture_collection(tmp_path,monkeypatch,synthetic,1)
    before=common.sha(answers[0]);result=responses.load_reviews()
    assert result['completed']==1 and result['human_seeded_valid']==1
    assert common.sha(answers[0])==before


def test_changed_item_blocks_validation(tmp_path,monkeypatch,synthetic):
    base,answers=fixture_collection(tmp_path,monkeypatch,synthetic,1)
    (base/'item.json').write_text(json.dumps({**synthetic[0],'window_end_s':99}),encoding='utf-8')
    with pytest.raises(ValueError,match='changed'):responses.load_reviews()


def test_exclusive_new_artifact_write_cannot_replace_original(tmp_path,monkeypatch):
    (tmp_path/'manifests').mkdir();(tmp_path/'manifests/phase1c_protected_before.json').write_text('{}',encoding='utf-8')
    monkeypatch.setattr(common,'OUT',tmp_path);monkeypatch.setattr(common,'ROOT',tmp_path)
    path=tmp_path/'synthetic_record.json';common.write(path,{'synthetic':True},exclusive=True);before=common.sha(path)
    with pytest.raises(FileExistsError):common.write(path,{},exclusive=True)
    assert before==common.sha(path)
    with pytest.raises(ValueError):common.write(tmp_path.parent/'outside.json',{})


@pytest.fixture(scope='module')
def packages():
    manifest=common.read(OUT/'human_seed_review/review_manifest.json')
    return manifest,[(e,common.read(OUT/'human_seed_review'/e['item_path'])) for e in manifest['items']]


def test_exact_seven_fullrate_packages(packages):
    manifest,items=packages
    assert [e['pack_id'] for e in manifest['items']]==list(EXPECTED)
    assert len(items)==7 and sum(len(i['frames']) for e,i in items)==726
    assert sum(len(i['references']) for e,i in items)==19
    assert not manifest['candidate_inventory_discrepancies']
    for e,i in items:
        assert common.sha(OUT/'human_seed_review'/e['item_path'])==e['item_sha256']
        assert i['clip']['full_rate'] and i['clip']['decoded_frame_count']==len(i['frames'])


def test_all_frames_and_references_authorized(packages):
    for e,item in packages[1]:
        a,b=item['authorized_half_open_frames'];start,end=item['window_start_s'],item['window_end_s']
        indices=[f['source_frame_index'] for f in item['frames']]
        assert indices==sorted(set(indices))
        assert all(a<=f['source_frame_index']<b and start<=f['source_timestamp_s']<end for f in item['frames'])
        assert all(r['source_timestamp_s']<start and r['role']=='REFERENCE_PRE_WINDOW' and not r['may_be_used_as_in_window_evidence'] for r in item['references'])
        assert not {f['source_frame_index'] for f in item['frames']} & {r['source_frame_index'] for r in item['references']}


def test_candidates_are_existing_inwindow_allowlist_without_future_or_diagnosis(packages):
    mappings={m['pack_id']:m for m in common.read(OUT/'manifests/window_target_mapping.json')['packs']}
    for e,item in packages[1]:
        seed,binding,seedrows,rows=projected_inventory(mappings[item['pack_id']])
        ids={f['source_frame_index'] for f in item['frames']}
        expected=[o for o in rows if o['source_frame_index'] in ids]
        assert item['observations']==expected and item['candidates']==candidate_inventory(expected)
        assert all(item['window_start_s']<=o['source_timestamp_s']<item['window_end_s'] for o in expected)
        assert all(c['evidence_frame_ids'] and c['observation_ids'] for c in item['candidates'])


def test_review_projection_excludes_answers_whole_video_scores_and_aliases(packages):
    forbidden={'diagnostic_only','ground_truth','event_gt','identityguard','alias','physical_identity',
               'vlm_prediction','human_label','source_video_path','score','confidence','area','visibility_count'}
    def walk(value):
        if isinstance(value,dict):
            assert not forbidden.intersection(k.lower() for k in value)
            for v in value.values():walk(v)
        elif isinstance(value,list):
            for v in value:walk(v)
        elif isinstance(value,str):
            assert '.mp4' not in value.lower() and 'phone_01' not in value and 'PICK_UP' not in value and 'PLACE' not in value
    for e,item in packages[1]:walk(item)
    for path in [ROOT/'src/memory_graph/pass_t/phase1c_viewer.py',ROOT/'scripts/run_pass_t_human_seed_review.py']:
        text=path.read_text(encoding='utf-8')
        assert 'source_video_path' not in text and 'diagnostic_only' not in text


def test_ascending_candidate_ids_no_rank_fields(packages):
    for e,item in packages[1]:
        ids=[c['candidate_id'] for c in item['candidates']];assert ids==sorted(ids)
        assert all(set(c)=={'candidate_id','local_track_id','observation_ids','evidence_frame_ids','recorded_provenance_edges','selection_scope'} for c in item['candidates'])


def test_review_only_assets_rejected_by_frozen_model_contract(packages):
    for e,item in packages[1]:
        assert item['not_model_input'] and item['human_review_only'] and not item['evaluation_eligible']
        assert validate_bundle(item) and validate_manifest(item) and validate_bundle(item['clip'])
        with pytest.raises(KeyError):bundle_from_manifest(item,'B','synthetic-prompt')


def test_overlap_duplicate_not_independent(packages):
    mappings={m['pack_id']:m for m in common.read(OUT/'manifests/window_target_mapping.json')['packs']}
    assert mappings['test1__W03']['overlap_group_id']==mappings['test1__W05']['overlap_group_id']
    assert mappings['test8__W06']['overlap_group_id']==mappings['test8__W07']['overlap_group_id']
    assert len({m['overlap_group_id'] for m in mappings.values()})==7
    assert packages[0]['recording_session_independence']=='UNKNOWN'


def test_native_viewer_all_cases_without_saving(monkeypatch,packages):
    from memory_graph.pass_t.phase1c_viewer import HumanSeedViewer
    # Fail loudly if any QA path attempts to save an annotation.
    monkeypatch.setattr(HumanSeedViewer,'save',lambda self:pytest.fail('QA must never submit'))
    root=tk.Tk();root.withdraw()
    try:
        viewer=HumanSeedViewer(root);root.update_idletasks()
        for e,item in packages[1]:
            viewer.pack.set(e['pack_id']);viewer.load_item();root.update_idletasks()
            assert viewer.decision.get()==viewer.candidate.get()==viewer.exposed.get()==''
            assert not viewer.human.get() and not viewer.citations
            assert list(viewer.candidate_box['values'])==[c['candidate_id'] for c in item['candidates']]
            viewer.slide(len(item['frames'])-1);assert viewer.frame_index==len(item['frames'])-1
            viewer.step(-1);viewer.cite();assert len(viewer.citations)==1
            assert viewer.save_button.winfo_y()>=0
            bad=copy.deepcopy(item['frames'][0]);bad['sha256']='altered'
            with pytest.raises(ValueError):viewer.verified_image(bad)
    finally:root.destroy()


def test_static_safety_utf8_and_zero_counters():
    paths=list((ROOT/'src/memory_graph/pass_t').glob('phase1c_*.py'))+[
        ROOT/'scripts/run_pass_t_phase1c.py',ROOT/'scripts/run_pass_t_human_seed_review.py',
        Path(__file__),ROOT/'tests/test_pass_t_causality_audit.py']
    assert not common.safety_scan(paths)['errors']
    assert all(v==0 for v in common.COUNTERS.values())


def test_only_viewer_human_callback_writes_production_answers():
    for path in (ROOT/'src/memory_graph/pass_t').glob('phase1c_*.py'):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        if path.name=='phase1c_viewer.py':
            callback=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='save')
            assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='write' for n in ast.walk(callback))
        else:
            for n in ast.walk(tree):
                if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='save':
                    # PIL image/crop saves create bounded media, not answers.
                    assert isinstance(n.func.value,ast.Name) and n.func.value.id in {'crop','image'}


def test_expanded_protection_and_frozen_prompt():
    protected=common.read(OUT/'manifests/phase1c_protected_before.json')
    assert len(protected)==17595
    assert all((ROOT/p).is_file() and common.sha(ROOT/p)==h for p,h in protected.items())
    preflight=common.read(OUT/'manifests/phase1c_preflight.json')
    assert preflight['pass_i_prompt_sha256']=='b6057e19de893514fabba7842dbd3a91957fc17e7255c2e9bfb2a3b16dd7b53d'


@pytest.mark.parametrize('completed,eligible',[(0,0),(7,6)])
def test_report_tracks_authentic_review_progress_without_stale_waiting_text(completed,eligible):
    from memory_graph.pass_t.phase1c_report import markdown
    # Entirely synthetic report structure; no production annotations used.
    r={'primary_status':'SYNTHETIC_STATUS','policy_receipt':{'policy_version':'SYNTHETIC',
         'created_at_utc':'2020-01-01T00:00:00+00:00','policy_md_sha256':'synthetic-md','policy_json_sha256':'synthetic-json'},
       'human_reviews':{'completed':completed,'responses_present':completed,'human_seeded_valid':eligible,'dev_eligible':eligible,'items':[]},
       'review_packages':{'full_rate_frames':0,'reference_crops':0,'items':[]},
       'readiness':{'causal_verified':0,'causality_unverified':9,'non_causal':0,'unique_media_windows':8,
           'nonoverlapping_evidence_groups':7,'valid_human_seeded_packs':eligible,'human_seeded_dev_eligible':eligible,
           'still_unresolved':7-eligible,'unique_candidate_present_media_windows':8,'unique_target_usable_media_windows':1+eligible},
       'binding_audit':{'packs':[]},'audit_isolation':{'status':'PASS','actual_input_count':0},
       'tests':{'tests':1,'failures':0,'errors':0,'skipped':0,'status':'PASS','groups':{}},
       'preservation':{'status':'PASS','protected_counts':{},'pass_i_prompt_sha256':'synthetic-prompt'},
       'safety':{'status':'PASS'},'runtime_counters':dict(common.COUNTERS)}
    text=markdown(r)
    if completed==7:
        assert '目前收到 7 份人工原始回覆，7/7 通過驗證' in text
        assert '目前 responses/ 為空' not in text
        assert '七份真實人工審閱與獨立審計已完成' in text
        assert '由你本人在本機 viewer 完成尚未完成' not in text
    else:
        assert '目前 responses/ 為空' in text
        assert '由你本人在本機 viewer 完成尚未完成' in text
    assert '不會新增 tracking edge、延伸到後續 IDs 或建立全域身分' in text

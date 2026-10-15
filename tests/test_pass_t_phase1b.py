"""Phase1b boundaries and actual media tests; missing codecs fail, never skip."""
import ast
import builtins
import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
import pytest
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor'),
             str(ROOT/'outputs/current_development/video_event_experiment/.deps')]
from memory_graph.pass_t.resolver import cutoff_records, resolve_window, stage0_gate, PILOT_RESTRICTION
from memory_graph.pass_t.overlap import interval_metrics, relationships
from memory_graph.pass_t import media
from memory_graph.pass_t.sampling import sample, validate_bundle, validate_manifest, shared_frames, verify_encoded_timing
from memory_graph.pass_t.phase1b import human_schema, sha


def fixture_rows(track=17, frames=(10,12)):
    return [{'frame_index':i,'timestamp':i/10,'source_track_id':track,'candidate_id':None,
             'semantic_class':'cell phone','bbox':[1,1,6,6],'observation_id':f'o{i}:{track}'} for i in frames]


def resolve(rows=None,binding=None,validated=True):
    window={'pack_id':'W1','window_start_s':1.,'window_end_s':2.}
    b={'source_track_id':17,'timestamp':.5,'binding_causality_status':'CAUSAL_VERIFIED'}
    if binding:b.update(binding)
    inv={'records':cutoff_records(fixture_rows() if rows is None else rows,2.),
         'source_paths':['source.json'],'coverage_validated':validated}
    return resolve_window(window,b,inv)


def test_01_explicit_bound_track():
    x=resolve();assert x['resolution_status']=='RESOLVED_UNIQUE' and x['resolved_local_track_id']=='17'


def test_02_zero_seed_observations():
    assert resolve(fixture_rows(99))['resolution_status']=='NEEDS_HUMAN_SEED'


def test_03_only_unrelated_candidate_not_identity():
    x=resolve(fixture_rows(99));assert x['resolved_local_track_id'] is None


def test_04_multiple_candidates_ambiguous():
    assert resolve(fixture_rows(98)+fixture_rows(99))['resolution_status']=='AMBIGUOUS'


def test_05_valid_inventory_empty():
    assert resolve([])['resolution_status']=='NO_CANDIDATE'


def test_06_unvalidated_inventory():
    for rows in [[],fixture_rows()]:
        assert resolve(rows,validated=False)['resolution_status']=='NEEDS_HUMAN_SEED'


def test_07_geometry_cannot_link_tracks():
    # identical boxes/times supply no positive cross-track linkage
    assert resolve(fixture_rows(99))['resolution_status']!='RESOLVED_UNIQUE'


def test_08_same_local_track_continuity_and_epoch():
    rows=fixture_rows();rows[0]['candidate_epoch_id']=rows[1]['candidate_epoch_id']='CE1'
    assert resolve(rows)['resolved_candidate_epoch_id']=='CE1'
    assert resolve()['resolved_candidate_epoch_id'] is None


@pytest.mark.parametrize('seed',[None,'phone_01',999])
def test_09_no_global_or_cross_track_guess(seed):
    assert resolve(binding={'source_track_id':seed})['resolved_local_track_id'] is None


def test_10_future_excluded():
    assert cutoff_records(fixture_rows(frames=(10,20,21)),2.)==fixture_rows(frames=(10,))
    assert resolve(fixture_rows(frames=(20,21)))['resolution_status']=='NO_CANDIDATE'
    with pytest.raises(ValueError,match='future'):
        resolve_window({'pack_id':'W','window_start_s':1.,'window_end_s':2.},{},
                       {'records':fixture_rows(frames=(21,))})


def test_11_diagnostic_separation():
    rows=fixture_rows();rows[0].update(entity_id='phone_01',reid_decision='MATCH',human_label='SAME')
    clean=cutoff_records(rows,2.)
    assert not any(k in clean[0] for k in ['entity_id','reid_decision','human_label'])
    with pytest.raises(ValueError,match='diagnostic'):
        resolve_window({'window_start_s':1.,'window_end_s':2.,'diagnostic_only':{}},{},{})


def test_12_reproducible_provenance():
    x=resolve();assert x['evidence_frame_range']==[10,12]
    assert x['supporting_observation_ids']==['o10:17','o12:17']
    assert x['evidence_source_paths']==['source.json'] and x['used_pre_window_metadata']
    assert x['used_post_window_metadata_for_binding'] is False


def test_13_unverified_never_upgraded_and_noncausal_blocked():
    x=resolve(binding={'binding_causality_status':'CAUSALITY_UNVERIFIED'})
    assert x['resolution_status']=='RESOLVED_UNIQUE' and x['binding_causality_status']=='CAUSALITY_UNVERIFIED'
    assert resolve(binding={'binding_causality_status':'NON_CAUSAL'})['resolution_status']!='RESOLVED_UNIQUE'


def test_14_forbidden_diagnosis_io(monkeypatch):
    original=Path.open
    def guarded(self,*args,**kwargs):
        assert self.name not in {'PASS_T_BLOCKER_DIAGNOSIS.json','human_seed_request.json'}
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'open',guarded)
    assert resolve()['resolution_status']=='RESOLVED_UNIQUE'
    # Source module AST has no diagnosis/human-seed import or filename reference.
    for name in ['resolver.py','media.py']:
        source=(ROOT/'src/memory_graph/pass_t'/name).read_text(encoding='utf-8')
        assert 'PASS_T_BLOCKER_DIAGNOSIS' not in source and 'human_seed_request' not in source
    written=[]
    monkeypatch.setattr(media,'stage0_gate',lambda *args,**kwargs:{'eligible_packs':[]})
    monkeypatch.setattr(media,'dump',lambda p,value:written.append((str(p),value)))
    media.run_pilot(False)
    assert written and all('diagnostic_only' not in json.dumps(value) for _,value in written)


def window(id_,bounds=(0,10),task='A',video='s'):
    return {'pack_id':id_,'source_video_hash':video,'target_scope':'T',
            'authorized_half_open_frames':list(bounds),'inclusive_half_open_equivalent':[bounds[0],bounds[1]+1],
            'window_start_s':bounds[0]/10,'window_end_s':bounds[1]/10,'task_context':task}


def test_15_identical_media():
    r=relationships([window('A'),window('B')]);assert r['unique_media_windows']==1
    assert r['packs']['B']['media_duplicate_of']=='A'


def test_16_different_contexts_preserved():
    r=relationships([window('A'),window('B',task='B')])
    assert len(r['packs'])==2 and r['unique_evaluation_items']==2
    assert r['pairs'][0]['reason']=='SAME_MEDIA_DIFFERENT_CONTEXT_CORRELATED'


def test_17_evaluation_duplicate():
    r=relationships([window('A'),window('B')]);assert r['unique_evaluation_items']==1
    assert r['packs']['B']['duplicate_of']=='A'


def test_18_overlap_sanity():
    r=interval_metrics([857,962],[936,1054])
    assert r['intersection']==26 and r['union']==197
    assert r['iou']==pytest.approx(26/197) and r['overlap_over_shorter']==pytest.approx(26/105)
    assert interval_metrics([857,963],[936,1055])['intersection']==27


def test_19_nonoverlap_touching_and_different_source():
    for ws in [[window('A'),window('B',(10,20))],[window('A'),window('B',video='other')]]:
        r=relationships(ws);assert not r['pairs'] and r['nonoverlapping_evidence_groups']==2


def test_20_stable_group_ids():
    ws=[window('A'),window('B',(5,15)),window('C',(12,20))]
    assert relationships(ws)==relationships(list(reversed(ws)))
    assert len({x['overlap_group_id'] for x in relationships(ws)['packs'].values()})==1


def test_21_no_independent_double_count():
    r=relationships([window('A'),window('B',(5,15)),window('C',(20,25))])
    assert r['nonoverlapping_evidence_groups']==2 and 'one split' in r['split_policy']


def gate_rows():
    return [{'pack_id':f'W{i}','resolution_status':'RESOLVED_UNIQUE' if i<2 else 'NEEDS_HUMAN_SEED',
             'clean_source_hash_verified':True} for i in range(9)]


def test_22_strict_default():
    g=stage0_gate(gate_rows());assert not g['legacy_stage0_gate_pass'] and not g['eligible_packs']


def test_23_partial_independent():
    assert stage0_gate(gate_rows(),True)['eligible_packs']==['W0','W1']


def test_24_unresolved_and_invalid_source_blocked():
    rows=gate_rows();rows[0]['clean_source_hash_verified']=False
    g=stage0_gate(rows,True);assert g['eligible_packs']==['W1'] and len(g['blocked_packs'])==8


def test_25_pilot_restriction():
    assert stage0_gate(gate_rows(),True).items() >= PILOT_RESTRICTION.items()


def test_26_no_promotion_even_all_resolved():
    rows=gate_rows()
    for row in rows:row['resolution_status']='RESOLVED_UNIQUE'
    assert stage0_gate(rows,True)['formal_evaluation_ready'] is False


@pytest.fixture(scope='module')
def real_media(tmp_path_factory):
    root=tmp_path_factory.mktemp('media')
    source=root/'source.mkv'
    frames=[Image.fromarray(np.full((24,32,3),i*35,dtype=np.uint8)) for i in range(8)]
    media.encode_video(source,frames,[i/10 for i in range(8)],.8)
    mapping={'pack_id':'W','video_id':'S','resolution_status':'RESOLVED_UNIQUE',
             'binding_causality_status':'CAUSALITY_UNVERIFIED','resolved_local_track_id':'17',
             'window_start_s':.1,'window_end_s':.7,'authorized_half_open_frames':[1,7],
             'source_fps':10,'source_video_hash':sha(source),'clean_source_hash_verified':True,
             'exact_observations':[{'frame_index':1,'bbox':[2,2,16,16],'timestamp':.1},
                                   {'frame_index':6,'bbox':[3,3,18,18],'timestamp':.6}]}
    folder=root/'unit';record=media.make_media(source,mapping,folder,'0'*64)
    manifest=json.loads((folder/'private/frame_manifest.json').read_text())
    bundles=[json.loads((folder/f'bundle_{mode}.json').read_text()) for mode in 'ABC']
    return source,mapping,folder,record,manifest,bundles


def test_27_authorized_halfopen(real_media):
    _,mapping,_,record,manifest,_=real_media
    assert all(media.authorized(f['source_frame_index'],f['source_timestamp_s'],mapping) for f in manifest['frames'])
    assert not media.authorized(7,.7,mapping) and not media.authorized(0,0,mapping)


def test_28_monotonic(real_media):
    fs=real_media[4]['frames'];assert all(a['source_timestamp_s']<b['source_timestamp_s'] for a,b in zip(fs,fs[1:]))


def test_29_deterministic_3fps(real_media):
    source,m,_,_,_,_=real_media
    rows,_,_=media.decode_authorized(source,m)
    a,info=sample(rows,.1,.7,3);b,other=sample(deepcopy(rows),.1,.7,3)
    assert a==b and info==other and [x['source_frame_index'] for x in a]==[1,4]


def test_30_shared_abc(real_media):
    assert shared_frames(real_media[5])
    assert all(not validate_bundle(b) for b in real_media[5])


def test_31_native_roundtrip(real_media):
    a=real_media[3]['A'];assert a['encoded_frame_count']==a['decoded_frame_count']==2
    assert a['ordered_pixel_signatures']==a['decoded_pixel_signatures'] and a['codec']=='ffv1'


def test_32_pts_or_explicit_failure(real_media):
    assert real_media[3]['A']['timing']['status']=='READY'
    assert verify_encoded_timing([0,.3],[0,.4])['status']=='A_NON_EQUIVALENT'
    a=real_media[3]['A'];assert sum(a['frame_duration_ticks'])+a['encoder_pts_ticks'][0]==600


def test_33_B_order_hashes(real_media):
    _,_,folder,_,manifest,bundles=real_media
    assert not validate_manifest(manifest,folder)
    assert [sha(folder/f['image_path']) for f in bundles[1]['frames']]==[f['sha256'] for f in manifest['frames']]


def test_34_C_actual_tile_order(real_media):
    _,_,folder,record,manifest,_=real_media
    grid=Image.open(folder/'media/grid.png');tw,th=record['C']['tile_dimensions']
    for mapping,f in zip(record['C']['tile_mapping'],manifest['frames']):
        expected=Image.open(folder/f['image_path']).resize((tw,th),Image.Resampling.LANCZOS)
        actual=grid.crop(mapping['pixel_rectangle'])
        assert np.array_equal(np.asarray(expected),np.asarray(actual))


def test_35_metadata_stripping(real_media):
    folder=real_media[2]
    for path in list((folder/'frames').glob('*.png'))+[folder/'media/grid.png']:
        with Image.open(path) as im:assert not im.info and not im.getexif()
    assert real_media[3]['leakage']['status']=='REAL_LEAKAGE_PASS'


def test_36_media_readability(real_media):
    av=media.require_media();folder=real_media[2]
    with av.open(str(folder/'media/input.mkv')) as c:
        assert len(list(c.decode(video=0)))==2


@pytest.mark.parametrize('token',['phone_01','PICK_UP','GT','trigger','IdentityGuard','candidate_012'])
def test_37_reject_actual_metadata_leaks(real_media,token):
    folder=real_media[2];bundles=deepcopy(real_media[5]);bundles[0]['extra']=token
    scan=media.scan_real(folder,bundles,real_media[3]['A'])
    assert scan['status']=='BLOCKED_LEAKAGE'


def test_38_no_future_pixels(real_media):
    source,mapping,_,_,manifest,_=real_media
    rows,pixels,record=media.decode_authorized(source,mapping)
    assert all(1<=i<7 for i in pixels) and record['codec_preroll_frames_not_model_input']==1
    assert max(f['source_frame_index'] for f in manifest['frames'])<7


def test_39_exact_overlay_no_snap(real_media):
    pixels=np.zeros((24,32,3),dtype=np.uint8)
    observations=[{'frame_index':2,'bbox':[2,2,16,16]}]
    image,marked=media.exact_overlay(pixels,3,observations)
    assert not marked and np.array_equal(np.asarray(image),pixels)
    image,marked=media.exact_overlay(pixels,2,observations)
    assert marked and tuple(np.asarray(image)[2,2])==(0,180,180)
    cov=real_media[3]['overlay_coverage'];assert cov['ratio']==.5 and cov['unmarked_source_frame_indices']==[4]


def test_40_private_mapping_excluded(real_media):
    for b in real_media[5]:
        s=json.dumps(b);assert '17' not in b['target_id'] and 'private/' not in s and 'CAUSALITY' not in s
        assert 'evaluation_eligible' not in b and b['target_id']=='T1'
    assert real_media[3].items() >= PILOT_RESTRICTION.items()


def test_41_sequential_index_pixels(real_media):
    source,mapping,_,_,_,_=real_media
    rows,pixels,record=media.decode_authorized(source,mapping)
    assert record['method'].startswith('SEQUENTIAL')
    assert all(int(pixels[r['source_frame_index']][0,0,0])==35*r['source_frame_index'] for r in rows)


def test_42_no_global_alias():
    x=resolve();assert not any(k in x for k in ['entity_id','alias','global_alias','phone_01'])


def test_43_no_graph_writes(monkeypatch,tmp_path):
    original=Path.write_bytes
    def guard(self,data):
        assert not any(k in str(self).lower() for k in ['memory_graph.json','entity_registry','graph_store'])
        return original(self,data)
    monkeypatch.setattr(Path,'write_bytes',guard)
    media.dump(tmp_path/'private.json',PILOT_RESTRICTION)
    assert resolve()['resolved_local_track_id']=='17'


def test_44_no_model_import_or_inference(real_media):
    for name in ['phase1b.py','resolver.py','media.py','overlap.py']:
        source=(ROOT/'src/memory_graph/pass_t'/name).read_text(encoding='utf-8')
        imports=[ast.unparse(node) for node in ast.walk(ast.parse(source)) if isinstance(node,(ast.Import,ast.ImportFrom))]
        assert not any(token in ' '.join(imports) for token in ['torch','openai','transformers','reasoning.model'])
    assert real_media[3]['model_inference_calls']==real_media[3]['graph_writes']==0


def protected_manifest():
    return json.loads((ROOT/'artifacts/pass_t/manifests/phase1b_protected_before.json').read_text())


def test_45_builder_unchanged():
    for key,h in protected_manifest().items():
        if key.startswith('src/memory_graph/events/'):
            assert sha(ROOT/key)==h


def test_46_frozen_schemas_unchanged():
    m=protected_manifest()
    for p in (ROOT/'artifacts/pass_t/contracts').glob('*SCHEMA_V1.json'):
        key=p.relative_to(ROOT).as_posix()
        if key in m:assert sha(p)==m[key]


def test_47_all_protected_hashes():
    m=protected_manifest()
    preflight=json.loads((ROOT/'artifacts/pass_t/manifests/phase1b_preflight.json').read_text(encoding='utf-8'))
    assert len(m)==preflight['expanded_protected_count']
    changed=[key for key,h in m.items() if not (ROOT/key).is_file() or sha(ROOT/key)!=h]
    assert not changed


def test_48_original_phase1_files_unchanged():
    m=protected_manifest()
    paths=['src/memory_graph/pass_t/'+x for x in ['__init__.py','contracts.py','sampling.py','phase1.py','fixtures.py','evaluation.py']]
    paths+=['scripts/run_pass_t_phase1.py','tests/test_pass_t.py','artifacts/pass_t/reports/PASS_T_PHASE1_SMOKE_REPORT.md']
    assert all(sha(ROOT/p)==m[p] for p in paths)


def test_49_human_schema_only_no_response_application():
    from jsonschema import Draft202012Validator
    schema=human_schema();Draft202012Validator.check_schema(schema)
    record={'pack_id':'W','selected_local_track_id':None,'answer_type':'UNRESOLVED','annotator_id':'A',
            'timestamp':'2026-10-11T00:00:00Z','frames_reviewed':[1],'notes':'No positive link','confidence':'LOW',
            'provenance':'HUMAN_SEEDED','global_identity_authority':False}
    # Validate format definition only; no human response loaded/applied to mapping.
    assert not list(Draft202012Validator(schema).iter_errors(record))
    record['answer_type']='SELECTED_CANDIDATE'
    assert list(Draft202012Validator(schema).iter_errors(record))
    assert 'HUMAN_SEEDED' not in json.dumps(resolve())


def test_missing_toolchain_fails_not_skips(monkeypatch):
    original=builtins.__import__
    def deny(name,*args,**kwargs):
        if name=='av':raise ImportError('intentional missing PyAV')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',deny)
    with pytest.raises(RuntimeError,match='BLOCKED_ENVIRONMENT'):
        media.require_media()


def test_exact_conflict_abstains():
    rows=fixture_rows();rows.append({**rows[0],'bbox':[2,2,8,8]})
    assert resolve(rows)['resolution_status']=='AMBIGUOUS'


def test_untracked_candidates_preserved_for_review_not_bound():
    rows=fixture_rows(None);rows[0]['candidate_id']='C1';rows[1]['candidate_id']='C2'
    x=resolve(rows)
    assert x['resolution_status']=='NEEDS_HUMAN_SEED'
    assert {c['candidate_id'] for c in x['available_candidates']}=={'C1','C2'}
    assert all(c['local_track_id'] is None for c in x['available_candidates'])


def test_real_test1_outputs_validated():
    report=json.loads((ROOT/'artifacts/pass_t/smoke/phase1b_real_media.json').read_text())
    eligible=[p for p in report['packs'] if p['real_smoke_status']=='PASS']
    assert len(eligible)==2
    for p in eligible:
        folder=ROOT/p['artifact_directory'];m=json.loads((folder/'private/frame_manifest.json').read_text())
        assert not validate_manifest(m,folder)
        assert p['overlay_coverage']['marked_count']==2 and p['overlay_coverage']['sampled_count']==11
        assert p['leakage']['status']=='REAL_LEAKAGE_PASS'
        bundles=[json.loads((folder/f'bundle_{mode}.json').read_text()) for mode in 'ABC']
        assert shared_frames(bundles) and all(not validate_bundle(b) for b in bundles)

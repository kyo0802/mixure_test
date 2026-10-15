"""Independent audit tests: source/config/runtime records, synthetic facts only."""
import ast
import pytest
from memory_graph.pass_t import phase1c_audit as audit
from memory_graph.pass_t.phase1c_common import ROOT, OUT, read, COUNTERS, safety_scan


def verified_facts():
    return {'claimed_cutoff_frame':12,'binding_influential_frame':12,'upstream_influential_frame':12,
            'runtime_lineage_complete':True,'upstream_independently_verified':True,
            'code_revision_verified':True,'gt_excluded_by_lineage':True,
            'future_influence_proven':False,'gt_influence_proven':False}


def test_hash_is_not_causal_evidence():
    assert audit.classify_chain({'artifact_sha256':'synthetic-hash'})=='CAUSALITY_UNVERIFIED'


def test_offline_time_is_not_noncausal():
    facts={'source_time_s':12,'artifact_wall_clock':'2026-10-11T00:00:00+00:00'}
    assert audit.classify_chain(facts)=='CAUSALITY_UNVERIFIED'


@pytest.mark.parametrize('flag',['future_influence_proven','gt_influence_proven'])
def test_positive_influence_noncausal(flag):
    facts=verified_facts();facts[flag]=True
    assert audit.classify_chain(facts)=='NON_CAUSAL'


def test_verified_prefix_with_complete_independent_lineage():
    assert audit.classify_chain(verified_facts())=='CAUSAL_VERIFIED'


@pytest.mark.parametrize('key',['runtime_lineage_complete','upstream_independently_verified','code_revision_verified','gt_excluded_by_lineage'])
def test_unknown_link_keeps_prefix_unverified(key):
    facts=verified_facts();facts[key]=False
    assert audit.classify_chain(facts)=='CAUSALITY_UNVERIFIED'


@pytest.mark.parametrize('key',['binding_influential_frame','upstream_influential_frame'])
def test_unknown_source_horizon_unverified(key):
    facts=verified_facts();facts[key]=None
    assert audit.classify_chain(facts)=='CAUSALITY_UNVERIFIED'


def test_potential_future_scan_requires_positive_influence_proof():
    facts=verified_facts();facts['runtime_lineage_complete']=False
    facts['direct_full_input_scan_through_frame']=500
    assert audit.classify_chain(facts)=='CAUSALITY_UNVERIFIED'


def test_missing_revision_not_invented():
    result=audit.revision_evidence(None,audit.CODE_PATHS[0])
    assert result['revision'] is None and not result['verifiable']
    assert audit.classify_chain({**verified_facts(),'code_revision_verified':False})=='CAUSALITY_UNVERIFIED'


def test_revision_reader_retrieves_blob_without_execution(monkeypatch):
    calls=[]
    class Result:returncode=1
    def run(args,**kwargs):calls.append(args);return Result()
    monkeypatch.setattr(audit.subprocess,'run',run)
    result=audit.revision_evidence('synthetic-nonexistent',audit.CODE_PATHS[0])
    assert not result['verifiable'] and calls[0][:2]==['git','show']


def test_input_allowlist_rejects_every_unknown_path():
    reader=audit.AllowedReader(['test1'])
    with pytest.raises(ValueError,match='allowlist'):reader.text('arbitrary/unknown/input.json')
    expected=set(audit.CODE_PATHS+audit.CONFIG_PATHS+audit.BASELINE_PATHS+('artifacts/pass_t/manifests/window_target_mapping.json',))
    expected.update('outputs_v292/test1/'+name for name in audit.ARTIFACT_NAMES)
    assert reader.allowed==expected
    assert not any('label' in p.lower() or 'ground_truth' in p.lower() for p in reader.allowed)


def test_static_import_isolation_and_no_inspected_code_execution():
    tree=ast.parse((ROOT/'src/memory_graph/pass_t/phase1c_audit.py').read_text(encoding='utf-8'))
    imports={n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
    imports.update(a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names)
    assert imports<={'hashlib','subprocess','pathlib','json','phase1c_common'}
    assert not safety_scan([ROOT/'src/memory_graph/pass_t/phase1c_audit.py'])['errors']
    for n in ast.walk(tree):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name):assert n.func.id not in {'exec','eval','__import__'}


def test_nine_bindings_record_cutoffs_integrity_and_missing_lineage():
    report=read(OUT/'reports/PASS_T_BINDING_CAUSALITY_AUDIT.json')
    assert len(report['packs'])==9 and report['completion']=='NINE_PACK_AUDIT_COMPLETE'
    assert report['causal_verified']+report['causality_unverified']+report['noncausal']==9
    assert set(report['actual_inputs_read'])<=set(report['input_allowlist'])
    for row in report['packs']:
        assert row['claimed_binding_decision_frame']==row['latest_frame_in_recorded_selection_prefix']
        assert row['latest_frame_read_directly_by_binding_logic']>row['claimed_binding_decision_frame']
        assert row['latest_source_frame_that_may_influence_upstream']>=row['latest_frame_read_directly_by_binding_logic']
        assert row['binding_artifact_sha256'] and row['positive_provenance_evidence'] and row['missing_provenance_evidence']
        assert row['upstream_track_causality_status']=='CAUSALITY_UNVERIFIED'
        assert not row['noncausal_dependency_proven']
    assert report['causality_unverified']==9
    assert all(v==0 for v in report['runtime_counters'].values()) and all(v==0 for v in COUNTERS.values())

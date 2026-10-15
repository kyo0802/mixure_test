import copy
import pytest
from memory_graph.pass_t.external_dev.resolutions import current_dataset_view
from memory_graph.pass_t.external_dev.audit import RECONCILE, VISUAL, EXPOSURE
from memory_graph.pass_t.external_dev.security import json_bytes, digest, Blocked


def record(flags=None, full=True, reviewer='alpha', archive='a'*64):
    return {'record_id':'r','archive_sha256':archive,'annotation_item_id':'item','reviewer_id':reviewer,
            'review_round':1,'valid':True,'schema_valid':True,'category':'ACCEPTED_STRICT_NEGATIVE',
            'human_review_flags':flags or [RECONCILE],'human_review_pending':True,
            'quality_cleared_for_model_scoring':False,'exploratory_positive_quality_cleared':False,
            'response':{'window_outcome':'NO_CONFIRMED_EVENT','events':[]},
            'evaluation':{'full_window_event_evaluation_supported':full,'primary_full_window_metrics_eligible':full,
                          'supported_event_exploratory_use_allowed':False},'source':None}


def register(root, confirmed=True):
    folder=root/'artifacts/pass_t/phase2a/v2/review_resolutions';folder.mkdir(parents=True)
    note={'record_type':'PROJECT_OWNER_CLARIFICATION_NOT_ANNOTATION_SUBMISSION',
          'reviewer_ids':['alpha','alhpa'],'same_person_confirmed_by_owner':confirmed}
    (root/'note.json').write_bytes(json_bytes(note))
    registry={'schema_version':'PASS_T_REVIEWER_IDENTITY_RESOLUTION_V1','archive_sha256':'a'*64,
              'reviewer_ids':['alpha','alhpa'],'source_note_path':'note.json',
              'source_note_sha256':digest((root/'note.json').read_bytes())}
    (folder/'identity_v1.json').write_bytes(json_bytes(registry))


def test_missing_resolution_keeps_pending(tmp_path):
    assert current_dataset_view([record()],tmp_path)['summary']['quality_cleared_for_model_scoring']==0


def test_identity_only_gate_clear_not_visual_attestation(tmp_path):
    register(tmp_path);r=record();before=copy.deepcopy(r)
    data=current_dataset_view([r],tmp_path);out=data['records'][0]
    assert out['quality_cleared_for_model_scoring'] and not out['human_review_pending']
    assert out['reviewer_id']=='alpha' and r==before
    assert out['independent_visual_quality_review']=='NOT_ESTABLISHED_BY_IDENTITY_RESOLUTION'
    assert data['summary']['formal_eligible']==0 and data['views']['pending_manual_review']==[]
    assert data==current_dataset_view([r],tmp_path)


@pytest.mark.parametrize('flag',[VISUAL,EXPOSURE,'ADJUDICATION_PENDING'])
def test_other_pending_never_cleared(tmp_path,flag):
    register(tmp_path);out=current_dataset_view([record([RECONCILE,flag])],tmp_path)['records'][0]
    assert out['human_review_flags']==[flag] and not out['quality_cleared_for_model_scoring']


@pytest.mark.parametrize('kwargs',[{'reviewer':'other'},{'archive':'b'*64}])
def test_scope_is_exact(tmp_path,kwargs):
    register(tmp_path);out=current_dataset_view([record(**kwargs)],tmp_path)['records'][0]
    assert RECONCILE in out['human_review_flags']


def test_excluded_record_cannot_be_promoted(tmp_path):
    register(tmp_path);out=current_dataset_view([record(full=False)],tmp_path)['records'][0]
    assert not out['quality_cleared_for_model_scoring']


def test_tampered_note_blocks(tmp_path):
    register(tmp_path);(tmp_path/'note.json').write_bytes(b'{}')
    with pytest.raises(Blocked,match='HASH_MISMATCH'):current_dataset_view([record()],tmp_path)


def test_unconfirmed_note_blocks(tmp_path):
    register(tmp_path,False)
    with pytest.raises(Blocked,match='NOT_CONFIRMED'):current_dataset_view([record()],tmp_path)

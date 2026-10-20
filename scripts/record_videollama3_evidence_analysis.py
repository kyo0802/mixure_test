"""Record this task's assistant analysis separately from immutable human GT.

All notes below are retrospective report annotations, never model inputs or GT.
This script performs no inference, automatic physical adjudication or score.
"""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True
OUT=ROOT/'artifacts/pass_t/phase3/videollama3_full_v1'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
gt=ROOT/'artifacts/pass_t/phase2a/v2/external_returns/datasets/ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c/external_dev_gt.json'
side=ROOT/'artifacts/pass_t/phase2a/v2/exhaustive_reviews/adjudicated_7e28b9edf80a8e4da88caa66/adjudicated_dev_view.json'
notes={
 'test1__W03':{'target_identification':'PHONE_OMITTED; BASKETBALL_ONLY','before_after_state':'Selected phone frames compatible with surface support; model provides no phone states.','physical_event':'Human strict-negative reference; model strict-invalid, not an authoritative negative.','wrong_target_event_attribution':'NO_VALID_EVENT_CANDIDATE; distractor-focused observations.','unsupported_state_claims':'OTHER is unexplained alongside ON_SURFACE.','citation_quality':'All parsed aliases supplied; physical meaning of OTHER not established.','uncertainty':'Missing required uncertainty; no global identity established.','structured_output':'INVALID_SCHEMA'},
 'test2__W01':{'target_identification':'PHONE_CATEGORY_PRESENT; INSTANCE_IDENTITY_UNAUTHORIZED','before_after_state':'Phone ON_SURFACE is compatible with all eight selected frames.','physical_event':'NO_CONFIRMED_EVENT; compatible with existing target-specific strict-negative reference.','wrong_target_event_attribution':'NO_EVENT_CANDIDATE','unsupported_state_claims':'No definite unsupported phone state identified in these selected frames; no full-window verification claim.','citation_quality':'All eight supplied aliases; selected imagery supports phone surface observation.','uncertainty':'Per-object UNCERTAIN strings preserved; not a calibrated certainty measure.','structured_output':'FULL_STRICT_VALID'},
 'test5__W01':{'target_identification':'PHONE_OMITTED; BASKETBALL_ONLY','before_after_state':'Phone remains on surface in the eight selected images; model omits phone.','physical_event':'Human strict-negative reference; invalid output cannot support structured negative scoring.','wrong_target_event_attribution':'NO_VALID_EVENT_CANDIDATE','unsupported_state_claims':'OTHER at invented F0008 cannot be grounded.','citation_quality':'Seven unsupplied aliases in parsed content.','uncertainty':'Missing required uncertainty.','structured_output':'INVALID_SCHEMA_AND_UNSUPPLIED_ALIASES'},
 'test5__W05':{'target_identification':'NO_USABLE_PHONE_OBSERVATION','before_after_state':'Selected F0001/F0016/F0032 show phone at table; F0062/F0077 show phone held. Later occluded frames do not establish continued holding.','physical_event':'Existing human non-exhaustive PICKUP retained; model provides no usable hypothesis. Invalid is not NO_EVENT.','wrong_target_event_attribution':'NO_VALID_EVENT_CANDIDATE; raw prefix focuses on basketball.','unsupported_state_claims':'Malformed raw enumeration cannot support physical states.','citation_quality':'Raw lists aliases beyond the supplied eight; not parsed into authoritative citations.','uncertainty':'Output truncation is a generation failure of the contract, not deliberate abstention.','structured_output':'TOKEN_CAP_1024_INVALID_JSON'},
 'test7__W05':{'target_identification':'PHONE_OMITTED; BASKETBALL_ONLY','before_after_state':'F0001/F0016 phone at table; F0031/F0046 phone visibly held. Model omits this state change.','physical_event':'Existing human non-exhaustive PICKUP retained; no usable phone event hypothesis.','wrong_target_event_attribution':'NO_VALID_EVENT_CANDIDATE; no claim that wrong-target problem is solved.','unsupported_state_claims':'Later basketball OTHER lacks explanatory grounding.','citation_quality':'Aliases exist, but citations concern basketball rather than known phone transition.','uncertainty':'Missing uncertainty; does not explain later phone unobservability.','structured_output':'INVALID_SCHEMA'},
 'test8__W07':{'target_identification':'NO_OBJECT_OBSERVATIONS; NO_INSTANCE_BINDING','before_after_state':'No model states to assess.','physical_event':'Existing INSUFFICIENT_EVIDENCE must not be converted into exhaustive negative by the valid empty model output.','wrong_target_event_attribution':'NO_EVENT_CANDIDATE','unsupported_state_claims':'No states claimed; this is not evidence of successful physical reasoning.','citation_quality':'No citations; membership validation passes vacuously.','uncertainty':'NO_CONFIRMED_EVENT without visibility explanation does not establish appropriate abstention.','structured_output':'FULL_STRICT_VALID_EMPTY_OBSERVATIONS'}
}
extra={
 'test2__W08':'Assistant contact-sheet inspection: visible held phone called brush. Later phone visibility is obscured; all-frame HELD assertion not fully supported. No new event GT assigned.',
 'test8__W06':'Assistant contact-sheet inspection only; raw output is truncated and cannot be converted into a scored state/event. No new event GT assigned.',
 'test9__W03':'Assistant contact-sheet inspection only: raw calls hand HELD_BY_PERSON, malformed brackets and invented sequential aliases. No event GT assigned.'
}
lookup={}
for record in read(gt)['records']:
    item=read(ROOT/'artifacts/pass_t/phase2a/v2/items'/record['annotation_item_id']/'item.json')
    for pack in item['original_pack_ids']:lookup[pack]=(record,item)
rows=[]
for w in read(OUT/'dataset_inventory.json')['windows']:
    if w['availability']!='ELIGIBLE' or w['duplicate_of']:continue
    r=lookup.get(w['pack_id']);row={'window':w['pack_id'],'new_human_adjudication':False,'graph_write_authorized':False,'assistant_visual_review':w['pack_id'] in notes or w['pack_id'] in extra,'assistant_dimensions':notes.get(w['pack_id']),'assistant_extra_note':extra.get(w['pack_id'])}
    if r:
        record,item=r;row['existing_human_reference']={'annotation_item_id':record['annotation_item_id'],'response_sha256':record['response_sha256'],'window_outcome':record['response']['window_outcome'],'event_list_exhaustiveness':record['response'].get('event_list_exhaustiveness'),'event_types':[e['event_type'] for e in record['response']['events']],'formal_eligible':record['formal_eligible'],'quarantine_excluded':w['pack_id']=='test3__W07','original_evaluation':record['evaluation'],'sidecar_must_be_applied':w['pack_id'] in ('test5__W05','test7__W05')}
        row['evaluation_scope']='EXCLUDED_GT_QUARANTINE' if w['pack_id']=='test3__W07' else 'DESCRIPTIVE_REFERENCE_COMPARISON_ONLY'
    else:row['evaluation_scope']='NO_CONFIRMED_USABLE_EVENT_GT_UNREVIEWED_FOR_SCORING'
    rows.append(row)
result={'analysis_type':'ASSISTANT_VISUAL_AND_EXISTING_REFERENCE_ANALYSIS_NOT_NEW_HUMAN_GT','analysis_was_not_model_visible':True,'gt_sources':{str(p.relative_to(ROOT)):sha(p) for p in (gt,side)},'sidecar_status':read(side)['status'],'all_notes_are_retrospective_and_not_input_features':True,'records':rows,'formal_scores':None}
with (OUT/'physical_evidence_analysis.json').open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print('Recorded retrospective analysis:',len(rows),'unique inputs; human GT unchanged.')

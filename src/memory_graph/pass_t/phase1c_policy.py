"""Prospective local policy freeze; no human answers are inspected here."""
from .phase1c_common import OUT, read, write, sha, now

NAME='PASS_T_HUMAN_SEED_ELIGIBILITY_POLICY_V1'


def policy_definition():
    return {'policy_version':'HUMAN_SEED_ELIGIBILITY_V1',
            'target_strata':['SOURCE_RESOLVED','HUMAN_SEEDED','UNRESOLVED'],
            'binding_strata':['CAUSAL_VERIFIED','CAUSALITY_UNVERIFIED','NON_CAUSAL'],
            'binding_causality_scope':'original automatic seed binding; never changed by human choice',
            'allow_pre_window_seed_reference':True,
            'pre_window_reference_selection':'Up to three exact original-seed observations: first, binding frame if present, last strictly pre-window; distinct ascending indices.',
            'pre_window_reference_use':'REFERENCE_PRE_WINDOW only; never in-window evidence; any reliance is HUMAN_VISUAL_LOCALIZATION_ONLY',
            'uses':{'SOURCE_RESOLVED':{'engineering':True,'dev_preparation':True,'dev_exploratory':True,'formal_phase1c':False},
                    'HUMAN_SEEDED':{'engineering':True,'dev_preparation':'CONDITIONAL_ALL_REQUIREMENTS','dev_exploratory':'OWN_STRATUM','frozen_formal':False,'primary_source_metric':False},
                    'UNRESOLVED':{'dev_preparation':False,'formal_phase1c':False}},
            'human_dev_requirements':['authentic_valid_viewer_submission','SELECT_LOCAL_CANDIDATE',
                'existing_authorized_candidate','in_window_evidence_support','no_gt_or_future_leakage',
                'no_global_identity_claim','no_event_label_exposure','no_event_dependent_selection',
                'provenance_recorded','no_unresolved_contradictory_evidence','HUMAN_SEEDED_stratum'],
            'source_unverified_dev_eligible':True,'source_unverified_formal_eligible':False,
            'trusted_global_identity_merge_from_seed':False,'trusted_graph_write_from_seed':False,
            'formal_evaluation_eligible_phase1c':False,'review_case_limit':7,
            'future_formal_exception':'Requires a separately pre-registered protocol, independent review, separate strata/denominators and no post-hoc promotion.'}


def wrapper_schema():
    string={'type':'string','minLength':1}
    strings={'type':'array','uniqueItems':True,'items':string}
    details={'review_decision':{'enum':['SELECT_LOCAL_CANDIDATE','UNRESOLVED','NO_VISIBLE_TARGET','MULTIPLE_PLAUSIBLE_TARGETS']},
             'selected_local_candidate_id':{'type':['string','null']},'reviewed_frame_ids':strings,
             'supporting_observation_ids':strings,'source_provenance_references':strings,
             'provenance_support':{'enum':['RECORDED_PROVENANCE_EDGE','HUMAN_VISUAL_LOCALIZATION_ONLY','NONE']},
             'rationale':string,'uncertainty_status':{'enum':['LOCAL_SELECTION_ONLY','UNCERTAIN','UNRESOLVED']},
             'reference_material_used':strings,'contradictory_candidate_evidence':{'type':'boolean'}}
    attest={'human_attestation':{'const':True},'event_labels_viewed_for_this_pack':{'type':'boolean'},
            'selection_depends_on_event_interpretation':{'type':'boolean'},'claims_global_identity':{'type':'boolean'}}
    submit={'submitted_via':{'const':'human_seed_review_viewer'},'automatic_timestamp_utc':{'type':'string','format':'date-time'},
            'timestamp_recorded_automatically':{'const':True},'submission_id':string,
            'policy_md_sha256':string,'policy_json_sha256':string,'review_item_sha256':string}
    def obj(properties):return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    return {'$schema':'https://json-schema.org/draft/2020-12/schema',**obj({
            'schema_version':{'const':'HUMAN_SEED_REVIEW_WRAPPER_V1'},'primary_response':{'type':'object'},
            'details':obj(details),'attestations':obj(attest),'submission':obj(submit)}),
            'description':'Primary response is separately validated against the unchanged frozen response schema.'}


def freeze():
    pre=read(OUT/'manifests/phase1c_preflight.json')
    if pre['preservation']!='PASS' or pre['baseline_tests']['tests']!=174:
        raise ValueError('Preflight/baseline not verified')
    base=OUT/'contracts'
    if (base/(NAME+'.freeze_receipt.json')).exists():
        return verify_freeze()
    md='''# HUMAN_SEEDED eligibility policy v1

Frozen before inspecting new review answers. Source-resolved local provenance, human-selected localization, automatic binding causality and global physical identity are separate.

| Use | SOURCE_RESOLVED | HUMAN_SEEDED |
|---|---|---|
| Engineering diagnostics | Allowed | Allowed |
| DEV preparation | Own stratum; unverified causality permitted | Own stratum, only all requirements below |
| DEV exploratory comparison | Own stratum | Own stratum |
| Frozen formal / primary source-resolved metric | Future protocol only; never Phase1c | Not allowed by default |
| Trusted global identity or Memory Graph | Never from seed alone | Never from seed alone |

SOURCE_RESOLVED with CAUSALITY_UNVERIFIED is DEV eligible, not formal eligible. Binding causality always refers to the original automatic seed and cannot be upgraded by human localization. NON_CAUSAL dependency findings are recorded separately; no formal promotion.

HUMAN_SEEDED DEV eligibility requires an authentic, schema-valid viewer submission; explicit candidate selection; existing authorized candidate; exact in-window frame/observation support; recorded provenance and rationale; no GT/future leakage; no global identity claim; no event-label exposure or event-dependent selection; no contradictory evidence; explicit HUMAN_SEEDED stratum. A visually plausible phone cannot create a recorded provenance edge. Human localization can be used in DEV only if the intended target is defensibly localized from authorized references; otherwise UNRESOLVED.

Attestations with event_labels_viewed_for_this_pack=true, selection_depends_on_event_interpretation=true or claims_global_identity=true remain valid records but are not seed-eligible. All four decisions count as completed review when authentic/valid; unresolved is legitimate.

allow_pre_window_seed_reference=true. Show at most three exact original-seed observations (first, binding if present, last strictly before start). REFERENCE_PRE_WINDOW crops are separate references, never in-window evidence. Reliance on them requires HUMAN_VISUAL_LOCALIZATION_ONLY. No at/after-window-end material, GT, event hints, prior labels, scores or full source-video paths enter the viewer.

Exactly seven cases. Human-seeded formal inclusion requires a separately pre-registered protocol, independent review, explicit strata/metrics and no post-hoc promotion. No exception is activated here.

Freeze evidence is local file hashes + UTC receipt, not an externally anchored commit. Viewer controls detect accidental unauthentic submissions but cannot cryptographically prove human authorship.
'''
    write(base/(NAME+'.md'),md,exclusive=True)
    write(base/(NAME+'.json'),policy_definition(),exclusive=True)
    write(base/'PASS_T_HUMAN_SEED_REVIEW_WRAPPER_SCHEMA_V1.json',wrapper_schema(),exclusive=True)
    receipt={'policy_version':policy_definition()['policy_version'],'created_at_utc':now(),
             'policy_md_sha256':sha(base/(NAME+'.md')),'policy_json_sha256':sha(base/(NAME+'.json')),
             'source_schemas':{p.name:sha(p) for p in [base/'PASS_T_HUMAN_SEED_RESPONSE_SCHEMA_V1.json',
                                                     base/'PASS_T_HUMAN_SEED_REVIEW_WRAPPER_SCHEMA_V1.json']},
             'repository_commit':pre['HEAD'],'human_responses_existed_before_creation':pre['responses_existed_before_freeze'],
             'response_candidates_before_creation':pre['authentic_response_candidates_before_freeze'],
             'excluded_old_gpt_test_fixtures':pre['excluded_fixture_response_files'],
             'prospective_pre_registration':not pre['responses_existed_before_freeze'],
             'allow_pre_window_seed_reference':True,'proof_limitation':'Local receipt only; no commit or external timestamp anchor.'}
    write(base/(NAME+'.freeze_receipt.json'),receipt,exclusive=True)
    return receipt


def verify_freeze():
    base=OUT/'contracts';receipt=read(base/(NAME+'.freeze_receipt.json'))
    if sha(base/(NAME+'.md'))!=receipt['policy_md_sha256'] or sha(base/(NAME+'.json'))!=receipt['policy_json_sha256']:
        raise ValueError('Frozen policy hash changed; do not promote reviewed cases')
    for path,h in receipt['source_schemas'].items():
        if sha(base/path)!=h:raise ValueError('Frozen referenced schema changed')
    return receipt

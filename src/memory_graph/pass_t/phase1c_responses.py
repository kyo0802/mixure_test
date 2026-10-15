"""Read-only response validation and eligibility; only the viewer writes answers."""
from datetime import datetime, timezone
from jsonschema import Draft202012Validator, FormatChecker
from .phase1c_common import OUT, read, sha
from .phase1c_policy import verify_freeze


def validate_response(value,item,receipt,primary_schema,companion_schema,item_hash):
    errors=[]
    for schema,record in [(companion_schema,value),(primary_schema,value.get('primary_response',{}))]:
        errors += [e.message for e in Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(record)]
    if errors:return {'valid':False,'errors':errors,'human_seed_eligible':False,'dev_eligible':False,'formal_evaluation_eligible':False}
    p=value['primary_response'];d=value['details'];a=value['attestations'];s=value['submission']
    frames={f['frame_id']:f for f in item['frames']};references={r['reference_id'] for r in item['references']}
    candidates={c['candidate_id']:c for c in item['candidates']}
    if p['pack_id']!=item['pack_id']:errors.append('Pack ID mismatch')
    if not p['annotator_id'].strip() or not d['rationale'].strip():errors.append('Reviewer ID and rationale required')
    if p['notes']!=d['rationale']:errors.append('Rationale mapping mismatch')
    if set(d['reviewed_frame_ids'])-frames.keys():errors.append('Unauthorized evidence frame')
    if not d['reviewed_frame_ids']:errors.append('At least one actual reviewed in-window frame required by frozen v1')
    if not set(d['reference_material_used'])<=references:errors.append('Unauthorized reference material')
    cited=[frames[x] for x in d['reviewed_frame_ids'] if x in frames]
    if p['frames_reviewed']!=[f['source_frame_index'] for f in cited]:errors.append('Primary/source frame mapping mismatch')
    if any(not item['window_start_s']<=f['source_timestamp_s']<item['window_end_s'] for f in cited):errors.append('Future or outside-window evidence')
    if not set(d['source_provenance_references'])<=set(item['source_provenance_references']):errors.append('Unauthorized provenance reference')
    if not d['source_provenance_references']:errors.append('Source provenance reference required')
    if p['timestamp']!=s['automatic_timestamp_utc']:errors.append('Automatic timestamp mismatch')
    try:
        stamp=datetime.fromisoformat(s['automatic_timestamp_utc'])
        if stamp.tzinfo is None or stamp.utcoffset().total_seconds()!=0:errors.append('UTC timestamp required')
        if stamp<datetime.fromisoformat(receipt['created_at_utc']):errors.append('Response precedes policy freeze')
    except (TypeError,ValueError):errors.append('Invalid automatic UTC timestamp')
    for key in ['policy_md_sha256','policy_json_sha256']:
        if s[key]!=receipt[key]:errors.append('Frozen policy receipt mismatch')
    if s['review_item_sha256']!=item_hash:errors.append('Review item hash mismatch')
    selected=d['review_decision']=='SELECT_LOCAL_CANDIDATE';id_=d['selected_local_candidate_id']
    mapping='SELECTED_CANDIDATE' if selected else d['review_decision']
    if p['answer_type']!=mapping or p['selected_local_track_id']!=id_:errors.append('Frozen primary decision mapping mismatch')
    if selected:
        candidate=candidates.get(id_)
        if candidate is None:errors.append('Selected candidate not in authorized inventory')
        else:
            cited_ids={f['frame_id'] for f in cited}
            if not cited_ids.intersection(candidate['evidence_frame_ids']):errors.append('Selection needs exact observed candidate evidence')
            obs={o['observation_id']:o for o in item['observations'] if o['candidate_id']==id_}
            if not d['supporting_observation_ids']:errors.append('Exact supporting observation references required')
            for observation_id in d['supporting_observation_ids']:
                if observation_id not in obs or f"S{obs[observation_id]['source_frame_index']:06d}" not in cited_ids:
                    errors.append('Observation is not the selected candidate on a cited frame')
                elif obs[observation_id]['provenance_reference'] not in d['source_provenance_references']:
                    errors.append('Supporting observation provenance must be cited')
            if d['provenance_support']=='RECORDED_PROVENANCE_EDGE' and not candidate['recorded_provenance_edges']:
                errors.append('Human cannot invent a recorded provenance edge')
            if d['reference_material_used'] and d['provenance_support']!='HUMAN_VISUAL_LOCALIZATION_ONLY':
                errors.append('Pre-window reference reliance must remain human visual localization only')
    else:
        if id_ is not None:errors.append('Nonselection must not contain a selected ID')
        allowed={o['observation_id']:o for o in item['observations']}
        for id_ in d['supporting_observation_ids']:
            if id_ not in allowed or f"S{allowed[id_]['source_frame_index']:06d}" not in d['reviewed_frame_ids']:
                errors.append('Unknown or uncited observation reference')
    reasons=[]
    if a['event_labels_viewed_for_this_pack']:reasons.append('EVENT_LABEL_EXPOSURE')
    if a['selection_depends_on_event_interpretation']:reasons.append('EVENT_DEPENDENT_SELECTION')
    if a['claims_global_identity']:reasons.append('UNSUPPORTED_GLOBAL_IDENTITY_CLAIM')
    if d['contradictory_candidate_evidence']:reasons.append('CONTRADICTORY_CANDIDATE_EVIDENCE')
    if d['provenance_support']=='NONE' and selected:reasons.append('NO_PROVENANCE_SUPPORT')
    if selected and d['uncertainty_status']!='LOCAL_SELECTION_ONLY':reasons.append('LOCAL_SELECTION_STILL_UNCERTAIN')
    if selected and d['provenance_support']=='HUMAN_VISUAL_LOCALIZATION_ONLY' and not d['reference_material_used']:
        reasons.append('INTENDED_TARGET_REFERENCE_NOT_ESTABLISHED')
    if not selected:reasons.append('NO_UNIQUE_HUMAN_SELECTION')
    valid=not errors;eligible=valid and selected and not reasons
    return {'valid':valid,'errors':errors,'review_completed':valid,'human_seed_eligible':eligible,
            'dev_eligible':eligible,'formal_evaluation_eligible':False,
            'target_source':'HUMAN_SEEDED' if eligible else 'UNRESOLVED',
            'binding_causality':item['binding_causality'],'ineligibility_reasons':reasons,
            'global_identity_authority':False,'trusted_graph_write':False}


def load_reviews():
    receipt=verify_freeze();base=OUT/'human_seed_review';manifest=read(base/'review_manifest.json')
    primary=read(OUT/'contracts/PASS_T_HUMAN_SEED_RESPONSE_SCHEMA_V1.json')
    companion=read(OUT/'contracts/PASS_T_HUMAN_SEED_REVIEW_WRAPPER_SCHEMA_V1.json')
    grouped={e['pack_id']:[] for e in manifest['items']};unknown=[]
    for path in sorted((base/'responses').glob('*.json')):
        try:
            value=read(path);id_=value.get('primary_response',{}).get('pack_id')
            entry={'response_path':path.relative_to(OUT).as_posix(),'sha256':sha(path),'response':value}
            if id_ in grouped:grouped[id_].append(entry)
            else:unknown.append({'response_path':entry['response_path'],'error':'Unknown pack'})
        except (ValueError,TypeError) as exc:unknown.append({'response_path':str(path.name),'error':str(exc)})
    results=[]
    for entry in manifest['items']:
        id_=entry['pack_id'];item_path=base/entry['item_path'];item=read(item_path)
        if sha(item_path)!=entry['item_sha256']:raise ValueError('Review package changed; validation blocked')
        responses=grouped[id_]
        common={'pack_id':id_,'original_resolution':entry['original_resolution'],
                'binding_causality':item['binding_causality'],'overlap_group_id':entry['overlap_group_id'],
                'review_decision':None,'selected_local_candidate':None,'evidence_frame_ids':[],
                'provenance_support':'NONE','human_seed_eligibility':False,'dev_eligible':False,
                'formal_evaluation_eligible':False,'target_source':'UNRESOLVED'}
        if not responses:
            results.append({**common,'human_review_status':'UNREVIEWED','remaining_uncertainty':'Await authentic human submission'})
        elif len(responses)>1:
            results.append({**common,'human_review_status':'DUPLICATE_RESPONSES_BLOCKED','remaining_uncertainty':'Manual correction required; originals preserved',
                            'response_files':[{k:v for k,v in r.items() if k!='response'} for r in responses]})
        else:
            response=responses[0];validation=validate_response(response['response'],item,receipt,primary,companion,entry['item_sha256'])
            d=response['response'].get('details',{})
            results.append({**common,**validation,'human_seed_eligibility':validation['human_seed_eligible'],
                            'human_review_status':'COMPLETE' if validation['valid'] else 'INVALID_RESPONSE',
                            'review_decision':d.get('review_decision'),'selected_local_candidate':d.get('selected_local_candidate_id'),
                            'evidence_frame_ids':d.get('reviewed_frame_ids',[]),'provenance_support':d.get('provenance_support','NONE'),
                            'remaining_uncertainty':validation.get('errors') or validation.get('ineligibility_reasons') or ['Local localization only; no global identity proof'],
                            'response_path':response['response_path'],'response_sha256':response['sha256']})
    return {'items':results,'unknown_or_unreadable_responses':unknown,
            'completed':sum(r['human_review_status']=='COMPLETE' for r in results),
            'human_seeded_valid':sum(r['human_seed_eligibility'] for r in results),
            'dev_eligible':sum(r['dev_eligible'] for r in results),'formal_eligible':0,
            'responses_present':sum(len(x) for x in grouped.values())+len(unknown),
            'authenticity_limitation':'Attestation/viewer metadata are not cryptographic proof of human authorship.'}

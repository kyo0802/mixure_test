"""Synthetic contract cases, never derived from development pack labels."""
from copy import deepcopy
from .contracts import baseline, unknown_state
from .sampling import sample,make_manifest,bundle_from_manifest


def context():
    source=[{'source_frame_index':i,'timestamp_s':i/3,'sha256':'0'*64,
             'timestamp_provenance':'DERIVED_FPS'} for i in range(12)]
    picked,info=sample(source,0.,4.)
    unit={'event_window_id':'synthetic_window','session_id':'synthetic_session','source_video_id':'synthetic_source',
          'source_video_hash':None,'target_local_id':'synthetic_track','window_start_s':0.,'window_end_s':4.,'target_fps':3.}
    m=make_manifest(unit,picked,info)
    return m,bundle_from_manifest(m,'B','0'*64,['P1','P2'],['A1'])


def relation(predicate='ON',anchor='A1'):
    return {'predicate':predicate,'anchor_local_id':anchor,'anchor_label':None,
            'reference_frame':'PHYSICAL_SCENE','evidence_frame_ids':['F009']}


def event(action, start=.5, end=1., actor='P1', receiver=None):
    return {'action':action,'actor_local_id':actor,'receiver_local_id':receiver,'target_local_id':'T1',
            'evidence_frame_ids':['F002','F003'],'onset_interval_s':[start,start],
            'offset_interval_s':[end,end],'boundary_status':'BRACKETED','boundary_reason':None,
            'relation':relation() if action=='PLACE' else None,'support_class':'DIRECT'}


def observe(value, sm, support='DIRECT', reason=None):
    x=deepcopy(value);x.pop('support_class',None)
    x.update(observable_in_full_window=True,
             sampled_observability={sm:{'support_class':support,'unobservable_reason':reason}},
             unobservable_reason=reason)
    return x


def prediction(actions=(), assessment=None, visibility='UNKNOWN'):
    m,b=context();p=baseline(b,4.)
    p['events']=deepcopy(list(actions));p['event_assessment']=assessment or ('EVENTS_OBSERVED' if actions else 'CONFIRMED_NONE')
    p['unresolved_transitions']=[] if p['event_assessment'] in {'EVENTS_OBSERVED','CONFIRMED_NONE'} else ['FINAL_STATE']
    p['current_visibility_at_window_end']=visibility
    p['visibility_evidence_frame_ids']=['F011'] if visibility!='UNKNOWN' else []
    return p


def gt_from_prediction(p,sm,coverage=True):
    g=deepcopy(p);g['events']=[observe(e,sm) for e in p['events']]
    s=observe(p['last_confirmed_state'],sm)
    if s['confirmation_status']=='NEVER_CONFIRMED':
        s['observable_in_full_window']=False;s['sampled_observability'][sm]={'support_class':'UNSUPPORTED','unobservable_reason':'OTHER'}
    g.update(event_window_id='synthetic_window',session_id='synthetic_session',window_start_s=0.,window_end_s=4.,
             target_valid=True,adequate_observable_coverage=coverage,
             reference_frames=[{'frame_id':f'F{i:03d}','source_timestamp_s':i/3} for i in range(12)],
             last_confirmed_state=s,provenance={'annotator_id':'fixture','timestamp_utc':'synthetic','tool_version':'v1'},adjudication=None)
    return g


def cases():
    m,b=context();sm=m['sampling_manifest_id']
    picked=prediction([event('PICK_UP',.5,1),event('MOVE_WHILE_HELD',1.5,2)])
    placed=prediction([event('PLACE',2,2.5),event('RELEASE',2.4,2.6)])
    placed['last_confirmed_state']={'confirmation_status':'CONFIRMED','confirmed_at_s':3.,
        'evidence_frame_ids':['F009'],'holder_status':'NOT_HELD','holder_local_id':None,'relation':relation()}
    held=prediction([], 'CONFIRMED_NONE','OCCLUDED')
    held['last_confirmed_state']={'confirmation_status':'CONFIRMED','confirmed_at_s':2.,'evidence_frame_ids':['F006'],
        'holder_status':'HELD_BY_PERSON','holder_local_id':'P1','relation':relation('HELD_BY','P1')}
    held['last_confirmed_state']['relation']['evidence_frame_ids']=['F006']
    leaving=deepcopy(held);leaving['current_visibility_at_window_end']='OUT_OF_VIEW'
    none=prediction();indeterminate=prediction([], 'INDETERMINATE')
    missed=gt_from_prediction(prediction([event('PICK_UP')]),sm)
    missed['events'][0]['sampled_observability'][sm]={'support_class':'UNSUPPORTED','unobservable_reason':'SAMPLING_MISSED'}
    handoff=prediction([event('HANDOFF',1,1.5,'P1','P2')])
    unknown=deepcopy(placed);unknown['last_confirmed_state']['holder_status']='UNKNOWN'
    prototypes={'pickup_then_move':picked,'place_release':placed,'held_before_occlusion':held,
                'out_of_view':leaving,'no_event':none,'indeterminate':indeterminate,
                'handoff':handoff,'unknown_holder':unknown,'never_confirmed':indeterminate}
    rows=[{'case_id':name,'bundle':deepcopy(b),'gt':gt_from_prediction(p,sm,coverage=name!='indeterminate'),
           'prediction':p} for name,p in prototypes.items()]
    rows.append({'case_id':'sampling_missed','bundle':deepcopy(b),'gt':missed,'prediction':prediction([], 'INDETERMINATE')})
    return rows

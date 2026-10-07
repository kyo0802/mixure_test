"""Explicit experiment runner; scenario labels never enter identity inference."""
from dataclasses import asdict
from collections import defaultdict,Counter
import time
import numpy as np
from PIL import Image
from memory_graph.identity.contracts import Observation,Policy
from memory_graph.v296_reid.epochs import CandidateEpochBuilder,EpochPolicy
from memory_graph.v296_reid.evidence import ConfirmationPolicy
from memory_graph.v296_reid.appearance import photometric_veto
from memory_graph.v296_reid.runner import audit_confirmations
from .io import ROOT,OUT,PREV,OLD,read,save,sha
from .inputs import prepare,visual_namespace,feature_provider,lightglue
from .physical import PhysicalIdentityState,PhysicalPolicy,compact
from .person import PersonEpochBuilder,PersonPolicy,CameraCompensator
from .guard import V297IdentityGuard

def config():return read(OUT/'calibration/parameters.json')
def source_hashes():
    files=[]
    for name in ['v297_physical_identity','v296_reid','v295_reid','identity','events','reasoning']:files+=list((ROOT/f'src/memory_graph/{name}').glob('*.py'))
    files+=list((ROOT/'configs').rglob('*.yaml'))+list((ROOT/'scripts').glob('*v297*.py'))+[ROOT/'scripts/run_findmind.py',ROOT/'tests/test_v297_identity.py']
    return {p.relative_to(ROOT).as_posix():sha(p) for p in files}
def freeze():
    if (OUT/'FROZEN_V297_POLICY_MANIFEST.json').exists():raise FileExistsError('Already frozen')
    files=list((OUT/'development_gt').glob('*.json'))+[OUT/'development_gt/DEVELOPMENT_SCENARIO_ACCEPTANCE.md']+list((OUT/'calibration').glob('*.json'))+[OUT/'person_epochs/policy.json',OUT/'physical_identity/state_policy.json',OUT/'interaction/state_machine.json']
    files+=list((OUT/'inputs').glob('test*/*.json'))
    f={'created_unix':time.time(),'source_hashes':source_hashes(),'frozen_artifacts':{p.relative_to(ROOT).as_posix():sha(p) for p in files},
        'model_revisions':{n:read(OLD/f'setup/{n}_model.json')['revision'] for n in ['dinov3','dinov2']},'development_metrics_sha256':sha(OUT/'development/identity_metrics.json'),
        'development_scenarios_sha256':sha(OUT/'development/scenario_results.json'),'scope':'Before val1–11 known regression; no later policy tuning'}
    save(OUT/'FROZEN_V297_POLICY_MANIFEST.json',f);save(OUT/'calibration/frozen_policy_manifest.json',f)
def verify_freeze():
    f=read(OUT/'FROZEN_V297_POLICY_MANIFEST.json')
    if not f or f['source_hashes']!=source_hashes() or any(not (ROOT/p).is_file() or sha(ROOT/p)!=h for p,h in f['frozen_artifacts'].items()):raise ValueError('Frozen source/config/scenario drift')
    if read(OUT/'calibration/frozen_policy_manifest.json')!=f:raise ValueError('Freeze mirror drift')

def replay(video_id,dest,rows=None,frames=None):
    if (dest/'metrics.json').exists():return read(dest/'metrics.json')
    if rows is None:rows,frames=prepare(video_id)
    cfg=config();vp=ConfirmationPolicy(**cfg['confirmation']);physical=PhysicalIdentityState('phone_01',PhysicalPolicy(**cfg['physical']))
    person=PersonEpochBuilder(video_id,PersonPolicy(**cfg['person']));camera=CameraCompensator(**cfg['camera']);epoch=CandidateEpochBuilder(video_id,EpochPolicy(**cfg['epoch']))
    metadata={};byframe=defaultdict(list)
    for r in rows:byframe[r['frame']].append(r)
    all_physical=[];latencies=[];start=time.perf_counter()
    with visual_namespace():
        provider=feature_provider(video_id,rows);verifier=lightglue(cfg['geometry'])
        g=V297IdentityGuard(Policy(admission_similarity=vp.admission),vp,metadata,lambda r:provider.vector('dinov2',r),verifier.verify,
            lambda r,core:photometric_veto(r['photometric'],[b['photometric'] for b in core if b.get('active',True)],vp.photometric_threshold),physical)
        try:
            for f in frames:
                t=time.perf_counter();current=[{**r,'v3':list(provider.vector('dinov3',r))} for r in byframe[f['frame']]]
                current=epoch.process(current,allow_stitch=g._bound);context={**f,'scene_ok':f.get('scene_ok',True) and not any(r.get('scene_break') for r in current)}
                people=person.process(f['time'],[{**a,'frame':f['frame']} for a in f['anchors'] if a['raw_label']=='person'],f['image_size'],not context['scene_ok']);cam=camera.update(context)
                physical.begin_frame(context,people,cam,current);obs=[]
                for r in current:
                    metadata[r['observation_id']]=r;all_physical.append(r['physical_identity_evidence'])
                    obs.append(Observation(r['observation_id'],r['candidate_epoch_id'],r['frame'],r['time'],tuple(r['bbox']),r['label'],r['confidence'],r['provenance']+'#V297CandidateEpoch='+r['candidate_epoch_id'],vector=tuple(r['v3']),source=r['source'],sam_overlap=r['sam_overlap'],drift=r['drift'],scene_break=r['scene_break']))
                g.process(f['time'],obs);physical.prune_aliases({a['alias_id'] for a in g._aliases if a['status']=='CONFIRMED'})
                current_ledger=[r for r in g._ledger if r['active'] and r['observation']['frame']==f['frame'] and r['alias_id'] in {a['alias_id'] for a in g._aliases if a['status']=='CONFIRMED'}]
                if current_ledger:
                    r=current_ledger[-1];physical.authorized(metadata[r['observation']['observation_id']],r)
                latencies.append(time.perf_counter()-t)
            snap=g.snapshot();finalledger=g.final_ledger();auth={x['observation']['frame']:x for x in finalledger};final=[]
            for f in frames:
                a=auth.get(f['frame']);o=a['observation'] if a else None;maskref=None
                if o:
                    r=metadata[o['observation_id']]
                    if r.get('foreground_mask_path'):
                        w,h=r['canonical_metadata']['source_dimensions'];mask=Image.new('L',(w,h));x,y,_,_=r['canonical_metadata']['crop_bounds'];mask.paste(Image.open(r['foreground_mask_path']),(x,y));p=dest/f'masks/f{f["frame"]:06d}.png';p.parent.mkdir(parents=True,exist_ok=True);mask.save(p);maskref=p.relative_to(ROOT).as_posix()
                final.append({**f,'identity_authorized':bool(a),'target_bbox':o['bbox'] if o else None,'chain_id':f'epoch:{a["epoch_id"]}' if a else None,'mask_reference':maskref,
                    'upstream_identity_state':'AUTHORIZED' if a else 'UNRESOLVED','source':'final_revocation_filtered_ledger','target_authorization_provenance':[a['authorization_id'],a['alias_id']] if a else []})
            audit=audit_confirmations(snap,metadata);resources=provider.close();provider=None
            violations=[]
            for a in snap['confirmation_audit']:
                p=a['physical_identity']
                if p['known_distinct'] or p['preexistence_contradiction'] or p['reachability']=='PHYSICALLY_INCONSISTENT' or a['confirmation_context'] not in ['CONTINUITY_RECOVERY','INTERACTION_CONDITIONED_RECOVERY'] or not p['unique_physical_support']:violations.append(a['current_observation'])
            audit['physical_identity_violations']=violations
            initial=snap['aliases'][0] if snap['aliases'] else None;local=metadata[initial['evidence_refs'][0]]['local_track_id'] if initial else None
            physical_counts={key:dict(Counter(p[key] for p in all_physical)) for key in ['reachability','interaction','candidate_preexistence_result','single_phone_state']}
            m={'initial_binding':bool(initial),'initial_local_track':local,'initial_frame':initial['confirmation_frame'] if initial else None,
                'authorized_observations':len(auth),'unresolved_candidate_frames':sum(r['candidate_present'] and not r['identity_authorized'] for r in final),
                'confirmed_recoveries':len(snap['confirmation_audit']),'continuity_confirmations':sum(a['confirmation_context']=='CONTINUITY_RECOVERY' for a in snap['confirmation_audit']),
                'interaction_conditioned_confirmations':sum(a['confirmation_context']=='INTERACTION_CONDITIONED_RECOVERY' for a in snap['confirmation_audit']),
                'ambiguous_appearance_only_long_gap_cases':sum(d['appearance_only_long_gap'] and d['decision']=='AMBIGUOUS' for d in g.physical_decisions),
                'backfilled_observations':sum(len(a['backfilled_observation_ids']) for a in snap['backfill_events']),'physical_counts':physical_counts,
                'known_distinct_entity_vetoes':sum(d['physical_identity']['known_distinct'] for d in g.physical_decisions),'candidate_preexistence_vetoes':sum(d['physical_identity']['preexistence_contradiction'] for d in g.physical_decisions),
                'known_distinct_records':len(physical.known_distinct),'motion_coupled_authorized_frames':sum(e['state']=='TARGET_MOTION_COUPLED_WITH_PERSON' for e in physical.events),
                'person_near_events':sum(e['state'] in ['TARGET_NEAR_PERSON','TARGET_MOTION_COUPLED_WITH_PERSON'] for e in physical.events),
                'occlusion_hypotheses':sum(e['state']=='TARGET_OCCLUDED_WITH_PERSON_HYPOTHESIS' for e in physical.events),'camera_reliable_frames':sum(c['reliable'] for c in camera.results),'sampled_frames':len(frames),
                'decision_counts':dict(Counter(d['decision'] for d in snap['decisions'])),'epoch_counts':dict(Counter(e['kind'] for e in epoch.events)),
                'unauthorized_writes':sum(not any(t['authorization_id']==r['authorization_id'] and 'AUTHORIZE_OBSERVATION' in t['capabilities'] for t in snap['authorizations']) for r in finalledger),
                'integrity_violation_counts':audit['violation_counts'],'physical_identity_violations':len(violations),'wall_seconds':time.perf_counter()-start,
                'frame_mean_seconds':float(np.mean(latencies)),'frame_p95_seconds':float(np.quantile(latencies,.95)),'feature_resources':resources,'runtime_labels_read':False,
                'video_sha256':read(OUT/f'inputs/{video_id}/source.json')['video_sha256']}
            import torch,psutil
            m['peak_cuda_allocated_bytes']=torch.cuda.max_memory_allocated();m['RSS_end_bytes']=psutil.Process().memory_info().rss
            for p,value in [('identity.json',snap),('authorized_rows.json',final),('candidate_epochs.json',epoch.snapshot()),('person_epochs.json',person.snapshot()),('confirmation_audit.json',audit),('physical_evidence.json',all_physical),('camera_compensation.json',camera.results),('metrics.json',m),('LightGlue.json',verifier.results)]:save(dest/p,value)
            save(dest/'metadata.json',{k:compact(v) for k,v in metadata.items()});return m
        finally:
            if provider:provider.close()
            verifier.close()

def run_set(kind):
    val=kind=='known_val_regression'
    if val:verify_freeze()
    ids=[f'val_{i}' for i in range(1,12)] if val else [f'test{i}' for i in range(1,10)];results={}
    for vid in ids:
        m=replay(vid,OUT/f'{kind}/runs/{vid}');results[vid]=m
        print(kind,vid,'authorized',m['authorized_observations'],'continuity/interaction',m['continuity_confirmations'],m['interaction_conditioned_confirmations'],'known-distinct vetoes',m['known_distinct_entity_vetoes'],flush=True)
    keys=['authorized_observations','unresolved_candidate_frames','confirmed_recoveries','continuity_confirmations','interaction_conditioned_confirmations','ambiguous_appearance_only_long_gap_cases','backfilled_observations','known_distinct_entity_vetoes','candidate_preexistence_vetoes','known_distinct_records','occlusion_hypotheses','unauthorized_writes','physical_identity_violations','wall_seconds']
    result={'scope':'POST-VALIDATION KNOWN REGRESSION ONLY' if val else 'DEVELOPMENT','videos':results,'totals':{k:sum(m[k] for m in results.values()) for k in keys}}
    save(OUT/f'{kind}/{"metrics" if val else "identity_metrics"}.json',result);return result

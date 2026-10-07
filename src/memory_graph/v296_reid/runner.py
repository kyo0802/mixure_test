"""Explicit opt-in experiment; never imports labels into identity decisions."""
from dataclasses import asdict
from collections import defaultdict,Counter
from pathlib import Path
import time
import numpy as np
from PIL import Image
from memory_graph.identity.contracts import Observation,Policy
from .io import ROOT,OUT,OLD,read,save,sha
from .appearance import validate_original,FeatureProvider,photometric_veto
from .epochs import CandidateEpochBuilder,EpochPolicy
from .evidence import ConfirmationPolicy
from .guard import V296IdentityGuard
from .geometry import CurrentLightGlue
from .integrity import FLAGS,clean,provenance

def parameters():return read(OUT/'calibration/parameters.json')
def source_hashes():
    files=list((ROOT/'src/memory_graph/v296_reid').glob('*.py'))+list((ROOT/'src/memory_graph/identity').glob('*.py'))+list((ROOT/'src/memory_graph/v295_reid').glob('*.py'))
    files+=[ROOT/'scripts/run_v296_reid.py',ROOT/'scripts/run_findmind.py',ROOT/'tests/test_v296_reid.py']
    for folder in ['events','reasoning']:files+=list((ROOT/f'src/memory_graph/{folder}').glob('*.py'))
    files+=list((ROOT/'configs').rglob('*.yaml'))
    return {p.relative_to(ROOT).as_posix():sha(p) for p in files}
def freeze():
    dest=OUT/'calibration/frozen_policy_manifest.json'
    if dest.exists():raise FileExistsError('Already frozen')
    artifacts=list((OUT/'calibration').glob('*.json'))+[OUT/'candidate_epochs/policy.json',OUT/'lightglue/policy.json']
    artifacts+=list((OUT/'inputs').glob('test*/*.json'))
    for name in ['dinov3','dinov2']:
        artifacts+=list((OLD/f'benchmark/embeddings/{name}').glob('test*.npz'))
        artifacts+=list((OLD/f'benchmark/embeddings/{name}').glob('test*.json'))
    save(dest,{'created_unix':time.time(),'source_hashes':source_hashes(),'parameters_sha256':sha(OUT/'calibration/parameters.json'),
        'frozen_artifacts':{p.relative_to(ROOT).as_posix():sha(p) for p in artifacts},
        'development_metrics_sha256':sha(OUT/'development/recovery_metrics.json'),
        'model_revisions':{name:read(OLD/f'setup/{name}_model.json')['revision'] for name in ['dinov3','dinov2']},
        'baseline_preservation_sha256':sha(OUT/'baseline/preservation_manifest.json'),
        'scope':'Before known val regression; no policy or inference code tuning afterward'})
def verify_freeze():
    f=read(OUT/'calibration/frozen_policy_manifest.json')
    if not f or f['source_hashes']!=source_hashes() or f['parameters_sha256']!=sha(OUT/'calibration/parameters.json'):raise ValueError('Missing freeze or source/policy drift')
    if any(not (ROOT/p).is_file() or sha(ROOT/p)!=h for p,h in f.get('frozen_artifacts',{}).items()):raise ValueError('Frozen policy/development input artifact drift')

def audit_confirmations(snap,metadata):
    audits=[];violations=[]
    for a in snap['confirmation_audit']:
        flags=[];epoch=a['candidate_epoch_id'];current=metadata[a['current_observation']]
        if any(metadata[o]['candidate_epoch_id']!=epoch for o in a['observation_ids']):flags.append('CROSS_CANDIDATE_EPOCH_EVIDENCE')
        if not a['integrity']['admissible']:flags+=a['integrity']['rejection_reasons']
        if not clean(current):flags.append('ANNOTATED_IMAGE_USED_FOR_REID')
        if a['route']=='G':
            positive=[p for p in a['LightGlue']['core_pairs'] if p['status']=='STRONG_MATCH']
            if not any(p['integrity']['candidate_provenance']['source_observation']==a['current_observation'] for p in positive):flags+=['CURRENT_FRAME_MISSING','OLD_FRAME_ONLY_CONFIRMATION']
            for pair in positive:
                if not pair['integrity']['admissible']:flags+=pair['integrity']['rejection_reasons']
        if a['LightGlue'].get('negative_positive') or a['photometric']['state']=='STRONG_CONTRADICTION':flags.append('NEGATIVE_CONTRADICTION_IGNORED')
        if any(metadata[o]['candidate_epoch_id']!=epoch for o in a['backfill']['backfilled_observation_ids']):flags.append('CROSS_CANDIDATE_EPOCH_EVIDENCE')
        audit={**a,'current_provenance':provenance(current,a['identity_epoch_id']),'flags':sorted(set(flags))}
        audits.append(audit)
        if flags:violations.append({'frame':a['frame'],'candidate_epoch_id':epoch,'flags':sorted(set(flags))})
    initial=[]
    for d in snap['decisions']:
        if d.get('reason')=='INITIAL_TARGET_BINDING':
            alias=snap['aliases'][0];r=next(x['observation'] for x in snap['ledger'] if x['authorization_id']==alias['authorization_id'])
            initial.append({'reason':'UNCHANGED_CAUSAL_INITIAL_BINDING_BOOTSTRAP','current_provenance':provenance(metadata[r['observation_id']],1),
                'alias':alias,'currentness':True,'clean':clean(metadata[r['observation_id']]),'independent_reidentification_claim':False})
    return {'recoveries':audits,'initial_binding_audit':initial,'violations':violations,'violation_counts':{flag:sum(flag in v['flags'] for v in violations) for flag in FLAGS}}

def replay(video_id,output,rows=None):
    if (output/'metrics.json').exists():return read(output/'metrics.json')
    cfg=parameters();p=ConfirmationPolicy(**cfg['confirmation']);rows=rows or validate_original(video_id)
    provider=FeatureProvider(video_id,rows);verifier=CurrentLightGlue(cfg['geometry']);builder=CandidateEpochBuilder(video_id,EpochPolicy(**cfg['epoch']))
    metadata={};byframe=defaultdict(list)
    for r in rows:byframe[r['frame']].append(r)
    g=V296IdentityGuard(Policy(admission_similarity=p.admission),p,metadata,lambda r:provider.vector('dinov2',r),verifier.verify,
        lambda r,core:photometric_veto(r['photometric'],[b['photometric'] for b in core if b.get('active',True)],p.photometric_threshold))
    start=time.perf_counter();latencies=[]
    try:
        for frame in read(OUT/f'inputs/{video_id}/frames.json'):
            t=time.perf_counter();current=[{**r,'v3':list(provider.vector('dinov3',r))} for r in byframe[frame['frame']]]
            # Initial selector sees unstitched local hypotheses; candidate grouping gains no early target authority.
            grouped=builder.process(current,allow_stitch=g._bound);observations=[]
            for r in grouped:
                metadata[r['observation_id']]=r
                observations.append(Observation(r['observation_id'],r['candidate_epoch_id'],r['frame'],r['time'],tuple(r['bbox']),r['label'],r['confidence'],
                    r['provenance']+f'#CandidateEpoch={r["candidate_epoch_id"]}',vector=tuple(r['v3']),source=r['source'],sam_overlap=r['sam_overlap'],drift=r['drift'],scene_break=r['scene_break']))
            g.process(frame['time'],observations);latencies.append(time.perf_counter()-t)
        snap=g.snapshot();auth={r['observation']['frame']:r for r in g.final_ledger()};final=[]
        for frame in read(OUT/f'inputs/{video_id}/frames.json'):
            authorized=auth.get(frame['frame']);o=authorized['observation'] if authorized else None;maskref=None
            if o:
                r=metadata[o['observation_id']]
                if r.get('foreground_mask_path'):
                    w,h=r['canonical_metadata']['source_dimensions'];mask=Image.new('L',(w,h));a,b,_,_=r['canonical_metadata']['crop_bounds'];mask.paste(Image.open(r['foreground_mask_path']),(a,b));path=output/f'masks/f{frame["frame"]:06d}.png';path.parent.mkdir(parents=True,exist_ok=True);mask.save(path);maskref=path.relative_to(ROOT).as_posix()
            final.append({**frame,'identity_authorized':bool(authorized),'target_bbox':o['bbox'] if o else None,
                'chain_id':f'epoch:{authorized["epoch_id"]}' if authorized else None,'mask_reference':maskref,
                'upstream_identity_state':'AUTHORIZED' if authorized else 'UNRESOLVED','source':'final_revocation_filtered_ledger',
                'target_authorization_provenance':[authorized['authorization_id'],authorized['alias_id']] if authorized else []})
        audit=audit_confirmations(snap,metadata);ep=builder.snapshot();resources=provider.close();provider=None
        old=read(ROOT/f'outputs/identity_rebuild/{"development" if video_id.startswith("test") else "known_validation_regression"}/runs_final/{video_id}/identity.json')
        first=snap['aliases'][0] if snap['aliases'] else None
        local=metadata[next(o for o in first['evidence_refs'])]['local_track_id'] if first else None
        m={'initial_binding':bool(first),'initial_local_track':local,'initial_frame':first['confirmation_frame'] if first else None,
            'initial_track_preserved':bool(first and old and old['aliases'] and local==old['aliases'][0]['candidate_id']),
            'initial_frame_preserved':bool(first and old and old['aliases'] and first['confirmation_frame']==old['aliases'][0]['confirmation_frame']),
            'authorized_observations':len(auth),'unresolved_candidate_frames':sum(f['candidate_present'] and not f['identity_authorized'] for f in final),
            'confirmed_recoveries':len(snap['confirmation_audit']),'route_g':sum(a['route']=='G' for a in snap['confirmation_audit']),
            'route_a':sum(a['route']=='A' for a in snap['confirmation_audit']),'backfilled_observations':sum(len(e['backfilled_observation_ids']) for e in snap['backfill_events']),
            'active_recovered_aliases':sum(a['status']=='CONFIRMED' for a in snap['aliases'][1:]),'revoked_aliases':sum(a['status']=='REVOKED' for a in snap['aliases']),
            'photometric_veto_count':sum(d.get('photometric',{}).get('state')=='STRONG_CONTRADICTION' for d in snap['decisions']),
            'v2_disagreements':sum(d.get('DINOv2',{}).get('state')=='DISAGREEMENT' for d in snap['decisions']),
            'epoch_counts':dict(Counter(e['kind'] for e in builder.events)),
            'decisions':dict(Counter(d['decision'] for d in snap['decisions'])),
            'LightGlue':dict(Counter(r['state'] for r in verifier.results)),
            'integrity_violation_counts':audit['violation_counts'],'rejected_invalid_pair_attempts':len(verifier.invalid_pairs),
            'unauthorized_writes':sum(not any(a['authorization_id']==r['authorization_id'] and 'AUTHORIZE_OBSERVATION' in a['capabilities'] for a in snap['authorizations']) for r in g.final_ledger()),
            'wall_seconds':time.perf_counter()-start,'identity_frame_mean_seconds':float(np.mean(latencies)),'identity_frame_p95_seconds':float(np.quantile(latencies,.95)),
            'feature_resources':resources,'LightGlue_new_pairs':len(verifier.latencies),'LightGlue_new_pair_mean_seconds':float(np.mean(verifier.latencies)) if verifier.latencies else None,
            'runtime_labels_read':False,'video_sha256':read(OUT/f'inputs/{video_id}/source.json')['video_sha256']}
        import torch,psutil
        m['peak_cuda_allocated_bytes']=torch.cuda.max_memory_allocated();m['RSS_end_bytes']=psutil.Process().memory_info().rss
        save(output/'identity.json',snap);save(output/'authorized_rows.json',final);save(output/'candidate_epochs.json',ep)
        save(output/'confirmation_audit.json',audit);save(output/'metadata.json',{oid:{k:v for k,v in r.items() if k not in ['v3','pixel_descriptor']} for oid,r in metadata.items()})
        save(output/'LightGlue.json',verifier.results);save(output/'metrics.json',m)
        return m
    finally:
        if provider:provider.close()
        verifier.close()

def run_set(kind):
    val=kind=='known_val_regression'
    if val:verify_freeze()
    ids=[f'val_{i}' for i in range(1,12)] if val else [f'test{i}' for i in range(1,10)]
    results={}
    for vid in ids:
        validate_original(vid);m=replay(vid,OUT/f'{kind}/runs/{vid}');results[vid]=m
        print(kind,vid,'authorized',m['authorized_observations'],'G/A',m['route_g'],m['route_a'],'backfill',m['backfilled_observations'],'initial track/frame',m['initial_track_preserved'],m['initial_frame_preserved'],flush=True)
    keys=['authorized_observations','unresolved_candidate_frames','confirmed_recoveries','route_g','route_a','backfilled_observations','initial_track_preserved','initial_frame_preserved','photometric_veto_count','v2_disagreements','unauthorized_writes','wall_seconds']
    r={'scope':'POST-VALIDATION KNOWN REGRESSION; never held-out' if val else 'DEVELOPMENT','videos':results,
        'totals':{k:sum(m[k] for m in results.values()) for k in keys}}
    save(OUT/f'{kind}/{"metrics" if val else "recovery_metrics"}.json',r)
    return r

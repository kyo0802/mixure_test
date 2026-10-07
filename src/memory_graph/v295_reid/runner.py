"""Opt-in causal replay. Development labels are never read by identity decisions."""
from collections import defaultdict
from dataclasses import asdict
import hashlib
import time
import numpy as np
from PIL import Image
from memory_graph.identity.contracts import Observation, Policy, digest
from .io import ROOT,OUT,read,save,sha,sources
from .dataset import extract
from .backbones import Backbone,embed_video
from .evidence import RecoveryPolicy
from .guard import V295IdentityGuard
from .geometry import LightGlueVerifier


def policy():
    return RecoveryPolicy(**read(OUT/'calibration/confirmation_policy.json')['policy'])


def source_hashes():
    paths=list((ROOT/'src/memory_graph/v295_reid').glob('*.py'))+list((ROOT/'src/memory_graph/identity').glob('*.py'))
    paths+=[ROOT/'scripts/run_v295_reid.py']
    for folder in ['events','reasoning']:
        paths+=list((ROOT/f'src/memory_graph/{folder}').glob('*.py'))
    paths+=list((ROOT/'configs').rglob('*.yaml'))
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}


def verify_freeze():
    f=read(OUT/'final/development_freeze.json')
    if not f or f['source_hashes']!=source_hashes():raise ValueError('Missing development freeze or source drift')
    if f['policy_sha256']!=sha(OUT/'calibration/confirmation_policy.json'):raise ValueError('Policy drift')
    if f['backbone_sha256']!=sha(OUT/'benchmark/selected_backbone.json'):raise ValueError('Backbone drift')


def freeze():
    if (OUT/'final/development_freeze.json').exists():raise FileExistsError('Development freeze already exists')
    save(OUT/'final/development_freeze.json',{'created_unix':time.time(),'source_hashes':source_hashes(),
        'policy_sha256':sha(OUT/'calibration/confirmation_policy.json'),
        'backbone_sha256':sha(OUT/'benchmark/selected_backbone.json'),
        'development_metrics_sha256':sha(OUT/'development/regression_metrics.json'),
        'scope':'Development only; created before known val replays. No tuning after this point.'})


def embedding_cache(video_id,p,model=None):
    path=OUT/f'benchmark/embeddings/{p.backbone}/{video_id}.npz'
    if model:return embed_video(model,video_id)
    if not path.exists():raise FileNotFoundError(path)
    m=read(path.with_suffix('.json'));selected=read(OUT/'benchmark/selected_backbone.json')
    if m['crop_manifest_sha256']!=sha(OUT/f'crops/{video_id}/observations.json') or m['model']['revision']!=selected['revision']:
        raise ValueError('Stale canonical crop or embedding cache')
    if m['model'].get('embedding_protocol')!='patch_mean_foreground_if_reliable_else_all_object_crop_patches':raise ValueError('Feature protocol drift')
    with np.load(path) as loaded:return {k:loaded[k] for k in loaded.files}


def geometry_callback(verifier,byid):
    def callback(observations,core,negative,cm,nm):
        # Latest frame plus best other quality frame; never future or label-selected crops.
        indices=[len(observations)-1]
        others=sorted(range(len(observations)-1),key=lambda i:(-observations[i].confidence,observations[i].time))
        if others:indices.append(others[0])
        groups={'core':[],'negative':[]};started=time.perf_counter()
        for i in indices:
            a=byid[observations[i].observation_id]
            for kind,bank,matrix,limit in [('core',core,cm,2),('negative',negative,nm,2)]:
                ranked=sorted(range(len(bank)),key=lambda j:-matrix[i][j])[:limit]
                for j in ranked:
                    b=byid[bank[j]['observation_id']]
                    if b['time']>observations[-1].time:raise ValueError('Noncausal geometry reference')
                    result=verifier.compare(a,b)
                    key=hashlib.sha256((a['crop_sha256']+b['crop_sha256']+'official_superpoint512').encode()).hexdigest()
                    groups[kind].append({k:v for k,v in result.items() if k not in ['keypoints0','keypoints1','matches','homography','inlier_mask']})
                    groups[kind][-1]['pair_reference']=f'lightglue/pairs/{key}.json'
        cp=any(x['status']=='STRONG_MATCH' for x in groups['core']);np_=any(x['status']=='STRONG_MATCH' for x in groups['negative'])
        return {'core_positive':cp,'negative_positive':np_,'core_pairs':groups['core'],'negative_pairs':groups['negative'],
                'status':'NEGATIVE_VERIFIED' if np_ else 'CORE_VERIFIED' if cp else 'UNKNOWN','wall_seconds':time.perf_counter()-started}
    return callback


def replay(video_id,output,verifier,*,model=None,rows=None):
    p=policy();output=output.resolve()
    if (output/'metrics.json').exists():return read(output/'metrics.json')
    rows=rows if rows is not None else extract(video_id)
    features=embedding_cache(video_id,p,model);byid={r['observation_id']:r for r in rows};byframe=defaultdict(list)
    metadata={}
    for r in rows:
        metadata[r['observation_id']]={**r,'pixel_descriptor':np.asarray(Image.open(r['crop_path']).convert('RGB').resize((32,32)))}
        byframe[r['frame']].append(Observation(**{k:r[k] for k in ['observation_id','candidate_id','frame','time','bbox','label','confidence','provenance','source','sam_overlap','drift','scene_break']},
                                             vector=tuple(float(x) for x in features[r['observation_id']])))
    g=V295IdentityGuard(Policy(admission_similarity=p.admission_support),recovery_policy=p,metadata=metadata,verifier=geometry_callback(verifier,byid))
    frames=read(OUT/f'crops/{video_id}/frames.json');started=time.perf_counter();latencies=[]
    for frame in frames:
        t=time.perf_counter();g.process(frame['time'],byframe[frame['frame']]);latencies.append(time.perf_counter()-t)
    snap=g.snapshot();authorized={r['observation']['frame']:r for r in g.final_ledger()};final=[]
    for frame in frames:
        auth=authorized.get(frame['frame']);o=auth['observation'] if auth else None;mask_ref=None
        if o:
            r=byid[o['observation_id']]
            if r.get('foreground_mask_path'):
                w,h=r['canonical_metadata']['source_dimensions'];mask=Image.new('L',(w,h));bounds=r['canonical_metadata']['crop_bounds']
                mask.paste(Image.open(r['foreground_mask_path']),(bounds[0],bounds[1]));path=output/f'masks/f{frame["frame"]:06d}.png'
                path.parent.mkdir(parents=True,exist_ok=True);mask.save(path);mask_ref=path.relative_to(ROOT).as_posix()
        final.append({**frame,'identity_authorized':bool(auth),'target_bbox':o['bbox'] if o else None,
            'chain_id':f'epoch:{auth["epoch_id"]}' if auth else None,'mask_reference':mask_ref,
            'upstream_identity_state':'AUTHORIZED' if auth else 'UNRESOLVED','source':'final_revocation_filtered_ledger',
            'target_authorization_provenance':[auth['authorization_id'],auth['alias_id']] if auth else []})
    source=read(OUT/f'crops/{video_id}/source.json')
    metrics={'initial_binding':bool(snap['aliases']),'authorized_observations':len(authorized),'sampled_frames':len(frames),
        'unresolved_candidate_frames':sum(f['candidate_present'] and not f['identity_authorized'] for f in final),
        'confirmed_recoveries':sum(e['start_reason']=='MULTI_EVIDENCE_REIDENTIFICATION' for e in snap['epochs']),
        'active_recovered_aliases':sum(a['status']=='CONFIRMED' for a in snap['aliases'][1:]),
        'revoked_aliases':sum(a['status']=='REVOKED' for a in snap['aliases']),
        'decision_counts':{s:sum(d['decision']==s for d in snap['decisions']) for s in ['NEW_CANDIDATE','EVIDENCE_ACCUMULATING','PROVISIONAL','AMBIGUOUS','CONFIRMED_MATCH','REJECTED']},
        'stage_episode_counts':{s:len({(d['candidate_id'],d.get('epoch_id')) for d in snap['decisions'] if d['decision']==s}) for s in ['AMBIGUOUS','REJECTED','PROVISIONAL']},
        'banks':{k:sum(b['active'] for b in bank) for k,bank in snap['banks'].items()},
        'unauthorized_matched':sum(not any(a['authorization_id']==r['authorization_id'] and 'AUTHORIZE_OBSERVATION' in a['capabilities'] for a in snap['authorizations']) for r in g.final_ledger()),
        'rejected_bank_updates':snap['rejected_bank_updates'],'wall_seconds':time.perf_counter()-started,
        'identity_frame_seconds_mean':float(np.mean(latencies)),'identity_frame_seconds_p95':float(np.quantile(latencies,.95)),
        'policy_sha256':digest(asdict(p)),'video_sha256':source['video_sha256'],'raw_sources':source['raw_sources'],
        'mode':'CAUSAL_RAW_EVIDENCE_REPLAY','selected_backbone':p.backbone,'development_labels_used_at_runtime':False}
    save(output/'identity.json',snap);save(output/'authorized_rows.json',final);save(output/'tracklet_evidence.json',g.accumulator.results);save(output/'metrics.json',metrics)
    return metrics


def run_set(kind):
    val=kind=='known_val_regression'
    if val:verify_freeze()
    ids=[f'val_{i}' for i in range(1,12)] if val else [f'test{i}' for i in range(1,10)]
    results={};p=policy();model=Backbone(p.backbone) if val else None
    try:
        for vid in ids:extract(vid)
        if model:
            for vid in ids:embed_video(model,vid)
            save(OUT/f'{kind}/embedding_resources.json',model.metadata());model.close();model=None
        verifier=LightGlueVerifier(p.geometry_policy())
        try:
            for vid in ids:
                dest=OUT/f'{kind}/runs/{vid}';m=replay(vid,dest,verifier)
                _,_,safe=sources(vid);old=read(safe/'identity.json');new=read(dest/'identity.json')
                m['initial_track_matches_baseline']=bool(old['aliases'] and new['aliases'] and old['aliases'][0]['candidate_id']==new['aliases'][0]['candidate_id'])
                m['initial_frame_matches_baseline']=bool(old['aliases'] and new['aliases'] and old['aliases'][0]['confirmation_frame']==new['aliases'][0]['confirmation_frame'])
                save(dest/'metrics.json',m);results[vid]=m
                print(kind,vid,'authorized',m['authorized_observations'],'recoveries',m['confirmed_recoveries'],'banks',m['banks'],flush=True)
            import torch
            save(OUT/f'{kind}/verifier_resources.json',{'pairs_newly_measured':len(verifier.latencies),'mean_pair_seconds':float(np.mean(verifier.latencies)) if verifier.latencies else None,
                'peak_cuda_allocated_bytes':torch.cuda.max_memory_allocated(),'feature_cache_entries':len(verifier.features)})
        finally:verifier.close()
    finally:
        if model:model.close()
    total={k:sum(m[k] for m in results.values()) for k in ['authorized_observations','unresolved_candidate_frames','confirmed_recoveries','active_recovered_aliases','initial_binding','initial_track_matches_baseline','initial_frame_matches_baseline','unauthorized_matched','wall_seconds']}
    result={'scope':'KNOWN POST-VALIDATION REGRESSION; NOT HELD-OUT' if val else 'DEVELOPMENT','videos':results,'totals':total}
    save(OUT/f'{kind}/{"val_1_to_11_metrics" if val else "regression_metrics"}.json',result)
    return result


def smoke():
    verify_freeze()
    from memory_graph.identity import pipeline as frozen
    old=frozen.OUT;frozen.OUT=OUT
    try:
        rawdest=OUT/'smoke/fresh_raw_seed';video=ROOT/'test2.mp4'
        if not (rawdest/'metrics.json').exists():frozen.raw(video,rawdest)
        sam=read(rawdest/'sam/unverified_propagation.json')
        if sam:save(rawdest/'raw/sam/sam_continuity_log.json',sam)
        rows=extract('test2_smoke',source_override=rawdest/'raw',video_override=video,safe_override=rawdest)
        model=Backbone(policy().backbone)
        try:embed_video(model,'test2_smoke')
        finally:model.close()
        verifier=LightGlueVerifier(policy().geometry_policy());dest=OUT/'smoke/v295_test2'
        try:replay('test2_smoke',dest,verifier,rows=rows)
        finally:verifier.close()
        prep=read(dest/'prepared/interface_smoke.json') or frozen.prepare(dest,video)
        result=frozen.reason(dest) if not (dest/'prepared/qwen/responses.json').exists() else read(dest/'prepared/qwen/responses.json')
        save(OUT/'smoke/result.json',{'fresh_yolo':True,'fresh_sam':True,'selected_backbone':policy().backbone,'Qwen':'Qwen2.5-VL-7B NF4',
            'Qwen3_or_Strata_used':False,'identity':read(dest/'metrics.json'),'prepare':prep,'reasoning':result,'unchanged_frozen_interfaces':True})
        print('smoke',result,flush=True)
    finally:frozen.OUT=old

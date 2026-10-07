"""Development-only reference/query separation; no val thresholds or averaged-only evidence."""
from collections import defaultdict
import json
import statistics
import time
import numpy as np
from .io import OUT,read,save,sha
from .backbones import Backbone,embed_video


def distribution(values):
    v=np.asarray(values,dtype=float)
    return {'count':len(v),'min':float(v.min()) if len(v) else None,
            'median':float(np.median(v)) if len(v) else None,'max':float(v.max()) if len(v) else None,
            'quantiles':{str(q):float(np.quantile(v,q)) for q in [.1,.25,.75,.9]} if len(v) else {}}


def choose_views(rows,vectors,limit=8,diversity=.985,min_interval=.4):
    selected=[]
    for r in sorted(rows,key=lambda x:x['time']):
        if not vectors.get(r['observation_id']) is not None:continue
        if any(abs(r['time']-s['time'])<min_interval-1e-5 for s in selected):continue
        if selected and max(float(vectors[r['observation_id']]@vectors[s['observation_id']]) for s in selected)>=diversity:continue
        selected.append(r)
        if len(selected)>=limit:break
    return selected


def measure(name):
    dest=OUT/f'benchmark/{name}_metrics.json'
    if dest.exists():return read(dest)
    meta=read(OUT/f'setup/{name}_model.json')
    if name!='mobilenet' and (not meta or meta.get('blocked')):
        result={'model':name,'available':False,'blocker':meta};save(dest,result);return result
    positives=read(OUT/'benchmark/positive_observations.json');negatives=read(OUT/'benchmark/negative_observations.json')
    model=Backbone(name);vectors={};records=[];references={};pair_matrices=[]
    try:
        for n in range(1,10):
            vid=f'test{n}';v=embed_video(model,vid);vectors[vid]=v
            pos=[r for r in positives if r['video_id']==vid];neg=[r for r in negatives if r['video_id']==vid]
            causal=[r for r in pos if r['label_provenance']['type'] in {'FINAL_CONTINUITY_AUTHORIZED_EPOCH','CAUSAL_INITIAL_BINDING_CORE'}]
            cutoff=statistics.median(r['time'] for r in causal)
            # Earliest half of the trusted epoch is reference-only; later positive points are query-only.
            initial=read(OUT/'benchmark/identity_dataset_manifest.json')['core_reference_ids'][vid]
            core=[r for r in causal if r['observation_id'] in initial]
            # Identical reference frames for every model; native feature spaces cannot select their own test population.
            prefix=sorted([r for r in causal if r['time']<=cutoff and r not in core],key=lambda r:r['time'])
            for r in prefix:
                if len(core)>=8:break
                if all(abs(r['time']-s['time'])>=.4-1e-5 for s in core):core.append(r)
            negative_refs=[]
            for r in sorted(neg,key=lambda r:r['time']):
                if len(negative_refs)>=4:break
                if all(r['view_hash']!=s['view_hash'] for s in negative_refs):negative_refs.append(r)
            references[vid]={'core_ids':[r['observation_id'] for r in core],'negative_ids':[r['observation_id'] for r in negative_refs],
                'core_last_time':max(r['time'] for r in core),'reference_cutoff':cutoff,
                'reference_protocol':'Same initial+temporally spaced Core prefix frames across all models; queries strictly after common prefix cutoff'}
            for r in pos+neg:
                if r in core or r['identity_label']=='TARGET' and r['time']<=cutoff:continue
                cs=[float(v[r['observation_id']]@v[c['observation_id']]) for c in core]
                ns=[float(v[r['observation_id']]@v[c['observation_id']]) for c in negative_refs if c['observation_id']!=r['observation_id']]
                row={'video_id':vid,'observation_id':r['observation_id'],'candidate_id':r['candidate_id'],'frame':r['frame'],'time':r['time'],
                     'label':r['identity_label'],'core_similarities':cs,'negative_similarities_leave_self_out':ns,
                     'core_top2_mean':float(np.mean(sorted(cs,reverse=True)[:2])),'core_best':max(cs),
                     'negative_best':max(ns,default=None),'negative_reference_scope':'Development distractor diagnostic; may include later reference views, never runtime bank input'}
                records.append(row)
        pos_scores=[r['core_top2_mean'] for r in records if r['label']=='TARGET'];neg_scores=[r['core_top2_mean'] for r in records if r['label']=='DISTRACTOR']
        operating=[]
        for threshold in np.arange(.3,.981,.02):
            operating.append({'threshold':round(float(threshold),3),'true_accepts':int(sum(x>=threshold for x in pos_scores)),
                              'false_accepts':int(sum(x>=threshold for x in neg_scores)),'positive_queries':len(pos_scores),'negative_queries':len(neg_scores)})
        zero=[x for x in operating if x['false_accepts']==0]
        best=max(zero,key=lambda x:(x['true_accepts'],-x['threshold'])) if zero else None
        auc=float(np.mean([p>n for p in pos_scores for n in neg_scores])+.5*np.mean([p==n for p in pos_scores for n in neg_scores])) if pos_scores and neg_scores else None
        grouped=defaultdict(list)
        for r in records:grouped[(r['video_id'],r['candidate_id'],r['label'])].append(r)
        for (vid,cid,label),items in grouped.items():
            # Split gaps: candidate IDs are not physical identity labels.
            chunks=[]
            for r in sorted(items,key=lambda x:x['time']):
                if not chunks or r['time']-chunks[-1][-1]['time']>.6:chunks.append([])
                chunks[-1].append(r)
            for i,chunk in enumerate(chunks):
                sc=[r['core_top2_mean'] for r in chunk]
                pair_matrices.append({'tracklet_id':f'{vid}/{cid}/{label}/{i}','label':label,'observations':chunk,
                    'core_matrix':[r['core_similarities'] for r in chunk],'negative_matrix':[r['negative_similarities_leave_self_out'] for r in chunk],
                    'duration':chunk[-1]['time']-chunk[0]['time'],'median':float(np.median(sc)),'lower_quantile':float(np.quantile(sc,.25)),
                    'supporting_frames_at_operating_point':sum(s>=(best['threshold'] if best else 1.) for s in sc)})
        measured_metadata=model.metadata()
        if not measured_metadata['observations']:
            measured_metadata=read(OUT/f'benchmark/embeddings/{name}/test9.json')['model']
            measured_metadata={**measured_metadata,'measurement_source':'Actual previous extraction of the identical crop manifest, reused cache'}
        result={'model':name,'available':True,'metadata':measured_metadata,'positive':distribution(pos_scores),'negative':distribution(neg_scores),
            'target_to_negative':distribution([r['negative_best'] for r in records if r['label']=='TARGET' and r['negative_best'] is not None]),
            'distractor_to_negative':distribution([r['negative_best'] for r in records if r['label']=='DISTRACTOR' and r['negative_best'] is not None]),
            'overlap_region':[max(min(pos_scores),min(neg_scores)),min(max(pos_scores),max(neg_scores))] if pos_scores and neg_scores else None,
            'ROC_AUC':None,'descriptive_pairwise_AUC':auc,'equal_error_estimate':None,
            'statistical_limit':'Sparse distractor instances and correlated video frames; AUC descriptive only, no statistically meaningful EER/ROC confidence.',
            'operating_points':operating,'zero_observed_false_acceptance_point':best,'reference_protocol':references,
            'selection_scope':'DEVELOPMENT_ONLY','record_count':len(records)}
        save(OUT/f'benchmark/{name}_single_frame_evidence.json',records);save(OUT/f'benchmark/{name}_tracklet_evidence.json',pair_matrices);save(dest,result)
        print(name,result['positive'],result['negative'],'zeroFA',best,flush=True)
    finally:model.close()
    return result


def select():
    dest=OUT/'benchmark/selected_backbone.json'
    if dest.exists():return read(dest)
    metrics={n:read(OUT/f'benchmark/{n}_metrics.json') for n in ['mobilenet','dinov2','dinov3']}
    available=[(n,m) for n,m in metrics.items() if m and m.get('available') and m['zero_observed_false_acceptance_point']]
    if not available:raise RuntimeError('No safely separable development operating point')
    name,result=max(available,key=lambda pair:(pair[1]['zero_observed_false_acceptance_point']['true_accepts'],
                     pair[1]['descriptive_pairwise_AUC'],-pair[1]['metadata']['latency_median_seconds']))
    selection={'backbone':name,'model_id':result['metadata']['model_id'],'revision':result['metadata']['revision'],
        'operating_point':result['zero_observed_false_acceptance_point'],'selected_unix':time.time(),
        'why':'Maximum development target acceptance at zero observed distractor acceptance; descriptive separation and runtime break ties.',
        'scope':'Development only; small correlated dataset, not proof of zero real-world false acceptance.',
        'unavailable_models':[n for n,m in metrics.items() if not m or not m.get('available')],
        'metric_hashes':{n:sha(OUT/f'benchmark/{n}_metrics.json') for n in metrics}}
    save(OUT/'benchmark/backbone_metrics.json',metrics);save(dest,selection)
    return selection

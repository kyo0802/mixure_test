"""Post-inference evaluator. Numeric metrics explicitly scoped to reviewed samples."""
from collections import defaultdict,Counter
from pathlib import Path
from ..v21.artifacts import read
from ..perception.track_manager import sha256
from ..memory.memory_store import save_json

NOT_MEASURABLE='NOT MEASURABLE FROM CURRENT GT'
ERROR_TYPES=['DETECTION_FAILURE','CLASSIFICATION_FAILURE','TRACK_FRAGMENTATION','ID_SWITCH',
             'ASSOCIATION_FAILURE','FALSE_MERGE','ADMISSION_FAILURE','SEMANTIC_REASONING_FAILURE',
             'RELATION_REASONING_FAILURE','INSUFFICIENT_EVIDENCE']


def distinct_tests(gt_entities,pairs):
    tests=[];errors=[]
    for a,b in pairs:
        left,right=set(gt_entities.get(a,[])),set(gt_entities.get(b,[]))
        shared=left&right; evaluable=bool(left and right)
        tests.append({'objects':[a,b],'evaluable':evaluable,'shared_entities':sorted(shared),
                      'result':'FALSE_MERGE' if shared else 'PASS' if evaluable else NOT_MEASURABLE})
        if shared:errors.append({'type':'FALSE_MERGE','objects':[a,b],'entities':sorted(shared)})
    return tests,errors


def render_reviewed_timeline(rows,path):
    from ..visualization.graph_visualizer import plt
    rows=[r for r in rows if r['gt_object_id']=='smartphone_01']
    fig,ax=plt.subplots(figsize=(15,4))
    for r in rows:
        t=r['timestamp']
        color='#277da8' if r.get('scored') else '#b6bbc0'
        ax.scatter(t,2,color=color,s=30)
        if r.get('scored'):
            ax.scatter(t,1,color='#28a065' if r['detected'] else '#d14f4f',s=30)
            ax.scatter(t,0,color='#28a065' if r['track_id'] else '#d14f4f',s=30)
            if r['track_id']:ax.annotate(f"T{r['track_id']}",(t,0),xytext=(0,-18),textcoords='offset points',fontsize=7,rotation=90)
    ax.set_yticks([0,1,2],['Local observation','Raw detection','Manually visible (blue) / excluded (gray)'])
    ax.set_ylim(-.8,2.5);ax.set_xlabel('seconds (only reviewed samples; gaps are not interpolated)')
    ax.set_title('Smartphone diagnostic timeline | green=present, red=missing on a visible sample')
    fig.tight_layout();fig.savefig(path,dpi=150);plt.close(fig)


def iou(a,b):
    x=max(0,min(a[2],b[2])-max(a[0],b[0])); y=max(0,min(a[3],b[3])-max(a[1],b[1]))
    inter=x*y; union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union else 0


def score_samples(samples,detections,tracks,mapping,annotations):
    errors=[];rows=[];by_object=defaultdict(list);track_objects=defaultdict(Counter)
    for sample in samples:
        if sample['visibility'] not in {'VISIBLE','PARTIALLY_VISIBLE'} or sample.get('bbox') is None:
            rows.append({**sample,'scored':False,'reason':'not manually verified visible with bbox'});continue
        if not sample.get('manually_reviewed'): raise ValueError('Visible GT requires manual review provenance')
        box=sample['bbox']; frame=sample['frame_index']; gt=sample['gt_object_id']
        dets=[d for d in detections if d['frame_index']==frame and iou(box,d['bbox'])>=.3]
        best=max(dets,key=lambda d:iou(box,d['bbox']),default=None)
        local=[(t,o) for t in tracks for o in t['observations'] if o['frame_index']==frame and iou(box,o['bbox'])>=.3]
        match=max(local,key=lambda p:iou(box,p[1]['bbox']),default=None)
        tid=match[0]['track_id'] if match else None
        row={**sample,'scored':True,'detected':best is not None,'detector_class':best['class_name'] if best else None,
             'track_id':tid,'entity_id':mapping.get(tid),'best_detection_iou':iou(box,best['bbox']) if best else None}
        rows.append(row);by_object[gt].append(row)
        if not best: errors.append({'type':'DETECTION_FAILURE','gt_object_id':gt,'frame_index':frame,'evidence':'visible manual box has no raw detection IoU >= .3'})
        elif best['class_name'] not in annotations.get('acceptable_detector_classes',{}).get(gt,[best['class_name']]):
            errors.append({'type':'CLASSIFICATION_FAILURE','gt_object_id':gt,'frame_index':frame,'predicted':best['class_name']})
        if best and not match:
            errors.append({'type':'INSUFFICIENT_EVIDENCE','gt_object_id':gt,'frame_index':frame,'evidence':'raw detection exists but no assigned local observation; tracker rejection, not persistent association'})
        if tid is not None: track_objects[tid][gt]+=1
    detection={gt:{'visible_reviewed_samples':len(rs),'detected_samples':sum(r['detected'] for r in rs),
                   'recall':sum(r['detected'] for r in rs)/len(rs)} for gt,rs in by_object.items()}
    fragments={gt:sorted({r['track_id'] for r in rs if r['track_id'] is not None}) for gt,rs in by_object.items()}
    for gt,ids in fragments.items():
        if len(ids)>1:errors.append({'type':'TRACK_FRAGMENTATION','gt_object_id':gt,'observed_track_ids':ids,'scope':'reviewed samples only; count is a lower bound'})
    purity={str(t):{'purity':max(counts.values())/sum(counts.values()),'reviewed_observations':sum(counts.values()),'gt_counts':dict(counts)} for t,counts in track_objects.items()}
    for t,counts in track_objects.items():
        if len(counts)>1:errors.append({'type':'ID_SWITCH','track_id':t,'gt_objects':list(counts),'scope':'multiple GT objects on reviewed observations; exact switch count requires dense annotation'})
    return rows,detection,fragments,purity,errors


def evaluate(output,annotation_path):
    output=Path(output); annotations=read(annotation_path)
    manifest=read(output/'prediction_manifest.json')
    mismatches=[p for p,h in manifest.items() if not(output/p).is_file() or sha256(output/p)!=h]
    if mismatches:raise ValueError(f'Frozen predictions changed: {mismatches}')
    tracks=read(output/'event_analysis'/'track_timelines.json'); detections=read(output/'event_analysis'/'detections.json')
    entities=read(output/'persistent_entities.json'); mapping={tid:e['entity_id'] for e in entities for tid in e['local_track_ids']}
    rows,detection,fragments,purity,errors=score_samples(annotations['samples'],detections,tracks,mapping,annotations)
    unassigned=[r for r in rows if r.get('scored') and r.get('detected') and r.get('track_id') is None]
    # Human mapping scope is explicit, not automatically extended from one frame to an entire track.
    verified=annotations.get('verified_track_segments',[])
    gt_entities=defaultdict(set)
    for seg in verified:
        if seg['track_id'] in mapping:gt_entities[seg['gt_object_id']].add(mapping[seg['track_id']])
    pair_tests,false_merges=distinct_tests(gt_entities,annotations.get('distinct_objects',[]))
    errors.extend(false_merges)
    recovery=[]
    decisions={a['track_id']:a for a in read(output/'track_entity_associations.json')}
    for pair in annotations.get('recoverable_fragment_pairs',[]):
        a,b=pair['track_ids'];status=NOT_MEASURABLE
        if pair.get('manually_verified_usable') and a in mapping and b in mapping:
            status='RECOVERED' if mapping[a]==mapping[b] else 'AMBIGUOUS' if decisions[b]['decision']=='AMBIGUOUS' else 'MISSED'
            if status!='RECOVERED':errors.append({'type':'ASSOCIATION_FAILURE','track_ids':[a,b],'evidence':pair['reason']})
        recovery.append({**pair,'result':status})
    admission=read(output/'admission_failures.json')
    known_tids={s['track_id'] for s in verified}
    usable_tids={q['track_id'] for q in read(output/'track_quality_report.json') if q['usable_for_identity']}
    current_admission_loss=sorted((usable_tids & known_tids)-set(mapping))
    for tid in current_admission_loss:
        errors.append({'type':'ADMISSION_FAILURE','track_id':tid,'scope':'V2.1 current identity admission'})
    removed=[r for r in admission['v2_counterfactual_removed'] if r['track_id'] in known_tids]
    for r in removed:errors.append({'type':'ADMISSION_FAILURE','track_id':r['track_id'],'scope':'V2 counterfactual only; V2.1 preserved identity','reasons':r['reasons']})
    errors.extend(annotations.get('manually_reviewed_errors',[]))
    physical=read(output/'memory_graph.json')['relations']; negative=[]
    semantic_checks=[]
    acceptable={'smartphone_01':{'phone','cell phone','cell_phone','smartphone'},
                'basketball_01':{'basketball'},'trash_bin_01':{'trash bin','trash can','waste bin','bin'}}
    entity_lookup={e['entity_id']:e for e in entities}
    for seg in verified:
        gt=seg['gt_object_id'];tid=seg['track_id']
        if gt not in acceptable or tid not in mapping:continue
        label=entity_lookup[mapping[tid]]['semantic_class']
        semantic_checks.append({'gt_object_id':gt,'track_id':tid,'semantic_class':label,
            'result':'UNRESOLVED' if label=='unknown' else 'CORRECT_ON_REVIEWED_SEGMENT' if label in acceptable[gt] else 'INCORRECT'})
    for a,b in annotations.get('not_physically_near',[]):
        claims=[r for r in physical if r['predicate']=='NEAR' and
                ((r['subject_entity_id'] in gt_entities[a] and r['object_entity_id'] in gt_entities[b]) or
                 (r['subject_entity_id'] in gt_entities[b] and r['object_entity_id'] in gt_entities[a]))]
        negative.append({'objects':[a,b],'false_promotions':len(claims),
                         'evaluable':bool(gt_entities[a] and gt_entities[b]),'note':'No promotion is conservative, not proof of physical understanding.'})
        for r in claims:errors.append({'type':'RELATION_REASONING_FAILURE','relation':r})
    observed=read(output/'observation_graph.json')['relations']
    counts={t:sum(e['type']==t for e in errors) for t in ERROR_TYPES}
    modes=[]
    if counts['DETECTION_FAILURE']:modes.append('DETECTION_LIMITED')
    if counts['TRACK_FRAGMENTATION'] or counts['ID_SWITCH'] or unassigned:modes.append('LOCAL_TRACKING_LIMITED')
    if counts['ASSOCIATION_FAILURE']:modes.append('ASSOCIATION_LIMITED')
    if current_admission_loss:modes.append('ADMISSION_LIMITED')
    if counts['SEMANTIC_REASONING_FAILURE'] or counts['CLASSIFICATION_FAILURE']:modes.append('SEMANTIC_LIMITED')
    diagnosis='MIXED' if len(modes)>1 else modes[0] if modes else 'INSUFFICIENT_EVIDENCE'
    analysis={'annotation_sha256':sha256(annotation_path),'prediction_manifest_sha256':sha256(output/'prediction_manifest.json'),
        'scope':'Sparse manually reviewed frames/segments, not full-video benchmark; counts use heterogeneous evidence units.',
        'samples':rows,'detection_recall_on_reviewed_samples':detection,'observed_fragments_per_gt_object':fragments,
        'raw_detections_without_local_track_on_reviewed_samples':unassigned,
        'last_valid_detection_on_reviewed_samples':{gt:max((r['frame_index'] for r in rs if r.get('detected')),default=None)
            for gt,rs in ((g,[r for r in rows if r['gt_object_id']==g]) for g in detection)},
        'track_purity_on_reviewed_samples':purity,'full_video_id_switch_count':NOT_MEASURABLE,
        'association_recovery':{'pairs':recovery,'rate':sum(p['result']=='RECOVERED' for p in recovery)/sum(p['result']!=NOT_MEASURABLE for p in recovery) if any(p['result']!=NOT_MEASURABLE for p in recovery) else NOT_MEASURABLE},
        'false_merge_count_on_evaluable_pairs':len(false_merges),'distinct_object_tests':pair_tests,
        'semantic_checks':semantic_checks,
        'v21_identity_relevant_tracks_removed':len(current_admission_loss),'v2_counterfactual_identity_relevant_removed':removed,
        'negative_physical_relation_tests':negative,'image_plane_observations_kept_out_of_memory':sum(r['reference_frame']=='image_plane' for r in observed),
        'error_counts':counts,'errors':errors,'narrative_only_facts':annotations.get('narrative_only_facts',[])}
    assessment={'classification':diagnosis,'supported_components':modes,'counts':counts,
        'segmentation_ab_justified_on_reviewed_sequences':counts['DETECTION_FAILURE']>=2 or bool(counts['ID_SWITCH']),
        'replace_yolo_and_vlm_now':False,'reason':'An A/B can test continuation; it cannot recover initialization misses or replace semantic reasoning.',
        'limits':'Sparse reviewed samples; no SAM experiment executed; no dense GT accuracy or global causal dominance claim.'}
    save_json(output/'error_analysis.json',analysis);save_json(output/'bottleneck_assessment.json',assessment)
    render_reviewed_timeline(rows,output/'gt_review'/'smartphone_diagnostic_timeline.png')
    text=f"# {output.name} V2.1 validation\n\nDiagnosis: {diagnosis}\n\n"+analysis['scope']+'\n\n'
    text+='| Object | Visible samples | Detected | Recall |\n|---|---:|---:|---:|\n'
    for gt,m in detection.items():text+=f"| {gt} | {m['visible_reviewed_samples']} | {m['detected_samples']} | {m['recall']:.3f} |\n"
    text+='\n## Error evidence counts\n\n'+''.join(f'- {t}: {c}\n' for t,c in counts.items())
    text+='\nFull-video ID switches and unannotated recall: '+NOT_MEASURABLE+'.\nSee error_analysis.json for exact evidence and denominators. Never require a later smartphone reappearance or merge it with desk phones.\n'
    (output/'validation_report.md').write_text(text,encoding='utf-8')
    return analysis,assessment

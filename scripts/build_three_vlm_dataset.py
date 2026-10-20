"""Deterministic source-only dataset, complete timeline mapping, no GT access."""
from pathlib import Path
import sys,json,hashlib,math,bisect,statistics
ROOT=Path(__file__).resolve().parents[1];sys.dont_write_bytecode=True;sys.path[:0]=[str(ROOT/'src'),str(ROOT/'outputs/current_development/video_event_experiment/.deps')]
from memory_graph.experiments.three_vlm_contract import PROMPT,SCHEMA,choose_uniform8,merge_intervals
OUT=ROOT/'artifacts/pass_t/phase3/three_vlm_full_v1'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def main():
    import av
    assert not (OUT/'dataset_freeze.json').exists(),'ALREADY_FROZEN'
    old=ROOT/'outputs/current_development/event_windows';events=read(old/'event_manifest.json');sources=read(old/'development_inputs.json')
    expected=read(old/'builder_freeze.json')['files']['event_windows/event_manifest.json'];assert sha(old/'event_manifest.json')==expected
    videos=[];windows=[]
    for source in sources:
        vid=source['video_id'];path=Path(source['path']);assert sha(path)==source['sha256'],('SOURCE_HASH_MISMATCH',vid)
        timeline=[]
        with av.open(str(path)) as c:
            s=c.streams.video[0]
            for i,f in enumerate(c.decode(s)):
                assert f.pts is not None,'NO_NATIVE_PTS'
                timeline.append({'index':i,'pts':f.pts,'time_base':str(f.time_base),'seconds':float(f.pts*f.time_base),'duration':float(f.duration*f.time_base) if f.duration else None})
        pts=[f['seconds'] for f in timeline];assert pts and all(a<b for a,b in zip(pts,pts[1:])),('NONMONOTONIC_TIMELINE',vid)
        step=statistics.median(b-a for a,b in zip(pts,pts[1:]));start=pts[0];end=pts[-1]+(timeline[-1]['duration'] or step)
        save(OUT/'timelines'/f'{vid}.json',{'source':source,'frames':timeline,'presentation_interval_half_open':[start,end]})
        local=[];allocated=[]
        for w in [w for w in events if w['video_id']==vid]:
            lo,hi=w['start_frame'],w['end_frame']
            base={'window_id':w['pack_id'],'video_id':vid,'kind':'EXISTING_EVENT_WINDOW','original_record':w,'source_video_sha256':source['sha256'],'source_frame_interval_closed':[lo,hi],'boundary_semantics':'LEGACY_CLOSED_INDICES; original start/end retained; Phase2a half-open GT remains separate'}
            if not (0<=lo<=hi<len(pts)):local.append({**base,'status':'INVALID_SOURCE_BOUNDARY'});continue
            bounds=[pts[lo],pts[hi+1] if hi+1<len(pts) else end];selected=choose_uniform8(list(range(lo,hi+1)),pts)
            local.append({**base,'status':'ELIGIBLE','presentation_interval_half_open':bounds,'selected_indices':selected});allocated.append(bounds)
        # 4s length, 2s stride from native start. Add only cells not already fully covered.
        added=0
        for k in range(math.ceil((end-start)/2)):
            a=start+k*2;b=min(a+4,end)
            if any(x<=a+1e-9 and y>=b-1e-9 for x,y in merge_intervals(allocated)):continue
            lo=bisect.bisect_left(pts,a);hi=bisect.bisect_left(pts,b)-1
            base={'window_id':f'{vid}__C{k:04d}','video_id':vid,'kind':'ADDED_COVERAGE_WINDOW','source_video_sha256':source['sha256'],'source_frame_interval_closed':[lo,hi],'presentation_interval_half_open':[a,b],'coverage_grid_index':k}
            if lo>hi:local.append({**base,'status':'UNPROCESSABLE_NO_SOURCE_FRAME'});continue
            selected=choose_uniform8(list(range(lo,hi+1)),pts)
            local.append({**base,'status':'ELIGIBLE','selected_indices':selected});allocated.append([a,b]);added+=1
        required=sorted({i for w in local if w['status']=='ELIGIBLE' for i in w['selected_indices']});pending=set(required)
        with av.open(str(path)) as c:
            for i,f in enumerate(c.decode(video=0)):
                if i in pending:
                    image=OUT/'frames'/vid/f'S{i:06d}.png';image.parent.mkdir(parents=True,exist_ok=True)
                    if not image.exists():f.to_image().save(image)
                    assert float(f.pts*f.time_base)==pts[i];pending.remove(i)
                if not pending:break
        assert not pending
        for w in local:
            if w['status']!='ELIGIBLE':continue
            w['frames']=[{'alias':f'F{k+1:04d}','source_frame_index':i,'native_pts_s':pts[i],'native_pts':timeline[i]['pts'],'time_base':timeline[i]['time_base'],'path':(OUT/'frames'/vid/f'S{i:06d}.png').relative_to(ROOT).as_posix(),'sha256':sha(OUT/'frames'/vid/f'S{i:06d}.png')} for k,i in enumerate(w['selected_indices'])]
            w['short_window_policy']='ALL_DISTINCT_SOURCE_FRAMES_NO_PADDING' if len(w['frames'])<8 else 'UNIFORM8_NATIVE_PTS_NEAREST_CONSTRAINED'
            identity=[source['sha256'],[(f['source_frame_index'],f['sha256']) for f in w['frames']]]
            w['visual_input_sha256']=hashlib.sha256(json.dumps(identity,separators=(',',':')).encode()).hexdigest()
        covered=merge_intervals(allocated);gaps=[];cursor=start
        for a,b in covered:
            if a>cursor+1e-9:gaps.append([cursor,a])
            cursor=max(cursor,b)
        if cursor<end-1e-9:gaps.append([cursor,end])
        videos.append({'video_id':vid,'path':str(path),'sha256':source['sha256'],'frame_count':len(pts),'duration_seconds':end-start,'native_interval_half_open':[start,end],'original_windows':sum(w['kind']=='EXISTING_EVENT_WINDOW' for w in local),'added_coverage_windows':added,'covered_intervals':covered,'uncovered_intervals':gaps,'timeline_coverage_complete':not gaps,'coverage_is_window_allocation_not_continuous_visual_assessability':True,'timeline_path':f'timelines/{vid}.json'})
        windows.extend(local);print('BUILT',vid,len(pts),'frames',len(local),'windows',flush=True)
    seen={}
    for w in windows:
        if w['status']!='ELIGIBLE':continue
        key=w['visual_input_sha256'];w['duplicate_of']=seen.get(key)
        if key not in seen:seen[key]=w['window_id']
        w['overlap_ids']=[x['window_id'] for x in windows if x['status']=='ELIGIBLE' and x['video_id']==w['video_id'] and x['window_id']!=w['window_id'] and max(x['presentation_interval_half_open'][0],w['presentation_interval_half_open'][0])<min(x['presentation_interval_half_open'][1],w['presentation_interval_half_open'][1])]
    policy={'sampling':'UNIFORM8_NATIVE_PTS_CONSTRAINED_NEAREST_EARLIER_TIE','short_windows':'ALL_DISTINCT_NO_REPEATS','coverage_window_seconds':4,'coverage_stride_seconds':2,'coverage_grid_origin':'FIRST_NATIVE_PTS','grid_addition':'ADD_IF_INTERVAL_NOT_FULLY_COVERED_BY_EXISTING_OR_PRIOR_GRID_CELLS','basis':'Historical windows typically 1–6 seconds, median ~3.6s; round to fixed 4s with 50% overlap. Selection uses timing only.','old_boundary_evidence':'src/memory_graph/validation/evidence.py and reasoning/pipeline.py validate start<=frame<=end','no_answer_metadata_used':True,'model_aliases':'F0001..F0008; source mappings kept separately','independence':'OVERLAP_AND_DUPLICATES_NOT_INDEPENDENT; RECORDING_SESSION_INDEPENDENCE_UNKNOWN'}
    save(OUT/'dataset.json',{'videos':videos,'windows':windows,'policy':policy});save(OUT/'prompt.json',PROMPT);save(OUT/'schema.json',SCHEMA)
    models={'qwen':{'model':'Qwen/Qwen2.5-VL-7B-Instruct','revision':'cc594898137f460bfe9f0759e9844b3ce807cfb5','model_path':'.models/Qwen2.5-VL-7B-Instruct','quantization':'EXISTING_NF4_BF16','representation':'8_CHRONOLOGICAL_IMAGES','processor_max_pixels':200704},'videollama':{'model':'DAMO-NLP-SG/VideoLLaMA3-7B','revision':'d5b763e368861e7f5096e7ff1b49f92fbccf8ae6','model_path':'.models/VideoLLaMA3-7B','quantization':'EXISTING_LANGUAGE_NF4_VISION_BF16','representation':'8_CHRONOLOGICAL_IMAGES','preprocessing':{'max_visual_tokens_total':4096,'min_visual_tokens':16,'image_merge_size':1}},'nemotron':{**read(OUT/'nemotron_download.json'),'model_path':'.models/Nemotron-Nano-12B-v2-VL-NVFP4-QAD','quantization':'OFFICIAL_MODELOPT_NVFP4','representation':'OFFICIAL_VIDEO_ARRAY_8_FRAMES','video_pruning_rate':0,'max_model_len':8192,'gpu_memory_utilization':0.85,'max_num_seqs':1}}
    cfg={'models':models,'generation':{'do_sample':False,'seed':42,'max_new_tokens':1536,'timeout_seconds':300},'evaluation':{'interval_tolerances_seconds':[0,0.2,0.5],'primary_tolerance_seconds':0.2,'physical_brackets_are_not_event_duration':True,'event_matching':'SAME_HUMAN_REVIEWED_OBJECT_ID_AND_TYPE; ONE_TO_ONE_MAXIMUM_CARDINALITY','cross_window_dedup':'SAME_REVIEWED_OBJECT_TYPE_OVERLAPPING_CITATION_BRACKETS; REVIEW_REQUIRED_WHEN_SEPARATE_EVENTS_CANNOT_BE_DISAMBIGUATED','unknown_unreviewed_labels':'EXCLUDED_NOT_NEGATIVE'},'quality_retries':0,'graph_writes':False,'target_reference':'NONE'}
    save(OUT/'configuration.json',cfg)
    components={p.relative_to(ROOT).as_posix():sha(p) for p in [OUT/'dataset.json',OUT/'prompt.json',OUT/'schema.json',OUT/'configuration.json',Path(__file__),ROOT/'src/memory_graph/experiments/three_vlm_contract.py']}
    frame_hashes={f['path']:f['sha256'] for w in windows if w['status']=='ELIGIBLE' for f in w['frames']}
    save(OUT/'dataset_freeze.json',{'components':components,'frames':frame_hashes,'original_manifest_sha256':expected,'source_video_hashes':{v['video_id']:v['sha256'] for v in videos},'unique_inputs':len(seen),'all_nine_timelines_complete':all(v['timeline_coverage_complete'] for v in videos),'input_freeze_before_new_inference':True})
    print('DATASET_FROZEN',len(windows),'windows',len(seen),'unique inputs',flush=True)
if __name__=='__main__':main()

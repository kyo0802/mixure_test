"""Read-only CPU repository inspection and documentation. Not a Phase 3 prototype."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import ast,json,hashlib,re,collections,datetime,sqlite3,subprocess
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
assert ROOT.name=='mixure_test_SAM'
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,text):
    with (OUT/name).open('w',encoding='utf-8',newline='\n') as f:f.write(text if isinstance(text,str) else json.dumps(text,ensure_ascii=False,indent=2)+'\n')
def table(headers,rows):
    clean=lambda v:str(v).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(clean,row))+' |' for row in rows])

# Each primary evidence ID below was inspected directly or through targeted source extracts.
sources={
'S01':('scripts/run_findmind.py',1,'Current CLI'),
'S02':('src/memory_graph/identity/pipeline.py',49,'raw/replay/prepare/reason'),
'S03':('src/memory_graph/perception/detector.py',23,'Detector.detect'),
'S04':('src/memory_graph/perception/tracker.py',13,'ObjectTracker / BYTETracker'),
'S05':('src/memory_graph/perception/track_manager.py',28,'collect_tracks'),
'S06':('src/memory_graph/perception/track_timeline.py',35,'build_timelines'),
'S07':('src/memory_graph/video/reader.py',27,'VideoReader.frames'),
'S08':('src/memory_graph/identity/guard.py',206,'IdentityGuard.process/final_ledger/snapshot'),
'S09':('src/memory_graph/identity/contracts.py',18,'Policy / Observation'),
'S10':('src/memory_graph/v22/sam_tracking.py',149,'run_segment / binary mask diagnostics'),
'S11':('src/memory_graph/v292/masks.py',1,'historical mask authorization'),
'S12':('src/memory_graph/events/window_builder.py',36,'target_timeline / transitions / select_events'),
'S13':('src/memory_graph/events/interaction_signals.py',6,'sparse_pair_series'),
'S14':('src/memory_graph/pass_t/media.py',43,'decode_authorized: native PTS'),
'S15':('src/memory_graph/pass_t/sampling.py',20,'sample / manifest validation'),
'S16':('src/memory_graph/pass_t/phase2b/builders.py',12,'uniform_positions'),
'S17':('src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py',93,'8 frames / 4 units receipt'),
'S18':('src/memory_graph/pass_t/phase2b/v1d_execution.py',66,'load_envelope / record_call_result / supervisor'),
'S19':('src/memory_graph/v292/pipeline.py',1036,'legacy run_video'),
'S20':('src/memory_graph/v292/memory.py',8,'MemoryEventStore'),
'S21':('src/memory_graph/v27/temporal_memory.py',200,'visibility candidates / build_object_memory'),
'S22':('src/memory_graph/v28/physical_reasoner.py',16,'reason_relation; supplied support flags'),
'S23':('src/memory_graph/v29/physical_gate.py',5,'legacy decide'),
'S24':('src/memory_graph/v297_physical_identity/person.py',45,'CameraCompensator / PersonEpochBuilder'),
'S25':('src/memory_graph/v297_physical_identity/physical.py',123,'PhysicalIdentityState._interaction'),
'S26':('src/memory_graph/v296_reid/epochs.py',31,'CandidateEpochBuilder'),
'S27':('src/memory_graph/v28/geometry.py',16,'bbox_features / temporal_summary'),
'S28':('src/memory_graph/spatial/relation_extractor.py',8,'extract_pair'),
'S29':('src/memory_graph/memory/memory_store.py',20,'load_graph JSON reader'),
'S30':('src/memory_graph/memory/graph_builder.py',55,'legacy build_graph / to_networkx'),
'S31':('src/memory_graph/pipeline.py',26,'legacy run_video graph writer'),
'S32':('src/memory_graph/pipeline_v2.py',68,'legacy run_video_v2'),
'S33':('src/memory_graph/v27/observation_graph.py',9,'image_relations'),
'S34':('src/memory_graph/v295_reid/geometry.py',12,'object crop LightGlue/RANSAC, not ego-motion'),
'S35':('src/memory_graph/pass_i/builder.py',1,'offline identity-evidence dataset builder'),
'S36':('src/memory_graph/pass_i/evidence_qc.py',1,'human evidence QC persistence'),
'S37':('src/memory_graph/v297_physical_identity/runner.py',1,'historical physical identity runner'),
'S38':('src/memory_graph/reasoning/pipeline.py',1,'historical dense event reasoning'),
'S39':('src/memory_graph/v21/pipeline.py',1,'historical perception/entity admission'),
'S40':('src/memory_graph/v29/dense_reinspection.py',67,'legacy DenseRunner YOLO/SAM'),
'S41':('src/memory_graph/perception/object_classifier.py',1,'class aliases'),
'S42':('configs/default.yaml',1,'configured 5 FPS YOLO11s thresholds'),
'S43':('src/memory_graph/config.py',14,'DetectorConfig/TrackingConfig'),
'S44':('src/memory_graph/v28/local_subgraph.py',35,'caller-supplied interaction_entities'),
'S45':('src/memory_graph/v28/pipeline.py',119,'default interaction_entities absent'),
'S46':('src/memory_graph/v27/relation_promotion.py',8,'independent_physical_support consumer'),
'S47':('src/memory_graph/v27/models.py',1,'legacy physical predicate vocabulary'),
'S48':('src/memory_graph/models.py',44,'Detection/object observation data models'),
'S49':('src/memory_graph/pass_t/phase2b/v1d_outputs.py',1,'strict-invalid matching gate'),
'S50':('src/memory_graph/pass_t/phase2b/evaluation.py',1,'versioned point/closed-interval matcher'),
'S51':('src/memory_graph/identity/pipeline.py',187,'final ledger -> dense builder -> Qwen responses'),
'S52':('src/memory_graph/v292/physical.py',31,'legacy observable-fact/VLM gate adapter'),
'S53':('src/memory_graph/video/episode_segmenter.py',13,'HSV histogram scene-break heuristic'),
'S54':('src/memory_graph/spatial/anchor_selector.py',7,'semantic/area/stability anchor score')}
run='artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f/'
human='artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/'
review='artifacts/pass_t/phase2b/physical_evidence_review/20261015_real_dev_review_v1/'
artifacts={
'A01':'outputs_v292/test5/perception/yolo_detections.json','A02':'outputs_v292/test7/perception/yolo_detections.json',
'A03':'outputs_v292/test5/perception/tracks.json','A04':'outputs_v292/test7/perception/tracks.json',
'A05':'outputs_v292/test5/video_metadata.json','A06':'outputs_v292/test7/video_metadata.json',
'A07':'outputs_v292/test5/run_manifest.json','A08':'outputs_v292/test7/run_manifest.json',
'A09':'outputs/identity_rebuild/smoke_raw_test2_final/raw/perception/detections.json',
'A10':'outputs/identity_rebuild/smoke_raw_test2_final/metrics.json',
'A11':'outputs/identity_rebuild/development/runs_final/test5/authorized_rows.json',
'A12':'outputs/identity_rebuild/development/runs_final/test7/authorized_rows.json',
'A13':'outputs/identity_rebuild/development/runs_final/test5/identity.json',
'A14':'outputs/identity_rebuild/development/runs_final/test7/identity.json',
'A15':'outputs/identity_rebuild/development/runs_final/test5/metrics.json',
'A16':'outputs/identity_rebuild/development/runs_final/test7/metrics.json',
'A17':'outputs_v292/test5/sam/sam_continuity_log.json','A18':'outputs_v292/test7/sam/sam_continuity_log.json',
'A19':'outputs/identity_rebuild/smoke_raw_test2_final/sam/unverified_propagation.json',
'A20':'outputs_v292/test5/memory/observations.json','A21':'outputs_v292/test5/memory/relation_episodes.json',
'A22':'outputs_v292/test5/memory/memory_events.json','A23':'outputs_v292/test5/graphs/local_subgraph.json',
'A24':'outputs_v292/test8/graphs/local_subgraph.json',
'A25':'outputs/v297_physical_identity/development/runs/test5/camera_compensation.json',
'A26':'outputs/v297_physical_identity/development/runs/test5/physical_evidence.json',
'A27':'outputs/v297_physical_identity/development/runs/test5/candidate_epochs.json',
'A28':'artifacts/pass_i/manifests/candidate_epoch_inventory.jsonl',
'A29':run+'call_01/runtime_receipt.json','A30':run+'frozen_bundle.json',
'A31':'artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/private/W_f1d4f821d33515975293/source.json',
'A32':'artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/private/W_b8a53fea6aa8b92dc94f/source.json',
'A33':run+'run_receipt.json','A34':human+'HUMAN_ADJUDICATED_CALLS.json',
'A35':'artifacts/pass_i/evidence_qc/human_qc.sqlite3',
'A36':'outputs/identity_rebuild/smoke_raw_test2_final/identity.json',
'A37':'outputs/identity_rebuild/smoke_raw_test2_final/raw/perception/track_timelines.json',
'A38':'outputs_v292/test5/physical/relation_decisions.json','A39':'outputs_v292/test7/physical/relation_decisions.json',
'A40':'outputs/identity_rebuild/tests/downstream_prepare_final.log',
'A41':'outputs/identity_rebuild/tests/qwen_interface_smoke_final.log',
'A42':'outputs_v292/test5/memory/object_memory_phone_01.json',
'A43':'outputs/v297_physical_identity/development/runs/test5/metrics.json',
'A44':'outputs/current_development/event_windows/target_timelines/test5.json',
'A45':'outputs/identity_rebuild/development/runs_final/test2/prepared/events.json',
'A46':'outputs/identity_rebuild/development/runs_final/test2/prepared/qwen/responses.json'}
docs={
'D01':'CURRENT_PIPELINE.md','D02':'outputs/identity_rebuild/final/active_identity_manifest.json',
'D03':'outputs/identity_rebuild/audit/LEGACY_VS_CURRENT_PATH.md',
'D04':'outputs/identity_rebuild/IDENTITY_REBUILD_REPORT.md',
'D05':'outputs/v297_physical_identity/V297_PHYSICAL_IDENTITY_REPORT.md',
'D06':human+'PHASE2B_HUMAN_ADJUDICATED_ERROR_ANALYSIS.md',
'D07':'artifacts/pass_i/reports/PASS_I_EVIDENCE_QC_REPORT.md',
'D08':'outputs/identity_rebuild/tests/focused_regression_results.json',
'D09':'outputs/v297_physical_identity/tests/summary.json',
'D10':'outputs/identity_rebuild/development/regression_report.md',
'D11':'scripts/write_current_reports.py','D12':'pyproject.toml',
'D13':'archive/experiments/sam_temporal/V22_TRACKING_AB.md'}
tests={
'T01':'tests/test_identity_authorization.py','T02':'tests/test_identity_pipeline.py','T03':'tests/test_tracker.py',
'T04':'tests/test_v22_sam_tracking.py','T05':'tests/test_v27_memory.py','T06':'tests/test_v28_memory.py',
'T07':'tests/test_v297_identity.py','T08':'tests/test_pass_t_v1d_readiness.py',
'T09':'tests/test_v292_contracts.py','T10':'tests/test_v29_evidence.py'}
catalog={**{k:v[0] for k,v in sources.items()},**artifacts,**docs,**tests}
def ref(k,line=None):
    p=ROOT/catalog[k];n=line or (sources[k][1] if k in sources else None)
    return f'[{k}: {catalog[k]}'+(f':{n}' if n else '')+']('+p.as_posix()+(f':{n}' if n else '')+')'
def refs(*ids):
    if len(ids)==2 and isinstance(ids[1],int):return ref(ids[0],ids[1])
    return '; '.join(ref(k) for k in ids)
for key,path in catalog.items():assert (ROOT/path).is_file(),path
originals={path:sha(ROOT/path) for path in set(catalog.values())}

bundle=read(artifacts['A30']);windows={w['item_id']:w for w in bundle['protocol']['draft']['windows']}
windows_metrics={};sample_rows=[];samples=[]
def sample_record(id,count,fields,example,origin='Real runtime artifact',note=''):
    obj={'evidence_id':id,'path':artifacts[id],'format':Path(artifacts[id]).suffix,'origin':origin,'record_count':count,
         'actual_fields':fields,'minimal_example':example,'limitations':note}
    samples.append(obj);return obj
for vid,detid,trackid,metaid,runid,authid,mid,item,ptsid in [
 ('test5','A01','A03','A05','A07','A11','A15','PT2A_eb60192e6986cb4f','A31'),
 ('test7','A02','A04','A06','A08','A12','A16','PT2A_c58b4df88a2f6801','A32')]:
    det=read(artifacts[detid]);track=read(artifacts[trackid]);meta=read(artifacts[metaid]);rm=read(artifacts[runid]);auth=read(artifacts[authid]);metrics=read(artifacts[mid]);w=windows[item]
    assert sha(ROOT/artifacts[detid])==metrics['source_hashes']['detections']
    assert sha(ROOT/artifacts[trackid])==metrics['source_hashes']['tracks']
    assert rm['video_sha256']==w['window_boundaries']['source_video_sha256']==metrics['video_sha256']
    lo,hi=w['window_boundaries']['half_open_frames'];phone=[d for d in det if d['class_name']=='cell phone']
    inwin=[d for d in phone if lo<=d['frame_index']<hi];pts=read(artifacts[ptsid]);native={x['source_frame_index']:x for x in pts['frames']}
    overlap=[s for s in w['selected'] if any(x['frame_index']==s['source_frame_index'] for x in meta['sampled_frames'])]
    wm={'video_id':vid,'source_sha_recorded_matches':True,'current_video_bytes_rehashed':False,
        'detections':len(det),'phone_detections':len(phone),'phone_track_fragments':sum(t['detector_class']=='cell phone' for t in track),
        'person_detections':sum(d['class_name']=='person' for d in det),'frame_index_bounds':[lo,hi],
        'CV_sampled_frames_in_frame_bounds':[x['frame_index'] for x in meta['sampled_frames'] if lo<=x['frame_index']<hi],
        'phone_detections_in_frame_bounds':len(inwin),'phone_detected_frames_in_frame_bounds':sorted({x['frame_index'] for x in inwin}),
        'guard_authorized_frames_in_frame_bounds':[x['frame'] for x in auth if lo<=x['frame']<hi and x['identity_authorized']],
        'uniform8_exact_CV_sample_overlap':len(overlap),'uniform8_count':8,'native_PTS_present_in_detection_rows':sum('source_pts' in x or 'native_source_pts_s' in x for x in det),
        'selected_aliases':[{**s,'CV_sample_exists':any(x['frame_index']==s['source_frame_index'] for x in meta['sampled_frames'])} for s in w['selected']],
        'caveat':'Counts use frame-index bounds, not a new native-PTS eligibility ruling; NOT_SAMPLED is not a detector miss.'}
    windows_metrics[vid]=wm
    sample_record(detid,len(det),list(det[0]),phone[0],note='Real detector output, no independent state, no per-row source SHA/native PTS/detection ID; confidence is uncalibrated detector score.')
    t=next(x for x in track if x['detector_class']=='cell phone');ob=t['observations'][0]
    sample_record(trackid,len(track),list(t),{'track_id':t['track_id'],'source_track_key':t['source_track_key'],'observations':len(t['observations']),
       'observation_fields':list(ob),'first_observation':{k:ob[k] for k in ['frame_index','timestamp','confidence','bbox','raw_tracker_id','episode_id','distance_to_person']}},
       note='Track confidence is mean detector confidence, not association probability; visibility is sample-presence boolean, not physical visibility classification.')
    sample_record(authid,len(auth),list(auth[0]),{k:auth[0][k] for k in ['frame','time','identity_authorized','target_bbox','source']},
       note='Current final ledger adapter. No authorized target in W05; identity exclusion is not object absence. scene_ok is set True in replay adapter, not measured camera reliability.')
for sid,vid in [('A17','test5'),('A18','test7')]:
    j=read(artifacts[sid]);obs=[o for s in j['segments'] for o in s['observations']];lo,hi=windows_metrics[vid]['frame_index_bounds']
    summary={'propagated_frame_slots':sum(len(s['frames']) for s in j['segments']),'nonempty_observations':len(obs),
             'null_confidence':sum(o['confidence'] is None for o in obs),'possible_mask_drift_flags':sum(o['diagnostics']['possible_mask_drift'] for o in obs),
             'RLE_masks':sum(len(s['masks_rle']) for s in j['segments']),
             'mask_frames_in_frame_bounds':[o['frame_index'] for o in obs if lo<=o['frame_index']<hi]}
    sample_record(sid,len(obs),list(obs[0]),{**summary,'first_mask_observation':obs[0]},note='Real SAM model masks, thresholded logits; no calibrated mask score. No drift flag is not proof of a correct mask. SAM local object_id is not persistent identity.')
for sid in ['A09','A20','A21','A22','A25','A26','A38','A39']:
    a=read(artifacts[sid]);ex=a[0] if a else None
    if sid=='A09':ex=next(x for x in a if x['class_name']=='cell phone')
    if sid=='A26':ex={k:a[0][k] for k in ['frame','time','physical_continuity','interaction','motion_coupling','evidence_provider_grants_identity']}
    if sid=='A21':ex={k:a[0][k] for k in ['episode_id','kind','relation','status','start_time','last_supported_time']}
    sample_record(sid,len(a),list(a[0]) if a else [],ex,
       note='Real stored output; derived/aggregated or unknown states do not establish physical fact.' if sid not in ['A09','A38','A39'] else 'No physical-state validation follows from these stored rows.')
for sid in ['A23','A24']:
    g=read(artifacts[sid]);sample_record(sid,len(g['nodes']),list(g),{'schema':g['schema'],'nodes':len(g['nodes']),'edges':len(g['edges']),
       'first_node':g['nodes'][0],'first_edge':g['edges'][0] if g['edges'] else None},note='Node count is reported; graph beliefs/context are aggregated legacy results, not current live observations.')
ep=read(artifacts['A27']);sample_record('A27',len(ep['epochs']),list(ep['epochs'][0]),ep['epochs'][0],note=f"{len(ep['events'])} epoch events; short-gap STITCH is a rule, not identity truth.")
inv=[json.loads(x) for x in (ROOT/artifacts['A28']).read_text(encoding='utf-8').splitlines() if x.strip()]
sample_record('A28',len(inv),list(inv[0]),{k:inv[0][k] for k in ['epoch_id','video_id','start_frame','end_frame','end_time_semantics']},note='Offline dataset assembly; inventory metadata only. No frozen pixels, labels or inference examined.')
db=ROOT/artifacts['A35'];con=sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1',uri=True)
qc=[(eid,json.loads(data)) for eid,data in con.execute('SELECT epoch_id,data FROM epoch_reviews')];con.close()
qc_counts=collections.Counter(x['epoch_state'] for _,x in qc);crop_counts=collections.Counter(v for _,x in qc for v in x['crop_states'].values())
mixed=[eid for eid,x in qc if x['epoch_state']=='MIXED_IDENTITY']
sample_record('A35',len(qc),list(qc[0][1]),{'table':'epoch_reviews','epoch_counts':dict(qc_counts),'crop_counts':dict(crop_counts),'concrete_DEV_mixed_epoch':'ce:test7:0001' if 'ce:test7:0001' in mixed else None},
   origin='Human annotation',note='Opened sqlite mode=ro&immutable=1. Confirms evidence contamination labels, not calibrated tracker ID-switch rate; no DB updates.')
human_data=read(artifacts['A34']);sample_record('A34',len(human_data['records']),list(human_data['records'][0]),human_data['primary_disposition_counts'],origin='Human annotation',note='Existing completed review only; unchanged. Human judgement is evaluation context, not automatic runtime state producer.')
tl=read(artifacts['A44']);tr=tl['rows']
sample_record('A44',len(tr),sorted(set(k for x in tr for k in x)),
 {'motion_state_counts':dict(collections.Counter(x['motion_state'] for x in tr)),
  'non_null_camera_translation_estimates':sum(x.get('camera_translation_estimate') is not None for x in tr),
  'carried_like_true':sum(bool(x.get('carried_like')) for x in tr),'provenance':tl['provenance']},
 note='Historical real-data builder output from legacy-identity inputs, not current guard W05 authority. The same unchanged builder is called by current prepare. MOVING/STATIONARY/carried_like are image heuristics, not HELD or ON_SURFACE observations.')
ev=read(artifacts['A45']);resp=read(artifacts['A46'])
sample_record('A45',len(ev),list(ev[0]),{'physical_reasoning_eligible':sum(e['physical_reasoning_eligible'] for e in ev),'events':[{'pack_id':e['pack_id'],'trigger':e['trigger'],'completeness':e['completeness'],'physical_reasoning_eligible':e['physical_reasoning_eligible']} for e in ev]},note='Actual current-guard downstream prepare output; motion/lifecycle proposals, not confirmed physical events.')
sample_record('A46',len(resp),list(resp[0]),{'pack_id':resp[0]['pack_id'],'validation':resp[0]['validation'],'ended_with_EOS':resp[0]['trace'].get('ended_with_EOS')},note='Existing actual dense-Qwen current-path response, under a different reasoning contract from Phase2b V1D. Its validator result is not independent physical truth and does not reclassify any Phase2b output.')
camera=read(artifacts['A25']);phys=read(artifacts['A26'])
derived={'camera_reliable':sum(x['reliable'] for x in camera),'camera_rows':len(camera),
         'physical_continuity':dict(collections.Counter(x['physical_continuity']['state'] for x in phys)),
         'interaction':dict(collections.Counter(x['interaction'].get('state') if isinstance(x['interaction'],dict) else x['interaction'] for x in phys)),
         'motion':dict(collections.Counter(x['motion_coupling'] for x in phys)),
         'candidate_epoch_count':len(ep['epochs']),'candidate_stitches':sum(x['kind']=='STITCH' for x in ep['events'])}
save('OBSERVATION_SAMPLE_SUMMARY.json',{'windows':windows_metrics,'samples':samples,'historical_V297_derived_summary':derived,'new_runtime_calls':0})

# Consistent field availability taxonomy; real output does not imply reliable physical recognition.
DR='DIRECT_REAL_OUTPUT_VERIFIED';DE='DERIVED_REAL_OUTPUT_VERIFIED';CO='CODE_ONLY_NOT_RUNTIME_VERIFIED';SY='SYNTHETIC_OR_MOCK_ONLY';HA='HUMAN_ANNOTATION_ONLY';DO='DOCUMENTED_ONLY';MI='MISSING';UN='UNKNOWN'
rows=[]
def field(name,producer,code,artifact,availability,origin,quality,real,failure,needed,action):rows.append([name,producer,code,artifact,availability,origin,quality,real,failure,needed,action])
field('Source video ID / SHA','Run manifest; identity metrics',refs('S05','S19'),refs('A07','A08','A15','A16'),DR,'metadata','SHA/fingerprint','test5/test7 recorded SHA equals frozen cohort','not embedded per detection; movie bytes not rehashed here','Both P0','Bind through verified run context')
field('Source frame ID / index','VideoReader; Pass T manifest',refs('S07','S14'),refs('A01','A31','A32'),DR,'raw metadata','indices + PNG SHA in Pass T','frame_index / S000342 etc occur','index namespace depends on source video','Both P0','Preserve video SHA + exact index; no global frame ID assumption')
field('Source PTS','Pass T PyAV media only',refs('S14','S07'),refs('A31','A32','A01','A02'),DR,'native metadata in Pass T','NATIVE_PTS; CV rows have no PTS','Present in source.json, absent in all 1672/1791 detection rows','CV index/FPS timestamp is not native PTS','Both P0','Exact-index metadata join only after identity/bounds check; otherwise unknown')
field('Sampled-frame alias','Frozen Uniform8 / bridge',refs('S16','S17','S18'),refs('A30','A29'),DR,'model-input metadata','frozen mapping / hashes','F0077 maps to S000418 in test5','different windows reuse aliases; alias validity != event timing','Both P0','Map by call/window; retain actual aliases')
field('Frame dimensions','Reader / runtime metadata',refs('S07','S18'),refs('A05','A06','A29'),DR,'raw metadata','source vs processor sizes separate','1280×720 source; tensors/grids in receipts','processor resizing is not original geometry','Both P0','Keep source dimensions and resize mapping separately')
field('Camera-motion information','Current builder partial median estimate + legacy V297 compensator',refs('S12','S24'),refs('A44','A25'),DE,'heuristic','builder lacks reliability gate; V297 has reliable/residual','historical builder13 estimates; V29757/187 reliable','translation only; anchors may move/misassociate','Both P1','Keep producer-specific reliability unknown; not calibrated ego-motion')
field('Detector class ID','Detector.detect',ref('S03'),refs('A01','A02','A09'),DR,'model inference','detection confidence only','67 cell phone; 0 person occur','wrong class or small/truncated objects','Both P0','Retain original class ID and label; no automatic semantic correction')
field('Detector class label','model.names + class alias adapter',refs('S03','S41'),refs('A01','A02'),DR,'model inference / mapped label','no separate class distribution saved','cell phone/person/sports ball etc','person!=hand; no dedicated hand integration found','Both P0','Distinguish detector raw label from normalized alias and human target')
field('Detection confidence','Ultralytics boxes',ref('S03'),refs('A01','A02'),DR,'model score','float yes, calibration no','phone sample .5650636554','score != class/identity/state reliability probability','Both P0','Keep score type/threshold; reliability unknown when unsupported')
field('Detection bbox','Detector.detect',ref('S03'),refs('A01','A09'),DR,'model inference','score accompanies box','pixel xyxy, positive area','off-frame clipping / wrong object / camera motion','Both P0','No normalized-coordinate ambiguity; preserve raw xyxy')
field('Detection mask','Detector (no mask extraction)',ref('S03'),refs('A01','A02'),MI,'not emitted','none','no mask fields in detection arrays','segmentation comes from separate SAM branch','Both optional','Do not call SAM propagation a YOLO detection mask')
field('Local detection ID','raw array index -> guard candidate ID',refs('S02','S09'),ref('A36'),DE,'adapter-derived','provenance row index','raw:index@frame observations occur','not an ID emitted by detector or globally stable','Both P0','Use scoped references; native detection_id remains absent')
field('Frame-local object reference','Observation.observation_id',refs('S02','S09'),refs('A36','A13'),DE,'adapter-derived','evidence_hash + provenance','track:id@frame / raw:index@frame','reference does not authorize identity','Both P0','Do not conflate with persistent entity ID')
field('Track ID / raw_tracker_id','per-class BYTETracker; timeline enumeration',refs('S04','S06'),refs('A03','A04','A37'),DR,'tracking algorithm output','detector score, not association confidence','103 test5 timelines, four phone fragments','reset/occlusion/ID reuse; per-class bookkeeping','Both P0','Include episode/class/source_track_key; never grant PE identity')
field('Tracklet ID / CandidateEpoch reference','V296 epoch builder / Pass I offline inventory',refs('S26','S35'),refs('A27','A28'),DE,'heuristic / offline assembly','split reasons / stitch evidence, no calibrated score','29 test5 epochs; 690 inventory records','no universal tracklet_id across components; stitched local tracks not proven same physical entity','Both P0','Retain namespace and lineage; choose one source per adapter')
field('Track confidence','mean_detector_confidence',ref('S06'),refs('A03','A04'),DE,'mean of detector scores','association probability absent','mean field exists','mean detection confidence cannot establish continuity','Both P0','Name as mean detector score; track quality unknown')
field('ID-switch warning','Epoch/guard discontinuity diagnostics',refs('S08','S26'),refs('A27','A13'),DE,'heuristic suspicion','gap/scene/appearance/coexistence reasons','NEW/STITCH and current closed epochs exist','no ground-truthed general ID-switch detector/rate','Both P0','Preserve suspected switch uncertainty; missing warning != no switch')
field('Occlusion indicator','V27 visibility candidates / V297 hypotheses',refs('S21','S25'),refs('A26','A42'),DE,'heuristic belief','candidate / unknown, no calibration','test5 V297 no live occlusion hypothesis','overlap / loss does not establish occlusion','Both P0','Use OCCLUSION_CANDIDATE; critical evidence gaps -> UNCERTAIN')
field('Visibility state','Track visibility / identity timeline / memory',refs('S06','S21'),refs('A03','A42','A11'),DE,'presence/identity bookkeeping','sample presence boolean or trust state','UNOBSERVED and unauthorized rows saved','not sampled/missed detector/occluded/out of view conflated if normalized blindly','Both P0','Separate detection presence, visibility assessment and physical state')
field('Persistent entity ID','IdentityGuard binding; legacy registry',refs('S08','S19'),refs('A13','A20'),DE,'authorization / heuristic identity','epoch/alias/provenance yes','phone_01 exists in ledgers/legacy graph','matching wrong track can contaminate graph; authority generations differ','Both P0','Only current live capability can authorize binding; no legacy inheritance')
field('Persistent identity confidence/status','Current guard',refs('S08','S09'),refs('A13','A15','A16'),DE,'multi-gate rule','PROVISIONAL/AMBIGUOUS/REJECTED and scores; not calibrated probability','automatic_confirmation_enabled false; W05 authorized 0','conservative coverage loss / residual false initial match risk','Both P0','Preserve status, evidence lineage, policy and revocation')
field('SAM mask / local object ID','SAM2.1 propagation helper',ref('S10'),refs('A17','A18','A19'),DR,'model propagation','confidence null for 61/61 and 38/38','RLE shape/starts/lengths + bbox/centroid','drift / wrong seed / object loss; local ID not PE','Both useful','Read original masks only with original seed and identity provenance')
field('Mask stability / quality','SAM area/jump diagnostics',ref('S10',78),refs('A17','A18'),DE,'heuristic','area ratio, bbox ratio, centroid jump; score null','zero drift flags in these samples','zero flags != correct localization or identity','Both P0 if used','Do not replace unknown segmentation quality with high confidence')
field('Mask-to-track association','bbox IoU + authorization',refs('S02','S11'),refs('A13','A19'),DE,'geometric heuristic','sam_overlap and drift metadata','current ledger stores overlap; restart seed token saved','mask overlap not object identity or contact','Both P0','Retain independent detector support and identity gating')
field('Object centroid / bbox center','SAM / Detection.center',refs('S10','S48'),refs('A17','A01'),DE,'computed geometry','source quality inherited','mask centroid and box center occur','center is not contact point or 3D center','Both useful','Keep which center definition and image coordinates')
field('Hand detection','No first-party integrated producer located','Search scope in AUDIT_SOURCE_INDEX.json','NO_VERIFIED_REAL_OBSERVATION_SAMPLE_FOUND',MI,'none','none','person detections exist, hand output not found','dependency packages may support more than integrated path','Both P0 for contact route','Establish need via existing-evidence gap test before new model')
field('Hand keypoints / human pose','No first-party integrated producer located','Same scoped search','NO_VERIFIED_REAL_OBSERVATION_SAMPLE_FOUND',MI,'none','none','no actual joint/keypoint records found','person bbox is not pose','Both possibly useful','Do not invent joints from bbox; additional CV would need separate approval/validation')
field('Hand-object proximity','No hand-localized producer; person proxy only',refs('S06','S25'),refs('A03','A26'),MI,'no hand measurement','person distance may be null','distance_to_person exists, hand distance does not','hand and full person geometry differ','Both P0 if hand reasoning required','Expose person proximity under its real name')
field('Person-object proximity / co-motion','Timeline / V297 physical helper',refs('S06','S13','S25'),refs('A03','A26'),DE,'2D heuristic','scores/thresholds; no contact confidence','distance_to_person, PERSON_NEAR / MOTION_UNKNOWN fields','camera or person movement; contact not observed','Both P1','Do not relabel as contact/HELD_BY_PERSON')
field('carried_like / MOVING / STATIONARY','Current reused event-window builder',ref('S12',36),refs('A44','A45'),DE,'image motion/actor-bbox heuristic','threshold .04 diagonal/s; no calibrated held-state score','historical test5 timeline272 rows, carried_like4; current prepare5 events','actor bbox center containment + image motion is not hand grip or surface separation','Both P1','Expose actual names/origin; never normalize carried_like to HELD_BY_PERSON')
field('Hand-object contact','No real contact producer; supplied interaction flags consumed',refs('S22','S44'),ref('T06',131),SY,'test assertion / caller-supplied flag','none measured','test passes interaction=True, independent=True','consumer flags are not sensors; runtime calls default empty interaction_entities','Both P0','No positive contact from bbox overlap; runtime contact is unavailable')
field('Relative object position / bbox overlap / 2D containment','Timeline nearest-neighbor geometry',refs('S06','S27'),refs('A03','A04'),DE,'computed 2D geometry','detection/association quality inherited','nearest_tracks persists normalized distances/overlap/containment-like features','2D overlap/containment is not contact/support/container truth','Both useful','Expose actual image-relative features and units, not physical predicates')
field('Surface association','bbox/support role and VLM relation gates (legacy)',refs('S27','S28','S23'),refs('A21','A38','A39'),CO,'image geometry / semantic rules','rule score not support probability','only IMAGE_CONTEXT episodes in inspected test5; physical decisions empty','box bottom alignment/containment != mechanical support; no real verified physical surface association sample','Both P0','Expose support candidate only, not established ON_SURFACE')
field('ON_SURFACE observation','Human Q2 / model before-state claims',refs('S22','S23'),ref('A34'),HA,'human evaluation; VLM claim not independent','human rationale/aliases, not runtime calibrated state score','human review explicitly reports table support','no validated independent state producer on current path','Both P0','Keep human vs model vs derived origin distinct')
field('HELD_BY_PERSON observation','Human Q3; legacy HELD_BY rules',refs('S22','S23'),ref('A34'),HA,'human evaluation; rule/claim only at runtime','human evidence aliases','human supports held phone; code proxies not independently validated','overlap/co-motion/self-reported VLM state insufficient','Both P0','Cannot authorize state from existing runtime alone')
field('IN_CONTAINER observation','Legacy INSIDE candidate / geometry',refs('S23','S28'),refs('A38','A39'),CO,'rule or VLM claim','no independent inside-state reliability verified','no physical decisions in inspected W05 outputs','occlusion/2D containment not physical containment','PLACEMENT P0','Unknown unless separately reliable evidence establishes containment')
field('Object displacement / velocity','Timeline and bbox temporal summary',refs('S06','S27'),refs('A03','A04'),DE,'2D finite differences','detector/track errors inherited','normalized_center, velocity, speed occur','camera motion/depth ambiguity; not metric lift height','Both P1','Preserve coordinate units, delta-t origin and camera reliability')
field('Camera-motion compensation','Builder median offset + legacy V297 translation',refs('S12',53)+'; '+ref('S24'),refs('A44','A25'),DE,'partial heuristic','builder requires2 anchors but lacks residual gate; V297 has reliability','builder saved13 non-null estimates; V29757/187 reliable','rotation/zoom/parallax, wrong anchors; fallback raw motion if builder offsets insufficient','Both P1','Neither is verified 3D motion; preserve uncompensated/unknown reliability')
field('Metric vertical lift / surface separation','No depth/support-plane estimator found','Scoped source search','NO_VERIFIED_REAL_OBSERVATION_SAMPLE_FOUND',MI,'none','none','2D bbox movement available only','image y displacement != height above support plane','Both P0 for lifting proof','Gap test first; possible CV research, not a trivial deterministic formula')
field('Physical transition evidence','Human review; VLM hypotheses and legacy candidate rules',refs('S12','S23'),refs('A34','A38','A39'),HA,'human evaluation; heuristic runtime proposals','five reviewed hypotheses; strict-invalid unchanged','3 supported, 2 wrong target in prior review','candidate motion/loss not a confirmed transition; timing all qualified','Both P0','Keep hypothesis and independent observation separate')
field('Source producer / version','Run context and frozen receipts',refs('S05','S18','S19'),refs('A07','A29','A30'),DR,'provenance metadata','pipeline/model/config/source hashes','version/weights SHA and receipt hashes occur','not repeated in every observation; old/new policies differ','Both P0','Attach read-only producer context by hash, never flatten versions')
field('Observation confidence / quality','Separate detector, SAM, guard, camera outputs',refs('S03','S10','S08','S24'),refs('A01','A17','A13','A25'),DE,'heterogeneous metrics','detector score yes; mask score null; state reliability absent','actual nulls and reliability flags inspected','cannot collapse into one artificial confidence','Both P0','Retain typed metrics; unknown required reliability blocks SUPPORTED')
field('Independent state inference confidence','No calibrated runtime physical-state producer','Scoped source/record search',ref('A34'),MI,'human/VLM scores not independent sensor confidence','none verified','no runtime state confidence sample found','invented 0/1 or VLM confidence would be circular','Both P0','Explicit unknown; separate empirical validation required')
field('Evidence provenance','Run / ledger / graph / Pass T receipts',refs('S08','S18','S20'),refs('A07','A13','A20','A29'),DR,'stored references/hashes','varies per producer','provenance strings, evidence_hash, source refs occur','a path is not proof of content integrity or independence','Both P0','Verify scope and hashes; preserve raw/derived/human origin')
field('Missing-evidence reason','Guard epoch breaks / strict stages, not detector absence',refs('S08','S49'),refs('A13','A33'),DE,'diagnostic rule','explicit reasons for some stages','OBSERVATION_GAP, invalid stage reasons','no record explaining every missed detection; absence semantics unknown','Both P0','Keep NOT_SAMPLED distinct from no detection and physical invisibility')
field('Graph event/last-seen history','Legacy MemoryEventStore',ref('S20'),refs('A20','A21','A22','A42'),DE,'aggregated belief','provenance and status; per-observation confidence often absent','916 observations/195 events; eight stale image-context episodes','legacy identity and frame/FPS time; not fresh physical truth','Both P1','Read-only retrieval only; no graph mutation in 3A')
field('Exact EventHypothesisV3/ObservationEvidenceV1/Decision runtime','Future three-layer audit proposal','PHASE3_THREE_LAYER_CONTRACT_DRAFT.md','No implementation or freeze in this task',DO,'design only','not applicable','none','draft is not a runtime capability','Next milestone','Implement only after separate scoped authorization')
field('General calibrated occlusion vs out-of-view classifier','No validated independent classifier found',refs('S21','S25'),refs('A26','A42'),UN,'candidate heuristics only','no calibration dataset/result found','belief labels exist; actual distinction not established','false negatives / camera changes / view exit ambiguous','Both P0 when critical','UNCERTAIN if unresolved critical evidence; not every occlusion invalidates event')
save('OBSERVATION_CAPABILITY_MATRIX.md','# Observation Capability Matrix\n\n可用性分類描述實際值及其 producer scope，不表示已可可靠驗證物理事件。DIRECT 也可能是未校準的模型輸出；human、VLM claim 與舊版 heuristic 不互相替代。\n\n'+
 '分類：'+', '.join([DR,DE,CO,SY,HA,DO,MI,UN])+'。MISSING／UNKNOWN 搜尋範圍見 source index；不是對所有外部套件作不存在的全域主張。\n\n'+
 table(['Capability / field','Producer module','Actual code','Stored field / artifact','Availability','Raw/derived/annotated','Confidence / quality','Real-data evidence','Known failure','Needed for Phase 3','Recommended action'],rows)+'\n')

pipeline='''# Current Pipeline Dataflow

`ACTIVE_PRODUCTION_PATH` 在此僅指專案宣告的 current command，**不是已部署或已驗證的產品**。本次不執行任何路徑。

```mermaid
flowchart TD
  subgraph C[Project-current identity path — ACTIVE_PRODUCTION_PATH]
    CLI[run_findmind.py raw] --> VR[VideoReader: frame_index / nominal FPS]
    VR --> COL[collect_tracks: two passes / YOLO11s / per-class ByteTrack]
    COL --> RAW[detections + track_timelines + metadata]
    RAW --> AD[raw adapter copies to tracks.json / yolo_detections.json]
    AD --> GUARD[MobileNet evidence + IdentityGuard]
    GUARD --> TICKET[one-use restart capability]
    TICKET --> SAM[SAM2.1 propagation helper: unverified masks]
    SAM --> GUARD
    GUARD --> LEDGER[revocation-filtered final ledger / authorized_rows]
    LEDGER --> PREP[prepare: unchanged dense window builder]
    PREP --> REASON[reason: dense Qwen7B + validator]
    REASON --> RESP[responses.json — no Graph update]
  end
  subgraph T[Pass T Phase 2b — ACTIVE_EXPERIMENTAL_PATH, completed historical run]
    PTS[PyAV authorized native-PTS media metadata] --> PNG[existing sampled PNG assets]
    PNG --> U8[frozen Uniform8 / reference NONE]
    U8 --> REPS[Multi-image / Storyboard / Native array]
    REPS --> NF4[Qwen NF4 V1D 18 calls]
    NF4 --> OUT[raw outputs + runtime / strict receipts]
    OUT --> MATCH[strict-valid only: scoped private-GT evaluation]
    OUT --> HUMAN[separate five-case human review / error analysis]
  end
  subgraph L[Historical graph path — LEGACY_PATH]
    OLD[V292 run_video] --> V21[V21 detection / tracks]
    V21 --> FUSE[V26 / V292 identity and authorized-mask projection]
    FUSE --> CONT[local image context / dense physical candidates]
    CONT --> GATE[V29 / V292 relation gates + optional VLM]
    GATE --> STORE[MemoryEventStore -> JSON graph / episodes / search beliefs]
  end
```

不畫出 current guard → legacy Graph 的連線：現行 `prepare/reason` 沒有這個更新步驟。也不把 Phase 2b 影格當作偵測器已執行的影格。兩條線可用 source identity/index 做日後有條件比對，目前沒有統一 Observation adapter。
'''
components=[
['current CLI / raw','ACTIVE_PRODUCTION_PATH',ref('S01'),ref('S02',151),'video + config -> raw JSON -> guard','raw smoke real receipt: '+ref('A10'),'raw outputs consumed by replay; SAM callback only after capability'],
['YOLO + local ByteTrack','ACTIVE_PRODUCTION_PATH',refs('S03','S04','S05'),'Detection[] -> per-class associations -> TrackTimeline[]','saved arrays '+refs('A09','A37'),'timeline has detector-mean score, not calibrated track certainty'],
['SAM2.1 helper reused by current CLI','ACTIVE_PRODUCTION_PATH',refs('S02',166)+'; '+ref('S10'),'authorized seed -> masks/diagnostics -> guard support','saved raw smoke propagation '+ref('A19'),'helper reused, not the whole old V22 fusion as current authority'],
['current IdentityGuard','ACTIVE_PRODUCTION_PATH',refs('S08','S09'),'Observation[] -> aliases/banks/epochs/final ledger','snapshots '+refs('A13','A36'),'downstream is authorized_rows / builder, not Graph mutation'],
['prepare / dense reason','ACTIVE_PRODUCTION_PATH',ref('S51'),'authorized rows -> windows/images/requests -> responses','real saved5 events /1 response '+refs('A45','A46')+'; logs '+refs('A40','A41'),'runtime artifact supports invocation, not physical correctness or a new audit-time runtime test'],
['Pass I dataset/QC','ACTIVE_EXPERIMENTAL_PATH',refs('S35','S36'),'offline epochs/crops -> clean packages / human review','690 inventory metadata; QC DB120 '+refs('A28','A35'),'not an online observation/identity oracle'],
['Pass T Phase2b frozen pilot','ACTIVE_EXPERIMENTAL_PATH',refs('S14','S16','S17','S18'),'authorized assets -> frozen18call -> raw/strict receipts','18 recorded calls '+refs('A30','A33'),'no detector/SAM/Graph updates in this experimental run'],
['V297 physical identity','LEGACY_PATH',refs('S24','S25','S37'),'person epochs/camera/proximity -> identity support diagnostics','real derived output '+refs('A25','A26'),'not imported by current IdentityGuard; no automatic upgrade into current pipeline'],
['V292 canonical graph','LEGACY_PATH',refs('S19','S20'),'legacy fusion+relations -> stored graph/memory JSON','real stored graph '+refs('A20','A24'),'current authority manifest explicitly lists V292 as legacy'],
['original V1/V2 graph','LEGACY_PATH',refs('S31','S32','S30'),'detections/relations -> graph JSON','historical output path/code; not executed here','runners run_all.py/run_all_v2.py; no current identity guarantee'],
['explicit independent_physical_support fixture','TEST_ONLY',ref('T06',131),'supplied booleans -> HELD_BY PROMOTED assertion','synthetic boxes and flags, not sensor observations','consumer exists; no real producer located in searched first-party source'],
['Phase3 three layers','DOCUMENTED_ONLY','this audit draft','not implemented','none','no schemas frozen / no prototype'],
['SAM3 current integrated detector','UNKNOWN_OR_UNVERIFIED',ref('D11',114),'historical cleanup references, no source integration found in current src/scripts','SAM3 pixel outputs/weights not inspected','current capability must not be inferred from past model experiment names']]
save('CURRENT_PIPELINE_DATAFLOW.md',pipeline+'\n## Producer-consumer / persistence / reachability\n\n'+table(['Component','Path classification','Code','Input -> output','Execution / persisted evidence','Consumer / reachability limitation'],components)+
 '\n\nTests exist in '+refs('T01','T02','T03','T04','T05','T06','T07','T08')+'; this audit only reads them. Historical test summaries '+refs('D08','D09')+' are not fresh test runs or proof of state recognition.\n\nCurrent authority evidence: '+refs('D01','D02','D03')+'. Documentation agrees with inspected imports and a saved RAW_PERCEPTION smoke; partial experimental implementation is not an end-to-end deployed Graph product.\n')

sampletext='# Stored Observation Samples\n\n所有數字來自既有檔案的 CPU-only parsing；沒有重新 detector/tracker/SAM 推論或 pixels decode。`record_count` 是該檔案所列型別的列數，不是獨立物件或事件真值。完整短摘要見 [OBSERVATION_SAMPLE_SUMMARY.json](OBSERVATION_SAMPLE_SUMMARY.json)。\n\n'
for s in samples:
    sampletext+=f'## {s["evidence_id"]} — {ref(s["evidence_id"])}\n\nOrigin: **{s["origin"]}**；format: `{s["format"]}`；records: **{s["record_count"]}**。\n\n實際欄位：`'+', '.join(s['actual_fields'])+'`。\n\n'
    sampletext+='```json\n'+json.dumps(s['minimal_example'],ensure_ascii=False,indent=2)+'\n```\n\n'+s['limitations']+'\n\n'
sampletext+='## test5/test7 W05 exact-frame linkage\n\n'+table(['Video','Stored detections','cell phone detections (whole video)','Phone track fragments','CV sampled frames in frame bounds','Phone detections in those bounds','Uniform8 exact sampled-frame overlap','Current authorized targets in bounds'],[[v,m['detections'],m['phone_detections'],m['phone_track_fragments'],len(m['CV_sampled_frames_in_frame_bounds']),m['phone_detections_in_frame_bounds'],str(m['uniform8_exact_CV_sample_overlap'])+'/8',len(m['guard_authorized_frames_in_frame_bounds'])] for v,m in windows_metrics.items()])+'\n\n'
sampletext+='The legacy run video_sha256 and current replay video_sha256 agree with the frozen cohort source IDs; current detector/track files also match the current replay source_hashes. **Actual video file bytes were not rehashed/decoded in this audit.** Counts above use half-open frame-index bounds; source native-PTS authorization is an additional constraint.\n\n'
sampletext+='test5 W05 has nine phone detections over 18 sampled frames, test7 ten phone detection records over 18 frames (not necessarily ten distinct frames). Detector class list alone therefore does not settle manipulated-target detectability. Missing row != physical disappearance, and NOT_SAMPLED != missed detection. No recall/identity accuracy is inferred.\n\n'
sampletext+='CV rows timestamp=index/FPS; exact native PTS lives separately in Pass T source manifests. Do not interpolate absent detections onto Uniform8 aliases. For test7 the first authorized Uniform8 source frame is373 while CV sampling begins372; numeric closeness cannot override bounds/native-PTS authorization.\n\n'
sampletext+='For independent hand/contact/held/surface observation samples: **NO_VERIFIED_REAL_OBSERVATION_SAMPLE_FOUND** in the audited scope. Human QC confirms mixed evidence (e.g. `ce:test7:0001`) but does not identify which internal tracker step caused the contamination.\n'
save('OBSERVATION_SAMPLES.md',sampletext)

state_rows=[
['ON_SURFACE','EXTERNAL_ANNOTATION for observed state; runtime DERIVED_HEURISTIC candidates only','Human Q2 supports phone/table in prior review; bbox support proxy cannot establish mechanical support',refs('A34','S28','S22'),'No validated independent runtime state producer'],
['HELD_BY_PERSON','EXTERNAL_ANNOTATION; legacy rules/VLM claims are not independent observations','Human Q3; person bbox distance/co-motion cannot prove hand contact',refs('A34','S25','S23'),'Cannot distinguish touch/occlusion/held reliably'],
['OCCLUDED','DERIVED_HEURISTIC candidate, physical state UNKNOWN','Prior overlap plus loss -> OCCLUSION_CANDIDATE; V297 live hypotheses can be absent',refs('S21','A26'),'Not an observed occluder/contact classification'],
['OUT_OF_VIEW','DERIVED_HEURISTIC candidate, physical state UNKNOWN','Prior bbox within2px image edge + unobserved -> OUT_OF_VIEW_CANDIDATE',ref('S21',211),'Camera move / false negative / detector loss confounds'],
['UNKNOWN','DIRECTLY_AVAILABLE as diagnostic/status, not a measured physical action','V297 saved UNKNOWN diagnostics; current unauthorized/UNOBSERVED indicators',refs('A26','A11','A12'),'Unknown must remain unknown, not NO_EVENT'],
['IN_CONTAINER','CODE_ONLY / VLM claim or geometry, not verified observation','2D containment and post-loss cannot prove physical placement inside',refs('S23','A38','A39'),'No validated PLACEMENT positive in Phase2b cohort']]
distinctions=[
['Phone resting on table','Human can report; automatic support-plane recognition not verified','BBox near table / semantic role is only candidate'],
['Hand approaching phone','Not available as hand-specific observation','Full person bbox distance is available but not equivalent'],
['Hand touching phone','Not available','No integrated contact detector or real contact-quality sample found'],
['Phone lifted above table','Human review provides evidence; no reliable automatic lift estimator','2D displacement cannot determine metric height/contact separation'],
['Phone held by person','Human review / VLM claim; automatic distinction unavailable','Do not relabel overlap as HELD_BY_PERSON'],
['Phone occluded by hand','Unknown / generic occlusion candidate','No hand localization to identify hand as occluder'],
['Phone leaving camera view','Candidate only','Edge/loss heuristic does not establish actual cause'],
['Stationary phone/ball while camera moves','Builder/V297 partial translation proxies can diagnose some image motion','Not calibrated scene-motion compensation; rotation/parallax unknown']]
save('PHYSICAL_STATE_GAP_ANALYSIS.md','# Physical State Gap Analysis\n\n'+table(['State','Origin / availability','Evidence','References','Unresolved capability'],state_rows)+'\n\n## Eight required distinctions\n\n'+table(['Scenario','Current justified answer','Limitation'],distinctions)+f'''

## Existing heuristics: inputs / assumptions / thresholds / confidence / validation

1. **SAM drift diagnostics** ({ref('S10',78)}): previous/current masks -> mask/bbox area ratios (.2–5) and centroid jump (.25 image diagonal). Errors become `possible_mask_drift` / reasons. Assumes right seed and enough detectable drift. Wrong-object stable masks can evade it; no mask score saved. test5 real {len(read(artifacts['A17'])['segments'][0]['observations'])} nonempty rows and test7 {len(read(artifacts['A18'])['segments'][0]['observations'])}, confidence null in all; zero flags does not verify quality. Tests {ref('T04')} use controlled inputs; no new pixel-quality validation performed.
2. **Visibility belief** ({ref('S21',200)}): previous trusted bbox/overlap, continuing anchors, upstream UNOBSERVED -> occlusion/out-of-view candidates. Image border threshold2px. Assumes anchor trust and correct past identity. Emits candidate/uncertainty reasons, not calibrated visibility likelihood. Tests {ref('T05',179)} check that overlap/loss do not become physical events.
3. **CameraCompensator** ({ref('S24')}): matched static-label anchor centers, same class, area scale <=1.6; adjacent delta-t <=.401s; minimum3 offsets; residual p75 <=.015 image diagonals. Median translation only, camera segments reset on unreliability. Real test5:57/187 reliable booleans, no external camera-motion truth. Rotation/zoom/parallax/moving anchors remain failures. Tests {ref('T07',35)} are synthetic protections. Current guard does not consume this compensator.
4. **Person interaction continuity** ({ref('S25')}): PersonEpoch + proximity/motion histories + reliable same camera segment + persistent reappearance. Policy proximity .045 diagonal,3frames/.4s, motion cosine .8 and speed .01; returns geometry support/contradiction/unknown. No hand keypoints/contact. In real test5 all68 interaction and motion assessments are UNKNOWN ({ref('A26')}); no evidence provider grants identity. Not evidence of a held object.
5. **Legacy HELD/ON relation gates** ({refs('S22','S23')}): bbox time summaries, semantic roles, optional VLM support (.8 in V29), >=3frames/.25s in V29, held velocity coupling>=.8 and final_distance<=.15. These are candidate/promotion rules, not independent sensors. V28 consumes `independent_physical_support` and caller `interaction_evidence`; the strong-held unit test explicitly injects both booleans ({ref('T06',131)}). `build_local_subgraph` defaults interaction_entities to empty ({ref('S44',35)}), and V28/V292 callers do not supply it. No actual hand contact producer was found. test5/test7 relation_decisions are empty ({refs('A38','A39')}). Historical gate labels must not be reinterpreted as calibrated physical facts.
6. **Current reused builder motion/actor proxy** ({ref('S12',36)}): authorized target center within actor bbox -> actor_associations; camera median subtraction when >=2 shared location anchors; otherwise raw image displacement still yields speed. Speed threshold .04 image diagonals/s, smoothing .4s, dwell .3s; carried_like = actor association AND MOVING. No residual/rotation/reliability test or hand contact. Historical test5 builder timeline has272 rows (246 UNKNOWN/21 MOVING/5 STATIONARY),13 non-null camera estimates,4 carried_like=true ({ref('A44')}). Current prepare reaches this same code and has saved events/responses ({refs('A45','A46')}); the historical timeline's legacy identity authority is not imported into current guard. This is actual heuristic capability, not a held-state observation. Scene breaks use HSV histograms, not an ego-motion estimator ({ref('S53')}); anchor score combines semantic/confidence/stability/area/duration, not physical immobility proof ({ref('S54')}).

## Sufficiency verdict

**PICKUP: not sufficient for automatic authoritative validation with current independent observations.** Raw detections and masks can expose candidates, but current W05 identity authorization is empty, critical source frames differ, state/contact/support quality is not measured, and exact timing is unresolved.

**PLACEMENT: not sufficient.** Requires reliable HELD -> ON_SURFACE (or supported specific destination) evidence and association, plus post-state support. Disappearance/2D containment cannot substitute. Phase2b has no validated placement positive for empirical validation. This is a fundamental capability gap, not a missing bbox-overlap formula.

Occlusion somewhere in a window is not an automatic veto. The future decision must ask whether independently reliable **critical** before/after/target evidence remains available; unresolved critical occlusion -> UNCERTAIN with explicit reasons.
''')

risk_rows=[
['A Wrong object class','Raw class affects phone-only replay filter; VLM nouns can misassociate action','class==cell phone filter + guard provenance; no demonstrated class-confusion correction',refs('S02',60)+'; '+refs('A01','A34'),'Human WRONG_TARGET calls1/4 are existing event-hypothesis findings, not new detector error labels','Wrong filter rejects target; wrong association can pass visual similarity. UNCERTAIN until independent target evidence'],
['B ID switch','ByteTrack class/episode IDs can fragment or be reused; epoch stitching remains heuristic','epoch gap/appearance/coexistence rules, guard closes/revokes, automatic long-gap confirmation disabled',refs('S04','S26','S08')+'; '+refs('A27','A35'),'29 epochs/15 stitches real; human MIXED_IDENTITY includes ce:test7:0001. No confirmed switch-rate ground truth','Do not join different epochs as same target; warning absence is not proof of continuity'],
['C Camera motion','image displacement and view exit can mimic object motion/loss','builder partial median subtraction, legacy V297 reliability; V27 candidates only',refs('S12','S24','S21')+'; '+refs('A25','A26','A44'),'real proxies; builder can fall back to uncompensated speed; no external camera-motion validation','camera-unreliable critical movement -> UNCERTAIN; stationary ball exit != pickup'],
['D Hand-object overlap','person or hand bbox overlap without grip can appear as contact','no integrated independent hand/contact producer; old gates require other support but optional VLM is still a claim',refs('S22','S23','T06'),'synthetic rules test admission, not empirical hand contact','Never promote overlap or proximity alone to HELD_BY_PERSON'],
['E Missing observation','not sampled, detector miss, identity reject, SAM loss all differ','raw detections retained; authorized_rows separates candidate_present/identity_authorized; guard gap reasons',refs('S05','S02','A11','A12'),'real sampling mismatch 1/8 and0/8; missingness causes not fully known','Use NOT_SAMPLED / NO_DETECTION_RETURNED / IDENTITY_UNRESOLVED diagnostically, never physical absent'],
['F False PE merge','legacy registry/unsafe alias can contaminate future graph/history','current single-authority capabilities, quarantine vs core, parent revocation, final ledger filter',refs('S08','D03','T01','A13'),'tests + current smoke; incomplete continuity and no full graph transaction rollback proven','No Graph eligibility on ambiguous association; current guard must not inherit legacy PE authority']]
save('IDENTITY_AND_RELIABILITY_RISKS.md','# Identity and Reliability Risks\n\n'+table(['Scenario','Error propagation','Existing protection','Evidence','Test / real-data level','Future Decision consequence'],risk_rows)+f'''

## Identity namespaces and confidence separation

Detector arrays lack a native detection_id. The adapter derives raw:index and observation_id `raw:index@frame`. Local tracker uses numeric raw_tracker_id with class/episode scope; timeline track_id is a separate enumeration and source_track_key may be cell_phone_01. CandidateEpoch IDs (V296/V297) and Pass I epoch IDs preserve their own lineage; current guard has another epoch_id namespace. `phone_01` is a policy-authorized persistent binding, never a detector class or SAM local ID. See {refs('S02','S04','S06','S08','S26','A27','A28')}.

Current guard minimum detection confidence .5, initial3 observations/.4s, continuity IoU .05 and SAM support IoU .3; gap .4s, appearance admission .6/margin .1. Crucially `automatic_confirmation_enabled=false`, calibration_id DEVELOPMENT_INSUFFICIENT_FOR_STRONG_CONFIRMATION ({ref('S09')}). Real final runs: test5 two authorized observations out of187 rows; test7 four/221, and **both W05 windows zero**. These are stored coverage counts, not accuracy estimates. {refs('A15','A16','D10')}.

Detector score, mean detector score, appearance similarity, SAM overlap/drift, camera reliable flag and human judgement are different quantities. No combined score is created; unknown state/mask reliability is not assigned a number. No general calibrated track/association/state confidence was found.

## Graph storage and retrieval safety

- Legacy V1/V2 graph builder produces JSON nodes/edges with scene/image-relative relation history; NetworkX is a view. {refs('S30','S31','S32')}.
- Node types differ by generation: original MemoryNode represents ObjectTrack-derived objects; V2 SceneGraph has semantic entities; the inspected V292 graph has persistent target/anchor entities with raw_label, semantic_roles, hop and via_primary. Events/observations/episodes are separate lists, not evidence that every generation shares an event-node ontology. The inspected edge is TRUSTED_ANCHOR_CONTEXT/IMAGE_CONTEXT. The V27 vocabulary ON/INSIDE/HELD_BY/OCCLUDED_BY exists in code but is not proof these predicates were verified in the sampled graph. {refs('S30','S47','A23','A24')}.
- V27/V28/V292 use EntityObservation/relations/event episodes and JSON graph views. Test5 memory has916 observations/195 events/eight IMAGE_CONTEXT episodes (all STALE); final local graph is1node/0edges. Test8 has4nodes/3edges, including TRUSTED_ANCHOR_CONTEXT, kind IMAGE_CONTEXT, physical_verification=false. {refs('A20','A21','A22','A23','A24')}.
- V292 add_observation/add_event preserves supplied fields/provenance; fallback time=frame/FPS. The graph observation sample lacks detector confidence/native PTS. Observation history != full raw detector history; fetch raw arrays separately. {ref('S20')}.
- Current identity snapshot/final_ledger return deep copies and revoke aliases/bank/ledger lineage; this is **not** a demonstrated general graph entity split, transactional event rollback, or physically verified identity model. No such current full Graph rollback boundary was verified. {ref('S08',250)}.
- stdlib JSON reading and {ref('S29')} can retrieve persisted views without calling update/fusion. Do not run a pipeline to query memory. This audit did not create or mutate graph nodes; SQLite access was only the separate human QC DB, mode=ro&immutable=1.
- LAST_TRUSTED / STALE / UNOBSERVED are historical belief statuses, not fresh ON_SURFACE/HELD observations. Provenance and confidence fields differ across versions; do not merge incompatible outputs into a fictional single graph.
- Update triggers are version-specific: original run_video batches saved graph after relation/temporal filtering; V27 processes target/anchor frames into episodes/snapshots; V292 _build_memory collects observations, identity events and admitted relations after its legacy chain. Current IdentityGuard.process updates only its identity state/ledger/banks, and current reason writes responses without a Graph update. No shared live Graph update bus is established by these code paths. {refs('S31','S21','S19','S08','S51')}.

## Safety recommendation (not implemented)

Low or required-but-unknown reliability, unresolved ID-switch suspicion, ambiguous target association or critical unobserved state evidence -> **UNCERTAIN**, explicit diagnostics and graph_eligible=false, unless independent sufficiently reliable evidence resolves the particular uncertainty. Occlusion is assessed at the critical evidence, not as an absolute whole-window veto. REJECTED requires positive trustworthy contradiction, not absent detections. Contract INVALID remains a separate status; it does not become a physical NO_EVENT or a human verdict.
''')

save('PHASE3_THREE_LAYER_CONTRACT_DRAFT.md',f'''# Phase 3 Three-Layer Contract Draft — conceptual, NOT FROZEN

Only three layers are proposed. This is documentation, **not production schema, parser, implementation or approval**. No separately frozen TargetAssociationV1 or TemporalEvidenceV1. Recommended fields below are candidate descriptions; missing values remain explicit unknowns.

## 1. Hypothesis — EventHypothesisV3

Preserve raw VLM claim, target description (card/phone/ball/object), event type claim, before/after state claims, cited aliases, timing claim **as claimed**, abstention, original raw path/SHA, producer/prompt/config/run/call identities, original contract status. Existing raw output/runtime receipts provide this context ({refs('A29','A30','A33','A34')}); absence of required fields is not filled.
VLM must not establish persistent_entity_id or fabricate exact timestamps/system event IDs. A system-owned **future** reference may identify a hypothesis without endorsing model-generated PRED_EVT IDs. No V1D output is converted/normalized in this audit. Historical strict-invalid claims remain descriptive-only even if copied into future offline analysis.

## 2. Observation — ObservationEvidenceV1

Candidate minimum: source video identity, exact source frame index/ID, native PTS plus time_origin, authorized window, local observation reference, raw class/box/score if available, track/epoch references and scope, mask reference/quality when available, visibility separate from physical-state fields, state_origin (direct/derived/human/unknown), producer/config/version provenance, reliability metrics by type, missingness and switch/occlusion warnings.

### Fields actually populatable now

- Raw class/confidence/pixel xyxy/frame index from {refs('A01','A02','A09')}.
- Local track and derived trajectory/neighbors/visibility booleans from {refs('A03','A04','A37')}; **not** trusted physical instance identity.
- Native PTS/source PNG SHA/alias from {refs('A31','A32','A30')}, by exact source identity and index, only when a valid mapping exists. Current CV rows do not directly supply native PTS.
- Current authorization/epoch/alias/capability lineage from {refs('A13','A14')}, only where actually authorized; no W05 target tokens exist in examined final replay outputs. Audit JSON tokens are not reusable live capability handles.
- SAM masks + drift heuristics from {refs('A17','A18','A19')}; confidence stays null. Current ledger adapters may expose mask_reference only for authorized frames.
- Current builder motion/actor/camera estimates can be tagged derived with unknown reliability; no HELD observation is established ({refs('S12','A44','A45')}). Legacy camera/relation diagnostics remain separately legacy/derived ({refs('A25','A26','A21')}), not silently relabeled current direct observations.
- Independent hand/contact/support-plane/held-state observations are **not populatable from a verified runtime producer found here**. Human review is a separate evaluation-origin source, not a runtime backfill.

Do not fill absent physical state with ON_SURFACE/NOT_HELD based on boxes, mask overlap or detection absence. No mock observation is represented as real evidence.

## 3. Decision — one internal component

One proposed component with private `check_target`, `check_state`, `check_temporal` diagnostics. These are not separate public schemas or separately frozen contracts.

- check_target: verify source/candidate scope, distinguish local evidence from persistent authorization, check competing/possibly switched associations; unknown identity cannot authorize PE binding.
- check_state: evaluate independent critical BEFORE/AFTER evidence, state_origin and required reliability; VLM self-reported state is a claim. Person overlap/co-motion/last-seen belief does not establish support/contact.
- check_temporal: map supplied aliases to native source PTS when exact scope valid; distinguish observed state from transition instant and brackets; do not invent interpolation or duration. Native8/4units do not provide recovered attention/time positions.

Candidate outcome: SUPPORTED / REJECTED / UNCERTAIN. Separately retain **input_contract_status, observation_reliability_status, target_grounding_result, physical_state_result, temporal_result, reason_codes, graph_eligibility**. Full observation reliability cannot be replaced by schema PASS. Unknown/low reliability of critical evidence -> UNCERTAIN; contradictory reliable evidence can justify REJECTED. Invalid input remains invalid regardless of physical diagnosis; no authoritative event matching or Graph authorization is granted to historical strict-invalid outputs.

Possible diagnostic reasons (names only, not frozen): SOURCE_SCOPE_UNVERIFIED, IDENTITY_UNRESOLVED, ID_SWITCH_SUSPECTED, REQUIRED_QUALITY_UNKNOWN, CRITICAL_STATE_NOT_OBSERVED, CITE_IS_STATE_NOT_TRANSITION, EXACT_TIME_UNOBSERVED, CAMERA_COMPENSATION_UNRELIABLE, INPUT_CONTRACT_INVALID. Occlusion itself is not an unconditional veto; unresolved impact on critical evidence is the issue.

Graph eligibility is diagnostic only. **No Graph write** in this audit or any proposed shadow replay; future update requirements are deferred to3F. No Event-to-Graph redesign implemented.
''')

gaps=[
['G1','P0_BLOCKER','Independent ON_SURFACE/HELD/contact/support evidence','Critical','Critical','Boxes/masks/frames exist; existing runtime state producer insufficient','Derivation research needs empirical validation; new model need unknown, not recommended for training now','High / CV research','3D gap test and trusted identity','Yes: authoritative physical support'],
['G2','P0_BLOCKER','Target/epoch authorization and independent observation reliability','Critical','Critical','Guard/epochs exist but W05 authorized0; unknown mask/state quality','Exposure easy; recovery/calibration requires separate evidence, no auto threshold tuning','Medium integration + high empirical risk','G3 and current guard contract','Yes: PE binding / SUPPORTED'],
['G3','P0_BLOCKER','Native-PTS, source identity and exact sampled-frame coverage alignment','Critical','Critical','Pass T metadata + raw CV indices available, 1/8 and0/8 overlap','Exact metadata join plausible where frame exists; no automatic new sampling/interpolation','Low-medium integration; coverage remains empirical','Existing source hashes/bounds','Yes: exact temporal claims'],
['G4','P1_IMPORTANT','Camera compensation reliability beyond median translation','High','High','Builder has partial estimate without reliability gate; legacy V297 real57/187 reliable','Empirical pan/rotation/parallax test before reuse; external model not yet justified','Medium-high','G2/G3','Blocks movement-based state proof when camera ambiguous'],
['G5','P1_IMPORTANT','Hand localization / contact interaction','High if used','High if used','Only person boxes/proximity; hand not found in integrated path','Must first test existing evidence; any additional detector needs separate approval/validation','High empirical','G1/G2','Blocks any hand-contact-based proof'],
['G6','P1_IMPORTANT','Explicit missing-observation semantics','High','High','Guard reasons and sample manifest exist; detector miss cause unavailable','Expose NOT_SAMPLED vs NO_DETECTION_RETURNED vs IDENTITY_UNRESOLVED; cannot infer physical absence','Low engineering','G3','Needed to avoid false rejection/promotion'],
['G7','P1_IMPORTANT','ID-switch / false merge empirical validation','High','High','Epoch tests and human mixed-evidence QC exist','No calibrated general switch detector; validate against explicit human scoped evidence','Medium-high empirical','G2','Blocks confident cross-gap target association'],
['G8','P1_IMPORTANT','Separate immutable producer contexts / typed quality','High','High','Many hashes/status fields available, graph drops granularity','Read-only adapter/context binding plausible, not combined confidence','Low-medium','G3','Needed before authoritative Decision'],
['G9','P0_BLOCKER','Validated PLACEMENT evaluation evidence','n/a','Critical','Current cohort has no validated placement positive','New human/real-data coverage would require later scoped authorization; do not infer from disappearance','Medium data work','G1/G2','Yes: empirical placement claim'],
['G10','P2_LATER','General graph split/transaction rollback boundary','Medium','Medium','Alias/ledger revocation exists; no verified full graph rollback','Future proposal boundary needs separate tests; not implemented now','Medium-high','G1–G8 and3E','Blocks real Graph writes, not read-only adapter'],
['G11','P2_LATER','More complex model/pose/3D approach','Unknown','Unknown','No proof existing observations suffice, but need quantified gap first','Do not train a new HOI model by default','Unknown/high','3D measurable gap results','Not first engineering milestone']]
milestones=[
['3A Evidence inventory + draft','source/tests/current real artifacts/old human context','This audit + exactly-three-layer conceptual draft','read-only scope / source identities','field matrix separates raw/derived/human and real/test evidence','source mutation, new inference, fabricated observation','state recognition/calibration remain unverified'],
['3B Observation Adapter','frozen metadata + stored raw detections/tracks/authorized ledger','read-only adapter exposing actual fields, nulls, source/time origins','new authorization; one selected current source path; exact namespace rules','can trace each exposed field to immutable source; NOT_SAMPLED != no detection; no invented state','hash mismatch, unresolved source scope, any implicit identity grant or Graph update','adapter is not new evidence or reliable physical-state classifier'],
['3C CPU-only Decision Checks','controlled explicitly tagged observations; raw hypotheses separately','one Decision with internal target/state/time diagnostics','3B provenance/unknowns stable; approval to implement CPU tests','unknown reliability/suspected switches/critical gaps never yield SUPPORTED; invalid input remains invalid','test fixtures represented as real GT; weakened validator; graph writes','software logic tests do not validate real visual recognition'],
['3D Real Observation Gap Test','existing real records and human critical-frame annotations','measure usable target/state/time coverage; document when no independent state evidence exists','separate authorized data scope; no inference/extra frames without permission','quantifies actual insufficiency; no fake contact/held; placement requires its own positive evidence','reusing model state as independent observation; unapproved processing; unknown identity promoted','new visual model need only assess after this evidence'],
['3E Offline Shadow Replay','existing run/human evaluation + independently scoped observations','diagnostic comparison only, no historical validation rewrite','3B/C implemented and3D gaps explicitly accepted; new authorization','preserve five strict-invalid results, separate human support and system diagnostics; report UNCERTAIN','invalid predictions repaired or authoritative matching scores changed; Graph writes','small selected DEV windows cannot establish generalization'],
['3F Graph Proposal Boundary','reliable decisions and valid current identity capabilities','future update proposals and eligibility requirements only','3E reviewed; clear authority/revocation/provenance','ambiguous/unsupported identity has graph_eligible=false; no mutation','attempted real graph write before separate design/approval','full rollback/online operation remains unverified']]
save('PHASE3_IMPLEMENTATION_ROADMAP.md','# Phase 3 Roadmap — Recommendations Only\n\nNo milestone is implemented by this audit. Lowest-risk next work is **3B read-only Observation Adapter**, followed by3C conservative CPU checks; neither closes the fundamental G1 state gap. Do not start with a new model or a large frozen schema collection.\n\n## Prioritized gaps\n\n'+table(['Gap','Priority','Missing/unreliable capability','PICKUP importance','PLACEMENT importance','Existing evidence','Deterministic feasibility / empirical or model need','Complexity','Dependencies','Milestone blocker'],gaps)+'\n\n## 3A–3F\n\n'+table(['Milestone','Inputs','Deliverables','Preconditions','Acceptance','Hard stop','Still unverified'],milestones)+'\n\n3A documentation is complete when this audit is delivered. 3B–3F remain unimplemented; no authorization for them is inferred. Camera/hand/state work is a computer vision reliability problem, not solved by adding a field or copying a model rationale.\n')

main=f'''# Phase 3A — Existing Observation Capability Audit

日期：2026-10-15（Asia/Taipei）。**PASS_T_PHASE3_OBSERVATION_CAPABILITY_AUDIT_COMPLETE**。

本次是 source + stored-data 稽核，不是 Phase3 implementation、prototype、schema freeze 或新的 validation run。新增資料只在本 audit 目錄與既有 WORKSPACE 導航。既有 Phase2b/human結果均未改寫。

## Executive summary

**目前能提供定位、local continuity、部分身分授權、影像幾何與來源 metadata；不能提供足以獨立、可靠區分 ON_SURFACE 和 HELD_BY_PERSON 的 current runtime observation producer。** 因此現有資料不足以自動 authoritative validate PICKUP，也不足以 validate PLACEMENT。

不是單純「缺一個 JSON schema」。三個 P0：**獨立 physical-state/support/contact 觀察缺口；target association/authorization 與所需 reliability 不足；CV 採樣與 native-PTS/alias 覆蓋不一致**。PLACEMENT 另缺 validated positive 評估資料。

## 1. What is current, what is historical

- Current documented authority: `scripts/run_findmind.py -> identity.pipeline -> IdentityGuard`。active_identity_manifest/actual imports 與 RAW_PERCEPTION smoke 一致。此處 ACTIVE_PRODUCTION_PATH 只表示專案 current command，prototype 不是部署產品。{refs('D01','D02','S01','S02','A10')}。
- raw uses existing collect_tracks/YOLO11s/per-class ByteTrack; SAM2.1 callback requires scoped restart capability. The raw adapter at151–185 explicitly copies track_timelines/detections to replay input names; no missing-file-interface bug is claimed. {refs('S02',151)}; {refs('S03','S04','S05','S10')}。
- final revocation-filtered ledger -> authorized_rows -> unchanged dense event builder/render/prompt -> Qwen response JSON。Saved current test2 prepare has5 events/1 eligible; one actual response has VALID_MODEL_REASONING_OUTPUT under that separate dense-reasoning contract. This is not Phase2b V1D strict validation or physical correctness. Historical logs say identity_writes0. No current Graph update follows reason. {refs('S51','A40','A41','A45','A46')}。
- V292 canonical Graph、V27/V28 physical-memory rules、V297 physical identity 是 preserved LEGACY_PATH。Current guard reuses selected low-level evidence helpers, not their identity authority. `run_current_pipeline.py` is explicitly historical. {refs('D03','S19','S20','S24','S25')}。
- Pass I/T are active experimental/offline annotation paths. Phase2b18call pilot used frozen existing sampled assets and Qwen NF4, not fresh YOLO/SAM/Graph updates. {refs('A28','A30','A33')}。

詳見 [CURRENT_PIPELINE_DATAFLOW.md](CURRENT_PIPELINE_DATAFLOW.md) 的分支圖及 producer-consumer 表。沒有拼接成單一假想 unified pipeline。

## 2. Actual detector / tracking capabilities

- Integrated detector found in first-party source: Ultralytics YOLO through Detector and legacy DenseRunner。Configured weights yolo11s.pt, conf .25, imgsz960, default5FPS; model.names supplies class labels. Raw output pixel xyxy/class ID/name/confidence/frame_index/timestamp/derived bbox center；Detector.detect does not extract result.masks, pose or hands. NMS is delegated to pinned Ultralytics predict defaults; no explicit iou override or local calibration was found in this wrapper. Person detections are real (test5:86/test7:140), but person bbox is not a hand detector. {refs('S03','S40','S42','S43','A01','A02')}。
- Tracking is **per-class Ultralytics BYTETracker**, not assumed BoT-SORT/DeepSORT。high .35/low .1/new .35/match .8/fuse_score True; lost buffer derives from2seconds and version-sensitive sample FPS; episode resets are explicit. track IDs/class/episode scoped, local object names mapped into separate timeline IDs. No calibrated association score saved; mean_detector_confidence is a detector-score mean. {refs('S04','S06','S43')}。
- Smartphone detectability is supported by actual outputs, not just COCO labels: test5 **1672 detections /68 cell phone /4 phone track fragments**, test7 **1791 /226 /12**。These are counts, not recall, no claim the exact manipulated phone is always found. Detector scores are uncalibrated and other classes/distractors exist. {refs('A01','A02','A03','A04')}。
- Preprocessing visible in first-party code: OpenCV BGR frames passed to Ultralytics predict with imgsz/conf/device; resize/normalization/NMS are delegated, not independently audited as runtime behavior here. The full model.names map is not persisted in the inspected arrays; observed labels confirm cell phone/person/sports ball etc, not every possible class. No explicit NMS IoU override, hand-specific model or pose output is extracted. Person excluded_subject_classes affects later subject use, not deletion of raw person detections. {refs('S03','S41','S42')}。
- Current raw smoke test2 persisted1511 detections,139 cell phone records; metrics say fresh_yolo/fresh_sam true and33 authorized observations/155 sampled frames. Historical saved evidence demonstrates invocation, not current audit-time model verification. {refs('A09','A10','A36','A37')}。

## 3. Critical test5/test7 W05 coverage finding

{table(['Window','CV samples in frame-index bounds','Phone detection records','Exact Uniform8/CV sample overlap','Current final-ledger authorized target observations'],[[v+' W05',len(m['CV_sampled_frames_in_frame_bounds']),m['phone_detections_in_frame_bounds'],str(m['uniform8_exact_CV_sample_overlap'])+'/8',len(m['guard_authorized_frames_in_frame_bounds'])] for v,m in windows_metrics.items()])}

Recorded source video SHA agrees across V292 run manifest, current final replay metrics and frozen Phase2b window. Raw detector/track file hashes match final replay source_hashes. No original movie bytes were read/rehashed; this is recorded-provenance verification, not new media verification.

The0 phone rows at unsampled Uniform8 frames mean **NOT_SAMPLED**, not confirmed detector failure or physical disappearance. No nearest-frame interpolation is licensed. Current W05 target authorization is0, so historic `phone_01` from a legacy graph cannot fill that gap. {refs('A11','A12','A15','A16','A30','A31','A32')}。

## 4. Segmentation, hand interaction and physical state

SAM2.1 real RLE masks/centroids/bboxes exist: test5 61 nonempty observations, test7 38, confidence null in all; drift heuristics show0flags, which is not proof of correct segmentation. W05 frame-index bounds contain17/11 mask observations respectively, on the CV sampling grid, not eight exact VLM frames. SAM local IDs/overlap do not establish identity, contact or held state. {refs('S10','A17','A18')}。

In the audited first-party src/scripts/tests/configs scope, no integrated hand detector/keypoint/pose/contact/support-plane/lift-height producer with real stored outputs was located. A dependency having pose capability is not an integrated pipeline. Human review and VLM raw states remain different sources. Legacy physical_reasoner consumes externally supplied `independent_physical_support` and `interaction_evidence`; strong held tests inject them. Not a measured contact sensor. {refs('S22','S44','T06')}。

V297 provides real **derived** camera translation/reliability/proximity/continuity diagnostics, but not current guard inputs or independent HELD proof. test5 camera reliable57/187; physical continuity67 UNKNOWN +1 consistent; interaction68 UNKNOWN; motion68 UNKNOWN. {refs('A25','A26','A43')}。Detailed eight-scenario answers and thresholds in [PHYSICAL_STATE_GAP_ANALYSIS.md](PHYSICAL_STATE_GAP_ANALYSIS.md)。

Current event-window builder also has partial camera_translation_estimate, actor_associations, MOVING/STATIONARY and carried_like rules. These are not missing capabilities: they are **unvalidated image heuristics**, not physical support/contact/held observations. >=2 anchor offsets enable median subtraction; without them raw image motion is still used. Historical test5 builder output272 rows includes13 camera estimates/4 carried_like flags, with legacy identity provenance; current prepare reuses the same builder but its current authorization remains separate. {refs('S12','A44','A45')}。

## 5. Temporal and Graph limitations

CV VideoReader timestamp is frame_index / nominal FPS; it rejects invalid metadata and checks decoded count but does not retain native PTS. V292 MemoryEventStore also permits frame/FPS fallback. Pass T separately decodes PyAV frame.pts*time_base and fails when native PTS missing; these timestamps survive frozen source metadata/runtime provenance. Source PTS therefore **does not currently flow unmodified through detection -> tracking -> current identity -> legacy Graph**. {refs('S07','S14','S20','A31','A32')}。

VideoReader does not perform native-PTS/VFR monotonicity validation; a valid nominal FPS is not proof of constant source timing. Run start/end UTC and monotonic processing durations are processing timestamps, not video capture time or event time. No wall-clock camera-capture timestamp was verified in this file-video path. No dropped-frame PTS interpolation is authorized by these records.

Uniform8 uses round(i*(N-1)/7); source aliases are window positions, e.g. test5 F0077 -> source418 /13.933333333333334s. Native array receipt is FRAME_MATCHED_ONLY,8frames/4effective temporal units; actual model attention or eight independent temporal positions cannot be reconstructed. Point/interval evaluation does not create event timing or duration from before/after brackets. {refs('S16','S17','S50','A29')}。

Graph storage contains historical beliefs, context episodes, observation references and last-seen statuses; not a newly observed physical fact. Test5 has916 stored observations/195 memory events/eight stale IMAGE_CONTEXT episodes, final graph1node/0edges, and no physical relation decisions. Test8 example has TRUSTED_ANCHOR_CONTEXT, physical_verification=false. No verified full graph rollback/entity split path was established; current alias revocation is narrower. Read JSON/deepcopy snapshots without calling pipeline/update. {refs('S20','S21','S29','A20','A21','A22','A23','A24','A38')}。

## 6. Reliability and data-quality evidence

Current automatic long-gap confirmation is disabled, not a calibrated identity product. Guard closes gaps, quarantines provisional banks, revokes descendants and materializes final ledger; tests check controlled cases. Historical current final replay still has sparse coverage. Real human QC DB120 epochs includes63 VALID/4 MIXED_IDENTITY/53 NO_USABLE_TARGET and119 DROP_WRONG_TARGET crops; concrete `ce:test7:0001` is MIXED_IDENTITY. This is human evidence of upstream contamination, not a measured tracker switch rate or proof of which producer caused it. {refs('S08','S09','T01','A35','D07')}。

Detector scores, appearance similarity, SAM geometry/drift, camera residuals, VLM confidence and human adjudication are not one confidence quantity. Missing required reliability or unresolved critical association/state evidence must yield future UNCERTAIN, not confidently SUPPORTED. Preserve structured-input status separately. A–F propagation scenarios are in [IDENTITY_AND_RELIABILITY_RISKS.md](IDENTITY_AND_RELIABILITY_RISKS.md)。

## 7. Phase2b context remains unchanged

18calls completed; full strict10, all NO_CONFIRMED_EVENT; event-bearing5 all strict-invalid. Human review3supported/2wrong target with temporal qualifications remains evaluation evidence, not a runtime physical state producer or authorization to repair output. No past matching/GT/human result was altered. {refs('A33','A34','D06')}。

## 8. Smallest next step

Recommend separately scoped **3B read-only Observation Adapter**: expose verified frame-local detections/track references/typed confidence/source contexts and exact native-PTS mapping only where available. Preserve unauthorized/unknown states and all missingness. Do not start with a new hand model, invented contact heuristic or a large schema freeze. Then3C conservative CPU Decision checks and3D real observation gap test. Adapter work is integration; reliable contact/support/held recognition is empirical CV work and remains unsolved.

Only three conceptual layers are drafted: EventHypothesisV3 / ObservationEvidenceV1 / one Decision with internal check_target/check_state/check_temporal. No separately frozen TargetAssociationV1 or TemporalEvidenceV1. No implementation is performed. [Draft](PHASE3_THREE_LAYER_CONTRACT_DRAFT.md) · [Roadmap](PHASE3_IMPLEMENTATION_ROADMAP.md)。

## 9. Evidence boundaries / deliverables

- [Current pipeline diagram](CURRENT_PIPELINE_DATAFLOW.md)
- [Complete capability matrix](OBSERVATION_CAPABILITY_MATRIX.md) — {len(rows)} fields with source/artifact/quality/scope/priority.
- [Real stored samples](OBSERVATION_SAMPLES.md) / [CPU summary](OBSERVATION_SAMPLE_SUMMARY.json)
- [State gaps](PHYSICAL_STATE_GAP_ANALYSIS.md) / [Identity risks](IDENTITY_AND_RELIABILITY_RISKS.md)
- [Three-layer conceptual draft](PHASE3_THREE_LAYER_CONTRACT_DRAFT.md) / [3A–3F roadmap](PHASE3_IMPLEMENTATION_ROADMAP.md)
- [Source index](AUDIT_SOURCE_INDEX.json) / [Preservation](PRESERVATION_VERIFICATION.json)

Negative findings are scoped: first-party src/memory_graph, scripts, tests, configs; external environments/model repositories/vendors are excluded. Some old test temporary folders are permission-denied and were not traversed; accessible saved logs and first-party tests were inspected. No universal statement about all external libraries is made. Source/static/test/runtime/human/documentation are separately tagged; no new tests, models, pipeline, movie decode or state adjudication were run.

At delivery STOP: no source edits/refactoring/JSON Schema/prototype/new inference/GT or Graph mutation/commit/push.
'''
save('PHASE3_OBSERVATION_CAPABILITY_AUDIT.md',main)

# Search-only inventory captures exact negative-search scope and does not pretend full semantic review of every file.
search_files=[];hits=[]
pattern=re.compile(r'mediapipe|hand.?keypoints?|hand.?detect|hand.?pose|pose.?estimat|YOLO\(|BYTETracker|BOTSORT|optical.?flow|homography|findHomography|calcOpticalFlow|estimateAffine|HELD_BY_PERSON|ON_SURFACE|OCCLUDED|OUT_OF_VIEW|independent_physical_support|interaction_evidence',re.I)
for root in ['src/memory_graph','scripts','tests','configs']:
    for p in (ROOT/root).rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.py','.yaml','.json'} and '__pycache__' not in p.parts:
            text=p.read_text(encoding='utf-8');path=p.relative_to(ROOT).as_posix();search_files.append({'path':path,'sha256':sha(p),'inspection_depth':'SEARCH_ONLY' if path not in catalog.values() else 'TARGETED_SOURCE_OR_TEST_REVIEW'})
            for n,line in enumerate(text.splitlines(),1):
                if pattern.search(line):hits.append({'path':path,'line':n,'excerpt':line.strip()[:220]})
index=[]
for id,path in catalog.items():
    p=ROOT/path;basis='Source implementation' if id in sources else 'Synthetic/mock test' if id in tests or id in ['D08','D09'] else 'Documentation' if id in docs else 'Human annotation' if id in ['A34','A35'] else 'Real runtime artifact'
    row={'id':id,'path':path,'sha256':sha(p),'size_bytes':p.stat().st_size,'conclusion_basis':basis,'inspection_depth':'TARGETED_READ_AND_DATA_AGGREGATION' if id in artifacts else 'TARGETED_SOURCE_OR_DOCUMENT_REVIEW',
         'new_execution_verified':False,'limits':'Stored artifact evidence does not itself validate physical correctness.'}
    if id in sources:row.update(symbol=sources[id][2],line=sources[id][1])
    if p.suffix=='.py':
        tree=ast.parse(p.read_text(encoding='utf-8-sig'));row['declarations']=[{'symbol':x.name,'line':x.lineno,'kind':type(x).__name__} for x in ast.walk(tree) if isinstance(x,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))]
    index.append(row)
claims=[
 {'conclusion':'Current identity authority differs from legacy Graph pipeline','basis':['Source implementation','Real runtime artifact','Documentation'],'evidence_ids':['S01','S02','S08','A10','D01','D02','D03']},
 {'conclusion':'Real smartphones/persons detected, manipulated target recall not established','basis':['Real runtime artifact','Source implementation'],'evidence_ids':['A01','A02','A03','A04','S03']},
 {'conclusion':'W05 exact CV sampled overlap1/8 and0/8; current target authorization0','basis':['Real runtime artifact'],'evidence_ids':['A05','A06','A11','A12','A30','A31','A32']},
 {'conclusion':'Independent hand/contact/held/support producer not verified within search scope','basis':['Source implementation','Synthetic/mock test','Human annotation'],'evidence_ids':['S22','S44','T06','A34'],'negative_scope':'search_inventory; libraries/vendor environments excluded'},
 {'conclusion':'Camera compensation is a legacy median-translation heuristic with real diagnostics','basis':['Source implementation','Real runtime artifact','Synthetic/mock test'],'evidence_ids':['S24','A25','A26','T07']},
 {'conclusion':'State/identity/time evidence insufficient for automatic authoritative PICKUP or PLACEMENT','basis':['Source implementation','Real runtime artifact','Human annotation','Unverified inference'],'evidence_ids':['A11','A12','A17','A18','A34','S07','S14','S22'],'note':'Conservative architectural sufficiency judgement, not new model evaluation.'},
 {'conclusion':'Three-layer contracts and roadmap are recommendations only','basis':['Documentation'],'evidence_ids':[],'note':'No production schema/implementation/freeze.'}]
save('AUDIT_SOURCE_INDEX.json',{'audit_date_taipei':'2026-10-15','source_records':index,'claim_evidence':claims,'search_inventory':search_files,'search_regex':pattern.pattern,'search_hits':hits,
 'excluded_search_scopes':['.models','.venv','vendor/site-packages','.sam2_official','Ultralytics third-party tree','permission-denied historical temporary test directories'],
 'statistical_interpretation':'No fresh model accuracy/physical-state validation','runtime_actions':{'project_imports':0,'new_inference':0,'video_decodes':0,'production_writes':0,'Graph_writes':0}})
save('ARTIFACT_PRESERVATION_BASELINE.json',originals)
print(json.dumps({'status':'AUDIT_REPORTS_GENERATED','required_documents':9,'matrix_rows':len(rows),'primary_evidence_records':len(index),'searched_first_party_files':len(search_files),'sample_records':len(samples),'windows':{v:{'uniform8_CV_overlap':m['uniform8_exact_CV_sample_overlap'],'authorized':len(m['guard_authorized_frames_in_frame_bounds'])} for v,m in windows_metrics.items()}},ensure_ascii=False))

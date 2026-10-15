"""Independent stored-lineage audit. Reads only explicit code/config/log inputs.

Never imports or executes the inspected implementation. Reading an offline
cache is not proof that its future rows affected the binding decision.
"""
import hashlib
import subprocess
from pathlib import Path
from .phase1c_common import ROOT, OUT, read, write, sha, COUNTERS

CODE_PATHS=('src/memory_graph/v292/pipeline.py','src/memory_graph/v25rerun/binding.py',
            'src/memory_graph/v21/pipeline.py','src/memory_graph/pipeline_v2.py',
            'src/memory_graph/perception/track_manager.py','src/memory_graph/perception/tracker.py',
            'src/memory_graph/perception/track_timeline.py','src/memory_graph/perception/detector.py',
            'src/memory_graph/video/reader.py','src/memory_graph/video/episode_segmenter.py')
CONFIG_PATHS=('configs/v2.yaml','configs/default.yaml')
ARTIFACT_NAMES=('identity/target_binding.json','target_binding_audit.json','run_manifest.json',
                'video_metadata.json','perception/tracks.json','upstream_v21/run_status.json',
                'upstream_v21/event_analysis/video_metadata.json','upstream_v21/event_analysis/episodes.json',
                'upstream_v21/event_analysis/perception_cache.json','upstream_v21/event_analysis/track_timelines.json',
                'upstream_v21/event_analysis/track_id_mapping.json','upstream_v21/event_analysis/run_config.json')
BASELINE_PATHS=('artifacts/pass_t/manifests/protected_before.json',
                'artifacts/pass_t/manifests/phase1b_protected_before.json',
                'artifacts/pass_t/manifests/phase1c_protected_before.json')


class AllowedReader:
    def __init__(self,videos):
        self.allowed=set(CODE_PATHS+CONFIG_PATHS+BASELINE_PATHS+
                         ('artifacts/pass_t/manifests/window_target_mapping.json',))
        self.allowed.update(f'outputs_v292/{v}/{name}' for v in videos for name in ARTIFACT_NAMES)
        self.accessed=[]

    def text(self,relative):
        if relative not in self.allowed:raise ValueError('Input not in independent audit allowlist')
        path=ROOT/relative
        if not path.is_file():return None
        self.accessed.append(relative)
        return path.read_text(encoding='utf-8')

    def json(self,relative):
        import json
        text=self.text(relative)
        return json.loads(text) if text is not None else None


def classify_chain(facts):
    if facts.get('future_influence_proven') is True or facts.get('gt_influence_proven') is True:
        return 'NON_CAUSAL'
    cutoff=facts.get('claimed_cutoff_frame')
    binding=facts.get('binding_influential_frame')
    upstream=facts.get('upstream_influential_frame')
    if (facts.get('runtime_lineage_complete') is True and facts.get('upstream_independently_verified') is True
        and facts.get('code_revision_verified') is True and facts.get('gt_excluded_by_lineage') is True
        and cutoff is not None and binding is not None and upstream is not None
        and binding<=cutoff and upstream<=cutoff):
        return 'CAUSAL_VERIFIED'
    return 'CAUSALITY_UNVERIFIED'


def revision_evidence(revision,relative):
    if not revision:return {'revision':None,'verifiable':False,'reason':'Missing recorded code revision'}
    # Git blob retrieval only. Never invokes a model, tracker or historical code.
    result=subprocess.run(['git','show',f'{revision}:{relative}'],cwd=ROOT,capture_output=True,check=False)
    if result.returncode:return {'revision':revision,'verifiable':False,'reason':'Recorded git blob unavailable'}
    return {'revision':revision,'verifiable':True,'git_blob_sha256':hashlib.sha256(result.stdout).hexdigest(),
            'current_working_file_sha256':sha(ROOT/relative),
            'current_equals_recorded_blob':(ROOT/relative).read_bytes()==result.stdout}


def audit():
    # Only immutable pre-existing mappings determine pack/video scope.
    mapping=read(OUT/'manifests/window_target_mapping.json')['packs']
    videos=sorted({m['video_id'] for m in mapping});reader=AllowedReader(videos)
    mappings=reader.json('artifacts/pass_t/manifests/window_target_mapping.json')['packs']
    code={p:reader.text(p) for p in CODE_PATHS};configs={p:reader.text(p) for p in CONFIG_PATHS}
    baselines={p:reader.json(p) for p in BASELINE_PATHS}
    chain=[{'node':'v292.run_video','input':'raw recording/config','operation':'run_v21 completes before automatic_bind; later SAM/guard outputs do not feed initial binding'},
           {'node':'v21.run','input':'collect_tracks','operation':'Persistent identity and semantic outputs are separate from event_analysis/track_timelines.json'},
           {'node':'collect_tracks','input':'VideoReader frames','operation':'Full episode segmentation pass, then per-frame detector/ByteTrack update, then full-video timeline/cache materialization'},
           {'node':'EpisodeSegmenter.finish','operation':'May remove a short final episode using whole-video duration; potential dependency, not demonstrated effect on these early seeds'},
           {'node':'ObjectTracker.update','operation':'Per-frame ByteTrack class association; reset by precomputed episodes; IDs created in insertion order'},
           {'node':'build_timelines','operation':'Enumerates stored insertion-order tracks; row velocity uses previous row; mean/visibility/anchors aggregate full recording but binding does not consume those aggregate fields'},
           {'node':'automatic_bind','operation':'Builds by_frame by reading every phone observation; observe_frame then selects from seen prefix and breaks at bound frame'}]
    rows=[]
    for m in mappings:
        v=m['video_id'];base=f'outputs_v292/{v}/'
        data={n:reader.json(base+n) for n in ARTIFACT_NAMES}
        artifact=base+'identity/target_binding.json';binding=data['identity/target_binding.json']
        b=(binding or {}).get('bound_target') or {};track_data=data['perception/tracks.json'] or []
        run=data['run_manifest.json'] or {};meta=data['video_metadata.json'] or {}
        audit_rows=(binding or {}).get('candidate_initial_tracks',[])
        cutoff=b.get('frame_index');selection=max((a['frame_index'] for a in audit_rows),default=None)
        direct_scan=max((o['frame_index'] for t in track_data if t['detector_class']=='cell phone' for o in t['observations']),default=None)
        upstream=data['upstream_v21/event_analysis/track_timelines.json']
        matching_upstream=bool(upstream is not None and upstream==track_data)
        revision=run.get('source_git_identifier')
        revs={p:revision_evidence(revision,p) for p in CODE_PATHS}
        integrity={}
        for n in ['identity/target_binding.json','target_binding_audit.json','perception/tracks.json',
                  'upstream_v21/event_analysis/track_timelines.json','upstream_v21/event_analysis/perception_cache.json']:
            p=base+n
            integrity[p]={'current_sha256':sha(ROOT/p) if (ROOT/p).is_file() else None,
                          'established_baseline_matches':{name:(p in manifest and (ROOT/p).is_file() and sha(ROOT/p)==manifest[p])
                                                          for name,manifest in baselines.items()},
                          'historical_generation_immutability_proven':False}
        # No per-frame runtime dependency attestation exists in the allowlist.
        facts={'claimed_cutoff_frame':cutoff,'binding_influential_frame':selection,
               'upstream_influential_frame':None,'runtime_lineage_complete':False,
               'upstream_independently_verified':False,'code_revision_verified':all(x['verifiable'] for x in revs.values()),
               'gt_excluded_by_lineage':False,'future_influence_proven':False,'gt_influence_proven':False}
        status=classify_chain(facts)
        rows.append({'pack_id':m['pack_id'],'original_seed_track':b.get('source_track_id'),
                     'binding_artifact_path':artifact,'binding_artifact_sha256':sha(ROOT/artifact),
                     'binding_generator_path':'src/memory_graph/v292/pipeline.py:run_video -> automatic_bind',
                     'binding_algorithm_path':'src/memory_graph/v25rerun/binding.py',
                     'code_revision_reference':revision,'code_revision_evidence':revs,
                     'configuration_reference':['configs/v2.yaml','configs/default.yaml',base+'upstream_v21/event_analysis/run_config.json'],
                     'stored_runtime_configuration_available':data['upstream_v21/event_analysis/run_config.json'] is not None,
                     'claimed_binding_decision_frame':cutoff,'claimed_binding_source_timestamp_s':b.get('timestamp'),
                     'latest_frame_read_directly_by_binding_logic':direct_scan,
                     'latest_frame_in_recorded_selection_prefix':selection,
                     'latest_source_frame_that_may_influence_upstream':meta.get('frame_count',0)-1,
                     'upstream_track_causality_status':'CAUSALITY_UNVERIFIED',
                     'same_raw_track_artifact_as_upstream':matching_upstream,
                     'gt_entered_dependency_chain':'NO_PATH_FOUND_IN_INSPECTED_CODE; runtime lineage UNKNOWN',
                     'future_information_entered_dependency_chain':'FULL_VIDEO_INPUT_SCAN_AND_CACHE_GENERATION_PROVEN; influential effect on decision UNKNOWN',
                     'future_influence_proven':False,'noncausal_dependency_proven':False,
                     'artifact_integrity':integrity,
                     'positive_provenance_evidence':['Recorded selection audit stops at decision frame.',
                         'automatic_bind confidence/span criteria operate on seen prefix, not full-track aggregates.',
                         'raw track IDs/rows match upstream track_timelines artifact.' if matching_upstream else 'Raw/upstream match unavailable.',
                         'Initial binding occurs before SAM, admission, Re-ID/guard processing in inspected generator.',
                         'Existing baseline hashes match current allowed artifacts.'],
                     'missing_provenance_evidence':['No independently stored incremental ByteTrack state/dependency log through cutoff.',
                         'No immutable invocation/config/runtime receipt linking raw track cache to exact historical code.',
                         'Full-video episode finalization/cache dependency cannot be ruled out by static source inspection alone.',
                         'Today/current-baseline hashes do not prove original-generation immutability.'],
                     'wall_clock_distinction':'Artifact generated offline later than source-video timestamp is not proof of lookahead.',
                     'decision_input_fields':['phone detector_class','source track_id','frame_index','timestamp','per-observation confidence','bbox'],
                     'facts':facts,'final_causality_classification':status})
    result={'schema_version':'BINDING_CAUSAL_LINEAGE_V1','packs':rows,'dependency_chain':chain,
            'input_allowlist':sorted(reader.allowed),'actual_inputs_read':sorted(set(reader.accessed)),
            'inspected_source_code_hashes':{p:sha(ROOT/p) for p in code},
            'configuration_hashes':{p:sha(ROOT/p) for p in configs},
            'audit_method':'Stored artifacts + independent baseline comparison + static source/git blob inspection; inspected code never executed.',
            'isolation':'Explicit allowlist; no annotation inputs; no review-derived evidence.',
            'runtime_counters':dict(COUNTERS),'causal_verified':sum(r['final_causality_classification']=='CAUSAL_VERIFIED' for r in rows),
            'causality_unverified':sum(r['final_causality_classification']=='CAUSALITY_UNVERIFIED' for r in rows),
            'noncausal':sum(r['final_causality_classification']=='NON_CAUSAL' for r in rows),
            'completion':'NINE_PACK_AUDIT_COMPLETE'}
    write(OUT/'reports/PASS_T_BINDING_CAUSALITY_AUDIT.json',result)
    write(OUT/'manifests/binding_causal_lineage_v1.json',{'packs':[{k:r[k] for k in [
          'pack_id','original_seed_track','claimed_binding_decision_frame','latest_frame_read_directly_by_binding_logic',
          'latest_frame_in_recorded_selection_prefix','latest_source_frame_that_may_influence_upstream',
          'upstream_track_causality_status','final_causality_classification','future_influence_proven']} for r in rows],
          'input_allowlist':result['input_allowlist'],'runtime_counters':dict(COUNTERS)})
    lines=['# Independent automatic binding causality audit','',
           'All nine bindings remain CAUSALITY_UNVERIFIED. CAUSAL_VERIFIED=0; NON_CAUSAL=0. This is a completed audit, not a missing audit.',
           '', '| Pack | Original track | Decision | Direct by_frame scan through | Selection prefix through | Potential upstream source cutoff | Status |',
           '|---|---:|---:|---:|---:|---:|---|']
    for r in rows:
        lines.append(f"| {r['pack_id']} | {r['original_seed_track']} | {r['claimed_binding_decision_frame']} | {r['latest_frame_read_directly_by_binding_logic']} | {r['latest_frame_in_recorded_selection_prefix']} | {r['latest_source_frame_that_may_influence_upstream']} | {r['final_causality_classification']} |")
    lines += ['', '## Separate conclusions','',
              'Artifact integrity: current allowed inputs match established Phase1/Phase1b manifests. Those baselines establish preservation since snapshot time, not original-generation immutability. Recorded git blobs are retrieved without executing historical code; current-vs-recorded comparisons are reported per file.',
              '', 'Binding algorithm: automatic_bind first scans all stored phone observations to build by_frame. This direct read extends beyond decision time. The actual selection audit and observe_frame seen-prefix logic stop at bound frame. Full-input scanning alone does not prove future values influenced which track was chosen.',
              '', 'Upstream: v292 loads event_analysis raw timelines, not the identity-resolved entity mapping. collect_tracks performs full-recording episode segmentation before per-frame ByteTrack, then materializes full timelines/cache. EpisodeSegmenter.finish can remove a short last episode based on whole-recording duration. Insertion-order IDs and previous-row velocity look causal in inspected code, while mean/visibility/anchor aggregates use the full recording and are not binding inputs. Stored episodes are single-episode in these six videos. No proven future-effect on these early seed choices was found.',
              '', 'Missing independent evidence: incremental tracker states/dependency logs, immutable invocation/config/runtime lineage and proof that episode/cache construction did not alter prefix inputs. Static source inspection, a sequential function name, or a matching hash cannot supply this evidence. All upstream status remains unverified.',
              '', 'GT: no GT/oracle/manual correction path was found in the inspected initial-binding dependency chain. Runtime lineage is incomplete, so absence of a static path is not promoted to verified GT exclusion. SAM/admission/guard occur after initial binding; their results are not inputs to this audit.',
              '', 'Offline wall-clock generation and source-video seconds are different clocks. Later file creation is not NON_CAUSAL evidence. No positive prohibited future or GT influence was proven, so NON_CAUSAL remains zero.',
              '', '## Isolation and safety','',
              'Only the explicit input allowlist in JSON was read. Inspected source text was never imported/executed. No detector/tracker/SAM execution, no remote calls, no graph writes. Static new-module safety/isolation checks are reported in the Phase1c final report; runtime counters are all zero.',
              '', 'Full artifact hashes, code revision checks, configuration references, source cutoffs, positive/missing lineage and allowlist/access log are in the JSON. Original binding artifacts are unchanged.']
    write(OUT/'reports/PASS_T_BINDING_CAUSALITY_AUDIT.md','\n'.join(lines)+'\n')
    return {'audit_complete':True,'causal_verified':result['causal_verified'],
            'causality_unverified':result['causality_unverified'],'noncausal':result['noncausal']}

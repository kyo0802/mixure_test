"""New-files-only Phase 1b checkpoints. No pipeline, inference or graph execution."""
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
from .overlap import relationships
from .resolver import cutoff_records, resolve_window, stage0_gate, PILOT_RESTRICTION

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'artifacts/pass_t'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write(relative, value):
    path = OUT / relative
    protected = read(OUT / 'manifests/phase1b_protected_before.json')
    if path.relative_to(ROOT).as_posix() in protected:
        raise RuntimeError('Refusing to overwrite pre-existing file: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False) + '\n'
    path.write_bytes(text.encode('utf-8'))


def test_counts(path):
    s = ET.parse(path).getroot()
    s = s.find('testsuite') if s.tag == 'testsuites' else s
    return {k: int(s.attrib[k]) for k in ['tests', 'failures', 'errors', 'skipped']}


def toolchain():
    import av
    import cv2
    codecs = {}
    for name in ['libx264', 'h264', 'mpeg4', 'ffv1']:
        codecs[name] = {}
        for mode in ['r', 'w']:
            try:
                c = av.codec.Codec(name, mode)
                codecs[name][mode] = {'available': True, 'implementation': c.name}
            except Exception as e:
                codecs[name][mode] = {'available': False, 'reason': str(e)}
    return {'PyAV': av.__version__, 'OpenCV': cv2.__version__,
            'ffmpeg_cli': shutil.which('ffmpeg'), 'ffprobe_cli': shutil.which('ffprobe'),
            'libav_versions': av.library_versions, 'codecs': codecs,
            'available_codec_names': sorted(av.codecs_available),
            'PTS_probe': 'PyAV/libavformat native frame PTS; independent ffprobe CLI unavailable',
            'warnings': ['ffmpeg/ffprobe CLI absent; existing PyAV handles encode/decode/PTS.',
                         'Baseline test process reported a sandbox temp-cleanup PermissionError after 114 passing tests; exit code 0.']}


def source_packs():
    base = ROOT / 'outputs/current_development'
    events = {e['pack_id']: e for e in read(base/'event_windows/event_manifest.json')}
    return [events[r['pack_id']] for r in read(base/'qwen/requests.json')]


def window(e, info):
    # Builder adaptive_window uses rows[lo:hi+1]; old native source_frame_indices
    # explicitly adds one to end_frame. Frozen Pass T keeps time end exclusive.
    return {'pack_id': e['pack_id'], 'video_id': e['video_id'], 'target_scope': e['target_id'],
            'window_start_s': e['start_time'], 'window_end_s': e['end_time'],
            'source_video_hash': info['sha256'], 'source_video_path': e['video_id']+'.mp4',
            'source_fps': info['fps'], 'authorized_half_open_frames': [e['start_frame'], e['end_frame']],
            'original_inclusive_frames': [e['start_frame'], e['end_frame']],
            'inclusive_half_open_equivalent': [e['start_frame'], e['end_frame']+1],
            'frame_bound_semantics': 'ORIGINAL_INCLUSIVE; PASS_T_CONSERVATIVE_HALF_OPEN',
            'frame_bound_evidence': {'start_s_times_fps': e['start_time']*info['fps'],
                                     'end_s_times_fps': e['end_time']*info['fps'],
                                     'builder': 'src/memory_graph/events/window_builder.py:adaptive_window rows[lo:hi+1]',
                                     'old_native': 'src/memory_graph/reasoning/video_experiment.py:source_frame_indices end_frame+1',
                                     'policy': 'Keep existing [start_time,end_time); do not extend to inclusive endpoint.'},
            'task_context': {k: e[k] for k in ['category','trigger','transition_frame','contexts']},
            'clean_source_hash_verified': (ROOT/(e['video_id']+'.mp4')).is_file() and
                                          sha(ROOT/(e['video_id']+'.mp4')) == info['sha256']}


def binding_audit(video):
    base = ROOT/'outputs_v292'/video
    path = base/'identity/target_binding.json'
    data = read(path)
    b = data.get('bound_target') or {}
    run = read(base/'run_manifest.json')
    audits = data.get('candidate_initial_tracks', [])
    # Online code and audit cutoff are consistent, but a recorded source git ID
    # is not an immutable per-artifact generation attestation. Never upgrade on
    # policy.no_future_frames_or_gt alone.
    proof = {'binding_source': path.relative_to(ROOT).as_posix(),
             'binding_sha256': sha(path), 'recorded_generator_git': run.get('source_git_identifier'),
             'generator_reference': 'src/memory_graph/v292/pipeline.py:run_video automatic_bind before guard',
             'algorithm_reference': 'src/memory_graph/v25rerun/binding.py:automatic_bind/observe_frame (prefix, early break)',
             'max_recorded_selection_frame': max((x['frame_index'] for x in audits), default=None),
             'bound_frame': b.get('frame_index'), 'bound_source_kind': b.get('source_kind'),
             'recorded_policy': data.get('policy'),
             'limitation': 'Generator/audit indicate causal prefix selection, but immutable runtime binding origin and upstream local-track causality are not independently attested.'}
    return {**b, 'binding_created_by': 'unknown',
            'binding_causal_cutoff': {'frame': b.get('frame_index'), 'timestamp_s': b.get('timestamp'),
                                      'meaning': 'recorded selection cutoff; not an origin attestation'},
            'binding_derived_from_gt': 'UNKNOWN', 'binding_derived_from_full_video': 'UNKNOWN',
            'binding_audit_evidence': proof, 'binding_causality_status': 'CAUSALITY_UNVERIFIED'}


def operational_inventory(video, end):
    """Read sources, project an allowlist, apply cutoff before resolver receives data."""
    base = ROOT/'outputs_v292'/video
    paths = [f'outputs_v292/{video}/candidate_stream.json', f'outputs_v292/{video}/perception/tracks.json',
             f'outputs_v292/{video}/video_metadata.json']
    try:
        stream = read(ROOT/paths[0])['observations']
        tracks = read(ROOT/paths[1])
        metadata = read(ROOT/paths[2])
        # Frame-observation association is an exact source track/index match.
        raw = {(str(t['track_id']), o['frame_index']): o for t in tracks if t['detector_class']=='cell phone'
               for o in t['observations'] if o['timestamp'] < end}
        rows = []
        for x in stream:
            if x['timestamp'] >= end:
                continue
            obs = raw.get((str(x.get('source_track_id')), x['frame_index']))
            rows.append({k: x.get(k) for k in ['frame_index','timestamp','source_track_id','candidate_id','semantic_class']})
            rows[-1].update(observation_id=f"raw:{x['raw_detection_index']}@{x['frame_index']}",
                            bbox=obs.get('bbox') if obs else None, source_path=paths[0])
        # Inventory coverage validates recorded full perception run, not phone visibility.
        status = read(base/'run_manifest.json')
        valid = (status.get('status')=='COMPLETE' and metadata.get('decoded_frame_count')==metadata.get('frame_count')
                 and len(metadata.get('sampled_frames', []))>0
                 and all(0<=x['frame_index']<metadata['frame_count'] for x in stream))
        return {'records': cutoff_records(rows, end), 'source_paths': paths,
                'coverage_validated': valid, 'coverage_kind': 'recorded sampled detector inventory, not continuous visibility'}
    except (OSError, KeyError, TypeError) as exc:
        return {'records': [], 'source_paths': paths, 'coverage_validated': False, 'missing_reason': str(exc)}


def stage_m1():
    preflight = read(OUT/'manifests/phase1b_preflight.json')
    preflight['baseline_tests'] = test_counts(OUT/'smoke/phase1b_baseline.xml')
    assert preflight['baseline_tests'] == {'tests':114, 'failures':0, 'errors':0, 'skipped':0}
    preflight['toolchain'] = toolchain()
    write('manifests/phase1b_preflight.json', preflight)
    inputs = {i['video_id']: i for i in read(ROOT/'outputs/current_development/event_windows/development_inputs.json')}
    packs = []
    for e in source_packs():
        v = e['video_id']; w = window(e, inputs[v]); b = binding_audit(v)
        inv = operational_inventory(v, w['window_end_s'])
        local = [x for x in inv['records'] if w['window_start_s']<=x['timestamp']<w['window_end_s']]
        seed_rows = [x for x in local if x['source_track_id']==b.get('source_track_id')]
        before = [x for x in inv['records'] if x['source_track_id']==b.get('source_track_id') and x['timestamp']<w['window_start_s']]
        timeline = read(ROOT/f'outputs/current_development/event_windows/target_timelines/{v}.json')['rows']
        timeline = [x for x in timeline if w['window_start_s']<=x['time']<w['window_end_s']]
        epoch_refs = []
        # Read only source observations / inventory linkage, never hidden provenance or annotations.
        inventory_path = ROOT/'artifacts/pass_i/manifests/candidate_epoch_inventory.jsonl'
        for line in inventory_path.read_text(encoding='utf-8').splitlines():
            epoch = json.loads(line)
            if epoch['video_id'] != v:
                continue
            observed = [o for o in epoch['source_observations'] if w['window_start_s']<=o['time']<w['window_end_s']]
            if observed:
                epoch_refs.append({'candidate_epoch_id': epoch['epoch_id'],
                                   'local_track_ids': sorted({o['local_track_id'] for o in observed}),
                                   'in_window_frame_range': [min(o['frame'] for o in observed),max(o['frame'] for o in observed)]})
        candidate_summary = []
        keys = sorted({(str(x.get('source_track_id')), str(x.get('candidate_id'))) for x in local})
        for track, candidate in keys:
            xs = [x for x in local if (str(x.get('source_track_id')),str(x.get('candidate_id')))==(track,candidate)]
            candidate_summary.append({'local_track_id': None if track=='None' else track,
                                      'candidate_id': None if candidate=='None' else candidate,
                                      'first_frame':min(x['frame_index'] for x in xs), 'last_frame':max(x['frame_index'] for x in xs),
                                      'observations':len(xs), 'explicit_original_track_link':track==str(b.get('source_track_id')),
                                      'coexists_with_competing_phone_candidate':any(y['frame_index']==x['frame_index'] and
                                          y.get('source_track_id')!=x.get('source_track_id') for x in xs for y in local)})
        # Future metadata exists only here, never in mapping or media files.
        all_seed = [x for x in read(ROOT/f'outputs_v292/{v}/candidate_stream.json')['observations']
                    if x.get('source_track_id')==b.get('source_track_id')]
        after = [x for x in all_seed if x['timestamp']>=w['window_end_s']]
        after_row = min(after,key=lambda x:x['timestamp']) if after else None
        last_before = max(before,key=lambda x:x['timestamp']) if before else None
        packs.append({**w, 'binding_provenance': b, 'bound_track_in_window_count':len(seed_rows),
                      'last_before_window': {k:last_before[k] for k in ['frame_index','timestamp']} if last_before else None,
                      'distance_from_before_to_start': {'frames':w['authorized_half_open_frames'][0]-last_before['frame_index'],
                                                       'seconds':w['window_start_s']-last_before['timestamp']} if last_before else None,
                      'in_window_candidates':candidate_summary, 'in_window_candidate_epochs':epoch_refs,
                      'inventory_validated':inv['coverage_validated'], 'missing_sources':inv.get('missing_reason'),
                      'target_timeline': {'rows':len(timeline),'visible_bbox_rows':sum(bool(x.get('target_bbox')) for x in timeline),
                                          'explicit_local_target_reference': False,
                                          'states':dict(Counter(x.get('visibility','UNKNOWN') for x in timeline)),
                                          'candidate_present_rows':sum(bool(x.get('candidate_present')) for x in timeline),
                                          'last_in_window_state':{k:timeline[-1].get(k) for k in
                                              ['frame','time','visibility','upstream_identity_state','candidate_present']} if timeline else None,
                                          'contradiction_status':'LOCAL_BINDING_UNVERIFIABLE_FROM_GLOBAL_CHAIN; no proven identity contradiction',
                                          'finding':'Global/guard chain and SAM boxes are not detector local-track bindings.'},
                      'missing_data_distinction':{'original_track_observed':bool(seed_rows),'candidate_records_observed':bool(local),
                                                 'source_inventory_validated':inv['coverage_validated'],
                                                 'track_id_switch_established':False,'target_absence_established':False,
                                                 'wrong_window_source_established':False},
                      'root_cause':'UNKNOWN','root_cause_confidence':'UNKNOWN',
                      'root_cause_evidence':['Recorded local-track support is available.' if seed_rows else
                                             'No original local-track support inside window; insufficient evidence for ID switch, absence or source mismatch.'],
                      'diagnostic_only': {'total_seed_observations':len(all_seed),
                                          'first_observed_frame':min((x['frame_index'] for x in all_seed),default=None),
                                          'last_observed_frame':max((x['frame_index'] for x in all_seed),default=None),
                                          'nearest_at_or_after_end':{k:after_row[k] for k in ['frame_index','timestamp']} if after_row else None,
                                          'distance_after_end':{'frames':after_row['frame_index']-w['authorized_half_open_frames'][1],
                                                                'seconds':after_row['timestamp']-w['window_end_s']} if after_row else None,
                                          'used_for_binding':False}})
    overlap = relationships(packs)
    write('manifests/window_overlap_groups.json', overlap)
    diagnosis = {'packs':packs, 'builder_changes':0, 'source_pixels_decoded':0,
                 'builder_findings':[{'finding':'test1 W03/W05 collapse distinct trigger transitions 186/222 to the same range.',
                                      'classification':'CORRELATED_MEDIA; POSSIBLE_BUILDER_DESIGN_LIMITATION',
                                      'recommendation':'Separate Builder task should inspect duplicate trigger/window policy; no repair here.'}],
                 'overlap_manifest':'artifacts/pass_t/manifests/window_overlap_groups.json'}
    write('reports/PASS_T_BLOCKER_DIAGNOSIS.json', diagnosis)
    lines = ['# Pass T Phase 1b source diagnosis', '', 'Metadata only. No source pixels decoded in M1. No identity/GT labels used.', '',
             '| Pack | Seed track | In-window seed observations | Other candidates | Binding causality | Root cause |',
             '|---|---:|---:|---:|---|---|']
    for p in packs:
        lines.append(f"| {p['pack_id']} | {p['binding_provenance'].get('source_track_id')} | {p['bound_track_in_window_count']} | {len(p['in_window_candidates'])} | {p['binding_provenance']['binding_causality_status']} | UNKNOWN |")
    lines += ['', 'Detailed before-boundary diagnostics, candidate ranges, CandidateEpoch references and binding generator evidence are in the JSON. Post-window details appear ONLY in its `diagnostic_only` blocks.',
              '', 'Original Builder frame endpoints are inclusive (rows[lo:hi+1], old native range includes end_frame). Pass T preserves original time end as exclusive and conservatively uses [start_frame,end_frame).',
              '', 'test1 W03/W05: identical media, distinct triggers/context; preserve both as correlated, not proven equivalent evaluation tasks.',
              'test8 operational overlap [857,962) / [936,1054): 26 intersection, 197 union, IoU 26/197, overlap/shorter 26/105. Original inclusive intervals and their half-open equivalents [857,963)/[936,1055): 27 intersection, 198 union. Operational decoding uses the smaller Pass T interval.',
              '', 'Builder finding: distinct test1 transitions collapse to the same range. Inspect in a separate task; BUILDER_CHANGES=0.',
              '', 'Zero bound-track observations do not establish occlusion, ID switch or source mismatch. Root causes remain UNKNOWN.',
              '', 'Causal origin: recorded automatic binding code selects from a prefix and stops at binding, but immutable execution/source-track causality is not attested. All bindings remain CAUSALITY_UNVERIFIED; allowed only for input-integrity pilot.']
    write('reports/PASS_T_BLOCKER_DIAGNOSIS.md', '\n'.join(lines)+'\n')
    write('manifests/phase1b_milestone_M1.json', {'status':'COMPLETE', 'original_packs':len(packs),
                                              'baseline_tests':preflight['baseline_tests']})
    return overlap


def human_schema():
    properties = {'pack_id':{'type':'string','minLength':1},'selected_local_track_id':{'type':['string','null']},
                  'answer_type':{'enum':['SELECTED_CANDIDATE','UNRESOLVED','NO_VISIBLE_TARGET','MULTIPLE_PLAUSIBLE_TARGETS']},
                  'annotator_id':{'type':'string','minLength':1},'timestamp':{'type':'string','format':'date-time'},
                  'frames_reviewed':{'type':'array','minItems':1,'uniqueItems':True,'items':{'type':'integer','minimum':0}},
                  'notes':{'type':'string'},'confidence':{'enum':['LOW','MEDIUM','HIGH']},
                  'provenance':{'const':'HUMAN_SEEDED'}, 'global_identity_authority':{'const':False}}
    return {'$schema':'https://json-schema.org/draft/2020-12/schema', 'type':'object',
            'properties':properties,'required':list(properties),'additionalProperties':False,
            'allOf':[{'if':{'properties':{'answer_type':{'const':'SELECTED_CANDIDATE'}}},
                      'then':{'properties':{'selected_local_track_id':{'type':'string','minLength':1}}},
                      'else':{'properties':{'selected_local_track_id':{'type':'null'}}}}]}


def stage_m2(pilot_partial=False):
    inputs = {i['video_id']:i for i in read(ROOT/'outputs/current_development/event_windows/development_inputs.json')}
    overlap = read(OUT/'manifests/window_overlap_groups.json')
    mappings = []
    for e in source_packs():
        w = window(e, inputs[e['video_id']]); w.pop('task_context'); w.pop('target_scope')
        w.update(overlap['packs'][e['pack_id']])
        b = binding_audit(e['video_id'])
        mapping = resolve_window(w, b, operational_inventory(e['video_id'], w['window_end_s']))
        mapping.update(PILOT_RESTRICTION)
        mappings.append(mapping)
    gate = stage0_gate(mappings, pilot_partial)
    write('manifests/window_target_mapping.json', {**PILOT_RESTRICTION,'packs':mappings,'gate':gate})
    requests = []
    for m in mappings:
        if m['resolution_status']=='RESOLVED_UNIQUE':
            continue
        frames = sorted({i for c in m['available_candidates'] for i in c['frames']})
        requests.append({'pack_id':m['pack_id'],'video_id':m['video_id'],
                         'authorized_window_s':[m['window_start_s'],m['window_end_s']],
                         'authorized_half_open_frames':m['authorized_half_open_frames'],
                         'available_local_candidates':m['available_candidates'],
                         'suggested_in_window_frames': frames[:3] if frames else [m['authorized_half_open_frames'][0]],
                         'review_question':'Which visible local candidate, if any, is directly supported as the target of this Event Window? Do not infer global physical identity from generic phone similarity.',
                         'allowed_answers':['UNRESOLVED','NO_VISIBLE_TARGET','MULTIPLE_PLAUSIBLE_TARGETS','SELECTED_CANDIDATE'],
                         'why_automatic_failed':m['reason_codes'],'source_provenance':m['evidence_source_paths'],
                         'clean_review_image_can_be_generated_safely':m['clean_source_hash_verified'],
                         'review_images_generated':False,'human_response_loaded_or_applied':False})
    write('manifests/human_seed_request.json', {'status':'REQUESTS_ONLY; NO_RESPONSES_APPLIED','requests':requests})
    write('contracts/PASS_T_HUMAN_SEED_RESPONSE_SCHEMA_V1.json', human_schema())
    write('contracts/PASS_T_STAGE0_GATE_DECISION.md', '# Stage 0 policy — Phase 1b\n\n'
          'Original script/source unchanged. Default new-script behavior preserves global strict gating: nine packs required and fewer than five blockers. The present seven unresolved packs block global processing. Aggregate target readiness is false whenever any mapping is missing.\n\n'
          '`--pilot-partial` explicitly allows safely resolved packs independently. All private wrappers carry evaluation_eligible=false, purpose=INPUT_INTEGRITY_SMOKE_ONLY, status=NOT_FOR_EVALUATION. Frozen v1 bundles cannot gain extra fields; restrictions and binding causality are in separate private pilot manifests. They are not model evidence.\n\n'
          'CAUSALITY_UNVERIFIED is allowed for integrity smoke only; NON_CAUSAL bindings cannot resolve. No pilot can be promoted by this command. Unresolved target processing remains blocked.\n\n'
          'Future evaluation proposal (not activated): at least 30 independent nonoverlapping windows from at least 5 distinct recording sessions/videos, grouped by actual recording session rather than assumed file independence; at least 5 observable examples of each evaluated event and 10 observable negative windows, causally verified local target support, independently adjudicated events/observability, and safe DEV/Frozen separation. These minima need a separate approved protocol; no claim of readiness here.\n\n'
          'Open decision: whether HUMAN_SEEDED windows should ever count toward evaluation eligibility. Schema only; no responses loaded, simulated or applied. Human seeds provide local selection, never global identity authority.\n')
    write('manifests/phase1b_milestone_M2.json', {'status':'COMPLETE','gate':gate,
                                              'resolution_counts':dict(Counter(m['resolution_status'] for m in mappings))})
    return gate


def stage_m4():
    """Final verification after tests; all artifact updates are new in this task."""
    counts = test_counts(OUT/'smoke/phase1b_all_tests.xml')
    if counts['failures'] or counts['errors'] or counts['skipped']:
        raise RuntimeError('Final tests failed or skipped; report cannot pass')
    baseline = read(OUT/'manifests/phase1b_preflight.json')
    protected = read(OUT/'manifests/phase1b_protected_before.json')
    changed = [p for p,h in protected.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    tracked = subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=no'],cwd=ROOT,text=True).splitlines()
    old_tracked = [line for line in baseline['git_status_lines'] if not line.startswith('??')]
    diff_names = subprocess.check_output(['git','diff','--name-status'],cwd=ROOT,text=True).splitlines()
    preservation = {'status':'PASS' if not changed and head==baseline['HEAD'] and tracked==old_tracked else 'FAIL',
                    'protected_files_verified':len(protected),'original_manifest_files':baseline['old_protected_count'],
                    'changed_files':changed,'HEAD_unchanged':head==baseline['HEAD'],
                    'tracked_status_unchanged':tracked==old_tracked,
                    'git_diff_reviewed_entry_count':len(diff_names),
                    'pass_i_prompt_sha256':sha(ROOT/'artifacts/pass_i/prompts/pass_i_prelabel_prompt.txt'),
                    'scope':'V297, Pass I, v1 contracts/source, existing Phase1 files, raw videos, outputs_v292, EWB/source packs',
                    'commit_created':False,'pushed':False,'mixed_original_directory_written':False}
    write('manifests/phase1b_preservation_check.json', preservation)
    mappings = read(OUT/'manifests/window_target_mapping.json')['packs']
    overlap = read(OUT/'manifests/window_overlap_groups.json')
    smoke = read(OUT/'smoke/phase1b_real_media.json')
    media = {p['pack_id']:p for p in smoke['packs']}
    packs=[]
    for m in mappings:
        p=media[m['pack_id']]
        resolved=m['resolution_status']=='RESOLVED_UNIQUE'
        packs.append({'pack_id':m['pack_id'],'video_id':m['video_id'],
                      'window_start':m['window_start_s'],'window_end':m['window_end_s'],
                      'original_seed_track':binding_audit(m['video_id']).get('source_track_id'),
                      'in_window_seed_observations':len(m['supporting_observation_ids']),
                      'root_cause':'UNKNOWN','root_cause_confidence':'UNKNOWN',
                      'binding_causality_status':m['binding_causality_status'],
                      'resolution_status':m['resolution_status'],'resolved_local_target':m['resolved_local_track_id'],
                      'resolution_method':m['method'],'duplicate_of':m['duplicate_of'],
                      'media_duplicate_of':m['media_duplicate_of'],'overlap_group_id':m['overlap_group_id'],
                      'strict_stage0_status':'BLOCKED_GLOBAL_GATE','pilot_stage0_status':'ALLOWED' if resolved else 'BLOCKED',
                      'A_media_status':p['A']['adapter_status'],'B_media_status':p['B']['adapter_status'],
                      'C_media_status':p['C']['adapter_status'],'overlay_coverage':p.get('overlay_coverage'),
                      'real_integrity_status':p.get('integrity_status','NOT_RUN_UNRESOLVED'),
                      'leakage_status':p.get('leakage',{}).get('status','NOT_RUN'),
                      'final_reason':p.get('errors') or p.get('error') or m['reason_codes'],
                      'artifact_directory':p.get('artifact_directory'),**PILOT_RESTRICTION})
    passed=[p for p in smoke['packs'] if p['real_smoke_status']=='PASS']
    eligible=smoke['gate']['eligible_packs']
    def unique_media(ids):
        return len({overlap['packs'][id_]['media_duplicate_of'] or id_ for id_ in ids})
    if preservation['status']!='PASS':status='PASS_T_PHASE1B_BLOCKED'
    elif passed:status='PASS_T_PHASE1B_PILOT_SMOKE_PASS'
    elif not eligible:status='PASS_T_PHASE1B_NEEDS_HUMAN_SEED'
    else:status='PASS_T_PHASE1B_PARTIAL_WITH_BLOCKERS'
    files=sorted([p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file() and
                  p.relative_to(ROOT).as_posix() not in protected and
                  not any(part.startswith('phase1b_') and part.endswith('_tmp') for part in p.parts)])
    files += ['src/memory_graph/pass_t/phase1b.py','src/memory_graph/pass_t/resolver.py',
              'src/memory_graph/pass_t/overlap.py','src/memory_graph/pass_t/media.py',
              'scripts/run_pass_t_phase1b.py','tests/test_pass_t_phase1b.py']
    report={**PILOT_RESTRICTION,'primary_status':status,'baseline':'V297_FROZEN',
            'pass_i':'PASS_I_CLOSED_ACQUISITION_LIMITED','pass_t_schema_version':'v1',
            'original_event_packs':len(packs),'unique_media_windows':overlap['unique_media_windows'],
            'unique_evaluation_items':overlap['unique_evaluation_items'],
            'nonoverlapping_evidence_groups':overlap['nonoverlapping_evidence_groups'],
            'distinct_source_video_files':len({m['video_id'] for m in mappings}),
            'recording_session_independence':'UNKNOWN; file IDs are grouping keys, not verified independent recording sessions',
            'local_target_resolved':sum(m['resolution_status']=='RESOLVED_UNIQUE' for m in mappings),
            'local_target_unresolved':sum(m['resolution_status']!='RESOLVED_UNIQUE' for m in mappings),
            'resolution_counts':dict(Counter(m['resolution_status'] for m in mappings)),
            'binding_causality':dict(Counter(m['binding_causality_status'] for m in mappings)),
            'pilot_eligible_packs':len(eligible),'pilot_unique_windows':unique_media(eligible),
            'real_integrity_pass':len(passed),'unique_real_integrity_pass_windows':unique_media([p['pack_id'] for p in passed]),
            'independent_usable_window_upper_bound':unique_media([p['pack_id'] for p in passed]),
            'human_seed_requests':len(packs)-len(eligible),'builder_defect_findings':1,
            'packs':packs,'A_backend_capability':'NOT_TESTED','model_inference_calls':0,
            'graph_write_attempts':0,'builder_changes':0,'formal_evaluation_ready':False,
            'tests':{'PassT_original':79,'PassT_phase1b':counts['tests']-114,'regression':35,'total':counts},
            'preservation':preservation,'toolchain':baseline['toolchain'], 'milestones':['M1','M2','M3','M4'],
            'next_action':'NEEDS_HUMAN_SEED',
            'next_smallest_task':'Review only seven unresolved local mappings using in-window source provenance; select a local candidate or an explicit unresolved/no-visible/multiple answer. Do not apply responses or begin evaluation without a separate decision.',
            'secondary_issues':['Verify immutable binding generation and upstream track causality before evaluation.',
                                'Only one unique media window is usable; broader independent DEV evidence is still needed.',
                                'Resolve HUMAN_SEEDED evaluation eligibility separately.',
                                'Investigate Builder duplicate-range behavior in a separate task.'],
            'source_files_added':files,
            'internal_repair_notes':['First test run: 172 passed/1 failed because new source audit used Windows cp950 default; fixed only new test to explicit UTF-8.',
                                    'Initial smoke retained separately; final r2 FFV1 packets bound final duration to the original window, avoiding nominal-FPS trailing hold beyond its end. No synthetic frames.'],
            'optional_scene_smoke':'NOT_RUN; minimal scope'}
    lines=['# Pass T Phase 1b Revision 2 — 完成報告','',f"**{status}**",'',
           'NOT_FOR_EVALUATION · evaluation_eligible=false · INPUT_INTEGRITY_SMOKE_ONLY','',
           '## 成果與分母','',
           f"9 個原始 pack；8 個不同媒體視窗；9 個不同評測任務紀錄（未證明 task 等價者不去重）；7 個不重疊證據群組；6 支來源影片。錄影 session 的獨立性尚未驗證，不能直接把 6 支影片當成 6 次獨立錄影。",
           '', '2/9 pack 可解析同一原始 local track 17，7/9 未解析。2/9 可進 pilot，2/2 真實媒體 smoke 通過，但只有 **1 個不同且可用的媒體視窗**。0/9 binding 為 CAUSAL_VERIFIED；9/9 為 CAUSALITY_UNVERIFIED；0/9 NON_CAUSAL。',
           '', '## 九個 pack（詳細欄位見同名 JSON）','',
           '| Pack | 視窗秒數 [start,end) | Seed / 觀測數 | Local resolution | A/B/C | Overlay | Integrity / leakage |',
           '|---|---|---|---|---|---|---|']
    for p in packs:
        cov=p['overlay_coverage'];cover=f"{cov['marked_count']}/{cov['sampled_count']} ({cov['ratio']:.2%})" if cov else '未執行'
        lines.append(f"| {p['pack_id']} | [{p['window_start']:.6f},{p['window_end']:.6f}) | {p['original_seed_track']} / {p['in_window_seed_observations']} | {p['resolution_status']} / {p['resolved_local_target'] or '—'} | {p['A_media_status']}/{p['B_media_status']}/{p['C_media_status']} | {cover} | {p['real_integrity_status']} / {p['leakage_status']} |")
    lines += ['', '所有 pack 的 strict Stage 0 都因全體有 7 個 blocker 而 BLOCKED；顯式 --pilot-partial 只允許兩個 test1 pack。所有 root cause / confidence 仍為 UNKNOWN，所有 binding 都 CAUSALITY_UNVERIFIED。',
              '', '## Local target 與因果來源','',
              '兩個 test1 pack 各有 17 筆原始綁定 track 17 的視窗內觀測，未捏造 CandidateEpoch ID。其他視窗出現的 track 並未有可靠 provenance 連回 seed：test2 track43、test3 track54、test5 W01 track31、test5 W05 track44 皆 NEEDS_HUMAN_SEED；test7 有 track32/34，test8 W06 有 track64/72/73/74/76、W07 有 track64/72/74/76，皆 AMBIGUOUS。單一候選、幾何相似及 global phone_01/SAM/guard chain 不作身分連結。',
              '', '缺少 seed 觀測不能證明 ID switch、遮蔽或來源錯置，因此沒有把 UNKNOWN 包装成根因。metadata 診斷中的 post-window 資料只留在 PASS_T_BLOCKER_DIAGNOSIS.json 的 diagnostic_only 區塊；resolver 只收到截止 window end 的 allowlist；media 只從 mapping 取得 target 資訊。',
              '', 'Binding generator 位於 v292 pipeline 的 automatic_bind，程式依序觀測且在綁定後停止；serialized selection audit 也停在 bound frame。但原始 artifact 的不可變 runtime 來源和 upstream track 因果性缺乏獨立證明，因此未升級成 CAUSAL_VERIFIED。完整 fields/檔案 hash/git reference 見 diagnosis JSON。',
              '', '## 真實 A/B/C 與時間','',
              '從原始 test1.mp4 依序解碼；codec preroll 不轉成輸入影像。原始 Builder endpoint 包含 end_frame，Pass T 保持既有 [start_time,end_time) 並保守排除 end_frame。3 FPS 網格、最近合法 frame／較早 tie、上限 16 張均沿用 frozen v1。',
              '', 'A 為 FFV1 lossless MKV：重新 decode 驗證 count、逐張 RGB signature/order、source mapping、PTS，沒有插值或補張；B 為 1280×720 chronological PNG；C 為 4 欄 row-major、每張有效 320×180，frame ID／timestamp header 獨立於縮圖。縮圖會降低可見細節，不能推論模型準確度。',
              '', '11 張來源 index：[157,166,176,186,196,206,216,226,236,246,256]。只有 216/246 有 exact observation，coverage=2/11=18.18%。其餘 [157,166,176,186,196,206,226,236,256] 無框。未改變 sampling grid，未 snapping、插值或搬用相鄰觀測。',
              '', '原始 native PTS 與 DERIVED_FPS 最大差約 0.846 ms；frame156 native time 在 start_time 前，因此使用 frame157。A encoded PTS 最大差約 0.420 ms，符合 1 ms 門檻。實際值與逐 frame 比較存於 private/pilot_integrity.json。ffprobe CLI 不存在，使用已有 PyAV/libavformat 讀取原始 PTS；沒有宣稱獨立 ffprobe cross-check。',
              '', '可見資產重新開啟檢查 PNG info/EXIF、MKV container/stream tags、檔名、bundle schema、hash、chronology、authorized bounds；只有 libavformat 必要 ENCODER/DURATION technical tags，其 key/value 有 allowlist。overlay 僅固定 cyan rectangle；storyboard 僅 frame ID／秒數。原始影片場景本身的文字不是 annotation metadata。兩份 bundle 的 REAL_LEAKAGE_PASS 為真實資產檢查結果。可見資產與 private source mapping/限制 sidecar 分離，未更動 frozen v1 schema。',
              '', 'A_MEDIA_ADAPTER=READY (2 pack)；B=READY (2)；C=READY (2)。其餘各 7 pack BLOCKED。A_BACKEND_CAPABILITY=NOT_TESTED。未呼叫模型，未聲稱 backend native-video 支援。',
              '', '## 重複與 Builder finding','',
              'test1 W03/W05 範圍相同，但 transition frame186/222 和 trigger 不同，保留原 pack ID；W05 media_duplicate_of=W03，duplicate_of=null。這是一項可能的 Builder 設計限制 finding，待另一任務檢查，未修復 Builder。',
              '', 'test8 保守操作區間 [857,962)/[936,1054)：intersection26、union197、IoU=0.13198、overlap/shorter=0.24762、時間重疊0.866745秒。原始 inclusive 的 half-open equivalents [857,963)/[936,1055)：intersection27、union198。來源 inclusive 與 Pass T operation 都有明確標示；同 source/session overlap group 不可跨 DEV/Frozen 分割，本次沒有建立 split。',
              '', '## 人工輸入與最小下一步','',
              '**NEXT_ACTION=NEEDS_HUMAN_SEED**。只 review 七個未解析 window 的合法視窗內來源，回答：哪個 local candidate 有直接 provenance 支持為此視窗 target？可選 selected candidate，或 UNRESOLVED／NO_VISIBLE_TARGET／MULTIPLE_PLAUSIBLE_TARGETS；不要依 generic 外觀猜 phone_01。request 檔列出範圍、候選觀測 frame、建議檢查 frame、來源及失败原因。',
              '', 'Human response schema 已定義 annotator/time/frames/notes/confidence/HUMAN_SEEDED provenance；未載入、套用或模擬任何實際 response，未啟動人工 annotation。HUMAN_SEEDED 是否可計入 formal evaluation 是未決事項。Secondary blockers：binding 因果來源驗證、獨立視窗不足、Builder 重複範圍另案檢查。',
              '', '## 測試、工具與保存','',
              f"原始 Pass T 79/79；新 Phase1b {counts['tests']-114}/{counts['tests']-114}；Pass I + Builder regression 35/35；合計 {counts['tests']}/{counts['tests']}；skipped=0。第一輪唯一 failure 為新測試在 Windows cp950 讀 UTF-8，僅修正新測試後全數通過。缺少 PyAV/FFV1 的測試會 FAIL，不會 skip。",
              '', f"Preservation={preservation['status']}：原始 9,472 + 擴大保護總數 {len(protected)} 個 hash，HEAD／tracked changes 不變。V297、Pass I、Frozen、outputs_v292、existing Phase1/v1、Event Packs 和 Builder 不變。Pass I prompt SHA={preservation['pass_i_prompt_sha256']}。",
              '', 'PyAV16.0.1、OpenCV4.14.0；libavcodec62.11.100、libavformat62.3.100。FFV1/MPEG4 encoder/decoder、libx264 encoder、H264 decoder 可用。ffmpeg/ffprobe CLI 不在 PATH；未下載或安裝。基線執行後 sandbox temp cleanup 曾輸出 PermissionError，但 test exit0；final temp 移到本專案新 smoke 路徑。完整 codec inventory 見 preflight JSON。',
              '', 'MODEL_INFERENCE_CALLS=0；GRAPH_WRITE_ATTEMPTS=0；BUILDER_CHANGES=0；沒有 commit/push，也沒有寫入 mixure_test。M1/M2/M3/M4 皆已保存。Optional scene-only M3b 未執行。',
              '', '## 新增檔案','',
              '程式：phase1b.py、resolver.py、overlap.py、media.py；新 CLI scripts/run_pass_t_phase1b.py；新 tests/test_pass_t_phase1b.py。Artifact 清單見 JSON source_files_added。原始 Phase1 所有程式與報告保留。初次 smoke 留存，最終使用 *_r2 directory，最後 frame duration 依 window end 縮短，未以 nominal FPS 延長靜止畫面。',
              '', '## 最終界線','',
              '**FORMAL_EVALUATION_READY=NO**。此結果證明一段安全 local-track-supported window 的 A/B/C 工程輸入可運作；尚非 event accuracy、身分正確率、評測資料集或 Shadow Mode readiness。停止於本任務。']
    write('reports/PASS_T_PHASE1B_REPORT.json',report)
    write('reports/PASS_T_PHASE1B_REPORT.md','\n'.join(lines)+'\n')
    write('manifests/phase1b_milestone_M4.json',{'status':'COMPLETE','primary_status':status,
                                             'tests':counts,'preservation':preservation['status']})
    return {'status':status,'tests':counts,'preservation':preservation['status']}

"""Stage 0 inspection and Stage 1a delivery. Never invokes a model or Builder."""
import hashlib
import json
from pathlib import Path
from . import contracts as c
from .fixtures import cases
from .evaluation import evaluate

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'artifacts/pass_t'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()


def write(path,value):
    p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True)
    content=value if isinstance(value,str) else json.dumps(value,indent=2,ensure_ascii=False)+'\n'
    p.write_bytes(content.encode('utf-8'))


def inspect_sources():
    base=ROOT/'outputs/current_development'
    events={e['pack_id']:e for e in read(base/'event_windows/event_manifest.json')}
    inputs={v['video_id']:v for v in read(base/'event_windows/development_inputs.json')}
    requests=read(base/'qwen/requests.json');rows=[]
    for request in requests:
        e=events[request['pack_id']];v=e['video_id'];source=ROOT/(v+'.mp4')
        binding_path=ROOT/f'outputs_v292/{v}/identity/target_binding.json'
        binding=read(binding_path).get('bound_target',{})
        candidate_path=ROOT/f'outputs_v292/{v}/candidate_stream.json'
        candidates=read(candidate_path)['observations']
        seed=binding.get('source_track_id')
        supported=[x for x in candidates if x.get('source_track_id')==seed and seed is not None
                   and e['start_time']<=x['timestamp']<e['end_time']]
        local_ids=sorted({str(x['candidate_id']) for x in supported if x.get('candidate_id')})
        # Only an explicit, original binding with observed local source support
        # is resolvable. We never use Re-ID matches or spatial similarity to fill
        # a later gap or choose among unrelated candidates.
        local=str(seed) if supported and len(local_ids)<=1 else None
        reason=[]
        if not e.get('start_time',0)<e.get('end_time',0):reason.append('missing/invalid authorization bounds')
        if e['completeness']!='COMPLETE_EVENT_WINDOW':reason.append('not an existing COMPLETE pack')
        if local is None:reason.append('pack stores global target phone_01 only; no explicit single window-local target mapping; original bound source track has zero observations inside this window')
        source_ok=source.is_file() and sha(source)==inputs[v]['sha256']
        if not source_ok:reason.append('clean source missing/hash mismatch')
        rows.append({'pack_id':e['pack_id'],'video_id':v,'window_start_s':e['start_time'],
            'window_end_s':e['end_time'],'authorized_source_frame_bounds':[e['start_frame'],e['end_frame']],
            'pack_target_id':e.get('target_id'),'target_local_id':local,'seed_source_track_id':seed,
            'seed_observations_in_window':len(supported),'seed_candidate_ids':local_ids,
            'classification':'BLOCKED_WITH_REASON' if reason else 'OK','reasons':reason,
            'clean_source_path':source.relative_to(ROOT).as_posix(),'clean_source_hash_verified':source_ok,
            'binding_source':binding_path.relative_to(ROOT).as_posix(),
            'local_observation_source':candidate_path.relative_to(ROOT).as_posix(),
            'timestamp_provenance_available':'DERIVED_FPS',
            'timeline_path':f'outputs/current_development/event_windows/target_timelines/{v}.json'})
    blocked=sum(x['classification']=='BLOCKED_WITH_REASON' for x in rows)
    return {'event_packs_found':len(rows),'expected_nine':len(rows)==9,'packs':rows,
            'stage0_gate_pass':len(rows)==9 and blocked<5,'blocked_with_reason':blocked,
            'source_pixels_decoded':0,'builder_reruns':0,'model_inference_calls':0}


CORE="""You annotate visually supported temporal events for one local target in one authorized window.
Use only supplied evidence, frame IDs and exact source timestamps. Never infer time from order or nominal FPS.
The vocabulary is target T1, people drawn as P1/P2/etc if supplied, and allowed observed anchors A1/A2/etc if supplied.
Use no other local ID or physical/global identity. If no person tracks are supplied, actor_local_id must be null or UNKNOWN.
Return only JSON satisfying PASS_T_PREDICTION_SCHEMA_V1.json (schema_version v1).
Actions are PICK_UP, MOVE_WHILE_HELD, PLACE, RELEASE, HANDOFF. PICK_UP requires visible support-to-held transition.
PLACE requires observed supported destination ON/IN; proximity alone is insufficient. RELEASE is not automatically PLACE.
HANDOFF requires distinct supplied giver and receiver IDs and visible transfer. Events need evidence_frame_ids, actor/receiver,
target_local_id, onset_interval_s/offset_interval_s, boundary_status, boundary_reason, relation and support_class.
Use uncertainty brackets; null boundaries require ONE_SIDED or UNLOCALIZABLE with a reason. Gaps do not imply activity.
CONFIRMED_NONE with events [] means adequately observable evidence supports no relevant event.
INDETERMINATE with events [] means insufficient evidence; list unresolved action transitions or FINAL_STATE.
EVENTS_OBSERVED means nonempty supported events without unresolved transitions. PARTIALLY_OBSERVED means supported events
plus nonempty unresolved_transitions. UNKNOWN and INDETERMINATE are valid outcomes. Never assert unsupported actions.
Visibility: VISIBLE, OCCLUDED, OUT_OF_VIEW, UNKNOWN. Track loss is not pickup. Occlusion is not placement.
Disappearance is not location. No detected event is not a confirmed negative. Never infer ON/IN/BEHIND from disappearance.
Separate last_confirmed_state from current_visibility_at_window_end; last confirmed state is not current state.
For CONFIRMED cite confirmed_at_s and evidence_frame_ids. Holder status is HELD_BY_PERSON, NOT_HELD or UNKNOWN;
null holder ID does not mean NOT_HELD. HELD_BY_PERSON needs supplied holder ID and matching HELD_BY relation.
NEVER_CONFIRMED requires null confirmed_at_s/holder ID, empty evidence and UNKNOWN holder/relation fields.
Relations: ON, IN, NEAR, LEFT_OF, RIGHT_OF, BEHIND, HELD_BY, UNKNOWN. Reference: IMAGE_2D, PHYSICAL_SCENE or UNKNOWN.
Do not turn image-plane geometry into physical geometry. Cite relation evidence. Use only supplied anchors;
otherwise a short observed anchor description is allowed, but it is not an identity. Never invent hidden destinations.
Every assertion must cite supplied evidence frame IDs. Do not assert an exact window-end state from older evidence.
Return window_end_timestamp_s and visibility_evidence_frame_ids separately. Do not include GT, annotation provenance,
sampled_observability, identity decisions, global aliases, memory writes or graph operations.
"""
SEGMENTS={
'A':"Native video: use the accompanying frame-ID/source-timestamp mapping, not nominal video rate. Encoded PTS must be verified against source-relative times. Unsupported video input must be reported; never substitute images.",
'B':"Ordered images: each separate frame is supplied in chronological order with frame ID and exact source timestamp. Use that mapping for temporal evidence.",
'C':"Storyboard: tiles are chronological row-major. Use the accompanying explicit tile row/column to frame-ID/time mapping. Tile resizing can reduce visible detail; abstain when detail is insufficient."}


DOCUMENTS={
'PASS_T_V1_CONTRACT.md':"""# Pass T v1 contract

Unit: one existing authorized half-open Event Window [start,end), one explicit local target. Never generate a physical alias, update identity authority or write to Trusted Memory Graph. Inputs missing bounds, target or clean recoverable pixels are invalid/unavailable.

Actions: PICK_UP (support→held), MOVE_WHILE_HELD, PLACE (observed support/destination), RELEASE (end contact), HANDOFF (distinct giver/receiver). Track loss, occlusion and disappearance never imply these actions or final location.

Assessment: []+CONFIRMED_NONE requires adequate observable coverage; []+INDETERMINATE requires unresolved transitions; nonempty+EVENTS_OBSERVED requires none unresolved; nonempty+PARTIALLY_OBSERVED requires unresolved transitions. UNKNOWN and NO_RELEVANT_EVENT are not action records. Unresolved enum: actions plus FINAL_STATE.

Temporal events cite evidence_frame_ids, target/actor/receiver local IDs, uncertainty onset and offset intervals, boundary status BRACKETED/ONE_SIDED/UNLOCALIZABLE and reason. Chronology required; gaps are allowed and are not negatives. Definite incompatible overlaps rejected; PICK_UP/MOVE, HANDOFF/MOVE and PLACE/RELEASE may overlap. Unlocalizable events are not assigned artificial times.

Relations: ON/IN/NEAR/LEFT_OF/RIGHT_OF/BEHIND/HELD_BY/UNKNOWN. Reference: IMAGE_2D/PHYSICAL_SCENE/UNKNOWN. HELD_BY anchors are allowed people; spatial anchors are allowed A IDs or null plus short observed anchor_label. Labels are non-authoritative descriptions and require human anchor-equivalence adjudication for scoring. NEAR does not justify PLACE. Never upgrade 2D geometry into physical scene relations.

last_confirmed_state is distinct from current_visibility_at_window_end (VISIBLE/OCCLUDED/OUT_OF_VIEW/UNKNOWN). CONFIRMED has time and evidence; NEVER_CONFIRMED has null time/holder, empty evidence, UNKNOWN holder and relation. Holder UNKNOWN is not NOT_HELD. HELD_BY_PERSON requires consistent holder/HELD_BY relation; NOT_HELD prohibits HELD_BY. Window-end visibility cites separate evidence. A held-before-occlusion state does not assert continued holding at window end.

GT is separate from prediction. GT has full-window observability, per-manifest sampled_observability map, limitations, uncertainty, independent annotation and separate adjudication. DIRECT is computed support_class==DIRECT, never a redundant boolean. INFERABLE is indirect support, UNSUPPORTED cannot justify a model action. SAMPLING_MISSED requires full-window observable=true and sampled support!=DIRECT. Different densities always have different manifests/observability.

OVERLAY_NEUTRAL_V1: clean full-resolution source origin; target fixed RGB(0,180,180), line width 2, no text; people fixed RGB(210,160,0), line width 2, neutral P1.. in first-appearance order. Only exact observed valid boxes; no interpolation during gaps. No event labels/scores. Neutral anchor A IDs if upstream observed. Private mapping is outside model-visible assets. All A/B/C derive from the same overlaid frames. Burned prior overlays are not reused.

Canonical manifest: F000.. zero-padded; original source index/timestamp, source-relative time, neutral image path, hash, timestamp provenance (native PTS preferred; DERIVED_FPS only when documented), overlay policy/version. Strict increasing timestamps and indices; 1ms tolerance for mapping; no unauthorized decoded model-input frames, duplicates or padding.

Grid N=ceil((end-start)*fps-1e-9); t_k=start+k/fps. Choose nearest authorized source time, earlier tie. Collisions retained once and recorded. N>16: indices floor(j*(N-1)/15+0.5), j=0..15, integer-safe. Fewer than eight allowed. SM_ identity hashes canonical sorted-key JSON of window ID/bounds/density/source ID-or-hash/ordered source indices/timestamp provenance. This metadata identity is private; model bundle contains only the opaque manifest ID.

Bundle exact allowlist: opaque hash-derived bundle_id, representation_type A/B/C, schema/version, opaque manifest ID, neutral frame paths/IDs/times/hashes, target T1, person P IDs, allowed A anchors, policy, frozen prompt ID/hash, neutral media path and C tile mapping. No upstream IDs or GT/trigger/reid/score/identityguard fields. All keys/strings/paths/metadata scanned. Core prompt taxonomy exempt, assets never exempt. Neutral aliases are required vocabulary; literal private mapping keys containing alias are forbidden. EXIF/PNG text/container descriptive metadata must be stripped and verified at Stage1b.

A requires decoded frame count/order and encoded PTS within 1ms, encoding details/hash/decoder/loss recorded; irregular mapping failure is A_NON_EQUIVALENT, not equivalence. A_ADAPTER and backend capability separate. B is ordered separate full-resolution images; C row-major deterministic mosaic with explicit mapping, dimensions/transforms and detail loss. Source-frame equivalence does not imply equal detail, tokens or resolution. Unsupported modalities remain unsupported. Stage0-gated adapters are not READY.
""",
'PASS_T_ANNOTATION_PROTOCOL.md':"""# Future Pass T annotation protocol

No DEV annotations are created in Phase1. Validate local target and authorization first. Inspect only the full authorized window and annotate events, uncertainty, actor, last confirmed state, end visibility, relation, unresolved transitions and full-window observability. Then inspect each exact sampled manifest and independently record DIRECT/INFERABLE/UNSUPPORTED plus limitation (OCCLUDED/OUT_OF_VIEW/TOO_SMALL/SAMPLING_MISSED/MOTION_BLUR/VIEW_MISMATCH/WINDOW_BOUNDARY/OTHER). Full-window truth stays constant; sampled observability is manifest-specific. Human references are not model evidence. Never import outside/future frames, physical identity GT or builder conclusions.

Negative CONFIRMED_NONE requires adequate observable coverage; short/occluded windows normally INDETERMINATE. Null holder is not NOT_HELD. Store pseudonym annotator ID, timestamp, tool/schema version, boundary uncertainty. Spatial descriptions require separate anchor adjudication.

Independently double-annotate first 10 DEV windows; then at least 20% of new windows. Preserve independent originals and separate adjudication. Require at least 10 dual cases before treating reliability summaries as informative. Report raw numerator/denominator by assessment agreement, temporally matched action agreement, actor agreement on evaluable cases, last-confirmed-state, end visibility, relation, interval overlap/boundary differences and adjudication count. No single overall percentage substitutes for field reliability; kappa optional. No new UI in Phase1.
""",
'PASS_T_EXPERIMENT_PLAN.md':"""# Future controlled Pass T experiment

Primary A native video / B ordered multi-image / C storyboard share one 3FPS manifest, target, bounds, source frames/timestamps, output schema, overlay, core prompt, model revision, decoding settings and adjudicated GT. Only input-description prompt segment differs. Record media encoding, actual processor resolution, effective tile detail, tokens, temporal resampling and backend behavior. Never replace unsupported native video with images. B is inspectable engineering baseline, not assumed most accurate.

Candidates documented only: historical Qwen2.5-VL, NVIDIA Nemotron Nano 12B v2 VL, VideoLLaMA3-7B. Within-model A/B/C precedes cross-model conclusions. No installations, inference or model performance claims in Phase1.

Always Abstain and Always No Event implemented as deterministic producers and evaluated only on synthetic GT. Last-Frame-Only is a future ablation. Secondary 2/4FPS use separate manifests and per-manifest sampled observability; do not confound FPS with representation. Do not widen rate search or change event windows. Safety filtering precedes coverage/selective accuracy, event understanding, then runtime ranking. DEV annotation is the next phase only after source blockers and integrity gate are resolved.
""",
'PASS_T_EVALUATION_SPEC.md':"""# Pass T evaluation specification

Window is the unit; no frame pooling. Priority: safety → event understanding → engineering. Phase1 validates a deterministic evaluator skeleton using synthetic fixtures, not a benchmark or model-accuracy measurement.

Event matching: same action, one-to-one; prediction extent contained within uncertainty GT bracket expanded by ±0.5s and overlaps that expanded interval. Earliest GT onset first, then smallest interval distance, then prediction index. Unlocalizable boundaries excluded from exact timing scores. Definite order accuracy over matched event pairs; mean boundary localization error over eligible matched brackets. Gaps not negatives. Report actual sample intervals and coarse-sampling limitations.

Direct-observation recall/F1 includes GT sampled support DIRECT only. SAMPLING_MISSED full-window true events are excluded from direct recall and counted separately. Unsupported predictions remain false positives for grounded event F1 even when physically true; separate physical factual error from lack of sampled grounding. Report all five action P/R/F1/support; N/A absent denominators/classes, macro over supported classes only.

False Pickup/Placement negatives: adjudicated window with no corresponding true action and action absent from unresolved_transitions (CONFIRMED_NONE or resolved EVENTS/PARTIALLY_OBSERVED cases). True but sampling-missed actions are not negatives. Report count, eligible negatives, rate and Wilson95% CI. Definite location claim: CONFIRMED state and predicate!=UNKNOWN. Incorrect factual claim and unsupported-by-manifest claim counted separately with totals/rates/CIs. Anchor descriptions require explicit human equivalence adjudication; pending cases excluded from factual location denominator and reported. Unsupported actions stratified SAMPLING_MISSED/OCCLUDED/OUT_OF_VIEW/TOO_SMALL/other. Authority logs include unsupported pickup/placement/holder/final location, invented anchor, invalid frame references, alias assertions, graph attempts. Validators reject invalid claims; no graph interface exists and graph writes must be zero.

Additional metrics: Event macro/per-class F1; order; localization; actor accuracy (N/A without person tracks); final relation precision/coverage; correct abstention; answer coverage and selective accuracy; sampling-missed exclusions. Engineering: schema-valid rate, completion rate, unsupported mode count, latency, peak VRAM, frames, visual tokens, runtime/OOM. Synthetic runs set actual inference metrics N/A. Always Abstain should have zero action FPs and zero answer coverage; Always No Event exposes FNs and class imbalance.

Always report raw numerator/denominator, meaningful percentage and Wilson CI, session counts, case distribution. Zero observed errors do not establish negligible risk. Only session-level resampling when enough independent sessions exist. Shared frames/windows are dependent. Rule: filter unsafe unsupported placement/final-location configurations first; survivors must exceed Always Abstain coverage with acceptable selective accuracy; rank Event F1/order/final relation before engineering on RTX5070Ti16GB. Provisional later DEV targets macroF1≥.75, relation precision≥.85, false placement≤5%, successful schema valid100%, zero unauthorized merges/writes; these are not Phase1 gates or strict tiny-sample cutoffs.
""",
'PASS_T_SHADOW_PROMOTION_CRITERIA.md':"""# Future Shadow Mode promotion contract

Documentation only. Proposals produced, no Trusted Graph writes; human-reviewed references, unchanged IdentityGuard authority. At least14 calendar days,150 eligible auditable windows,3 independent sessions/multiple scene conditions,20 true pickups,20 true placements,75 eligible pickup negatives and75 eligible placement negatives,20 occlusion/out-of-view/insufficient windows. Categories may overlap logically. Extend observation when any gate unmet. Zero-error Wilson upper bound≈3.84/(n+3.84); n≈73 needed for5%, so smaller negative samples report only upper bound, never claim≤5% target.

Review counts/rates/CIs for pickup/placement, unsupported/false location, hallucinated holder changes, abstention, schema failure, unknown coverage, IdentityGuard/gate decisions, proposed versus authorized changes, latency/resources and scene/category distribution. Target zero observed critical unsupported placement/location and unauthorized writes with residual upper bound; any critical error blocks promotion pending correction and re-evaluation.

Shadow success permits consideration of limited guarded end-to-end trial after explicit human engineering review, safety gate review, unchanged identity authority, rollback/audit capability and explicit UNKNOWN handling. It never authorizes production Trusted Graph writes or automatic promotion.
"""}


def deliver_stage1a():
    schemas={'PASS_T_GT_SCHEMA_V1.json':c.GT_SCHEMA,'PASS_T_PREDICTION_SCHEMA_V1.json':c.PREDICTION_SCHEMA,
             'PASS_T_FRAME_MANIFEST_SCHEMA_V1.json':c.MANIFEST_SCHEMA,'PASS_T_MODEL_INPUT_BUNDLE_SCHEMA_V1.json':c.BUNDLE_SCHEMA}
    for name,schema in schemas.items():write('contracts/'+name,{'$schema':'https://json-schema.org/draft/2020-12/schema',**schema})
    for name,doc in DOCUMENTS.items():write('contracts/'+name,doc)
    write('contracts/pass_t_event_annotator_v1.txt',CORE)
    prompt_hash=hashlib.sha256(CORE.encode('utf-8')).hexdigest()
    for mode,text in SEGMENTS.items():write(f'contracts/pass_t_event_annotator_v1_{mode}.txt',text+'\n')
    write('contracts/prompt_manifest.json',{'prompt_id':'pass_t_event_annotator_v1','core_sha256':prompt_hash,
        'core_path':'artifacts/pass_t/contracts/pass_t_event_annotator_v1.txt',
        'segment_sha256':{k:hashlib.sha256((v+'\n').encode()).hexdigest() for k,v in SEGMENTS.items()},
        'combined_prompt_rule':'exact core bytes + newline + exact representation segment bytes',
        'prediction_schema_sha256':sha(OUT/'contracts/PASS_T_PREDICTION_SCHEMA_V1.json'),
        'annotation_started':False,'inference_calls':0})
    fixture_rows=cases();write('smoke/synthetic_contract_fixtures.json',fixture_rows)
    outputs={}
    for abstain in [True,False]:
        rows=[{**item,'prediction':c.baseline(item['bundle'],item['gt']['window_end_s'],abstain)} for item in fixture_rows]
        outputs['ALWAYS_ABSTAIN' if abstain else 'ALWAYS_NO_EVENT']=evaluate(rows)
    write('smoke/synthetic_baseline_evaluation.json',outputs)
    return prompt_hash


def run():
    findings=inspect_sources();write('manifests/stage0_findings.json',findings)
    prompt_hash=deliver_stage1a()
    gate=findings['stage0_gate_pass']
    # Never silently proceed, invent a target or re-derive frozen windows.
    if gate:raise RuntimeError('Stage0 now passes: Stage1b not implemented by this gated delivery; must resolve/report before READY')
    report={'status':'PASS_T_PHASE1_PARTIAL_WITH_BLOCKERS','baseline':'V297_FROZEN',
        'pass_i':'PASS_I_CLOSED_ACQUISITION_LIMITED','schema_version':'v1',
        'event_packs_found':findings['event_packs_found'],'event_packs_integrity_pass':0,
        'event_packs_blocked':findings['event_packs_found'],'stage0_blocked_with_reason':findings['blocked_with_reason'],
        'stage0_gate_pass':False,'stage1a_complete':True,'stage1b':'NOT_STARTED_SOURCE_GATE',
        'A_ADAPTER':'BLOCKED','A_BACKEND_CAPABILITY':'NOT_TESTED','B_MULTI_IMAGE':'BLOCKED','C_STORYBOARD':'BLOCKED',
        'leakage_scan':'NOT_RUN_ON_REAL_PACKS_STAGE0_GATE','prompt_sha256':prompt_hash,
        'model_inference_calls':0,'graph_write_attempts':0,'builder_changes':0,'source_pixels_decoded':0,
        'packs':[{**p,'integrity_status':'NOT_RUN_STAGE0_GATE','A':'BLOCKED','B':'BLOCKED','C':'BLOCKED'} for p in findings['packs']],
        'next_phase':'BLOCKER_RESOLUTION'}
    write('reports/PASS_T_PHASE1_SMOKE_REPORT.json',report)
    table='\n'.join(f"| {p['pack_id']} | {p['window_start_s']:.9f}–{p['window_end_s']:.9f} | {p['target_local_id'] or 'unresolved'} | {p['classification']} | {'; '.join(p['reasons']) or 'original local binding supported in window'} |" for p in findings['packs'])
    write('reports/PASS_T_REPO_FINDINGS.md',f"""# Pass T repository findings

Current commit at task start: 43f08669b37c88a8b17e2e66faed1069308da0b8. Existing unrelated deletions retained, no commit/push.
Builder: `src/memory_graph/events/window_builder.py`, frozen windows in `outputs/current_development/event_windows/event_manifest.json`; selected nine from `outputs/current_development/qwen/requests.json`. Source videos/development membership and FPS in `event_windows/development_inputs.json`; per-video target/person/anchor rows in `event_windows/target_timelines/*.json`.

The actual pack keys are start_time/end_time/start_frame/end_frame/video_id/pack_id/target_id/contexts/frames. Target is global phone_01, not CandidateEpoch/local detector ID. Direct original binding is read from `outputs_v292/<video>/identity/target_binding.json` and matched only to recorded source_track_id in `outputs_v292/<video>/candidate_stream.json` inside the window. Two test1 packs resolve explicit original track17 with seventeen recorded source-track observations each; their candidate_id is not populated. Seven later packs lack that local support. Multiple later candidates or global identity authorization cannot fill this gap. Re-ID/GT not used to choose targets.

| Pack | Authorized seconds [start,end) | Resolved local seed | Stage0 | Verified reason |
|---|---|---|---|---|
{table}

All nine original clean videos exist and hashes match manifested development input SHA. No pixels decoded; native PTS discovery remains untested, documented frame/FPS derivation exists. Stage0 has seven BLOCKED_WITH_REASON (threshold≥5), so Stage1b is stopped for all nine, including the two provisionally OK input records. No MODEL_EVAL_BLOCKED records: clean original media is available.

Existing 5FPS renderer: `reasoning/pipeline.py::render_frame` resizes scene to768×432 on800×600, burns pack ID, frame, trigger-relative BEFORE/DURING/AFTER, identity-authorized markers, masks and reference panels. Review sheets add trigger/completeness labels. These pixels fail new neutrality and cannot be reused.
Native path: `reasoning/video_experiment.py` with existing PyAV under `outputs/current_development/video_event_experiment/.deps`, original-FPS MP4 plus the same burned renderer. Ordered dense images and contact_sheet composition exist but need neutral Stage1b conversion after target gate. Source reading uses cv2 seek/frame reads and FPS-derived timing; the prior native path uses PyAV decode/PTS. Neither existing path satisfies the new common3FPS, half-open, neutral-pixel contract directly, and neither was changed.

Transports: local Qwen `reasoning/model.py`/video_experiment processor; historical model `Qwen/Qwen2.5-VL-7B-Instruct`, revision in `reasoning/common.py`; Pass I Codex transport is unrelated and preserved. No live endpoint invoked; capability NOT_TESTED. jsonschema/Streamlit vendor already exists under `artifacts/pass_i/runtime/vendor`; no installation. Tests use pytest and local src path. Frozen source/prediction/manifests and Pass I protected_before.json were snapshotted to `artifacts/pass_t/manifests/protected_before.json` before new implementation.
""")
    write('reports/PASS_T_PHASE1_SMOKE_REPORT.md',f"""# Pass T Phase1 report

Status: **PASS_T_PHASE1_PARTIAL_WITH_BLOCKERS**. Stage1a contracts delivered; Stage1b stopped by specified Stage0 gate. This establishes no model accuracy and no DEV annotation readiness.

Found9 existing COMPLETE packs, all nine with authorized bounds and hash-verified clean source videos. Seven cannot resolve one explicit local target inside the window. Two test1 records have recorded original local binding support; gate nevertheless stops all real-pack integrity/adaptation work. Integrity pass0/9; actual leakage checks on real assets NOT_RUN. Synthetic neutral bundles are tested separately. A_ADAPTER/B/C BLOCKED, A_BACKEND_CAPABILITY NOT_TESTED; no representations silently substituted.

Contracts: fixed actions/relations/visibility, explicit assessment consistency, manifest-keyed observability, last confirmed vs window-end visibility, holder UNKNOWN, NEVER_CONFIRMED, HANDOFF receiver, uncertain timing/gaps and identity/write rejection. Strict schemas and semantic validators exist. Pure synthetic timestamp sampler implements exact3FPS grid,16 cap, collision/tie handling, content IDs and shared A/B/C manifests. It reads no pixels. Frozen core prompt SHA256: `{prompt_hash}`; separate A/B/C descriptions and schema hash recorded.

Evaluator skeleton implements deterministic baseline producers, matching, direct-observation F1, eligible-negative safety rates/Wilson CIs, unsupported-vs-factual action distinctions, relation/actor/order/coverage and sampling-missed accounting on synthetic fixtures. Runtime/model engineering fields N/A. Synthetic fixture validation/test results and final preservation check are appended by the verified task execution.

Not delivered due gate: clean full-resolution neutral overlay renderer, native encoder/decode verification, real B/C media packaging/metadata stripping, nine-pack integrity smoke. Therefore READY is not claimed. Protected infrastructure not changed; no model installed/downloaded/inferred, no annotations, no graph/alias authority and graph write attempts0.

Next bounded task: obtain explicit, auditable window-local target mapping for the seven blocked existing packs from authoritative recorded local observations, without rerunning Builder or inventing identity. If no such record exists, keep packs unavailable. After source gate passes, implement neutral A/B/C adapters and run no-inference integrity smoke. DEV annotation, formal benchmark,2/4FPS model experiment and Shadow Mode remain later documented protocols only.

See `PASS_T_REPO_FINDINGS.md`, `manifests/stage0_findings.json`, contracts/protocols and `smoke/synthetic_baseline_evaluation.json` for reproduction. Run `.venv/Scripts/python.exe -B scripts/run_pass_t_phase1.py` to regenerate this gated Stage1a delivery. No commit or push.
""")
    return report

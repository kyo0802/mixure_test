# FindMind Event GT annotation policy V2

Policy ID: `PASS_T_EVENT_GT_POLICY_V2` · Response schema: `PASS_T_EVENT_GT_V2` · Use: exploratory DEV only.

This is a prospective policy, not a set of event answers. After the freeze receipt is issued, these bytes, the companion policy JSON and response schema are immutable. Stage B requires the exact human approval `APPROVE_PHASE2A_POLICY_V2 <first 12 hex characters of this MD file's SHA256>`. Missing, mismatched or stale approval blocks Stage B. A requested correction requires a new policy version and receipt; an implementation conflict must stop rather than patch frozen V2. A receipt/hash/UTC is local evidence, not an externally anchored timestamp or proof of human authorship.

V2 is a prospective minimal amendment of frozen V1 (policy MD SHA256 `f443a54675fd3481448da64e1f7afb60d0f94f6ed29f29d428ce21ffd467e614`). V1 and its entire file tree/receipt remain unchanged and unapproved. This revision does not authorize Stage B, collect event answers, migrate V1 responses, or evaluate a model. `V1_TO_V2_DIFFERENCES.md` enumerates every contract change. Except the version/approval boundary and the confirmed-event completeness/evaluation rules below, V1 behavior is inherited unchanged.

## 1. Scope, provenance and eligible items

The V297 baseline, Pass I, IdentityGuard/Re-ID, detector/tracker/SAM, Builder/configurations, original videos, old Pass T contracts/packs, and Phase 1c policies/responses/outcomes/audit remain unchanged. No model inference, automated event labels, Graph writes, global aliases, commit or push is authorized.

There are 9 original packs, 8 unique media windows, 7 non-overlap evidence groups and 6 source video files. Recording-session independence is UNKNOWN. test1 W03/W05 is one SOURCE_RESOLVED media window. Six HUMAN_SEEDED windows are DEV eligible; test8 W06 remains `EXCLUDED_OR_UNRESOLVED` for `EVENT_DEPENDENT_SELECTION`. It is not repaired or promoted by new annotation. All nine original automatic bindings remain `CAUSALITY_UNVERIFIED`; formal eligibility is zero.

Eligible unique window inventory before annotation:

| Original pack(s) | Stratum | Selected local candidate | Authorized native frames | Full-rate frames |
|---|---|---|---|---:|
| test1 W03 + W05 | SOURCE_RESOLVED_DEV | 17 | S000157–S000263 | 107, verified source; new Phase 2a assets pending approval |
| test2 W01 | HUMAN_SEEDED_DEV | 43 | S000180–S000287 | 108 |
| test3 W07 | HUMAN_SEEDED_DEV | 54 | S000402–S000509 | 108 |
| test5 W01 | HUMAN_SEEDED_DEV | 31 | S000162–S000233 | 72 |
| test5 W05 | HUMAN_SEEDED_DEV | 44 | S000342–S000449 | 108 |
| test7 W05 | HUMAN_SEEDED_DEV | 32 | S000373–S000479 | 107 |
| test8 W07 | HUMAN_SEEDED_DEV | 74 | S000936–S001053 | 118 |

These are 7 windows / 7 non-overlap groups / 6 video files, **not seven independent recordings**. Annotated counts are zero at policy freeze. Counts of submitted windows, overlap groups and source files must always be reported separately; no significance or power claim is permitted. Windows were selected because events were expected. No negative controls were sampled; a later NO_CONFIRMED_EVENT answer does not remove this selection bias.

Canonical deduplication uses the verified source SHA256, exact stored window start/end seconds and conservative half-open frame bounds. Serialize keys sorted with compact UTF-8 JSON; item ID is `PT2A_` plus the first 16 SHA256 hex characters. Detect prefix collisions. Preserve all original pack IDs, source/media provenance, local selected ID, eligibility reasons and overlap groups in the private manifest. Never infer recording sessions from filenames. Human localization is not global identity or machine continuity.

## 2. Four separate axes

### Physical transition events — only these two

- `PICKUP`: directly supported transition from resting/supported to held or lifted by an actor.
- `PLACEMENT`: directly supported transition from held to resting/supported at an observable location.

Visibility loss, a nearby hand, experiment expectations or window selection alone support neither event. A handover, slide, push or insertion into a container is not automatically one of these labels. If the visible action has a separately supported ordinary pickup/placement component, cite that component independently; do not rename the entire unmodeled action as an event.

### Physical state — at a cited frame only

`ON_SURFACE`, `HELD_BY_PERSON`, `OTHER_OBSERVED`, `STATE_UNKNOWN`.

ON_SURFACE requires directly visible resting/support, not a guessed table. HELD_BY_PERSON requires visible support by a person, not hand proximity. OTHER_OBSERVED needs a description and direct evidence (for example, visible support inside a container); it is not a speculative new event. STATE_UNKNOWN asserts no physical state. Never persist any known state through an unobserved period.

### Visibility — independent of physical state

`VISIBLE`, `PARTIALLY_OCCLUDED`, `NOT_VISIBLE`, `VISIBILITY_UNKNOWN`.

NOT_VISIBLE uses exactly one observed reason: `OCCLUDED_BY_OBSERVED_OBJECT`, `LEFT_FIELD_OF_VIEW_OBSERVED`, or `REASON_UNKNOWN`. The first two require positively cited visible occlusion/exit evidence. Missing detection does not prove invisibility. Unknown support and visible target can coexist; held state and later unknown visibility can coexist at their separate cited times.

### Window outcome — exactly one

| Outcome | Required meaning and evidence |
|---|---|
| CONFIRMED_EVENTS | One or more supported target events, with explicit event_list_exhaustiveness. Completeness is claimed only with a valid EXHAUSTIVE_ATTESTED human declaration; never infer it from the event list. |
| NO_CONFIRMED_EVENT | Target/state transitions assessable throughout; no PICKUP/PLACEMENT transition occurred. Explicit start/middle/end COVERAGE citations and full-assessability attestation are required. |
| INSUFFICIENT_EVIDENCE | A transition may have occurred, but evidence or target association does not establish it. |
| TARGET_NOT_OBSERVABLE | Target cannot be reliably observed in this window. |

Do not merge these outcomes. Except CONFIRMED_EVENTS, the events array must be empty. NO_CONFIRMED_EVENT requires the first authorized native frame, at least one frame in the middle third of the ordered authorized frame list, and the last authorized native frame. The reviewer must additionally attest that the target's transitions were assessable throughout, with no unobservable gaps; three images alone do not prove this. An ambiguous target or a gap in event assessability requires INSUFFICIENT_EVIDENCE, not a negative event judgment. TARGET_NOT_OBSERVABLE requires no positively supported target-visible citation/state anywhere in the item; limited or ambiguous observations use INSUFFICIENT_EVIDENCE instead. NO_CONFIRMED_EVENT says nothing about motions outside this two-event ontology.

## 2.1. Confirmed-event list exhaustiveness — V2 amendment

For CONFIRMED_EVENTS only, the required field `event_list_exhaustiveness` has **exactly** these values:

- `EXHAUSTIVE_ATTESTED`
- `NOT_ATTESTED`
- `UNKNOWN`

No value is inferred or preselected. One supported event, several events, high confidence or start/end images do not imply an exhaustive list.

EXHAUSTIVE_ATTESTED requires a separate explicit `event_list_exhaustiveness_attestation` with all four statements affirmatively chosen by the human:

1. `entire_authorized_window_reviewed=true`: the entire authorized window was reviewed.
2. `all_confirmable_target_pickup_and_placement_annotated=true`: all confirmable target PICKUP and PLACEMENT transitions inside it were annotated.
3. `no_unresolved_gap_could_conceal_additional_target_events=true`: no unresolved visibility, target-association or temporal gap could conceal additional target PICKUP/PLACEMENT events.
4. `scope_limited_to_pickup_placement_ontology=true`: this completeness claim applies only to the two-event ontology, not to all physical actions.

A general human-attestation checkbox does not substitute for these four statements. An unchecked, false, absent or unknown statement does not establish completeness. The attestation object is present only for EXHAUSTIVE_ATTESTED; NOT_ATTESTED/UNKNOWN must not carry a stale exhaustive claim.

EXHAUSTIVE_ATTESTED also requires the existing `coverage_assessment=THROUGHOUT_ASSESSABLE`, supported COVERAGE citations at the first authorized frame, a frame in the middle third and the last authorized frame, and their IDs in `observation_coverage_frame_ids`. Validate these citations by the unchanged frame/time/kind rules. **These citations alone are not proof of continuous assessability.** Full-window assessability is an explicit human declaration; the human must review the complete authorized window, not only its three cited images.

If a possible transition could have occurred during an unobservable or unresolved association/temporal gap, EXHAUSTIVE_ATTESTED is unavailable. Preserve supported events with NOT_ATTESTED or UNKNOWN, and explicit existing uncertainty status/description explaining the incompleteness, gap or unknown completeness. At the window level, these non-exhaustive values require OTHER_UNCERTAINTY, TIMING_UNCERTAIN or UNKNOWN; NO_ADDITIONAL_UNCERTAINTY is incompatible with unresolved list completeness. Event-specific uncertainty fields remain unchanged. Uncertain exact time of an already supported event is not by itself proof of additional hidden events; do not blanket-reject the inherited bounded/timing-uncertain event representations when full event assessability genuinely remains established.

NO_CONFIRMED_EVENT is unchanged: full-window assessability, start/middle/end coverage, explicit human negative-event choice and general human attestation are required. No new exhaustiveness field or redundant negative-attestation field is added to this outcome. INSUFFICIENT_EVIDENCE and TARGET_NOT_OBSERVABLE make no completeness claim. For all three non-confirmed outcomes, both new exhaustiveness fields are **absent**, not null or given a default.

## 2.2. Evaluation evidence eligibility — V2 amendment

Only **validated EXHAUSTIVE_ATTESTED CONFIRMED_EVENTS windows** and **validated strict NO_CONFIRMED_EVENT windows** can support full-window FP, FN, precision, recall and hallucination-rate evaluation of the target PICKUP/PLACEMENT ontology. This is a necessary evidence condition, not a complete scoring protocol or authorization to run evaluation now.

The derived `full_window_event_evaluation_supported` flag is true only when the response is schema/semantically valid; Phase 1c originally permits that DEV item; selected-target association supports the full-window determination; all leakage/global-identity/unsupported-track-extension exclusions are clear; and the exhaustive-confirmed or strict-no-event condition is valid. An attestation cannot override an excluded Phase 1c pack, unreliable target association, unauthorized information or any existing invalidity.

The derived `primary_full_window_metrics_eligible` flag additionally requires NOT_DEPENDENT. PARTIALLY_DEPENDENT, DEPENDENT and UNKNOWN retain the inherited separate sensitivity strata and never enter primary silently. Record causality without modification: CAUSALITY_UNVERIFIED is not upgraded by completeness; exploratory DEV permission is not formal eligibility. All current formal eligibility remains zero.

NOT_ATTESTED and UNKNOWN are never treated as exhaustive negatives for unlisted events. Supported event annotations in validated, otherwise eligible non-exhaustive windows may support **separately reported exploratory matching or qualitative error analysis**. A model prediction absent from such a list is unevaluated, not automatically FP or hallucination; the list also cannot establish full-window FN/recall. Report observed matching separately from full-window metrics. A gap affecting unobserved events does not erase a separately valid positive event with supported target association.

Completeness applies only to the two event types. Unmodeled actions, actor identity, global physical identity or guaranteed current location are outside this claim. Future Phase 2b must preregister event matching/timing tolerances, scoring, metrics and hallucination-rate denominators/zero-denominator handling, sampling and information conditions. No metrics are calculated or parameters chosen in Stage A.

## 3. Unmodeled observations

Use a separate `unmodeled_observations` list: description, authorized evidence frame IDs and full citations. Sliding, pushing, handover, container/bag insertion and other motions remain free text, never confirmed two-event ontology event types. If they prevent determining the two transitions, use INSUFFICIENT_EVIDENCE and explain. Finalize reports observation count, affected windows and descriptions as an ontology-coverage gap. Do not automatically classify free text or claim a general “moved” detector.

## 4. Authorized evidence and time authority

Only native source frames satisfying **both** `lo ≤ source_frame_index < hi` and `start_s ≤ native_PTS_s < end_s` are citable. The immutable review-item frame table is the authority. Bounds are conservative; do not extend the old inclusive endpoint. Native timestamps must be finite and match that table within 1 microsecond; store the table value, never interpolate time. Source/index continuity, monotonic PTS and hashes must be verified before an item is released. No fallback from missing PTS to derived FPS.

Existing full-rate IDs are `S` plus six decimal source-frame digits. test1 legacy `F000..F010` is sampled-pack notation, not a full-rate citation ID; preserve the verified F-to-S map privately. `Rxxxxxx` is never citable. Observation-row timestamps may use derived FPS and differ from native PTS; link observations by **exact source frame index**, then cite the native frame-table timestamp. Do not nearest-match, interpolate boxes, infer a track edge, or let a candidate label substitute for visual evidence.

All review images are verified full source frames, 1280×720. Coordinate system `REVIEW_FRAME_PIXELS_V1`: origin top-left, x right, y down, raw image pixels. Full-frame crop-to-source transform is `[[1,0,0],[0,1,0]]`. GUI scale/letterbox must be inverted before saving coordinates. Existing pre-window crops use verified integer left/top and ceil right/bottom bounds; their source translation is recorded only when image dimensions and source pixels match. They are references, not marker/event evidence.

The inherited Phase 1c policy allows at most three exact original-seed observations (first, binding if present, last) strictly before start, deduplicated and in ascending order. Show only verified existing authorized references, or newly bounded/verified reference assets satisfying that exact policy during Stage B preparation; do not invent a reference. Label `REFERENCE_PRE_WINDOW — non-citable`. References help recognition only. Event/state support must be visible in-window. No arbitrary source-video scrubbing, full source-video path, beyond-window material, answer keys, physical GT or model predictions enters the viewer.

### Citation fields and kinds

Each citation records frame ID, authoritative timestamp, role, kind, observation IDs, written visual description if needed and target association status. Roles: BEFORE, TRANSITION, AFTER, STATE, COVERAGE. Association statuses: SUPPORTED, AMBIGUOUS, NOT_VISIBLE, UNKNOWN.

- `CANDIDATE_OBSERVATION_BACKED`: existing selected-local-candidate observation at that exact authorized frame; nonempty IDs verified against the immutable item table. A detector observation alone does not make association SUPPORTED.
- `DIRECT_VISUAL_ONLY`: no existing selected-candidate observation at that frame; observation IDs empty; nonempty written description of **what target evidence is visible and where**. This establishes no machine association and cannot extend a track. Other candidates' observations do not back the selected target.

All confirmed-event and known-state citations require SUPPORTED target association. If a visible event cannot reliably be associated to the selected local target, record uncertainty without a confirmed target event. A mistaken/ambiguous recorded box is not automatically trusted or quietly edited. Direct evidence while held/occluded is permitted without a detector observation; this avoids detector-visibility bias.

No automatic association from test7 local 32 to 34 or test8 local 74 to candidate_014 is authorized. If the reviewer can independently support the selected target at a later frame with no selected observation, it may be DIRECT_VISUAL_ONLY with written support, never a new machine edge.

## 5. Confirmed events and chronology

Each event contains its item ID, `EVT001`-style unique event ID, PICKUP/PLACEMENT type, the selected local reference, temporal status/bounds, citations, optional actor (VISIBLE_PERSON_UNRESOLVED / NOT_OBSERVED / null), optional directly observed before/after physical-state records, uncertainty, confidence, human rationale and provenance. Actor is not a person's identity. Confidence (HIGH / MEDIUM / LOW / UNKNOWN) is a subjective declaration, not probability or a replacement for evidence. Uncertainty status is NO_ADDITIONAL_UNCERTAINTY / TIMING_UNCERTAIN / OTHER_UNCERTAINTY / UNKNOWN with a written description; it is not an outcome label.

Every confirmed event requires at least one BEFORE and one AFTER citation with strict timestamp order. Both must positively support the event's transition and local target. States are recorded if observed; null/STATE_UNKNOWN is allowed and does not imply a state. Definite contrary state claims must be rejected: PICKUP cannot claim a known HELD_BY_PERSON before-state or known ON_SURFACE after-state; PLACEMENT cannot claim a known ON_SURFACE before-state or known HELD_BY_PERSON after-state. OTHER_OBSERVED is judged by the reviewer with explicit support, not converted automatically. Unknown states never establish the transition alone.

| Temporal status | Stored time representation |
|---|---|
| EXACT_OBSERVED_TRANSITION | At least one TRANSITION citation; start and end equal one cited transition's native frame/time. BEFORE strictly earlier, AFTER strictly later. “Exact” means observed native-frame resolution, not subframe physical certainty. |
| BOUNDED_BY_BEFORE_AFTER_EVIDENCE | Start = latest cited BEFORE; end = earliest cited AFTER; strict positive interval. Transition moment is unknown. TRANSITION citations, if supplied, must lie inside the bracket. |
| TIMING_UNCERTAIN | Same conservative observed BEFORE/AFTER bracket, with explicit timing uncertainty. No fabricated midpoint. |

All event evidence and endpoints remain inside the authorized half-open window. Before/after state citations use STATE role. A before-state frame is no later than the latest BEFORE citation; an after-state frame is no earlier than the earliest AFTER citation. State evidence must include its asserted frame and support that assertion. Other citations cannot contradict the claimed chronology. Sort events by `(start timestamp, end timestamp, event ID)`. IDs are unique; duplicate events/citations are rejected. Overlapping uncertain brackets are retained only with an explicit chronology-uncertainty flag on each involved event, not treated as precise order. Contradictory definite opposite transitions at the same exact instant/frame are invalid. Do not enforce alternating events across unobserved gaps or infer missing events.

## 6. Last confirmed state and location

Record the latest frame at which the claimed physical state is directly supported, with STATE citations. Known state requires a frame, native timestamp and SUPPORTED target evidence. OTHER_OBSERVED also requires a description. A physical state at an earlier visible frame is not the final frame's state. Annotators must consider all reviewed in-window evidence; the validator cannot prove their visual judgment or absence of a later visible state.

STATE_UNKNOWN may have no last-confirmed frame/time. It may also accompany a directly supported target location at a frame when support/physical state is uncertain; in that case frame/time, STATE citations and rationale are required, and no physical support is asserted. If frame is null, timestamp, location, marker and location evidence must all be absent. Do not make up a frame for missing evidence.

`last_confirmed_location_description` is optional and only directly supported at the cited last-confirmed frame. Nonempty location evidence is required when a description or marker is present and must include that frame and corresponding SUPPORTED STATE citations. A marker is optional, drawn manually in the GUI (origin GUI_DRAWN), never copied from a detector box. POINT has two coordinates with `0 ≤ x < width`, `0 ≤ y < height`; BBOX has four with `0 ≤ x1 < x2 ≤ width`, `0 ≤ y1 < y2 ≤ height`. Marker frame equals last-confirmed frame; coordinates use REVIEW_FRAME_PIXELS_V1 and the verified transform. No room, named surface, destination or current-location claim may be guessed.

`visibility_at_window_end` is an independent assessment at the **last authorized native frame**, which can precede the numeric end boundary. VISIBLE/PARTIALLY_OCCLUDED requires supported target evidence at that frame; NOT_VISIBLE requires an assessment citation there and a reason, plus direct cited evidence for any positive occlusion/exit reason. VISIBILITY_UNKNOWN explicitly records uncertainty and need not invent evidence. These labels never overwrite earlier physical state.

Record `unknown_or_unobserved_afterward` for the period after last confirmation (within the reviewed window; if nothing is confirmed, treat the window's target state as unknown). `subsequent_location` defaults to UNKNOWN. OBSERVED_IN_WINDOW is permitted only with directly supported, strictly later in-window location citations and description; never infer location beyond the window. It does not silently persist the earlier state. If a later known physical state is supported, update last-confirmed-state to that later evidence. A target leaving view while held can have last state HELD_BY_PERSON and subsequent location UNKNOWN.

## 7. Identity dependence, reviewer context and leakage

Record target_identification_event_dependence: NOT_DEPENDENT / PARTIALLY_DEPENDENT / DEPENDENT / UNKNOWN, with rationale. Only an originally eligible, valid, uncompromised NOT_DEPENDENT item enters the **primary target-localized denominator**. PARTIALLY_DEPENDENT, DEPENDENT and UNKNOWN remain separate sensitivity strata, never merged into primary. This does not upgrade formal eligibility or causality. An initially excluded Phase 1c item remains excluded regardless of new declarations.

Backend computes same_reviewer_as_phase1c by exact reviewer ID equality; SOURCE_RESOLVED without a Phase 1c reviewer uses null. The annotator declares target_recognition_used_pre_window_reference; interaction logs record references opened and overlay toggles but are advisory. Matching IDs cannot prove authorship. The same person likely performed identity localization and event annotation; self-declared dependence is not independently verified.

The new response adapter may read only the selected local ID and its provenance: eligibility/stratum, source response/item hashes, reviewer ID for backend comparison and policy linkage. No Phase 1c rationale, cited evidence frames or uncertainty text is loaded/displayed by the new UI; never import the old viewer/response-loader that loads those answers. Raw outcomes/full source manifests stay private. Seed selection cannot be retroactively changed by event GT.

Explicit attestations record whether unauthorized future material, source scrubbing, experimental answer keys, model predictions or prior event answers were viewed; global identity or unsupported track-extension claims; and whether event-derived recognition affected identification. Compromised records remain auditable but are excluded; never silently repaired. UNKNOWN/dependence is a meaningful response, not invalid GT by itself. Automated checks can enforce allowed paths/fields/hashes and detect known prohibited data paths; they cannot prove visual correctness or verify all free text. No claim of cryptographic human correctness is made.

## 8. UI, submission and blinded repeat

The native local Tk GUI has no network. It exposes only hashed authorized frames/references, provenance stratum/local selected ID, neutral exact-index boxes, frame IDs and native PTS. It starts with selected-candidate-only overlay, has a global off-switch, hides other candidates until explicit logged opt-in, and displays no scores, areas, ranking, track history or global identities. No event/state/outcome/marker answer is prefilled. Controls support playback, slider, navigation, all citation roles/kinds, multiple events, unknown outcomes, unmodeled observations, manual point/box, dependence and attestations. Pause/resume exposes completion status without earlier event answers; submission is explicit.



V2 planned GUI amendment: show the three-value completeness selector only for CONFIRMED_EVENTS, with no default. Four independent attestation controls start unchecked. Enable exhaustive submission only with all four affirmative statements and full-window assessability/coverage; explain gap exclusion and the limited ontology scope. Selecting GAPS_OR_UNCERTAINTY or UNKNOWN assessability blocks an exhaustive claim. Non-exhaustive/unknown records require explicit uncertainty. Switching to any other outcome omits both completeness fields. No completion status, tracking confidence or earlier answer can prefill them.

Use append-only exclusive response creation with real UTC, UUID, reviewer ID, human_attestation=true, submitted_via=human_event_gt_review_viewer, automatic timestamp flag, schema/policy/item/source/authorization hashes and round. Round 1 has relabel_of=null. A second submission for the same item/round is a duplicate; never choose latest/first silently. Old bytes are immutable; a correction needs an explicit separately authorized versioned workflow, not overwriting.

Optional round 2 has review_round=2 and relabel_of equal to the validated round-1 response's SHA256. Blinded UI receives only linkage SHA, backend reviewer/time metadata and original evidence; it does not load first-round event answers. Recommended minimum delay is **7 days**, proposed as part of this policy for human approval. Shorter delay is flagged and reported, not silently treated as independent or automatically rejected. Same-reviewer comparison is descriptive only.

Repeat subset is selected before any event labels: sort eligible unique item IDs by SHA256 of UTF-8 `PASS_T_PHASE2A_REPEAT_V1|` + item ID (ties by ID); take `max(1, ceil(N/4))`, or zero if N=0. Thus N=7 proposes two repeat items. Freeze chosen IDs and rule in the Stage B manifest before first event response. No outcome-based selection. Subset/delay policy changes after this freeze need a new policy version. Optional repeats do not imply that a single annotator establishes reliability.

## 9. Validation, finalize and sampling diagnostic

Validate schema first, then immutable manifest membership/provenance, exact selected candidate, role/kind/observation membership, native PTS, half-open bounds, chronology/state consistency, coverage, axis separation, direct last-state support, marker geometry, reviewer linkage, strata, duplicate/immutability, round isolation, overlap accounting, exposure attestations and preserved hashes. JSON Schema cannot enforce all cross-record visual/temporal relations; Stage B semantic validation is mandatory. Incomplete and invalid responses have explicit reasons. No automatic GT guesses or invented events to pass validation.



V2 semantic validation additionally enforces confirmed-only field presence, exact enum, the four-part attestation, supported start/middle/end COVERAGE and full assessability; explicit incompleteness uncertainty; and all original eligibility/leakage/association/dependence rules before evaluation flags. Known structured gaps or unsupported coverage cannot coexist with valid exhaustive completeness. Checks cannot independently prove a visual statement or infer truth from free text. No automatic downgrading, upgrade, gap filling or event inference is allowed.

Finalize runs separately **after genuine human annotation**. It writes separate validated outcomes, completeness/unresolved counts, read-only DEV export with hashes, label/citation-kind/unmodeled distributions, source/dependence strata and exclusions. Report windows, non-overlap groups and source files separately; flag overlap/session uncertainty, no negatives and base-rate bias. Record original CAUSALITY_UNVERIFIED without promotion. Empty data stays empty; infrastructure readiness is never EVENT_GT_COMPLETE.



V2 finalize exports confirmed-only event_list_exhaustiveness, a derived completeness_basis (EXHAUSTIVE_ATTESTED / STRICT_NO_CONFIRMED_EVENT / NON_EXHAUSTIVE / UNKNOWN / NOT_APPLICABLE), full_window_event_evaluation_supported, primary_full_window_metrics_eligible, explicit event_evaluation_exclusion_reasons and supported_event_exploratory_use_allowed. These are validated derived metadata, not new human completeness answers for the other outcomes. Report exhaustiveness values, full-window eligible/excluded counts and reasons, seed/dependence strata and windows/groups/source counts separately. INSUFFICIENT_EVIDENCE/TARGET_NOT_OBSERVABLE use NOT_APPLICABLE and remain excluded from full-window event evaluation. Preserve non-exhaustive positives separately; never create negatives for unlisted events. No model comparison or metric computation is part of Phase 2a.

Sampling-resolvability is a deterministic descriptive diagnostic with **human-supplied positive integer frame strides only**, no model and no selected default. For each confirmed event, map cited BEFORE/AFTER frames to positions in the full-rate authorized frame list. Their spans are inclusive envelopes from earliest to latest cited frame of each role, not proof that every interior frame is informative. For every offset `o=0..k-1`, the uniform sample positions satisfy `j % k = o`. Report whether at least one sample is inside the BEFORE span and at least one inside the AFTER span, all-offset success, successful/failed offsets and endpoint frame/time values. Flag transition bracket width in full-rate frame-position units shorter than k; also report its native PTS duration. Use native time deltas for variable rate; do not equate k with a guessed constant-FPS duration. Sampling is window-relative and independent of GT, never GT-driven frame selection for a model. If no strides were supplied report SAMPLING_NOT_REQUESTED; if no confirmed events report NO_CONFIRMED_EVENTS. An all-offset hit is necessary evidence availability under this envelope diagnostic, not guaranteed VLM resolvability or model accuracy.

The future VLM sampling/frame count/prompt/model settings and whether model inputs include pre-window references remain TBD until a separate Phase 2b preregistration. Human access to references must be disclosed. No present policy implies approval for future model transmission.

V2 test specification adds: each enum, every missing/false attestation, first/middle/end coverage membership, both citation kinds, known-gap exclusion, explicit non-exhaustive uncertainty, unchanged negative-event semantics and absent completeness fields for other outcomes, V1/V2 incompatibility, original eligibility/association/leakage/dependence/causality gates, no unlisted-event negatives, GUI unchecked/no-default/stale-field behavior and finalize counts. All other V1 test categories remain required after approval. Stage A checks are synthetic document checks only; production GUI/semantic/finalize behavior remains unimplemented.

## 10. Release and stop conditions

Stage A releases V2 policy/schema/receipt/report only and stops at PASS_T_PHASE2A_POLICY_V2_FROZEN_AWAITING_APPROVAL. Stage B may release annotation infrastructure only after matching approval and passing required tests/preservation; status PASS_T_PHASE2A_ANNOTATION_INFRASTRUCTURE_READY. Event GT is completed only by genuine validated human responses, never by the engineer.

Stop for missing/inconsistent source evidence, failed hashes/PTS/coordinate verification, incompatible candidate localization, unauthorized future evidence, a required protected-file edit, incompatible frozen policy/schema, or absent/mismatched approval. Protected manifests are not extended in place. A confirmed transition is not proof of global identity, causal binding or a trusted Memory Graph fact.


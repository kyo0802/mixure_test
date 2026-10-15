# V1D Output Contract Root-Cause Diagnosis — locked criteria

Task: PASS_T_PHASE2B_QWEN_NF4_V1D_CONTRACT_DIAGNOSIS

## Scope and plan
Only existing evidence, CPU/text/hash/JSON analysis, and existing synthetic C6 pixels. No weights, torch/transformers/model initialization, CUDA, GPU, inference, fixtures, real Phase 2a DEV media or GT, source/runtime/prompt/schema/parser/validator/evaluator changes, protocol freeze, pilot, Memory Graph, installation, download, branch/worktree, commit/push. All writes are confined to this one new directory. Existing WORKSPACE navigation files remain unchanged under the task's narrower read-only rule.

Sequence: inventory paths/hashes and Git state; write independent lock receipt; C1–C6; report; compare preservation snapshots. Do not change this criteria file after the lock. Preliminary inventory inspects receipt structure only and does not constitute C1–C6 conclusions.

## Authority and evidence levels
Authoritative regression: artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c. Verify actual existing paths, eight raw outputs and receipt hashes, execution manifest, prompt identities and schema. V1D SHA: 7008254e618dc8bacdbdeaae3cbf471220afb5efd6c80afc8b9ea5fb5c96b9b0. V1C SHA: 3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722. Root uncertainty is /uncertainty.

E1: original captured execution prompt/input receipt/token inventory, attributable to attempt and verified hash. E2: deterministic reconstruction, explicitly RECONSTRUCTED_NOT_EXECUTION_CAPTURED; never replace E1 with E2. E3: static source/configuration, not historical delivery proof. E4: UNVERIFIED, missing/incomplete evidence. Distinguish rendered visible text, chat serialization, token IDs, processor tensors/pixels and private frame/PTS mappings. Rendered or decoded text alone is not full multimodal input. Record missing historical tokens/tensors. No reconstruction is necessary if adequate captured text exists.

## C1 — all eight historical texts
Find every occurrence of timing_uncertainty, root uncertainty and window_cited_frame_aliases, plus empty string/array placeholders and other required-field skeletons. Record attempt, representation, source SHA, section, offsets and exact context, evidence level. Distinguish literal output example, schema type declaration, explicit permission for empty, and replace-required placeholder. Mere empty syntax or type declarations are not causal evidence.

## C2 — all attempts, all three representations
Check the exact three V1D additions (Timing evidence, Window uncertainty, Citation scope) in captured final rendered text, record offsets/hash, chat preservation, token evidence, truncation indicators and generation-input provenance. Classify each attempt DELIVERED_VERIFIED, DELIVERY_MISMATCH_VERIFIED, RECONSTRUCTED_ONLY or UNVERIFIED. Current code alone proves neither delivery nor absence. Optional receipt absence does not prove an instruction was missing. Full token arrays absent must be disclosed even if captured serialization supports delivery.

## C3 — explicit contradictions
Inspect system, task, JSON schema, representation instructions and chat wrapper. Look for unknown-to-empty instructions, empty citation permissions, empty-as-no-uncertainty definitions, retain-placeholder instructions and required/optional conflicts. Every definite or suspected conflict must quote both instructions, locations, applicable fields, instruction levels and representation scope. Concise JSON-only formatting does not itself contradict nonempty strings. Output violations alone do not prove contradictory instructions.

## C4 — copying and empty outputs
Inspect each raw JSON for empty required fields. Record field paths, exact output substring/offset, matching prompt substring/offset/length/evidence. Search substantive exact overlaps (at least 12 whitespace-delimited words) and all repeated nonempty natural-language leaf values across attempts, excluding mandatory enum labels and keys from distinctive-copy claims. Generic empty strings and schema-mandated structure are weak, nondistinctive matches. D1 requires distinctive transmitted template/copying pattern across fields or explicit encouragement to retain empty placeholders; even strong association is not experimental causal proof.

## C5 — descriptive distributions only
Denominator: eight attempts, and separately emitted event objects. Tabulate representation, actual outcome, actual event count, event index, private intended zero/one/multiple events, and co-occurrence of empty event timing/root uncertainty/window citations. Show counts and denominators, not population estimates or significance. Private synthetic intentions are designer labels, not adjudicated physical GT. No model accuracy or hallucination-rate conclusion.

## C6 — R05_C04
Verify raw SHA; enumerate both original events, event types, timing/citations and window citations. Audit all eight aliases and source mappings. Decode only this existing scenario's source RGB frames on CPU and compare canonical RGB hashes and exact byte equality. Trace storyboard/processor mapping via original receipts and existing manifest; distinguish verified source equality from any unrecorded transformed pixels/encoding/model interpretation. If identical, conclude only no observed interframe source-RGB change. No attention claim, adjudicated false positive or formal metrics. Any unresolved visual judgment: VISUAL_JUDGMENT_NOT_ADJUDICATED.

## Primary classification — choose exactly one, in this precedence
1. D2_INSTRUCTION_NOT_DELIVERED: E1 proves a V1D addition was actually missing, modified or truncated.
2. D3_INSTRUCTION_CONFLICT: definite explicit contradictory requirement.
3. D1_TEMPLATE_INDUCED: stronger distinctive transmitted template/copying evidence or explicit empty-retention instruction; generic empty syntax insufficient, no causal proof asserted.
4. D5_INSUFFICIENT_EVIDENCE: critical historical evidence prevents deciding C1–C3 across representations.
5. D4_NO_DEFECT_FOUND: adequate captured evidence across all representations, no definite observable C1–C3 defect; scoped finding, not proof of error-free runtime or physical capability.

Secondary supported findings may coexist. D1–D3: prose-only minimum correction for human consideration, no patch/new prompt. D4: close this diagnosis line, no speculative prompt revision. D5: list missing evidence, no rebuild/rerun. Always stop for human final exploratory Qwen Pilot protocol review; do not approve/freeze V1D or run DEV.

## Required evidence and preservation
Produce diagnosis_report.md with 12 sections: primary, completeness, C1, C2, C3, C4, C5, C6, secondary, limitations, human decision, preservation. evidence_index.json contains claim ID, source+SHA, attempt, representation, byte/character/line location, exact quote and E level. Additional machine-readable tables permitted only here. readonly_preservation_report.md compares Git HEAD/index/staged/worktree and relevant existing hashes, including V1C/V1D, schema/parser/validator, V2, bridge/NF4, eight raw outputs and all synthetic assets. Do not claim hashes alone prove absence of actions by external processes. Record actual diagnostic imports/access scope, no real DEV, no model/CUDA/generation/commit. Any preservation mismatch is reported, never silently repaired.

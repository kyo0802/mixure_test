# V2.4 — Appearance-Assisted Safe Long-Gap Re-identification

## 1. Research Question

Can a persistent phone identity be recovered after a long `UNOBSERVED` interval, among three phone-like candidates, using inference-time evidence without reviewed identity labels? In this one controlled Task2 case, yes: the frozen matcher selected one candidate uniquely, and evaluation afterward verified it.

## 2. Frozen Baseline

V2.3 YOLO + SAM 2.1 fusion, persistent entity registry, observation graph, source-ID separation, and the frame312 hand-drift rejection were reused. No V2.1–V2.3 artifact was rewritten. There were zero new YOLO, SAM propagation, or Qwen calls. The V2.3 registry SHA-256 is recorded in each V2.4 audit.

## 3. Appearance Model

One model: torchvision 0.25.0 MobileNetV3 Small ImageNet-1K, pooled convolutional features, L2 normalization, cosine similarity. The official weight checkpoint SHA-256 is `047dcff4addef86ea5bc2eff13c9614dc11f47ab1160d0a71a25e7db994f4e1f`; inference used CUDA. Each crop uses original RGB pixels, a 5% padded YOLO box, a trustworthy SAM foreground mask when available with neutral RGB-128 background, then Resize 256, CenterCrop 224, and ImageNet normalization. Embeddings are cached under `cache/` by model hash and crop pixels. One model and one preprocessing path were used for trusted prototypes and late candidates.

## 4. Trusted Appearance Memory

The Task1 bank contains frames 240 and 270; Task2 contains 90, 114, 210, and 216. Frames were chosen as the highest-confidence views, up to two per YOLO track and four total. Admission required V2.3 local YOLO confidence ≥0.5, an accepted V2.2 SAM mask without drift flag, and box IoU ≥0.5. The bank persists while `phone_01` is `UNOBSERVED`. Frame312, conflict/rejected propagation, ambiguous candidates, and unknown identities cannot enter it. [Task1 bank](task1/appearance_bank.json) and [Task2 bank](task2/appearance_bank.json) contain provenance and cache keys; vectors are stored in binary cache files.

## 5. Development Controls

The permitted Task2 short-gap positive control, track22 ↔ track43, reached max cosine **0.7113** (top-two mean 0.7057). The Task1 original phone ↔ later distinct desk phone negative control reached **0.3642** (top-two mean 0.3634); no merge occurred. The two Task2 desk phones had cosine **0.8285 to each other**, but 18 trusted same-frame distinct observations, so appearance cannot justify merging them. That pair was measured only in evaluation after the parameter freeze and did not calibrate thresholds. These controls do not establish a population error rate.

## 6. Frozen Re-ID Parameters

The [manifest](reid_parameter_manifest.json) was written and SHA-256 locked **before** any late Task2 candidate scoring: `83be58f427c2c7723d026eb52504f7c3f89afd7497595861885a0ca302b404ba`. Threshold **0.60** lies between the permitted positive and Task1 negative controls; required best-versus-second margin is **0.10**. A match also requires at least two trusted prototypes, compatible semantics, a later timestamp, a reliable YOLO-seeded nonempty candidate mask, and no trusted simultaneous-distinct contradiction. Graph neighborhood is logged but never sufficient to match. A weak score remains `AMBIGUOUS`, rather than asserting a new identity solely from appearance.

The parameter manifest hash and a programmatic GT-isolation check passed before blind inference. The inference modules use frozen visual/registry artifacts and contain no reviewed identity or GT access. The prediction audit hashes were recorded before the separate evaluator read GT; see [summary](reid_summary.json).

## 7. Task1

The later desk phone (`entity_0067`, track70) scored **0.3642** against `phone_01` and received `AMBIGUOUS`. It remained separate, with no false merge. The candidate uses a YOLO crop without a trusted SAM mask, so the matcher correctly did not assert a categorical `REJECT` or `NEW_ENTITY` from low appearance alone. See [Task1 review](task1/review.md), [audit](task1/reid_audit.json), and [contact sheet](task1/reid_contact_sheet.jpg).

## 8. Task2 Long-gap Challenge

All three candidates were scored at their first frozen YOLO-seeded SAM candidate frame, 528. All were phone-like, occurred after the last trusted `phone_01` observation, and had no query/candidate coexistence contradiction. Graph context remained supporting only. Scores below are cosine similarities to trusted prototypes at frames **90 / 114 / 210 / 216**:

| Candidate | Per-prototype similarity | Max | Top-two mean | Inference decision |
|---|---|---:|---:|---|
| `candidate_phone_01` | .645 / .630 / .695 / .670 | **.695** | .683 | `MATCH` |
| `candidate_phone_02` | .460 / .453 / .445 / .444 | .460 | .456 | `AMBIGUOUS` |
| `candidate_phone_03` | .498 / .474 / .419 / .418 | .498 | .486 | `AMBIGUOUS` |

The best-versus-second margin was **0.1969**, exceeding 0.10. No candidate was selected from an argmax alone. `candidate_phone_01` passed all frozen gates and its observations were merged into the existing `phone_01`; its candidate entity was removed from the post-Re-ID registry, while its source IDs remained provenance. The other candidates remained separate and did not update `phone_01` appearance memory. See [similarity matrix](task2/appearance_similarity.json), [audit and post-Re-ID registry](task2/reid_audit.json), and [contact sheet](task2/reid_contact_sheet.jpg).

**Evaluation-only reveal, after inference froze:** reviewed GT identifies `candidate_phone_01` as the original smartphone and `candidate_phone_02` / `candidate_phone_03` as distinct desk phones. The predicted match was correct in this case. The desk phones remained separate from `phone_01` and each other. See [Task2 review](task2/review.md).

## 9. Re-ID Audit

Four attempts: **1 MATCH, 3 AMBIGUOUS, 0 NEW_ENTITY, 0 REJECT**. Each attempt records query/candidate frame and time, gap, semantics, all prototype scores, temporal and coexistence evidence, graph context, hard contradictions, thresholds, margin, decision, and reason. `AMBIGUOUS` is retained where evidence is insufficient; it is not treated as a false match. The audited post-merge registry preserves `phone_01` across the gap.

## 10. Identity Safety

On the reviewed cases: **1 true Re-ID, 0 wrong-candidate matches, 0 false merges into `phone_01`, 0 unresolved original-phone duplicates after the one match, and no appearance-memory poisoning**. The two distinct desk phones were not merged. The principal critical error, `REID_FALSE_MATCH`, was absent; the conservative `REID_AMBIGUOUS` outcomes remain provisional. No semantic/coexistence contradiction was invented from stale memory; trusted distinct same-frame evidence vetoes identity when present. This is a case-level audit, not an estimated false-merge rate.

## 11. SAM Reinitialization

The safe `MATCH` authorized same-identity SAM reinitialization from the matched candidate; **SAM reinitialization was not executed**. `AMBIGUOUS`, `NEW_ENTITY`, and `REJECT` cannot authorize it. No extra SAM propagation was needed to answer the Re-ID question.

## 12. Limitations

This experiment contains one primary long-gap challenge and sparse, non-random reviewed GT. Viewpoint, scale, occlusion, lighting, and crop quality may change cosine scores. MobileNetV3 ImageNet features are lightweight general image features, not a phone-specific Re-ID model. Each late candidate contributed one first-frame view, while Task1's desk-phone control lacked a trusted SAM mask. Current graph context is weak image-plane neighborhood evidence with no world-fixed anchors, camera pose, or physical relations. Other videos and harder negatives require further evaluation before generalizing safety.

## 13. Result Classification

`SAFE_LONG_GAP_REID_SUCCESS` — the tested long-gap case was re-identified under these conditions without GT leakage or reviewed false merge. This does **not** mean long-gap Re-ID is solved generally.

## 14. Next Architecture Decision

`PROCEED_TO_SPATIAL_MEMORY_GRAPH` — appearance separated the original phone from both desk phones in this challenge, and the unique safe match was confirmed. Future spatial memory should be evaluated independently and should preserve the conservative identity gates.

## Verification

The 12 new focused tests and all existing regression tests passed: **90 passed**. The GT-isolation and manifest-lock checks passed after inference. All V2.4 results are confined to `outputs_v24/`; code is confined to `src/memory_graph/v24/`, `scripts/`, and `tests/` in `mixure_test_SAM`.

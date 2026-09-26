# V2.3 YOLO + SAM Persistent Entity Fusion Prototype

## 1. Question

Can frozen full-scene YOLO evidence and selected SAM 2.1 smartphone propagation update the same persistent physical-object hypotheses without using either model's local ID as physical identity?

## 2. Architecture

```text
frozen YOLO detections / V2.1 local tracks ──┐
                                              ├→ source-neutral observations
frozen V2.2 SAM 2.1 masks ────────────────────┘          ↓
                                               contradiction gates + fusion
                                                          ↓
                                                   EntityRegistry
                                                          ↓
                                               image-plane graph snapshots
```

The V2.1 resolver's conservative track groups are reused as scene priors. V2.3 decides new YOLO/SAM matches with same-frame semantic and spatial checks plus inherited SAM identity. It does not rerun YOLO, SAM, or Qwen VLM; new VLM calls: **0**. V2.1 and V2.2 files were read and hash-checked, not overwritten. The original `mixure_test` folder was not accessed.

## 3. Identity separation

The registry owns `phone_01` and other `entity_*` / provisional `candidate_phone_*` IDs. YOLO `track22` and `track43`, and SAM `phone_track22`, are separate source IDs supporting one registry entity. SAM target inheritance is a hypothesis and can be contradicted. Source-neutral observations carry frame/time, source ID, bbox, semantic label, optional detector confidence, optional mask reference, quality and provenance. SAM confidence remains null; mask RLE stays in the frozen V2.2 log.

## 4. Task1

YOLO track17 established `phone_01`; SAM `phone_track17` inherited it. Six reviewed visible frames had joint YOLO/SAM support. Six sampled frames accepted SAM-only continuation. After the mask became empty at frame420, `phone_01` remained in the registry as `UNOBSERVED`. The later desk-phone track70 mapped to `entity_0067`, not `phone_01`. There are 75 scene/target registry hypotheses; the frame240 snapshot has 35 nodes, including remembered unobserved scene objects. Reviewed phone duplicate count: **0**.

## 5. Task2

YOLO tracks22 and43 both mapped to `phone_01` via the inherited SAM object's same-frame evidence. Seven reviewed phone frames had joint YOLO/SAM support; two sampled frames accepted SAM-only continuation. At frame312, the SAM box overlapped a nearby raw phone YOLO box by about 0.227 IoU while its bbox area was over four times the YOLO box area. The fixed contradiction gate returned `CONFLICT`; the SAM hand mask was not entered into `phone_01` trusted history. The registry retained the phone hypothesis and then marked it `UNOBSERVED`.

At frame528, all three frozen YOLO phone boxes seeded three separate V2.2 SAM candidates. V2.3 kept `candidate_phone_01`, `_02`, and `_03` separate and marked association with old `phone_01` ambiguous across the long gap. Evaluation-only reviewed frames identify candidate 1 as the original phone: this leaves **one conservative duplicate physical-object hypothesis**. The two desk phones stayed distinct: YOLO tracks78/81 map to candidate 2, track80 to candidate 3. No GT selected a candidate during fusion.

## 6. Fusion audit

| Decision | Task1 | Task2 |
|---|---:|---:|
| MATCH | 597 | 827 |
| AMBIGUOUS | 2 | 5 |
| CONFLICT | 0 | 1 |
| NEW_ENTITY | 75 | 95 |

These counts include repeated observations and broad scene objects; they are audit events, not independent accuracy samples. Each important record stores source, IDs, candidate entity IDs, semantic/spatial/temporal evidence, optional appearance/context, contradiction and reason. [Task1 audit](task1/fusion_audit.json) · [Task2 audit](task2/fusion_audit.json).

## 7. Entity Registry

Entities retain `first_seen`, `last_seen`, `last_trusted_seen`, latest trusted observation, YOLO/SAM source lists, observation/association history, uncertainty and anchor-candidate metadata. `VISIBLE_TRUSTED` requires YOLO support; accepted SAM-only frames are `VISIBLE_PROPAGATED`. Uncertain or rejected SAM masks never update trusted appearance/history. No appearance embedding was used: the interface and empty memory are explicit, avoiding extra model dependencies. Anchor candidacy uses only semantic suitability and repeat YOLO observations; it makes no world-fixed claim. At representative snapshots, as many as 65 task1 and 72 task2 nodes remained remembered while unobserved.

## 8. Observation Graph

The [task1 snapshots](task1/graph_snapshots.json) and [task2 snapshots](task2/graph_snapshots.json) use PersistentEntity IDs as nodes. Edges are conservative `IMAGE_NEAR` co-visible image-plane observations. Isolated nodes remain valid. No edge is promoted to a physical relation. `get_entity_context(entity_id)` exposes nearby registry nodes and anchor-candidate metadata for a later experiment. [Task1 timeline](task1/entity_timeline.png) · [task2 timeline](task2/entity_timeline.png).

## 9. Failure analysis

- **Duplicate creation:** Task1 reviewed phone 0; task2 late original phone 1 provisional duplicate because long-gap re-identification was not forced.
- **False merge:** 0 on the six reviewed distinct-object pairs across both tasks. This does not prove a full-video false-merge rate.
- **Drift:** task2 frame312 was flagged `CONFLICT`; confirmed drift accepted into trusted `phone_01` history: **0**. This known V2.2 regression case informed the gate design, so it is not independent evidence of general drift detection.
- **Re-identification ambiguity:** candidate 1 cannot be linked to `phone_01` without a stronger inference-time identity signal. Class and raw overlap alone are insufficient.
- **YOLO miss:** trusted SAM-only observations preserve the phone entity; a miss never deletes a node.
- **SAM miss:** when the mask is absent or rejected, the entity remains `UNOBSERVED`/`CONFLICT` rather than receiving a fabricated current observation.

## 10. Conclusion

`FUSION_WORKS_BUT_REIDENTIFICATION_UNRESOLVED`. The prototype demonstrates one shared registry for scene-wide YOLO and selected SAM continuity, avoids reviewed false merges, and rejects the known hand drift. It does not yet resolve the late original phone candidate automatically.

## 11. Next architecture decision

`IMPROVE_REIDENTIFICATION_FIRST`. Add and validate a lightweight trusted appearance cue, plus a conservative long-gap candidate gate, before attaching late candidates to an existing physical entity or building persistent physical memory claims.

## 12. Remaining uncertainty

GT is sparse and deliberately selected. The fixed contradiction gate is a regression fix for a known case, and may miss other drift. V2.1 scene-track groups are inherited priors, not independently proven identities. No full-video identity purity, universal false-merge rate, world-fixed anchor position, or physical relation accuracy is claimed. All existing and new tests pass: **78 passed**.

# Human protocol decisions

PROTOCOL_NOT_READY_TO_FREEZE. No approval inferred. All recommendations are prospective.

| VERIFIED SETTING | RECOMMENDED SETTING | USER APPROVAL REQUIRED |
|---|---|---|
| Baseline: historical smoke health.model | Qwen/Qwen2.5-VL-7B-Instruct, NF4 double/BF16/SDPA; retain exact baseline | Approve NF4; do not substitute AWQ/3B |
| Revision: download_provenance.json revision cc594898… | Pin full cc594898137f460bfe9f0759e9844b3ce807cfb5 and local SHA manifest | Accept provenance limitation or require independent checksum evidence |
| V2 system: prepared V2 deployment.response_format_system | Exact saved system; parity repair to video adapter required | Approve new serialized prompt version after adapter parity |
| Multi-image smoke verified only 3×224² | UNIFORM_8 candidate, full frame, subject to capacity probe; 12/16 alternatives | Choose 8 (preferred exploratory compromise),12,16 or sparse3; no accuracy claim |
| Temporal tables measured in private/timing.json | Same GT-independent uniform-position policy for every window; fixedFPS4 alternate | Approve uniform8 or fixedFPS4; no event-centered offsets |
| Storyboard layout measured candidate manifests | 3 columns; 480×270 tiles +32 label; same selected frames/order | Approve geometry/resolution limitation or require new layout candidate |
| Video CPU trace14/8frames, grid52×92 actual937664pixel/frame | Full-frame FFV1 clip, processor4fps; resolve spatial cap and restrict citations to processed aliases | Approve encoding and separate video pixel budget after new offline/probe checks |
| Reference policy V2 §191: human access != model permission | Consistent neutral target scheme future task, or earliest static ref for5 + test1 separate | Choose neutral scheme / asymmetric static / NONE primary with ambiguity |
| NONE inputs built offline only | Do not add NONE ablation by default; doubles conditions with localization ambiguity | Include or omit distinct reference ablation (preferred omit initially) |
| Image receipt max_pixels200704 vs size config | Use measured effective grid-derived resized areas, explicitly reconcile size/max_pixels | Approve actual per-image effective cap after capacity proposal; no declared-only cap |
| Output smoke 179<512, EOS unrecorded | 1024 output tokens (proposal); multi-event schema not bounded by one no-event JSON | Approve1024 or justified larger budget;512 insufficiently established |
| Smoke load20.44s; generation49.34s, V1 deadlines80s | Load120s, generation300s, request330s prospective; matching probe required | Approve budgets after probe;180s not established for real shapes |
| Greedy used in code/runtime.py; seed42 manual | do_sample=false; temperature/top_p/top_k inactive, seed42 initialization only | Approve greedy; seed does not guarantee determinism |
| No pilot repeats verified | repeat1 main descriptive pilot; later deterministic stability separate | Choose1 (preferred) or2 stability repeats, not stochastic replication |
| Opaque IDs deterministic source_contract | Order sort sha256(PASS_T_PILOT_ORDER_V1/opaque/representation/refpolicy/repeat) | Approve locked order after refs/conditions selected; no adaptation |
| Exact native GT authority preserved; old0.2 only proposed | Fixed common0.2s tolerance candidate; timing sensitivity separate, not gap/2 | Explicitly approve0.2 or choose independent task tolerance; currently unresolved |
| Strict parser refuses Markdown; V1 failures retained | No JSON repair; retry0 generation; infrastructure-only retry1 pre-generation | Approve failure categories, raw output retention and no outcome-based retry |
| Historic process load peak6.74GiB; no global peak/RSS | Beforeload ≥10GiB freeGPU/8GiB freeRAM; stopglobal14.5GiB/RSS20GiB | Approve prospective measured gates after matching capacity probe |
| Eligibility private/eligibility.json:3neg2known1uncertain1excluded | Fixed six windows; test8 separate, test3 excluded; event-expected no independent-session claim | Approve exact cohort and restricted exploratory denominators |
| No capacity result for approved long shape | Separate synthetic matched-shape capacity probe before freeze | Authorize capacity task separately, or defer freeze (preferred probe) |
| Native PTS available; current aliases lack original timestamps | Candidate native-time map in instructions + storyboard neutral header | Approve timestamp formatting as additional model-visible serialization component |
| V2 policy formal eligibility0 / no exhaustive positive | Only known PICKUP matches / negative case alerts / uncertainty/schema/citation/runtime counts | Approve exploratory scope; formal metrics UNDEFINED |

## Dependencies

Frame count/layout affects resized tiles, visual tokens, capacity/timeouts and temporal resolution. Reference policy affects media budget, target interpretability, serialization and hashes. V2 formatting/video parity changes full prompt hash. Selected video FPS/size changes decoded-frame mapping and capacity. Run order depends on final conditions/reference/repeats. Matching tolerance is an independent scoring choice, never automatically sampling_gap/2. No dependent field is frozen.

Baseline evidence per-property source/file/field/verification/limitation is in private/baseline_audit.json and the final report. User must approve the complete revised package in a future task; no current approval string or frozen receipt exists.

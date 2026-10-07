# Pass I GPT-6.1 Sol DEV Pilot

## Current result

| Field | Value |
|---|---|
| Prompt version | pass_i_visual_annotator_v1 |
| Prompt SHA-256 | `b6057e19de893514fabba7842dbd3a91957fc17e7255c2e9bfb2a3b16dd7b53d` |
| Output schema | pass_i_visual_identity_v1 |
| CASE_CHANGE_POLICY | UNKNOWN |
| Model | gpt-6.1-sol |
| Model revision | Not exposed; no snapshot invented |
| DEV pilot pairs | 40 |
| Blind-first pairs | 6 (15%) |
| Requests attempted / completed | 40 / 40 |
| JSON valid / schema valid | 40 / 40 |
| PRELABEL_PARSE_FAILED | 0 |
| SAME / DIFFERENT / AMBIGUOUS | 3 / 8 / 29 |
| needs_human_review (UI priority only) | 31 |
| Frozen items sent | 0 |
| Gold frozen | NO |
| Human reviewed pilot items | 0 |
| Completed model wall time | 508.09 seconds |

Ready for complete human DEV review: **YES**.
Main blocker: None.

## Stage A and fixed inputs

Existing CandidateEpoch inventory, pair/split manifests and evidence packages were validated without rebuilding the dataset.
`reports/dev_pilot_stage_a.json` records the integrity checks; `reports/dev_pilot_tests.xml` records 25 tests, 0 failures and 0 errors.
Prompt extraction preserves the exact supplied text between BEGIN/END markers, removing only framing blank lines; no wording is edited.
Prompt, output schema and pilot manifest hashes are recorded in `manifests/dev_pilot_hashes.json`.
The original dataset manifest hashes, session split and V297/V2101 preservation baseline remain unchanged.
Actual sent-request/raw-response audit: `{"passed": 489, "failed": 0, "errors": [], "requests_audited": 40, "raw_responses_audited": 40, "frozen_requests": 0, "protected_files_verified": 4186, "token_usage": {"inputTokens": 533209, "outputTokens": 9054, "reasoningOutputTokens": 5156, "totalTokens": 542263}, "complete": true}`

## Selection

Fixed seed: 297102; target count: 40. Select from the existing DEV partition only.
Deterministic round-robin over available sampling strata, recordings and image-count diversity; no GPT output or expected correctness participates in selection.
Recording counts: `{"test4": 11, "test7": 6, "test8": 4, "val_5": 6, "val_6": 5, "val_7": 8}`.
Overlapping sampling counts: `{"long_gap_pairs": 29, "blur_low_quality_pairs": 10, "near_identical_phone_pairs": 6, "same_object_candidate_pairs": 6, "reappearance_cases": 3, "different_object_candidate_pairs": 3}`. These attributes are not labels and never enter model inputs.
Blind-first subset: deterministic seeded 15% sample of this fixed pilot, independent of predictions.

## Model input and execution boundary

Transport uses the authenticated local Codex app-server and explicitly requests `gpt-6.1-sol`, with a fresh ephemeral thread per pair and the exact saved prompt as `baseInstructions`.
High reasoning effort is fixed. No output-schema forcing or JSON repair is used; the prompt itself requests JSON.
The turn input is built from the same whitelisted adapter as the UI: item ID, UNKNOWN case policy, numbered Q/R crop/context labels and original image data URIs.
No timestamps, tracking, scores, aliases, epoch creation reasons, pair strata, IdentityGuard decisions, physical GT or video enter the turn input.
The configuration disables browser, shell, apps, view-image tools and multi-agent and requests that host skill discovery be skipped; any tool attempt is rejected and the pilot turn is interrupted.
The isolated workspace contains no source metadata, inventories or videos. No API key is copied or exported.
The CLI transport still supplies its generic runtime/sandbox context; this is recorded as transport context, not experimental evidence.
Official source: [GPT-6.1 Sol model](https://developers.openai.com/api/docs/models/gpt-6.1-sol).

## Raw-first output and strict validation

Each complete raw response is persisted in an exclusive `<item>.raw.json` and raw JSONL before annotation parsing.
Strict `json.loads` plus output consistency checks validate label, ambiguity cause, challenge tags, item identity, evidence indices and evidence/label relationships.
Invalid JSON, extra fields or schema failures remain `PRELABEL_PARSE_FAILED`; no fence stripping, relabeling or guessed evidence is performed.
Derived review priority is stored outside the model's annotation object:

```python
needs_human_review = (
    label == 'AMBIGUOUS'
    or confidence != 'high'
    or (len(evidence_for_same) > 0 and len(evidence_for_different) > 0)
)
```

All final items still require human review regardless of this flag.

## Human workflow

Open `http://127.0.0.1:8511`, choose **DEV pilot**. Default mode is Review; priority sorting is optional.
For the six blind-first items, GPT label/evidence/confidence and Accept GPT remain hidden until the human saves a blind visual label, then explicitly chooses **Reveal GPT prelabel**.
The original blind judgment is retained separately even after accepting/overriding GPT. Exclusion requires a reason; ambiguity requires one cause; challenge tags remain editable.
Pilot annotation storage is isolated under `annotations/dev_pilot/`; original full-dataset annotations are not overwritten.
Physical GT remains separate and cannot enter model inputs. No Cohen's kappa, accuracy, false-merge/false-split rate or other-model benchmark is calculated.

## Artifacts

- `prompts/pass_i_prelabel_prompt.txt`, `prompt_manifest.json`, `output_schema.json`
- `manifests/dev_pilot_manifest.json`, `dev_pilot_hashes.json`
- `prelabels/dev_pilot/dev_pilot_raw_responses.jsonl`
- `prelabels/dev_pilot/dev_pilot_prelabels.jsonl`
- `prelabels/dev_pilot/dev_pilot_runtime.json`
- `prelabels/dev_pilot/PI_*.raw.json`, `PI_*.json`, sanitized request audits and transport logs once inference runs
- `annotations/dev_pilot/annotations/{annotations.sqlite3,human_annotations.jsonl,physical_gt.jsonl,excluded_items.jsonl,annotation_progress.json}`
- `reports/dev_pilot_stage_a.json`, `dev_pilot_tests.xml`, `dev_pilot_summary.json`, `PASS_I_DEV_PILOT_REPORT.md`

## Human inspection priorities

Inspect whether SAME evidence is instance-specific, DIFFERENT evidence excludes viewpoint/lighting/case-change explanations, ambiguity causes match the actual limitation, tags are visually supported and crops permit corresponding-region inspection.
Example draft item IDs by label: `{"SAME": ["PI_000425", "PI_000426", "PI_000747"], "DIFFERENT": ["PI_000456", "PI_000751", "PI_000756", "PI_000889", "PI_000958"], "AMBIGUOUS": ["PI_000361", "PI_000365", "PI_000424", "PI_000439", "PI_000440"]}`. These are review entry points, not accepted identity labels.
AMBIGUOUS cause distribution: `{"LOW_QUALITY": 21, "VIEW_MISMATCH": 6, "NO_DISCRIMINATIVE_FEATURE": 2}`. Challenge-tag distribution: `{"poor_image_quality": 30, "partial_occlusion": 23, "front_vs_back": 9, "large_viewpoint_change": 5, "none": 1, "motion_blur": 7, "distractor_present": 20, "near_identical_appearance": 12}`. These are model output counts, not accuracy metrics.
Any future prompt revision must receive a new version/hash and be evaluated on DEV. Frozen inference and formal gold freezing are not authorized at this stage.

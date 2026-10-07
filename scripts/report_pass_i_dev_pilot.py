"""Report actual pilot completions only; never compare with identity GT."""
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from memory_graph.pass_i.common import OUT, read, write, read_lines, sha
from memory_graph.pass_i.pilot import verify_pilot, PILOT_OUT, PILOT_ANNOTATIONS
from memory_graph.pass_i.annotations import AnnotationStore


def main():
    manifest = verify_pilot()
    prompt = read(OUT / 'prompts/prompt_manifest.json')
    records = read_lines(PILOT_OUT / 'dev_pilot_prelabels.jsonl')
    raw_records = read_lines(PILOT_OUT / 'dev_pilot_raw_responses.jsonl')
    labels = Counter(r['parsed']['label'] for r in records if r['schema_valid'])
    causes = Counter(r['parsed']['ambiguity_cause'] for r in records if r['schema_valid'] and r['parsed']['label'] == 'AMBIGUOUS')
    tags = Counter(t for r in records if r['schema_valid'] for t in r['parsed']['challenge_tags'])
    pilot_store = AnnotationStore(PILOT_ANNOTATIONS, prelabels_out=PILOT_OUT)
    pilot_store.export(len(manifest['items']))
    stats = {'prompt_sha256': prompt['prompt_sha256'], 'schema_version': prompt['output_schema_version'],
        'CASE_CHANGE_POLICY': prompt['CASE_CHANGE_POLICY'], 'model': prompt['model_name'], 'model_revision': prompt['model_revision'],
        'dev_pilot_pairs': len(manifest['items']), 'blind_first_pairs': manifest['blind_first_count'],
        'requests_attempted': len(list((PILOT_OUT / 'requests').glob('PI_*.json'))),
        'requests_completed': sum(r['runtime'].get('turn_status') == 'completed' for r in raw_records),
        'json_valid': sum(r['json_valid'] for r in records), 'schema_valid': sum(r['schema_valid'] for r in records),
        'parse_failures': sum(r['status'] == 'PRELABEL_PARSE_FAILED' for r in records),
        'labels': {k: labels[k] for k in ['SAME', 'DIFFERENT', 'AMBIGUOUS']},
        'ambiguity_causes': dict(causes), 'challenge_tags': dict(tags),
        'needs_human_review': sum(r['needs_human_review'] for r in records),
        'streamlit_pilot_review_ready': True, 'frozen_items_sent_to_gpt': 0,
        'total_model_wall_seconds': sum(r['runtime']['wall_seconds'] for r in raw_records),
        'all_pilot_requests_finished': len(raw_records) == len(manifest['items']),
        'human_reviewed': len(pilot_store.gold()),
        'gold_frozen': False}
    runtime_file = PILOT_OUT / 'dev_pilot_runtime.json'
    existing = read(runtime_file) if runtime_file.exists() else {}
    write(runtime_file, {**existing, **stats})
    write(OUT / 'reports/dev_pilot_summary.json', stats)
    tree = ET.parse(OUT / 'reports/dev_pilot_tests.xml').getroot().find('testsuite')
    tests = tree.attrib
    gate = OUT / 'reports/dev_pilot_approval_gate.json'
    blocker = read(gate)['message'] if gate.exists() and not raw_records else 'None.' if stats['all_pilot_requests_finished'] else 'Inference not yet complete.'
    coverage = Counter(c for p in manifest['items'] for c in p['sampling_attributes'])
    videos = Counter(p['video_id'] for p in manifest['items'])
    examples = {label: [r['item_id'] for r in records if r['schema_valid'] and r['parsed']['label'] == label][:5] for label in ['SAME', 'DIFFERENT', 'AMBIGUOUS']}
    final_audit = read(OUT / 'reports/dev_pilot_final_audit.json') if (OUT / 'reports/dev_pilot_final_audit.json').exists() else None
    lines = f'''# Pass I GPT-6.1 Sol DEV Pilot

## Current result

| Field | Value |
|---|---|
| Prompt version | {prompt['prompt_version']} |
| Prompt SHA-256 | `{stats['prompt_sha256']}` |
| Output schema | {stats['schema_version']} |
| CASE_CHANGE_POLICY | {stats['CASE_CHANGE_POLICY']} |
| Model | {stats['model']} |
| Model revision | Not exposed; no snapshot invented |
| DEV pilot pairs | {stats['dev_pilot_pairs']} |
| Blind-first pairs | {stats['blind_first_pairs']} (15%) |
| Requests attempted / completed | {stats['requests_attempted']} / {stats['requests_completed']} |
| JSON valid / schema valid | {stats['json_valid']} / {stats['schema_valid']} |
| PRELABEL_PARSE_FAILED | {stats['parse_failures']} |
| SAME / DIFFERENT / AMBIGUOUS | {labels['SAME']} / {labels['DIFFERENT']} / {labels['AMBIGUOUS']} |
| needs_human_review (UI priority only) | {stats['needs_human_review']} |
| Frozen items sent | 0 |
| Gold frozen | NO |
| Human reviewed pilot items | {stats['human_reviewed']} |
| Completed model wall time | {stats['total_model_wall_seconds']:.2f} seconds |

Ready for complete human DEV review: **{'YES' if stats['all_pilot_requests_finished'] else 'NO'}**.
Main blocker: {blocker}

## Stage A and fixed inputs

Existing CandidateEpoch inventory, pair/split manifests and evidence packages were validated without rebuilding the dataset.
`reports/dev_pilot_stage_a.json` records the integrity checks; `reports/dev_pilot_tests.xml` records {tests['tests']} tests, {tests['failures']} failures and {tests['errors']} errors.
Prompt extraction preserves the exact supplied text between BEGIN/END markers, removing only framing blank lines; no wording is edited.
Prompt, output schema and pilot manifest hashes are recorded in `manifests/dev_pilot_hashes.json`.
The original dataset manifest hashes, session split and V297/V2101 preservation baseline remain unchanged.
Actual sent-request/raw-response audit: `{json.dumps(final_audit, ensure_ascii=False) if final_audit else 'Pending final audit.'}`

## Selection

Fixed seed: {manifest['seed']}; target count: 40. Select from the existing DEV partition only.
Deterministic round-robin over available sampling strata, recordings and image-count diversity; no GPT output or expected correctness participates in selection.
Recording counts: `{json.dumps(dict(videos))}`.
Overlapping sampling counts: `{json.dumps(dict(coverage))}`. These attributes are not labels and never enter model inputs.
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
- `annotations/dev_pilot/annotations/{{annotations.sqlite3,human_annotations.jsonl,physical_gt.jsonl,excluded_items.jsonl,annotation_progress.json}}`
- `reports/dev_pilot_stage_a.json`, `dev_pilot_tests.xml`, `dev_pilot_summary.json`, `PASS_I_DEV_PILOT_REPORT.md`

## Human inspection priorities

Inspect whether SAME evidence is instance-specific, DIFFERENT evidence excludes viewpoint/lighting/case-change explanations, ambiguity causes match the actual limitation, tags are visually supported and crops permit corresponding-region inspection.
Example draft item IDs by label: `{json.dumps(examples)}`. These are review entry points, not accepted identity labels.
AMBIGUOUS cause distribution: `{json.dumps(dict(causes))}`. Challenge-tag distribution: `{json.dumps(dict(tags))}`. These are model output counts, not accuracy metrics.
Any future prompt revision must receive a new version/hash and be evaluated on DEV. Frozen inference and formal gold freezing are not authorized at this stage.
'''
    (OUT / 'reports/PASS_I_DEV_PILOT_REPORT.md').write_text(lines, encoding='utf-8')
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()

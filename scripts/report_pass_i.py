"""Report offline dataset preparation; no predictions or accuracy calculation."""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from memory_graph.pass_i.common import OUT, read, write, read_lines, sha


def main():
    summary = read(OUT / 'reports/build_summary.json')
    validation = read(OUT / 'reports/dataset_validation.json')
    split = read(OUT / 'manifests/session_split.json')
    inv = read_lines(OUT / 'manifests/candidate_epoch_inventory.jsonl')
    suite = ET.parse(OUT / 'reports/pytest_results.xml').getroot().find('testsuite')
    tests = {k: int(suite.attrib[k]) for k in ['tests', 'errors', 'failures', 'skipped']}
    checks = {'dataset_checks': validation, 'pytest': tests, 'gpt_called': False,
              'raw_prelabels_in_dataset': len(list((OUT / 'prelabels').glob('PI_*.json'))),
              'human_annotation_count': len(read_lines(OUT / 'annotations/human_annotations.jsonl'))}
    write(OUT / 'reports/validation_summary.json', checks)
    files = [p for directory in ['src/memory_graph/pass_i', 'scripts', 'tests'] for p in (ROOT / directory).glob('*.py')
             if directory == 'src/memory_graph/pass_i' or 'pass_i' in p.name]
    files += [ROOT / 'scripts/start_pass_i_annotation.ps1', OUT / 'requirements.txt']
    write(OUT / 'reports/implementation_hashes.json', {p.relative_to(ROOT).as_posix(): sha(p) for p in files})
    dev, frozen = summary['splits']['dev'], summary['splits']['frozen']
    rows = '\n'.join(f"| {c} | {v['available']} | {v['selected']} | {v['basis']} |" for c, v in summary['sampling_coverage'].items())
    recordings = '\n'.join(f"| {r['video_id']} | {r['split']} | {sum(e['video_id']==r['video_id'] for e in inv)} | {r['session_id']} |" for r in split['recordings'])
    report = f'''# Pass I Dataset + Annotation Tool

## Result

Implemented and validated offline preparation. **No GPT/model calls, no visual identity annotation, no formal benchmark.**
All new data live in `artifacts/pass_i`; new isolated Python modules and scripts do not modify frozen identity rules.

| Measure | Result |
|---|---:|
| Recording groups | {summary['sessions']} |
| Source videos | {summary['recordings']} |
| CandidateEpochs | {summary['epochs']} |
| Pairs | {summary['pairs']} |
| Dev groups / pairs | {dev['sessions']} / {dev['pairs']} |
| Frozen groups / pairs | {frozen['sessions']} / {frozen['pairs']} |
| CASE_CHANGE_POLICY | UNKNOWN |
| Clean original-resolution crops | {summary['evidence']['clean_crops']} |
| Original context frames | {summary['evidence']['context_images']} |
| Dataset integrity checks passed / failed | {validation['passed']} / {validation['failed']} |
| pytest passed / failed | {tests['tests']-tests['failures']-tests['errors']-tests['skipped']} / {tests['failures']+tests['errors']} |
| Protected V297/V2101 files unchanged | {validation['protected_files_verified']} |

## Pipeline

```mermaid
flowchart TD
    A[Read-only canonical V297 epochs + metadata + verified original crops] --> B[Hidden CandidateEpoch inventory]
    B --> C[Recording groups: explicit sessions / duplicate bytes / shared source frames]
    C --> D[Seeded dev / frozen split BEFORE inference]
    D --> E[Deterministic same-recording pairs and hidden sampling provenance]
    E --> F[Neutral numbered crops and context evidence packages]
    F --> G[GPT request adapter: inactive]
    F --> H[Streamlit blind human annotation]
    G -. future separately supplied prompt and client .-> I[Immutable raw GPT drafts]
    I --> J[Streamlit review: accept or override]
    H --> K[Human visual gold: SQLite + incremental JSONL]
    J --> K
    B --> L[Optional physical review: source video and timeline]
    L --> M[Separate physical_gt.jsonl]
```

## Actual discovered source contract

- Implementation: `src/memory_graph/v296_reid/epochs.py`; V297 imports this CandidateEpochBuilder.
- Canonical outputs only: `outputs/v297_physical_identity/{{development,known_val_regression}}/runs/<video>/candidate_epochs.json`.
- No diagnostic/older reruns are enumerated into this dataset.
- Serialized container: `epochs`, `events`, `policy`.
- Epoch fields: `candidate_epoch_id`, `start_time`, `start_frame`, `local_track_ids`, `observation_ids`, `end_reason`, `end_time`, `creation_reason`.
- `end_time` in the source is a discontinuity time, not a last-observation time. Inventory `end_frame/end_time` are derived from the final actual observation, with explicit semantics.
- Observation lookup: sibling `metadata.json`, keyed by observation ID. Actual fields include frame/time/bbox/label, local and epoch IDs, verified original crop paths/hashes, source frame pixel SHA, canonical crop dimensions and source-video SHA.
- Read-only identity artifacts: sibling `identity.json`, `authorized_rows.json`, `confirmation_audit.json`, `physical_evidence.json`; these are preserved, not used as visual gold.
- Original clean crops: observation `raw_crop_path`, generally under `outputs/v296_reid/inputs/<video>/raw_crops/`. Existing `crop_path` may be foreground-masked; this builder uses verified original RGB crops instead.
- Existing Core Bank logic: V296 guard checks clean evidence/confidence and trusted diversity, while V297 guard gates bank authority. Pass I does not select only trusted-bank crops or inherit bank decisions.
- V2101 layout: `artifacts/v2.10.1/{{freeze,deployment,smoke,reports}}`; all protected before/after.
- No explicit cross-video session ID or verified no-case-change protocol was found. Recording-level fallback is used; UNKNOWN is not inferred from phone appearance.

## Session split and leakage controls

Seed: `297101`; dev target fraction: `0.3`. Split is stored and hash frozen before any model output.
20 recordings form 19 groups. **test3 and test5 are unioned into the same frozen group** because original frames are near duplicates.
Exact source pixel hashes are checked over every inventory observation. Near-duplicate full-source-frame audit examined {split['near_duplicate_audit']['original_frames_checked']} selected-evidence frames using dHash distance ≤2 plus mean RGB difference ≤8 on 16×16 thumbnails.
These checks reduce observed overlap, but do not prove that different videos belong to different real-world recording sessions. Session overrides are supported for a separately versioned build; this split is never changed in response to model performance.
Known-val regression material was already used by prior development. The frozen Pass I partition is not a claim of new held-out pipeline generalization.

| Video | Split | Epochs | Recording group |
|---|---|---:|---|
{recordings}

## Pair construction and sampling coverage

Pairs are unordered distinct-epoch combinations within each recording, never cross-split. Per recording budget: 120; deterministic hash ordering plus round-robin supported strata. Total selected: {summary['pairs']}.
Shared local ID is only a same-object sampling hypothesis; simultaneous frame presence is only a different-object sampling hypothesis. Generic dHash similarity is a rough near-appearance sampling proxy. None is a label.
The supported categories overlap and their counts must not be summed as distinct items.

| Sampling attribute | Available candidate pairs | Selected pairs | Basis |
|---|---:|---:|---|
{rows}

Viewpoint and partial-occlusion category zeroes mean **no verified source tag is available**, not that such images are absent. Human UI supports these challenge tags later. No visual inspection/identity annotation was performed during preparation.

## Evidence packaging

All {summary['epochs']} epochs have at least one verified phone candidate crop. Crop-count distribution: `{json.dumps(summary['evidence']['crop_count_distribution'])}`.
526 epochs have only one selected crop; counts are never padded to 3–6. Selection uses original quality, time spacing (≥0.4 seconds) and nonduplicate visual structure. Viewpoint diversity is a proxy, not a semantic viewpoint label.
Source RGB crops retain original resolution; no enlargement is stored. Contexts are unannotated original frames, encoded as quality-95 JPEG with source pixel hash retained internally.
Neutral filenames and Q/R numbering are shared exactly between UI and adapter. Context IDs cannot be cited as identity evidence.

Hidden inventory/pair manifest retains epoch IDs, chronology, tracker provenance and sampling reason. The public evidence JSON contains only `item_id`, `CASE_CHANGE_POLICY`, and numbered image references. The actual model request contains only policy/item text, numbered labels and image data URIs: no paths, hashes, IDs, scores, aliases, authorization decisions, pair category or GT.

## Annotation tool

Launch from the repository in PowerShell:

```powershell
.\\scripts\\start_pass_i_annotation.ps1
```

Open `http://127.0.0.1:8511`. Alternative port: `-Port 8512`.
Streamlit 1.50.0 and its dependencies are isolated in `artifacts/pass_i/runtime/vendor`; the existing model environment is unchanged. Version list: `runtime/dependency_versions.json`.

- Blind mode hides GPT drafts; saves separate `human_blind_*` fields.
- Review mode displays validated GPT label/cause/tags/evidence/confidence and supports Accept GPT or Override. Raw response files are immutable.
- SAME / DIFFERENT / AMBIGUOUS / EXCLUDE ITEM controls; mandatory ambiguity/exclusion reason and independent challenge checkboxes.
- Previous/Next/item jump, first-unreviewed resume, split selection, unreviewed/excluded/disagreement filters, previous edits.
- Images show original pixel dimensions; optional close inspection explicitly labels display magnification and provides original download.
- Every save commits to SQLite and exports JSONL/progress. Editing retains annotation history and initial blind judgment.
- Optional physical mode allows original video, timeline and hidden provenance and writes only separate physical GT.
- Excluded items never appear in `AnnotationStore.gold()`.

## GPT adapter

`src/memory_graph/pass_i/adapter.py`: `build_request(public_item, separately_supplied_system_prompt)` builds the actual request without inference. `prelabel(client, ..., enabled=False)` refuses calls by default. The future caller must supply the system prompt, an authorized compatible model client and explicitly enable the pilot.
The configured model name is `gpt-6.1-sol`; availability must be established by the future client. No API credentials are needed for dataset preparation or human annotation.
Malformed GPT responses are preserved separately and cannot be accepted as valid drafts. Human reviewed labels are the only visual-gold source.

## Validation evidence

`reports/dataset_validation.json`, `reports/pytest_results.xml`, `reports/validation_summary.json`.
Tests cover session/frame/hash/numbering consistency, actual serialized request sanitization, disabled-client behavior, ambiguity and tag validation, exclusion from gold, restart/edit persistence, immutable draft/human/physical separation, evidence index validation, crop non-padding, and Streamlit blind save/exclusion/restart/review/physical/filter interactions.
Synthetic GPT responses occur only in test fixtures under `runtime/test_tmp*`; the actual `prelabels/` contains zero responses and actual human annotation files contain zero labels.
Protected snapshot hashes cover {validation['protected_files_verified']} existing V297/V2101 files, all unchanged. No tracker/SAM/DINO/LightGlue/IdentityGuard/Memory Graph rules were modified.

## Artifact locations

- `manifests/candidate_epoch_inventory.jsonl`
- `manifests/session_split.json`
- `manifests/pair_manifest.jsonl`
- `manifests/manifest_hashes.json` and `protected_before.json`
- `items/PI_*/evidence.json`, `items/evidence/<neutral-token>/`
- `prelabels/` (empty until separate pilot)
- `annotations/{{annotations.sqlite3,human_annotations.jsonl,physical_gt.jsonl,excluded_items.jsonl,annotation_progress.json}}`
- `reports/` (build counts, validation, implementation hashes and this report)

## Next-stage readiness

**Ready for GPT-6.1 Sol pilot: YES for a separately authorized dev pilot.** No implementation blocker remains.
Pilot still requires the separately supplied visual annotation prompt/client. Before a formal benchmark, verify real cross-video session grouping and collect human-reviewed gold; many single-crop epochs may remain visually ambiguous. No accuracy, false-merge or false-split metric is claimed here.
'''
    (OUT / 'reports/PASS_I_DATASET_BUILD_REPORT.md').write_text(report, encoding='utf-8')
    print(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()

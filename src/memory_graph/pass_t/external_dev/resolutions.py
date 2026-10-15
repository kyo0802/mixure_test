"""Downstream human clarifications; never rewrite immutable imported records."""
from pathlib import Path
from .audit import dataset_view, summarize, RECONCILE
from .security import Blocked, digest, strict_json, safe_path


def current_dataset_view(records, repository_root=None):
    data = dataset_view(records)
    if repository_root is None:
        return data
    root = Path(repository_root)
    registry = root / 'artifacts/pass_t/phase2a/v2/review_resolutions/identity_v1.json'
    if not registry.exists():
        return data
    raw = registry.read_bytes()
    resolution = strict_json(raw)
    if resolution.get('schema_version') != 'PASS_T_REVIEWER_IDENTITY_RESOLUTION_V1':
        raise Blocked('UNSUPPORTED_IDENTITY_RESOLUTION')
    note_path = safe_path(root, resolution['source_note_path'])
    note_raw = note_path.read_bytes()
    if digest(note_raw) != resolution['source_note_sha256']:
        raise Blocked('IDENTITY_CLARIFICATION_HASH_MISMATCH')
    note = strict_json(note_raw)
    aliases = resolution['reviewer_ids']
    if (not isinstance(aliases, list) or len(aliases) < 2 or
            any(not isinstance(a, str) or not a for a in aliases) or len(set(aliases)) != len(aliases)
            or note.get('reviewer_ids') != aliases or note.get('same_person_confirmed_by_owner') is not True
            or note.get('record_type') != 'PROJECT_OWNER_CLARIFICATION_NOT_ANNOTATION_SUBMISSION'):
        raise Blocked('IDENTITY_CLARIFICATION_NOT_CONFIRMED')
    linkage = {'registry_sha256': digest(raw), 'source_note_sha256': digest(note_raw),
               'source_note_path': resolution['source_note_path'], 'reviewer_ids_preserved': aliases}
    for record in data['records']:
        if record['archive_sha256'] != resolution['archive_sha256'] or record['reviewer_id'] not in aliases:
            continue
        if RECONCILE not in record['human_review_flags']:
            continue
        record['import_time_human_review_flags'] = list(record['human_review_flags'])
        record['human_review_flags'] = [f for f in record['human_review_flags'] if f != RECONCILE]
        record['human_review_pending'] = bool(record['human_review_flags'])
        record['reviewer_identity_resolution'] = linkage
        # Same gate as the original importer. It is not a visual-quality attestation.
        record['quality_cleared_for_model_scoring'] = bool(
            record['evaluation']['full_window_event_evaluation_supported'] and not record['human_review_pending'])
        record['exploratory_positive_quality_cleared'] = bool(
            record['evaluation']['supported_event_exploratory_use_allowed'] and not record['human_review_pending'])
        record['quality_gate_basis'] = 'ORIGINAL_V2_ELIGIBILITY_AND_NO_UNRESOLVED_IMPORT_FLAGS; NOT_INDEPENDENT_VISUAL_REVIEW'
        record['independent_visual_quality_review'] = 'NOT_ESTABLISHED_BY_IDENTITY_RESOLUTION'
    data['review_resolution_provenance'] = linkage
    data['summary'] = summarize(data['records'])
    data['views']['pending_manual_review'] = [r['record_id'] for r in data['records'] if r['human_review_pending']]
    return data

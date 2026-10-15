"""Deterministic provenance resolver. No geometry-based cross-track identity."""
from copy import deepcopy

FIELDS = ('observation_id', 'frame_index', 'timestamp', 'source_track_id', 'candidate_id',
          'candidate_epoch_id', 'bbox', 'source_path', 'semantic_class')


def cutoff_records(records, end):
    """Expose only observed fields strictly before the authorized end, never annotations."""
    return [{k: deepcopy(row[k]) for k in FIELDS if k in row}
            for row in records if row['timestamp'] < end]


def resolve_window(window, binding, inventory):
    if any('diagnostic_only' in value for value in (window, binding, inventory)):
        raise ValueError('Private diagnostic records are forbidden resolver inputs')
    start, end = window['window_start_s'], window['window_end_s']
    records = inventory['records']
    if any(row['timestamp'] >= end for row in records):
        raise ValueError('Causal interface contains future observations')
    inside = [row for row in records if start <= row['timestamp'] < end and
              row.get('semantic_class') == 'cell phone']
    tracks = sorted({str(x['source_track_id']) for x in inside if x.get('source_track_id') is not None})
    seed = binding.get('source_track_id')
    seed = str(seed) if seed is not None else None
    valid_binding = (seed is not None and seed != 'phone_01' and
                     binding.get('timestamp', float('inf')) < end and
                     binding.get('binding_causality_status') != 'NON_CAUSAL')
    supported = [x for x in inside if str(x.get('source_track_id')) == seed] if valid_binding else []
    conflicts = []
    by_frame = {}
    for row in supported:
        by_frame.setdefault(row['frame_index'], set()).add(tuple(row.get('bbox') or []))
    if any(len(boxes) > 1 for boxes in by_frame.values()):
        conflicts.append('CONFLICTING_EXACT_OBSERVATIONS')
    if binding.get('conflicting_local_bindings'):
        conflicts.append('CONFLICTING_EXPLICIT_BINDINGS')
    if not inventory.get('coverage_validated'):
        status, reason = 'NEEDS_HUMAN_SEED', 'SOURCE_INVENTORY_UNVALIDATED_OR_MISSING'
    elif supported and not conflicts:
        status, reason = 'RESOLVED_UNIQUE', 'EXPLICIT_BOUND_SAME_LOCAL_TRACK_OBSERVED_IN_WINDOW'
    elif conflicts or len(tracks) > 1:
        status, reason = 'AMBIGUOUS', 'LOCAL_CANDIDATES_WITHOUT_UNIQUE_POSITIVE_LINK'
    elif not inside:
        status, reason = 'NO_CANDIDATE', 'NO_QUALIFYING_RECORDS_IN_VALIDATED_INVENTORY'
    else:
        status, reason = 'NEEDS_HUMAN_SEED', 'NO_POSITIVE_SOURCE_LINK_TO_BOUND_TARGET'
    resolved = status == 'RESOLVED_UNIQUE'
    epochs = {x.get('candidate_epoch_id') for x in supported if x.get('candidate_epoch_id')}
    evidence = sorted({x['frame_index'] for x in supported}) if resolved else []
    available = []
    keys = sorted({(str(x.get('source_track_id')), str(x.get('candidate_id'))) for x in inside})
    for track, candidate in keys:
        rows = [x for x in inside if (str(x.get('source_track_id')), str(x.get('candidate_id')))==(track,candidate)]
        available.append({'local_track_id': None if track=='None' else track,
                          'candidate_id': None if candidate=='None' else candidate,
                          'frames': sorted({x['frame_index'] for x in rows}),
                          'observation_ids': [x['observation_id'] for x in rows],
                          'linkage_status': 'RECORDED_SOURCE_TRACK' if track!='None' else 'NO_SOURCE_TRACK_LINK'})
    return {**window, 'resolution_status': status, 'resolved_local_track_id': seed if resolved else None,
            'resolved_candidate_epoch_id': next(iter(epochs)) if resolved and len(epochs) == 1 else None,
            'method': 'EXPLICIT_SOURCE_TRACK_PROVENANCE_ONLY',
            'evidence_source_paths': inventory.get('source_paths', []),
            'evidence_frame_range': [min(evidence), max(evidence)] if evidence else None,
            'supporting_observation_ids': [x['observation_id'] for x in supported] if resolved else [],
            'used_pre_window_metadata': bool(valid_binding and binding.get('timestamp', end) < start),
            'used_in_window_metadata': bool(inside), 'used_post_window_metadata_for_binding': False,
            'competing_candidates': [t for t in tracks if t != seed], 'conflicts': conflicts,
            'reason_codes': [reason], 'binding_causality_status': binding.get('binding_causality_status', 'CAUSALITY_UNVERIFIED'),
            'exact_observations': [{k: x[k] for k in ('frame_index','timestamp','bbox','observation_id') if k in x}
                                   for x in supported] if resolved else [],
            'available_candidates': available}


PILOT_RESTRICTION = {'evaluation_eligible': False, 'purpose': 'INPUT_INTEGRITY_SMOKE_ONLY',
                     'status': 'NOT_FOR_EVALUATION'}


def stage0_gate(mappings, pilot_partial=False):
    blocked = [m['pack_id'] for m in mappings if m['resolution_status'] != 'RESOLVED_UNIQUE' or
               not m.get('clean_source_hash_verified')]
    strict_pass = len(mappings) == 9 and len(blocked) < 5
    eligible = [m['pack_id'] for m in mappings if m['resolution_status'] == 'RESOLVED_UNIQUE' and
                m.get('clean_source_hash_verified')] if pilot_partial or strict_pass else []
    return {**PILOT_RESTRICTION, 'mode': 'PILOT_PARTIAL' if pilot_partial else 'STRICT_DEFAULT',
            'legacy_stage0_gate_pass': strict_pass, 'aggregate_target_readiness': not blocked,
            'formal_evaluation_ready': False, 'eligible_packs': eligible, 'blocked_packs': blocked}

"""Raw-preserving staged strict validation and explicitly gated event matching."""
from __future__ import annotations
import json
from pathlib import Path
from .common import Phase2BBlocked, digest, pretty_bytes
from .predictions import parse_raw, validate_prediction
from .evaluation import evaluate_item, CLOSED_INTERVAL_MATCHER

STAGES = ('JSON_SYNTAX','SCHEMA','SEMANTIC','CITATION','FULL_STRICT')

def classify_output(raw: bytes | None, supplied_aliases: list[str]):
    stages={k:'NOT_ASSESSED' for k in STAGES}
    base={'raw_sha256':digest(raw) if raw is not None else None,'raw_bytes':len(raw) if raw is not None else None,
          'stages':stages,'prediction':None,'authoritative_prediction':None,'qualitative_review':{'status':'UNREVIEWED','authoritative_structured_prediction':False}}
    if raw is None:
        return {**base,'classification':'ABSENT_PREDICTION','failure':'No model output available'}
    try:
        prediction=parse_raw(raw)
    except Phase2BBlocked as error:
        stages['JSON_SYNTAX']='FAIL';stages['FULL_STRICT']='FAIL'
        return {**base,'classification':'INVALID_JSON','failure':str(error)}
    stages['JSON_SYNTAX']='PASS'
    result=validate_prediction(prediction,supplied_aliases)
    base['prediction']=prediction; base['validation']=result
    stages['SCHEMA']='FAIL' if result['structural_errors'] else 'PASS'
    if result['structural_errors']:
        stages['SEMANTIC']=stages['CITATION']='NOT_ASSESSED_DUE_TO_SCHEMA_FAILURE'
    else:
        stages['SEMANTIC']='FAIL' if result['semantic_errors'] else 'PASS'
        stages['CITATION']='FAIL' if result['citation_errors'] else 'PASS'
    stages['FULL_STRICT']='PASS' if result['valid'] else 'FAIL'
    if not result['valid']:
        return {**base,'classification':'STRICT_INVALID','matching_status':'UNAVAILABLE_STRICT_INVALID'}
    return {**base,'classification':'VALID_NO_CONFIRMED_EVENT' if prediction['window_outcome']=='NO_CONFIRMED_EVENT' else 'VALID_'+prediction['window_outcome'],
            'authoritative_prediction':prediction,'matching_status':'ELIGIBLE_SUBJECT_TO_GT_SCOPE'}

def preserve_raw(path: Path, raw: bytes):
    """Exclusive durable raw write must occur before parsing/receipt validation."""
    import os
    with Path(path).open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return digest(raw)

def gated_evaluation(raw, aliases, record, eligibility, representation, *, matcher_policy=CLOSED_INTERVAL_MATCHER):
    classified=classify_output(raw,aliases)
    if classified['authoritative_prediction'] is None:
        return {'classification':classified,'matching_status':classified.get('matching_status','UNAVAILABLE_ABSENT_OR_INVALID'),
                'sensitivity_results':None,'no_event_inferred':False,'qualitative_review':classified['qualitative_review']}
    results={}
    for tolerance in (0,0.2,0.5):
        results[str(tolerance)]=evaluate_item(record,eligibility,classified['authoritative_prediction'],representation,
            {'event_time_tolerance_s':tolerance,'bounded_interval_overlap_required':False,'matcher_policy':matcher_policy})
    return {'classification':classified,'matching_status':'EVALUATED_WITH_GT_SCOPE','sensitivity_results':results,
            'qualitative_review':classified['qualitative_review'],'formal_metrics':'UNDEFINED'}

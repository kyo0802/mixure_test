"""Identity acceptance gates the unchanged fresh Qwen2.5 integration path."""
from .io import ROOT,OUT,read,save
from .runner import verify_freeze,replay
from .inputs import visual_namespace

def run_smoke():
    verify_freeze();gate=read(OUT/'known_val_regression/safety_summary.json',{})
    if not gate.get('identity_safety_gate_passed'):
        result={'status':'SKIPPED_IDENTITY_SAFETY_GATE','model_requested':'Qwen2.5-VL-7B NF4',
            'model_loaded':False,'Qwen3_or_Strata_used':False,
            'reason':gate.get('blockers',['Identity acceptance not established'])}
        save(OUT/'smoke/qwen25_smoke.json',result);return result
    from memory_graph.identity import pipeline as frozen
    from memory_graph.v296_reid import smoke as helpers
    old=frozen.OUT;old_helper=helpers.OUT;frozen.OUT=OUT;helpers.OUT=OUT
    try:
        video=ROOT/'test2.mp4';raw=OUT/'smoke/fresh_raw_seed'
        frozen.raw(video,raw)
        log=read(raw/'sam/unverified_propagation.json')
        if log:save(raw/'raw/sam/sam_continuity_log.json',log)
        with visual_namespace():rows=helpers.fresh_crops(raw/'raw','smoke_test2',video)
        frames=read(OUT/'inputs/smoke_test2/frames.json')
        dest=OUT/'smoke/v297_test2';metrics=replay('smoke_test2',dest,rows,frames)
        prepared=frozen.prepare(dest,video);frozen.reason(dest)
        responses=read(dest/'prepared/qwen/responses.json',[])
        result={'status':'COMPLETE' if responses else 'FAILED_NO_EVENT_CALLS','model':'Qwen2.5-VL-7B NF4',
            'Qwen3_or_Strata_used':False,'fresh_yolo':True,'fresh_sam':bool(log),'V297_identity':metrics,
            'events':prepared,'calls':len(responses),'EOS_complete':bool(responses) and all(r['trace']['ended_with_EOS'] for r in responses),
            'schema_valid':bool(responses) and all(r['validation']['schema_valid'] for r in responses),
            'validator_valid':bool(responses) and all(r['validation']['valid'] for r in responses),'unchanged_frozen_interfaces':True}
        save(OUT/'smoke/qwen25_smoke.json',result);return result
    finally:frozen.OUT=old;helpers.OUT=old_helper

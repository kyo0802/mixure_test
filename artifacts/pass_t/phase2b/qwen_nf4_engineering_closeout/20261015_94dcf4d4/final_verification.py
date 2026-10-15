"""Post-run integrity and ordering verification only, no VLM/processor calls."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import support as s
from collections import Counter

def main():
    manifest=s.read(s.OUT/'run_manifest.json');lock=s.read(s.OUT/'PREREGISTRATION_LOCK_RECEIPT.json')
    assert s.sha(s.OUT/'run_manifest.json')==lock['manifest_sha256']
    assert s.sha(s.ROOT/manifest['criteria_path'])==lock['criteria_sha256']
    for name,h in {**manifest['source_hashes'],**manifest['input_hashes'],**manifest['CPU_preprocessing_receipt_hashes']}.items():
        assert s.sha(s.ROOT/name)==h,name
    assets=manifest['model_assets']['files_sha256']
    for name,h in assets.items():
        assert s.sha(s.MODEL/name)==h,name
    metadata={
      'artifacts/pass_t/phase2a/v2/external_returns/datasets/ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c/external_dev_gt.json':'ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c',
      'artifacts/pass_t/phase2a/v2/exhaustive_reviews/adjudicated_7e28b9edf80a8e4da88caa66/adjudicated_dev_view.json':'fa0133e4e49e54bdbac2ba59420d29b504e8bf219fa8179b57cd1b35261a005c',
      'artifacts/pass_t/phase2a/v2/contracts/EVENT_GT_ANNOTATION_POLICY_V2.md':'c90f527eb01e3b320138961570c5647670536d3611feae3c4b7a1d10e33fdac4'}
    for name,h in metadata.items():assert s.sha(s.ROOT/name)==h,name
    markers=sorted((s.OUT/'runs').glob('*/started.json'))
    assert len(markers)==13
    assert (s.OUT/'MODEL_UNLOADED.json').exists()
    model_start=s.read(s.OUT/'MODEL_LOAD_STARTED.json')['started_at_unix']
    starts=[s.read(p)['started_at_unix'] for p in markers]
    assert lock['locked_at_unix']<model_start<min(starts)
    for p in markers:
        finished=s.read(p.parent/'completed.json')
        assert s.sha(p.parent/'raw_output.txt')==finished['raw_output_sha256']
    for i,row in enumerate(manifest['original_B_order'],1):
        record=s.read(s.OUT/f'runs/B_{i:02d}/completed.json')
        assert record['fixture']==row['fixture_id']
        assert record['representation']+'_8'==row['representation']
        assert record['video_input_mode']=='NATIVE_VIDEO_ARRAY_DISABLED'
    categories=s.read(s.OUT/'VARIANT_B_SUMMARY.json')['violation_attempt_counts']
    paths=Counter()
    for i in range(1,13):
        for predicate in s.read(s.OUT/f'runs/B_{i:02d}/completed.json')['validation'].get('predicates_diagnostic_only',[]):
            if predicate['status']=='VIOLATED':paths[predicate['json_path']]+=1
    s.save('POST_RUN_WARNING_DISCLOSURE.json',{'temporal_uncertainty_warning_attempts':categories.get('EMPTY_TIMING_UNCERTAINTY',0),
      'window_citation_evidence_warning_attempts':categories.get('EMPTY_WINDOW_CITATIONS',0),
      'individual_schema_violation_path_counts':dict(paths),
      'membership_pass_not_complete_citation_evidence':True,'semantic_diagnostic_pass_not_schema_or_strict_pass':True,
      'warnings_do_not_authorize_tuning_or_additional_calls':True})
    s.save('POST_RUN_INTEGRITY_AND_ORDER.json',{'model_assets_checked':len(assets),'model_assets_unchanged':True,
      'Phase2a_GT_metadata_hashes_unchanged':metadata,'DEV_image_reads':0,'source_manifest_hashes_unchanged':True,
      'lock_before_model_load_before_first_generation':True,'lock_unix':lock['locked_at_unix'],
      'model_load_started_unix':model_start,'first_generation_started_unix':min(starts),
      'actual_started_generations':len(markers),'smoke_generations':1,'B_generations':12,'B_order_unchanged':True,
      'all_raw_hashes_valid':True,'single_runtime_unloaded':True,'hardware_after':s.hardware(),
      'scope':'hash verification only; no model/processor/forward/generate invoked'})
    print('FINAL_INTEGRITY_PASS: model assets, metadata, locked sources, 13 raw receipts, pre-generation lock order',flush=True)

if __name__=='__main__':main()

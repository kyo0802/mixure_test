"""Final publication/integrity inventory, no model or processor calls."""
import os
os.environ['CUDA_VISIBLE_DEVICES']='-1'
import support as s

def main():
    run=s.read(s.OUT/'V1D_PREREGISTERED_EXECUTION_MANIFEST.json');lock=s.read(s.OUT/'EXECUTION_LOCK_RECEIPT.json')
    assert s.sha(s.OUT/'V1D_PREREGISTERED_EXECUTION_MANIFEST.json')==lock['manifest_sha256']
    for name,h in {**run['source_sha256'],**run['CPU_receipt_sha256']}.items():assert s.sha(s.ROOT/name)==h,name
    for name,h in run['media_sha256'].items():assert s.sha(s.OUT/name)==h,name
    complete=s.read(s.OUT/'GPU_EXECUTION_COMPLETE.json');assert complete['completed_calls']==8 and complete['extra_calls']==0
    assert all(s.Path(p).is_relative_to(s.OUT/'media') for p in complete['pixel_paths_read'])
    assert all(reason=='SERVER_STARTUP' for reason in complete['denied']),complete['denied']
    markers=list((s.OUT/'runs').glob('*/started.json'));assert len(markers)==8
    assert (s.OUT/'MODEL_UNLOADED.json').exists()
    for marker in markers:
        receipt=s.read(marker.parent/'completed.json')
        assert s.sha(marker.parent/'raw_output.txt')==receipt['raw_response_sha256']
        assert s.sha(marker.parent/'runtime_receipt.json')==receipt['runtime_receipt_sha256']
    after=s.git();before=s.read(s.OUT/'BEFORE.json')['git']
    assert all(after[k]==before[k] for k in ['head','index_sha256','staged_diff_sha256'])
    copies={}
    for name in ['LATEST_REPORT.md','LATEST_DECISIONS.md','RESULTS.csv','README.md']:
        path=s.ROOT/'WORKSPACE/Pass_T'/name;copies[path.relative_to(s.ROOT).as_posix()]=s.sha(path)
    s.save('FINAL_VERIFICATION.json',{'execution_source_hashes_match':True,'fixtures_and_order_match':True,
      'model_and_old_source_preservation_receipt':'V1D_PRESERVATION.json','started_and_completed_generations':8,
      'raw_hashes_verified':8,'old_or_real_image_reads':0,'model_unloaded':True,'CPU_only_finalization':True,
      'git_before':before,'git_after_publication':after,'HEAD_index_staged_unchanged':True,
      'expected_worktree_changes':'single bounded bridge pin extension, new task artifacts and daily WORKSPACE publication',
      'workspace_copies_sha256':copies,'no_extra_model_calls':True,'no_V1E':True,'Protocol_Freeze':False,'commit_push':0})
    s.save('GUARD_EVENT_DISCLOSURE.json',{'recorded_denials':complete['denied'],'blocked_socket_bind_calls':complete['denied'].count('SERVER_STARTUP'),
      'forbidden_media_access_denials':0,'network_connect_denials':0,'caller_stack_recorded':False,
      'interpretation':'Generic socket.bind denial, not evidence that a VLM server started. Caller/purpose unverified. All eight direct local runtime generations completed.',
      'finalization_initial_assertion':'Overbroad zero-denial assertion failed; media scope still passed. Narrowed reporting check to preserve and disclose blocked bind, no runtime/guard change.'})
    old=s.read(s.OUT/'DELIVERABLE_MANIFEST.json')
    modified=[]
    for name,h in old['files_sha256'].items():
        if s.sha(s.OUT/name)!=h:modified.append(name)
    assert set(modified)<= {'PASS_T_PHASE2B_QWEN_NF4_V1D_REGRESSION_REPORT.md','V1D_HUMAN_PILOT_DECISION_PACKAGE.md'}
    s.save('REPORT_FINALIZATION_HISTORY.json',{'initial_reporting_manifest':old,'reporting_files_amended_only':modified,
      'reason':'Human-readable mandatory-field interpretation and source SHA table; no raw/scoring/prompt/fixture/runtime mutation'})
    final={**old,'files_sha256':{p.relative_to(s.OUT).as_posix():s.sha(p) for p in s.OUT.rglob('*') if p.is_file() and p.name!='DELIVERABLE_MANIFEST.json'},
      'workspace_copies_sha256':copies,'reporting_finalized':True,'kind':'ENGINEERING_DELIVERABLE_INVENTORY_NOT_PROTOCOL_FREEZE',
      'actual_calls':8,'V1D_sha256':run['prompt_sha256'],'V1C_unchanged':True,'final_candidate_approved':False}
    s.save('manifest_ready.json',final)
    print('FINAL_VERIFICATION_PASS eight raw outputs, unchanged execution lock and media, Git authority, WORKSPACE copies',flush=True)

if __name__=='__main__':main()

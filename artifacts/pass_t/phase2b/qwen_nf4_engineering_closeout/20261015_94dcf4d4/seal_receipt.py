"""Prepare final reporting inventory; cannot alter locked execution or model outputs."""
import support as s

def main():
    old=s.read(s.OUT/'DELIVERABLE_MANIFEST.json')
    amended=[]
    for name,h in old['files_sha256'].items():
        if s.sha(s.OUT/name)!=h:amended.append(name)
    allowed={'PASS_T_PHASE2B_QWEN_NF4_ENGINEERING_CLOSEOUT_REPORT.md','QWEN_NF4_FINAL_PILOT_DECISION_PACKAGE.md'}
    assert set(amended)<=allowed,amended
    integrity=s.read(s.OUT/'POST_RUN_INTEGRITY_AND_ORDER.json')
    assert integrity['all_raw_hashes_valid'] and integrity['actual_started_generations']==13
    s.save('REPORT_FINALIZATION_HISTORY.json',{'initial_reporting_manifest':old,'initial_manifest_sha256':s.sha(s.OUT/'DELIVERABLE_MANIFEST.json'),
      'amended_reporting_files_only':amended,'reason':'Add explicit failure/warning interpretation, readable tables and exact source SHA; no result/raw/contract mutation',
      'execution_manifest_unchanged':True})
    files={p.relative_to(s.OUT).as_posix():s.sha(p) for p in s.OUT.rglob('*') if p.is_file() and p.name!='DELIVERABLE_MANIFEST.json'}
    copies={}
    for name in ['LATEST_REPORT.md','LATEST_DECISIONS.md','RESULTS.csv','README.md']:
        p=s.ROOT/'WORKSPACE/Pass_T'/name;copies[p.relative_to(s.ROOT).as_posix()]=s.sha(p)
    final={**old,'files_sha256':files,'workspace_copies_sha256':copies,'reporting_finalized':True,
      'kind':'FINAL_ENGINEERING_DELIVERABLE_INVENTORY_NOT_PROTOCOL_FREEZE','post_run_integrity_verified':True,
      'original_Git_HEAD_index_staged_unchanged':True,'only_authorized_existing_source_change':'nf4.py opt-in branch',
      'default_mode':'NATIVE_VIDEO_ARRAY_DISABLED','raw_outputs_preserved':13,'event_bearing_B':9,'strict_B_pass':2,
      'CPU_unique_checks':89,'human_protocol_approval_inferred':False}
    s.save('manifest_ready.json',final)
    print('FINAL_MANIFEST_READY',len(files),'files;13 raw;only2 draft reporting files amended',flush=True)

if __name__=='__main__':main()

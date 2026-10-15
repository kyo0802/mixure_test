"""Seal this audit only; deliberately not a protocol freeze function."""
import csv
import hashlib
import json
import re
from pathlib import Path
import audit

REQUIRED = [
 'QWEN_NF4_STRUCTURED_OUTPUT_AUDIT.csv',
 'QWEN_NF4_STRUCTURED_OUTPUT_FAILURE_REPORT.md',
 'QWEN_NF4_PREDICTION_CONTRACT_SEMANTICS_REVIEW.md',
 'QWEN_NF4_STRUCTURED_OUTPUT_REMEDIATION_OPTIONS.md',
 'QWEN_NF4_MINIMAL_SYNTHETIC_REGRESSION_PLAN.md',
 'QWEN_NF4_FINAL_PILOT_DECISION_DRAFT.md',
 'QWEN_NF4_FREEZE_READINESS_AUDIT.md',
 'QWEN_NF4_OUTPUT_AUDIT_PRESERVATION_REPORT.md',
 'PASS_T_PHASE2B_QWEN_NF4_OUTPUT_AUDIT_REPORT.md',
]

def main():
    assert all((audit.OUT/n).is_file() and (audit.OUT/n).stat().st_size for n in REQUIRED)
    summary=audit.read(audit.OUT/'analysis_summary.json')
    preservation=audit.read(audit.OUT/'preservation.json')
    tests=audit.read(audit.OUT/'test_results.json')
    assert not summary['issues'] and not preservation['changed_files'] and preservation['git_unchanged']
    assert audit.git()==preservation['git_after']
    assert tests['passed']==tests['tests']==28 and not tests['failures'] and not tests['errors']
    with (audit.OUT/REQUIRED[0]).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==66 and len({r['attempt_id'] for r in rows})==66
    assert sum(r['population']=='PRIMARY' for r in rows)==33
    primary=[r for r in rows if r['population']=='PRIMARY']
    assert sum(r['strict_pass']=='True' for r in primary)==15
    assert all(r['transport_receipt_path']!='UNKNOWN' for r in rows)
    checked=0
    for n in REQUIRED[1:]:
        for link in re.findall(r'\]\(([^)]+)\)',(audit.OUT/n).read_text(encoding='utf-8')):
            link=link.strip('<>')
            if link.startswith(('http:','https:','#')):continue
            p=Path(link)
            if not p.is_absolute():p=audit.OUT/p
            assert p.exists(),(n,link)
            checked+=1
    files={p.relative_to(audit.OUT).as_posix():audit.sha(p)
           for p in sorted(audit.OUT.rglob('*')) if p.is_file()}
    receipt={'kind':'CPU_ONLY_OUTPUT_AUDIT_NOT_PROTOCOL_FREEZE',
       'status':'PASS_T_PHASE2B_QWEN_NF4_OUTPUT_AUDIT_COMPLETE_AWAITING_USER_DECISIONS',
       'date':'2026-10-15','timezone':'Asia/Taipei',
       'required_deliverables':REQUIRED,'files_sha256':files,
       'primary_attempts':33,'history_attempts_separate':33,'csv_rows':66,
       'strict_primary_passes':15,'strict_primary_failures':18,'historical_replay_matches':66,
       'cpu_tests_passed':28,'protected_files_checked':preservation['checked_files'],
       'existing_file_changes':[],'git_unchanged':True,'checked_report_links':checked,
       'new_model_calls':0,'actual_phase2a_pilot_generations':0,
       'protocol_freeze_created':False,'protocol_approved':False,'human_approval':None,
       'next_task_requires_authorization':'PREPARE_QWEN_NF4_PROMPT_CLARIFICATION_AND_MATCHED8_CPU_PREFLIGHT'}
    audit.write('audit_completion_receipt.json',receipt)
    # Mark only new audit output files read-only. Historical files are never chmod'ed.
    for p in audit.OUT.rglob('*'):
        if p.is_file():p.chmod(0o444)
    changed=[n for n,h in files.items() if audit.sha(audit.OUT/n)!=h]
    assert not changed
    print(json.dumps({'status':receipt['status'],'required_deliverables':len(REQUIRED),'sealed_files':len(files)+1,
       'report_links_valid':checked,'receipt_sha256':audit.sha(audit.OUT/'audit_completion_receipt.json')},ensure_ascii=False))

if __name__=='__main__':main()

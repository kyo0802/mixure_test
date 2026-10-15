"""Record final publication state; no inference or execution configuration changes."""
import support as s

before=s.read(s.OUT/'BEFORE.json')['git']
after=s.git()
assert all(before[k]==after[k] for k in ['head','index_sha256','staged_diff_sha256'])
copies={}
for name in ['LATEST_REPORT.md','LATEST_DECISIONS.md','RESULTS.csv','README.md']:
    path=s.ROOT/'WORKSPACE/Pass_T'/name
    copies[path.relative_to(s.ROOT).as_posix()]=s.sha(path)
s.save('FINAL_GIT_AND_PUBLICATION.json',{'git_before':before,'git_after_publication':after,
    'HEAD_index_staged_unchanged':True,'expected_worktree_changes':'authorized NF4 opt-in branch, new engineering files, WORKSPACE report/navigation publication',
    'WORKSPACE_sha256':copies,'no_commit_push':True,'protocol_freeze':False})
print('PUBLICATION_AND_GIT_VERIFIED',flush=True)

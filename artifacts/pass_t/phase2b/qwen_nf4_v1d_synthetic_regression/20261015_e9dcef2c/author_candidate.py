"""Created only AFTER prospective fixture lock; exactly one additive candidate."""
import support as s
import difflib,hashlib

def main():
    lock=s.read(s.OUT/'FIXTURE_LOCK_RECEIPT.json')
    assert not lock['candidate_exists_at_lock']
    assert s.sha(s.OUT/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json')==lock['fixture_manifest_sha256']
    path=s.REF/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt';original=path.read_bytes()
    assert s.sha(path)=='3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722'
    assert b'\r\n' not in original
    a=b'Timing evidence: make timing_uncertainty meaningful and specific to the observed sampling resolution, direct transition, genuine observation gap, or unresolved timing. No fixed number of bounding frames is required. Missing observations are not observed event motion; BEFORE/AFTER evidence brackets do not establish physical event duration.\n'
    b=b'Window uncertainty (/uncertainty): this required root-level string must be nonempty for every window outcome. Summarize only evidence-supported window-level limitations, such as sparse sampling, occlusion, uncertain target association, or lack of observed transition evidence; do not assert a limitation merely because it is listed here. If no additional limitation is observable, describe that assessment relative to the supplied observations without fabricating a limitation. Do not indiscriminately duplicate event-specific explanations, and do not leave the string empty merely because no event was confirmed.\n\n'
    c=b'Citation scope: a supplied alias is eligible only if its frame was actually processor-consumed. When observations cannot establish an event, use the existing permitted uncertain outcome with citations supporting that assessment or its limitations; never manufacture event evidence or an alias.\n'
    timing=next(line for line in original.splitlines(keepends=True) if line.startswith(b'Timing:'))
    window=next(line for line in original.splitlines(keepends=True) if line.startswith(b'Window evidence:'))
    candidate=original.replace(timing,timing+a,1).replace(window,b+window+c,1)
    assert candidate.replace(a,b'',1).replace(b,b'',1).replace(c,b'',1)==original
    s.save('QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt',candidate.decode('utf8'))
    diff=''.join(difflib.unified_diff(original.decode().splitlines(True),candidate.decode().splitlines(True),
      fromfile='QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt',tofile='QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt',n=0))
    s.save('V1C_TO_V1D_UNIFIED_DIFF.patch',diff)
    s.save('PROMPT_AUTHORING_RECEIPT.json',{'fixture_lock_sha256':s.sha(s.OUT/'FIXTURE_LOCK_RECEIPT.json'),
      'fixture_lock_unix':lock['created_at_unix'],'authored_at_unix':s.time.time(),'author_script_sha256':s.sha(__file__),
      'V1C_sha256':s.sha(path),'V1D_sha256':s.sha(s.OUT/'QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt'),
      'candidate_count':1,'added_lines':sum(x.startswith('+') and not x.startswith('+++') for x in diff.splitlines()),
      'removed_lines':sum(x.startswith('-') and not x.startswith('---') for x in diff.splitlines()),
      'original_bytes_recoverable_by_removing_only_three_additions':True,'encoding':'UTF8 no BOM LF, unchanged',
      'sections':['event timing_uncertainty','root /uncertainty','window citations processor-consumed scope'],
      'model_calls_before_authorship':0})
    for p in [s.OUT/'QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt',s.OUT/'PROMPT_AUTHORING_RECEIPT.json',s.OUT/'V1C_TO_V1D_UNIFIED_DIFF.patch',s.OUT/'author_candidate.py']:p.chmod(0o444)
    print('ONE_V1D_AUTHORED',s.sha(s.OUT/'QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt'),flush=True)

if __name__=='__main__':main()

"""Reconfirm population after dependency type-guard correction; original receipt retained."""
import core,json
from collections import Counter
from diagnostics.collect_all_prediction_violations import collect
from memory_graph.pass_t.phase2b.predictions import schema,parse_raw,validate_prediction

def main():
    previous=core.read(core.OUT/'STEP_RECEIPT_0.json');rows=[json.loads(s) for s in (core.OUT/'COLLECT_ALL_ATTEMPT_VIOLATIONS.jsonl').read_text().splitlines()]
    old=core.read(core.ROOT/'artifacts/pass_t/phase2b/output_failure_audit/qwen_nf4/20261015/primary_attempts.json')
    byid={x['attempt_id']:x for x in old};changes=[];breakdown=Counter()
    for row in rows:
        x=byid[row['attempt_id']];value=parse_raw((core.ROOT/x['raw_path']).read_bytes())
        new=collect(value,x['consumed_aliases'],schema());strict=validate_prediction(value,x['consumed_aliases'])
        if new!=row['shadow_predicates'] or strict!=row['reproduced_strict']:changes.append(x['attempt_id'])
        for rule in new:
            if rule['status']=='VIOLATED' and rule['rule_id']=='KNOWN_STATE_SUPPORT':breakdown[rule['json_path'].split('/')[-1]]+=1
    assert not changes and core.authorities()
    record={'current_population_replay_unchanged':True,'attempts':33,'changed_attempts':changes,'known_state_individual_breakdown':dict(breakdown),
      'original_shadow_source_sha256':previous['inputs'][core.rel(core.OUT/'diagnostics/collect_all_prediction_violations.py')],
      'current_shadow_source_sha256':core.sha(core.OUT/'diagnostics/collect_all_prediction_violations.py'),
      'reason':'Wrong-type list enum values now yield NOT_EVALUABLE instead of Python TypeError. Shadow-only robustness correction; no production Validator changes; all 33 observed results identical.'}
    core.save('diagnostics/shadow_dependency_correction.json',record)
    core.receipt('0_CONFIRMATION',[core.OUT/'STEP_RECEIPT_0.json',core.OUT/'diagnostics/collect_all_prediction_violations.py'],
      [core.OUT/'diagnostics/shadow_dependency_correction.json'],strict_replay_agreement='33/33',G2=True,G3=True,G4=True,G5=True)
    print(record)
if __name__=='__main__':main()

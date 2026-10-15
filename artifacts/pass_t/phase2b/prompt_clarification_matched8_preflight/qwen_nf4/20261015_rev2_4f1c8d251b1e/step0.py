import core
from collections import Counter
from memory_graph.pass_t.phase2b.predictions import schema,parse_raw,validate_prediction
from diagnostics.collect_all_prediction_violations import collect

def run():
    authority=core.authorities();cap=core.ROOT/'artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree'
    inventory=core.read(core.ROOT/'artifacts/pass_t/phase2b/output_failure_audit/qwen_nf4/20261015/primary_attempts.json')
    manifest=core.read(cap/'engineering_completion_receipt.json')['files'];rows=[];g2=[];g3=[];mismatches=[]
    for x in inventory:
        rawp=core.ROOT/x['raw_path'];raw=rawp.read_bytes();digest=core.sha(rawp)
        if digest!=x['raw_sha256'] or manifest[str(rawp.relative_to(cap)).replace('\\','/')]!=digest:raise RuntimeError('INTEGRITY_BLOCKED_RAW_HASH')
        value=parse_raw(raw);original=core.read(core.ROOT/x['attempt_receipt_path'])['validation']
        strict=validate_prediction(value,x['consumed_aliases']);shadow=collect(value,x['consumed_aliases'],schema())
        if strict!=original:mismatches.append(x['attempt_id'])
        violated=[s for s in shadow if s['status']=='VIOLATED']
        if (not violated)!=strict['valid']:g2.append(x['attempt_id'])
        first=next((v for key in ['structural_errors','citation_errors','semantic_errors'] for v in strict[key]),None)
        # Structural iterator is exact original sorted order. For this population
        # every failure has that first stage; no speculation about source intent.
        shadow_first=next((s['strict_error'] for s in shadow if s['status']=='VIOLATED'),None)
        if shadow_first!=first:g3.append({'attempt':x['attempt_id'],'strict':first,'shadow':shadow_first})
        masked=[s for s in violated if s['rule_id']=='KNOWN_STATE_SUPPORT' and strict['structural_errors']]
        rows.append({'attempt_id':x['attempt_id'],'condition':x['condition'],'kind':x['kind'],
          'raw_path':x['raw_path'],'raw_sha256':digest,'event_count':len(value['events']),
          'original_strict':original,'reproduced_strict':strict,'shadow_predicates':shadow,
          'violations':violated,'masked_count':len(masked),'not_evaluable':[s for s in shadow if s['status']=='NOT_EVALUABLE'],
          'strict_first_error':first,'shadow_first_error':shadow_first,'discrepancies':[]})
    counts=Counter(v['rule_id'] for r in rows for v in r['violations']);attempt_counts=Counter(k for r in rows for k in set(v['rule_id'] for v in r['violations']))
    masked_attempts=sum(bool(r['masked_count']) for r in rows)
    gates={'G1':len(rows)==33 and len({r['attempt_id'] for r in rows})==33 and not mismatches and sum(r['reproduced_strict']['valid'] for r in rows)==15,
       'G2':not g2,'G3':not g3,'G4':attempt_counts['EMPTY_TIMING_UNCERTAINTY']==13 and attempt_counts['EMPTY_WINDOW_CITATIONS']==5 and masked_attempts==11,
       'G5':core.sha(core.ROOT/'src/memory_graph/pass_t/phase2b/predictions.py')==authority['src/memory_graph/pass_t/phase2b/predictions.py']}
    report={'gates':gates,'strict_agreement':len(rows)-len(mismatches),'passes':sum(r['reproduced_strict']['valid'] for r in rows),
      'attempts':len(rows),'warmup':sum(r['kind']=='WARMUP' for r in rows),'measured':sum(r['kind']=='MEASURED' for r in rows),
      'affected_attempts_per_rule':dict(attempt_counts),'individual_violations_per_rule':dict(counts),
      'masked_attempts':masked_attempts,'masked_individual_violations':sum(r['masked_count'] for r in rows),
      'g2_discrepancies':g2,'g3_discrepancies':g3,'strict_mismatches':mismatches,
      'conditions':{c:{'attempts':sum(r['condition']==c for r in rows),'affected_rules':dict(Counter(k for r in rows if r['condition']==c for k in set(v['rule_id'] for v in r['violations'])))} for c in sorted({r['condition'] for r in rows})},
      'event_cross_tab':{n:dict(Counter(v['rule_id'] for r in rows if r['event_count']==n for v in r['violations'])) for n in [0,1,2]}}
    core.save('diagnostics/COLLECT_ALL_ATTEMPT_VIOLATIONS.jsonl',''.join(core.canon(r).decode() for r in rows))
    core.save('diagnostics/frequencies.json',report)
    core.save('COLLECT_ALL_ATTEMPT_VIOLATIONS.jsonl',''.join(core.canon(r).decode() for r in rows))
    core.save('COLLECT_ALL_VALIDATOR_DIAGNOSTIC_REPORT.md',f'''# Collect-all 非計分診斷

主要母體33次，11 warmup/22 measured，strict原判定15/33。重播一致{report['strict_agreement']}/33；G1–G5={gates}。

影子module不接入scoring。現validator只有完整函式、未暴露獨立semantic predicates，因此只讀匯入原schema/parser/validator，另依原碼逐條reimplement shadow；G2/G3核對該做法而不改validator。所有原raw SHA由capacity完成回條驗證。

Affected attempts：{dict(attempt_counts)}；individual predicate violations：{dict(counts)}。不可將兩種數量相加。被early return遮住的known-state缺支持：{masked_attempts}份、{report['masked_individual_violations']}個欄位。包括event before/after與last state，完整JSON path、既有error文字、state/alias證據在JSONL；不只猜HELD狀態。零事件的event-specific checks是NOT_APPLICABLE；wrongtype/missingalias prerequisites用NOT_EVALUABLE。

13空timing/5空windowlist/11masked與前audit核對，G4={gates['G4']}。精確數量及condition/event-count tables在diagnostics/frequencies.json；解釋模型內在機制仍是推測。沒有schema relax、raw修補或重新評分。target HIGH/POSSIBLE/confirmed政策並非現validator規則，標NOT_APPLICABLE待語意審查。
''')
    core.receipt(0,[core.ROOT/'src/memory_graph/pass_t/phase2b/predictions.py',cap/'engineering_completion_receipt.json',core.OUT/'diagnostics/collect_all_prediction_violations.py'],
      [core.OUT/n for n in ['COLLECT_ALL_ATTEMPT_VIOLATIONS.jsonl','COLLECT_ALL_VALIDATOR_DIAGNOSTIC_REPORT.md','diagnostics/frequencies.json']],
      'COMPLETE' if all(gates.values()) else 'PARTIAL_WITH_BLOCKERS',gates=gates)
    print(report)
    if not all(gates.values()):raise SystemExit('STEP_0_GATE_FAILED')
if __name__=='__main__':run()

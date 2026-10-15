"""Final checks after temporal-position supplement; original preservation report retained."""
import core
import ast
from datetime import datetime,timezone

def main():
    core.authorities();tests=core.read(core.OUT/'cpu_tests.json');positions=core.read(core.OUT/'MODEL_VISIBLE_TEMPORAL_POSITION_AUDIT.json')
    assert tests['passed']==60 and positions['additional_cpu_tests_passed']==3
    lock=core.read(core.OUT/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json')
    assert core.sha(core.OUT/'fixture_generator.py')==lock['generator_sha256']
    for n,h in lock['model_visible_frames_sha256'].items():assert core.sha(core.OUT/n)==h
    bad=[];scan=[]
    for p in core.OUT.rglob('*.py'):
        hits=[]
        for n in ast.walk(ast.parse(p.read_text())):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ['generate','from_pretrained']:
                text=ast.unparse(n.func);hits.append({'line':n.lineno,'call':text})
                if text!='AutoProcessor.from_pretrained':bad.append((str(p),n.lineno,text))
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ['serve','serve_forever','uvicorn']:
                bad.append((str(p),n.lineno,n.func.id))
        scan.append({'path':str(p.relative_to(core.OUT)),'sha256':core.sha(p),'sensitive_calls':hits})
    assert not bad
    before=core.read(core.OUT/'PREFLIGHT_BEFORE.json');now=core.git();assert now==before['git']
    def command(args):
        p=core.subprocess.run(args,cwd=core.ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    result={'timestamp':datetime.now(timezone.utc).isoformat(),'all_new_scripts_scanned':scan,'forbidden_calls':bad,
      'gpu':command(['nvidia-smi','--query-gpu=index,name,memory.used,memory.free,utilization.gpu','--format=csv,noheader']),
      'compute_processes':command(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader']),
      'running_processes':command(['powershell','-NoProfile','-Command','Get-Process | Select-Object Id,ProcessName | ConvertTo-Json -Compress']),
      'git_unchanged':True,'locked_fixture_hashes_unchanged':True,'unique_cpu_tests_passed':63,'new_model_calls':0,
      'scope':'Final source scan, observations and lock/source gates. Full historical-file rehash already completed in preservation.json; only new audit outputs were added subsequently.'}
    core.save('FINAL_CPU_SAFETY_CHECKS.json',result)
    core.save('FINAL_CPU_SAFETY_CHECKS.md','''# 最終補充核對

完整保護hash核對後另補model temporal-position稽核與3個CPU計算tests。最終所有新scripts再做AST scan，完整結果及新的GPU/processsnapshot在FINAL_CPU_SAFETY_CHECKS.json。

總uniqueCPUchecks為60+3=63，全通過；locked56frames/generatorhash再核對不變。原報告的10script ASTscan是當時範圍，最終scan包含後增補的time-position與此checker；沒有modelclassfrompretrained/generate/serverlaunchcall，唯一AutoProcessor loader保持local-only。

model時間欄位需合讀MODEL_VISIBLE_TEMPORAL_POSITION_AUDIT：processor的gridseconds與model.long()後的relativepositionproxy分開。前者是CPU實際tensor，後者是installedsource的CPU算式，不是model forward。全部Video仍FRAME_MATCHED_ONLY，沒有改既有判定或fixture。

此補充不改原保護驗證、原步驟回條或任何productionfile。GPU/process觀察不是全機連續trace，不聲稱能排除其他process的GPU操作。
''')
    core.receipt('5_FINAL_CHECKS',[core.OUT/'STEP_RECEIPT_5.json',core.OUT/'STEP_RECEIPT_2_TIME_POSITION.json'],
      [core.OUT/'FINAL_CPU_SAFETY_CHECKS.json',core.OUT/'FINAL_CPU_SAFETY_CHECKS.md'],cpu_tests_passed=63,new_model_calls=0)
    print({'scripts_scanned':len(scan),'forbidden':bad,'unique_CPU_tests':63,'GPU':result['gpu']['stdout']})
if __name__=='__main__':main()

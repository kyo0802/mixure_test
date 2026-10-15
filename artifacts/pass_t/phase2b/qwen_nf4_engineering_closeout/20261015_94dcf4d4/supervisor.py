"""Bounded watchdog of one owned worker process tree; no model in supervisor."""
import support as s
import subprocess,time,sys,os
import psutil

def stop_owned(process):
    try:
        for child in reversed(psutil.Process(process.pid).children(recursive=True)):
            try:child.kill()
            except psutil.NoSuchProcess:pass
    except psutil.NoSuchProcess:pass
    if process.poll() is None:process.kill()

def main():
    if (s.OUT/'SUPERVISOR_STARTED.json').exists():raise RuntimeError('EXECUTION_ALREADY_STARTED_NO_AUTOMATIC_REPLAY')
    from worker import verify_lock
    manifest=verify_lock();before=s.hardware()
    memory_free=float(before['gpu_csv'].split(',')[2].split()[0])
    if memory_free<10*1024 or before['ram_available_bytes']<8*2**30:raise RuntimeError('RESOURCE_GATE_BLOCKED')
    # Do not interfere with unrelated processes. Any existing Qwen worker/server blocks launch.
    other=[]
    for p in psutil.process_iter(['pid','cmdline']):
        try:
            cmd=' '.join(p.info['cmdline'] or [])
            if p.pid!=os.getpid() and ('serve_pass_t_local_vlm.py' in cmd or ('worker.py' in cmd and 'qwen_nf4_engineering_closeout' in cmd)):
                other.append(p.pid)
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    if other:raise RuntimeError('EXISTING_VLM_PROCESS_BLOCKS_SINGLE_INSTANCE:'+str(other))
    env=dict(os.environ);env.pop('CUDA_VISIBLE_DEVICES',None);env.pop('PASS_T_PHASE2B_REAL_RUN_PERMISSION',None)
    s.save('SUPERVISOR_STARTED.json',{'started_at_unix':time.time(),'hardware_before':before,'manifest_sha256':s.sha(s.OUT/'run_manifest.json')})
    opened=time.monotonic();samples=[];reason=None
    with (s.OUT/'gpu_worker.log').open('xb') as log:
        proc=subprocess.Popen([sys.executable,'-B',str(s.OUT/'worker.py')],cwd=s.ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
          creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        print('GPU_WORKER_STARTED',proc.pid,flush=True)
        while proc.poll() is None:
            now=time.monotonic()
            try:
                owned=[psutil.Process(proc.pid),*psutil.Process(proc.pid).children(recursive=True)]
                rows=[]
                for p in owned:
                    try:
                        info=p.memory_info();rows.append({'pid':p.pid,'rss_bytes':info.rss,'peak_wset_bytes':getattr(info,'peak_wset',info.rss)})
                    except psutil.NoSuchProcess:pass
                csv=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits'],encoding='utf8',timeout=5).strip().split(',')
                sample={'elapsed_s':now-opened,'owned_pids':rows,'owned_rss_bytes':sum(r['rss_bytes'] for r in rows),
                  'global_gpu_used_mib':float(csv[0]),'global_gpu_free_mib':float(csv[1]),'gpu_util_percent':float(csv[2]),
                  'system_ram_available_bytes':psutil.virtual_memory().available}
                samples.append(sample)
                if sample['global_gpu_used_mib']>14.5*1024 or sample['owned_rss_bytes']>20*2**30 or sample['system_ram_available_bytes']<2*2**30:
                    reason='UNSAFE_RESOURCE_HARD_STOP'
            except (psutil.NoSuchProcess,subprocess.TimeoutExpired):pass
            if (s.OUT/'MODEL_LOAD_STARTED.json').exists() and not (s.OUT/'MODEL_LOADED.json').exists():
                if time.time()-s.read(s.OUT/'MODEL_LOAD_STARTED.json')['started_at_unix']>120:reason='MODEL_LOAD_TIMEOUT'
            for marker in (s.OUT/'runs').glob('*/started.json'):
                if not (marker.parent/'completed.json').exists() and not (marker.parent/'failure.json').exists():
                    if time.time()-s.read(marker)['started_at_unix']>330:reason='REQUEST_TIMEOUT'
            if now-opened>4500:reason='WHOLE_EXECUTION_TIMEOUT'
            if reason:
                stop_owned(proc);break
            time.sleep(1)
        proc.wait()
    s.save('SUPERVISOR_RECEIPT.json',{'exit_code':proc.returncode,'stop_reason':reason,'wall_seconds':time.monotonic()-opened,
      'owned_process_exited':True,'samples':samples,'monitor_scope':'complete owned tree; variable intervals due to NVIDIA-SMI sampling overhead',
      'global_gpu_observed_peak_mib':max((r['global_gpu_used_mib'] for r in samples),default=None),
      'owned_cpu_rss_observed_peak_bytes':max((r['owned_rss_bytes'] for r in samples),default=None),
      'hardware_after':s.hardware(),'no_model_loaded_in_supervisor':True})
    print('GPU_SUPERVISOR_FINISHED',proc.returncode,reason,flush=True)

if __name__=='__main__':main()

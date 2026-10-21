"""One local GPU job at a time, with disk ownership and idempotent submission."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime,timezone
from .sessions import read,session_path
from memory_graph.integration.adapters import sha

TERMINAL={'COMPLETED','PARTIAL','FAILED'}
STAGES=['registration','extraction','cv','nemotron','localization','memory','ready']


def stamp():return datetime.now(timezone.utc).isoformat()


def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');os.replace(temp,path)


def job_path(root,job_id):
    if not re.fullmatch(r'[a-f0-9]{32}',job_id):raise ValueError('Invalid job ID')
    base=(Path(root)/'artifacts/findmind_jobs').resolve();path=(base/job_id).resolve()
    if path.parent!=base:raise ValueError('Job outside approved directory')
    return path


def store_upload(root,name,data,limit_mb=200):
    if Path(name).suffix.lower()!='.mp4':raise ValueError('請上傳 MP4 影片。')
    if not data or len(data)>limit_mb*1024*1024:raise ValueError(f'影片超過 {limit_mb} MB 或內容為空。')
    # ISO BMFF signature preflight only. The actual Phase 7 decoder performs
    # full video/native-PTS validation in the background before model loading.
    if len(data)<12 or data[4:8]!=b'ftyp':raise ValueError('檔案不是可辨識的 MP4 容器。')
    digest=hashlib.sha256(data).hexdigest();folder=Path(root)/'artifacts/findmind_uploads';folder.mkdir(parents=True,exist_ok=True)
    path=folder/(digest+'.mp4')
    if path.exists():
        if sha(path)!=digest:raise ValueError('Existing upload integrity failure')
    else:
        try:
            with path.open('xb') as f:f.write(data)
        except FileExistsError:
            if sha(path)!=digest:raise ValueError('Upload collision/incomplete upload; retry after transfer finishes')
    metadata=folder/(digest+'.json')
    if not metadata.exists():atomic(metadata,dict(filename=Path(name).name,sha256=digest,uploaded=stamp()))
    return path,digest


def phase7_command(root,config):
    return [config['python'],'-X','utf8','-B',str(Path(root)/'scripts/run_findmind_video.py'),
        '--video',config['video_path'],'--query',config['query']]


def submit(root,video_path,query,token):
    root=Path(root).resolve();path=Path(video_path).resolve()
    if not path.is_relative_to((root/'artifacts/findmind_uploads').resolve()) or not path.is_file():raise ValueError('Approved upload required')
    if not query or len(query)>300:raise ValueError('Invalid query')
    folder=job_path(root,token);base=folder.parent;base.mkdir(parents=True,exist_ok=True)
    digest=sha(path)
    if (folder/'config.json').exists():
        existing=read(folder/'config.json')
        if (existing['source_sha256'],existing['query'])!=(digest,query):raise ValueError('Submission token already belongs to another request')
        return token
    lock=base/'gpu.lock'
    try:
        with lock.open('x',encoding='utf8') as f:json.dump(dict(job_id=token,owner_pid=os.getpid(),created=stamp()),f)
    except FileExistsError:raise RuntimeError('已有 GPU 工作或尚未解除的執行鎖。請先查看背景工作狀態，避免重複推論。')
    try:
        folder.mkdir(exist_ok=False)
        config=dict(job_id=token,video_path=str(path),source_sha256=digest,query=query,created=stamp(),
            python=str(root/'.venv/Scripts/python.exe') if os.name=='nt' else sys.executable)
        atomic(folder/'config.json',config)
        atomic(folder/'state.json',dict(job_id=token,status='PENDING',created=config['created'],updated=stamp(),session_id=None,error=None))
        args=[config['python'],'-X','utf8','-B',str(root/'scripts/run_findmind_job.py'),'--job-id',token]
        with (folder/'wrapper.log').open('ab') as log:
            process=subprocess.Popen(args,cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        atomic(folder/'launch.json',dict(pid=process.pid,started=stamp(),command=args))
        return token
    except Exception as e:
        if folder.exists():atomic(folder/'state.json',dict(job_id=token,status='FAILED',updated=stamp(),error=str(e),session_id=None))
        if lock.exists() and read(lock).get('job_id')==token:lock.unlink()
        raise


def alive(pid):
    if not pid:return False
    if os.name=='nt':
        import ctypes
        kernel=ctypes.windll.kernel32
        kernel.OpenProcess.restype=ctypes.c_void_p
        handle=kernel.OpenProcess(0x1000,False,int(pid))
        if not handle:return False
        code=ctypes.c_ulong();ok=kernel.GetExitCodeProcess(ctypes.c_void_p(handle),ctypes.byref(code));kernel.CloseHandle(ctypes.c_void_p(handle))
        return bool(ok and code.value==259)
    try:os.kill(int(pid),0);return True
    except ProcessLookupError:return False
    except PermissionError:return True


def poll(root,job_id):
    folder=job_path(root,job_id);state=read(folder/'state.json');config=read(folder/'config.json')
    # Refreshable progress derives from actual Phase 7 artifacts, not a timer.
    stages={s:'PENDING' for s in STAGES};sid=state.get('session_id')
    active=state['status'] not in TERMINAL
    stages['registration']='RUNNING' if state['status']=='RUNNING' else 'PENDING' if active else 'FAILED'
    if sid:
        session=session_path(root,sid);stages['registration']='COMPLETED'
        stages['extraction']='COMPLETED' if (session/'source_manifest.json').exists() else 'RUNNING' if active else 'FAILED'
        for name in ['cv','nemotron','localization']:
            receipt=session/(name+'_stage.json')
            if receipt.exists():
                status=read(receipt)['status'];stages[name]={'COMPLETE':'COMPLETED','NOT_EXECUTED':'SKIPPED'}.get(status,status)
            elif (session/(name+'.log')).exists():stages[name]='RUNNING' if active else 'FAILED'
        sam=session/'sam_stage.json'
        if sam.exists() and read(sam)['status']!='COMPLETE':stages['localization']=read(sam)['status']
        elif (session/'sam.log').exists() and not sam.exists():stages['localization']='RUNNING' if active else 'FAILED'
        if (session/'memory_graph.json').exists():stages['memory']='COMPLETED'
        elif sam.exists():stages['memory']='RUNNING' if active else 'FAILED'
        if (session/'run_receipt.json').exists() and (session/'memory_graph.json').exists():stages['ready']='COMPLETED'
    launch=read(folder/'launch.json') if (folder/'launch.json').exists() else {}
    worker_pid=state.get('worker_pid') or launch.get('pid')
    if active and worker_pid and not alive(worker_pid):
        state=dict(state,status='FAILED',error='背景工作已中斷；保留日誌與部分輸出。執行鎖不會自動解除，避免尚存的模型程序與新工作重疊。')
        active=False
    if not active:
        stages={s:('SKIPPED' if v=='PENDING' else 'FAILED' if v=='RUNNING' else v) for s,v in stages.items()}
    return dict(**state,stages=stages,source_sha256=config['source_sha256'],query=config['query'])


def list_jobs(root):
    base=Path(root)/'artifacts/findmind_jobs'
    if not base.exists():return []
    rows=[]
    for folder in base.iterdir():
        if folder.is_dir() and (folder/'state.json').exists():
            try:rows.append(poll(root,folder.name))
            except (OSError,ValueError,KeyError):continue
    return sorted(rows,key=lambda s:s.get('created',s.get('updated','')),reverse=True)


def run_job(root,job_id):
    folder=job_path(root,job_id);config=read(folder/'config.json');lock=folder.parent/'gpu.lock'
    if not lock.exists() or read(lock).get('job_id')!=job_id:raise RuntimeError('Job has no GPU execution lease')
    # A second wrapper for the same job must never launch another pipeline.
    with (folder/'worker.started').open('x') as f:f.write(str(os.getpid()))
    atomic(lock,dict(job_id=job_id,owner_pid=os.getpid(),created=config['created']))
    state=dict(job_id=job_id,status='RUNNING',created=config['created'],updated=stamp(),worker_pid=os.getpid(),session_id=None,error=None)
    atomic(folder/'state.json',state)
    try:
        if sha(config['video_path'])!=config['source_sha256']:raise ValueError('Upload changed after submission')
        command=phase7_command(root,config)
        atomic(folder/'execution.json',dict(command=command,started=stamp(),real_phase7_runner=True))
        with (folder/'pipeline.log').open('w',encoding='utf8') as log:
            process=subprocess.Popen(command,cwd=root,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                text=True,encoding='utf8',errors='replace',bufsize=1,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            atomic(folder/'pipeline_process.json',dict(pid=process.pid))
            for line in process.stdout:
                log.write(line);log.flush()
                if line.startswith('SESSION '):
                    candidate=Path(line[8:].strip()).name
                    session_path(root,candidate);state['session_id']=candidate;state['updated']=stamp();atomic(folder/'state.json',state)
            code=process.wait()
        if state['session_id']:
            session=session_path(root,state['session_id'])
            r=read(session/'run_receipt.json') if (session/'run_receipt.json').exists() else None
        else:r=None
        if r and (session/'memory_graph.json').exists():
            state['status']='PARTIAL' if code or r.get('assembly_errors') or any(s['status']!='COMPLETE' for s in r['stages']) else 'COMPLETED'
        else:state.update(status='FAILED',error=f'Phase 7 未建立可查詢 Graph（exit {code}）。請查看日誌。')
        state['exit_code']=code
    except Exception as e:state.update(status='FAILED',error=str(e))
    finally:
        state['updated']=stamp();atomic(folder/'state.json',state)
        # A timed-out GPU worker may remain in WSL; retain its lock for explicit
        # operator inspection rather than enabling a conflicting model load.
        timeout=bool(state.get('session_id') and any(x.get('exit_code')==-9 for x in (r or {}).get('stages',[]))) if 'r' in locals() else False
        child_active='process' in locals() and process.poll() is None
        if not timeout and not child_active and lock.exists() and read(lock).get('job_id')==job_id:lock.unlink()

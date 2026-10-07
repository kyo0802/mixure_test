"""Read-only preservation snapshot for the V294 experiment."""
from pathlib import Path
import hashlib,json,subprocess,time,shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/v294_qwen38'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(rel,data):
    p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf8')
def main():
    dest=OUT/'setup/preserved_state.json'
    if dest.exists():raise FileExistsError('Snapshot already exists')
    paths=[]
    for folder in ('src','scripts','configs','outputs/validation','outputs/identity_rebuild','outputs_v293'):
        paths += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    paths += [ROOT/name for name in ('README.md','CURRENT_PIPELINE.md','pyproject.toml','uv.lock')]
    hashes={};unreadable=[]
    for p in paths:
        try:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
        except PermissionError:unreadable.append(p.relative_to(ROOT).as_posix())
    save('setup/preserved_state.json',{'created_unix':time.time(),'files':hashes,'unreadable':unreadable})
    import psutil
    hardware={'RAM':psutil.virtual_memory()._asdict(),'disk':shutil.disk_usage(ROOT)._asdict(),
        'GPU':subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,memory.free,driver_version','--format=csv,noheader'],text=True).strip(),
        'pagefile':'See hardware_windows.json; performance-counter swap API unavailable on this system.'}
    save('setup/hardware.json',hardware)
    save('setup/strata_version.json',{'repository':'https://github.com/Niko1221/Strata',
        'commit':subprocess.check_output(['git','-C',str(ROOT/'tools/Strata'),'rev-parse','HEAD'],text=True).strip(),
        'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()})
    print('Preserved',len(hashes),'files; unreadable',len(unreadable))
if __name__=='__main__':main()

import hashlib
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'outputs/validation'
VIDEOS = [f'val_{i}' for i in range(1, 12)]

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def read(path):
    path = Path(path)
    if path.parent == ROOT/'val_set' and path.suffix == '.txt':
        if not (OUT/'PREDICTION_FREEZE_COMPLETE.txt').is_file():
            raise RuntimeError('Ground truth is sealed')
    return json.loads(path.read_text(encoding='utf-8'))

def write(path, value):
    path = Path(path).resolve()
    if OUT.resolve() not in path.parents: raise ValueError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def source_hashes():
    paths = [* (ROOT/'src').rglob('*.py'), *(ROOT/'scripts').glob('*.py'), *(ROOT/'configs').rglob('*.yaml')]
    paths += list((ROOT/'.sam2_official/sam2').rglob('*.py'))
    paths += list((ROOT/'.sam2_official/sam2/configs').rglob('*.yaml'))
    paths += list((ROOT/'.models/Qwen2.5-VL-7B-Instruct').glob('*.json'))
    paths += [ROOT/'outputs_v24/reid_parameter_manifest.json',ROOT/'outputs_v24/cache/reid_parameter_manifest.sha256']
    return {p.relative_to(ROOT).as_posix():sha(p) for p in paths}

def check_sources():
    p=OUT/'pre_run_freeze_manifest.json'
    if p.exists():
        expected=read(p)['sources']; actual=source_hashes()
        if actual != expected: raise RuntimeError('Executable/config freeze changed')

def register():
    import cv2
    from memory_graph.reasoning.pipeline import verify_manifest
    check=verify_manifest(ROOT/'outputs/current_development',ROOT/'outputs/current_development/final/final_integrity_manifest.json')
    if not check['valid']: raise RuntimeError(check)
    dataset=ROOT/'val_set'; items=[]
    expected={v+s for v in VIDEOS for s in ('.mp4','.txt')}
    actual={p.name for p in dataset.iterdir() if p.is_file()}
    if actual != expected: raise RuntimeError({'unexpected':list(actual-expected),'missing':list(expected-actual)})
    for v in VIDEOS:
        p=dataset/(v+'.mp4'); gt=dataset/(v+'.txt'); cap=cv2.VideoCapture(str(p))
        if not cap.isOpened(): raise OSError(p)
        fps=cap.get(cv2.CAP_PROP_FPS); count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); code=int(cap.get(cv2.CAP_PROP_FOURCC))
        items.append({'validation_id':v,'video_path':str(p),'video_SHA256':sha(p),'size':p.stat().st_size,
            'codec':''.join(chr((code >> 8*i)&255) for i in range(4)),
            'resolution':[int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))],
            'FPS':fps,'duration':count/fps,'frame_count':count,
            'txt_path':str(gt),'txt_SHA256':sha(gt),'txt_size':gt.stat().st_size,'txt_content_read':False})
        cap.release()
    dev={p.name:sha(p) for p in ROOT.glob('test*.mp4')}
    collisions=[v['validation_id'] for v in items if v['video_SHA256'] in dev.values()]
    prior=[]
    # Inspect only output manifests/configs, never paired TXT semantics.
    for folder in ROOT.iterdir():
        if not folder.is_dir() or not folder.name.startswith('outputs'):continue
        for p in folder.rglob('*.json'):
            if OUT in p.parents or not any(s in p.name for s in ('manifest','config','inputs')):continue
            raw=p.read_text(encoding='utf-8',errors='replace')
            hits=[v['validation_id'] for v in items if v['video_SHA256'] in raw or v['video_path'] in raw or ('val_set/'+v['validation_id']+'.mp4') in raw]
            if hits:prior.append({'path':str(p),'videos':hits})
    write(OUT/'input_manifest.json',{'registered_unix':time.time(),'videos':items,'ground_truth_content_read':False})
    isolation={'valid':not collisions and not prior,'development_raw_hashes':dev,'raw_collisions':collisions,
        'prior_output_references':prior,'historical_integrity':check,'prior_access':'Earlier authorized directory listing only; no TXT/video semantic inspection.'}
    write(OUT/'data_isolation_check.json',isolation)
    if not isolation['valid']:raise RuntimeError(isolation)
    return items

class VideoRoot(type(Path())):
    """Keep model/provenance root, route only exact registered video filenames."""
    def __truediv__(self, key):
        if str(key) in {v+'.mp4' for v in VIDEOS}:return ROOT/'val_set'/str(key)
        return Path(str(self))/key

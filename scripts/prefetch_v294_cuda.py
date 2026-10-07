"""Exact official Strata pinned CUDA wheels, checked against PyPI SHA256."""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from download_v294_asset import download

ROOT = Path(__file__).resolve().parents[1]
provenance = []; paths = []
for package, version in [('nvidia-cublas', '13.0.2.14'), ('nvidia-cuda-runtime', '13.0.96')]:
    data = json.load(urllib.request.urlopen(f'https://pypi.org/pypi/{package}/{version}/json', timeout=20))
    asset = next(a for a in data['urls'] if a['filename'].endswith('win_amd64.whl'))
    path = ROOT/'tools/Strata/wheels'/asset['filename']
    download(asset['url'], path, asset['digests']['sha256'], asset['size'], workers=12, chunk_bytes=8*2**20)
    paths.append(path); provenance.append({k: asset[k] for k in ['filename', 'url', 'size', 'digests']})
(ROOT/'outputs/v294_qwen38/setup/cuda_assets.json').write_text(json.dumps(provenance, indent=2), encoding='utf8')
subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-index', '--no-deps', *map(str, paths)], check=True)

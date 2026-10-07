"""Prefetch the exact official setup Coder files; verified SHA256 before setup reuse."""
from pathlib import Path
import json
from download_v294_asset import download

ROOT = Path(__file__).resolve().parents[1]
assets = json.loads((ROOT/'outputs/v294_qwen38/setup/coder_assets.json').read_text())
for asset in assets['files']:
    if 'lfs' not in asset:
        continue
    name = Path(asset['rfilename']).name
    folder = ROOT/'tools/Strata-data/models'
    if asset['rfilename'].startswith('IQ1_M/'):
        folder /= 'coder-IQ1_M'
    destination = folder/name
    if destination.exists() and destination.with_name(name+'.verified.json').exists():
        continue
    url = f'https://huggingface.co/{assets["repository"]}/resolve/{assets["revision"]}/{asset["rfilename"]}'
    download(url, destination, asset['lfs']['sha256'], asset['size'], workers=8, chunk_bytes=32*2**20)
    destination.with_name(name+'.verified.json').write_text(json.dumps({'sha256': asset['lfs']['sha256'], 'size': asset['size'],
                                                                       'url': url, 'whole_file_verified': True}, indent=2), encoding='utf8')

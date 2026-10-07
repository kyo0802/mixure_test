"""Bounded HTTP range download of official assets, with a required whole-file SHA256."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def download(url, destination, expected_sha, size, workers=4, chunk_bytes=8*2**20):
    destination = Path(destination).resolve()
    if not destination.is_relative_to(ROOT/'tools'):
        raise ValueError('Assets must remain in this repository tools directory')
    if not (url.startswith('https://github.com/Niko1221/Strata/') or url.startswith('https://huggingface.co/')
            or url.startswith('https://files.pythonhosted.org/')):
        raise ValueError('Official asset URL required')
    if len(expected_sha) != 64 or any(c not in '0123456789abcdef' for c in expected_sha.lower()):
        raise ValueError('Trusted expected SHA256 required')
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name+'.ranges')
    checkpoint = destination.with_name(destination.name+'.ranges.json')
    state = {'url': url, 'size': size, 'sha256': expected_sha, 'chunk_bytes': chunk_bytes, 'done': []}
    if checkpoint.exists():
        old = json.loads(checkpoint.read_text())
        if any(old[k] != state[k] for k in ['url', 'size', 'sha256', 'chunk_bytes']):
            raise ValueError('Download checkpoint mismatch')
        state = old
    if not partial.exists():
        with partial.open('wb') as f:
            f.truncate(size)
        state['done'] = []
    lock = threading.Lock(); started = time.monotonic()
    def fetch(index):
        if index in state['done']:
            return
        lo = index*chunk_bytes; hi = min(size, lo+chunk_bytes)-1
        for attempt in range(5):
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'FindMind-V294-official-assets',
                                                               'Range': f'bytes={lo}-{hi}'})
                with urllib.request.urlopen(request, timeout=45) as response:
                    expected_range = f'bytes {lo}-{hi}/{size}'
                    if response.status != 206 or response.headers.get('Content-Range') != expected_range:
                        raise ValueError('Server did not honor exact range: '+str(response.headers.get('Content-Range')))
                    data = response.read(hi-lo+2)
                if len(data) != hi-lo+1:
                    raise ValueError('Incomplete range')
                with lock:
                    with partial.open('r+b') as f:
                        f.seek(lo); f.write(data); f.flush()
                    state['done'].append(index)
                    checkpoint.write_text(json.dumps(state), encoding='utf8')
                    print(f'{destination.name}: {len(state["done"])*chunk_bytes/1e9:.2f}/{size/1e9:.2f} GB; {time.monotonic()-started:.1f}s', flush=True)
                return
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(attempt+1)
    # Bound the queue as well as active connections; a network failure must not wait
    # for hundreds of already queued retries before the caller can resume.
    indices = iter(i for i in range((size+chunk_bytes-1)//chunk_bytes) if i not in state['done'])
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    pending = {pool.submit(fetch, i) for i in list(__import__('itertools').islice(indices, workers))}
    try:
        while pending:
            finished, pending = concurrent.futures.wait(pending, return_when=concurrent.futures.FIRST_COMPLETED)
            for future in finished:
                future.result()
                index = next(indices, None)
                if index is not None:
                    pending.add(pool.submit(fetch, index))
    except Exception:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        pool.shutdown(wait=True)
    h = hashlib.sha256()
    with partial.open('rb') as f:
        for block in iter(lambda: f.read(8*2**20), b''):
            h.update(block)
    if h.hexdigest() != expected_sha.lower():
        raise ValueError('Whole-file SHA256 mismatch: '+h.hexdigest())
    partial.replace(destination)
    print('VERIFIED SHA256', h.hexdigest(), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('url'); ap.add_argument('destination'); ap.add_argument('sha256'); ap.add_argument('size', type=int)
    ap.add_argument('--workers', type=int, default=4); ap.add_argument('--chunk-mib', type=int, default=8)
    a = ap.parse_args()
    download(a.url, a.destination, a.sha256, a.size, a.workers, a.chunk_mib*2**20)

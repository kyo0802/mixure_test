"""Internal Linux worker for a single isolated fresh-video session."""
import argparse
import os
from pathlib import Path
import site
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
ENTRY_MONOTONIC=time.monotonic()
sys.dont_write_bytecode=True
for key in ('HF_HOME','HF_MODULES_CACHE','TORCH_HOME','TRITON_CACHE_DIR','VLLM_CACHE_ROOT','XDG_CACHE_HOME'):
    path=ROOT/'.runtime/nemotron/cache'/key;path.mkdir(parents=True,exist_ok=True);os.environ[key]=str(path)
ipc=Path('/tmp/findmind_nemotron');ipc.mkdir(mode=0o700,exist_ok=True)
os.environ.update(TMPDIR=str(ipc),VLLM_RPC_BASE_PATH=str(ipc),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
    VLLM_WORKER_MULTIPROC_METHOD='spawn',TOKENIZERS_PARALLELISM='false',TORCH_COMPILE_DISABLE='1')
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'.runtime/nemotron/sitepackages_linux')]
site.addsitedir(str(ROOT/'.runtime/nemotron/sitepackages_linux'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--session',required=True);a=p.parse_args()
    session=Path(a.session).resolve()
    if not session.is_relative_to(ROOT/'artifacts/findmind_sessions'):raise PermissionError('ISOLATED_SESSION_REQUIRED')
    from memory_graph.integration.nemotron_video import run
    from memory_graph.integration.runtime_timing import Trace
    trace=Trace(session/'vlm/timing.jsonl','16853d6c682223e967d5622c99d0082cb994b771')
    trace.event('linux_launcher_ready',seconds=time.monotonic()-ENTRY_MONOTONIC,
        parent_launch_utc=os.environ.get('FINDMIND_WORKER_LAUNCH_UTC'),
        limitation='Cross-OS UTC boundary is approximate; durations within each process use monotonic clocks')
    run(ROOT,session)
    trace.event('linux_launcher_return_before_interpreter_shutdown')

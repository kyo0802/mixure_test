"""Internal Linux worker for a single isolated fresh-video session."""
import argparse
import os
from pathlib import Path
import site
import sys

ROOT=Path(__file__).resolve().parents[1]
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
    run(ROOT,session)

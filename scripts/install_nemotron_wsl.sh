#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Users/smile/Desktop/test2/mixure_test_SAM
export UV_CACHE_DIR="$PWD/.runtime/nemotron/uv_cache"
export UV_LINK_MODE=copy
export PIP_CACHE_DIR="$PWD/.runtime/nemotron/pip_cache"
export TMPDIR="$PWD/.runtime/nemotron/tmp"
mkdir -p .runtime/nemotron/bin "$TMPDIR"
if [ ! -f .runtime/nemotron/bin/uv ]; then
  curl -L --fail https://github.com/astral-sh/uv/releases/download/0.9.7/uv-x86_64-unknown-linux-gnu.tar.gz -o .runtime/nemotron/uv.tar.gz
  tar -xzf .runtime/nemotron/uv.tar.gz -C .runtime/nemotron/bin --strip-components=1
fi
.runtime/nemotron/bin/uv venv --python /usr/bin/python3 .runtime/nemotron/venv_linux
version=$(python3 -c 'import json;print(json.load(open("artifacts/pass_t/phase3/three_vlm_full_v1/nemotron_download.json"))["vllm_version"])')
.runtime/nemotron/bin/uv pip install --python .runtime/nemotron/venv_linux/bin/python "vllm==$version" pillow
.runtime/nemotron/venv_linux/bin/python -c 'import torch,vllm;print("INSTALLED",torch.__version__,vllm.__version__);print(torch.cuda.get_device_name(),torch.cuda.get_device_capability())'

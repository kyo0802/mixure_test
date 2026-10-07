"""Version-aware, write-once cache keys for isolated v2.10.1 experiments."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


IDENTITY_FIELDS = (
    "source_git_sha",
    "model_revision",
    "model_config_sha256",
    "threshold_config_sha256",
    "input_media_sha256",
    "producer_version",
)

VLM_FIELDS = IDENTITY_FIELDS + (
    "processor_revision",
    "inference_engine",
    "inference_engine_version",
    "quantization",
    "cache_dtype",
    "prompt_sha256",
    "schema_sha256",
    "media_preprocessing_sha256",
    "frame_sampling_config",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def cache_key(kind: str, fields: Mapping[str, Any]) -> str:
    """Return a SHA-256 key after validating every dependency field."""
    if kind not in {"identity_perception", "vlm"}:
        raise ValueError(f"unsupported cache kind: {kind}")
    required = IDENTITY_FIELDS if kind == "identity_perception" else VLM_FIELDS
    missing = [name for name in required if name not in fields]
    if missing:
        raise ValueError(f"missing {kind} cache dependencies: {', '.join(missing)}")
    payload = {"schema": f"v2101:{kind}:1", "dependencies": {name: fields[name] for name in required}}
    return hashlib.sha256(_canonical(payload)).hexdigest()


def cache_path(root: str | Path, kind: str, fields: Mapping[str, Any]) -> Path:
    return Path(root) / kind / f"{cache_key(kind, fields)}.json"


def write_cache_entry_once(path: str | Path, payload: Mapping[str, Any]) -> Path:
    """Create a cache entry without ever replacing a valid existing entry."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    body = _canonical(payload) + b"\n"
    with destination.open("xb") as stream:
        stream.write(body)
        stream.flush()
    return destination

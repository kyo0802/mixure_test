"""Small deterministic helpers shared only inside Phase 2b."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


class Phase2BBlocked(ValueError):
    """A hard Phase 2b contract gate failed."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def pretty_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise Phase2BBlocked(f"INVALID_JSON:{path}:{error}") from error
    if not isinstance(value, dict):
        raise Phase2BBlocked(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def safe_join(base: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative or "\x00" in relative:
        raise Phase2BBlocked("UNSAFE_RELATIVE_PATH")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in relative.split("/")):
        raise Phase2BBlocked("UNSAFE_RELATIVE_PATH")
    target = base.resolve() / relative
    if not target.resolve().is_relative_to(base.resolve()):
        raise Phase2BBlocked("PATH_OUTSIDE_ROOT")
    return target


def exclusive_tree(base: Path, files: dict[str, bytes], receipt: dict) -> Path:
    """Create an immutable, content-addressed artifact tree."""
    manifest = {name: digest(raw) for name, raw in sorted(files.items())}
    key = digest(canonical_bytes({"files_sha256": manifest, "receipt": receipt}))
    destination = base / key
    full_receipt = {**receipt, "content_id": key, "files_sha256": manifest}
    expected = {**files, "completion_receipt.json": pretty_bytes(full_receipt)}
    if destination.exists():
        actual = {p.relative_to(destination).as_posix(): p.read_bytes() for p in destination.rglob("*") if p.is_file()}
        if actual != expected:
            raise Phase2BBlocked("CONTENT_ADDRESSED_ARTIFACT_CONFLICT")
        return destination
    destination.mkdir(parents=True, exist_ok=False)
    for name, raw in expected.items():
        path = safe_join(destination, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
        try:
            path.chmod(0o444)
        except OSError:
            pass
    return destination


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def environment_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


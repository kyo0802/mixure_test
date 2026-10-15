"""Capture a Phase 2b preservation baseline without mutating protected assets."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/pass_t/phase2b/preflight"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def main() -> None:
    protected_roots = [
        ROOT / "artifacts/pass_t/phase2a/v2",
        ROOT / "annotation_handoff/pass_t_phase2a_v2",
    ]
    files: dict[str, str] = {}
    for base in protected_roots:
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            files[path.relative_to(ROOT).as_posix()] = sha256(path)
    for relative in (
        "artifacts/pass_t/manifests/window_target_mapping.json",
        "artifacts/pass_t/manifests/human_seed_outcomes_v1.json",
        "artifacts/pass_t/manifests/binding_causal_lineage_v1.json",
    ):
        path = ROOT / relative
        files[relative] = sha256(path)
    payload = {
        "schema_version": "PASS_T_PHASE2B_PRESERVATION_BASELINE_V1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": git("rev-parse", "HEAD"),
        "git_diff_sha256": hashlib.sha256(git("diff", "--binary").encode("utf-8")).hexdigest(),
        "git_cached_diff_sha256": hashlib.sha256(git("diff", "--cached", "--binary").encode("utf-8")).hexdigest(),
        "protected_file_count": len(files),
        "protected_files_sha256": files,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT / "protected_before.json"
    if destination.exists():
        raise SystemExit("Phase 2b preservation baseline already exists; refusing to overwrite")
    destination.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(destination), "protected_file_count": len(files), "git_head": payload["git_head"]}))


if __name__ == "__main__":
    main()

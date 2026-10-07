from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAG = "v2.9.7-frozen"
MANIFEST = ROOT / "outputs/v297_physical_identity/FROZEN_V297_POLICY_MANIFEST.json"


def run(*args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source_hashes = manifest["source_hashes"]
    current_tag_commit = run("rev-parse", f"{TAG}^{{commit}}")
    for relative, expected in source_hashes.items():
        path = ROOT / relative
        if not path.is_file() or sha_file(path) != expected:
            raise SystemExit(f"Refusing to freeze: V297 source does not match recorded SHA-256: {relative}")

    index_path = ROOT / "artifacts/v2.10.1/freeze" / f".temporary-index-{uuid.uuid4().hex}"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    old_index = os.environ.get("GIT_INDEX_FILE")
    try:
        os.environ["GIT_INDEX_FILE"] = str(index_path)
        run("read-tree", current_tag_commit)
        for relative in sorted(source_hashes):
            blob = run("hash-object", "-w", "--", str(ROOT / relative))
            # Remove any parent-tree entry before inserting the frozen worktree blob.
            # update-index --add alone can otherwise preserve an existing index entry.
            run("update-index", "--force-remove", relative, check=False)
            run("update-index", "--add", "--cacheinfo", f"100644,{blob},{relative}")
        tree = run("write-tree")
        commit = run("commit-tree", tree, "-p", current_tag_commit,
                     "-m", "Complete the frozen V2.9.7 source dependency snapshot")
        # This tag was created locally for the current v2.10.1 task and has not been pushed.
        run("tag", "-f", "-a", TAG, commit,
            "-m", "FindMind v2.9.7 frozen source baseline with all manifest-pinned source dependencies")
        print("previous_tag_commit", current_tag_commit)
        print("completed_freeze_commit", commit)
        print("annotated_tag_object", run("rev-parse", TAG))
        print("source_dependency_count", len(source_hashes))
        print("branch_unchanged", run("branch", "--show-current"))
    finally:
        if old_index is None:
            os.environ.pop("GIT_INDEX_FILE", None)
        else:
            os.environ["GIT_INDEX_FILE"] = old_index
        if index_path.exists():
            index_path.unlink()


if __name__ == "__main__":
    main()

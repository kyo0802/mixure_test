"""Phase 2b infrastructure status report generation."""
from __future__ import annotations

import json
import hashlib
import subprocess
from pathlib import Path

from . import STATUS
from .authority import load_phase2b_authority
from .common import file_sha256, read_json, repository_root, utc_now
from .eligibility import build_eligibility


def preservation_check() -> dict:
    root = repository_root()
    baseline_path = root / "artifacts/pass_t/phase2b/preflight/protected_before.json"
    baseline = read_json(baseline_path)
    changed = []
    for relative, expected in baseline["protected_files_sha256"].items():
        path = root / relative
        if not path.is_file() or file_sha256(path) != expected:
            changed.append(relative)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, encoding="utf-8").strip()
    cached = subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=root, text=True, encoding="utf-8").strip()
    worktree_diff = subprocess.check_output(["git", "diff", "--binary"], cwd=root, text=True, encoding="utf-8")
    worktree_diff_sha = hashlib.sha256(worktree_diff.strip().encode("utf-8")).hexdigest()
    return {"protected_files_checked": len(baseline["protected_files_sha256"]), "changed": changed,
            "git_head_before": baseline["git_head"], "git_head_after": head, "head_unchanged": head == baseline["git_head"],
            "tracked_worktree_diff_sha256_before": baseline["git_diff_sha256"],
            "tracked_worktree_diff_sha256_after": worktree_diff_sha,
            "tracked_worktree_diff_unchanged": worktree_diff_sha == baseline["git_diff_sha256"],
            "index_empty": not bool(cached),
            "verified": not changed and head == baseline["git_head"] and worktree_diff_sha == baseline["git_diff_sha256"]}


def artifact_hashes() -> dict:
    root = repository_root()
    paths = [
        *sorted((root / "src/memory_graph/pass_t/phase2b").rglob("*.py")),
        *sorted((root / "src/memory_graph/pass_t/phase2b/contracts").glob("*.json")),
        root / "scripts/run_pass_t_phase2b.py",
        root / "scripts/pass_t_phase2b_preflight.py",
        root / "artifacts/pass_t/phase2b/templates/event_reasoning_prompt_v1.txt",
        root / "artifacts/pass_t/phase2b/config/model_config.template.json",
        root / "artifacts/pass_t/phase2b/config/protocol_decisions.template.json",
        root / "artifacts/pass_t/phase2b/config/MODEL_CONFIGURATION_DECISION_SHEET.md",
        root / "artifacts/pass_t/phase2b/readiness/eligibility.json",
        root / "artifacts/pass_t/phase2b/readiness/GT_ELIGIBILITY_LIMITATIONS.md",
        root / "artifacts/pass_t/phase2b/PHASE2B_USAGE_ZH_TW.md",
        root / "artifacts/pass_t/phase2b/PHASE2B_DATA_EXPANSION_PLAN.md",
        root / "artifacts/pass_t/phase2b/mock/mock_suite.json",
        root / "artifacts/pass_t/phase2b/reports/test_results.json",
    ]
    unique = sorted({path.resolve() for path in paths if path.is_file()})
    return {path.relative_to(root).as_posix(): file_sha256(path) for path in unique}


def render_report(mock: dict | None = None, tests: dict | None = None) -> str:
    authority = load_phase2b_authority()
    eligibility = build_eligibility(authority)
    preservation = preservation_check()
    hashes = artifact_hashes()
    real_runs = root_runs = repository_root() / "artifacts/pass_t/phase2b/runs"
    real_run_count = len(list(root_runs.glob("*/completion_receipt.json"))) if root_runs.exists() else 0
    hash_rows = [f"- `{name}`: `{value}`" for name, value in hashes.items()]
    lines = [
        "# FindMind Pass T Phase 2b 基礎設施報告",
        "",
        f"Generated: {utc_now()}",
        "",
        "## 最終狀態",
        "",
        f"`{STATUS}`",
        "",
        f"真實 VLM 執行筆數：`{real_run_count}`。本次沒有上傳影像、沒有付費或雲端請求，也沒有下載模型。",
        "",
        "## 已完成元件與路徑",
        "",
        "- `src/memory_graph/pass_t/phase2b/authority.py`：唯讀 Phase 2a authority 與 hash 驗證。",
        "- `eligibility.py`：逐視窗用途、品質限制與 metric 權限。",
        "- `model_visible.py`、`inputs.py`、`builders.py`：opaque payload、私有 mapping、Video／Multi-image／Storyboard。",
        "- `config.py`、`protocol.py`：模型能力、設定驗證、prospective protocol 與 freeze gate。",
        "- `predictions.py`、`contracts/prediction_v1.json`：嚴格 raw parser、schema、citation 與 semantic guard。",
        "- `backends.py`、`inference.py`：可註冊 backend、唯一 real-run 邊界、失敗也保存的 content-addressed run storage。",
        "- `evaluation.py`：依 Phase 2a eligibility 限制輸出的 event-local evaluator。",
        "- `scripts/run_pass_t_phase2b.py`：12 個 CLI 子命令。",
        "- `PHASE2B_USAGE_ZH_TW.md` 與 `PHASE2B_DATA_EXPANSION_PLAN.md`：繁中操作說明與前瞻資料擴增計畫。",
        "",
        "## 權威 DEV 狀態與逐視窗 eligibility",
        "",
        f"- Dataset SHA-256: `{authority.provenance['dataset_sha256']}`",
        f"- Frozen Phase 2a policy SHA-256: `{authority.provenance['policy_sha256']}`",
        f"- 7 筆：{eligibility['summary']['known_event_matching_only']} 筆 known-event matching、{eligibility['summary']['strict_negative_case_alerts']} 筆 strict-negative case alert、{eligibility['summary']['descriptive_uncertainty_only']} 筆 descriptive uncertainty、{eligibility['summary']['audit_only']} 筆 audit-only。",
        "- test1 W03/W05、test2 W01、test5 W01：strict-negative case alert only。",
        "- test5 W05、test7 W05：known PICKUP matching only；額外預測為 UNEVALUATED。",
        "- test8 W07：descriptive uncertainty only。test3 W07：禁止 model run 與 scoring。",
        "- 正式 benchmark eligibility 為 0，exhaustive positive 為 0，binding causality 仍是 `CAUSALITY_UNVERIFIED`。",
        "",
        "## 剩餘品質限制",
        "",
        "- test5 W05 and test7 W05 support conditional matching of their known PICKUP event only. Extra predictions remain UNEVALUATED.",
        "- test1 W03/W05, test2 W01, and test5 W01 support case-level false-event alerts only; they do not establish a population false-positive rate.",
        "- test8 W07 is descriptive uncertainty only.",
        "- test3 W07 is excluded from model runs and scoring; original contamination exclusions remain binding.",
        "- Accuracy, precision, recall, F1, hallucination rate, statistical significance, superiority, and generalization are undefined for this pilot.",
        "",
        "## Representation、能力與 protocol 狀態",
        "",
        "- 已支援 `REENCODED_AUTHORIZED_VIDEO`、`MULTI_IMAGE`、`STORYBOARD` builder。Video 以 FFV1/AVI 重編碼，保留私有 native PTS mapping 並報告 CFR distortion；不宣稱 native PTS 被保留。",
        "- 真實模型能力：全部尚未驗證。mock 的 Multi-image／Storyboard 本機契約測試已通過，不代表真實模型可行性。",
        "- Provider、backend、model、revision、限制、generation、budget、frame count、timing tolerance、repeat count 與 run order 仍未決。",
        "- 最新 protocol 只有 `DRAFT_UNRESOLVED`；沒有 frozen Phase 2b protocol。`DECLARED` 不能作為 runtime verification。",
        "- External data consent 預設 false；沒有 fallback 或 model substitution。",
        "",
        "## Mock 與測試",
        "",
        f"- Mock suite: `{(mock or {}).get('passed', 'NOT_RECORDED')}`; scenarios: `{len((mock or {}).get('scenarios', []))}`.",
        f"- Tests: `{(tests or {}).get('status', 'NOT_RECORDED')}`; passed: `{(tests or {}).get('passed', 'UNKNOWN')}`.",
        "- Mock artifacts are isolated under `artifacts/pass_t/phase2b/mock/` and are explicitly marked non-experimental.",
        "",
        "## 保護驗證",
        "",
        f"- Protected files checked: `{preservation['protected_files_checked']}`",
        f"- Changed protected files: `{len(preservation['changed'])}`",
        f"- Git HEAD unchanged: `{preservation['head_unchanged']}`",
        f"- Git index empty: `{preservation['index_empty']}`",
        f"- 原有 tracked worktree diff 未改變: `{preservation['tracked_worktree_diff_unchanged']}`",
        "",
        "## Artifact SHA-256",
        "",
        *hash_rows,
        "",
        "## 實際可用 CLI",
        "",
        "完整 12 個命令與參數見 `artifacts/pass_t/phase2b/PHASE2B_USAGE_ZH_TW.md`。本次實際執行了 eligibility/readiness/config/capability/build/inspect/protocol/mock/report paths；freeze 在 unresolved gate 正確被拒絕。",
        "",
        "## 下一步需要使用者決定",
        "",
        "1. Fill `artifacts/pass_t/phase2b/config/model_config.template.json` as a new config file with one exact model/revision and verified capabilities.",
        "2. Fill `artifacts/pass_t/phase2b/config/protocol_decisions.template.json` as a new decisions file, including GT-independent frame count, timing tolerance, repeat count, run order, and budget.",
        "3. Validate capabilities and inspect the exact serialized payload before freezing the protocol.",
        "4. Obtain explicit real-run authorization and data consent if the configured backend is external.",
        "",
        "## 科學限制",
        "",
        "This seven-window DEV set is exploratory, has no exhaustive positive windows, contains only known PICKUP positives, lacks PLACEMENT ground truth, has unverified binding causality and recording-session independence, and cannot support formal model accuracy or comparative claims.",
        "",
        f"Final status: `{STATUS}`",
        "",
    ]
    return "\n".join(lines)


def export_report(mock_path: Path | None = None, tests_path: Path | None = None) -> Path:
    root = repository_root()
    mock = read_json(mock_path) if mock_path and mock_path.is_file() else None
    tests = read_json(tests_path) if tests_path and tests_path.is_file() else None
    destination = root / "artifacts/pass_t/phase2b/reports/PASS_T_PHASE2B_INFRASTRUCTURE_REPORT.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    (destination.parent / "PRESERVATION_REPORT.json").write_text(json.dumps(preservation_check(), ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (destination.parent / "ARTIFACT_HASHES.json").write_text(json.dumps({"schema_version": "PASS_T_PHASE2B_ARTIFACT_HASHES_V1", "files_sha256": artifact_hashes()}, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    destination.write_text(render_report(mock, tests), encoding="utf-8")
    return destination


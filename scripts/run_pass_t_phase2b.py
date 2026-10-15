"""Command line interface for isolated Pass T Phase 2b infrastructure."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_BOOT_ROOT = Path(__file__).resolve().parents[1]
for _relative in ("src", "artifacts/pass_i/runtime/vendor", "outputs/current_development/video_event_experiment/.deps"):
    _candidate = str(_BOOT_ROOT / _relative)
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from memory_graph.pass_t.phase2b.authority import load_phase2b_authority
from memory_graph.pass_t.phase2b.common import Phase2BBlocked, exclusive_tree, pretty_bytes, read_json, repository_root
from memory_graph.pass_t.phase2b.common import digest
from memory_graph.pass_t.phase2b.config import check_capabilities, require_valid, validate_config
from memory_graph.pass_t.phase2b.eligibility import build_eligibility, by_id
from memory_graph.pass_t.phase2b.evaluation import evaluate_item, summarize_evaluations
from memory_graph.pass_t.phase2b.inference import run_real_pilot
from memory_graph.pass_t.phase2b.inputs import build_input_package, load_package
from memory_graph.pass_t.phase2b.mocks import run_mock_suite
from memory_graph.pass_t.phase2b.model_visible import inspect_payload
from memory_graph.pass_t.phase2b.protocol import freeze_protocol, prepare_protocol
from memory_graph.pass_t.phase2b.reporting import export_report, preservation_check


ROOT = repository_root()


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pretty_bytes(value))


def authority_and_eligibility():
    authority = load_phase2b_authority()
    return authority, build_eligibility(authority)


def check_eligibility(args):
    _, eligibility = authority_and_eligibility()
    if args.output:
        write_json(Path(args.output), eligibility)
    emit(eligibility)


def inspect_readiness(args):
    authority, eligibility = authority_and_eligibility()
    emit({"status": "READY_FOR_CONFIGURATION_NOT_INFERENCE", "authority": authority.provenance,
          "eligibility_summary": eligibility["summary"], "metric_policy": eligibility["metric_policy"],
          "preservation": preservation_check()})


def validate_config_cmd(args):
    config = read_json(Path(args.config))
    emit(validate_config(config, real_run=args.real_run))


def check_capabilities_cmd(args):
    emit(check_capabilities(read_json(Path(args.config))))


def build_inputs_cmd(args):
    authority, eligibility = authority_and_eligibility()
    config = read_json(Path(args.config))
    require_valid(config)
    capability = check_capabilities(config)
    selected = args.representations.split(",")
    if any(rep not in capability["verified_representations"] for rep in selected):
        raise Phase2BBlocked("REQUESTED_REPRESENTATION_NOT_VERIFIED")
    row = by_id(eligibility).get(args.item_id)
    if row is None or row["pilot_scoring_permission"] == "AUDIT_ONLY_NO_MODEL_RUN":
        raise Phase2BBlocked("ITEM_NOT_PERMITTED_FOR_PILOT_INPUT")
    secret = os.environ.get("PASS_T_PHASE2B_OPAQUE_SECRET")
    if not secret or len(secret) < 16:
        raise Phase2BBlocked("PASS_T_PHASE2B_OPAQUE_SECRET_MIN_16_CHARS_REQUIRED")
    prompt = (ROOT / "artifacts/pass_t/phase2b/templates/event_reasoning_prompt_v1.txt").read_text(encoding="utf-8")
    folder = build_input_package(authority.items[args.item_id], secret=secret, prompt_text=prompt,
                                 representations=selected, frame_count=args.frame_count,
                                 storyboard_columns=args.storyboard_columns, video_fps=args.video_fps,
                                 reference_policy=config["reference_policy"])
    emit({"status": "INPUTS_BUILT_NO_INFERENCE", "path": str(folder), "content_id": folder.name})


def inspect_payload_cmd(args):
    package = load_package(Path(args.package))
    rows = {}
    for rep, value in package["representations"].items():
        rows[rep] = inspect_payload(value["payload"], package["private"]["source_contract"])
    emit({"safe": all(row["safe"] for row in rows.values()), "representations": rows})


def prepare_protocol_cmd(args):
    _, eligibility = authority_and_eligibility()
    protocol = prepare_protocol(read_json(Path(args.config)), eligibility, read_json(Path(args.decisions)))
    folder = exclusive_tree(ROOT / "artifacts/pass_t/phase2b/protocol_drafts", {"protocol.json": pretty_bytes(protocol)},
                            {"schema_version": "PASS_T_PHASE2B_PROTOCOL_DRAFT_RECEIPT_V1", "status": protocol["status"]})
    emit({"status": protocol["status"], "path": str(folder), "unresolved_fields": protocol["unresolved_fields"]})


def freeze_protocol_cmd(args):
    protocol = read_json(Path(args.draft) / "protocol.json")
    folder = freeze_protocol(protocol)
    emit({"status": "FROZEN", "path": str(folder), "content_id": folder.name})


def mock_cmd(args):
    result = run_mock_suite()
    destination = ROOT / "artifacts/pass_t/phase2b/mock/mock_suite.json"
    write_json(destination, result)
    folder = exclusive_tree(ROOT / "artifacts/pass_t/phase2b/mock/suites", {"mock_suite.json": pretty_bytes(result)},
                            {"schema_version": "PASS_T_PHASE2B_MOCK_SUITE_RECEIPT_V1", "mock_only": True})
    emit({**result, "content_addressed_path": str(folder)})


def run_pilot_cmd(args):
    packages = []
    for folder_name in args.input_package:
        folder = Path(folder_name)
        loaded = load_package(folder)
        for rep, value in loaded["representations"].items():
            media_folder = folder / f"model_visible/{rep}/media"
            blobs = [path.read_bytes() for path in media_folder.iterdir() if path.is_file()]
            by_hash = {digest(blob): blob for blob in blobs}
            media_bytes = {row["media_id"]: by_hash[row["content_sha256"]] for row in value["payload"]["media"]}
            packages.append({"payload": value["payload"], "private_mapping": loaded["private"], "media_bytes": media_bytes})
    result = run_real_pilot(protocol_folder=Path(args.protocol), packages=packages,
                            confirmation=args.confirm_exact, run_permission=args.allow_real_run)
    emit({"status": "REAL_PILOT_COMPLETE", "path": str(result)})


def evaluate_cmd(args):
    authority, eligibility = authority_and_eligibility()
    elig = by_id(eligibility)
    protocol = read_json(Path(args.protocol) / "protocol.json")
    run_folder = Path(args.run)
    run_data = read_json(run_folder / "run_manifest.json")["runs"]
    inputs = [load_package(Path(path)) for path in args.input_package]
    package_by_request = {(value["payload"]["request_id"], rep): (package, rep, value)
                          for package in inputs for rep, value in package["representations"].items()}
    rows = []
    for run in run_data:
        if run["status"] != "VALID_PREDICTION":
            continue
        request = read_json(run_folder / f"per_run/{run['run_id']}/request.json")
        prediction = read_json(run_folder / f"per_run/{run['run_id']}/parsed_prediction.json")
        package, rep, value = package_by_request[(request["request_id"], request["representation"])]
        item_id = package["private"]["source_contract"]["private_annotation_item_id"]
        representation = {**value["private"], "private_mapping": value["private"].get("private_mapping", value["private"].get("temporal_mapping", {}).get("private_mapping", []))}
        rows.append(evaluate_item(authority.records[item_id], elig[item_id], prediction, representation, protocol["decisions"]))
    summary = summarize_evaluations(rows)
    folder = exclusive_tree(ROOT / "artifacts/pass_t/phase2b/evaluations", {"evaluation.json": pretty_bytes(summary)},
                            {"schema_version": "PASS_T_PHASE2B_EVALUATION_RECEIPT_V1", "run_content_id": Path(args.run).name})
    emit({"status": "EVALUATED_WITH_ELIGIBILITY_LIMITS", "path": str(folder), "counts": summary["counts"]})


def report_cmd(args):
    path = export_report(Path(args.mock) if args.mock else None, Path(args.tests) if args.tests else None)
    emit({"status": "REPORT_EXPORTED", "path": str(path)})


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(required=True)
    p = commands.add_parser("check-eligibility"); p.add_argument("--output"); p.set_defaults(func=check_eligibility)
    p = commands.add_parser("inspect-readiness"); p.set_defaults(func=inspect_readiness)
    p = commands.add_parser("validate-config"); p.add_argument("--config", required=True); p.add_argument("--real-run", action="store_true"); p.set_defaults(func=validate_config_cmd)
    p = commands.add_parser("check-capabilities"); p.add_argument("--config", required=True); p.set_defaults(func=check_capabilities_cmd)
    p = commands.add_parser("build-inputs"); p.add_argument("--config", required=True); p.add_argument("--item-id", required=True); p.add_argument("--representations", required=True); p.add_argument("--frame-count", type=int, required=True); p.add_argument("--storyboard-columns", type=int, required=True); p.add_argument("--video-fps", type=float, required=True); p.set_defaults(func=build_inputs_cmd)
    p = commands.add_parser("inspect-model-payload"); p.add_argument("--package", required=True); p.set_defaults(func=inspect_payload_cmd)
    p = commands.add_parser("prepare-protocol"); p.add_argument("--config", required=True); p.add_argument("--decisions", required=True); p.set_defaults(func=prepare_protocol_cmd)
    p = commands.add_parser("freeze-protocol"); p.add_argument("--draft", required=True); p.set_defaults(func=freeze_protocol_cmd)
    p = commands.add_parser("run-mock-tests"); p.set_defaults(func=mock_cmd)
    p = commands.add_parser("run-pilot"); p.add_argument("--protocol", required=True); p.add_argument("--input-package", action="append", required=True); p.add_argument("--confirm-exact", required=True); p.add_argument("--allow-real-run", action="store_true"); p.set_defaults(func=run_pilot_cmd)
    p = commands.add_parser("evaluate-pilot"); p.add_argument("--protocol", required=True); p.add_argument("--run", required=True); p.add_argument("--input-package", action="append", required=True); p.set_defaults(func=evaluate_cmd)
    p = commands.add_parser("export-report"); p.add_argument("--mock"); p.add_argument("--tests"); p.set_defaults(func=report_cmd)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        args.func(args)
        return 0
    except Phase2BBlocked as error:
        emit({"status": "BLOCKED", "reason": str(error)})
        return 2


if __name__ == "__main__":
    sys.exit(main())

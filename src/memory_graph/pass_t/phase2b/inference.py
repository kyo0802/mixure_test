"""Pilot execution gate and immutable run storage."""
from __future__ import annotations

from pathlib import Path
import time

from .backends import real_backend
from .common import Phase2BBlocked, digest, environment_bool, exclusive_tree, pretty_bytes, repository_root, utc_now
from .config import require_valid
from .model_visible import inspect_payload, serialized_request
from .predictions import parse_and_validate
from .protocol import verify_frozen_protocol


EXACT_CONFIRMATION = "RUN_PHASE2B_EXPLORATORY_PILOT"


def run_real_pilot(*, protocol_folder: Path, packages: list[dict], confirmation: str, run_permission: bool,
                   output_base: Path | None = None) -> Path:
    """The sole code path permitted to call a real provider backend."""
    protocol = verify_frozen_protocol(protocol_folder)
    config = protocol["model_config"]
    require_valid(config, real_run=True)
    if confirmation != EXACT_CONFIRMATION or not run_permission or not environment_bool("PASS_T_PHASE2B_REAL_RUN_PERMISSION"):
        raise Phase2BBlocked("EXPLICIT_REAL_RUN_PERMISSION_REQUIRED")
    if config["execution_location"] == "EXTERNAL" and config["external_data_consent"] is not True:
        raise Phase2BBlocked("EXTERNAL_DATA_CONSENT_REQUIRED")
    budget = config["transport"]["monetary_budget_usd"]
    if budget is None or budget < 0 or budget > protocol["decisions"]["budget_limit_usd"]:
        raise Phase2BBlocked("BUDGET_GATE_FAILED")
    expected_items = set(protocol["decisions"]["pilot_item_ids"])
    actual_items = {package.get("private_mapping", {}).get("source_contract", {}).get("private_annotation_item_id") for package in packages}
    if actual_items != expected_items:
        raise Phase2BBlocked("SELECTED_WINDOW_INVENTORY_MISMATCH")
    expected_representations = set(protocol["decisions"]["run_order"])
    actual_representations = {package.get("payload", {}).get("representation") for package in packages}
    if actual_representations != expected_representations:
        raise Phase2BBlocked("SELECTED_REPRESENTATION_INVENTORY_MISMATCH")
    expected_pairs = {(item, rep) for item in expected_items for rep in expected_representations}
    actual_pairs = {(package["private_mapping"]["source_contract"]["private_annotation_item_id"], package["payload"]["representation"]) for package in packages}
    if actual_pairs != expected_pairs or len(packages) != len(expected_pairs):
        raise Phase2BBlocked("ITEM_REPRESENTATION_MATRIX_MISMATCH")
    for package in packages:
        payload = package["payload"]
        media = package.get("media_bytes", {})
        if set(media) != {row["media_id"] for row in payload["media"]}:
            raise Phase2BBlocked("MODEL_MEDIA_INVENTORY_MISMATCH")
        if any(digest(media[row["media_id"]]) != row["content_sha256"] for row in payload["media"]):
            raise Phase2BBlocked("MODEL_MEDIA_HASH_MISMATCH")
        private = package["private_mapping"]
        if private["source_contract"]["reference_policy"] != protocol["decisions"]["reference_policy"]:
            raise Phase2BBlocked("REFERENCE_POLICY_MISMATCH")
        representation = payload["representation"]
        rep_private = private["representations"][representation]
        if representation in {"MULTI_IMAGE", "STORYBOARD"}:
            decision = "multi_image_frame_count" if representation == "MULTI_IMAGE" else "storyboard_frame_count"
            if rep_private["selection_policy"]["requested_count"] != protocol["decisions"][decision]:
                raise Phase2BBlocked("FRAME_SELECTION_BUDGET_MISMATCH")
        if representation == "REENCODED_AUTHORIZED_VIDEO" and rep_private["encoding"]["fps"] != protocol["decisions"]["video_fps"]:
            raise Phase2BBlocked("VIDEO_FPS_MISMATCH")
    backend = real_backend(config)
    run_rows = []
    files = {}
    repeat_count = int(protocol["decisions"]["repeat_count"])
    for package in packages:
        payload = package["payload"]
        inspection = inspect_payload(payload, package.get("private_mapping"))
        if not inspection["safe"]:
            raise Phase2BBlocked("MODEL_PAYLOAD_INSPECTION_FAILED")
        request_raw = serialized_request(payload)
        if digest(payload["instructions"].encode("utf-8")) != protocol["prompt_sha256"]:
            raise Phase2BBlocked("PROMPT_HASH_MISMATCH")
        for repeat_index in range(repeat_count):
            run_id = digest(request_raw + f"|{repeat_index}|{backend.name}".encode("utf-8"))[:24]
            raw = b""; prediction = None; validation = None; failure = None; attempts = []
            started = time.perf_counter()
            for attempt_index in range(int(config["transport"]["max_retries"]) + 1):
                attempt_started = time.perf_counter()
                raw = b""; failure = None
                try:
                    raw = backend.invoke(payload, package["media_bytes"], float(config["transport"]["timeout_seconds"]))
                    aliases = [alias for row in payload["media"] for alias in row["supplied_frame_aliases"]]
                    prediction, validation = parse_and_validate(raw, list(dict.fromkeys(aliases)))
                except Exception as error:
                    failure = {"type": type(error).__name__, "message": str(error)}
                attempt = {"attempt_index": attempt_index, "runtime_seconds": time.perf_counter() - attempt_started,
                           "status": "VALID_PREDICTION" if prediction is not None else "FAILED_RECORDED", "failure": failure}
                attempts.append(attempt)
                attempt_prefix = f"per_run/{run_id}/attempt_{attempt_index:02d}"
                files[f"{attempt_prefix}/raw_output.txt"] = raw
                files[f"{attempt_prefix}/metadata.json"] = pretty_bytes(attempt)
                if prediction is not None:
                    files[f"{attempt_prefix}/parsed_prediction.json"] = pretty_bytes(prediction)
                    files[f"{attempt_prefix}/validation.json"] = pretty_bytes(validation)
                    break
                files[f"{attempt_prefix}/failure.json"] = pretty_bytes(failure)
            runtime = time.perf_counter() - started
            metadata = {
                "run_id": run_id, "protocol_content_id": protocol_folder.name,
                "model": config["model"], "revision": config["revision"], "backend": backend.name,
                "representation": payload["representation"], "opaque_item_id": payload["request_id"],
                "payload_sha256": digest(request_raw), "prompt_sha256": protocol["prompt_sha256"],
                "generation": config["generation"], "repeat_index": repeat_index,
                "attempts": attempts,
                "runtime_seconds": runtime, "cost": {"value": "UNAVAILABLE", "currency": "USD"},
                "status": "VALID_PREDICTION" if prediction is not None else "FAILED_RECORDED",
                "failure": failure,
            }
            prefix = f"per_run/{run_id}"
            files[f"{prefix}/request.json"] = request_raw
            files[f"{prefix}/metadata.json"] = pretty_bytes(metadata)
            if prediction is not None:
                files[f"{prefix}/parsed_prediction.json"] = pretty_bytes(prediction)
                files[f"{prefix}/validation.json"] = pretty_bytes(validation)
            run_rows.append(metadata)
    files["run_manifest.json"] = pretty_bytes({"schema_version": "PASS_T_PHASE2B_RUN_MANIFEST_V1", "runs": run_rows})
    receipt = {"schema_version": "PASS_T_PHASE2B_REAL_RUN_RECEIPT_V1", "created_at_utc": utc_now(), "protocol_content_id": protocol_folder.name, "backend": backend.name, "run_count": len(run_rows), "all_failures_preserved": True}
    return exclusive_tree(output_base or repository_root() / "artifacts/pass_t/phase2b/runs", files, receipt)


def store_mock_run(scenario: str, payload: dict, raw: bytes, prediction: dict | None, validation: dict, error: str | None) -> Path:
    value = {"schema_version": "PASS_T_PHASE2B_MOCK_RUN_V1", "scenario": scenario, "payload": payload,
             "raw_output_utf8": raw.decode("utf-8", errors="replace"), "prediction": prediction,
             "validation": validation, "error": error}
    return exclusive_tree(repository_root() / "artifacts/pass_t/phase2b/mock/runs", {"mock_run.json": pretty_bytes(value)}, {"schema_version": "PASS_T_PHASE2B_MOCK_RECEIPT_V1", "scenario": scenario})


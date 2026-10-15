"""Prospective protocol drafting and immutable freeze gates."""
from __future__ import annotations

from pathlib import Path

from .common import Phase2BBlocked, canonical_bytes, digest, exclusive_tree, file_sha256, pretty_bytes, repository_root, utc_now
from .config import REPRESENTATIONS, check_capabilities, validate_config


REQUIRED_DECISIONS = {
    "multi_image_frame_count", "storyboard_frame_count", "storyboard_columns", "video_fps",
    "event_time_tolerance_s", "bounded_interval_overlap_required", "repeat_count",
    "run_order", "pilot_item_ids", "reference_policy", "budget_limit_usd",
}


def prompt_path() -> Path:
    return repository_root() / "artifacts/pass_t/phase2b/templates/event_reasoning_prompt_v1.txt"


def prepare_protocol(config: dict, eligibility: dict, decisions: dict) -> dict:
    config_validation = validate_config(config, real_run=True)
    capabilities = check_capabilities(config)
    unresolved = [f"model_config.{field}" for field in config_validation["errors"]]
    unresolved.extend(f"decisions.{key}" for key in sorted(REQUIRED_DECISIONS)
                      if key not in decisions or decisions.get(key) is None)
    if not capabilities["real_run_ready"]:
        unresolved.append("capabilities.runtime_verification")
    if decisions.get("multi_image_frame_count") is not None and decisions.get("storyboard_frame_count") is not None:
        if decisions["multi_image_frame_count"] != decisions["storyboard_frame_count"]:
            unresolved.append("decisions.same_frame_selection_budget_required")
    pilot_ids = decisions.get("pilot_item_ids", [])
    allowed = {row["annotation_item_id"] for row in eligibility["records"] if row["pilot_scoring_permission"] != "AUDIT_ONLY_NO_MODEL_RUN"}
    if pilot_ids and (not isinstance(pilot_ids, list) or not set(pilot_ids) <= allowed):
        unresolved.append("decisions.pilot_item_ids_contains_excluded_or_unknown")
    if decisions.get("repeat_count") not in (None, 1, 3):
        unresolved.append("decisions.repeat_count_must_be_1_or_3")
    for key in ("multi_image_frame_count", "storyboard_frame_count", "storyboard_columns"):
        value = decisions.get(key)
        if value is not None and (type(value) is not int or value < 1):
            unresolved.append(f"decisions.{key}.positive_integer_required")
    for key in ("video_fps", "event_time_tolerance_s", "budget_limit_usd"):
        value = decisions.get(key)
        if value is not None and (type(value) not in (int, float) or value < 0 or (key == "video_fps" and value == 0)):
            unresolved.append(f"decisions.{key}.invalid_numeric_value")
    if decisions.get("bounded_interval_overlap_required") is not None and type(decisions["bounded_interval_overlap_required"]) is not bool:
        unresolved.append("decisions.bounded_interval_overlap_required.boolean_required")
    if pilot_ids == []:
        unresolved.append("decisions.pilot_item_ids.empty")
    if decisions.get("run_order") == []:
        unresolved.append("decisions.run_order.empty")
    if decisions.get("reference_policy") is not None and decisions.get("reference_policy") != config.get("reference_policy"):
        unresolved.append("decisions.reference_policy_must_match_model_config")
    verified = set(capabilities["verified_representations"])
    declared_run_order = decisions.get("run_order", [])
    if declared_run_order and (not isinstance(declared_run_order, list) or not set(declared_run_order) <= REPRESENTATIONS or not set(declared_run_order) <= verified):
        unresolved.append("decisions.run_order_contains_unverified_representation")
    prompt = prompt_path()
    if not prompt.is_file():
        unresolved.append("prompt_template_missing")
        prompt_sha = None
    else:
        prompt_sha = file_sha256(prompt)
    protocol = {
        "schema_version": "PASS_T_PHASE2B_PROTOCOL_V1",
        "status": "DRAFT_UNRESOLVED" if unresolved else "READY_TO_FREEZE",
        "created_at_utc": utc_now(),
        "model_config": config,
        "model_config_sha256": digest(canonical_bytes(config)),
        "capability_check": capabilities,
        "authority": eligibility["authority"],
        "eligibility_sha256": digest(canonical_bytes(eligibility)),
        "prompt_path": prompt.relative_to(repository_root()).as_posix() if prompt.is_file() else None,
        "prompt_sha256": prompt_sha,
        "decisions": decisions,
        "unresolved_fields": sorted(set(unresolved)),
        "fixed_rules": {
            "same_model_all_representations": True,
            "no_model_substitution": True,
            "no_representation_fallback": True,
            "selection_is_gt_independent": True,
            "all_repeats_retained": True,
            "best_of_selection_forbidden": True,
            "test3_model_run_forbidden": True,
            "global_metrics_forbidden": True,
        },
    }
    protocol["protocol_draft_sha256"] = digest(canonical_bytes({k: v for k, v in protocol.items() if k != "protocol_draft_sha256"}))
    return protocol


def freeze_protocol(protocol: dict, base: Path | None = None) -> Path:
    expected_draft = digest(canonical_bytes({k: v for k, v in protocol.items() if k != "protocol_draft_sha256"}))
    if protocol.get("protocol_draft_sha256") != expected_draft:
        raise Phase2BBlocked("PROTOCOL_DRAFT_HASH_MISMATCH")
    if protocol.get("status") != "READY_TO_FREEZE" or protocol.get("unresolved_fields"):
        raise Phase2BBlocked("PROTOCOL_HAS_UNRESOLVED_DECISIONS")
    if not protocol.get("capability_check", {}).get("real_run_ready"):
        raise Phase2BBlocked("PROTOCOL_CAPABILITIES_NOT_VERIFIED")
    frozen = {**protocol, "status": "FROZEN", "frozen_at_utc": utc_now()}
    raw = pretty_bytes(frozen)
    receipt = {
        "schema_version": "PASS_T_PHASE2B_PROTOCOL_FREEZE_RECEIPT_V1",
        "protocol_sha256": digest(raw),
        "dataset_sha256": protocol["authority"]["dataset_sha256"],
        "model_config_sha256": protocol["model_config_sha256"],
        "prompt_sha256": protocol["prompt_sha256"],
    }
    base = base or repository_root() / "artifacts/pass_t/phase2b/protocols"
    return exclusive_tree(base, {"protocol.json": raw}, receipt)


def verify_frozen_protocol(folder: Path) -> dict:
    protocol_path = folder / "protocol.json"
    receipt_path = folder / "completion_receipt.json"
    from .common import read_json
    protocol = read_json(protocol_path)
    receipt = read_json(receipt_path)
    if protocol.get("status") != "FROZEN" or receipt.get("protocol_sha256") != file_sha256(protocol_path):
        raise Phase2BBlocked("FROZEN_PROTOCOL_HASH_MISMATCH")
    if receipt.get("dataset_sha256") != protocol.get("authority", {}).get("dataset_sha256"):
        raise Phase2BBlocked("FROZEN_PROTOCOL_DATASET_MISMATCH")
    from .authority import DATASET_SHA256
    if receipt.get("dataset_sha256") != DATASET_SHA256:
        raise Phase2BBlocked("APPROVED_DATASET_VERSION_MISMATCH")
    if digest(canonical_bytes(protocol["model_config"])) != receipt.get("model_config_sha256"):
        raise Phase2BBlocked("FROZEN_MODEL_CONFIG_HASH_MISMATCH")
    if file_sha256(prompt_path()) != receipt.get("prompt_sha256"):
        raise Phase2BBlocked("FROZEN_PROMPT_HASH_MISMATCH")
    return protocol


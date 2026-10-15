"""Model configuration and capability verification contracts."""
from __future__ import annotations

import json
from pathlib import Path
import jsonschema

from .common import Phase2BBlocked


CAPABILITY_STATUSES = {"DECLARED", "LOCALLY_VERIFIED", "PROVIDER_VERIFIED", "UNKNOWN", "UNSUPPORTED"}
REPRESENTATIONS = {"REENCODED_AUTHORIZED_VIDEO", "MULTI_IMAGE", "STORYBOARD"}
REFERENCE_POLICIES = {"NONE", "AUTHORIZED_STATIC_REFERENCE", "APPROVED_NEUTRAL_LOCALIZATION"}


def unresolved_template() -> dict:
    return {
        "schema_version": "PASS_T_PHASE2B_MODEL_CONFIG_V1",
        "provider": None,
        "backend": None,
        "model": None,
        "revision": None,
        "execution_location": None,
        "external_data_consent": False,
        "modalities": [],
        "capabilities": {
            rep: {"status": "UNKNOWN", "evidence": None} for rep in sorted(REPRESENTATIONS)
        },
        "limits": {"max_images": None, "max_pixels_per_image": None, "context_tokens": None},
        "generation": {"temperature": None, "sampling": None, "seed": None, "max_output_tokens": None},
        "transport": {"timeout_seconds": None, "max_retries": None, "monetary_budget_usd": None},
        "reference_policy": "NONE",
        "complete": False,
    }


def validate_config(config: dict, *, real_run: bool = False) -> dict:
    errors: list[str] = []
    config_schema = json.loads((Path(__file__).parent / "contracts/model_config_v1.json").read_text(encoding="utf-8"))
    for error in jsonschema.Draft202012Validator(config_schema).iter_errors(config):
        errors.append("schema." + ".".join(map(str, error.absolute_path)))
    if config.get("schema_version") != "PASS_T_PHASE2B_MODEL_CONFIG_V1":
        errors.append("schema_version")
    for key in ("provider", "backend", "model", "revision", "execution_location"):
        if not isinstance(config.get(key), str) or not config[key].strip():
            errors.append(key)
    if config.get("execution_location") not in {"LOCAL", "EXTERNAL"}:
        errors.append("execution_location.enum")
    if any(token in str(key).lower() for key in _all_keys(config) for token in ("api_key", "access_token", "password", "credential", "secret")):
        errors.append("credentials_must_not_be_stored")
    if not isinstance(config.get("external_data_consent"), bool):
        errors.append("external_data_consent")
    if config.get("reference_policy") not in REFERENCE_POLICIES:
        errors.append("reference_policy")
    capabilities = config.get("capabilities")
    if not isinstance(capabilities, dict) or set(capabilities) != REPRESENTATIONS:
        errors.append("capabilities")
    else:
        for rep, cap in capabilities.items():
            if not isinstance(cap, dict) or cap.get("status") not in CAPABILITY_STATUSES:
                errors.append(f"capabilities.{rep}.status")
            elif cap.get("status") in {"LOCALLY_VERIFIED", "PROVIDER_VERIFIED"} and not cap.get("evidence"):
                errors.append(f"capabilities.{rep}.evidence")
            if real_run and cap.get("status") == "DECLARED":
                errors.append(f"capabilities.{rep}.DECLARED_NOT_VERIFIED")
    generation = config.get("generation", {})
    if generation.get("temperature") is None or generation.get("sampling") is None or generation.get("max_output_tokens") is None:
        errors.append("generation")
    elif not isinstance(generation.get("sampling"), bool) or not isinstance(generation.get("max_output_tokens"), int) or generation["max_output_tokens"] < 1:
        errors.append("generation.types")
    transport = config.get("transport", {})
    if transport.get("timeout_seconds") is None or transport.get("max_retries") is None or transport.get("monetary_budget_usd") is None:
        errors.append("transport")
    elif (not isinstance(transport.get("timeout_seconds"), (int, float)) or transport["timeout_seconds"] <= 0
          or not isinstance(transport.get("max_retries"), int) or transport["max_retries"] < 0
          or not isinstance(transport.get("monetary_budget_usd"), (int, float)) or transport["monetary_budget_usd"] < 0):
        errors.append("transport.types")
    limits = config.get("limits", {})
    if not isinstance(limits, dict) or any(not isinstance(limits.get(key), int) or limits[key] < 1 for key in ("max_images", "max_pixels_per_image", "context_tokens")):
        errors.append("limits")
    if config.get("complete") is not True:
        errors.append("complete")
    if real_run and config.get("execution_location") == "EXTERNAL" and config.get("external_data_consent") is not True:
        errors.append("external_data_consent_required")
    return {"valid": not errors, "errors": sorted(set(errors)), "real_run_gate": real_run}


def _all_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_keys(child)


def require_valid(config: dict, *, real_run: bool = False) -> None:
    result = validate_config(config, real_run=real_run)
    if not result["valid"]:
        raise Phase2BBlocked("MODEL_CONFIG_INVALID:" + ",".join(result["errors"]))


def check_capabilities(config: dict) -> dict:
    validation = validate_config(config)
    statuses = {rep: config.get("capabilities", {}).get(rep, {}).get("status", "UNKNOWN") for rep in sorted(REPRESENTATIONS)}
    return {
        "schema_version": "PASS_T_PHASE2B_CAPABILITY_CHECK_V1",
        "config_valid": validation["valid"],
        "statuses": statuses,
        "verified_representations": [rep for rep, status in statuses.items() if status in {"LOCALLY_VERIFIED", "PROVIDER_VERIFIED"}],
        "real_run_ready": validation["valid"] and all(status in {"LOCALLY_VERIFIED", "PROVIDER_VERIFIED", "UNSUPPORTED"} for status in statuses.values()),
        "notes": ["DECLARED is documentation only and is not runtime verification", "No representation fallback or model substitution is permitted"],
    }


"""Strict numeric-loopback transport shared by three model-specific adapters."""
from __future__ import annotations

import base64
import io
import json
import os
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image

from ..common import Phase2BBlocked, canonical_bytes, digest, environment_bool, exclusive_tree, pretty_bytes, repository_root
from ..model_visible import inspect_payload
from .catalog import for_backend

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Phase2BBlocked("LOCAL_ENDPOINT_REDIRECT_FORBIDDEN")

def validate_endpoint(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in ("", "/") or parsed.port is None):
        raise Phase2BBlocked("NUMERIC_LOOPBACK_HTTP_ENDPOINT_REQUIRED")
    return url.rstrip("/")

def request_json(url, value, timeout):
    parsed = urlsplit(url)
    validate_endpoint(f"{parsed.scheme}://{parsed.netloc}")
    if parsed.path not in {"/health", "/generate", "/smoke", "/shutdown"} or parsed.query or parsed.fragment:
        raise Phase2BBlocked("LOCAL_ENDPOINT_PATH_NOT_ALLOWED")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url, data=canonical_bytes(value) if value is not None else None,
                                    headers={"Content-Type": "application/json"})
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise Phase2BBlocked("LOCAL_RESPONSE_SIZE_LIMIT")
    return json.loads(raw)

class LocalModelAdapter:
    """No automatic model load/download; connects to a separately approved runtime."""
    def __init__(self, config, deployment, *, exchange=request_json):
        self.config = config
        self.spec = for_backend(config["backend"])
        if self.spec is None:
            raise Phase2BBlocked("UNSUPPORTED_LOCAL_BACKEND")
        self.name = self.spec.backend
        self.deployment = deployment
        self.endpoint = validate_endpoint(deployment["endpoint"])
        self.exchange = exchange
        self.last_receipt = None
        if config["model"] != self.spec.model or config["revision"] != self.spec.revision:
            raise Phase2BBlocked("EXACT_MODEL_OR_REVISION_MISMATCH")
        if deployment.get("quantization") != self.spec.quantization:
            raise Phase2BBlocked("UNAUTHORIZED_QUANTIZATION_OR_FALLBACK")
        if config.get("execution_location") != "LOCAL":
            raise Phase2BBlocked("LOCAL_EXECUTION_REQUIRED")

    def capability_check(self, timeout=5):
        health = self.exchange(self.endpoint + "/health", None, timeout)
        for key, expected in (("model", self.spec.model), ("revision", self.spec.revision), ("quantization", self.spec.quantization)):
            if health.get(key) != expected:
                raise Phase2BBlocked("RUNTIME_IDENTITY_MISMATCH:" + key)
        if health.get("model_loaded") is not True or health.get("kernel_verified") is not True:
            raise Phase2BBlocked("RUNTIME_NOT_MODEL_AND_KERNEL_VERIFIED")
        return health

    def construct_request(self, request, media):
        if not inspect_payload(request)["safe"]:
            raise Phase2BBlocked("UNSAFE_LOCAL_MODEL_PAYLOAD")
        rep = request["representation"]
        if rep not in self.deployment.get("approved_representations", []):
            raise Phase2BBlocked("MODALITY_NOT_RUNTIME_APPROVED")
        if rep not in self.spec.documented:
            raise Phase2BBlocked("EXACT_CHECKPOINT_MODALITY_NOT_DOCUMENTED")
        rows = request["media"]
        if set(media) != {row["media_id"] for row in rows}:
            raise Phase2BBlocked("MEDIA_INVENTORY_MISMATCH")
        images = 0; aliases = []; encoded = []
        for row in rows:
            blob = media[row["media_id"]]
            if digest(blob) != row["content_sha256"]:
                raise Phase2BBlocked("MEDIA_HASH_MISMATCH")
            if row["media_type"] == "image/png":
                images += 1
                with Image.open(io.BytesIO(blob)) as image:
                    if image.width * image.height > self.deployment["max_input_pixels"]:
                        raise Phase2BBlocked("VISUAL_INPUT_EXCEEDS_APPROVED_PIXEL_BUDGET")
            aliases.extend(row["supplied_frame_aliases"])
            encoded.append({"media_id": row["media_id"], "base64": base64.b64encode(blob).decode("ascii")})
        if images > self.deployment["max_images"]:
            raise Phase2BBlocked("VISUAL_INPUT_EXCEEDS_IMAGE_COUNT")
        if len(set(aliases)) > self.deployment["max_frames"]:
            raise Phase2BBlocked("VISUAL_INPUT_EXCEEDS_FRAME_COUNT")
        return {"schema_version": "PASS_T_LOCAL_RUNTIME_REQUEST_V1", "model": self.spec.model,
                "revision": self.spec.revision, "quantization": self.spec.quantization,
                "payload": request, "media": encoded, "generation": self.config["generation"],
                "runtime_policy": {"no_frame_dropping": True, "no_network_loading": True}}

    def invoke(self, request, media, timeout_seconds):
        synthetic_allowed = (environment_bool("PASS_T_LOCAL_SYNTHETIC_APPROVAL")
                             and self.deployment.get("synthetic_only") is True
                             and digest(canonical_bytes(request)) in self.deployment.get("synthetic_payload_sha256_allowlist", []))
        if not environment_bool("PASS_T_PHASE2B_REAL_RUN_PERMISSION") and not synthetic_allowed:
            raise Phase2BBlocked("LOCAL_INFERENCE_AUTHORIZATION_REQUIRED")
        body = self.construct_request(request, media)
        health = self.capability_check()
        if request["representation"] not in health.get("tested_representations", []) and not synthetic_allowed:
            raise Phase2BBlocked("MODALITY_NOT_ACTUALLY_SMOKE_TESTED")
        started = time.perf_counter()
        response = self.exchange(self.endpoint + "/generate", body, timeout_seconds)
        raw = response.get("raw_output", "")
        if not isinstance(raw, str):
            raise Phase2BBlocked("RAW_OUTPUT_STRING_REQUIRED")
        # Preserve raw output before receipt/schema validation; no model-output repair.
        self.last_receipt = {k: v for k, v in response.items() if k != "raw_output"}
        response_store = repository_root() / "artifacts/pass_t/phase2b/local_vlm/v1/runtime_responses"
        if self.deployment.get('response_store_path'):
            from ..common import safe_join
            candidate=safe_join(repository_root(),self.deployment['response_store_path'])
            if not candidate.is_relative_to(repository_root()/'artifacts/pass_t/phase2b/capacity_probe') or not synthetic_allowed:
                raise Phase2BBlocked('SYNTHETIC_RESPONSE_NAMESPACE_REQUIRED')
            response_store=candidate
        if os.name == "nt" and not str(response_store).startswith("\\\\?\\"):
            response_store = Path("\\\\?\\" + str(response_store.resolve()))
        exclusive_tree(response_store,
                       {"raw_output.txt": raw.encode("utf8"), "receipt.json": pretty_bytes(self.last_receipt)},
                       {"schema_version": "PASS_T_LOCAL_RESPONSE_RECEIPT_V1", "request_sha256": digest(canonical_bytes(body)),
                        "runtime_seconds": time.perf_counter() - started})
        for key, expected in (("model", self.spec.model), ("revision", self.spec.revision), ("quantization", self.spec.quantization)):
            if response.get(key) != expected:
                raise Phase2BBlocked("GENERATION_IDENTITY_MISMATCH:" + key)
        if response.get("error"):
            raise Phase2BBlocked(str(response["error"]))
        from .qwen_contract import verify_processed_aliases
        aliases=verify_processed_aliases(request,response,self.deployment.get('video_sampling_contract')=='EXPLICIT_QWEN_VIDEO_FPS_V1')
        self.last_receipt['citation_allowed_aliases']=aliases
        return raw.encode("utf8")

def register_local_backends(register):
    def factory(config):
        from ..common import read_json
        path = os.environ.get("PASS_T_LOCAL_DEPLOYMENT_CONFIG")
        if not path:
            raise Phase2BBlocked("LOCAL_DEPLOYMENT_CONFIG_REQUIRED")
        return LocalModelAdapter(config, read_json(__import__('pathlib').Path(path)))
    from .catalog import SPECS
    from ..backends import _BACKEND_FACTORIES
    for spec in SPECS.values():
        if spec.backend not in _BACKEND_FACTORIES:
            register(spec.backend, factory)

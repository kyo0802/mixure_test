"""Loopback model host, blocked until explicit runtime and smoke authorization."""
from __future__ import annotations
import argparse
import base64
import json
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for relative in ("src", "artifacts/pass_i/runtime/vendor"):
    sys.path.insert(0, str(ROOT / relative))
from memory_graph.pass_t.phase2b.common import Phase2BBlocked, read_json, digest, environment_bool
from memory_graph.pass_t.phase2b.local_vlm.runtime import load_runtime
from memory_graph.pass_t.phase2b.local_vlm.transport import LocalModelAdapter, validate_endpoint
from memory_graph.pass_t.phase2b.predictions import parse_raw, validate_prediction
from urllib.parse import urlsplit

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True); parser.add_argument("--deployment", required=True)
    parser.add_argument("--metadata-manifest", required=True)
    parser.add_argument("--approve-runtime-load", action="store_true")
    args = parser.parse_args()
    if not args.approve_runtime_load or not environment_bool("PASS_T_LOCAL_RUNTIME_APPROVAL"):
        raise Phase2BBlocked("EXPLICIT_RUNTIME_LOAD_APPROVAL_REQUIRED")
    config = read_json(Path(args.config)); deployment = read_json(Path(args.deployment))
    adapter = LocalModelAdapter(config, deployment)
    if not deployment.get("snapshot_path"):
        raise Phase2BBlocked("LOCAL_PINNED_WEIGHTS_MISSING")
    # One runtime at a time, across models using this same namespace.
    lock = ROOT / "artifacts/pass_t/phase2b/local_vlm/v1/runtime.lock"
    with lock.open("x", encoding="utf8") as stream:
        stream.write(str(os.getpid()))
    try:
        runtime = load_runtime(config, deployment, Path(deployment["snapshot_path"]), read_json(Path(args.metadata_manifest)))
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def send(self, value, status=200):
                body = json.dumps(value).encode("utf8")
                self.send_response(status); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_GET(self):
                if self.path == "/health":
                    self.send(runtime.health())
                else:
                    self.send({"error": "NOT_FOUND"}, 404)
            def do_POST(self):
                if self.path == "/shutdown" and deployment.get("synthetic_only") is True:
                    self.send({"status":"OWNED_RUNTIME_SHUTDOWN"})
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                    return
                if self.path not in {"/generate", "/smoke"} or not environment_bool("PASS_T_LOCAL_SMOKE_APPROVAL"):
                    self.send({"error": "GENERATION_APPROVAL_REQUIRED"}, 403); return
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 64_000_000:
                    self.send({"error": "REQUEST_SIZE_LIMIT"}, 413); return
                try:
                    envelope = json.loads(self.rfile.read(length))
                    if deployment.get("synthetic_only") is True and digest(__import__('memory_graph.pass_t.phase2b.common',fromlist=['canonical_bytes']).canonical_bytes(envelope["payload"])) not in deployment.get("synthetic_payload_sha256_allowlist",[]):
                        raise Phase2BBlocked("ONLY_PREREGISTERED_SYNTHETIC_PAYLOADS_ALLOWED")
                    if any(envelope.get(k) != v for k, v in (("model", adapter.spec.model), ("revision", adapter.spec.revision), ("quantization", adapter.spec.quantization))):
                        raise Phase2BBlocked("GENERATION_IDENTITY_MISMATCH")
                    media = {row["media_id"]: base64.b64decode(row["base64"], validate=True) for row in envelope["media"]}
                    adapter.construct_request(envelope["payload"], media)
                    if envelope["generation"] != config["generation"]:
                        raise Phase2BBlocked("GENERATION_SETTINGS_MISMATCH")
                    result = runtime.generate(envelope)
                    if self.path == "/smoke":
                        aliases = list(dict.fromkeys(a for row in envelope["payload"]["media"] for a in row["supplied_frame_aliases"]))
                        try:
                            validation = validate_prediction(parse_raw(result["raw_output"].encode("utf8")), aliases)
                        except Exception as error:
                            validation = {"valid": False, "parser_error": str(error)}
                        result["prediction_validation"] = validation
                        if validation["valid"]:
                            representation = envelope["payload"]["representation"]
                            if representation not in runtime.tested_representations:
                                runtime.tested_representations.append(representation)
                    self.send(result)
                except Exception as error:
                    self.send({"model": adapter.spec.model, "revision": adapter.spec.revision, "quantization": adapter.spec.quantization,
                               "raw_output": "", "error": str(error)})
        parsed = urlsplit(validate_endpoint(deployment["endpoint"]))
        if parsed.hostname != "127.0.0.1":
            raise Phase2BBlocked("HOST_REQUIRES_IPV4_LOOPBACK")
        HTTPServer(("127.0.0.1", parsed.port), Handler).serve_forever()
    finally:
        lock.unlink(missing_ok=True)

if __name__ == "__main__":
    main()

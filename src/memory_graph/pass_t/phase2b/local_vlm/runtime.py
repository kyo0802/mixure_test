"""Guarded model-specific runtime loader; no load on import or diagnostics."""
from __future__ import annotations
import base64
import io
import json
import time
from pathlib import Path
from PIL import Image
from ..common import Phase2BBlocked, file_sha256, environment_bool
from .catalog import for_backend, runtime_error

def validate_local_snapshot(spec, snapshot, metadata_manifest):
    if not snapshot.is_dir():
        raise Phase2BBlocked("LOCAL_PINNED_WEIGHTS_MISSING")
    row = next((row for row in metadata_manifest["models"] if row["model"] == spec.model and row["revision"] == spec.revision), None)
    if row is None:
        raise Phase2BBlocked("PINNED_METADATA_MODEL_REVISION_MISMATCH")
    for weight in row["weight_files"]:
        path = snapshot / weight["name"]
        if not path.is_file():
            raise Phase2BBlocked("LOCAL_PINNED_WEIGHTS_MISSING:" + weight["name"])
        expected = (weight.get("lfs") or {}).get("sha256")
        if not expected or file_sha256(path) != expected:
            raise Phase2BBlocked("LOCAL_WEIGHT_HASH_MISMATCH")
    config = json.loads((snapshot / "config.json").read_text(encoding="utf8"))
    if config != row["config"]:
        raise Phase2BBlocked("LOCAL_MODEL_CONFIG_CHANGED")
    return config

class QwenAWQRuntime:
    """Official Transformers Qwen2.5-VL AWQ loader; untested until approved smoke."""
    def __init__(self, spec, deployment, snapshot, metadata_manifest):
        if not environment_bool("PASS_T_LOCAL_RUNTIME_APPROVAL") or deployment.get("approved") is not True:
            raise Phase2BBlocked("MODEL_LOAD_REQUIRES_RUNTIME_APPROVAL")
        config = validate_local_snapshot(spec, snapshot, metadata_manifest)
        if config.get("quantization_config", {}).get("quant_method") != "awq":
            raise Phase2BBlocked("OFFICIAL_AWQ_CHECKPOINT_REQUIRED")
        import torch
        if not torch.cuda.is_available():
            raise Phase2BBlocked("CUDA_UNAVAILABLE")
        probe = torch.ones((16, 16), device="cuda") @ torch.ones((16, 16), device="cuda")
        torch.cuda.synchronize()
        if probe[0, 0].item() != 16:
            raise Phase2BBlocked("CUDA_KERNEL_PROBE_FAILED")
        free, total = torch.cuda.mem_get_info()
        if free < deployment["max_gpu_memory_gib"] * 2**30:
            raise Phase2BBlocked("INSUFFICIENT_FREE_VRAM_FOR_APPROVED_LOAD_BUDGET")
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
        torch.cuda.reset_peak_memory_stats()
        self.spec = spec; self.deployment = deployment
        started = time.perf_counter()
        self.processor = AutoProcessor.from_pretrained(snapshot, local_files_only=True,
            max_pixels=deployment["processor_max_pixels"])
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(snapshot, local_files_only=True,
            torch_dtype="auto", device_map={"": "cuda:0"}, attn_implementation=deployment["attention"])
        self.load_seconds = time.perf_counter() - started
        self.load_peak_bytes = torch.cuda.max_memory_allocated()
        self.tested_representations = []

    def health(self):
        return {"model": self.spec.model, "revision": self.spec.revision, "quantization": self.spec.quantization,
                "model_loaded": True, "kernel_verified": True, "tested_representations": self.tested_representations,
                "model_load_peak_vram_bytes": self.load_peak_bytes, "model_load_seconds": self.load_seconds}

    def generate(self, envelope):
        import torch
        payload = envelope["payload"]
        if payload["representation"] == "REENCODED_AUTHORIZED_VIDEO":
            raise Phase2BBlocked("VIDEO_PROCESSOR_FRAME_PTS_INSTRUMENTATION_NOT_VERIFIED")
        blobs = {row["media_id"]: base64.b64decode(row["base64"], validate=True) for row in envelope["media"]}
        content = []; images = []; dimensions = []
        for row in payload["media"]:
            with Image.open(io.BytesIO(blobs[row["media_id"]])) as image:
                rgb = image.convert("RGB")
            images.append(rgb); dimensions.append(list(rgb.size))
            content.append({"type": "text", "text": "Supplied aliases: " + ", ".join(row["supplied_frame_aliases"])})
            content.append({"type": "image", "image": rgb})
        schema = json.loads((Path(__file__).parents[1] / "contracts/prediction_v1.json").read_text(encoding="utf8"))
        content.append({"type": "text", "text": payload["instructions"] + "\nRequired JSON schema:\n" + json.dumps(schema)})
        messages = [{"role": "user", "content": content}]
        if self.deployment.get("response_format_system"):
            messages.insert(0,{"role":"system","content":self.deployment["response_format_system"]})
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=images, padding=True, return_tensors="pt").to("cuda:0")
        generation = envelope["generation"]
        if generation["seed"] is not None:
            torch.manual_seed(generation["seed"])
        kwargs = {"max_new_tokens": generation["max_output_tokens"], "do_sample": generation["sampling"]}
        if generation["sampling"]:
            kwargs["temperature"] = generation["temperature"]
        torch.cuda.reset_peak_memory_stats(); started = time.perf_counter()
        try:
            with torch.inference_mode():
                generated = self.model.generate(**inputs, max_time=self.deployment.get("generation_timeout_seconds", 120), **kwargs)
            torch.cuda.synchronize()
        except Exception as error:
            raise Phase2BBlocked(runtime_error(error)) from error
        ids = generated[:, inputs.input_ids.shape[-1]:]
        raw = self.processor.batch_decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        return {"model": self.spec.model, "revision": self.spec.revision, "quantization": self.spec.quantization,
                "raw_output": raw, "processed_frame_aliases": list(dict.fromkeys(a for row in payload["media"] for a in row["supplied_frame_aliases"])),
                "input_image_dimensions": dimensions, "processor_grid_thw": inputs.get("image_grid_thw").tolist(),
                "generated_tokens": ids.shape[-1], "runtime_seconds": time.perf_counter() - started,
                "peak_inference_vram_bytes": torch.cuda.max_memory_allocated(), "cpu_offload_used": False}

def load_runtime(config, deployment, snapshot, metadata_manifest):
    spec = for_backend(config["backend"])
    if spec is None or config["model"] != spec.model or config["revision"] != spec.revision:
        raise Phase2BBlocked("EXACT_MODEL_OR_REVISION_MISMATCH")
    if deployment.get("quantization") != spec.quantization:
        raise Phase2BBlocked("UNAUTHORIZED_QUANTIZATION_OR_FALLBACK")
    if not environment_bool("PASS_T_LOCAL_RUNTIME_APPROVAL") or not deployment.get("approved"):
        raise Phase2BBlocked("MODEL_LOAD_REQUIRES_RUNTIME_APPROVAL")
    if spec.key == "qwen_nf4":
        from .nf4 import QwenNF4Runtime
        return QwenNF4Runtime(spec,deployment,snapshot,metadata_manifest)
    if spec.key == "videollama3_7b":
        raise Phase2BBlocked("VIDEOLLAMA3_BF16_OFFLOAD_AND_CUSTOM_CODE_COMPATIBILITY_NOT_VERIFIED")
    if spec.key == "nemotron_nvfp4":
        raise Phase2BBlocked("NEMOTRON_EXACT_NVFP4_VLLM_SM120_KERNEL_NOT_VERIFIED")
    return QwenAWQRuntime(spec, deployment, snapshot, metadata_manifest)

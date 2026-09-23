"""Optional Transformers backend. No model is loaded unless explicitly enabled."""
from pathlib import Path
import torch
from .base import BackendUnavailable
from .hardware import hardware_report
from .prompts import make_prompt


class LocalBackend:
    def __init__(self, config):
        self.config = config
        self.hardware = hardware_report()
        self.device = ("cuda" if torch.cuda.is_available() else "cpu") if config.device == "auto" else config.device
        available = self.hardware.get("available_ram_gb")
        if self.device == "cpu" and available is not None and available < 3:
            raise BackendUnavailable("Less than 3 GiB free RAM; use event-only mode or a stronger machine")
        try:
            from transformers import AutoProcessor, AutoModelForImageTextToText
        except ImportError as error:
            raise BackendUnavailable("Install optional backend with uv sync --extra vlm") from error
        torch.set_num_threads(config.cpu_threads)
        kwargs = {"cache_dir": str(Path(config.cache_dir).resolve()), "revision": config.revision,
                  "local_files_only": config.local_files_only, "trust_remote_code": False}
        self.processor = AutoProcessor.from_pretrained(config.model, **kwargs)
        # Qwen's BF16-trained weights can overflow in FP16 and produce repeated
        # punctuation instead of JSON. Prefer BF16 on supported CUDA hardware.
        dtype = (torch.float32 if self.device == "cpu" else
                 torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16)
        if config.load_in_4bit:
            if not self.device.startswith("cuda"):
                raise BackendUnavailable("The 4-bit profile requires CUDA")
            from transformers import BitsAndBytesConfig
            quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=dtype)
            self.model = AutoModelForImageTextToText.from_pretrained(config.model, torch_dtype=dtype,
                attn_implementation="sdpa", quantization_config=quantization, device_map={"":self.device}, **kwargs).eval()
        else:
            self.model = AutoModelForImageTextToText.from_pretrained(config.model, torch_dtype=dtype,
                            attn_implementation="sdpa", **kwargs).to(self.device).eval()
        self.resolved_revision = getattr(self.model.config, "_commit_hash", None) or config.revision
        provenance = Path(config.model)/"download_provenance.json"
        if provenance.is_file():
            import json
            self.resolved_revision = json.loads(provenance.read_text())["revision"]

    @property
    def identity(self):
        from importlib.metadata import version
        from .grounded_analysis import GROUNDING_VERSION
        return {"backend": "transformers", "model": self.config.model, "revision": self.resolved_revision,
                "max_new_tokens": self.config.max_new_tokens, "image_longest_edge": self.config.image_longest_edge,
                "device": self.device, "dtype": str(self.model.dtype), "sampling": False,
                "quantization": "nf4-double" if self.config.load_in_4bit else "none",
                "max_inference_seconds": self.config.max_inference_seconds,
                "transformers_version": version("transformers"), "torch_version": torch.__version__,
                "processor": type(self.processor.image_processor).__name__,
                "grounding": GROUNDING_VERSION if self.config.ground_entities_individually else "joint"}

    def analyze_event(self, images, track_metadata, event_metadata):
        from PIL import Image
        self.last_trace, self.last_component_errors = [], []
        if self.config.ground_entities_individually:
            from .grounded_analysis import analyze_grounded
            result, self.last_trace, self.last_component_errors = analyze_grounded(
                self._generate, images, track_metadata, event_metadata)
            return result
        loaded = []
        for path in images:
            with Image.open(path) as original:
                image = original.convert("RGB")
                image.thumbnail((self.config.image_longest_edge, self.config.image_longest_edge))
                loaded.append(image)
        return self._generate(loaded, make_prompt(track_metadata, event_metadata), self.config.max_new_tokens)

    def _generate(self, loaded, prompt, max_new_tokens):
        from transformers import StoppingCriteria, StoppingCriteriaList
        import time
        loaded = [image.copy() for image in loaded]
        for image in loaded:
            image.thumbnail((self.config.image_longest_edge, self.config.image_longest_edge))
        content = [{"type": "image"} for _ in loaded] + [{"type": "text", "text": prompt}]
        text = self.processor.apply_chat_template([{"role": "user", "content": content}], tokenize=False, add_generation_prompt=True)
        # SmolVLM uses longest_edge/splitting; Qwen uses its own patch-aligned resize.
        # Do not pass model-specific image options to unrelated processors.
        image_options = {}
        if self.model.config.model_type in {"smolvlm", "idefics3"}:
            image_options = {"size": {"longest_edge": self.config.image_longest_edge},
                             "do_image_splitting": False}
        inputs = self.processor(text=text, images=loaded, return_tensors="pt", **image_options)
        inputs = {key: value.to(self.device) if hasattr(value, "to") else value for key, value in inputs.items()}
        if self.device != "cpu" and "pixel_values" in inputs:
            inputs["pixel_values"] = inputs["pixel_values"].to(self.model.dtype)
        deadline = time.monotonic()+self.config.max_inference_seconds
        class Deadline(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                return time.monotonic() >= deadline
        with torch.inference_mode():
            generated = self.model.generate(**inputs, max_new_tokens=min(max_new_tokens,self.config.max_new_tokens), do_sample=False,
                                            stopping_criteria=StoppingCriteriaList([Deadline()]))
        # The parser rejects incomplete JSON if generation was stopped by the bounded deadline.
        return self.processor.batch_decode(generated[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]

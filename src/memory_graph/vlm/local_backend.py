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
        dtype = torch.float32 if self.device == "cpu" else torch.float16
        self.model = AutoModelForImageTextToText.from_pretrained(config.model, torch_dtype=dtype,
                        attn_implementation="sdpa", **kwargs).to(self.device).eval()
        self.resolved_revision = getattr(self.model.config, "_commit_hash", None) or config.revision

    @property
    def identity(self):
        return {"backend": "transformers", "model": self.config.model, "revision": self.resolved_revision,
                "max_new_tokens": self.config.max_new_tokens, "image_longest_edge": self.config.image_longest_edge,
                "device": self.device, "sampling": False}

    def analyze_event(self, images, track_metadata, event_metadata):
        from PIL import Image
        from transformers import StoppingCriteria, StoppingCriteriaList
        import time
        loaded = []
        for path in images:
            with Image.open(path) as original:
                image = original.convert("RGB")
                image.thumbnail((self.config.image_longest_edge, self.config.image_longest_edge))
                loaded.append(image)
        content = [{"type": "image"} for _ in loaded] + [{"type": "text", "text": make_prompt(track_metadata, event_metadata)}]
        text = self.processor.apply_chat_template([{"role": "user", "content": content}], tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=text, images=loaded, return_tensors="pt",
                                size={"longest_edge": self.config.image_longest_edge}, do_image_splitting=False)
        inputs = {key: value.to(self.device) if hasattr(value, "to") else value for key, value in inputs.items()}
        if self.device != "cpu" and "pixel_values" in inputs:
            inputs["pixel_values"] = inputs["pixel_values"].to(self.model.dtype)
        deadline = time.monotonic()+self.config.max_inference_seconds
        class Deadline(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                return time.monotonic() >= deadline
        with torch.inference_mode():
            generated = self.model.generate(**inputs, max_new_tokens=self.config.max_new_tokens, do_sample=False,
                                            stopping_criteria=StoppingCriteriaList([Deadline()]))
        # The parser rejects incomplete JSON if generation was stopped by the bounded deadline.
        return self.processor.batch_decode(generated[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]

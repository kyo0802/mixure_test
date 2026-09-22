"""Explicitly configured OpenAI-compatible vision endpoint; disabled by default."""
import base64
import json
import os
from urllib.request import Request, urlopen
from .prompts import make_prompt


class HTTPBackend:
    def __init__(self, config):
        self.config = config

    @property
    def identity(self):
        return {"backend": "http", "model": self.config.model, "revision": self.config.revision,
                "endpoint": self.config.endpoint, "max_new_tokens": self.config.max_new_tokens}

    def analyze_event(self, images, track_metadata, event_metadata):
        content = [{"type": "text", "text": make_prompt(track_metadata, event_metadata)}]
        for image in images:
            content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,"+
                           base64.b64encode(image.read_bytes()).decode("ascii")}})
        payload = {"model": self.config.model, "messages": [{"role": "user", "content": content}],
                   "max_tokens": self.config.max_new_tokens, "temperature": 0, "response_format": {"type": "json_object"}}
        headers = {"Content-Type": "application/json"}
        key = os.environ.get(self.config.api_key_env)
        if key:
            headers["Authorization"] = "Bearer "+key
        request = Request(self.config.endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urlopen(request, timeout=self.config.request_timeout_seconds) as response:
            result = json.load(response)
        return result["choices"][0]["message"]["content"]

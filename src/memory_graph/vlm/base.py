from typing import Protocol
from pathlib import Path


class VLMBackend(Protocol):
    @property
    def identity(self) -> dict: ...
    def analyze_event(self, images: list[Path], track_metadata: list[dict], event_metadata: dict) -> str | dict: ...


class BackendUnavailable(RuntimeError):
    pass


def create_backend(config):
    if config.backend == "disabled":
        return None
    if config.backend == "http":
        from .http_backend import HTTPBackend
        return HTTPBackend(config)
    from .local_backend import LocalBackend
    return LocalBackend(config)

"""Model-independent, raw-first observation experiment boundary.

No model registry, processor assumptions, hidden resampling, retries or GT access.
Adapters report their actual token/tiling/temporal behavior in metadata. The
caller must obtain human authorization before allowing any real generation.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Protocol


@dataclass(frozen=True)
class SourceFrame:
    alias: str
    path: Path
    source_frame_index: int
    native_pts_s: float
    sha256: str


@dataclass(frozen=True)
class ObservationRequest:
    frames: tuple[SourceFrame, ...]
    recorded_source_video_sha256: str
    system_instruction: str
    task_instruction: str
    output_schema: Mapping[str, Any]
    generation: Mapping[str, Any]
    model_settings: Mapping[str, Any]
    preprocessing: Mapping[str, Any]


@dataclass(frozen=True)
class AdapterValue:
    """Data is model-specific; metadata must be serializable and factual."""
    data: Any
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class RawResponse:
    text: str
    metadata: Mapping[str, Any]


class ObservationAdapter(Protocol):
    def load(self, settings: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def render(self, request: ObservationRequest) -> AdapterValue: ...
    def preprocess(self, frames: tuple[SourceFrame, ...], rendered: AdapterValue,
                   settings: Mapping[str, Any]) -> AdapterValue: ...
    def generate(self, prepared: AdapterValue, rendered: AdapterValue,
                 generation: Mapping[str, Any]) -> RawResponse: ...
    def resources(self) -> Mapping[str, Any]: ...
    def close(self) -> None: ...


def verify_sources(request: ObservationRequest) -> None:
    aliases=[f.alias for f in request.frames]
    if not aliases or any(not a for a in aliases) or len(set(aliases))!=len(aliases):
        raise ValueError("EMPTY_OR_DUPLICATE_ALIASES")
    pts=[f.native_pts_s for f in request.frames]
    if any(not math.isfinite(p) for p in pts) or any(a>=b for a,b in zip(pts,pts[1:])):
        raise ValueError("NON_CHRONOLOGICAL_NATIVE_PTS")
    indices=[f.source_frame_index for f in request.frames]
    if any(i<0 for i in indices) or any(a>=b for a,b in zip(indices,indices[1:])):
        raise ValueError("NON_CHRONOLOGICAL_SOURCE_INDICES")
    for frame in request.frames:
        if hashlib.sha256(frame.path.read_bytes()).hexdigest()!=frame.sha256:
            raise ValueError("SOURCE_IMAGE_HASH_MISMATCH:"+frame.alias)


def execute_once(adapter: ObservationAdapter, request: ObservationRequest,
                 destination: Path, validator: Callable[[str, list[str]], Mapping[str, Any]],
                 *, allow_generation: bool=False) -> Mapping[str, Any]:
    """One explicit invocation; directory creation is an at-most-once marker.

    No automatic model selection, download, or load on import/construction.
    Permission is a caller assertion, not a human-approval receipt or a way to
    bypass an adapter's own resource/security gates. No GUI/CLI runs this API.
    """
    if not allow_generation:
        raise PermissionError("GENERATION_NOT_AUTHORIZED_BY_CALLER")
    verify_sources(request)
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    def save(name,value):
        with (destination/name).open("x",encoding="utf8") as f:
            json.dump(value,f,ensure_ascii=False,indent=2)
    request_record=asdict(request)
    for frame in request_record["frames"]:frame["path"]=str(frame["path"])
    save("request.json",request_record)
    started=time.perf_counter();stage="LOAD";raw_saved=False
    try:
        save("model.json",adapter.load(request.model_settings))
        stage="RENDER";rendered=adapter.render(request)
        save("rendering.json",rendered.metadata)
        stage="PREPROCESS";prepared=adapter.preprocess(request.frames,rendered,request.preprocessing)
        save("preprocessing.json",prepared.metadata)
        expected=[f.alias for f in request.frames]
        if prepared.metadata.get("consumed_aliases")!=expected:
            raise ValueError("ADAPTER_DROPPED_REORDERED_OR_ADDED_SOURCE_FRAMES")
        stage="GENERATE";response=adapter.generate(prepared,rendered,request.generation)
        with (destination/"raw.txt").open("xb") as f:
            f.write(response.text.encode("utf8"));f.flush()
            import os
            os.fsync(f.fileno())
        raw_saved=True
        save("generation.json",response.metadata)
        stage="VALIDATE"
        try:diagnostics=dict(validator(response.text,expected))
        except Exception as error:
            diagnostics={"classification":"VALIDATOR_ERROR","error":str(error),"no_invalid_to_no_event_conversion":True}
        save("validation.json",diagnostics)
        receipt={"completed":True,"raw_sha256":hashlib.sha256(response.text.encode("utf8")).hexdigest(),"elapsed_s":time.perf_counter()-started,"resources":adapter.resources(),"independent_physical_validation":False,"retries":0}
        save("receipt.json",receipt)
        return receipt
    except Exception as error:
        save("failure.json",{"stage":stage,"error_type":type(error).__name__,"error":str(error),"raw_saved":raw_saved,"retries":0})
        raise
    finally:
        try:adapter.close()
        except Exception as error:save("cleanup_failure.json",{"error":str(error)})

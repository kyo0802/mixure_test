from pathlib import Path
from typing import Literal
import yaml
from pydantic import Field
from .models import Model, Probability
from .config import Config, load_config


class EventConfig(Model):
    min_track_duration: float = Field(default=.8, gt=0)
    min_observations: int = Field(default=3, ge=2)
    min_detector_confidence: Probability = .4
    disappearance_seconds: float = Field(default=1, gt=0)
    before_offset_seconds: float = Field(default=1, gt=0)
    after_offset_seconds: float = Field(default=1, gt=0)
    proximity_change_threshold: float = Field(default=.12, gt=0)
    proximity_window_seconds: float = Field(default=1.2, gt=0)
    near_threshold: float = Field(default=.35, gt=0)
    motion_coupling_threshold: Probability = .85
    min_motion_speed: float = Field(default=.03, gt=0)
    signal_persistence_seconds: float = Field(default=.6, gt=0)
    merge_window_seconds: float = Field(default=.4, ge=0)
    max_merged_duration: float = Field(default=4, gt=0)
    cooldown_seconds: float = Field(default=1, gt=0)
    max_vlm_events: int = Field(default=8, ge=0)
    nearest_neighbors: int = Field(default=3, ge=1)


class KeyframeConfig(Model):
    search_radius_seconds: float = Field(default=.45, ge=0)
    require_involved_track_visibility: bool = True
    sharpness_weight: float = Field(default=.2, ge=0)
    bbox_area_weight: float = Field(default=.3, ge=0)
    detector_confidence_weight: float = Field(default=.2, ge=0)
    visibility_weight: float = Field(default=.3, ge=0)
    image_width: int = Field(default=960, ge=256)
    max_context_tracks: int = Field(default=6, ge=2)


class VLMConfig(Model):
    backend: Literal["auto", "local", "http", "disabled"] = "disabled"
    model: str = "HuggingFaceTB/SmolVLM2-500M-Video-Instruct"
    revision: str = "main"
    cache_dir: str = ".models/huggingface"
    local_files_only: bool = True
    device: str = "auto"
    cpu_threads: int = Field(default=4, ge=1)
    max_new_tokens: int = Field(default=768, ge=64)
    max_inference_seconds: float = Field(default=120, gt=0)
    ground_entities_individually: bool = False
    load_in_4bit: bool = False
    image_longest_edge: int = Field(default=512, ge=256)
    confidence_threshold: Probability = .55
    semantic_margin: Probability = .15
    endpoint: str = "http://127.0.0.1:8000/v1/chat/completions"
    api_key_env: str = "VLM_API_KEY"
    request_timeout_seconds: float = Field(default=120, gt=0)


class AdmissionConfig(Model):
    min_observations: int = Field(default=4, ge=2)
    min_track_duration: float = Field(default=.8, gt=0)
    min_mean_confidence: Probability = .4
    min_area_fraction: Probability = .001


class GraphConfig(Model):
    max_geometric_neighbors: int = Field(default=3, ge=1)
    min_relation_confidence: Probability = .55
    near_threshold: float = Field(default=.35, gt=0)
    direction_margin: float = Field(default=.025, gt=0)
    conflict_multiplier: Probability = .25
    temporal_merge_gap_seconds: float = Field(default=1.2, ge=0)
    transition_max_gap_seconds: float = Field(default=3, gt=0)
    max_render_entities: int = Field(default=24, ge=2)
    max_render_relations: int = Field(default=32, ge=1)
    max_attributes_per_entity: int = Field(default=3, ge=0)


class V2Config(Model):
    perception_config: str = "default.yaml"
    perception: Config = Field(default_factory=Config)
    events: EventConfig = Field(default_factory=EventConfig)
    keyframes: KeyframeConfig = Field(default_factory=KeyframeConfig)
    vlm: VLMConfig = Field(default_factory=VLMConfig)
    admission: AdmissionConfig = Field(default_factory=AdmissionConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)


def load_v2_config(path="configs/v2.yaml"):
    path = Path(path)
    content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    content["perception"] = load_config(path.parent/content.get("perception_config", "default.yaml"))
    return V2Config.model_validate(content)

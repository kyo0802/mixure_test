from pathlib import Path
from typing import Annotated
import yaml
from pydantic import Field, model_validator
from .models import Model, Probability, Predicate

Positive = Annotated[float, Field(gt=0)]


class VideoConfig(Model):
    sample_fps: Positive = 5


class DetectorConfig(Model):
    model: str = "yolo11s.pt"
    confidence: Probability = .25
    image_size: int = Field(default=960, ge=32)
    device: str = "auto"
    cpu_threads: int = Field(default=4, ge=1)


class TrackingConfig(Model):
    high_threshold: Probability = .35
    low_threshold: Probability = .1
    new_track_threshold: Probability = .35
    match_threshold: Probability = .8
    lost_seconds: Positive = 2

    @model_validator(mode="after")
    def thresholds(self):
        if self.low_threshold >= self.high_threshold:
            raise ValueError("tracking.low_threshold must be below high_threshold")
        return self


class EpisodesConfig(Model):
    min_duration_seconds: Positive = 5
    scene_change_threshold: Probability = .55
    cooldown_seconds: Positive = 5


class AnchorsConfig(Model):
    classes: list[str] = Field(default_factory=lambda: ["table", "desk", "chair", "sofa", "bed", "refrigerator", "cabinet", "shelf", "door", "counter", "sink", "bench", "toilet", "tv", "microwave", "oven"])
    min_observations: int = Field(default=5, ge=2)
    min_track_duration: Positive = 2
    min_area_fraction: Probability = .01
    max_center_speed: Positive = .30
    min_anchor_score: Probability = .60
    duration_saturation_seconds: Positive = 6
    area_saturation_fraction: Positive = .10


class ObjectsConfig(Model):
    aliases: dict[str, str] = Field(default_factory=lambda: {"dining table": "table", "couch": "sofa"})
    excluded_subject_classes: list[str] = Field(default_factory=lambda: ["person"])


class RelationsConfig(Model):
    near_threshold: Positive = .25
    direction_margin: Positive = .03
    overlap_threshold: Probability = .05
    containment_threshold: Probability = .90
    on_above_max_gap: Positive = .15
    min_confidence: Probability = .5
    max_anchors_per_object: int = Field(default=3, ge=1)


class TemporalConfig(Model):
    min_support: int = Field(default=3, ge=2)
    min_duration_seconds: Positive = .6
    max_gap_seconds: Positive = 1
    confidence_threshold: Probability = .5


class TransitionsConfig(Model):
    predicates: list[Predicate] = Field(default_factory=lambda: ["INSIDE", "ON_OR_ABOVE", "NEAR"])
    max_gap_seconds: Positive = 10


class VisualizationConfig(Model):
    annotated_video: bool = True
    max_video_width: int = Field(default=1280, ge=160)
    graph_nodes_per_page: int = Field(default=24, ge=4)
    overlay_relations: int = Field(default=5, ge=0)


class Config(Model):
    video: VideoConfig = Field(default_factory=VideoConfig)
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    episodes: EpisodesConfig = Field(default_factory=EpisodesConfig)
    anchors: AnchorsConfig = Field(default_factory=AnchorsConfig)
    objects: ObjectsConfig = Field(default_factory=ObjectsConfig)
    relations: RelationsConfig = Field(default_factory=RelationsConfig)
    temporal_filter: TemporalConfig = Field(default_factory=TemporalConfig)
    transitions: TransitionsConfig = Field(default_factory=TransitionsConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)


def load_config(path: str | Path) -> Config:
    return Config.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {})

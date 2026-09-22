import re
from ..config import ObjectsConfig


def canonical_class(name: str, config: ObjectsConfig) -> str:
    return config.aliases.get(name, name)


def id_prefix(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "object"


def is_subject(name: str, anchor_classes: list[str], config: ObjectsConfig) -> bool:
    return name not in anchor_classes and name not in config.excluded_subject_classes

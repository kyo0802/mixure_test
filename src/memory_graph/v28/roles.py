"""Deterministic label roles used for compatibility, never to overwrite raw labels."""
from __future__ import annotations

SUPPORT = {"table", "dining table", "desk", "counter", "shelf", "bed", "couch", "sofa", "bench"}
CONTAINER = {"box", "container", "bag", "handbag", "backpack", "suitcase", "drawer", "bowl"}
OCCLUDER = {"sports ball", "teddy bear", "potted plant", "bottle", "book", "tv", "laptop", "microwave",
            "refrigerator", "chair", "couch", "sofa", "bed"}
LANDMARK = {"chair", "microwave", "refrigerator", "tv", "sports ball", "teddy bear", "potted plant",
            "bottle", "laptop", "book", "remote", "cup", "clock", "sink", "oven", "toaster"}
INTERACTION = {"person", "hand"}


def semantic_roles(label: str) -> list[str]:
    value = (label or "unknown").casefold().strip()
    roles = []
    for role, labels in (("SUPPORT", SUPPORT), ("CONTAINER", CONTAINER), ("OCCLUDER", OCCLUDER),
                         ("LANDMARK", LANDMARK), ("INTERACTION_AGENT", INTERACTION)):
        if value in labels:
            roles.append(role)
    return roles or ["OTHER"]


def primary_compatible(label: str, interaction_evidence: bool = False) -> bool:
    roles = set(semantic_roles(label))
    if "INTERACTION_AGENT" in roles:
        return interaction_evidence
    return bool(roles & {"SUPPORT", "CONTAINER", "OCCLUDER", "LANDMARK"})


def context_compatible(label: str) -> bool:
    roles = set(semantic_roles(label))
    return bool(roles & {"SUPPORT", "CONTAINER", "OCCLUDER", "LANDMARK"}) and "INTERACTION_AGENT" not in roles


def compatible_relations(label: str) -> list[str]:
    roles = set(semantic_roles(label))
    relations = []
    if "INTERACTION_AGENT" in roles:
        relations.append("HELD_BY")
    if "SUPPORT" in roles:
        relations.append("ON")
    if "CONTAINER" in roles:
        relations.append("INSIDE")
    if "OCCLUDER" in roles:
        relations.extend(["OCCLUDED_BY", "BEHIND"])
    if roles & {"SUPPORT", "CONTAINER", "OCCLUDER", "LANDMARK"}:
        relations.append("NEAR")
    return relations

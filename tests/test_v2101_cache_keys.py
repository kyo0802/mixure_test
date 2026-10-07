from __future__ import annotations

import json

import pytest

from memory_graph.v2101_deploy.cache_keys import (
    IDENTITY_FIELDS,
    VLM_FIELDS,
    cache_key,
    cache_path,
    write_cache_entry_once,
)


def _fields(names):
    return {name: f"fixed:{name}" for name in names}


@pytest.mark.parametrize("field", IDENTITY_FIELDS)
def test_identity_dependency_change_invalidates_cache(field):
    original = _fields(IDENTITY_FIELDS)
    changed = dict(original)
    changed[field] = "changed"
    assert cache_key("identity_perception", original) != cache_key("identity_perception", changed)


@pytest.mark.parametrize("field", VLM_FIELDS)
def test_vlm_dependency_change_invalidates_cache(field):
    original = _fields(VLM_FIELDS)
    changed = dict(original)
    changed[field] = {"changed": True} if field == "frame_sampling_config" else "changed"
    assert cache_key("vlm", original) != cache_key("vlm", changed)


def test_cache_keys_are_order_independent_and_namespaced():
    fields = _fields(VLM_FIELDS)
    assert cache_key("vlm", fields) == cache_key("vlm", dict(reversed(list(fields.items()))))
    assert cache_key("vlm", fields) != cache_key("identity_perception", _fields(IDENTITY_FIELDS))


def test_cache_entry_creation_never_overwrites_existing(tmp_path):
    fields = _fields(VLM_FIELDS)
    target = cache_path(tmp_path, "vlm", fields)
    write_cache_entry_once(target, {"response": "old", "valid": True})
    before = target.read_bytes()
    with pytest.raises(FileExistsError):
        write_cache_entry_once(target, {"response": "new", "valid": True})
    assert target.read_bytes() == before
    assert json.loads(before)["response"] == "old"


def test_missing_dependencies_fail_closed():
    with pytest.raises(ValueError, match="missing"):
        cache_key("vlm", {})

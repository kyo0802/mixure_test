from __future__ import annotations

import ast
from pathlib import Path

from memory_graph.v2101_deploy.boundary import AUTHORITY, make_candidate_record


ROOT = Path(__file__).resolve().parents[1]


def test_smoke_runner_imports_no_operational_identity_or_memory_capabilities():
    source = (ROOT / "scripts/run_v2101_model_smoke.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden_prefixes = (
        "memory_graph.identity", "memory_graph.v296_reid", "memory_graph.v297_physical_identity",
        "memory_graph.memory", "memory_graph.search", "memory_graph.tracking", "memory_graph.sam",
    )
    assert not any(name.startswith(forbidden_prefixes) for name in imported_modules)
    assert "require_v2101_artifact_path(output_dir)" in source


def test_model_response_record_cannot_authorize_or_mutate_operational_state():
    record = make_candidate_record(
        model_id="candidate", model_revision="pinned-revision", event_id="event-1",
        raw_response="{}", completed=True, json_valid=True, schema_valid=True,
        semantic_validator_valid=False, metrics={},
    )
    assert record["authority"] == AUTHORITY == "NONE_DEPLOYMENT_EXPERIMENT_ONLY"
    assert set(record).isdisjoint({
        "persistent_id", "alias", "identity_write", "identity_guard", "candidate_epoch",
        "person_epoch", "core", "negative_bank", "physical_memory", "sam_restart",
        "search_planner", "memory_graph_write",
    })

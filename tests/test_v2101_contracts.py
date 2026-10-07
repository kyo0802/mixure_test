from memory_graph.v2101_deploy.contracts import event_json_schema, schema_sha256, schema_valid


def test_schema_is_exact_frozen_seven_field_contract():
    schema = event_json_schema(["A", "B"])
    assert schema["required"] == [
        "event_type", "interaction_anchor", "released", "target_visible_after",
        "final_relation", "final_relation_anchor", "confidence",
    ]
    assert schema["additionalProperties"] is False
    assert schema_sha256(["A", "B"]) == schema_sha256(["A", "B"])
    assert schema_sha256(["A", "B"]) != schema_sha256(["A", "C"])


def test_schema_validator_checks_dynamic_anchor_enums():
    answer = {
        "event_type": "STATIC", "interaction_anchor": "A", "released": "NO",
        "target_visible_after": "YES", "final_relation": "ON",
        "final_relation_anchor": "B", "confidence": "MEDIUM",
    }
    assert schema_valid(["A", "B"], answer)
    answer["interaction_anchor"] = "C"
    assert not schema_valid(["A", "B"], answer)

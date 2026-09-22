import json
from .schemas import VLMSceneGraphResult


def parse_result(raw, allowed_ids, event_id):
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()
        raw = json.loads(text)
    if isinstance(raw, VLMSceneGraphResult):
        raw = raw.model_dump()
    result = VLMSceneGraphResult.model_validate(raw)
    if result.event_id != event_id:
        raise ValueError("VLM event ID does not match request")
    ids = {e.track_id for e in result.entities}
    ids.update(r.subject_track_id for r in result.relations)
    ids.update(r.object_track_id for r in result.relations if r.object_track_id is not None)
    if not ids <= set(allowed_ids):
        raise ValueError(f"VLM invented/unsupplied track IDs: {sorted(ids-set(allowed_ids))}")
    return result

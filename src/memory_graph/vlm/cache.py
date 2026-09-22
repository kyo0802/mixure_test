import hashlib
import json
from pathlib import Path
from .prompts import PROMPT_VERSION, make_prompt
from .parser import parse_result
from ..memory.memory_store import save_json


def cache_key(images, identity, tracks, event):
    data = {"images": [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in images],
            "backend": identity, "prompt_version": PROMPT_VERSION, "prompt": make_prompt(tracks, event)}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def analyze_cached(backend, images, tracks, event, cache_dir, raw_path):
    key = cache_key(images, backend.identity, tracks, event)
    path = Path(cache_dir)/(key+".json")
    hit = path.is_file()
    if hit:
        record = json.loads(path.read_text(encoding="utf-8"))
    else:
        raw = backend.analyze_event(images, tracks, event)
        record = {"cache_key": key, "backend": backend.identity, "prompt_version": PROMPT_VERSION, "response": raw}
        save_json(path, record)
    save_json(raw_path, {**record, "cache_hit": hit})
    # Failed parse output is cached as well: retry requires changed inputs or explicit cache removal.
    result = parse_result(record["response"], [t["track_id"] for t in tracks], event["event_id"])
    return result, hit

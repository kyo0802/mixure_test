import json
from pathlib import Path
from pydantic import BaseModel
from ..models import MemoryGraphData


def save_json(path: str | Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    def encode(item):
        if isinstance(item, BaseModel):
            return item.model_dump(mode="json")
        raise TypeError(f"Cannot serialize {type(item)}")
    # Atomic replacement prevents a partial JSON file from looking like a completed artifact.
    temporary = path.with_suffix(path.suffix+".tmp")
    temporary.write_text(json.dumps(value, default=encode, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    temporary.replace(path)


def load_graph(path: str | Path) -> MemoryGraphData:
    return MemoryGraphData.model_validate_json(Path(path).read_text(encoding="utf-8"))

"""Prepare an unlabelled offline Pass I dataset. Never invokes a model."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from memory_graph.pass_i.builder import build, validate_dataset
from memory_graph.pass_i.common import OUT, read, write

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    if args.validate_only:
        result = validate_dataset()
        write(OUT / 'reports/dataset_validation.json', result)
        print(json.dumps(result, indent=2))
        sys.exit(bool(result['failed']))
    summary, validation = build(cfg=read(args.config) if args.config else None)
    print(json.dumps({'summary': summary, 'validation': validation}, indent=2))

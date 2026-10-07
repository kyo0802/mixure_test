"""Opt-in Strata experiment; never changes the normal FindMind entrypoint."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.v294_strata import runner

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['prepare', 'first', 'run'])
    ap.add_argument('--include-incomplete', action='store_true', help='Diagnostic abstention tests only; no graph writes')
    args = ap.parse_args()
    result = runner.prepare() if args.stage == 'prepare' else runner.run(first=args.stage == 'first', include_incomplete=args.include_incomplete)
    print(json.dumps(result, ensure_ascii=False))

"""Strict isolated native annotated event-video A/B runner."""
import argparse
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run','evaluate','verify']);args=p.parse_args()
    from memory_graph.reasoning import video_experiment as v
    if args.command=='prepare':result=v.prepare()
    elif args.command=='run':result=v.run()
    elif args.command=='evaluate':
        from memory_graph.reasoning.video_evaluation import evaluate
        result=evaluate()
    else:
        from memory_graph.reasoning.pipeline import verify_manifest
        result=verify_manifest(v.EXP,v.EXP/'final/final_integrity_manifest.json')
    print(result)

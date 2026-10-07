"""V293 audit, bounded evidence preparation, replay and freeze entry point."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.v293.audit import run_audit
from memory_graph.v293.runner import prepare_all,replay_vlm,reselect_prepared

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['audit','prepare','reselect','replay','finalize','verify','all'])
    args=parser.parse_args()
    if args.command=='audit':run_audit()
    if args.command in {'prepare','all'}:prepare_all()
    if args.command=='reselect':reselect_prepared()
    if args.command in {'replay','all'}:replay_vlm()
    if args.command in {'finalize','verify','all'}:
        from memory_graph.v293.report import finalize,verify
        print(verify() if args.command=='verify' else finalize())

if __name__=='__main__':main()

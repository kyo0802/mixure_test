"""Ordered offline Phase1c checkpoints; no response submission path."""
import argparse
import sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'src'),str(root/'artifacts/pass_i/runtime/vendor'),
             str(root/'outputs/current_development/video_event_experiment/.deps')]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--step',choices=['freeze','prepare','audit','finalize'],required=True)
    step=parser.parse_args().step
    if step=='freeze':
        from memory_graph.pass_t.phase1c_policy import freeze
        result=freeze()
    elif step=='prepare':
        from memory_graph.pass_t.phase1c_review import prepare
        result=prepare()
    elif step=='audit':
        from memory_graph.pass_t.phase1c_audit import audit
        result=audit()
    else:
        from memory_graph.pass_t.phase1c_report import finalize
        result=finalize()
    print(step,result)


if __name__=='__main__':main()

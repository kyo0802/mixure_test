"""Explicit checkpoint runner; preserves the original Phase 1 entrypoint."""
import sys
import argparse
from pathlib import Path
sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root/'src'), str(root/'artifacts/pass_i/runtime/vendor'),
               str(root/'outputs/current_development/video_event_experiment/.deps')]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--milestone', choices=['M1','M2','M3','M4'], required=True)
    p.add_argument('--pilot-partial', action='store_true')
    args = p.parse_args()
    from memory_graph.pass_t import phase1b
    if args.milestone == 'M1':
        result = phase1b.stage_m1()
    elif args.milestone == 'M2':
        result = phase1b.stage_m2(args.pilot_partial)
    elif args.milestone == 'M3':
        from memory_graph.pass_t.media import run_pilot
        result = run_pilot(args.pilot_partial)
    else:
        result = phase1b.stage_m4()
    print(args.milestone, result)


if __name__ == '__main__':
    main()

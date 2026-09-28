"""Run the isolated V2.9.1 corrective experiment."""
import argparse

from memory_graph.v291.pipeline import (freeze, post_freeze_evaluation, run_all,
                                        verify_freeze, write_report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("run", "freeze", "evaluate", "verify"), nargs="?", default="run")
    args = parser.parse_args()
    if args.stage == "run":
        run_all()
    elif args.stage == "freeze":
        print(freeze()["freeze_utc"])
    elif args.stage == "evaluate":
        evaluation = post_freeze_evaluation()
        write_report(evaluation=evaluation)
    else:
        verify_freeze()
        print("V2.9.1 prediction manifest verifies")


if __name__ == "__main__":
    main()

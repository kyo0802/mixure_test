"""Run V2.9 stages. Historical outputs are read only."""
import argparse
from memory_graph.v29.pipeline import stage_ab, stage_dense, stage_candidates, stage_vlm, stage_decisions, freeze, verify_freeze


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["audit-events", "dense", "candidates", "vlm", "decisions", "freeze", "verify"])
    parser.add_argument("--task", choices=[f"test{i}" for i in range(3, 10)])
    args = parser.parse_args()
    if args.stage == "audit-events":
        audit, events = stage_ab()
        for row, event in zip(audit, events):
            print(row["task"], "trusted_masks", row["trusted_phone_01_masks_available"],
                  "events", event["peak_frames"])
    elif args.stage == "dense":
        stage_dense([args.task] if args.task else None)
    elif args.stage == "candidates":
        stage_candidates([args.task] if args.task else None)
    elif args.stage == "vlm":
        stage_vlm([args.task] if args.task else None)
    elif args.stage == "decisions":
        stage_decisions()
    elif args.stage == "freeze":
        manifest = freeze()
        print("frozen", len(manifest["files_sha256"]), "prediction files", flush=True)
    elif args.stage == "verify":
        verify_freeze()
        print("V2.9 freeze verified", flush=True)


if __name__ == "__main__":
    main()

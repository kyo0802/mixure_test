import argparse
import logging
from pathlib import Path
from memory_graph.config import load_config
from memory_graph.pipeline import run_video


def main():
    parser = argparse.ArgumentParser(description="Process task1.mp4 and task2.mp4 with fresh trackers")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--no-annotated", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    config = load_config(args.config)
    if args.no_annotated:
        config.visualization.annotated_video = False
    failed = []
    for name in ["task1.mp4", "task2.mp4"]:
        try:
            run_video(name, config)
        except Exception as error:
            logging.error("%s failed: %s", name, error)
            failed.append(name)
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import logging
from pathlib import Path
from memory_graph.config import load_config
from memory_graph.pipeline import run_video


def main():
    parser = argparse.ArgumentParser(description="Build an RGB-relative temporal memory graph")
    parser.add_argument("video", type=Path)
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-annotated", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    config = load_config(args.config)
    if args.no_annotated:
        config.visualization.annotated_video = False
    try:
        run_video(args.video, config, args.output)
    except (FileNotFoundError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()

import argparse
import logging
from memory_graph.config_v2 import load_v2_config
from memory_graph.pipeline_v2 import run_video_v2


def main():
    parser = argparse.ArgumentParser(description="Event-driven V2 semantic-memory framework; VLM disabled by default")
    parser.add_argument("video")
    parser.add_argument("--config", default="configs/v2.yaml")
    parser.add_argument("--output")
    parser.add_argument("--events-only", action="store_true")
    parser.add_argument("--backend", choices=["disabled", "local", "http", "auto"])
    parser.add_argument("--allow-model-download", action="store_true", help="Explicitly permit local model downloads when a VLM backend is enabled")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    config = load_v2_config(args.config)
    if args.backend:
        config.vlm.backend = args.backend
    if args.allow_model_download:
        config.vlm.local_files_only = False
    run_video_v2(args.video, config, args.output, args.events_only)


if __name__ == "__main__":
    main()

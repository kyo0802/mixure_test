import argparse
import logging
from memory_graph.config_v2 import load_v2_config
from memory_graph.pipeline_v2 import run_video_v2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run both videos through the separate V2 pipeline")
    parser.add_argument("videos", nargs="*", default=["task1.mp4", "task2.mp4"])
    parser.add_argument("--config", default="configs/v2.yaml")
    parser.add_argument("--events-only", action="store_true")
    parser.add_argument("--backend", choices=["disabled", "local", "http", "auto"])
    parser.add_argument("--allow-model-download", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    config = load_v2_config(args.config)
    if args.backend:
        config.vlm.backend = args.backend
    if args.allow_model_download:
        config.vlm.local_files_only = False
    failed = []
    for name in args.videos:
        try:
            run_video_v2(name, config, events_only=args.events_only)
        except Exception as error:
            logging.error("%s: %s", name, error)
            failed.append(name)
    raise SystemExit(int(bool(failed)))

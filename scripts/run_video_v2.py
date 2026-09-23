import argparse
import logging
import json
from pathlib import Path
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
    parser.add_argument("--cached-vlm", action="store_true", help="Replay existing validated/raw VLM cache without loading a model; VLM config must match")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    config = load_v2_config(args.config)
    if args.backend:
        config.vlm.backend = args.backend
    if args.allow_model_download:
        config.vlm.local_files_only = False
    backend = None
    output = Path(args.output or Path("outputs_v2")/Path(args.video).stem)
    if args.cached_vlm:
        if args.events_only or config.vlm.backend == "disabled":
            parser.error("--cached-vlm requires an enabled VLM config and cannot be combined with --events-only")
        prior = json.loads((output/"run_config.json").read_text(encoding="utf-8"))
        if prior["vlm"] != config.vlm.model_dump():
            parser.error("VLM config changed; run the actual backend to obtain new evidence")
        identity = json.loads((output/"memory_graph.json").read_text(encoding="utf-8"))["metadata"]["vlm_backend"]
        class CachedBackend:
            def __init__(self, identity):
                self.identity = identity
            def analyze_event(self, *args):
                raise RuntimeError("VLM cache miss; rerun without --cached-vlm")
        backend = CachedBackend(identity)
    run_video_v2(args.video, config, output, args.events_only, backend)
    if args.cached_vlm and json.loads((output/"run_status.json").read_text())["vlm_failed_events"]:
        parser.exit(1, "One or more cached VLM events could not be replayed; see run_status.json\n")


if __name__ == "__main__":
    main()

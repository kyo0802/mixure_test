import argparse
import json
import logging
from memory_graph.config_v2 import load_v2_config
from memory_graph.v21.pipeline import run

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Inference only. No GT or annotation inputs.')
    parser.add_argument('video'); parser.add_argument('--output',required=True)
    parser.add_argument('--config',default='configs/v2_gpu_7b.yaml')
    parser.add_argument('--reuse-v2'); parser.add_argument('--events-only',action='store_true')
    args=parser.parse_args(); logging.basicConfig(level=logging.INFO)
    print(json.dumps(run(args.video,load_v2_config(args.config),args.output,args.reuse_v2,args.events_only),indent=2))

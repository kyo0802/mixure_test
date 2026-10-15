"""Explicit V1D draft/freeze/run commands; default is CPU metadata dry-run."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
# Match the already successful V1D worker's local dependency search path.
# No install/download or alternate model/runtime environment is selected.
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor'),
             str(ROOT/'outputs/current_development/video_event_experiment/.deps')]
import argparse,json
from memory_graph.pass_t.phase2b.common import read_json,pretty_bytes
from memory_graph.pass_t.phase2b.v1d_protocol import dry_run,freeze_protocol

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['dry-run','freeze','run'],nargs='?',default='dry-run')
    parser.add_argument('--draft');parser.add_argument('--human-approval');parser.add_argument('--frozen');parser.add_argument('--execution-authorization')
    parser.add_argument('--output',help='New dry-run JSON file only; never overwritten')
    args=parser.parse_args()
    if args.mode=='dry-run':
        result=dry_run(ROOT)
        if args.output:
            with Path(args.output).open('xb') as f:f.write(pretty_bytes(result['draft']))
        print(json.dumps({'mode':'CPU_METADATA_DRY_RUN','draft_sha256':result['readiness']['draft_sha256'],
            'decisions_pending':21,'planned_calls':18,'media_integrity':'PENDING_AUTHORIZED_EXECUTION',
            'model_initialized':False,'calls_executed':0,'protocol_frozen':False}))
    elif args.mode=='freeze':
        if not args.draft or not args.human_approval:parser.error('freeze requires --draft and --human-approval; no approval inferred')
        print(freeze_protocol(read_json(Path(args.draft)),read_json(Path(args.human_approval)),ROOT))
    else:
        if not args.frozen or not args.execution_authorization:parser.error('run requires --frozen and --execution-authorization')
        from memory_graph.pass_t.phase2b.v1d_execution import execute_authorized
        print(execute_authorized(read_json(Path(args.frozen)),read_json(Path(args.execution_authorization)),ROOT))

if __name__=='__main__':main()

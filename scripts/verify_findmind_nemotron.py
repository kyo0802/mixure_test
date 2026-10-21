"""CPU-only model asset verification; never imports torch or loads weights."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'src'))

if __name__=='__main__':
    from memory_graph.integration.nemotron_assets import verify_existing, atomic
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['cached','strict'],default='cached')
    p.add_argument('--force',action='store_true');p.add_argument('--report')
    a=p.parse_args();r=verify_existing(ROOT,mode=a.mode,force=a.force)
    if a.report:
        dest=Path(a.report).resolve()
        if not dest.is_relative_to(ROOT):raise ValueError('REPORT_MUST_STAY_IN_PROJECT')
        atomic(dest,r)
    print(json.dumps({k:r[k] for k in ['validation_kind','elapsed_s','fresh_files','cached_files','trust_policy']},indent=2))

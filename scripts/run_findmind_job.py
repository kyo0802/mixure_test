"""Detached local wrapper around the unchanged Phase 7 CLI."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor')]
if __name__=='__main__':
    from findmind_demo.jobs import run_job
    p=argparse.ArgumentParser();p.add_argument('--job-id',required=True);a=p.parse_args()
    run_job(ROOT,a.job_id)

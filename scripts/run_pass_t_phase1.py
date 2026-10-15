"""Offline read-only source inspection and gated Pass T Stage1a artifact delivery."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
sys.path.insert(0,str(root/'artifacts/pass_i/runtime/vendor'))
if __name__=='__main__':
    from memory_graph.pass_t.phase1 import run
    result=run()
    print(result['status'],result['event_packs_found'],result['stage0_blocked_with_reason'])

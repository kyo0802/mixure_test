"""Open the local native viewer; no server or internet required."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'src'),str(root/'artifacts/pass_i/runtime/vendor')]
if __name__=='__main__':
    from memory_graph.pass_t.phase1c_viewer import run
    run()

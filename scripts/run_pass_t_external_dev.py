"""Run without activating or modifying the annotation environment."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'artifacts/pass_i/runtime/vendor')]
from memory_graph.pass_t.external_dev.cli import main
if __name__ == '__main__': raise SystemExit(main())

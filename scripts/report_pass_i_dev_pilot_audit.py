"""Generate the fixed DEV pilot GPT-vs-human audit without inference."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from memory_graph.pass_i.dev_pilot_audit import render_report

if __name__ == '__main__':
    print(render_report())

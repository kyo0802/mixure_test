"""Freeze the DEV-only Evidence QC queue and report human review progress."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from memory_graph.pass_i.evidence_qc import report

if __name__ == '__main__':
    print(report())

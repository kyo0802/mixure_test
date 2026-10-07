"""Development-only evaluation. Review labels never enter preparation or inference."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
if __name__=='__main__':
    from memory_graph.reasoning.evaluation import evaluate
    print(evaluate())

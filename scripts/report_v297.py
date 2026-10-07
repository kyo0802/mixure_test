"""V297 post-run artifact entry point; no labels are consumed by inference."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.v297_physical_identity import evaluation
if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='review_sheets':evaluation.review_sheets(sys.argv[2])
    else:getattr(evaluation,cmd)()

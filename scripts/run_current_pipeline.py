"""Current clean Qwen direct-event runner and frozen-baseline verification."""
import argparse,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.reasoning.pipeline import prepare,run,verify,verify_reference
def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','run','verify','verify-reference']);args=parser.parse_args()
    result={'prepare':prepare,'run':run,'verify':verify,'verify-reference':verify_reference}[args.command]()
    print(result)
if __name__=='__main__':main()

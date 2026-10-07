"""Explicit experimental entrypoint; never changes the normal FindMind entrypoint."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.v295_reid.runner import run_set,freeze,smoke

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['development','freeze','known_val_regression','smoke'])
    command=parser.parse_args().command
    if command=='freeze':freeze()
    elif command=='smoke':smoke()
    else:run_set(command)

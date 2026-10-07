import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.v296_reid.runner import run_set,freeze
from memory_graph.v296_reid.calibration import calibrate
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['calibrate','development','freeze','known_val_regression','smoke'])
    cmd=parser.parse_args().command
    if cmd=='calibrate':calibrate()
    elif cmd=='freeze':freeze()
    elif cmd=='smoke':
        from memory_graph.v296_reid.smoke import run_smoke
        print(run_smoke(),flush=True)
    else:run_set(cmd)

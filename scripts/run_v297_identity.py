import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.v297_physical_identity.runner import run_set,freeze
from memory_graph.v297_physical_identity.calibration import calibrate
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['calibrate','development','freeze','known_val_regression','smoke']);cmd=p.parse_args().command
    if cmd=='calibrate':calibrate()
    elif cmd=='freeze':freeze()
    elif cmd=='smoke':
        from memory_graph.v297_physical_identity.smoke import run_smoke
        print(run_smoke(),flush=True)
    else:run_set(cmd)

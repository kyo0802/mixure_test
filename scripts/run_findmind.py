"""Sole current FindMind identity entrypoint; versioned runners are reference."""
from pathlib import Path
import argparse,sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.identity.pipeline import replay,raw,prepare,reason

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['replay','raw','prepare','reason'])
    p.add_argument('--output',required=True);p.add_argument('--video');p.add_argument('--source')
    a=p.parse_args()
    if a.command in {'raw','replay','prepare'} and not a.video:p.error('--video required')
    if a.command=='replay' and not a.source:p.error('--source required')
    result=(replay(a.source,a.video,a.output) if a.command=='replay' else raw(a.video,a.output) if a.command=='raw'
            else prepare(a.output,a.video) if a.command=='prepare' else reason(a.output))
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()

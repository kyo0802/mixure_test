import argparse
import json
from memory_graph.evaluation_v21.evaluator import evaluate

if __name__=='__main__':
    p=argparse.ArgumentParser(description='Post-inference only. GT cannot enter run_video_v21.')
    p.add_argument('output');p.add_argument('annotations')
    a=p.parse_args();_,assessment=evaluate(a.output,a.annotations);print(json.dumps(assessment,indent=2))

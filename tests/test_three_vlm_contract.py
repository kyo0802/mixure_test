"""Bounded CPU checks using nonvisual mock dictionaries; no physical GT claim."""
import sys,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor'),str(ROOT/'outputs/current_development/video_event_experiment/.deps')]
from memory_graph.experiments.three_vlm_contract import choose_uniform8,merge_intervals,validate_raw,interval_distance
from memory_graph.experiments.three_vlm_evaluation import match_one_to_one,event_metrics,eligible_coverage
class ContractTests(unittest.TestCase):
 def test_uniform_distinct_and_short(self):
  self.assertEqual(choose_uniform8(list(range(3)),[0,.2,.8]),[0,1,2]);p=[0,.01,.02,.03,.04,.05,.06,.07,.08,99];x=choose_uniform8(list(range(10)),p);self.assertEqual(len(set(x)),8);self.assertEqual(x,sorted(x))
 def test_coverage_union(self):self.assertEqual(merge_intervals([[0,4],[2,6],[6,7]]),[[0,7]])
 def test_invalid_not_negative(self):
  x=validate_raw('{"status":"NO_CONFIRMED_EVENT"', ['F0001']);self.assertFalse(x['raw']['full_valid']);self.assertIsNone(x['raw']['parsed'])
 def test_fence_separate(self):
  b=json.dumps({'status':'UNCERTAIN','observations':[],'events':[]});x=validate_raw('```json\n'+b+'\n```',['F0001']);self.assertFalse(x['raw']['json_valid']);self.assertTrue(x['normalized_body']['validation']['full_valid']);self.assertFalse(x['normalized_body']['authoritative'])
 def test_citation_unknown_and_contradiction(self):
  d={'status':'NO_CONFIRMED_EVENT','observations':[{'object':'mock','states':[{'frame':'X','state':'UNKNOWN'}]}],'events':[]};self.assertFalse(validate_raw(json.dumps(d),['F0001'])['raw']['citation_valid']);d['observations'][0]['states']=[{'frame':'F0001','state':'UNKNOWN'}]*2;self.assertFalse(validate_raw(json.dumps(d),['F0001'])['raw']['semantic_valid'])
 def test_closed_distances(self):
  for a,b,d in [([1,1],[0,2],0),([0,0],[0,2],0),([2,2],[0,2],0),([3,3],[0,2],1),([0,2],[1,3],0),([0,2],[2,4],0),([0,0],[0,0],0),([0,1],[1.2,2],.2)]:self.assertAlmostEqual(interval_distance(a,b),d)
 def test_one_to_one_tolerances_missing_identity(self):
  g={'type':'PICKUP','reviewed_object_id':'MOCK_ID','video_sha256':'MOCK_VIDEO','time_interval':[1,1]};p={**g,'time_interval':[1.2,1.2]}
  self.assertEqual(len(match_one_to_one([p,p],[g],0)),0)
  for t in (.2,.5):self.assertEqual(len(match_one_to_one([p,p],[g],t)),1)
  self.assertEqual(match_one_to_one([{**p,'reviewed_object_id':None}],[g],.5),[]);self.assertEqual(match_one_to_one([{**p,'time_interval':None}],[g],.5),[])
 def test_no_gt_no_metrics(self):self.assertIsNone(event_metrics([],[],[],.2)['metrics']);self.assertFalse(eligible_coverage({'coverage':'EXHAUSTIVE_ATTESTED','review_status':'UNREVIEWED'}))
if __name__=='__main__':unittest.main()

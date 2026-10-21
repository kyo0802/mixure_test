"""Read-only Graph mapping, real evidence, UI handoff and CPU import contracts."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor')]
from findmind_demo.graph_adapter import project,filter_graph,load_projection,search_focus,evidence_groups,node_id
from findmind_demo.graph_ui import reset_selection
from findmind_demo.sessions import discover_sessions
from findmind_demo.agent import ask
from findmind_demo.evidence import overlay


def fixture():
    """Deterministic record metadata only, not physical-event GT."""
    obs=[dict(observation_id='o'+str(i),object_category='phone',object_instance_candidate='c'+str(i),
        source_times_s=[float(i)],source_frame_indices=[i],source='CV') for i in range(3)]
    return dict(metadata=dict(observations=obs,scene_regions=[dict(region_id='r',region_label='table candidate',source_time_s=1.,source_frame_index=1)],
        location_observations=[dict(observation_id='l',object_observation_id='o1',object_candidate_id='c1',object_category='phone',region_id='r',source_time_s=1.,source_frame_index=1,grounding_status='CANDIDATE')],
        graph_edges=[dict(source='c1',target='o1',predicate='OBSERVED_BY'),dict(source='l',target='r',predicate='NEAR_REGION',grounding_status='CANDIDATE')]),
        events=[dict(hypothesis_id='e',type='PICKUP',object_category='phone',decision='REJECTED',before_refs=[],after_refs=[])])


class GraphTests(unittest.TestCase):
    def setUp(self):self.raw=fixture();self.graph=project(self.raw,'CPU_MOCK')
    def test_stable_session_scoped_ids_no_mutation(self):
        before=copy.deepcopy(self.raw);self.assertEqual(self.graph,project(self.raw,'CPU_MOCK'))
        self.assertEqual(before,self.raw)
        self.assertFalse({n['id'] for n in self.graph['nodes']}&{n['id'] for n in project(self.raw,'OTHER')['nodes']})
    def test_candidates_not_merged_or_authorized(self):
        self.assertEqual(len([n for n in self.graph['nodes'] if n['kind']=='Candidate']),3)
        self.assertFalse(any(n['kind']=='Identity' for n in self.graph['nodes']))
        self.raw['metadata']['observations'][0]['authorized_entity_id']='phone_01'
        self.assertFalse(any(n['kind']=='Identity' for n in project(self.raw,'x')['nodes']))
        self.raw['metadata']['observations'][0]['identity_authorization']={'capability':'CPU_MOCK'}
        self.assertEqual(len([n for n in project(self.raw,'x')['nodes'] if n['kind']=='Identity']),1)
    def test_record_and_relation_mapping(self):
        e=next(e for e in self.graph['edges'] if e['predicate']=='NEAR_REGION')
        self.assertEqual(e['source'],node_id('CPU_MOCK','SpatialEvidence','l'))
        self.assertEqual(e['source_pointer'],'/metadata/graph_edges/1')
        n=next(n for n in self.graph['nodes'] if n['record_id']=='l')
        self.assertEqual(n['source_pointer'],'/metadata/location_observations/0')
    def test_rejected_event_not_verified(self):
        self.assertEqual(next(n for n in self.graph['nodes'] if n['kind']=='Event')['status'],'REJECTED')
    def test_category_unknown_does_not_fabricate(self):
        self.assertFalse(filter_graph(self.graph,category='keys')['nodes'])
    def test_time_kind_status_and_predicate_filters(self):
        sub=filter_graph(self.graph,category='phone',time_range=(1.,1.))
        self.assertTrue(all(1. in n['times'] for n in sub['nodes']))
        self.assertTrue(any(n['kind']=='Region' for n in sub['nodes']))
        sub=filter_graph(self.graph,category='',kinds=['Event'],statuses=['REJECTED'])
        self.assertEqual(len(sub['nodes']),1)
        self.assertTrue(all(e['predicate']=='NEAR_REGION' for e in filter_graph(self.graph,predicates=['NEAR_REGION'])['edges']))
    def test_bound_and_exact_focus_priority(self):
        focus=node_id('CPU_MOCK','Observation','o0');sub=filter_graph(self.graph,limit=1,focus=[focus])
        self.assertEqual(sub['nodes'][0]['id'],focus);self.assertGreater(sub['hidden_by_limit'],0)
        with self.assertRaises(ValueError):filter_graph(self.graph,limit=301)
        sub=filter_graph(self.graph,focus=[focus],focus_only=True)
        self.assertTrue(all(n['record_id'] in {'o0','c0'} for n in sub['nodes']))

    def test_every_pointer_resolves_to_real_record(self):
        for n in self.graph['nodes']:
            value=self.raw
            for k in n['source_pointer'].strip('/').split('/'):
                value=value[int(k)] if isinstance(value,list) else value[k]
            self.assertIsNotNone(value)
    def test_no_continuous_presence_edges(self):
        self.assertFalse(any(e['predicate'] in {'SAME_ENTITY','PRESENT_BETWEEN'} for e in self.graph['edges']))
    def test_cross_session_selection_reset(self):
        state={'gv_identity':'old','gv_selection':'old_node','gv_evidence_old':'old','response':'keep'}
        reset_selection(state,'new');self.assertNotIn('gv_selection',state);self.assertEqual(state['response'],'keep')
    def test_evidence_frame_uses_exact_record(self):
        groups=evidence_groups(self.graph,node_id('CPU_MOCK','SpatialEvidence','l'))
        self.assertEqual(groups[0]['primary']['source_frame_index'],1)
        self.assertEqual(groups[0]['records'][0]['object_observation_id'],'o1')
    def test_imports_gpu_free_in_new_process(self):
        code="import sys;sys.path[:0]="+repr([str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor')])+";import findmind_demo.graph_adapter,findmind_demo.graph_ui;assert not {'torch','vllm','ultralytics','transformers'} & set(sys.modules)"
        p=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)


class RealGraphTests(unittest.TestCase):
    def setUp(self):
        rows=discover_sessions(ROOT);self.sid=next((s['id'] for s in rows if s['id'].startswith('video_932b70')),None)
        if not self.sid:self.skipTest('Existing real test8 session is local only')
        self.graph,self.manifest=load_projection(ROOT,self.sid)
    def test_real_three_records_two_times_zero_verified(self):
        candidates=[n for n in self.graph['nodes'] if n['kind']=='SpatialEvidence' and n['category']=='phone' and n['status']=='CANDIDATE']
        self.assertEqual(len(candidates),3)
        self.assertEqual({round(t,6) for n in candidates for t in n['times']},{6.008333,13.803333})
        self.assertFalse(any(n['kind']=='Identity' for n in self.graph['nodes']))
        self.assertFalse(any(n['status']=='VERIFIED' for n in self.graph['nodes']))
    def test_exact_search_mapping_and_real_overlay(self):
        response=ask(ROOT,self.sid,'我的手機在哪裡？');focus=search_focus(self.graph,response)
        self.assertEqual(focus['mapping'],'EXACT_RECORD_IDS')
        self.assertEqual(len([n for n in self.graph['nodes'] if n['id'] in focus['focus'] and n['kind']=='SpatialEvidence']),3)
        nid=next(n['id'] for n in self.graph['nodes'] if n['kind']=='SpatialEvidence' and n['record_id']==response['result']['candidates'][0]['observation_id'])
        data=overlay(ROOT,self.sid,evidence_groups(self.graph,nid)[0])
        self.assertEqual(data['frame']['source_frame_index'],414)
        self.assertAlmostEqual(data['frame']['source_time_s'],13.803333333333333)
    def test_changed_graph_is_rejected_even_with_cache(self):
        from findmind_demo.graph_adapter import _cached_projection
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'memory_graph.json';path.write_text('{}')
            with self.assertRaisesRegex(ValueError,'Graph changed'):_cached_projection(str(path),'wrong','CPU_MOCK')
    def test_missing_corrupt_and_cross_session_evidence(self):
        from findmind_demo.evidence import scoped_file
        with self.assertRaises(ValueError):scoped_file(ROOT,ROOT/'artifacts/findmind_sessions'/self.sid,'README.md')
        nid=next(n['id'] for n in self.graph['nodes'] if n['kind']=='SpatialEvidence' and n['category']=='phone' and n['status']=='CANDIDATE')
        groups=evidence_groups(self.graph,nid);groups[0]['primary']['source_frame_index']=99999999
        with self.assertRaises(ValueError):overlay(ROOT,self.sid,groups[0])
    def test_streamlit_search_graph_return_and_filters(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'apps/findmind_demo.py'),default_timeout=30).run()
        app.selectbox[0].set_value(self.sid).run();app.radio[1].set_value('尋找物品').run()
        next(b for b in app.button if b.label=='在記憶圖譜中查看 / View in Memory Graph').click();app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['demo_view'],'Memory Graph / 記憶圖譜')
        self.assertEqual(app.session_state['gv_handoff']['search_status'],'POSSIBLE_LOCATIONS')
        self.assertEqual(app.session_state['recorded_session'],self.sid)
        next(b for b in app.button if b.label=='返回尋找物品 / Back to Find Item').click();app.run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state['recorded_session'],self.sid)
        app.text_input[0].set_value('幫我找鑰匙');next(b for b in app.button if b.label=='查找線索').click();app.run()
        next(b for b in app.button if b.label=='在記憶圖譜中查看 / View in Memory Graph').click();app.run()
        self.assertFalse(app.exception);self.assertEqual(app.session_state['gv_category'],'keys')
        self.assertTrue(any('沒有原始紀錄' in x.value for x in app.info))

    def test_streamlit_native_time_filter_and_session_switch(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'apps/findmind_demo.py'),default_timeout=30).run()
        app.selectbox[0].set_value(self.sid).run();app.radio[1].set_value('Memory Graph / 記憶圖譜').run()
        app.slider[0].set_value((6.,7.)).run();self.assertFalse(app.exception)
        self.assertTrue(all('13.803' not in option for option in app.selectbox if option.label=='選取節點 / Selected node' for option in option.options))
        other=next((s['id'] for s in discover_sessions(ROOT) if s['queryable'] and s['id']!=self.sid),None)
        if other:
            app.selectbox[0].set_value(other).run();self.assertFalse(app.exception)
            self.assertNotIn(self.sid,app.session_state['gv_selection'])
            self.assertFalse(app.session_state.filtered_state.get('gv_handoff'))

if __name__=='__main__':unittest.main()

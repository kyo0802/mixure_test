"""Deterministic CPU contracts, no GPU initialization or real media access."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor')]
from memory_graph.integration.fresh_video import (validate_timeline,sampling_plan,select_localization,
    windows_with_frames,query_category,save,search_session,assemble_memory)
from memory_graph.integration.adapters import sha,adapt_cv,adapt_nemotron
from memory_graph.integration.pipeline import build_memory


def video():
    times=[0.,.04,.09,.2,.43,.9,1.1,1.8,2.2,2.9,3.8,4.1,4.6,5.0,5.9,6.0]
    return dict(video_id='arbitrary-new-scene',source_sha256='mock',source_duration_s=6.1,presentation_start_s=0,
        width=100,height=100,time_base='1/100',fps=30,frame_count=len(times),
        frame_timeline=[dict(index=i,pts=round(t*100),source_time_s=t,time_base='1/100') for i,t in enumerate(times)])


class FreshVideoTests(unittest.TestCase):
    def test_vfr_windows_cover_unique_native_indices(self):
        v=video();validate_timeline(v['frame_timeline']);w,cv=sampling_plan(v,3,2)
        covered=[i for x in w for i in range(x['source_frame_interval_closed'][0],x['source_frame_interval_closed'][1]+1)]
        self.assertEqual(covered,list(range(v['frame_count'])))
        self.assertTrue(all(0<len(x['selected_indices'])<=8 for x in w))
        self.assertEqual(len(cv),len(set(cv)))
        self.assertNotEqual(v['frame_timeline'][7]['source_time_s'],7/30)
        self.assertTrue(all(i in cv for x in w for i in x['selected_indices']))

    def test_nonmonotonic_native_pts_rejected(self):
        v=video();v['frame_timeline'][2]['source_time_s']=0
        with self.assertRaisesRegex(ValueError,'MONOTONIC'):validate_timeline(v['frame_timeline'])

    def test_query_categories(self):
        for q,c in [('Where is my phone?','phone'),('Where are my keys?','keys'),('bottle','bottle'),('Where is my wallet?','wallet')]:
            self.assertEqual(query_category(q),c)

    def test_localization_bounded_and_reasoned(self):
        f=[dict(source_frame_index=i,source_time_s=float(i)) for i in range(30)]
        o=[dict(source='CV',object_category='phone',source_frame_indices=[i]) for i in range(10)]
        chosen=select_localization(f,o,'phone',6)
        self.assertEqual(len(chosen),6)
        self.assertEqual(len({x['source_frame_index'] for x in chosen}),6)
        self.assertEqual(len({x['selection_reason'] for x in chosen}),2)
        self.assertEqual(select_localization(f,o,'phone',0),[])

    def test_track_never_identity(self):
        t=[dict(track_id='phone_01',detector_class='cell phone',observations=[dict(frame_index=2,bbox=[1,2,5,8],confidence=.9)])]
        o=adapt_cv(t,dict(aliases=[],authorizations=[],final_ledger=[]),video(),dict(tracks='mock',identity='mock'))
        self.assertIsNone(o[0]['authorized_entity_id'])
        self.assertEqual(o[0]['source_times_s'],[.09])

    def test_invalid_vlm_not_no_event(self):
        v=video();w=dict(window_id='new',video_id=v['video_id'],source_video_sha256='mock',
            frames=[dict(alias='F0001',source_frame_index=0,native_pts_s=0.)])
        o,h,r=adapt_nemotron('bad-json',w,v,'mock')
        self.assertEqual(r['response_status'],'INVALID_OUTPUT');self.assertEqual(o,[]);self.assertEqual(h,[])

    def test_no_outputs_yields_honest_partial_memory(self):
        with tempfile.TemporaryDirectory() as d:
            m,errors=assemble_memory(ROOT,Path(d),dict(video=video(),frames=[],windows=[],query='phone',localization_query='smartphone'))
            self.assertEqual(m.metadata['observations'],[])
            self.assertEqual(m.events,[])
            self.assertEqual(errors,[])

    def test_saved_query_gpu_free_and_hash_guard(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);m=build_memory('new',[],[],[],[])
            save(p/'memory_graph.json',m.model_dump(mode='json'));save(p/'source_manifest.json',dict(frames=[]))
            save(p/'run_receipt.json',dict(graph_sha256=sha(p/'memory_graph.json'),manifest_sha256=sha(p/'source_manifest.json'),
                stages=[dict(stage='nemotron',status='FAILED')]))
            with patch('subprocess.Popen',side_effect=AssertionError('QUERY_MUST_NOT_SPAWN')):
                r=search_session(ROOT,p,'phone')
            self.assertEqual(r['status'],'UNKNOWN');self.assertFalse(r['query_reloaded_models'])
            self.assertEqual(len(r['incomplete_stages']),1)
            (p/'memory_graph.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'GRAPH_HASH'):search_session(ROOT,p,'phone')

    def test_aliases_preserve_native_mapping(self):
        v=video();windows,_=sampling_plan(v,3,2)
        frames=[dict(source_frame_index=r['index'],native_pts_s=r['source_time_s']) for r in v['frame_timeline']]
        result=windows_with_frames(windows,frames)
        for w in result:
            self.assertEqual(len(w['frames']),len(w['selected_indices']))
            for f in w['frames']:self.assertEqual(f['native_pts_s'],v['frame_timeline'][f['source_frame_index']]['source_time_s'])


if __name__=='__main__':unittest.main()

"""User-journey checks. CPU fixtures are not physical-event ground truth."""
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch,MagicMock
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor')]
from findmind_demo import agent,jobs,sessions,evidence
from memory_graph.integration.adapters import sha
from memory_graph.integration.pipeline import build_memory


def fixture(root,name='session_a'):
    path=root/'artifacts/findmind_sessions'/name;path.mkdir(parents=True)
    graph=build_memory(name,[],[],[],[])
    (path/'memory_graph.json').write_text(graph.model_dump_json(),encoding='utf8')
    manifest=dict(video=dict(video_id=name,source_sha256='mock',original_filename=name+'.mp4',presentation_duration_s=1,frame_timeline=[]),
        created_utc='2026-10-21T00:00:00+00:00',frames=[])
    (path/'source_manifest.json').write_text(json.dumps(manifest),encoding='utf8')
    receipt=dict(session_id=name,graph_sha256=sha(path/'memory_graph.json'),manifest_sha256=sha(path/'source_manifest.json'),
        stages=[dict(stage='cv',status='COMPLETE')],elapsed_s=1,assembly_errors=[])
    (path/'run_receipt.json').write_text(json.dumps(receipt),encoding='utf8')
    return path,manifest,receipt


def candidate(frame=1,region='table_a',verified=False):
    return dict(source_frame_index=frame,source_time_s=1.25,region_id=region,grounding_status='VERIFIED' if verified else 'CANDIDATE',
        persistent_entity_id='enrolled_a' if verified else None,location_label='tabletop candidate',ordering_unresolved_tie=True)


class DemoTests(unittest.TestCase):
    def test_bilingual_queries(self):
        for q in ['Where is my phone?','Where did you last see my phone?','Find my phone.',
            'Show me the last observation of my phone.','我的手機在哪裡？','幫我找手機。','手機最後出現在哪裡？']:
            self.assertEqual(agent.interpret(q)['category'],'phone')
        self.assertEqual(agent.interpret('Where are my keys?')['category'],'keys')

    def test_unsupported_and_ambiguous_request(self):
        for q in ['', 'Find my phone and wallet','What time is it?','phone_01']:
            with self.assertRaises(ValueError):agent.interpret(q)
        self.assertEqual(agent.interpret('entity_a',['entity_a'])['entity_id'],'entity_a')
        with self.assertRaises(ValueError):agent.interpret('phone',[],explicit_entity='unknown_entity')

    def test_groups_preserve_order_without_identity_merge(self):
        a,b=candidate(8),candidate(3);rows=[a,b,deepcopy(b)]
        groups=agent.group_candidates(rows)
        self.assertEqual([g['primary']['source_frame_index'] for g in groups],[8,3])
        self.assertEqual(len(groups[1]['records']),2)
        self.assertIsNone(groups[1]['primary']['persistent_entity_id'])

    def test_answers_distinguish_candidate_verified_unknown(self):
        intent=dict(category='phone',language='zh',entity_id=None)
        c=candidate();groups=agent.group_candidates([c])
        answer=agent.describe(dict(status='POSSIBLE_LOCATIONS'),intent,groups)
        self.assertIn('候選',answer);self.assertIn('不能確認',answer);self.assertNotIn('可信位置',answer)
        self.assertIn('無法',agent.describe(dict(status='UNKNOWN'),intent,[]))
        self.assertIn('可信位置',agent.describe(dict(status='LAST_CONFIRMED_LOCATION'),dict(intent,entity_id='enrolled_a'),agent.group_candidates([candidate(verified=True)])))

    def test_discovery_hash_guard_and_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path,_,_=fixture(root)
            self.assertTrue(sessions.discover_sessions(root)[0]['queryable'])
            sessions.load_session(root,'session_a')
            for bad in ['../session_a','a/b','C:\\Windows']:
                with self.assertRaises(ValueError):sessions.session_path(root,bad)
            (path/'memory_graph.json').write_text('{}')
            with self.assertRaises(ValueError):sessions.load_session(root,'session_a')

    def test_unknown_query_no_gpu_or_subprocess(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);fixture(root)
            with patch('subprocess.Popen',side_effect=AssertionError('No inference during search')):
                first=agent.ask(root,'session_a','我的手機在哪裡？')
                second=agent.ask(root,'session_a','Where did you last see my phone?')
            self.assertEqual(first['result']['status'],'UNKNOWN');self.assertEqual(second['groups'],[])
            self.assertFalse(any(k in sys.modules for k in ['torch','vllm','ultralytics','transformers']))

    def test_evidence_outside_session_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a,_,_=fixture(root);b,_,_=fixture(root,'session_b')
            file=b/'secret.png';file.write_bytes(b'not image')
            with self.assertRaises(ValueError):evidence.scoped_file(root,a,str(file))

    def test_evidence_wrong_frame_and_tampered_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path,m,r=fixture(root)
            with self.assertRaises(ValueError):evidence.source_frame(root,'session_a',99)
            f=path/'frame.png';f.write_bytes(b'original')
            m['video']['frame_timeline']=[dict(source_time_s=0)]
            m['frames']=[dict(source_frame_index=0,path=str(f),sha256=sha(f),source_video_sha256='mock',source_time_s=0)]
            (path/'source_manifest.json').write_text(json.dumps(m));r['manifest_sha256']=sha(path/'source_manifest.json')
            (path/'run_receipt.json').write_text(json.dumps(r))
            f.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'hash'):evidence.source_frame(root,'session_a',0)

    def test_upload_size_type_and_content_address(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);data=b'\x00\x00\x00\x18ftypisom'+b'payload'
            a,d=jobs.store_upload(root,'../clip.mp4',data)
            b,_=jobs.store_upload(root,'another.mp4',data)
            self.assertEqual(a,b);self.assertEqual(a.stem,d)
            for name,value,limit in [('bad.txt',data,1),('bad.mp4',b'invalid',1),('big.mp4',data,0)]:
                with self.assertRaises(ValueError):jobs.store_upload(root,name,value,limit)

    def test_submission_idempotent_and_gpu_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path,_=jobs.store_upload(root,'a.mp4',b'0000ftypisomdata')
            proc=MagicMock(pid=999999)
            with patch.object(jobs.subprocess,'Popen',return_value=proc) as popen:
                token='a'*32;jobs.submit(root,path,'phone',token);jobs.submit(root,path,'phone',token)
                self.assertEqual(popen.call_count,1)
                with self.assertRaises(RuntimeError):jobs.submit(root,path,'phone','b'*32)
            with patch.object(jobs,'alive',return_value=False):state=jobs.poll(root,token)
            self.assertEqual(state['status'],'FAILED');self.assertIn('中斷',state['error'])

    def test_background_wrapper_invokes_real_phase7_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);session,_,_=fixture(root);path,_=jobs.store_upload(root,'a.mp4',b'0000ftypisomdata')
            token='c'*32
            with patch.object(jobs.subprocess,'Popen',return_value=MagicMock(pid=123)):jobs.submit(root,path,'phone',token)
            child=MagicMock(pid=555);child.stdout=iter(['SESSION '+str(session)+'\n']);child.wait.return_value=0;child.poll.return_value=0
            with patch.object(jobs.subprocess,'Popen',return_value=child) as spawn:jobs.run_job(root,token)
            command=spawn.call_args.args[0]
            self.assertIn(str(root/'scripts/run_findmind_video.py'),command)
            self.assertIn('--video',command);self.assertIn(str(path),command)
            state=jobs.poll(root,token);self.assertEqual(state['status'],'COMPLETED',state);self.assertEqual(state['stages']['ready'],'COMPLETED')
            self.assertFalse((root/'artifacts/findmind_jobs/gpu.lock').exists())
            with self.assertRaises(RuntimeError):jobs.run_job(root,token)

    def test_failed_pipeline_retains_error_log(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path,_=jobs.store_upload(root,'a.mp4',b'0000ftypisomdata');token='d'*32
            with patch.object(jobs.subprocess,'Popen',return_value=MagicMock(pid=123)):jobs.submit(root,path,'phone',token)
            child=MagicMock(pid=555);child.stdout=iter(['decoder failed\n']);child.wait.return_value=1;child.poll.return_value=1
            with patch.object(jobs.subprocess,'Popen',return_value=child):jobs.run_job(root,token)
            self.assertEqual(jobs.poll(root,token)['status'],'FAILED')
            self.assertIn('decoder failed',(jobs.job_path(root,token)/'pipeline.log').read_text(),jobs.poll(root,token))

    def test_timeout_partial_graph_keeps_gpu_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);session,_,receipt=fixture(root)
            failed=dict(stage='nemotron',status='FAILED',exit_code=-9)
            receipt['stages'].append(failed)
            (session/'run_receipt.json').write_text(json.dumps(receipt))
            (session/'nemotron_stage.json').write_text(json.dumps(failed))
            path,_=jobs.store_upload(root,'a.mp4',b'0000ftypisomdata');token='e'*32
            with patch.object(jobs.subprocess,'Popen',return_value=MagicMock(pid=123)):jobs.submit(root,path,'phone',token)
            child=MagicMock(pid=555);child.stdout=iter(['SESSION '+str(session)+'\n']);child.wait.return_value=0;child.poll.return_value=0
            with patch.object(jobs.subprocess,'Popen',return_value=child):jobs.run_job(root,token)
            state=jobs.poll(root,token)
            self.assertEqual(state['status'],'PARTIAL');self.assertEqual(state['stages']['nemotron'],'FAILED')
            self.assertTrue((root/'artifacts/findmind_jobs/gpu.lock').exists())


class StreamlitJourneyTests(unittest.TestCase):
    def test_recorded_mode_real_graph_search_and_new_mode(self):
        from streamlit.testing.v1 import AppTest
        saved=[s for s in sessions.discover_sessions(ROOT) if s['queryable']]
        if not saved:self.skipTest('No saved real session available')
        app=AppTest.from_file(str(ROOT/'apps/findmind_demo.py'),default_timeout=30).run()
        # This assertion concerns the known test8 fixture, not whichever upload is newest.
        test8=next((s['id'] for s in saved if s['id'].startswith('video_932b70')),None)
        if not test8:self.skipTest('Known test8 evidence session unavailable')
        app.selectbox[0].set_value(test8).run()
        app.radio[1].set_value('尋找物品').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['response']['result']['status'],'POSSIBLE_LOCATIONS')
        app.text_input[0].set_value('Where did you last see my phone?')
        next(b for b in app.button if b.label=='查找線索').click();app.run()
        self.assertFalse(app.exception);self.assertIn('category candidates',app.session_state['response']['answer'])
        app.text_input[0].set_value('幫我找鑰匙。');next(b for b in app.button if b.label=='查找線索').click();app.run()
        self.assertEqual(app.session_state['response']['result']['status'],'UNKNOWN')
        app.radio[0].set_value('新影片分析').run();self.assertFalse(app.exception)
        next(b for b in app.button if b.label=='開始分析').click();app.run()
        self.assertTrue(any('先選擇' in e.value for e in app.error))

    def test_session_switch_discards_old_response(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as temp:
            path,manifest,receipt=fixture(Path(temp))
            rows=[dict(id=n,label=n,created='2026-10-21',status='COMPLETED',queryable=True,evidence=False) for n in ['demo_a','demo_b']]
            def fake_ask(root,sid,text,*args):return dict(session_id=sid,intent=dict(category='phone',language='zh',entity_id=None),
                result=dict(status='UNKNOWN',candidates=[],incomplete_stages=[]),groups=[],answer=sid,elapsed_s=.01,last_observation=None)
            with patch('findmind_demo.sessions.discover_sessions',return_value=rows),patch('findmind_demo.sessions.load_session',return_value=(path,manifest,receipt)),\
                 patch('findmind_demo.sessions.enrolled_entities',return_value=[]),patch('findmind_demo.agent.ask',side_effect=fake_ask),patch('findmind_demo.agent.history',return_value=[]):
                app=AppTest.from_file(str(ROOT/'apps/findmind_demo.py'),default_timeout=30).run()
                app.radio[1].set_value('尋找物品').run()
                self.assertEqual(app.session_state['response']['session_id'],'demo_a')
                app.selectbox[0].set_value('demo_b').run()
                self.assertFalse(app.exception);self.assertEqual(app.session_state['response']['session_id'],'demo_b')


if __name__=='__main__':unittest.main()

"""Persistent manual-check semantics and real saved-memory UI integration."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor')]
from findmind_demo.checklist_store import ChecklistStore
from findmind_demo.departure import evaluate,search_handoff
from findmind_demo.sessions import discover_sessions
from findmind_demo.agent import ask
from memory_graph.integration.adapters import sha


class ChecklistTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=ChecklistStore(self.root)
    def tearDown(self):self.tmp.cleanup()

    def test_defaults_are_config_not_detection_and_persist(self):
        data=self.store.read();self.assertEqual([i['category'] for i in data['items']],['phone','keys','wallet'])
        self.assertEqual(data['checks'],[])
        self.assertEqual(ChecklistStore(self.root).read(),data)

    def test_add_rename_disable_remove(self):
        item=self.store.add('雨傘','umbrella')
        self.store.update(item['item_id'],label='我的傘',category='umbrella',enabled=False)
        check=self.store.start('memory_a');self.assertNotIn(item['item_id'],[i['item_id'] for i in check['items']])
        self.assertEqual(self.store.read()['items'][-1]['label'],'我的傘')
        self.store.remove(item['item_id']);self.assertEqual(len(self.store.read()['items']),3)

    def test_start_resume_and_idempotent_new_request(self):
        first=self.store.start('memory_a');self.assertEqual(self.store.start('memory_a')['check_id'],first['check_id'])
        a=self.store.start('memory_a',new=True,request_id='click_1');b=self.store.start('memory_a',new=True,request_id='click_1')
        self.assertEqual(a['check_id'],b['check_id']);self.assertEqual(len(self.store.read()['checks']),2)

    def test_confirm_undo_and_rerun_deduplication(self):
        c=self.store.start('memory_a');item=c['items'][0]['item_id']
        a=self.store.set_packed(c['check_id'],item,True);b=self.store.set_packed(c['check_id'],item,True)
        self.assertEqual(len(b['events']),1);self.assertEqual(a,b)
        undone=self.store.set_packed(c['check_id'],item,False);self.assertEqual(len(undone['events']),2)
        self.assertFalse(undone['confirmations'][item]['packed'])
        self.assertEqual(undone['events'][0]['source'],'USER_MANUAL_CONFIRMATION')

    def test_new_check_never_carries_old_confirmation(self):
        c=self.store.start('memory_a');old=self.store.set_packed(c['check_id'],c['items'][0]['item_id'],True)
        fresh=self.store.start('memory_a',new=True)
        self.assertEqual(fresh['confirmations'],{});self.assertEqual(fresh['status'],'OPEN')
        with self.assertRaises(ValueError):self.store.set_packed(old['check_id'],old['items'][0]['item_id'],False)
        saved=next(x for x in ChecklistStore(self.root).read()['checks'] if x['check_id']==old['check_id'])
        self.assertEqual(saved,old)

    def test_memory_switch_isolates_checks_and_manual_status(self):
        a=self.store.start('memory_a');self.store.set_packed(a['check_id'],a['items'][0]['item_id'],True)
        b=self.store.start('memory_b')
        self.assertEqual(b['confirmations'],{});self.assertEqual(self.store.active('memory_a')['check_id'],a['check_id'])
        self.assertNotEqual(self.store.active('memory_b')['check_id'],a['check_id'])

    def test_history_snapshot_survives_preferences_change(self):
        c=self.store.start('memory_a');i=c['items'][0]
        self.store.update(i['item_id'],label='新的名稱',category='bottle',enabled=False)
        self.store.remove(c['items'][1]['item_id'])
        self.assertEqual(self.store.active('memory_a')['items'],c['items'])
        fresh=self.store.start('memory_a',new=True);self.assertEqual(len(fresh['items']),1)

    def test_all_confirmed_and_empty_list_not_false_complete(self):
        c=self.store.start('memory_a')
        for i in c['items']:c=self.store.set_packed(c['check_id'],i['item_id'],True)
        self.assertEqual(c['status'],'COMPLETE')
        for i in self.store.read()['items']:self.store.remove(i['item_id'])
        self.assertEqual(self.store.start('memory_a',new=True)['status'],'NO_ENABLED_ITEMS')

    def test_demo_records_are_not_real_packing_claims(self):
        c=self.store.start('memory_a',purpose='DEMO_PRESENTATION')
        c=self.store.set_packed(c['check_id'],c['items'][0]['item_id'],True)
        self.assertEqual(c['events'][0]['source'],'UI_DEMO_CONFIRMATION')

    def test_evidence_does_not_confirm_packing(self):
        c=self.store.start('memory_a')
        response=dict(groups=[dict(primary=dict(source_time_s=12,location_label='tabletop candidate'))],last_observation=None,result=dict(status='POSSIBLE_LOCATIONS'))
        with patch('findmind_demo.departure.load_session'),patch('findmind_demo.departure.ask',return_value=response):
            result=evaluate(self.root,c,'memory_a')
        self.assertEqual(result['pending'],3)
        self.assertTrue(all(not i['possession_verified'] for i in result['items']))
        self.assertTrue(all(i['status']=='HAS_LOCATION_CANDIDATE' for i in result['items']))
        self.assertEqual(self.store.active('memory_a')['events'],[])

    def test_unknown_not_forgotten_and_memory_mismatch_rejected(self):
        c=self.store.start('memory_a');response=dict(groups=[],last_observation=None,result=dict(status='UNKNOWN'))
        with patch('findmind_demo.departure.load_session'),patch('findmind_demo.departure.ask',return_value=response):
            result=evaluate(self.root,c,'memory_a')
        self.assertEqual(result['items'][0]['status'],'NO_RELEVANT_OBSERVATION')
        self.assertIn('不表示',result['items'][0]['message']);self.assertFalse(result['complete'])
        with self.assertRaises(ValueError):evaluate(self.root,c,'memory_b')

    def test_handoff_preserves_memory_category_and_check(self):
        c=self.store.start('memory_a');item=self.store.add('雨傘','umbrella')
        h=search_handoff(c,item)
        self.assertEqual((h['session_id'],h['check_id'],h['category']),('memory_a',c['check_id'],'umbrella'))
        self.assertEqual(h['question'],'雨傘在哪裡？')


class DepartureIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rows=[s for s in discover_sessions(ROOT) if s['queryable']]
        if not rows:raise unittest.SkipTest('Real saved session not available')
        cls.sid=rows[0]['id']

    def test_real_graph_reminder_then_manual_completion_no_graph_write(self):
        graph=ROOT/'artifacts/findmind_sessions'/self.sid/'memory_graph.json';before=sha(graph)
        with tempfile.TemporaryDirectory() as temp:
            store=ChecklistStore(Path(temp));c=store.start(self.sid)
            result=evaluate(ROOT,c,self.sid)
            self.assertEqual(result['items'][0]['evidence_status'],'HAS_LOCATION_CANDIDATE')
            self.assertEqual(result['items'][1]['status'],'NO_RELEVANT_OBSERVATION')
            self.assertEqual(result['pending'],3)
            for i in c['items']:c=store.set_packed(c['check_id'],i['item_id'],True)
            self.assertTrue(evaluate(ROOT,c,self.sid)['complete'])
            self.assertEqual(sha(graph),before)
            self.assertFalse(any(n in sys.modules for n in ['torch','vllm','ultralytics','transformers']))

    def test_explicit_custom_category_uses_existing_search_api(self):
        r=ask(ROOT,self.sid,'雨傘在哪裡？',category_hint='umbrella')
        self.assertEqual(r['intent']['category'],'umbrella');self.assertEqual(r['result']['status'],'UNKNOWN')
        self.assertEqual(ask(ROOT,self.sid,'手機在哪裡？',category_hint='smartphone')['intent']['category'],'phone')

    def test_streamlit_full_departure_search_return_confirm_reset(self):
        from streamlit.testing.v1 import AppTest
        with tempfile.TemporaryDirectory() as temp:
            store=ChecklistStore(Path(temp));store.read()
            with patch('findmind_demo.checklist_store.ChecklistStore',return_value=store),patch('findmind_demo.departure_ui.ChecklistStore',return_value=store):
                app=AppTest.from_file(str(ROOT/'apps/findmind_demo.py'),default_timeout=30).run()
                next(b for b in app.button if b.label=="我要出門了 / I'm Leaving").click();app.run()
                self.assertFalse(app.exception)
                self.assertTrue(any('3 件' in w.value for w in app.warning))
                next(b for b in app.button if b.label=='尋找 手機 / Find').click();app.run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state['response']['intent']['category'],'phone')
                self.assertEqual(app.session_state['response']['result']['status'],'POSSIBLE_LOCATIONS')
                self.assertEqual(app.text_input[0].value,'手機在哪裡？')
                self.assertFalse(store.active(self.sid)['confirmations'])
                next(b for b in app.button if b.label=='返回出門檢查 / Back to checklist').click();app.run()
                for _ in range(3):
                    next(b for b in app.button if b.label=='我已帶妥 / Confirm packed').click();app.run()
                    self.assertFalse(app.exception)
                self.assertEqual(store.active(self.sid)['status'],'COMPLETE')
                self.assertTrue(any('所有必帶' in s.value for s in app.success))
                next(b for b in app.button if b.label=='開始新檢查 / New Check').click();app.run()
                self.assertEqual(store.active(self.sid)['confirmations'],{})
                # A new AppTest script session simulates application/UI restart.
                again=AppTest.from_file(str(ROOT/'apps/findmind_demo.py'),default_timeout=30).run()
                again.radio[1].set_value('我要出門了').run()
                self.assertFalse(again.exception)
                self.assertEqual(len(store.read()['checks']),2)


if __name__=='__main__':unittest.main()

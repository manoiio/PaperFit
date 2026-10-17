"""Native UI actions, fake transport only; production UI has no mock switch."""
from unittest import TestCase
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from streamlit.testing.v1 import AppTest
from web.session import WebSession
from ai.short_spec import Settings
import json
ROOT=Path(__file__).resolve().parents[1]

class StructureUIAcceptance(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  status=patch('web.structure_ui.config_status',return_value={'configured':True,'model':'deepseek-flash','message':'mock'});status.start();self.addCleanup(status.stop)
  self.s=WebSession(self.tmp.name);self.s.set_mode('academic');self.s.load((ROOT/'samples/phase41/structure.docx').read_bytes(),'合成.docx')
  self.at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);self.at.session_state.workflow=self.s;self.at.run();self.at.button(key='smart-entry').click().run();self.at.button(key='onepass-legacy').click().run()
 def test_explicit_request_cached_then_original_scope_and_shortcut(self):
  def transport(req,timeout):
   sent=json.loads(json.loads(req.data)['messages'][1]['content']);labels=json.loads((ROOT/'samples/phase41/labels.json').read_text())['paragraphs']
   rows=[{'id':r['id'],'role':labels[int(r['id'][2:])-1]['role'],'evidence':r['text'],'reason':'合成结构测试'} for r in sent['candidates']]
   return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'suggestions':rows})}}]})
  with patch('web.structure_session.settings',return_value=Settings('synthetic-placeholder')),patch('ai.structure.http_post',side_effect=transport) as post:
   self.at.run();self.assertEqual(post.call_count,0)
   self.at.button(key='structure-request').click().run();self.assertFalse(self.at.exception);self.assertEqual(post.call_count,1);self.assertIsNone(self.s.report)
   self.at.button(key='structure-request').click().run();self.assertEqual(post.call_count,1)
   self.assertTrue(any('AI补充' in m.value for m in self.at.markdown))
   self.at.button(key='smart-confirm-scope').click().run();self.assertIsNotNone(self.s.report);self.assertEqual(self.s.paragraph_types['9'],'heading1')
   self.at.button(key='smart-execute').click().run();self.assertTrue(self.s.downloads());self.at.run();self.assertEqual(post.call_count,1)
 def test_failure_falls_back_and_no_private_cache_on_project(self):
  with patch('web.structure_session.settings',return_value=Settings('synthetic-placeholder')),patch('ai.structure.http_post',side_effect=TimeoutError()) as post:
   self.at.button(key='structure-request').click().run();self.assertFalse(self.at.exception);self.assertEqual(post.call_count,1);self.assertIsNone(self.s.confirmed)
   self.at.button(key='smart-confirm-scope').click().run();self.assertIsNotNone(self.s.report);self.assertEqual(post.call_count,1)

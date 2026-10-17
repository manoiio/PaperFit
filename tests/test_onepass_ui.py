"""Native controls only in tests; production has no fixture state injection switch."""
from unittest import TestCase
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from streamlit.testing.v1 import AppTest
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1]

class OnePassUIAcceptance(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.s=WebSession(self.tmp.name);self.s.set_mode('academic');self.s.load((ROOT/'samples/phase31/errors.docx').read_bytes(),'合成.docx')
  self.at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);self.at.session_state.workflow=self.s;self.at.session_state['workspace-smart']=True;self.at.run()
 def test_ordinary_start_download_no_technical_stages(self):
  self.assertFalse(any(b.label in ('接受此范围并检查','一键智能修正','确认采用此副本') for b in self.at.button))
  self.assertFalse(any(b.key=='workspace-nav-2' for b in self.at.button))
  self.at.button(key='onepass-start').click().run();self.assertFalse(self.at.exception);self.assertEqual(len(self.s.history),1)
  self.assertTrue(any(b.label=='下载修正版' for b in self.at.get('download_button')))
  self.at.run();self.assertEqual(len(self.s.history),1);self.assertTrue(self.at.button(key='onepass-start').disabled)
  self.at.button(key='onepass-legacy').click().run();self.assertFalse(self.at.exception);self.assertTrue(any(b.label=='分析范围建议（不修改论文）' for b in self.at.button))
 def test_supplement_failure_plain_exception_template_continue(self):
  self.at.text_input(key='onepass-extra-'+self.s.task_dir.name).set_value('正文改为四号、2倍行距').run()
  with patch('ai.short_spec.parse_requirements',side_effect=TimeoutError()):
   self.at.button(key='onepass-start').click().run();self.assertFalse(self.at.exception);self.assertIsNone(self.s.result)
   choices=[x for x in self.at.selectbox if x.label=='您的选择'];self.assertEqual(len(choices),1);self.assertIsNone(choices[0].value)
   self.assertTrue(self.at.button(key='onepass-continue').disabled)
   choices[0].set_value('template').run();self.at.button(key='onepass-continue').click().run();self.assertFalse(self.at.exception);self.assertTrue(self.s.result)

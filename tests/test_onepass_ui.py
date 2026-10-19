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
  self.s=WebSession(self.tmp.name);self.s.set_mode('academic');self.s.load((ROOT/'samples/phase31/errors.docx').read_bytes(),'合成.docx');self.s.set_table_enabled(False);self.s.enable_notes(False)
  # This legacy interaction task deliberately tests the retained format-only path.
  from core.page_policy import DEFAULT
  self.s.page_layout_draft={'enabled':False,'explicit':True,'policy':dict(DEFAULT)}
  self.at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);self.at.session_state.workflow=self.s;self.at.session_state['workspace-smart']=True;self.at.run()
 def test_ordinary_start_download_no_technical_stages(self):
  self.assertFalse(any(b.label in ('接受此范围并检查','一键智能修正','确认采用此副本') for b in self.at.button))
  self.assertFalse(any(b.key=='workspace-nav-2' for b in self.at.button))
  self.at.button(key='onepass-start').click().run();self.assertFalse(self.at.exception);self.assertEqual(len(self.s.history),1)
  self.assertTrue(any(b.label=='下载修正版' for b in self.at.get('download_button')))
  self.at.run();self.assertEqual(len(self.s.history),1);self.assertTrue(self.at.button(key='onepass-start').disabled)
  self.at.button(key='onepass-detail').click().run();self.at.button(key='workspace-nav-2').click().run();self.assertFalse(self.at.exception);self.assertTrue(any(b.label=='分析范围建议（不修改论文）' for b in self.at.button))
 def test_new_default_is_full_and_format_only_is_an_explicit_single_choice(self):
  from core.page_policy import DEFAULT
  from copy import deepcopy
  model=WebSession(self.tmp.name+'/default');model.set_mode('academic');model.load((ROOT/'samples/phase55/source.docx').read_bytes(),'公开目录.docx')
  app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);app.session_state.workflow=model;app.session_state['workspace-smart']=True;app.run()
  self.assertFalse(app.exception);self.assertFalse(any(x.label=='本次整理方案' for x in app.selectbox));self.assertTrue(model.page_layout_draft['enabled']);self.assertEqual(model.page_layout_draft['toc_appearance'],'reference');self.assertEqual(model.page_layout_draft['toc_policy']['depth'],3)
  before=deepcopy(model.page_layout_draft);app.run();self.assertEqual(before,model.page_layout_draft);self.assertIsNone(model.result)
  app.checkbox(key='assembly-'+model.task_dir.name+'-smart-v55-only').check().run();self.assertFalse(model.page_layout_draft['enabled']);self.assertFalse(model.field_updates_enabled)
  app.button(key='onepass-start').click().run();self.assertFalse(app.exception);self.assertTrue(model.result);self.assertNotIn('assembly',model.result)
  next(b for b in app.button if b.label=='重新开始').click().run();self.assertFalse(app.exception);self.assertIsNone(model.page_layout_draft);self.assertFalse(next(c for c in app.checkbox if c.label=='仅整理文字格式').value)
 def test_supplement_failure_plain_exception_template_continue(self):
  self.at.text_input(key='onepass-extra-'+self.s.task_dir.name).set_value('正文改为四号、2倍行距').run()
  with patch('ai.semantic_spec.parse_requirements',side_effect=TimeoutError()):
   self.at.button(key='onepass-start').click().run();self.assertFalse(self.at.exception);self.assertIsNone(self.s.result)
   choices=[x for x in self.at.selectbox if x.label=='您的选择'];self.assertEqual(len(choices),1);self.assertIsNone(choices[0].value)
   self.assertTrue(self.at.button(key='onepass-continue').disabled)
   choices[0].set_value('template').run();self.at.button(key='onepass-continue').click().run();self.assertFalse(self.at.exception);self.assertTrue(self.s.result)

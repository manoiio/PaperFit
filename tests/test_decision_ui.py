"""Frontend projection, authorization and escaping; no new formatting rules."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import json
from streamlit.testing.v1 import AppTest
from web.session import WebSession
from tests.ui_navigation import show
ROOT=Path(__file__).resolve().parents[1]

class DecisionUIAcceptance(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=WebSession(Path(self.tmp.name));self.s.load((ROOT/'samples/errors.docx').read_bytes(),'合成.docx',json.loads((ROOT/'samples/errors.body.json').read_text()));self.s.confirm_and_check()
  self.at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=25);self.at.session_state.workflow=self.s;self.at.run()
 def click(self,label):next(b for b in self.at.button if b.label==label).click().run();self.assertFalse(self.at.exception)
 def test_viewing_detail_does_not_select_and_explicit_button_only_selects_one(self):
  self.assertEqual(self.s.selected,[]);self.click('加入修正');self.assertEqual(len(self.s.selected),1);self.assertIsNone(self.s.result)
 def test_empty_filter_clear_retains_explicit_selection(self):
  self.click('加入修正');keys=self.s.selected.copy();next(t for t in self.at.text_input if t.label=='关键词筛选').set_value('从不匹配这份合成文档').run();self.click('清除筛选');self.assertEqual(keys,self.s.selected);self.assertEqual(next(t for t in self.at.text_input if t.label=='关键词筛选').value,'')
 def test_partial_result_shows_remaining_without_full_document_success(self):
  key=next(f['key'] for f in self.s.eligible() if f['rule_id']=='R05');self.s.set_selection([key]);self.s.rehearse();self.s.adopt_rehearsal(self.s.rehearsal['id'],acknowledged=True);self.at.run();show(self.at,5)
  self.assertTrue(any('仍有 10 个问题' in x.value for x in self.at.warning));self.assertFalse(any('所选修改的落盘复查' in x.value for x in self.at.success));self.assertEqual(self.s.current_round,0)
 def test_output_detail_does_not_select_input_key_by_collision(self):
  key=next(f['key'] for f in self.s.eligible() if f['rule_id']=='R05');self.s.set_selection([key]);self.s.rehearse();self.s.adopt_rehearsal(self.s.rehearsal['id'],acknowledged=True);self.at.run();show(self.at,3)
  self.assertFalse(any(b.label=='加入修正' for b in self.at.button));self.assertEqual(self.s.selected,[key])
 def test_project_entry_only_opens_existing_panel(self):
  report=self.s.report;self.click('保存 / 恢复');self.assertEqual(self.at.session_state['workspace-step'],1);self.assertTrue(self.at.session_state['project-panel']);self.assertIs(self.s.report,report);self.assertIsNone(self.s.project_export)
 def test_comparison_escapes_all_untrusted_values(self):
  a=AppTest.from_string('from web.decision_ui import comparison\ncomparison("<script>x()</script>","<img src=x onerror=x()>","<b>12</b>","<svg onload=x()>")').run()
  self.assertFalse(a.exception);text=' '.join(x.proto.body for x in a.get('html'))
  self.assertIn('&lt;script&gt;',text);self.assertNotIn('<script>x()',text);self.assertNotIn('<img src=x',text)

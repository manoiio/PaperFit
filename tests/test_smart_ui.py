"""Real native UI callback paths; existing detailed workspace remains accessible."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from streamlit.testing.v1 import AppTest
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1]
class SmartUIAcceptance(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=WebSession(self.tmp.name);self.at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);self.at.session_state.workflow=self.s;self.at.run();self.at.button(key='smart-entry').click().run();self.at.button(key='onepass-legacy').click().run()
 def click(self,label):next(b for b in self.at.button if b.label==label).click().run();self.assertFalse(self.at.exception)
 def test_summary_then_shortcut_without_individual_selection(self):
  self.click('使用错误样本');self.assertIsNone(self.s.confirmed);self.assertTrue(any(b.label=='接受此范围并检查' for b in self.at.button));self.assertIsNone(self.s.report)
  self.click('接受此范围并检查');self.assertFalse(self.s.selected);self.assertTrue(self.s.report);self.assertTrue(any('未套普通段落规则' in c.value and '未纳入模块' in c.value for c in self.at.caption))
  self.click('一键智能修正');self.assertEqual(self.s.generation_count,1);self.assertEqual(self.s.current_round,0);self.assertTrue(self.s.downloads())
  self.assertTrue(any(x.label=='下载修正版DOCX' for x in self.at.get('download_button')));self.assertFalse(any(x.value for x in self.at.checkbox if x.label=='启用本次动态处理'))
  self.at.run();self.assertEqual(self.s.generation_count,1)
  self.click('保存项目');self.assertTrue(any(x.label=='下载项目包（含论文）' for x in self.at.get('download_button')))
  self.click('详细调整范围与例外');self.assertFalse(self.at.session_state['workspace-smart']);self.assertTrue(any(b.label=='进入核对' for b in self.at.button))
 def test_changed_draft_requires_new_summary(self):
  self.click('使用错误样本');self.click('分析范围建议（不修改论文）');self.s.set_body([4]);self.at.run()
  self.assertIsNone(self.s.report);self.assertFalse(any(b.label=='接受此范围并检查' for b in self.at.button));self.assertTrue(any('摘要已失效' in x.value for x in self.at.warning))

"""Navigation is presentation, never confirmation or execution authorization."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from streamlit.testing.v1 import AppTest
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1]

def nav(app,n):
    app.button(key=f'workspace-nav-{n}').click().run()
    if app.exception:raise AssertionError(str(list(app.exception)))

class WorkflowAcceptance(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.s=WebSession(Path(self.tmp.name));self.app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=25);self.app.session_state.workflow=self.s;self.app.run()
 def tearDown(self):self.tmp.cleanup()
 def click(self,label):
  next(b for b in self.app.button if b.label==label).click().run();self.assertFalse(self.app.exception)
 def load(self):self.click('使用错误样本');nav(self.app,2)
 def check(self):
  self.load();next(c for c in self.app.checkbox if c.label.startswith('我已核对以上所有')).check().run();self.click('确认这些范围并开始检查')
 def test_empty_first_screen_and_lazy_rendering(self):
  self.assertTrue(any(x.label.startswith('上传自己的') for x in self.app.get('file_uploader')))
  self.assertFalse(any(x.label=='问题类别' for x in self.app.selectbox));self.assertFalse(any(x.label.startswith('核对并编辑待发送') for x in self.app.text_area))
  self.assertTrue(self.app.button(key='workspace-nav-3').disabled)
 def test_navigation_preserves_scope_draft_and_never_checks(self):
  self.load();before=self.s.body.copy();nav(self.app,1);nav(self.app,2);self.assertEqual(before,self.s.body);self.assertIsNone(self.s.confirmed);self.assertIsNone(self.s.report)
 def test_unmount_never_restores_acknowledgement(self):
  self.load();next(c for c in self.app.checkbox if c.label.startswith('我已核对以上所有')).check().run();nav(self.app,1);nav(self.app,2)
  self.assertFalse(next(c for c in self.app.checkbox if c.label.startswith('我已核对以上所有')).value)
 def test_problem_filter_selection_survive_navigation_but_not_scope_change(self):
  self.check();m=self.s
  next(x for x in self.app.text_input if x.label=='关键词筛选').set_value('字号').run();self.click('选择本页可修正项');selected=m.selected.copy();self.assertTrue(selected)
  nav(self.app,4);nav(self.app,3);self.assertEqual(m.selected,selected);self.assertEqual(next(x for x in self.app.text_input if x.label=='关键词筛选').value,'字号')
  nav(self.app,2);self.app.button(key='enter-scope-paragraph').click().run();next(c for c in self.app.checkbox if c.label.startswith('段 4 ·')).uncheck().run();self.assertIsNone(m.report);self.assertFalse(m.selected);self.assertTrue(self.app.button(key='workspace-nav-3').disabled)
 def test_rehearsal_adoption_navigates_only_after_real_success(self):
  self.check();self.click('选择本页可修正项');nav(self.app,4)
  self.click('预演所选修正')
  self.assertEqual(self.s.generation_count,0);self.assertIsNone(self.s.result)
  next(c for c in self.app.checkbox if c.label.startswith('我已核对全部所选修改')).check().run();self.click('确认采用此副本')
  self.assertEqual(self.s.generation_count,1);self.assertEqual(self.app.session_state['workspace-step'],5);self.assertEqual(self.s.current_round,0)
  self.assertTrue(any(x.label=='下载修正版DOCX' for x in self.app.get('download_button')))
  self.app.run();self.assertEqual(self.s.generation_count,1)
 def test_unsubmitted_rule_form_value_preserved_without_applying(self):
  self.s.set_mode('academic');self.app.run();self.click('使用错误样本');nav(self.app,1)
  self.app.radio(key='workspace-rule-entry').set_value('导入规则包 / 编辑规则').run();self.click('从当前配置建立编辑草稿（不调用AI）')
  next(x for x in self.app.checkbox if x.label=='编辑未提及或保留字段').check().run()
  next(x for x in self.app.selectbox if x.label=='选择格式对象').set_value('正文').run()
  next(x for x in self.app.selectbox if x.label=='编辑字段').set_value('font_size').run()
  value=next(x for x in self.app.number_input if x.label=='普通文字字号（磅 / pt）')
  value.set_value(14.).run();rules=self.s.rules_hash
  nav(self.app,2);nav(self.app,1)
  self.assertEqual(next(x for x in self.app.number_input if x.label=='普通文字字号（磅 / pt）').value,14.)
  self.assertEqual(self.s.rules_hash,rules)

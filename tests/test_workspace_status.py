"""Presentation history cannot create confirmation, adoption or file identity."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from web.session import WebSession
from web.workspace_status import check_status, latest_output, view_label
ROOT=Path(__file__).resolve().parents[1]

class WorkspaceStatusAcceptance(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.s=WebSession(Path(self.tmp.name));self.app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30)
  self.app.session_state.workflow=self.s;self.app.run()
 def click(self,label):
  next(b for b in self.app.button if b.label==label).click().run();self.assertFalse(self.app.exception)
 def html(self):return '\n'.join(x.proto.body for x in self.app.get('html'))
 def check(self):
  self.click('使用错误样本');self.s.confirm();self.s.check();self.app.run()
 def test_never_checked_observed_invalidation_and_new_task_are_distinct(self):
  self.click('使用错误样本');self.assertIn('范围待核对 · 尚未检查',self.html());self.assertNotIn('旧检查',self.html())
  self.s.set_body(self.s.body[:-1]);self.app.run();self.assertNotIn('原检查当前不可用',self.html())
  self.s.confirm();self.s.check();self.app.run();self.assertIn('已有有效检查',self.html())
  next(b for b in self.app.button if b.key=='workspace-nav-1').click().run();self.assertIn('已有有效检查',self.html())
  self.s.set_body(self.s.body[:-1]);self.app.run();self.assertIn('原检查当前不可用',self.html());self.assertTrue(self.app.button(key='workspace-nav-3').disabled)
  self.s.project_notice='已恢复草稿'
  self.click('使用正确对照');self.assertNotIn('原检查当前不可用',self.html());self.assertIsNone(self.s.report)
  self.app.button(key='workspace-nav-1').click().run()
  self.assertTrue(any(i.value.startswith('此前项目恢复记录（不代表当前文件来源或范围确认）') for i in self.app.info))
 def test_unadopted_adopted_continued_and_history_view_are_distinct(self):
  self.check();self.s.set_selection([next(f['key'] for f in self.s.eligible() if f['rule_id']=='R05')]);self.s.rehearse();self.app.run()
  self.assertIn('尚未采用',self.html());self.assertEqual(self.s.generation_count,0);self.assertIsNone(latest_output(self.s))
  self.assertTrue(self.s.adopt_rehearsal(self.s.rehearsal['id'],acknowledged=True));self.app.run();self.assertIn('与当前输入不同',self.html());self.assertEqual(self.s.current_round,0)
  raw=self.s.downloads()['fixed.docx']
  # Identical bytes alone do not authorize or identify a round switch.
  with patch.object(self.s,'inventory',{'input_sha256':self.s.result['output_body_manifest']['input_sha256']}):
   self.assertFalse(latest_output(self.s)['current'])
  self.assertTrue(self.s.next_round());self.app.run();self.assertIn('已是当前输入',self.html());self.assertNotIn('尚未切换',self.html());self.assertEqual(self.s.input_path.read_bytes(),raw)
  ui={'history-view-'+str(self.s.revision):True,'history-object-'+self.s.task_dir.name:self.s.history[0]['stem']}
  self.assertEqual(view_label(self.s,5,ui),'历史第1轮记录（不切换输入）');self.assertEqual(self.s.current_round,1)
  self.s.history[-1]['result']['output']=str(Path(self.tmp.name)/'missing.docx');self.assertFalse(latest_output(self.s)['available'])
 def test_view_targets_are_not_input_or_completion_and_untrusted_labels_are_escaped(self):
  self.check();s=self.s;seed=s.task_dir.name
  ui={'reader-open-'+seed:True,'reader-request-'+seed:{'target':'round-2','compare':True}}
  self.assertEqual(view_label(s,5,ui),'原稿 / 第2轮副本');self.assertEqual(s.current_round,0)
  s.display_name='<img src=x onerror=alert(1)>.docx';self.app.run();html=self.html();self.assertIn('&lt;img',html);self.assertNotIn('<img src=x',html)
  self.assertIn('已确认',self.app.button(key='workspace-nav-2').label)
 def test_ui_observation_is_session_local_and_empty_selection_does_not_authorize(self):
  self.check();self.s.invalidate();self.app.run();self.assertIn('原检查当前不可用',self.html())
  other=WebSession(Path(self.tmp.name)/'other');other.load((ROOT/'samples/errors.docx').read_bytes(),'另一任务.docx',json.loads((ROOT/'samples/errors.body.json').read_text()))
  at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);at.session_state.workflow=other;at.run();self.assertFalse(at.exception)
  self.assertEqual(check_status(other)[0],'范围待核对 · 尚未检查');self.assertFalse(at.session_state['workspace-observed-check']);self.assertIsNone(other.confirmed)
  other.confirm();other.check();at.run();at.button(key='workspace-nav-4').click().run();self.assertFalse(at.exception)
  self.assertIn('尚未选择修正','\n'.join(x.proto.body for x in at.get('html')));self.assertIsNone(other.rehearsal);self.assertFalse(other.selected)

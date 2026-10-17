"""Real report projections and original selection methods; no new engine judgments."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from web.session import WebSession
from web.problem_browser_ui import full_groups,status_counts,plain_label
from web.selection_ui import selection_rows
from tests.ui_navigation import show
ROOT=Path(__file__).resolve().parents[1]

class ProblemBrowserAcceptance(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=WebSession(Path(self.tmp.name))
  self.s.load((ROOT/'samples/errors.docx').read_bytes(),'已有合成样本.docx',json.loads((ROOT/'samples/errors.body.json').read_text()));self.s.confirm_and_check();self.open()
 def open(self):
  self.at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=35);self.at.session_state.workflow=self.s;self.at.run();self.assertFalse(self.at.exception)
 def click(self,name):next(b for b in self.at.button if b.label==name).click().run();self.assertFalse(self.at.exception)
 def obj(self,name):next(r for r in self.at.radio if r.label=='本页对象（点击仅查看）').set_value(name).run();self.assertFalse(self.at.exception)
 def record(self,key):next(r for r in self.at.radio if r.label=='查看检查项（不勾选修正）').set_value('format:'+key).run();self.assertFalse(self.at.exception)
 def test_visible_objects_properties_and_explicit_individual_removal(self):
  self.obj('paragraph:4');self.assertFalse(self.s.selected)
  self.record('R06:paragraph=4');self.assertFalse(self.s.selected);self.click('加入修正');self.assertEqual(self.s.selected,['R06:paragraph=4'])
  self.obj('paragraph:5');self.assertEqual(len(self.s.selected),1);self.record('R03:paragraph=5:run=1');self.click('加入修正')
  rows=selection_rows(self.s);self.assertEqual({r['key'] for r in rows},{'R06:paragraph=4','R03:paragraph=5:run=1'});self.assertTrue(all(r['实际'] and r['要求'] for r in rows))
  next(r for r in self.at.radio if r.label=='查看已选属性').set_value('R06:paragraph=4').run();self.assertEqual(len(self.s.selected),2)
  self.click('移除此项选择');self.assertEqual(self.s.selected,['R03:paragraph=5:run=1'])
  show(self.at,4);show(self.at,3);self.assertEqual(next(r for r in self.at.radio if r.label=='本页对象（点击仅查看）').value,'paragraph:5');self.assertEqual(self.s.selected,['R03:paragraph=5:run=1'])
 def test_mixed_counts_and_empty_filter_do_not_misrepresent_or_select(self):
  records=self.s.current_bundle()['projection']['records'];group=full_groups(records)['paragraph:4']
  self.assertEqual({r['status'] for r in group},{'pass','problem','not_applicable'});counts=status_counts(group);self.assertIn('发现问题2',counts);self.assertIn('符合',counts)
  self.obj('paragraph:4');self.click('加入修正');before=self.s.selected.copy()
  next(t for t in self.at.text_input if t.label=='关键词筛选').set_value('不存在的筛选内容').run();self.assertEqual(before,self.s.selected)
  self.assertFalse(any('id="current-problem"' in x.proto.body for x in self.at.get('html')))
  self.click('清除筛选');self.assertEqual(before,self.s.selected)
  next(t for t in self.at.text_input if t.label.startswith('段落编号筛选')).set_value('错误范围').run();self.assertFalse(self.at.exception);self.assertEqual(before,self.s.selected)
  self.click('清除筛选');self.assertEqual(before,self.s.selected)
  self.assertIn('\\[',plain_label('[img](https://example.invalid/x)<script>'));self.assertIn('\\<',plain_label('<script>'))
 def test_long_view_is_bounded_and_ids_survive_pages_sort_and_filter(self):
  p=ROOT/'tests/fixtures/history/phase12/long-400.docx';s=WebSession(Path(self.tmp.name)/'long');s.set_mode('extended');s.load(p.read_bytes(),'既有长文.docx');s.set_types(json.loads(p.with_suffix('.types.json').read_text())['paragraph_types']);s.confirm_and_check();self.s=s;self.open()
  self.assertEqual(len(s.report['findings']),2015);self.obj('paragraph:2');self.record(next(f['key'] for f in s.eligible() if f['rule_id']=='R05' and f['locator'].get('paragraph')==2));self.click('加入修正');chosen=s.selected.copy()
  next(n for n in self.at.number_input if n.label=='对象页码').set_value(2).run();self.assertEqual(s.selected,chosen)
  selected_object=next(r for r in self.at.radio if r.label=='本页对象（点击仅查看）').value;self.assertIn(selected_object,s.center_selection_view['objects']);self.record(next(f['key'] for f in s.eligible() if f['rule_id']=='R05' and f['locator'].get('paragraph')==int(selected_object.split(':')[1])));self.click('加入修正');both=s.selected.copy();self.assertEqual(len(both),2)
  next(n for n in self.at.selectbox if n.label=='对象排序').set_value('编号降序').run();self.assertEqual(both,s.selected);self.assertEqual(next(n for n in self.at.number_input if n.label=='对象页码').value,1)
  next(t for t in self.at.text_input if t.label.startswith('段落编号筛选')).set_value('390-400').run();self.assertEqual(both,s.selected)
  current=next(r for r in self.at.radio if r.label=='本页对象（点击仅查看）').value;self.assertTrue(390<=int(current.split(':')[1])<=400)
  self.assertLessEqual(len(next(r for r in self.at.radio if r.label=='本页对象（点击仅查看）').options),20)
  self.assertLessEqual(len(next(r for r in self.at.radio if r.label=='查看检查项（不勾选修正）').options),4)
  self.assertLess(len(self.at.button),40);self.assertEqual(len(self.at.json),0)
  self.click('清除筛选');self.assertEqual(both,s.selected)
 def test_selected_list_paging_output_protection_and_view_only_callbacks(self):
  self.s.set_selection([f['key'] for f in self.s.eligible()]);self.at.run();all_keys=self.s.selected.copy()
  self.assertEqual(len(next(r for r in self.at.radio if r.label=='查看已选属性').options),8)
  next(n for n in self.at.number_input if n.label=='已选清单页码').set_value(2).run();self.assertEqual(self.s.selected,all_keys)
  radio=next(r for r in self.at.radio if r.label=='查看已选属性');self.assertEqual(len(radio.options),len(all_keys[8:]));self.assertEqual(radio.value,all_keys[8])
  for k in all_keys[8:]:
   next(r for r in self.at.radio if r.label=='查看已选属性').set_value(k).run();self.assertEqual(next(r for r in self.at.radio if r.label=='查看已选属性').value,k);self.assertEqual(self.s.selected,all_keys)
  self.s.generate();self.at.run();show(self.at,3)
  self.assertFalse(any(b.label=='加入修正' for b in self.at.button));self.assertTrue(all(b.disabled for b in self.at.button if b.label in ('选择本页可修正项','选择当前筛选的可修正项','选择全部可修正问题')))
  before=self.s.downloads()['fixed.docx']
  with patch.object(self.s,'set_selection',side_effect=AssertionError('view must not select')),patch.object(self.s,'generate',side_effect=AssertionError('view must not fix')),patch.object(self.s,'submit_preview',side_effect=AssertionError('view must not render')):
   objects=next(r for r in self.at.radio if r.label=='本页对象（点击仅查看）');self.obj(objects.value);show(self.at,4);show(self.at,3)
  self.assertEqual(self.s.downloads()['fixed.docx'],before);self.assertEqual(self.s.current_round,0)

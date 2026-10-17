"""Object buffers use the original strict draft path, without publishing partial edits."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from core import rule_bundle as rb
from core.package import DemoError
from scripts.reproduce_internal_reference_demo import session
from tests.ui_navigation import show
from web.object_rules_ui import save_object_changes,editor_signature
ROOT=Path(__file__).resolve().parents[1]

class ObjectRulesAcceptance(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=session(Path(self.tmp.name),checked=False)
  self.s.import_rule_bundle((ROOT/'samples/phase25/repaired-rule-bundle.json').read_bytes())
  self.app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);self.app.session_state.workflow=self.s;self.app.run();show(self.app,1,rules=True);self.select('选择格式对象','正文')
 def select(self,label,value):next(x for x in self.app.selectbox if x.label==label).set_value(value).run();self.assertFalse(self.app.exception)
 def number(self,label,value):next(x for x in self.app.number_input if x.label==label).set_value(value).run();self.assertFalse(self.app.exception)
 def click(self,label):next(x for x in self.app.button if x.label==label).click().run();self.assertFalse(self.app.exception)
 def pending(self):return next(b.label for b in self.app.button if b.label.startswith('保存本对象的'))
 def three(self):self.select('中文字体','楷体');self.number('普通文字字号（磅 / pt）',13.);self.select('倍数行距',2.)
 def test_three_values_save_once_only_and_match_original_field_path(self):
  before=deepcopy(self.s.workbench['draft']);active=self.s.current_rule_bundle();self.three();self.assertEqual(self.pending(),'保存本对象的3项改动到草稿');self.assertEqual(before,self.s.workbench['draft']);self.assertEqual(active['provenance'],self.s.current_rule_bundle()['provenance']);self.assertEqual(rb.flat('main',active['modules']['main']),rb.flat('main',self.s.current_rule_bundle()['modules']['main']))
  self.click(self.pending());saved=self.s.workbench['draft'];self.assertEqual(self.pending(),'保存本对象的0项改动到草稿');self.assertEqual(active['provenance'],self.s.current_rule_bundle()['provenance']);self.assertEqual(rb.flat('main',active['modules']['main']),rb.flat('main',self.s.current_rule_bundle()['modules']['main']))
  other=session(Path(self.tmp.name)/'reference',checked=False);other.import_rule_bundle((ROOT/'samples/phase25/repaired-rule-bundle.json').read_bytes())
  for n,v in {'font_cn':'楷体','font_size':13.,'line_spacing':2.}.items():other.workbench_edit('main',n,'manual',v)
  self.assertEqual(other.workbench['draft']['fields'],saved['fields'])
  for m,fields in saved['fields'].items():
   for n,f in fields.items():
    if m!='main' or n not in ('font_cn','font_size','line_spacing'):self.assertEqual(f,before['fields'][m][n])
  self.assertEqual(other.proposed_rule_bundle()['provenance'],self.s.proposed_rule_bundle()['provenance'])
 def test_invalid_spacing_rejects_entire_group_preserves_inputs_and_other_buffers(self):
  self.select('选择格式对象','一级标题');self.number('字号（磅 / pt）',20.)
  self.select('选择格式对象','正文');next(x for x in self.app.checkbox if x.label=='编辑未提及或保留字段').check().run()
  self.select('中文字体','楷体');self.number('段前间距数值',4.);self.select('间距单位','lines')
  old=deepcopy(self.s.workbench);self.click(self.pending());self.assertEqual(self.s.workbench,old);self.assertTrue(any('段前间距' in e.value and '未保存' in e.value for e in self.app.error));self.assertEqual(next(n.value for n in self.app.number_input if n.label=='段前间距数值'),4.)
  self.select('选择格式对象','一级标题');self.assertFalse(self.app.error);self.select('选择格式对象','正文');self.assertTrue(self.app.error)
  self.number('段前间距数值',.5);self.click(self.pending());self.assertEqual(self.s.workbench['draft']['fields']['main']['body__before']['value'],{'value':.5,'unit':'lines'})
  self.assertTrue(next(b for b in self.app.button if b.label=='核对并应用整份规则').disabled)
  self.select('选择格式对象','一级标题');self.assertEqual(next(n.value for n in self.app.number_input if n.label=='字号（磅 / pt）'),20.);self.assertEqual(self.pending(),'保存本对象的1项改动到草稿')
 def test_current_object_discard_and_advanced_share_one_buffer(self):
  self.number('普通文字字号（磅 / pt）',13.);self.select('选择格式对象','一级标题');self.number('字号（磅 / pt）',20.);self.click('放弃本对象未保存改动');self.assertEqual(self.pending(),'保存本对象的0项改动到草稿');self.assertEqual(next(n.value for n in self.app.number_input if n.label=='字号（磅 / pt）'),18.)
  self.select('选择格式对象','正文');self.assertEqual(next(n.value for n in self.app.number_input if n.label=='普通文字字号（磅 / pt）'),13.)
  next(x for x in self.app.radio if x.label=='编辑方式').set_value('高级：单字段编辑').run();self.select('编辑字段','font_size');self.assertEqual(next(n.value for n in self.app.number_input if '字号' in n.label),13.);self.click('保存本字段到草稿')
  next(x for x in self.app.radio if x.label=='编辑方式').set_value('集中编辑本对象').run();self.assertEqual(self.pending(),'保存本对象的0项改动到草稿');self.assertEqual(self.s.workbench['draft']['fields']['main']['font_size']['value'],13.)
 def test_decisions_missing_fields_import_namespace_and_restore(self):
  next(x for x in self.app.checkbox if x.label=='编辑未提及或保留字段').check().run()
  self.assertIsNone(next(n.value for n in self.app.number_input if n.label=='段前间距数值'))
  self.select('普通文字字号采用方式','disabled');self.assertIsNone(next(n.value for n in self.app.number_input if n.label=='普通文字字号（磅 / pt）'));self.click(self.pending());self.assertIsNone(rb.flat('main',self.s.proposed_rule_bundle()['modules']['main'])['font_size'])
  next(x for x in self.app.checkbox if x.label.startswith('已核对整体差异')).check().run();self.number('段前间距数值',.5)
  self.assertFalse(next(x.value for x in self.app.checkbox if x.label.startswith('已核对整体差异')))
  raw=self.s.prepare_project();n=session(Path(self.tmp.name)/'restore-base',checked=False);n.stage_project(raw);n=n.restore_project(acknowledged=True)
  self.assertEqual(n.workbench['draft']['fields']['main']['font_size']['mode'],'disabled');self.assertNotEqual(n.workbench['draft']['fields']['main']['body__before']['mode'],'manual');self.assertIsNone(n.workbench['active'])
  self.s.import_rule_bundle((ROOT/'samples/phase25/repaired-rule-bundle.json').read_bytes());self.app.run();self.assertFalse(self.app.exception);self.assertEqual(self.pending(),'保存本对象的0项改动到草稿')
  self.select('选择格式对象','正文')
  next(x for x in self.app.checkbox if x.label=='编辑未提及或保留字段').check().run()
  self.assertIsNone(next(n.value for n in self.app.number_input if n.label=='段前间距数值'))
 def test_stage_failure_and_stale_signature_never_publish(self):
  old=deepcopy(self.s.workbench);h=editor_signature(self.s);changes={'font_cn':{'mode':'manual','value':'楷体'},'font_size':{'mode':'manual','value':999}}
  with self.assertRaisesRegex(DemoError,'字号'):save_object_changes(self.s,'main','正文',changes,h)
  self.assertEqual(old,self.s.workbench)
  with self.assertRaises(DemoError):save_object_changes(self.s,'main','正文',{'heading1_font_size':{'mode':'manual','value':18}},h)
  self.assertEqual(old,self.s.workbench)
  with self.assertRaises(DemoError):save_object_changes(self.s,'main','正文',{},'stale')
  self.assertEqual(old,self.s.workbench)
  self.assertTrue(self.s.load((ROOT/'samples/phase32/errors.docx').read_bytes(),'更换文件.docx'));after_load=deepcopy(self.s.workbench)
  with self.assertRaises(DemoError):save_object_changes(self.s,'main','正文',{'font_size':{'mode':'manual','value':14.}},h)
  self.assertEqual(after_load,self.s.workbench)

 def test_legal_candidate_and_keep_use_original_source_decisions(self):
  from tests.test_workbench import draft
  draft(self.s);self.s.workbench_edit('main','font_cn','manual','楷体');self.app.run();self.select('选择格式对象','正文')
  candidate=deepcopy(self.s.workbench['draft']['fields']['main']['font_cn']['candidate'])
  self.select('中文字体采用方式','ai');self.assertEqual(next(n.value for n in self.app.selectbox if n.label=='中文字体'),'宋体');self.assertEqual(self.pending(),'保存本对象的1项改动到草稿');self.click(self.pending())
  p=self.s.proposed_rule_bundle();self.assertEqual(p['provenance']['main']['font_cn'],{'kind':'ai_extracted','quote':candidate['quote'],'location':candidate['location']})
  self.select('中文字体采用方式','keep');self.assertEqual(next(n.value for n in self.app.selectbox if n.label=='中文字体'),'宋体');self.click(self.pending());self.assertEqual(self.s.workbench['draft']['fields']['main']['font_cn']['mode'],'keep')
  self.assertNotEqual(self.s.proposed_rule_bundle()['provenance']['main']['font_cn']['kind'],'ai_extracted')

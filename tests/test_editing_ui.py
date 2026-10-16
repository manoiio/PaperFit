"""Typed presentation, unsaved buffers, explicit draft operations and protections."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from streamlit.testing.v1 import AppTest
from core import rule_bundle as rb
from web.rule_fields_ui import spec
from scripts.reproduce_internal_reference_demo import session
from tests.ui_navigation import show
ROOT=Path(__file__).resolve().parents[1]

class EditingUIAcceptance(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=session(Path(self.tmp.name),checked=False);self.at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);self.at.session_state.workflow=self.s;self.at.run()
 def select(self,label,value):next(x for x in self.at.selectbox if x.label==label).set_value(value).run();self.assertFalse(self.at.exception)
 def click(self,label):next(x for x in self.at.button if x.label==label).click().run();self.assertFalse(self.at.exception)
 def rule(self):
  self.s.import_rule_bundle((ROOT/'samples/phase25/repaired-rule-bundle.json').read_bytes());show(self.at,1,rules=True);self.select('选择格式对象','正文');self.select('编辑字段','font_size')
 def test_control_options_are_existing_validator_projection(self):
  for m in rb.MODULES:
   for n in rb.FIELDS[m]:
    c=spec(m,n);self.assertNotEqual(c['kind'],'unsupported',(m,n))
    for v in c.get('options',[]):rb.validate_value(m,n,v)
    if c['kind']=='number':rb.validate_value(m,n,c['min']);rb.validate_value(m,n,c['max'])
 def test_unsaved_number_survives_fields_and_steps_and_blocks_apply(self):
  self.rule();h=self.s.rules_hash;next(x for x in self.at.number_input if '字号' in x.label).set_value(13.).run();self.select('编辑字段','font_cn');self.select('编辑字段','font_size');self.assertEqual(next(x for x in self.at.number_input if '字号' in x.label).value,13.)
  show(self.at,2);show(self.at,1);self.assertEqual(next(x for x in self.at.number_input if '字号' in x.label).value,13.);self.assertEqual(h,self.s.rules_hash)
  self.assertTrue(next(x for x in self.at.button if x.label=='核对并应用整份规则').disabled)
  self.click('保存本字段到草稿');self.assertEqual(self.s.workbench['draft']['fields']['main']['font_size']['value'],13.);self.assertEqual(h,self.s.rules_hash)
  ack=next(c for c in self.at.checkbox if c.label.startswith('已核对整体差异'));ack.check().run();self.assertFalse(next(x for x in self.at.button if x.label=='核对并应用整份规则').disabled)
  next(x for x in self.at.number_input if '字号' in x.label).set_value(14.).run();self.click('保存本字段到草稿');self.assertFalse(next(c for c in self.at.checkbox if c.label.startswith('已核对整体差异')).value)
  next(c for c in self.at.checkbox if c.label.startswith('已核对整体差异')).check().run()
  self.assertTrue(self.s.load((ROOT/'samples/phase32/errors.docx').read_bytes(),'重新载入的合成.docx'));self.at.run();show(self.at,1)
  self.assertFalse(next(c for c in self.at.checkbox if c.label.startswith('已核对整体差异')).value)
 def test_spacing_units_and_missing_enum_never_gain_defaults(self):
  a=AppTest.from_string("from web.rule_fields_ui import value_control\nvalue_control('main','body__before',None,'spacing',lambda:None)\nvalue_control('main','font_cn',None,'font',lambda:None)").run();self.assertFalse(a.exception)
  self.assertIsNone(a.number_input[0].value);self.assertIsNone(a.selectbox[0].value);self.assertIsNone(a.selectbox[1].value)
  a=AppTest.from_string("from web.rule_fields_ui import value_control\nvalue_control('main','font_cn','不支持字体','font',lambda:None)").run();self.assertTrue(a.error);self.assertEqual(len(a.selectbox),0)
 def test_classification_context_return_does_not_confirm_and_protects_material(self):
  show(self.at,2,'paragraph');self.assertTrue(any('完整文本' in m.value for m in self.at.markdown))
  editable=next(d.value for d in self.at.dataframe if '核对类型' in d.value);self.assertNotIn(12,editable['编号'].tolist())
  picker=next(x for x in self.at.selectbox if x.label=='查看段落');picker.set_value(3).run();self.select('本段草稿分类','other');self.click('保存本段分类草稿并返回范围总览');self.assertEqual(self.s.paragraph_types['3'],'other');self.assertIsNone(self.s.confirmed);self.assertIsNone(self.s.report);self.assertFalse(self.at.session_state['workspace-scope-editor'])
  show(self.at,2,'paragraph');next(x for x in self.at.selectbox if x.label=='查看段落').set_value(12).run();self.assertTrue(next(b for b in self.at.button if b.label=='保存本段分类草稿').disabled);self.assertIn('12',self.s.material_exclusions)
  self.assertTrue(any('合成代码' in w.value for w in self.at.warning))

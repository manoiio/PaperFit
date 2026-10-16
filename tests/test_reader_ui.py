"""Read-only reader navigation and accurate page boundaries; mock page bytes, not visual QA."""
import base64,json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from core.package import sha256
from tests.preview_fixture import configuration
from web.session import WebSession
from web.preview_ui import page_absence
from tests.ui_navigation import show
ROOT=Path(__file__).resolve().parents[1]
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a/e8AAAAASUVORK5CYII=')
class ReaderUIAcceptance(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=WebSession(Path(self.tmp.name));s=self.s
  self.assertTrue(s.load((ROOT/'samples/errors.docx').read_bytes(),'已有合成样本.docx',json.loads((ROOT/'samples/errors.body.json').read_text())));s.confirm();s.check()
  s.set_selection([next(f['key'] for f in s.eligible() if f['rule_id']=='R05')]);self.assertTrue(s.generate(),s.error)
  def renderer(path,root,context):
   root.mkdir(parents=True,exist_ok=True);count=12 if context['round']==0 else 2;pages=[]
   for n in range(min(count,10)):
    p=root/('mock-'+str(context['round'])+'-'+str(n)+'.png');p.write_bytes(PNG);pages.append(str(p))
   return {'document_sha256':sha256(Path(path).read_bytes()),'render_config_sha256':configuration()[1],'pages':pages,'context':context,'page_count':count,'preview_range':[1,len(pages)],'generated_at':'mock-only','renderer':'mock-only','renderer_version':'mock','fonts':[],'font_notes':[],'artifact_sha256':{p:sha256(Path(p).read_bytes()) for p in pages}}
  with patch('web.preview_session.configuration',side_effect=configuration):
   self.assertTrue(s.generate_preview('original',renderer));self.assertTrue(s.generate_preview('round-1',renderer))
  for target in ('web.preview_session.configuration','web.async_preview.configuration'):
   p=patch(target,side_effect=AssertionError('View navigation must not probe environment'));p.start();self.addCleanup(p.stop)
  p=patch.object(s,'submit_preview',side_effect=AssertionError('No implicit render'));p.start();self.addCleanup(p.stop)
  self.at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);self.at.session_state.workflow=s;self.at.run();self.assertFalse(self.at.exception)
 def click(self,label):next(b for b in self.at.button if b.label==label).click().run();self.assertFalse(self.at.exception)
 def test_result_entry_and_unmount_keep_view_without_switching_input(self):
  before=self.s.input_path.read_bytes();self.click('查看本轮页面');self.assertEqual(self.at.radio(key='reader-mode-'+self.s.task_dir.name).value,'单份查看')
  self.assertEqual(next(x for x in self.at.selectbox if x.label.startswith('正在查看')).value,'round-1');self.click('下一页')
  show(self.at,3);show(self.at,5);self.assertEqual(next(x for x in self.at.number_input if x.label=='页码').value,2)
  self.assertEqual(self.s.current_round,0);self.assertEqual(before,self.s.input_path.read_bytes());self.assertEqual(self.s.generation_count,1)
  self.click('返回结果与下载');self.assertTrue(any(x.label=='下载修正版DOCX' for x in self.at.get('download_button')))
 def test_unequal_counts_missing_page_and_ten_page_limit_are_distinct(self):
  self.click('与原稿对比');self.assertTrue(any('页数不同' in x.value for x in self.at.caption))
  self.s.preview_view_request='original';self.at.run();self.assertFalse(self.at.exception)
  self.assertEqual(next(x for x in self.at.selectbox if x.label=='右侧文件').value,'round-1')
  next(x for x in self.at.number_input if x.label=='页码').set_value(12).run();self.assertFalse(self.at.exception)
  self.assertTrue(any('超出本次预览范围' in x.value for x in self.at.info));self.assertTrue(any('实际2页，没有第12页' in x.value for x in self.at.info))
  self.assertTrue(next(b for b in self.at.button if b.label=='下一页').disabled)
  self.assertIsNone(page_absence(self.s.get_preview('round-1',verify_environment=False),2))
 def test_view_changes_are_read_only_and_new_document_does_not_inherit_view(self):
  raw=self.s.downloads()['fixed.docx'];self.click('与原稿对比');next(r for r in self.at.radio if r.label=='查看方式').set_value('单份查看').run()
  next(x for x in self.at.selectbox if x.label.startswith('正在查看')).set_value('original').run();self.assertFalse(self.at.exception)
  self.assertEqual(raw,self.s.downloads()['fixed.docx']);show(self.at,1);self.click('使用正确对照')
  self.assertFalse(self.s.preview_cache);self.assertFalse(self.s.preview_jobs);self.assertIsNone(self.s.result);self.assertTrue(self.at.button(key='workspace-nav-5').disabled)
 def test_auxiliary_and_details_are_explicit_secondary_views(self):
  self.click('查看本轮页面');self.assertFalse(any(x.label=='本次辅助输入' for x in self.at.selectbox));self.assertFalse(any(x.label=='刷新预览环境' for x in self.at.button))
  next(r for r in self.at.radio if r.label=='预览工作区').set_value('排版辅助').run();self.assertTrue(any('基础模式未启用' in x.value for x in self.at.info))
  next(r for r in self.at.radio if r.label=='预览工作区').set_value('预览详情与人工观察记录').run();self.assertFalse(self.at.exception);self.assertTrue(any(x.label=='刷新预览环境' for x in self.at.button));self.assertFalse(self.s.visual_reviews)
  self.s.display_name='<img src="invalid" onerror="alert(1)">.docx';self.at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);self.at.session_state.workflow=self.s;self.at.run();show(self.at,5);self.click('查看本轮页面')
  next(r for r in self.at.radio if r.label=='预览工作区').set_value('预览详情与人工观察记录').run();self.assertFalse(self.at.exception)
  titles=[x.proto.body for x in self.at.get('html') if '<strong>' in x.proto.body];self.assertTrue(titles);self.assertTrue(all('&lt;img' in x and '<img' not in x for x in titles))
 def test_auxiliary_confirmation_does_not_survive_a_generated_round(self):
  s=WebSession(Path(self.tmp.name)/'aux');s.set_mode('extended');s.load((ROOT/'samples/extended-errors.docx').read_bytes(),'既有扩展合成样本.docx');s.set_types(json.loads((ROOT/'samples/extended-errors.types.json').read_text())['paragraph_types']);s.confirm();self.assertTrue(s.check())
  self.s=s;self.at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);self.at.session_state.workflow=s;self.at.run();show(self.at,5);self.click('查看论文页面')
  next(r for r in self.at.radio if r.label=='预览工作区').set_value('排版辅助').run();first=next(c for c in self.at.checkbox if c.label.startswith('确认 L01'))
  self.assertFalse(first.value);first.check().run();self.assertEqual(s.generation_count,0);self.click('确认关联并生成排版副本')
  self.assertEqual(s.generation_count,1);self.assertEqual(s.current_round,0);self.assertFalse(self.at.exception);self.assertFalse(any(c.value for c in self.at.checkbox if c.label.startswith('确认 L')))

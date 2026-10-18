from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch,Mock
import local_tools as local
from web.result_overview import attention

class LocalDelivery(TestCase):
 def test_ownership_requires_exact_root_and_app(self):
  def output(command,**kw):return Mock(stdout=('python -m streamlit run app.py --server.port 8501' if command[0]=='/bin/ps' else 'p42\nfcwd\nn'+str(local.ROOT)+'\n'))
  with patch('local_tools.subprocess.run',side_effect=output):self.assertTrue(local.owned(42))
  with patch('local_tools.subprocess.run',return_value=Mock(stdout='python other.py')):self.assertFalse(local.owned(42))
 def test_foreign_port_is_never_stopped_or_started(self):
  with TemporaryDirectory() as d,patch.object(local,'STATE',Path(d)),patch.object(local,'dependencies',return_value={'ok':True}),patch.object(local,'listeners',return_value=[42]),patch.object(local,'owned',return_value=False),patch('local_tools.subprocess.Popen') as start:
   with self.assertRaisesRegex(RuntimeError,'其他服务'):local.launch(False)
   start.assert_not_called()
 def test_existing_service_is_reused_without_spawning(self):
  with TemporaryDirectory() as d,patch.object(local,'STATE',Path(d)),patch.object(local,'dependencies',return_value={'ok':True}),patch.object(local,'listeners',return_value=[42]),patch.object(local,'owned',return_value=True),patch.object(local,'health',return_value=True),patch('local_tools.subprocess.Popen') as start:
   self.assertEqual(local.launch(False),'reused');start.assert_not_called();self.assertNotIn('api', (Path(d)/'startup.jsonl').read_text().lower())
 def test_self_check_never_controls_word_or_paid_http(self):
  with patch('core.word_native.export_pdf',side_effect=AssertionError('Word')),patch('core.word_native.calculate',side_effect=AssertionError('Word')),patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('HTTP')):
   rows=local.environment();self.assertEqual(len(rows),5);self.assertTrue(any('未调用' in r['state'] or '未配置' in r['state'] for r in rows));self.assertFalse(any(r['state']=='调用成功' for r in rows))
 def test_attention_counts_preserve_raw_records_and_severity(self):
  report={'findings':[{'key':'a','status':'problem','fixable':True,'detail':'错误字号'},{'key':'b','status':'review','fixable':False,'detail':'复杂域保护'},{'key':'c','status':'pass'}],'coverage_notes':['未纳入范围','字体缺失']}
  import copy
  original=copy.deepcopy(report);groups=attention(report)
  self.assertEqual(sum(map(len,groups.values())),4);self.assertEqual(report,original)
  self.assertEqual(groups['仍可处理的格式问题'][0]['key'],'a');self.assertEqual(groups['不支持或受保护的复杂结构'][0]['status'],'review')
 def test_launcher_uses_own_directory_and_no_install(self):
  text=(local.ROOT/'启动论文有格.command').read_text();self.assertIn('dirname -- "$0"',text);self.assertIn('.venv/bin/python scripts/local_start.py',text);self.assertNotIn('pip install',text);self.assertNotIn('kill',text)
 def test_new_smart_task_after_restart_uses_recommended_mode(self):
  from streamlit.testing.v1 import AppTest
  from web.session import WebSession
  with TemporaryDirectory() as d:
   model=WebSession(d);model.set_mode('academic')
   app=AppTest.from_file(str(local.ROOT/'app.py'));app.session_state.workflow=model;app.session_state['workspace-smart']=True;app.run()
   reset=next(b for b in app.button if b.label=='重新开始');reset.click().run()
   next(b for b in app.button if b.label=='使用错误样本').click().run()
   self.assertFalse(app.exception);self.assertEqual(model.mode,'academic')
 def test_unstarted_source_choice_does_not_claim_old_result_invalid(self):
  from streamlit.testing.v1 import AppTest
  from web.session import WebSession
  with TemporaryDirectory() as d:
   model=WebSession(d);model.set_mode('academic');model.load((local.ROOT/'samples/errors.docx').read_bytes(),'公开.docx')
   app=AppTest.from_file(str(local.ROOT/'app.py'));app.session_state.workflow=model;app.session_state['workspace-smart']=True;app.run()
   next(r for r in app.radio if r.label=='排版要求来源').set_value('saved').run()
   self.assertFalse(app.exception);self.assertFalse(any('旧处理结果' in i.value for i in app.info))
 def test_starter_zip_is_allowlisted_and_manifest_matches(self):
  from scripts.build_starter_pack import build,FILES
  import zipfile,json,hashlib
  from io import BytesIO
  with TemporaryDirectory() as d:
   root=Path(d)
   for folder,names in FILES.items():
    (root/folder).mkdir()
    for name in names:(root/folder/name).write_bytes(('public-'+name).encode())
   (root/'private.env').write_text('not public');(root/'basic'/'extra.docx').write_bytes(b'private')
   data=build(root);self.assertEqual(data,build(root))
   with zipfile.ZipFile(BytesIO(data)) as z:
    self.assertNotIn('private.env',z.namelist());self.assertNotIn('basic/extra.docx',z.namelist())
    for row in json.loads(z.read('文件与哈希清单.json')):self.assertEqual(hashlib.sha256(z.read(row['file'])).hexdigest(),row['sha256'])
 def test_starter_zip_rejects_symlink(self):
  from scripts.build_starter_pack import build
  with TemporaryDirectory() as d:
   root=Path(d);(root/'basic').mkdir();(root/'secret').write_text('private');(root/'basic'/'使用说明.md').symlink_to(root/'secret')
   with self.assertRaises(ValueError):build(root)
 def test_smart_result_does_not_build_package_while_merely_viewing(self):
  from streamlit.testing.v1 import AppTest
  from web.session import WebSession
  with TemporaryDirectory() as d:
   model=WebSession(d);model.set_mode('academic');model.load((local.ROOT/'samples/errors.docx').read_bytes(),'公开.docx')
   app=AppTest.from_file(str(local.ROOT/'app.py'));app.session_state.workflow=model;app.session_state['workspace-smart']=True;app.run()
   with patch.object(model,'result_package',side_effect=AssertionError('Only explicit preparation')) as package:
    app.button(key='onepass-start').click().run();self.assertFalse(app.exception);self.assertIsNotNone(model.result);app.run();package.assert_not_called()
 def test_physical_space_path_is_owned_but_prefix_lookalike_is_not(self):
  root=Path('/tmp/公开 项目').resolve()
  def result(app):
   def run(command,**kw):return Mock(stdout=('python -m streamlit run '+app+' --server.port 8501' if command[0]=='/bin/ps' else 'p42\nfcwd\nn'+str(root)+'\n'))
   return run
  with patch('local_tools.subprocess.run',side_effect=result(str(root/'app.py'))):self.assertTrue(local.owned(42,root))
  with patch('local_tools.subprocess.run',side_effect=result(str(root/'app.py.evil'))):self.assertFalse(local.owned(42,root))
  with patch('local_tools.subprocess.run',side_effect=result('other.py -m streamlit run '+str(root/'app.py'))):self.assertFalse(local.owned(42,root))
 def test_environment_reads_the_same_timeout_guard_as_native_word(self):
  with TemporaryDirectory() as d,patch('local_tools.tempfile.gettempdir',return_value=d):
   (Path(d)/('paperfit-word-'+str(__import__('os').getuid())+'.uncertain')).write_text('public-probe')
   row=next(r for r in local.environment() if r['item']=='Word自动化')
   self.assertEqual(row['state'],'超时隔离中')

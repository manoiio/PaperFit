from tests.ui_navigation import show, click as ui_click
"""长文纯展示与可控后台替身；替身不作为真实渲染证据。"""
import unittest,json,time,threading
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from copy import deepcopy
from core.package import sha256,DemoError
from core.preview_jobs import PreviewJobs
from web.session import WebSession
from web.report_pages import object_page,merge_page_selection,selection_counts
ROOT=Path(__file__).resolve().parents[1]
class LongPreviewAcceptance(unittest.TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name);self.schedulers=[];self.gates=[]
 def tearDown(self):
  for gate in self.gates:gate.set()
  for sch in self.schedulers:
   thread=sch.thread
   if thread:thread.join(5)
  self.tmp.cleanup()
 def model(self,long=False):
  s=WebSession(self.root/'sessions');s.set_mode('extended' if long else 'basic');p=ROOT/('tests/fixtures/history/phase12/long-400.docx' if long else 'samples/errors.docx');s.load(p.read_bytes(),'synthetic.docx')
  if long:s.set_types(json.loads(p.with_suffix('.types.json').read_text())['paragraph_types'])
  else:s.set_body([4,5,6,11,14,15])
  s.confirm();s.check();return s
 def scheduler(self,n=2):s=PreviewJobs(n);self.schedulers.append(s);return s
 def wait(self,fn):
  deadline=time.monotonic()+5
  while time.monotonic()<deadline:
   value=fn()
   if value:return value
   time.sleep(.005)
  self.fail('controlled worker did not reach expected state')
 def renderer(self,gate=None,cfg='cfg',bad=False,fail=False):
  calls=[]
  def render(path,root,context):
   calls.append((threading.current_thread().name,sha256(Path(path).read_bytes())))
   if gate:gate.wait(4)
   if fail:raise DemoError('预览超时（受控替身）')
   root.mkdir(parents=True,exist_ok=True);p=root/'page.png';p.write_bytes(b'mock, no visual assertion')
   return {'document_sha256':'bad' if bad else sha256(Path(path).read_bytes()),'render_config_sha256':cfg,'pages':[str(p)],'artifact_sha256':{str(p):sha256(p.read_bytes())}}
  return render,calls
 def submit(self,s,sch,renderer,key='input'):
  with patch('web.preview_session.configuration',return_value=({},'cfg')):return s.submit_preview(key,scheduler=sch,renderer=renderer)
 def finish(self,s,identity):
  self.wait(lambda:s.preview_jobs[identity]['scheduler'].status(s.preview_owner,identity)['state'] not in ('queued','running'))
  with patch('web.async_preview.configuration',return_value=({},'cfg')):return s.preview_job_status(identity)
 def test_full_2015_projection_and_paging_lossless(self):
  s=self.model(True);b=s.current_bundle();records=b['projection']['records'];self.assertEqual(len(s.report['findings']),2015);gold=deepcopy(s.report);seen=[]
  view=object_page(records)
  for p in range(1,view['pages']+1):seen.extend(r['id'] for rows in object_page(records,page=p)['groups'].values() for r in rows)
  self.assertEqual(set(seen),{r['id'] for r in records});self.assertEqual(len(seen),len(records));self.assertEqual(s.report,gold);self.assertLessEqual(len(view['objects']),20)
 def test_sort_filter_range_do_not_change_identity(self):
  rows=self.model(True).current_bundle()['projection']['records'];view=object_page(rows,paragraph_range='81-100',descending=True);self.assertEqual(view['objects'][0],'paragraph:100');self.assertTrue(all(81<=r['locator']['paragraph']<=100 for r in view['records']));self.assertEqual({r['id'] for r in view['records']},{r['id'] for r in object_page(rows,paragraph_range='81-100')['records']})
 def test_invalid_range_and_page_clamp(self):
  rows=self.model().current_bundle()['projection']['records'];self.assertEqual(object_page(rows,page=1000)['page'],1)
  for value in ('0','4-2','x','1-2-3'):
   with self.assertRaises(DemoError):object_page(rows,paragraph_range=value)
 def test_page_selection_preserves_hidden_and_not_authorized_filter(self):
  s=self.model(True);records=s.current_bundle()['projection']['records'];a=object_page(records,page=1);b=object_page(records,page=2);keys=merge_page_selection([],a['page_keys'],a['page_keys'][:2]);keys=merge_page_selection(keys,b['page_keys'],b['page_keys'][:3]);self.assertEqual(len(keys),5)
  only=object_page(records,paragraph_range='390-400');self.assertEqual(selection_counts(keys,only)['outside_filter'],5);self.assertEqual(keys,merge_page_selection(keys,only['page_keys'],[]))
 def test_review_and_unsafe_never_in_page_keys(self):
  s=self.model(True);v=object_page(s.current_bundle()['projection']['records']);allowed={f['key'] for f in s.eligible()};self.assertTrue(set(v['filtered_keys'])<=allowed)
 def test_all_export_records_survive_pagination(self):
  s=self.model(True);s.prepare_reading_export();data=json.loads(s.reading_downloads()['report.json']);self.assertEqual(len([r for r in data['records'] if r['record_key'].startswith('R')]),2015);self.assertEqual(data['format_summary'],s.report['summary'])
 def test_mode_or_scope_change_clears_selection(self):
  s=self.model(True);s.set_selection([f['key'] for f in s.eligible()][:3]);s.set_mode('basic');self.assertFalse(s.selected);self.assertIsNone(s.report)
 def test_duplicate_submission_executes_once_and_background_does_not_mutate_session(self):
  s=self.model();sch=self.scheduler();gate=threading.Event();self.gates.append(gate);render,calls=self.renderer(gate);before=deepcopy(s.report);first=self.submit(s,sch,render);second=self.submit(s,sch,render);self.assertEqual(first['id'],second['id']);self.wait(lambda:len(calls)==1);self.assertFalse(s.preview_cache);self.assertEqual(s.report,before);gate.set();self.assertTrue(self.finish(s,first['id'])['accepted']);self.assertEqual(len(calls),1);self.assertEqual(calls[0][0],'paper-preview')
 def test_global_queue_limit_and_sequential_rendering(self):
  sch=self.scheduler(1);gate=threading.Event();self.gates.append(gate);render,calls=self.renderer(gate);a=self.model();b=self.model();c=self.model();one=self.submit(a,sch,render);self.wait(lambda:len(calls)==1);two=self.submit(b,sch,render);self.assertEqual(sch.status(b.preview_owner,two['id'])['state'],'queued');self.assertEqual(self.submit(c,sch,render)['state'],'failed');self.assertEqual(len(calls),1);gate.set();self.finish(a,one['id']);self.finish(b,two['id']);self.assertEqual(len(calls),2)
 def test_cancel_queued_prevents_start(self):
  sch=self.scheduler();gate=threading.Event();self.gates.append(gate);render,calls=self.renderer(gate);a=self.model();b=self.model();one=self.submit(a,sch,render);self.wait(lambda:len(calls)==1);two=self.submit(b,sch,render);state=b.cancel_preview(two['id']);self.assertEqual(state['state'],'cancelled');self.assertIn('不会启动',state['error']);gate.set();self.finish(a,one['id']);self.assertEqual(len(calls),1)
 def test_running_cancel_only_discards_and_allows_explicit_retry(self):
  s=self.model();sch=self.scheduler();gate=threading.Event();self.gates.append(gate);render,calls=self.renderer(gate);one=self.submit(s,sch,render);self.wait(lambda:len(calls)==1);state=s.cancel_preview(one['id']);self.assertIn('不表示子进程已停止',state['error']);two=self.submit(s,sch,render);self.assertNotEqual(one['id'],two['id']);gate.set();self.finish(s,two['id']);self.assertEqual(len(calls),2)
 def test_reset_snapshot_survives_but_result_not_received(self):
  s=self.model();sch=self.scheduler();gate=threading.Event();self.gates.append(gate);render,calls=self.renderer(gate);job=self.submit(s,sch,render);self.wait(lambda:len(calls)==1);s.reset();gate.set();self.wait(lambda:sch.active is None);self.assertEqual(s.preview_job_status(job['id'])['state'],'missing');self.assertFalse(s.preview_cache);self.assertEqual(len(calls),1)
 def test_rule_or_scope_epoch_change_rejects_old_job(self):
  s=self.model();sch=self.scheduler();gate=threading.Event();self.gates.append(gate);render,calls=self.renderer(gate);job=self.submit(s,sch,render);self.wait(lambda:len(calls)==1);s.set_body([4]);s.confirm();gate.set();self.wait(lambda:sch.active is None);self.assertFalse(s.preview_cache);self.assertEqual(s.preview_job_status(job['id'])['state'],'missing')
 def test_new_round_rejects_old_pending_result(self):
  s=self.model();s.set_selection([f['key'] for f in s.eligible()]);s.generate();sch=self.scheduler();gate=threading.Event();self.gates.append(gate);render,calls=self.renderer(gate);job=self.submit(s,sch,render,'round-1');self.wait(lambda:len(calls)==1);s.next_round();gate.set();self.wait(lambda:sch.active is None);self.assertFalse(s.preview_cache)
 def test_generating_new_output_does_not_bind_old_job_to_it(self):
  s=self.model();sch=self.scheduler();gate=threading.Event();self.gates.append(gate);render,calls=self.renderer(gate);job=self.submit(s,sch,render);self.wait(lambda:len(calls)==1);s.set_selection([f['key'] for f in s.eligible()]);s.generate();gate.set();self.finish(s,job['id']);self.assertIsNone(s.get_preview('round-1',verify_environment=False));self.assertIsNotNone(s.get_preview('input',verify_environment=False))
 def test_changed_environment_rejects_finished_result(self):
  s=self.model();sch=self.scheduler();render,calls=self.renderer();job=self.submit(s,sch,render);self.wait(lambda:sch.status(s.preview_owner,job['id'])['state']=='succeeded')
  with patch('web.async_preview.configuration',return_value=({},'new')):state=s.preview_job_status(job['id'])
  self.assertEqual(state['state'],'invalidated');self.assertFalse(s.preview_cache)
 def test_corrupted_artifact_refuses_acceptance(self):
  s=self.model();sch=self.scheduler();render,calls=self.renderer();job=self.submit(s,sch,render);self.wait(lambda:sch.status(s.preview_owner,job['id'])['state']=='succeeded');meta=sch.result(s.preview_owner,job['id']);Path(meta['pages'][0]).write_bytes(b'changed');self.assertEqual(self.finish(s,job['id'])['state'],'invalidated')
 def test_result_hash_mismatch_fails_job(self):
  s=self.model();sch=self.scheduler();render,calls=self.renderer(bad=True);job=self.submit(s,sch,render);self.assertEqual(self.finish(s,job['id'])['state'],'failed');self.assertFalse(s.preview_cache)
 def test_timeout_failure_allows_retry_without_changing_report(self):
  s=self.model();gold=deepcopy(s.report);sch=self.scheduler();fail,calls=self.renderer(fail=True);job=self.submit(s,sch,fail);self.assertEqual(self.finish(s,job['id'])['state'],'failed');render,calls=self.renderer();job=self.submit(s,sch,render);self.assertTrue(self.finish(s,job['id'])['accepted']);self.assertEqual(s.report,gold)
 def test_owner_isolation(self):
  s=self.model();other=self.model();sch=self.scheduler();render,calls=self.renderer();job=self.submit(s,sch,render)
  with self.assertRaises(DemoError):sch.status(other.preview_owner,job['id'])
  with self.assertRaises(DemoError):sch.cancel(other.preview_owner,job['id'])
  self.assertEqual(other.preview_job_status(job['id'])['state'],'missing');self.finish(s,job['id']);self.assertFalse(other.preview_cache)
 def test_polling_running_does_not_read_docs_or_probe_environment(self):
  s=self.model();sch=self.scheduler();gate=threading.Event();self.gates.append(gate);render,calls=self.renderer(gate);job=self.submit(s,sch,render);self.wait(lambda:len(calls)==1)
  with patch.object(s,'preview_targets',side_effect=AssertionError()),patch('web.async_preview.configuration',side_effect=AssertionError()):
   for _ in range(4):self.assertEqual(s.preview_job_status(job['id'])['state'],'running')
 def test_cached_preview_submission_creates_no_task(self):
  s=self.model();sch=self.scheduler();render,calls=self.renderer();job=self.submit(s,sch,render);self.finish(s,job['id']);self.assertEqual(self.submit(s,sch,render)['state'],'cached');self.assertEqual(len(calls),1)
 def test_missing_task_after_restart_not_fake_success(self):
  s=self.model();sch=self.scheduler();gate=threading.Event();self.gates.append(gate);render,calls=self.renderer(gate);job=self.submit(s,sch,render);s.preview_jobs[job['id']]['scheduler']=self.scheduler();self.assertEqual(s.preview_job_status(job['id'])['state'],'missing');self.assertFalse(s.preview_cache)
 def test_reset_does_not_delete_other_sessions_accepted_pages(self):
  a=self.model();b=self.model();sch=self.scheduler();render,calls=self.renderer();job=self.submit(b,sch,render);self.finish(b,job['id']);path=next(iter(b.preview_cache.values()))['pages'][0];a.reset();self.assertTrue(Path(path).is_file())
 def test_input_load_publishes_complete_classification(self):
  from core import suggest_paragraph_types
  s=WebSession(self.root/'atomic')
  def read(path):
   self.assertIsNone(s.inventory);return suggest_paragraph_types(path)
  with patch('web.session.suggest_paragraph_types',side_effect=read):self.assertTrue(s.load((ROOT/'samples/errors.docx').read_bytes(),'file.docx'))
  self.assertIsNotNone(s.inventory);self.assertIsNotNone(s.suggestions)
 def test_classification_failure_publishes_no_success_state(self):
  s=self.model()
  with patch('web.session.suggest_paragraph_types',side_effect=DemoError('分类读取失败')):self.assertFalse(s.load((ROOT/'samples/correct.docx').read_bytes(),'file.docx'))
  self.assertIsNone(s.inventory);self.assertIsNone(s.report);self.assertFalse(s.preview_jobs)
 def test_rule_hash_change_invalidates_pending(self):
  s=self.model();path=self.root/'rules.json';path.write_bytes(s.rules_path.read_bytes());s.rules_path=path;s.sync_rules();sch=self.scheduler();gate=threading.Event();self.gates.append(gate);renderer,calls=self.renderer(gate);job=self.submit(s,sch,renderer);self.wait(lambda:len(calls)==1);path.write_text(json.dumps(json.loads(path.read_text()),ensure_ascii=False,indent=4));self.assertTrue(s.sync_rules());gate.set();self.wait(lambda:sch.active is None);self.assertEqual(s.preview_job_status(job['id'])['state'],'missing');self.assertFalse(s.preview_cache)
 def test_input_changed_after_completion_is_rejected(self):
  s=self.model();sch=self.scheduler();renderer,calls=self.renderer();job=self.submit(s,sch,renderer);self.wait(lambda:sch.status(s.preview_owner,job['id'])['state']=='succeeded');s.input_path.write_bytes(b'changed externally');self.assertEqual(self.finish(s,job['id'])['state'],'invalidated');self.assertFalse(s.preview_cache)
 def test_original_and_round_bytes_preserved(self):
  s=self.model();raw=s.input_path.read_bytes();sch=self.scheduler();render,calls=self.renderer();job=self.submit(s,sch,render);self.finish(s,job['id']);self.assertEqual(s.input_path.read_bytes(),raw)
if __name__=='__main__':unittest.main()

class LongUIAcceptance(unittest.TestCase):
 def test_bounded_controls_cross_page_and_full_detail(self):
  from streamlit.testing.v1 import AppTest
  at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run();show(at,1);s=at.session_state['workflow']
  try:
   next(x for x in at.radio if x.label=='检查模式').set_value('正文及标题题注检查').run();s=at.session_state['workflow'];p=ROOT/'tests/fixtures/history/phase12/long-400.docx';s.load(p.read_bytes(),'long.docx');s.set_types(json.loads(p.with_suffix('.types.json').read_text())['paragraph_types']);s.confirm_and_check();at.run();self.assertFalse(at.exception);self.assertEqual(len(s.report['findings']),2015);self.assertLess(len(at.dataframe),8);self.assertLess(len(at.button),40);self.assertLessEqual(len(next(x for x in at.multiselect if x.label=='逐项选择修正').options),100);self.assertEqual(len(at.json),0)
   next(x for x in at.button if x.label=='选择本页可修正项').click().run();first=set(s.selected);next(x for x in at.number_input if x.label=='对象页码').set_value(2).run();self.assertEqual(first,set(s.selected));next(x for x in at.button if x.label=='选择本页可修正项').click().run();self.assertTrue(first<set(s.selected));chosen=set(s.selected);next(x for x in at.text_input if x.label.startswith('段落编号筛选')).set_value('390-400').run();self.assertEqual(chosen,set(s.selected));self.assertEqual(next(x for x in at.number_input if x.label=='对象页码').value,1);self.assertFalse(at.exception)
   next(x for x in at.toggle if x.label=='查看完整执行清单（含key）').set_value(True).run();self.assertFalse(at.exception)
   selected_frame=next(x.value for x in at.dataframe if 'key' in x.value.columns);self.assertEqual(set(selected_frame['key']),chosen)
  finally:s.reset()
 def test_lazy_json_explicitly_contains_full_report(self):
  from streamlit.testing.v1 import AppTest
  at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
  try:
   next(x for x in at.button if x.label=='使用错误样本').click().run();show(at,2,'paragraph');next(x for x in at.button if x.label=='核对完成并开始检查').click().run();self.assertEqual(len(at.json),0);show(at,5);next(x for x in at.toggle if x.label.startswith('显示原始完整JSON')).set_value(True).run();self.assertFalse(at.exception);self.assertEqual(json.loads(at.json[0].value)['findings'],at.session_state['workflow'].report['findings'])
  finally:at.session_state['workflow'].reset()

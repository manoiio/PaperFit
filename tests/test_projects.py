"""Project packages are untrusted data; verify real engine/files rather than UI presence."""
import unittest,json,zipfile,stat
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest.mock import patch
from web.session import WebSession
from core.project import stage,pack,MAX_ROUNDS
from core.package import DemoError,sha256
from core import check_document
ROOT=Path(__file__).resolve().parents[1]

class ProjectAcceptance(unittest.TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def model(self,ext=False,confirmed=True):
  s=WebSession(self.root);s.set_mode('extended' if ext else 'basic');p=ROOT/('samples/extended-errors.docx' if ext else 'samples/errors.docx');self.assertTrue(s.load(p.read_bytes(),'software-demo.docx'))
  if ext:s.set_types(json.loads(p.with_suffix('.types.json').read_text())['paragraph_types'])
  else:s.set_body([4,5,6,11,14,15])
  if confirmed:self.assertTrue(s.confirm_and_check())
  return s
 def rounds(self):
  s=self.model()
  for _ in range(2):s.set_selection([f['key'] for f in s.eligible()][:2]);self.assertTrue(s.generate());self.assertTrue(s.next_round())
  s.set_selection([f['key'] for f in s.eligible()][:1]);return s
 def restore(self,s,raw=None):s.stage_project(raw or s.prepare_project());return s.restore_project(acknowledged=True)
 def edited(self,s,fn):
  d,m=s.project_snapshot();fn(d);return pack(d,m)
 def reject(self,s,fn):
  p=s.input_path;old=p.read_bytes();r=deepcopy(s.report)
  with self.assertRaises(DemoError):s.stage_project(self.edited(s,fn))
  self.assertEqual(p.read_bytes(),old);self.assertEqual(s.report,r)
 def test_basic_fresh_check_equivalent(self):
  s=self.model()
  with patch('web.session.check_document',wraps=check_document) as check:
   n=self.restore(s);self.assertGreaterEqual(check.call_count,1)
  self.assertEqual(s.report['findings'],n.report['findings']);self.assertEqual(s.rules_hash,n.rules_hash)
 def test_scope_draft_and_adjustment_preserved(self):
  s=self.model(True,False);s.batch_types([8,20],'other');n=self.restore(s)
  self.assertEqual(n.paragraph_types,s.paragraph_types);self.assertIsNone(n.confirmed);self.assertIsNone(n.report);self.assertFalse(n.selected)
 def test_custom_template_and_sources_preserved_no_api(self):
  s=self.model(True);self.assertTrue(s.import_template((ROOT/'tests/fixtures/history/phase9/final/template-B-active.json').read_bytes()));self.assertTrue(s.apply_template());s.confirm_and_check()
  with patch('ai.template_spec.parse_template_requirements',side_effect=AssertionError('No API')),patch('core.preview.render_preview',side_effect=AssertionError('No renderer')):
   n=self.restore(s)
  self.assertEqual(s.active_template,n.active_template);self.assertEqual(s.rules_hash,n.rules_hash);self.assertEqual(n.report['findings'],s.report['findings'])
 def test_unapplied_template_edits_stay_draft(self):
  s=self.model(True,False);s.import_template((ROOT/'tests/fixtures/history/phase9/final/template-B-active.json').read_bytes());s.edit_template('heading1_font_size','manual',20,touched=True)
  n=self.restore(s);self.assertIsNone(n.active_template);self.assertEqual(n.template_values['heading1_font_size'],20);self.assertIn('heading1_font_size',n.template_touched);self.assertIsNone(n.confirmed)
 def test_short_spec_draft_preserved_without_request(self):
  s=self.model(False,False);s.set_spec_text('正文小四号，1.5倍行距');s.edit_draft('R05','manual',14,touched=True)
  n=self.restore(s);self.assertEqual(n.spec_text,s.spec_text);self.assertEqual(n.draft_values['R05'],14);self.assertIn('R05',n.draft_edited)
 def test_two_round_parent_and_current(self):
  n=self.restore(self.rounds());self.assertEqual(n.current_round,2);self.assertEqual(n.generation_count,2);self.assertEqual([h['result']['round']['input_round'] for h in n.history],[0,1])
 def test_filter_selection_invalid_keys(self):
  s=self.model();valid=s.eligible()[0]['key']
  raw=self.edited(s,lambda d:d['state'].update(selected=[valid,'R05:paragraph=999']))
  n=self.restore(s,raw);self.assertEqual(n.selected,[valid]);self.assertIn('已丢弃1个',n.project_notice)
 def test_continue_unique_original_and_previous_preserved(self):
  n=self.restore(self.rounds());old={p:p.read_bytes() for p in [n.original_path,*[Path(h['result']['output']) for h in n.history]]}
  self.assertTrue(n.generate());self.assertEqual(n.result['round']['number'],3);self.assertTrue(n.next_round());self.assertEqual(n.report['summary']['problem_count'],6)
  for p,data in old.items():self.assertEqual(p.read_bytes(),data)
 def test_resave_restore_same_rules_scope_and_result(self):
  n=self.restore(self.rounds());m=self.restore(n);self.assertEqual(n.report['findings'],m.report['findings']);self.assertEqual(n.paragraph_types,m.paragraph_types);self.assertEqual(n.current_round,m.current_round)
 def test_docx_deduplicated_by_hash(self):
  s=self.rounds();d,_=s.project_snapshot();self.assertEqual(len(d['documents']),3);self.assertEqual(len({x['sha256'] for x in d['documents']}),3)
 def test_repeated_prepare_reuses_bytes_no_extra_files(self):
  s=self.rounds();raw=s.prepare_project();count=len(list(s.task_dir.iterdir()))
  with patch('web.project_session.pack',side_effect=AssertionError('No repack')):self.assertIs(s.prepare_project(),raw);self.assertIs(s.project_download(),raw)
  self.assertEqual(len(list(s.task_dir.iterdir())),count)
 def test_selection_change_invalidates_download(self):
  s=self.model();s.prepare_project();s.set_selection([s.eligible()[0]['key']]);self.assertIsNone(s.project_download())
 def test_classification_change_invalidates_download(self):
  s=self.model(True);s.prepare_project();s.batch_types([8],'other');self.assertIsNone(s.project_download())
 def test_mode_change_invalidates_download(self):
  s=self.model();s.prepare_project();s.set_mode('extended');self.assertIsNone(s.project_download())
 def test_template_change_invalidates_download(self):
  s=self.model();s.prepare_project();s.import_template((ROOT/'tests/fixtures/history/phase9/final/template-B-active.json').read_bytes());self.assertIsNone(s.project_download())
 def test_output_external_change_refused(self):
  s=self.rounds();s.prepare_project();Path(s.history[0]['result']['output']).write_bytes(b'changed')
  with self.assertRaises(DemoError):s.project_download()
 def test_external_input_refused(self):
  s=self.model();s.prepare_project();s.input_path.write_bytes(b'bad')
  with self.assertRaises(DemoError):s.project_download()
 def test_missing_history_refused(self):
  s=self.rounds();s.prepare_project();Path(s.history[0]['result']['output']).unlink()
  with self.assertRaises(OSError):s.project_download()
 def test_ack_required_preserves_current(self):
  s=self.model();s.stage_project(s.prepare_project());p=s.input_path
  with self.assertRaises(DemoError):s.restore_project()
  self.assertEqual(s.input_path,p);self.assertIsNotNone(s.project_pending)
 def test_history_peek_not_switch(self):
  n=self.restore(self.rounds());p=n.input_path;sha=n.inventory['input_sha256'];h=n.history[0];b=n.history_bundle(h['stem']);n.history_reading_downloads(h['stem'])
  self.assertEqual(n.input_path,p);self.assertEqual(n.inventory['input_sha256'],sha);self.assertIsNone(b['preservation']);self.assertIn('保存时',b['saved_record']['status'])
 def test_history_explicit_continue_rechecks(self):
  n=self.restore(self.rounds());self.assertTrue(n.continue_history(n.history[0]['stem'],acknowledged=True));self.assertEqual(n.current_round,1);self.assertEqual(n.generation_count,2);self.assertIsNotNone(n.report)
  n.set_selection([f['key'] for f in n.eligible()][:1]);self.assertTrue(n.generate());self.assertEqual(n.result['round']['number'],3)
 def test_forged_saved_success_not_current(self):
  s=self.rounds();raw=self.edited(s,lambda d:d['state']['history'][0]['saved_summary'].update(preservation={'all':True},format={'problem_count':0}))
  n=self.restore(s,raw);self.assertGreater(n.report['summary']['problem_count'],0);self.assertIsNone(n.history[0]['result']['preservation']);self.assertTrue(all(c['verification']=='review' for c in n.history[0]['result']['changes']))
 def test_unknown_version_refused(self):self.reject(self.model(),lambda d:d.update(version=999))
 def test_unknown_executable_field_refused(self):self.reject(self.model(),lambda d:d['state'].update(command='run'))
 def test_scope_hash_refused(self):self.reject(self.model(),lambda d:d['state']['scope'].update(file_sha256='0'*64))
 def test_invalid_classification_refused(self):self.reject(self.model(True),lambda d:d['state']['scope']['types'].update({'8':'run_script'}))
 def test_cycles_refused(self):self.reject(self.rounds(),lambda d:d['state']['history'][0].update(parent=2))
 def test_wrong_parent_hash_refused(self):self.reject(self.rounds(),lambda d:d['state']['history'][1].update(parent=0))
 def test_current_round_ambiguous_refused(self):self.reject(self.rounds(),lambda d:d['state'].update(current_round=1))
 def test_bool_round_refused(self):self.reject(self.model(),lambda d:d['state'].update(current_round=True))
 def test_reduce_history_explicit_checkpoint(self):
  s=self.rounds();n=self.restore(s,s.prepare_project('current'));self.assertEqual(len(n.history),0);self.assertEqual(n.current_round,2);self.assertEqual(n.project_checkpoint['round'],2)
  n.set_selection([n.eligible()[0]['key']]);n.generate();n.next_round();m=self.restore(n);self.assertEqual(m.current_round,3);self.assertEqual(len(m.history),1)
 def test_import_failure_only_removes_its_directory(self):
  s=self.model();old=set(self.root.iterdir());d,m=s.project_snapshot();member=d['documents'][0]['member'];m[member]=b'not-docx';d['documents'][0]['sha256']=sha256(m[member]);d['state'].update(original=sha256(m[member]),current=sha256(m[member]));d['state']['scope']['file_sha256']=sha256(m[member]);d['state']['checkpoint']['file']=sha256(m[member])
  with self.assertRaises(DemoError):s.stage_project(pack(d,m))
  self.assertEqual(old,set(self.root.iterdir()));self.assertIsNotNone(s.report)
 def test_independent_sessions_paths_downloads(self):
  a=self.model();raw=a.prepare_project();b=self.model();b.stage_project(raw);n=b.restore_project(acknowledged=True);self.assertNotEqual(a.task_dir,n.task_dir);self.assertNotEqual(a.preview_owner,n.preview_owner);a.input_path.write_bytes(b'changed');self.assertIsNotNone(n.project_download() if n.project_export else n.prepare_project())
 def test_cancel_pending_does_not_clean_other_task(self):
  a=self.model();b=self.model();a.stage_project(a.prepare_project());p=a.project_pending['directory'];a.cancel_project_import();self.assertFalse(p.exists());self.assertTrue(b.input_path.exists());self.assertTrue(a.input_path.exists())
 def test_old_background_invalidated_only_after_adoption(self):
  s=self.model();s.stage_project(s.prepare_project())
  with patch.object(s,'invalidate_preview_jobs',wraps=s.invalidate_preview_jobs) as cancel:
   n=s.restore_project(acknowledged=True);self.assertEqual(cancel.call_count,1)
  self.assertFalse(n.preview_jobs);self.assertFalse(n.preview_cache);self.assertIsNone(n.preview_environment)
 def test_package_privacy_and_data_only(self):
  s=self.rounds();(s.task_dir/'.env').write_text('DEEPSEEK_API_KEY=sk-secret');(s.task_dir/'log.txt').write_text('private log');raw=s.prepare_project()
  with zipfile.ZipFile(BytesIO(raw)) as z:
   self.assertTrue(all(n=='project.json' or n.startswith(('documents/','rules/')) for n in z.namelist()));manifest=z.read('project.json').decode();self.assertNotIn(str(self.root),manifest);self.assertNotIn('sk-secret',manifest);self.assertNotIn('preview_owner',manifest);self.assertNotIn('pickle',manifest)
 def malicious(self,kind):
  s=self.model();raw=s.prepare_project();stream=BytesIO()
  with zipfile.ZipFile(BytesIO(raw)) as old,zipfile.ZipFile(stream,'w') as z:
   for n in old.namelist():
    if kind=='missing' and n.endswith('.docx'):continue
    z.writestr(n,old.read(n))
   if kind=='duplicate':z.writestr('project.json',old.read('project.json'))
   elif kind=='hash':z.writestr('rules/9999.json',b'wrong')
   elif kind=='symlink':
    info=zipfile.ZipInfo('documents/9999.docx');info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,b'outside')
   else:z.writestr(kind,b'outside')
  with self.assertRaises(DemoError):s.stage_project(stream.getvalue())
 def test_traversal_refused(self):self.malicious('../outside.docx')
 def test_absolute_refused(self):self.malicious('/outside.docx')
 def test_duplicate_refused(self):self.malicious('duplicate')
 def test_symlink_refused(self):self.malicious('symlink')
 def test_missing_refused(self):self.malicious('missing')
 def test_unreferenced_member_refused(self):self.malicious('hash')
 def test_mismatched_file_hash_refused(self):
  s=self.model();d,m=s.project_snapshot();m[d['documents'][0]['member']]=b'changed'
  with self.assertRaises(DemoError):s.stage_project(pack(d,m))
 def test_size_limits_checked_before_writing(self):
  import tomllib
  cfg=tomllib.loads((ROOT/'.streamlit/config.toml').read_text());self.assertGreaterEqual(cfg['server']['maxUploadSize'],100)
  s=self.model();raw=s.prepare_project()
  with patch('core.project.MAX_TOTAL',1024):
   with self.assertRaises(DemoError):s.stage_project(raw)
  with patch('core.project.MAX_MEMBERS',1):
   with self.assertRaises(DemoError):s.stage_project(raw)
  with patch('core.project.MAX_DOCX',100):
   with self.assertRaises(DemoError):s.stage_project(raw)
 def test_rule_bytes_tampered_refused(self):
  s=self.model();d,m=s.project_snapshot();name=d['rules'][0]['member'];m[name]=b'{}';h=sha256(m[name]);d['rules'][0]['sha256']=h;d['state']['rule']=h
  with self.assertRaises(DemoError):s.stage_project(pack(d,m))
 def test_plain_zip_not_project(self):
  stream=BytesIO()
  with zipfile.ZipFile(stream,'w') as z:z.writestr('anything.txt','data')
  with self.assertRaises(DemoError):self.model().stage_project(stream.getvalue())
 def test_draft_edit_invalidates_saved_zip(self):
  s=self.model();s.prepare_project();s.edit_draft('R05','manual',14,touched=True);self.assertIsNone(s.project_download())
 def test_renderer_running_discard_does_not_attach_after_restore(self):
  import threading,time
  from core.preview_jobs import PreviewJobs
  s=self.model();gate=threading.Event();started=threading.Event();sch=PreviewJobs();calls=[]
  def render(path,root,context):
   started.set();calls.append(sha256(Path(path).read_bytes()));gate.wait(3);root.mkdir(parents=True);p=root/'page.png';p.write_bytes(b'controlled')
   return {'document_sha256':calls[-1],'render_config_sha256':'cfg','pages':[str(p)],'artifact_sha256':{str(p):sha256(p.read_bytes())}}
  try:
   with patch('web.preview_session.configuration',return_value=({},'cfg')):job=s.submit_preview('input',scheduler=sch,renderer=render)
   self.assertTrue(started.wait(2));n=self.restore(s);self.assertEqual(sch.status(s.preview_owner,job['id'])['state'],'cancelled');self.assertEqual(n.preview_job_status(job['id'])['state'],'missing');self.assertIsNone(n.get_preview('input'))
  finally:
   gate.set()
   if sch.thread:sch.thread.join(4)
  self.assertFalse(n.preview_cache);self.assertEqual(len(calls),1)
 def test_restore_cancels_queued_only_not_other_owner(self):
  import threading
  from core.preview_jobs import PreviewJobs
  s=self.model();other=self.model();sch=PreviewJobs();gate=threading.Event();started=threading.Event();calls=[]
  def render(path,root,context):
   started.set();calls.append(1);gate.wait(3);return {'document_sha256':sha256(Path(path).read_bytes()),'render_config_sha256':'cfg'}
  try:
   with patch('web.preview_session.configuration',return_value=({},'cfg')):first=other.submit_preview('input',scheduler=sch,renderer=render)
   self.assertTrue(started.wait(2))
   with patch('web.preview_session.configuration',return_value=({},'cfg')):second=s.submit_preview('input',scheduler=sch,renderer=render)
   self.assertEqual(sch.status(s.preview_owner,second['id'])['state'],'queued');self.restore(s)
   self.assertEqual(sch.status(other.preview_owner,first['id'])['state'],'running');self.assertEqual(sch.status(s.preview_owner,second['id'])['state'],'missing')
  finally:
   gate.set()
   if sch.thread:sch.thread.join(4)
  self.assertEqual(len(calls),1)
 def test_legacy_custom_rules_restore_same(self):
  s=self.model();s.set_spec_text('正文小四号，1.5倍行距');s.edit_draft('R05','manual',14,touched=True);s.edit_draft('R06','manual',2,touched=True);self.assertTrue(s.apply_draft());s.confirm_and_check()
  n=self.restore(s);self.assertIsNone(n.active_template);self.assertEqual(s.rules_hash,n.rules_hash);self.assertEqual(s.report['findings'],n.report['findings'])
 def test_pending_import_file_tamper_refused_without_current_change(self):
  s=self.model();s.stage_project(s.prepare_project());p=s.input_path
  next(iter(s.project_pending['paths'].values())).write_bytes(b'tampered')
  with self.assertRaises(DemoError):s.restore_project(acknowledged=True)
  self.assertEqual(s.input_path,p);self.assertIsNotNone(s.report);self.assertIsNone(s.project_pending)
  s.stage_project(s.prepare_project());current=s.project_pending['manifest']['state']['current'];s.project_pending['paths'][current].write_bytes(b'changed')
  with self.assertRaises(DemoError):s.project_review()
 def test_editor_invalid_value_refused(self):self.reject(self.model(),lambda d:d['state']['editor']['draft_values'].update(R05=True))
 def test_version2_template_sources_compatible(self):
  from core.templates import defaults,make_template,FIELDS
  from core import load_rules
  s=self.model();base=load_rules();values=defaults(base);sources={n:{'kind':'default_inherited','quote':'','location':None} for n in FIELDS};cfg=make_template('旧正文演示',values,sources,[],base)
  s.import_template(json.dumps(cfg,ensure_ascii=False).encode());s.apply_template();s.confirm_and_check();n=self.restore(s);self.assertEqual(n.active_template['structure_version'],2);self.assertEqual(n.active_template['field_sources'],s.active_template['field_sources'])
 def test_restore_review_full_custom_alignment_and_spacing(self):
  s=self.model(True);s.import_template((ROOT/'tests/fixtures/history/phase9/final/template-B-active.json').read_bytes());s.apply_template();s.confirm_and_check();s.stage_project(s.prepare_project());rules,rows=s.project_review()
  self.assertEqual(len(rules),12);self.assertEqual(len(rows),len(s.inventory['paragraphs']));r=next(r for r in rules if r['规则'].startswith('R09'));self.assertIn('居右',r['要求']);self.assertIn('1.5倍行距',r['要求']);self.assertNotIn('单倍',r['要求'])
 def test_full_heading_justified_summary_supported(self):
  from web.presentation import fmt
  text=fmt({'font_cn':'黑体','font_latin':'Times New Roman','size_pt':20,'alignment':'both','line_multiple':2},'R08',True)
  self.assertIn('两端对齐',text);self.assertIn('2倍行距',text)
 def test_streamlit_restore_rebinds_uploader_and_requires_new_ack(self):
  from streamlit.testing.v1 import AppTest
  s=self.rounds();raw=s.prepare_project();s.stage_project(raw)
  app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
  app.session_state['workflow']=s;app.run()
  self.assertFalse(app.exception)
  first=[x.proto.id for x in app.get('file_uploader') if '项目包' in x.proto.label][0]
  next(x for x in app.checkbox if x.label=='已核对恢复摘要、规则与范围；同意切换当前工作').check();app.run()
  next(x for x in app.button if x.label=='核对并恢复项目').click();app.run()
  self.assertFalse(app.exception);n=app.session_state['workflow'];self.assertEqual(n.current_round,2);self.assertIsNotNone(n.report)
  second=[x.proto.id for x in app.get('file_uploader') if '项目包' in x.proto.label][0];self.assertNotEqual(first,second)
  n.stage_project(raw);app.run();ack=next(x for x in app.checkbox if x.label=='已核对恢复摘要、规则与范围；同意切换当前工作');self.assertFalse(ack.value)
  ack.check();app.run();next(x for x in app.button if x.label=='核对并恢复项目').click();app.run();self.assertFalse(app.exception);self.assertEqual(app.session_state['workflow'].current_round,2)
  n=app.session_state['workflow'];current=n.input_path;n.stage_project(raw);pending=n.project_pending;n.project_pending['paths'][pending['manifest']['state']['current']].write_bytes(b'changed');app.run()
  self.assertFalse(app.exception);self.assertEqual(n.input_path,current);self.assertIsNone(n.project_pending);self.assertIsNotNone(n.report)

if __name__=='__main__':unittest.main()

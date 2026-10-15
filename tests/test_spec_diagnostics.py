import unittest,json,tempfile
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from core import spec_diagnostics as sd,rule_bundle as rb,check_document
from core.package import DemoError,Package,NS,q
from core.norms import selected_segments
from ai.workbench_spec import parse_requirements,parse_diagnosed
from ai.short_spec import Settings
from tests.test_workbench import response,SEGMENTS,make_session,scopes

ROOT=Path(__file__).resolve().parents[1]
def rec(data=None,segments=SEGMENTS,**kw):return sd.make_record(segments,json.dumps(response(segments) if data is None else data,ensure_ascii=False),**kw)
def envelope(content,finish='stop',**message):return json.dumps({'choices':[{'finish_reason':finish,'message':{'content':content,**message}}]}).encode()
class SpecDiagnosisTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.s=make_session(Path(self.tmp.name));self.s.workbench_text('\n'.join(s['text'] for s in SEGMENTS),SEGMENTS);self.s.confirm_workbench_excerpt()
 def tearDown(self):self.tmp.cleanup()
 def test_legal_equal_strict(self):
  r=rec();a=sd.diagnose(r);self.assertEqual(a['status'],'validated');self.assertEqual(a['strict_draft'],rb.validate_draft(response(),SEGMENTS));self.assertEqual(a['summary']['qualified'],42)
 def test_independent_errors_and_qualified_candidates(self):
  d=response();d['main']['fields']['font_size']['value']=True;d['front']['fields']['cover_title__font_size']['unit']='cm';a=sd.diagnose(rec(d));self.assertEqual(a['summary']['isolated'],2);self.assertEqual(a['summary']['qualified'],40);self.assertEqual(a['status'],'isolated');self.assertIn('VALUE',[r['code'] for r in a['records']]);self.assertIn('UNIT_SUPPORT',[r['code'] for r in a['records']])
 def test_old_strict_still_rejects(self):
  d=response();d['main']['fields']['font_size']['location']='L2'
  with self.assertRaises(DemoError):rb.validate_draft(d,SEGMENTS)
 def test_invalid_issue_keeps_related_fields_isolated(self):
  d=response();d['main']['issues']=[{'fields':['font_size'],'quote':'假的','location':'bad','reason':'unsupported'}];a=sd.diagnose(rec(d));self.assertEqual(a['fields']['main.font_size']['state'],'isolated');self.assertIn('main.issues.0',a['unresolved']);self.assertEqual(a['summary']['qualified'],41)
 def test_unknown_issue_influence_blocks_module(self):
  d=response();d['front']['issues']=[{'fields':['execute'],'quote':'X','location':'X','reason':'unsupported'}];a=sd.diagnose(rec(d));self.assertTrue(all(a['fields']['front.'+n]['state']=='isolated' for n in rb.FIELDS['front']));self.assertGreater(a['summary']['qualified'],0)
 def test_short_location_unique_and_explicit(self):
  d=response();f=d['main']['fields']['font_size'];f['location']='L2';r=rec(d);a=sd.diagnose(r);self.assertEqual(a['fields']['main.font_size']['suggestion']['to'],SEGMENTS[1]['location']);self.assertEqual(sd.diagnose(r)['status'],'isolated');f['location']=SEGMENTS[1]['location'];r=sd.revise(r,'main.fields.font_size','candidate',f,'核对唯一原行号及完整原文');a=sd.diagnose(r);self.assertEqual(a['status'],'validated');self.assertIn('main.font_size',a['user_confirmed']);self.assertEqual(json.loads(r['content'])['main']['fields']['font_size']['location'],'L2')
 def test_repeated_quote_no_quick_mapping(self):
  f={'location':'L2','quote':'正文1.5倍行距'};self.assertIsNone(sd.suggestion(f,SEGMENTS));self.assertIsNone(sd.suggestion({'location':'L1','quote':'正文12pt'},[{'location':'TXT:L1','text':'正文12pt'},{'location':'DOCX:L1','text':'正文12pt'}]))
 def test_quote_paraphrase_and_wrong_location_isolated(self):
  for quote,location in [('正文字号小四号',SEGMENTS[1]['location']),('正文小四号',SEGMENTS[2]['location']),('正文中文字体宋体正文小四号',SEGMENTS[1]['location'])]:
   d=response();d['main']['fields']['font_size'].update(quote=quote,location=location);a=sd.diagnose(rec(d));self.assertEqual(a['fields']['main.font_size']['state'],'isolated')
 def test_source_repair_cannot_hide_conflict(self):
  segments=SEGMENTS+[{'location':'摘录:L98','text':'正文四号。'}];d=response();d['main']['fields']['font_size']['location']='L2';r=rec(d,segments)
  f=deepcopy(d['main']['fields']['font_size']);f['location']=SEGMENTS[1]['location']
  with self.assertRaises(DemoError):sd.revise(r,'main.fields.font_size','candidate',f,'试图只改来源但不删除原文冲突')
  r=sd.revise(r,'main.fields.font_size','manual',14,'明确选择14pt，原文冲突保留');self.assertEqual(sd.diagnose(r)['status'],'validated')
 def test_type_unit_object_errors(self):
  for changes in ({'value':'12'},{'unit':'mm'},{'quote':'一级标题18pt','value':18,'location':SEGMENTS[2]['location']}):
   d=response();d['main']['fields']['font_size'].update(changes);a=sd.diagnose(rec(d));self.assertEqual(a['fields']['main.font_size']['state'],'isolated')
 def test_issue_removal_needs_per_field_confirmation(self):
  d=response();d['main']['issues']=[{'fields':['font_size'],'quote':SEGMENTS[0]['text'],'location':SEGMENTS[0]['location'],'reason':'unsupported'}];r=rec(d);i=deepcopy(d['main']['issues'][0]);i['fields']=[];r=sd.revise(r,'main.issues.0','issue',i,'核对为免责声明，不是正文字号限制');a=sd.diagnose(r);self.assertEqual(a['fields']['main.font_size']['state'],'isolated');r=sd.revise(r,'main.fields.font_size','candidate',d['main']['fields']['font_size'],'再次核对实际字段并以用户值采用');self.assertEqual(sd.diagnose(r)['status'],'validated')
 def test_retain_issue_manual_or_disabled(self):
  d=response();d['main']['issues']=[{'fields':['font_size'],'quote':SEGMENTS[1]['text'],'location':SEGMENTS[1]['location'],'reason':'ambiguous'}]
  for action,value in [('manual',14),('disabled',None)]:
   r=sd.revise(rec(d),'main.fields.font_size',action,value,'明确手动取舍或不检查，提示保留');a=sd.diagnose(r);self.assertEqual(a['status'],'validated');self.assertEqual(len(a['strict_draft']['main']['issues']),1);self.assertNotIn('font_size',a['strict_draft']['main']['fields'])
 def test_protocols_stay_whole_rejection(self):
  for content,kw in [('{',{}),('{"main":{},"main":{}}',{}),(json.dumps(response()),{'finish_reason':'length'}),(json.dumps(response()),{'tool_calls':True}),('',{})]:
   r=sd.make_record(SEGMENTS,content,**kw);self.assertEqual(sd.diagnose(r)['status'],'rejected')
   with self.assertRaises(DemoError):sd.revise(r,'main.fields.font_size','manual',12,'不能从整体拒绝中拼出草稿')
 def test_unknown_module_or_executable_field_rejected(self):
  for d in ({**response(),'execute':{}},response()):
   if 'execute' not in d:d['main']['fields']['execute']='code'
   self.assertEqual(sd.diagnose(rec(d))['status'],'rejected')
 def test_no_network_retry_and_full_snapshot(self):
  calls=[]
  def transport(req,timeout):calls.append(req.data);return envelope('{')
  r=parse_diagnosed(SEGMENTS,config=Settings('test-key'),transport=transport);self.assertEqual(len(calls),1);self.assertEqual(r['segments'],SEGMENTS);self.assertEqual(r['content'],'{');self.assertEqual(sd.diagnose(r)['status'],'rejected');self.assertNotIn('test-key',json.dumps(r))
 def test_default_parser_strict_protocol_unchanged(self):
  for kw in ({'finish':'length'},{'tool_calls':[{'name':'x'}]}):
   with self.assertRaises(DemoError):parse_requirements(SEGMENTS,config=Settings('test-key'),transport=lambda *args:envelope(json.dumps(response()),**kw))
 def test_diagnosed_request_valid_json_isolates_instead_of_apply(self):
  d=response();d['main']['fields']['font_size']['value']=True;r=parse_diagnosed(SEGMENTS,config=Settings('test-key'),transport=lambda *args:envelope(json.dumps(d)));self.assertEqual(r['receipt']['request_count'],1);self.assertEqual(sd.diagnose(r)['summary']['qualified'],41)
 def test_synthetic_repairs_all_and_effective_docx_equal(self):
  self.s.load_synthetic_diagnostic();a=self.s.diagnostic_analysis();paths=[m+'.fields.'+n for short,f in a['fields'].items() if f['suggestion'] for m,n in [short.split('.')]];self.s.repair_unique_sources(paths,acknowledged=True)
  r=self.s.diagnostic_store()['current'];d=json.loads(r['content']);f=deepcopy(d['main']['fields']['line_spacing']);f['location']='TXT:L2';self.s.repair_diagnostic('main.fields.line_spacing','candidate',f,'手工核对重复原句的准确正文来源')
  for m,loc in [('main','TXT:L1'),('front','TXT:L14')]:
   i=deepcopy(d[m]['issues'][0]);i.update(fields=[],location=loc);self.s.repair_diagnostic(m+'.issues.0','issue',i,'核对为与执行字段无关的说明')
  self.assertEqual(self.s.diagnostic_analysis()['status'],'validated');self.s.use_diagnostic_draft(acknowledged=True);self.s.workbench_policy('keep',acknowledged=True);self.s.workbench_edit('front','cover_title__font_size','manual',24);b=self.s.apply_workbench(acknowledged=True);self.assertEqual(b['provenance']['main']['font_size']['kind'],'user_confirmed');scopes(self.s);self.s.set_selection([f['key'] for f in self.s.eligible()]);self.assertTrue(self.s.generate(),self.s.error)
  self.assertEqual(Path(self.s.result['output']).read_bytes(),(ROOT/'tests/fixtures/history/phase24/browser-round2.docx').read_bytes())
 def test_unresolved_does_not_become_missing_policy(self):
  d=response();d['main']['fields']['font_size']['value']=True;self.s.receive_diagnostic(rec(d));self.assertIsNone(self.s.workbench['draft'])
  with self.assertRaises(DemoError):self.s.use_diagnostic_draft(acknowledged=True)
  self.assertIsNone(self.s.workbench['active'])
 def test_excerpt_change_archives_and_invalidates(self):
  self.s.receive_diagnostic(rec());self.s.use_diagnostic_draft(acknowledged=True);self.s.workbench_text('正文四号。');self.assertIsNone(self.s.workbench['draft']);self.assertIsNone(self.s.diagnostic_store()['current']);self.assertEqual(len(self.s.diagnostic_store()['history']),1)
  with self.assertRaises(DemoError):self.s.use_diagnostic_draft(acknowledged=True)
 def test_wrong_snapshot_hash_and_import_rejected(self):
  r=rec();r['input_sha256']='0'*64
  with self.assertRaises(DemoError):sd.diagnose(r)
  segments=[{'location':'TXT:L1','text':'正文四号。'}];r=sd.make_record(segments,json.dumps(response()))
  with self.assertRaises(DemoError):self.s.receive_diagnostic(r)
 def test_project_unapplied_repair_restore_zero_network(self):
  self.s.load_synthetic_diagnostic();self.s.repair_diagnostic('main.fields.font_size','manual',14,'明确手动选择14pt但尚不应用');before=self.s.rules_hash;self.s.prepare_project();raw=self.s.project_download();other=make_session(Path(self.tmp.name)/'other');other.stage_project(raw)
  with patch('ai.workbench_spec.parse_diagnosed',side_effect=AssertionError('No API')):new=other.restore_project(acknowledged=True)
  self.assertEqual(new.rules_hash,before);self.assertEqual(len(new.diagnostic_store()['current']['edits']),1);self.assertEqual(new.diagnostic_analysis()['status'],'isolated');self.assertTrue(new.workbench['historical'])
 def test_active_unchanged_on_bad_bundle_and_storage_failure(self):
  self.s.receive_diagnostic(rec());self.s.use_diagnostic_draft(acknowledged=True);self.s.workbench_policy('keep',acknowledged=True);before=self.s.rules_hash
  with patch('web.workbench_session.write_new',side_effect=OSError('disk')):
   with self.assertRaises(OSError):self.s.apply_workbench(acknowledged=True)
  self.assertEqual(self.s.rules_hash,before)
 def test_no_diagnostic_history_in_rule_bundle(self):
  self.s.receive_diagnostic(rec());self.s.use_diagnostic_draft(acknowledged=True);self.s.workbench_policy('keep',acknowledged=True);self.s.apply_workbench(acknowledged=True);b=json.loads(self.s.rule_bundle_download());self.assertNotIn('diagnostics',b);self.assertNotIn('content',b)
 def test_capacity_and_sensitive_text(self):
  r=sd.make_record(SEGMENTS,'x'*65537);self.assertIsNone(r['content']);self.assertEqual(sd.diagnose(r)['status'],'rejected')
  r=sd.make_record(SEGMENTS,'/Users/private/file');self.assertIsNone(r['content'])
  r=rec();r['edits']=[{'path':'main.fields.font_size','action':'manual','data':12,'reason':'明确选择'}]*101
  with self.assertRaises(DemoError):sd.validate_record(r)
 def test_isolated_sessions_and_archive_capacity(self):
  self.s.receive_diagnostic(rec());other=make_session(Path(self.tmp.name)/'other');self.assertIsNone(other.diagnostic_store()['current']);self.s.diagnostic_store()['history']=[rec()]*3
  with self.assertRaises(DemoError):self.s.workbench_text('正文四号。')
  self.assertEqual(self.s.workbench['segments'],SEGMENTS)
 def test_raw_html_never_executed_or_repaired(self):
  d=response();d['main']['fields']['font_size']['quote']='<script>alert(1)</script>';a=sd.diagnose(rec(d));self.assertEqual(a['fields']['main.font_size']['state'],'isolated');self.assertIn('<script>',json.dumps(a))
 def test_adoption_record_tamper_rejected(self):
  self.s.receive_diagnostic(rec());self.s.use_diagnostic_draft(acknowledged=True);self.s.diagnostic_store()['current']['edits'].append({'path':'main.fields.font_size','action':'disabled','data':None,'reason':'篡改采用后记录'})
  with self.assertRaises(DemoError):self.s.proposed_rule_bundle()

 def test_issue_form_uses_submitted_relation_and_reason(self):
  from streamlit.testing.v1 import AppTest
  self.s.load_synthetic_diagnostic();app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);app.session_state['workflow']=self.s;app.run();self.assertFalse(app.exception)
  next(x for x in app.radio if x.label=='关联决定').set_value('note')
  next(x for x in app.selectbox if x.label=='提示来源位置').set_value('TXT:L1')
  next(x for x in app.text_input if x.label=='用户决定与理由（必填）').set_value('已经核对免责声明，只是说明并不阻止执行字段')
  next(x for x in app.button if x.label=='记录提示决定并重新校验').click();app.run();self.assertFalse(app.exception)
  e=self.s.diagnostic_store()['current']['edits'][-1];self.assertEqual(e['data']['fields'],[]);self.assertEqual(e['data']['location'],'TXT:L1');self.assertTrue(e['reason'].startswith('已经核对'))
  self.assertEqual(self.s.diagnostic_analysis()['fields']['main.font_size']['state'],'isolated')
 def test_batch_repair_is_atomic_on_bad_member(self):
  self.s.load_synthetic_diagnostic();before=deepcopy(self.s.diagnostic_store()['current'])
  with self.assertRaises(DemoError):self.s.repair_unique_sources(['main.fields.font_size','main.fields.line_spacing'],acknowledged=True)
  self.assertEqual(self.s.diagnostic_store()['current'],before)
 def test_diagnostic_import_is_historical_and_no_apply(self):
  self.s.receive_diagnostic(rec());raw=self.s.diagnostic_download();other=make_session(Path(self.tmp.name)/'imported');other.workbench_text('\n'.join(s['text'] for s in SEGMENTS),SEGMENTS);other.confirm_workbench_excerpt()
  with patch('ai.workbench_spec.parse_diagnosed',side_effect=AssertionError('No API')):other.import_diagnostic(raw)
  self.assertTrue(other.workbench['historical']);self.assertIsNone(other.workbench['active']);self.assertIsNone(other.workbench['draft']);self.assertEqual(other.diagnostic_analysis()['status'],'validated')

 def test_repaired_issue_form_retains_actual_source(self):
  from streamlit.testing.v1 import AppTest
  self.s.load_synthetic_diagnostic();issue=json.loads(self.s.diagnostic_store()['current']['content'])['front']['issues'][0];issue.update(fields=[],location='TXT:L14');self.s.repair_diagnostic('front.issues.0','issue',issue,'核对后不规定页脚距，仅记录说明')
  app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);app.session_state['workflow']=self.s;app.run();next(x for x in app.selectbox if x.label=='待核对提示').set_value('front.issues.0');app.run();self.assertFalse(app.exception)
  self.assertEqual(next(x for x in app.selectbox if x.label=='提示来源位置').value,'TXT:L14');self.assertEqual(next(x for x in app.selectbox if x.label=='提示原因').value,'unsupported')

 def test_default_after_adoption_can_save_project(self):
  self.s.receive_diagnostic(rec());self.s.use_diagnostic_draft(acknowledged=True);self.s.workbench_policy('keep',acknowledged=True);self.s.apply_workbench(acknowledged=True);self.s.use_default_rules();self.s.prepare_project();self.assertTrue(self.s.project_download());self.assertIsNone(self.s.diagnostic_store()['adopted_sha256'])
 def test_rule_import_moves_old_diagnosis_to_history(self):
  self.s.receive_diagnostic(rec());before=self.s.rule_bundle_download();self.s.import_rule_bundle(before);self.assertIsNone(self.s.diagnostic_store()['current']);self.assertEqual(len(self.s.diagnostic_store()['history']),1)
 def test_network_failure_keeps_snapshot_and_reason(self):
  from urllib.error import HTTPError
  def fail(*a):raise HTTPError('https://api.deepseek.com',402,'no secret',{},None)
  r=parse_diagnosed(SEGMENTS,config=Settings('test-key'),transport=fail);self.assertEqual(r['segments'],SEGMENTS);self.assertIsNone(r['content']);self.assertEqual(r['receipt']['request_count'],1);a=sd.diagnose(r);self.assertEqual(a['status'],'rejected');self.assertIn('余额',a['reason'])

 def test_note_bulk_selection_under_active_workbench_uses_inventory(self):
  from streamlit.testing.v1 import AppTest
  self.s.receive_diagnostic(rec());self.s.use_diagnostic_draft(acknowledged=True);self.s.workbench_policy('keep',acknowledged=True);self.s.apply_workbench(acknowledged=True);self.s.enable_notes(True)
  app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);app.session_state['workflow']=self.s;app.run();next(x for x in app.button if x.label=='选择当前筛选的注释').click();app.run();self.assertFalse(app.exception);self.assertEqual(len(self.s.note_draft['objects']),6);self.assertIsNone(self.s.error)

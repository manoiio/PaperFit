"""One start authorization over old legal transactions, all network mocked."""
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from web.session import WebSession
from web.onepass_session import start,continue_command,cancel,current,overlay
from web.structure_session import run
from ai.short_spec import Settings
from core.package import DemoError
ROOT=Path(__file__).resolve().parents[1]

class OnePassAcceptance(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  for target in ('ai.structure.http_post','ai.short_spec.http_post'):
   guard=patch(target,side_effect=AssertionError('Automatic tests must never use real API'));guard.start();self.addCleanup(guard.stop)
 def session(self,name='s',fixture='samples/phase41/structure.docx'):
  s=WebSession(self.root/name);s.set_mode('academic');self.assertTrue(s.load((ROOT/fixture).read_bytes(),'合成.docx'));s.set_table_enabled(False);s.enable_notes(False);return s
 def runner(self,m,p,store):
  labels=json.loads((ROOT/'samples/phase41/labels.json').read_text())['paragraphs']
  rows=[{'id':c['id'],'role':'heading3' if c['id']=='p:13' else labels[int(c['id'][2:])-1]['role'],'evidence':c['text'],'reason':'模拟结构证据'} for c in p['request']['candidates']]
  if p['request']['version']=='structure-v3-context':
   for row,c in zip(rows,p['request']['candidates']):
    row['evidence_location']=c['fragments'][0]['id'] if c.get('kind')=='table' else 'text';row['evidence']=c['fragments'][0]['text'] if c.get('kind')=='table' else c['text']
  return run(m,p,store,transport=lambda *_:json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'suggestions':rows})}}]}),config=Settings('synthetic-placeholder'))
 def parser(self,text):return {'draft':{'font_size':{'value':14,'quote':'正文改为四号'},'line_spacing':{'value':2,'quote':'正文改为四号、2倍行距'},'unsupported':[]},'receipt':{'kind':'mock_api','model':'deepseek-flash','timestamp_utc':'2026-10-17T00:00:00+00:00','request_count':1}}
 def test_no_candidate_three_actions_idempotent_and_old_bytes(self):
  s=self.session(fixture='samples/phase31/errors.docx');st={}
  with patch('web.onepass_session.structure.run',side_effect=AssertionError('no candidate no request')):
   start(s,st);self.assertEqual(st['status'],'done',st.get('error'));self.assertEqual(len(s.history),1)
   data=s.downloads()['fixed.docx'];start(s,st);self.assertEqual(len(s.history),1)
  ref=self.session('reference','samples/phase31/errors.docx');ref.set_types(s.paragraph_types);ref.confirm_and_check();ref.set_selection(s.selected);self.assertTrue(ref.generate(),ref.error);self.assertEqual(data,ref.downloads()['fixed.docx'])
  self.assertIn('一站式开始命令授权',s.classification_confirmed['confirmation']);self.assertEqual(s.current_round,0)
 def test_one_exception_and_resume_without_call_again(self):
  s=self.session();st={};calls=[]
  def runner(*args):calls.append(1);return self.runner(*args)
  start(s,st,structure_runner=runner);self.assertEqual(st['status'],'waiting');self.assertIsNone(s.confirmed);self.assertFalse(s.history);self.assertEqual([q['paragraph'] for q in st['questions']],['13'])
  self.assertNotEqual(st['proposal']['draft']['paragraph_types']['13'],'heading3')
  start(s,st,structure_runner=runner);self.assertEqual(calls,[1])
  continue_command(s,st,'',{'paragraph:13':'heading2'});self.assertEqual(st['status'],'done',st.get('error'));self.assertEqual(calls,[1]);self.assertEqual(s.paragraph_types['13'],'heading2')
  ref=self.session('reference');ref.set_types(s.paragraph_types);ref.confirm_and_check();ref.set_selection(s.selected);self.assertTrue(ref.generate());self.assertEqual(s.downloads()['fixed.docx'],ref.downloads()['fixed.docx'])
 def test_missing_decision_tampering_changed_text_and_cancel(self):
  s=self.session();st={};start(s,st,structure_runner=self.runner)
  with self.assertRaises(DemoError):continue_command(s,st,'',{})
  with self.assertRaises(DemoError):continue_command(s,st,'new',{'paragraph:13':'heading2'})
  st['questions'][0]['text']='tampered'
  with self.assertRaises(DemoError):continue_command(s,st,'',{'paragraph:13':'heading2'})
  cancel(s,st);self.assertFalse(s.history);self.assertIsNone(s.report)
 def test_requirements_supported_only_touched_fields_and_source(self):
  s=self.session(fixture='samples/phase31/errors.docx');prior=s.current_rule_bundle();st={};text='在SCUT要求基础上，正文改为四号、2倍行距'
  start(s,st,text,spec_parser=self.parser);self.assertEqual(st['status'],'done',st.get('error'));b=s.current_rule_bundle()
  from core.rule_bundle import flat
  self.assertEqual(flat('main',b['modules']['main'])['font_size'],14)
  self.assertEqual(flat('main',b['modules']['main'])['line_spacing'],2)
  for n,source in prior['provenance']['main'].items():
   if n not in ('font_size','line_spacing'):self.assertEqual(source,b['provenance']['main'][n],n)
  self.assertEqual(b['provenance']['main']['font_size']['kind'],'ai_extracted')
  self.assertEqual(st['audit']['API']['requirements']['receipt']['request_count'],1)
 def test_unsupported_and_failed_requirements_never_ignored(self):
  for text,parser in [('正文改为四号，页边距20mm',lambda t:self.fail('local refusal must not send')),('正文改为四号、2倍行距',lambda t:(_ for _ in ()).throw(TimeoutError()))]:
   s=self.session(str(len(text)),fixture='samples/phase31/errors.docx');old=s.rules_hash;st={};start(s,st,text,spec_parser=parser)
   self.assertEqual(st['status'],'waiting');self.assertFalse(s.history);self.assertEqual(old,s.rules_hash)
   continue_command(s,st,text,{'requirements':'template'});self.assertEqual(st['status'],'done',st.get('error'));self.assertEqual(old,s.rules_hash)
 def test_failed_structure_local_fallback_and_atomic_archive_failure(self):
  s=self.session();st={};start(s,st,structure_runner=lambda *_:(_ for _ in ()).throw(DemoError('模拟无配置')))
  self.assertEqual(st['status'],'done',st.get('error'));self.assertIn('structure_fallback',st['audit'])
  b=self.session('b',fixture='samples/phase31/errors.docx');old=deepcopy(b._scope_snapshot());state={}
  with patch.object(WebSession,'_archive_round',side_effect=OSError('synthetic storage failure')):start(b,state)
  self.assertEqual(state['status'],'failed');self.assertFalse(b.history);self.assertIsNone(b.confirmed);self.assertIsNone(b.report);self.assertEqual(b._scope_snapshot(),old)
 def test_rule_or_file_changes_during_execution_do_not_publish(self):
  for name,change in [('rules',lambda s:setattr(s,'rules_hash','stale')),('file',lambda s:s.input_path.write_bytes(b'changed'))]:
   s=self.session(name,fixture='samples/phase31/errors.docx');st={}
   def emit(label):
    if label=='调整格式':change(s)
   start(s,st,emit=emit);self.assertEqual(st['status'],'failed');self.assertFalse(s.history);self.assertIsNone(s.result)
 def test_inflight_duplicate_and_cancel_cannot_publish(self):
  s=self.session();st={};count=[]
  def runner(*args):
   count.append(1);start(s,st,structure_runner=lambda *_:self.fail('duplicate POST'));cancel(s,st);return self.runner(*args)
  start(s,st,structure_runner=runner);self.assertEqual(count,[1]);self.assertEqual(st['status'],'cancelled');self.assertFalse(s.history);self.assertIsNone(s.result)
 def test_protected_drafts_keep_partial_and_project_no_authorization(self):
  a=self.session();a.exclude_materials([13],'用户保护材料');a.batch_types([9],'heading2');st={};start(a,st,structure_runner=self.runner)
  self.assertEqual(st['status'],'done',st.get('error'));self.assertEqual(a.paragraph_types['13'],'other');self.assertEqual(a.paragraph_types['9'],'heading2')
  self.assertFalse(any(x.get('complete') for x in (a.classification_confirmed or {}).values() if isinstance(x,dict)))
  b=self.session('b');b.stage_project(a.prepare_project());restored=b.restore_project(acknowledged=True)
  self.assertIsNone(restored.result);self.assertIsNone(restored.rehearsal);self.assertFalse(hasattr(restored,'onepass'));self.assertEqual(restored.paragraph_types['13'],'other')

 def test_existing_legal_two_step_and_direct_conflict_guard_retained(self):
  from scripts.reproduce_plan_demo import session
  from core import fix_document
  s=session(self.root/'plan');s.set_table_enabled(False);s.enable_notes(False);before=deepcopy(s.classification_confirmed);selected=s.selected.copy()
  with self.assertRaises(DemoError):fix_document(s.input_path,self.root/'illegal.docx',s.confirmed,selected_keys=selected,**s._rules_arguments())
  st={};start(s,st);self.assertEqual(st['status'],'done',st.get('error'));self.assertEqual(st['outcome']['rounds'],2);self.assertEqual(s.generation_count,2);self.assertEqual(s.current_round,0)

 def test_ambiguous_short_title_not_silently_downgraded_to_body(self):
  s=self.session();st={}
  def runner(*args):
   result=self.runner(*args)
   for r in result['suggestions']:
    if r['id']=='p:13':r['role']='body'
   return result
  start(s,st,structure_runner=runner);self.assertEqual(st['status'],'waiting');self.assertEqual(st['questions'][0]['paragraph'],'13');self.assertFalse(s.history)

 def test_existing_basic_explicit_body_is_never_expanded(self):
  s=WebSession(self.root/'basic');s.load((ROOT/'samples/errors.docx').read_bytes(),'合成.docx');s.set_body([4]);st={}
  with patch('web.onepass_session.structure.run',side_effect=AssertionError('explicit scope never sent')):start(s,st)
  self.assertEqual(st['status'],'done',st.get('error'));self.assertEqual(s.body,[4]);self.assertEqual(s.confirmed['body_paragraphs'],[4]);self.assertEqual(s.mode,'basic')

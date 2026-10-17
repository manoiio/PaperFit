"""Automatic scope preparation uses original engines; HTTP strictly blocked in tests."""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
import json,zipfile
from lxml import etree as E
from web.session import WebSession
from web.structure_session import prepare,run,merge
from web.onepass_session import start,continue_command
from ai.structure import validate
from ai.short_spec import Settings
from core.package import DemoError,NS,q
ROOT=Path(__file__).resolve().parents[1]

class AutoRangeAcceptance(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  for target in ('ai.structure.http_post','ai.short_spec.http_post'):
   guard=patch(target,side_effect=AssertionError('No paid network in tests'));guard.start();self.addCleanup(guard.stop)
 def session(self,n='a'):
  s=WebSession(self.root/n);s.set_mode('academic');self.assertTrue(s.load((ROOT/'samples/phase43/errors.docx').read_bytes(),'合成.docx'));return s
 def runner(self,s,p,store):
  rows=[{'id':c['id'],'role':'content' if c.get('kind')=='table' else 'body','evidence':c['text'],'reason':'作者预先标注的模拟响应'} for c in p['request']['candidates']]
  if p['request']['version']=='structure-v3-context':
   for row,c in zip(rows,p['request']['candidates']):
    row['evidence_location']=c['fragments'][0]['id'] if c.get('kind')=='table' else 'text';row['evidence']=c['fragments'][0]['text'] if c.get('kind')=='table' else c['text']
  return run(s,p,store,transport=lambda *_:json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'version':'structure-ids-v1','suggestions':[{k:(r['evidence_location'] if k=='evidence' else r[k]) for k in ('id','role','evidence','reason')} for r in rows]} if p['request']['version']=='structure-v3-context' else {'suggestions':rows})}}]}),config=Settings('synthetic-placeholder'))
 def test_combined_budget_exact_ids_and_private_complex_not_sent(self):
  s=self.session();p=prepare(s,include_tables=True);self.assertEqual({c['id'] for c in p['request']['candidates']},{'p:2','t:2'})
  self.assertNotIn('20260001234',json.dumps(p['request']));self.assertEqual(p['auto_ranges']['tables'],{'1':'cover','2':'pending','3':'pending'});self.assertEqual(p['auto_ranges']['note_counts'],{'footnote':3,'endnote':3})
  raw={'suggestions':[{'id':'t:2','role':'body','evidence':'方案','reason':'wrong type'}]}
  with self.assertRaises(DemoError):validate(raw,p['request'])
  raw['suggestions'][0].update(role='content',evidence='invented',evidence_location='r1:c1');self.assertFalse(validate(raw,p['request'])[0]['accepted'])
 def test_new_scopes_original_confirmation_recheck_and_independent_parts(self):
  s=self.session();state={};start(s,state,structure_runner=self.runner);self.assertEqual(state['status'],'done',state.get('error'));self.assertTrue(s.table_enabled);self.assertTrue(s.note_enabled)
  self.assertEqual(s.table_types,{'1':'cover','2':'content','3':'pending'});self.assertEqual(len(s.note_draft['objects']),6);self.assertIn('一站式开始命令授权',s.note_draft['confirmation']);self.assertIn('一站式开始命令授权',s.table_confirmed['scope']['confirmation'])
  for rid in ('R23','R36','R37'):self.assertTrue(any(c['rule_id']==rid for c in s.result['changes']),rid)
  ref=self.session('legal');ref.set_types(s.paragraph_types);ref.set_table_enabled(True);ref.set_table_types(s.table_types);ref.enable_notes(True);ref.edit_notes(s.note_draft);ref.confirm_tables();ref.confirm_notes()
  self.assertTrue(ref.confirm_and_check(),ref.error);ref.set_selection(s.selected);self.assertTrue(ref.generate(),ref.error);self.assertEqual(s.downloads()['fixed.docx'],ref.downloads()['fixed.docx'])
  with zipfile.ZipFile(s.input_path) as z:a={n:z.read(n) for n in z.namelist()}
  with zipfile.ZipFile(Path(s.result['output'])) as z:b={n:z.read(n) for n in z.namelist()}
  for n in a:
   if n not in ('word/document.xml','word/footnotes.xml','word/endnotes.xml'):self.assertEqual(a[n],b[n],n)
  ap=E.fromstring(a['word/document.xml']);bp=E.fromstring(b['word/document.xml'])
  for n in (0,2):self.assertEqual(E.tostring(ap.find(q('body')).findall(q('tbl'))[n],method='c14n'),E.tostring(bp.find(q('body')).findall(q('tbl'))[n],method='c14n'))
  for part in ('word/document.xml','word/footnotes.xml','word/endnotes.xml'):
   x,y=E.fromstring(a[part]),E.fromstring(b[part]);self.assertEqual(x.xpath('//w:t/text()',namespaces=NS),y.xpath('//w:t/text()',namespaces=NS))
  old=s.generation_count;start(s,state,structure_runner=lambda *_:self.fail('duplicate call'));self.assertEqual(old,s.generation_count)
 def test_failure_question_once_then_resume_without_request(self):
  s=self.session();state={};calls=[]
  def fail(*args):calls.append(1);raise DemoError('模拟失败')
  start(s,state,structure_runner=fail);self.assertEqual(state['status'],'waiting');self.assertEqual([q['id'] for q in state['questions']],['table:2']);self.assertFalse(s.history)
  continue_command(s,state,'',{'table:2':'content'});self.assertEqual(state['status'],'done',state.get('error'));self.assertEqual(calls,[1])
 def test_explicit_off_partial_and_restored_unknown_never_expand(self):
  for n in ('off','partial','restored','legacy'):
   s=self.session(n)
   if n=='off':s.set_table_enabled(False);s.enable_notes(False)
   if n=='partial':s.set_table_enabled(True);s.set_table_types({'1':'cover','2':'other','3':'pending'});s.enable_notes(True)
   if n=='legacy':del s.table_explicit_choice;del s.note_explicit_choice
   if n=='restored':s.project_notice='旧项目恢复；没有明确新任务意图'
   p=prepare(s,include_tables=True);self.assertFalse(any(c.get('kind')=='table' for c in p['request']['candidates']));self.assertIsNone(p['auto_ranges']['notes'])
 def test_missing_rules_not_filled_and_original_drafts_untouched(self):
  s=self.session();s.import_rule_bundle(json.dumps(s.current_rule_bundle(),ensure_ascii=False).encode());s.apply_workbench(acknowledged=True)
  before=deepcopy(s._scope_snapshot());p=prepare(s,include_tables=True);self.assertEqual(before,s._scope_snapshot());self.assertIsNone(p['auto_ranges']['notes'])
 def test_inflight_off_or_cross_session_response_rejected(self):
  s=self.session();p=prepare(s,include_tables=True);s.set_table_enabled(False)
  with self.assertRaises(DemoError):self.runner(s,p,{})
  a=self.session('a2');p=prepare(a,include_tables=True);result=self.runner(a,p,{})
  with self.assertRaises(DemoError):merge(self.session('b'),p,result)

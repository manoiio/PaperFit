"""Shortcut uses original permissions/transactions; no relaxed execution tests."""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import json,unittest
from unittest.mock import patch
from web.session import WebSession
from web.smart_session import suggest,accept_scope,shortcut_plan,execute,binding
from core.package import DemoError,Package,NS
ROOT=Path(__file__).resolve().parents[1]

class SmartAcceptance(unittest.TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def session(self,name='s',mode='basic'):
  s=WebSession(self.root/name);s.set_mode(mode);self.assertTrue(s.load((ROOT/'samples/errors.docx').read_bytes(),'合成.docx'));return s
 def test_suggestion_read_only_partial_and_material_protection(self):
  s=self.session(mode='academic');s.exclude_materials([4],'人工保护合成数据');before=deepcopy(s._scope_snapshot());p=suggest(s)
  self.assertEqual(s._scope_snapshot(),before);self.assertIsNone(s.confirmed);self.assertIsNone(s.report)
  self.assertEqual(p['draft']['paragraph_types']['4'],'other');self.assertEqual(p['preflight']['areas'][0]['excluded'],1)
  for r in s.suggestions['paragraphs']:
   if r['ambiguous'] and str(r['index']) not in s.material_exclusions:self.assertIn(p['draft']['paragraph_types'][str(r['index'])],('other','pending'))
  self.assertFalse(any(getattr(s,a+'_enabled') for a in ('table','toc','citation','caption','note')))
 def test_original_path_bytes_and_idempotent_zero_refix_adoption(self):
  a=self.session('a');b=self.session('b');plan=accept_scope(a,suggest(a));accept_scope(b,suggest(b))
  self.assertEqual(a.confirmed,b.confirmed);self.assertEqual(a.report['findings'],b.report['findings']);b.set_selection(plan['keys']);self.assertTrue(b.generate(),b.error)
  from web import session as api
  original=api.fix_document
  with patch.object(api,'fix_document',wraps=original) as engine:
   state={};result=execute(a,plan,state);self.assertEqual(engine.call_count,1);self.assertEqual(a.generation_count,1)
   self.assertEqual(execute(a,plan,state),result);self.assertEqual(engine.call_count,1)
  self.assertEqual(a.downloads()['fixed.docx'],b.downloads()['fixed.docx']);self.assertEqual(a.current_round,0)
 def test_snapshot_and_forged_plan_rejected(self):
  s=self.session();p=suggest(s);s.set_body([4])
  with self.assertRaises(DemoError):accept_scope(s,p)
  plan=accept_scope(s,suggest(s));plan['keys']=[]
  with self.assertRaises(DemoError):execute(s,plan,{})
  self.assertEqual(s.generation_count,0)
 def test_failed_scope_and_archive_publish_nothing(self):
  s=self.session();p=suggest(s)
  with patch.object(WebSession,'check',return_value=False):
   with self.assertRaises(DemoError):accept_scope(s,p)
  self.assertIsNone(s.confirmed);self.assertIsNone(s.report)
  plan=accept_scope(s,suggest(s))
  with patch.object(WebSession,'_archive_round',side_effect=OSError('synthetic storage error')):
   with self.assertRaises(DemoError):execute(s,plan,{})
  self.assertFalse(s.history);self.assertEqual(s.generation_count,0);self.assertIsNone(s.result)
 def test_known_two_step_still_uses_original_guard(self):
  from scripts.reproduce_plan_demo import session as prepare
  s=prepare(self.root/'plan')
  # Original fixture helper returns a checked session and explicit selections.
  plan=shortcut_plan(s);self.assertTrue(plan['plan']['two_steps']);self.assertFalse(plan['plan']['blocked'])
  selected=plan['keys'];from core import fix_document
  with self.assertRaises(DemoError):fix_document(s.input_path,self.root/'illegal.docx',s.confirmed,selected_keys=selected,**s._rules_arguments())
  result=execute(s,plan,{});self.assertEqual(result['rounds'],2);self.assertEqual(s.generation_count,2)
 def test_restore_no_shortcut_authority_and_sessions_isolated(self):
  a=self.session('a');b=self.session('b');p=suggest(a);plan=accept_scope(a,p);execute(a,plan,{})
  self.assertIsNone(b.confirmed);self.assertIsNone(b.result)
  b.stage_project(a.prepare_project());new=b.restore_project(acknowledged=True)
  self.assertFalse(hasattr(new,'smart_authorization'));self.assertIsNone(new.rehearsal);self.assertIsNone(new.result)
  self.assertEqual(new.report['findings'],a.report['findings'])
 def test_no_work_means_no_round(self):
  s=WebSession(self.root/'good');s.load((ROOT/'samples/correct.docx').read_bytes(),'correct.docx',json.loads((ROOT/'samples/correct.body.json').read_text()))
  p=accept_scope(s,suggest(s));self.assertFalse(p['keys']);self.assertEqual(execute(s,p,{})['status'],'no_changes');self.assertEqual(s.generation_count,0)

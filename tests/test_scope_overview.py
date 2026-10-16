from tests.ui_navigation import show, click as ui_click
"""Portable behavioural tests: no local history outputs, API, Word or renderer."""
import json,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from scripts.reproduce_scope_demo import session,old_check,ROOT
from core.package import DemoError,Package,NS,sha256
from web.session import WebSession
from web.scope_session import report_scope_summary

class ScopeOverviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=session(Path(self.tmp.name)/'a')
 def commit(self,s=None):
  s=s or self.s;p=s.scope_preflight();self.assertTrue(p['ready'],p['blockers']);self.assertTrue(s.confirm_scopes_and_check(p['signature'],acknowledged=True),s.error);return p
 def test_overview_matches_real_drafts_and_inventories(self):
  p=self.s.scope_preflight();a={r['area']:r for r in p['areas']}
  self.assertEqual([a[k]['detected'] for k in ('paragraph','table','note','caption','citation')],[19,1,6,2,1]);self.assertEqual(a['note']['selected'],6)
  self.assertEqual(a['paragraph']['excluded'],1);self.assertEqual(a['paragraph']['details']['protected_paragraphs'],['13']);self.assertEqual(a['caption']['details']['associations'],self.s.caption_draft['associations'])
  self.assertTrue(all(r['enabled'] and not r['confirmed'] for r in p['areas'] if r['area']!='reference'));self.commit();self.assertTrue(all(r['confirmed'] for r in self.s.scope_preflight()['areas'] if r['enabled']));self.assertFalse(a['reference']['enabled']);self.assertFalse(a['reference']['confirmed'])
 def test_preflight_no_side_effects_or_implicit_actions(self):
  self.commit();self.s.set_selection([self.s.eligible()[0]['key']]);before=deepcopy(self.s.__dict__);files={str(p):p.read_bytes() for p in self.s.task_dir.rglob('*') if p.is_file()}
  with patch.object(self.s,'_current',side_effect=AssertionError('mutating _current')),patch.object(self.s,'check',side_effect=AssertionError('check')),patch.object(self.s,'invalidate',side_effect=AssertionError('invalidate')),patch.object(self.s,'sync_rules',side_effect=AssertionError('sync')):
   a=self.s.scope_preflight();b=self.s.scope_preflight();self.assertEqual(a,b)
   a['limits'].append('caller edit');next(r for r in a['areas'] if r['area']=='toc')['declarations']['covered_levels'].append(99);next(r for r in a['areas'] if r['area']=='citation')['details']['scan_paragraphs'].append(1)
  self.assertEqual(before,self.s.__dict__);self.assertEqual(files,{str(p):p.read_bytes() for p in self.s.task_dir.rglob('*') if p.is_file()})
 def test_multiple_independent_invalid_areas_reported_together(self):
  self.s.note_draft['objects']=['missing'];self.s.front_draft['section_roles']={'999':'mixed'};self.s.toc_draft['objects']={'d:999':'title'}
  p=self.s.scope_preflight();self.assertFalse(p['ready']);self.assertTrue({'note','front','toc'}<={r['area'] for r in p['blockers']});self.assertIsNone(self.s.confirmed)
 def test_cross_scope_conflicts_and_citation_scan_detected(self):
  self.s.paragraph_types['3']='body';self.s.citation_draft['scan']=[15];self.s.caption_draft['chapter_map']={'15':1}
  p=self.s.scope_preflight();why='\n'.join(r['reason'] for r in p['blockers']);self.assertIn('目录范围与正文',why);self.assertIn('引文只能扫描',why);self.assertIn('题注/章节',why)
 def test_atomic_invalid_scope_does_not_publish(self):
  self.s.note_draft['objects']=['missing'];old=deepcopy(self.s.__dict__)
  with self.assertRaises(DemoError):self.s.confirm_scopes_and_check(self.s.scope_preflight()['signature'],acknowledged=True)
  self.assertEqual(old,self.s.__dict__)
 def test_atomic_storage_failure_no_partial_confirmations(self):
  p=self.s.scope_preflight();old=deepcopy(self.s.__dict__)
  with patch('web.scope_session.write_new',side_effect=OSError('disk full')),self.assertRaises(OSError):self.s.confirm_scopes_and_check(p['signature'],acknowledged=True)
  self.assertEqual(old,self.s.__dict__)
 def test_storage_race_draft_change_rejected_and_temp_record_removed(self):
  from web.scope_session import write_new
  p=self.s.scope_preflight();before=set(self.s.task_dir.iterdir())
  def race(*args,**kwargs):
   path=write_new(*args,**kwargs);self.s.note_draft['objects']=[];return path
  with patch('web.scope_session.write_new',side_effect=race),self.assertRaises(DemoError):self.s.confirm_scopes_and_check(p['signature'],acknowledged=True)
  self.assertIsNone(self.s.front_confirmed);self.assertIsNone(self.s.confirmed);self.assertEqual(before,set(self.s.task_dir.iterdir()))
 def test_requires_ack_and_fresh_draft_signature(self):
  p=self.s.scope_preflight()
  with self.assertRaises(DemoError):self.s.confirm_scopes_and_check(p['signature'])
  self.s.caption_draft['complete']=True
  with self.assertRaises(DemoError):self.s.confirm_scopes_and_check(p['signature'],acknowledged=True)
  self.assertIsNone(self.s.confirmed)
 def test_external_input_change_rejected_without_preflight_mutation(self):
  p=self.s.scope_preflight();self.s.input_path.write_bytes((ROOT/'samples/correct.docx').read_bytes());old=deepcopy(self.s.__dict__)
  self.assertFalse(self.s.scope_preflight()['ready']);self.assertEqual(old,self.s.__dict__)
  with self.assertRaises(DemoError):self.s.confirm_scopes_and_check(p['signature'],acknowledged=True)
 def test_rule_file_change_or_mode_change_invalidates_summary(self):
  p=self.s.scope_preflight();rp=Path(self.tmp.name)/'rules.json';rp.write_bytes(self.s.rules_path.read_bytes()+b' ');self.s.rules_path=rp
  self.assertFalse(self.s.scope_preflight()['ready'])
  with self.assertRaises(DemoError):self.s.confirm_scopes_and_check(p['signature'],acknowledged=True)
  self.s.rules_path=ROOT/'rules/scut_2015_demo.json';self.s.set_mode('extended')
  with self.assertRaises(DemoError):self.s.confirm_scopes_and_check(p['signature'],acknowledged=True)
 def test_partial_flags_not_auto_complete_and_no_suggestions_accepted(self):
  p=self.s.scope_preflight();before=deepcopy(self.s.paragraph_types);self.commit()
  self.assertEqual(before,self.s.paragraph_types)
  for d,keys in [(self.s.toc_draft,['complete','headings_complete']),(self.s.caption_draft,['complete','chapters_complete']),(self.s.citation_draft,['complete','references_complete'])]:
   self.assertTrue(all(d[k] is False for k in keys))
  self.assertNotIn('d:20',self.s.toc_draft['objects']);self.assertTrue(any(w['code']=='partial_scope' for w in p['warnings']))
 def test_old_and_unified_range_and_check_equivalent(self):
  old=session(Path(self.tmp.name)/'old');old_check(old);self.commit()
  self.assertEqual(old.classification_confirmed,self.s.classification_confirmed)
  for k in ('findings','coverage','coverage_notes','summary'):self.assertEqual(old.report[k],self.s.report[k])
  keys=[self.s.eligible()[0]['key']]
  for s in (old,self.s):s.set_selection(keys);self.assertTrue(s.generate(),s.error)
  self.assertEqual(old.downloads()['fixed.docx'],self.s.downloads()['fixed.docx'])
 def test_disabled_unconfigured_pending_and_complex_distinct(self):
  self.s.enable_notes(False);self.s.toc_draft['template']['values']={k:None for k in self.s.toc_draft['template']['values']}
  for k in self.s.toc_draft['template']['sources']:self.s.toc_draft['template']['sources'][k]={'kind':'not_enabled','quote':'','location':None}
  p=self.s.scope_preflight();r={x['area']:x for x in p['areas']};self.assertEqual(r['note']['status'],'未启用');self.assertFalse(r['toc']['configured']);self.assertEqual(r['toc']['status'],'格式未配置');self.assertGreater(r['toc']['details']['automatic'],0)
 def test_material_protection_preserved_by_batch_and_confirmation(self):
  self.s.batch_types([13],'body');self.assertEqual(self.s.paragraph_types['13'],'other');self.commit();self.assertIn('13',self.s.classification_confirmed['material_exclusions'])
 def test_new_draft_conservatively_invalidates_and_overview_honest(self):
  self.commit();d=deepcopy(self.s.note_draft);d['objects']=d['objects'][:1];self.s.edit_notes(d)
  self.assertIsNone(self.s.report);p=self.s.scope_preflight();self.assertFalse(any(r['confirmed'] for r in p['areas']));self.assertEqual(self.s.material_exclusions.keys(),{'13'})
 def test_project_restores_drafts_and_recomputes_summary_without_authorization(self):
  p=self.s.scope_preflight();raw=self.s.prepare_project();t=WebSession(Path(self.tmp.name)/'restore');t.stage_project(raw);r=t.restore_project(acknowledged=True)
  self.assertIsNone(r.report);self.assertEqual(r.scope_preflight()['summary']['selected_areas'],p['summary']['selected_areas']);self.assertEqual(r.material_exclusions,self.s.material_exclusions);self.assertEqual(r.note_draft,self.s.note_draft);self.commit(r)
  self.assertIsNotNone(r.report)
 def test_two_sessions_do_not_share_drafts_confirmations_or_results(self):
  t=session(Path(self.tmp.name)/'other');p=t.scope_preflight()
  with self.assertRaises(DemoError):self.s.confirm_scopes_and_check(p['signature'],acknowledged=True)
  self.commit();self.assertIsNone(t.confirmed);self.assertIsNone(t.report);self.assertEqual(p,t.scope_preflight())
 def test_report_summary_is_actual_bound_snapshot_not_latest_draft(self):
  self.commit();r=self.s.report;manifest=deepcopy(self.s.classification_confirmed);summary=report_scope_summary(r,manifest);self.s.note_draft['objects']=[]
  self.assertEqual(summary,report_scope_summary(r,manifest));self.assertEqual(next(x['selected'] for x in summary['areas'] if x['area']=='note'),6)
 def test_report_formats_and_package_include_same_scope_summary(self):
  self.commit();self.s.set_selection([self.s.eligible()[0]['key']]);self.assertTrue(self.s.generate(),self.s.error)
  from io import BytesIO
  import zipfile
  data=self.s.prepare_reading_export();d=json.loads(data['report.json']);self.assertIn('scope_summary',d);self.assertIn('本轮实际范围',data['report.html'].decode());self.assertIn('范围状态摘要',data['report.md'].decode())
  with zipfile.ZipFile(BytesIO(self.s.result_package())) as z:self.assertEqual(json.loads(z.read('scope-summary.json')),d['scope_summary'])
 def test_basic_and_extended_modes_keep_original_meanings(self):
  for mode in ('basic','extended'):
   s=WebSession(Path(self.tmp.name)/mode);s.set_mode(mode);s.load((ROOT/'samples/correct.docx').read_bytes(),'a.docx')
   if mode=='basic':s.set_body([4,5,6,7,8,9])
   p=s.scope_preflight();self.assertTrue(p['ready'],p['blockers']);self.assertTrue(s.confirm_scopes_and_check(p['signature'],acknowledged=True),s.error)
   self.assertEqual(s.report['summary']['rule_count'],7 if mode=='basic' else 12)
 def test_l05_mapped_ranges_follow_output_and_not_old_paragraph_ids(self):
  from tests.test_captions import manifest,BAD
  s=WebSession(Path(self.tmp.name)/'move');s.set_mode('academic');s.load(BAD.read_bytes(),'移动演示.docx');m=manifest();s.set_types(m['paragraph_types']);s.adopt_caption_scope(m['caption_scope'],confirmed=False)
  self.commit(s);self.assertTrue(s.generate_caption_move(['L05:5:image:p:6']),s.error)
  self.assertTrue(s.next_round(),s.error);p=s.scope_preflight();self.assertTrue(p['ready'],p['blockers']);self.assertTrue(all(r['confirmed'] for r in p['areas'] if r['enabled']));self.assertEqual(s.caption_draft['input_sha256'],s.inventory['input_sha256']);self.assertIn('6',s.caption_draft['captions']);self.assertNotEqual(s.inventory['input_sha256'],m['input_sha256'])
 def test_missing_enabled_draft_blocks_but_does_not_prepare_or_overwrite(self):
  self.s.note_draft=None;p=self.s.scope_preflight();self.assertFalse(p['ready']);self.assertTrue(any(x['area']=='note' for x in p['blockers']));self.assertIsNone(self.s.note_draft)
 def test_unchecked_object_not_claimed_actively_excluded(self):
  self.s.note_draft['objects']=[];r=next(x for x in self.s.scope_preflight()['areas'] if x['area']=='note');self.assertEqual(r['excluded'],0);self.assertEqual(r['pending'],6)
 def test_streamlit_ack_reset_after_draft_change_and_preflight_does_not_check(self):
  from streamlit.testing.v1 import AppTest
  app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=25);app.session_state['workflow']=self.s;app.run();self.assertFalse(app.exception)
  label='我已核对以上所有已启用区域的完整草稿、主动排除和部分范围声明；确认这些范围用于本轮检查'
  next(x for x in app.checkbox if x.label==label).check();app.run();self.assertIsNone(self.s.report)
  d=deepcopy(self.s.note_draft);d['objects']=[];self.s.edit_notes(d);app.run();self.assertFalse(next(x for x in app.checkbox if x.label==label).value)
  self.assertTrue(next(x for x in app.button if x.label=='确认这些范围并开始检查').disabled)
 def test_streamlit_confirm_uses_actual_scope_and_original_engine(self):
  from streamlit.testing.v1 import AppTest
  app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=25);app.session_state['workflow']=self.s;app.run()
  next(x for x in app.checkbox if x.label.startswith('我已核对以上所有已启用区域')).check();app.run()
  next(x for x in app.button if x.label=='确认这些范围并开始检查').click();app.run();self.assertFalse(app.exception);self.assertIsNotNone(self.s.report);self.assertIsNone(self.s.result)
  self.assertEqual(self.s.report['coverage']['note_scope']['objects'],self.s.note_draft['objects'])
if __name__=='__main__':unittest.main()

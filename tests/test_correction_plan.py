"""Known two-step dependency with independent XML/ZIP proof and failure injection."""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest import TestCase,mock
from io import BytesIO
import zipfile,json
from core.package import Package,DemoError,sha256,q,NS
from core import fix_document,check_document
from core.correction_plan import resolve_targets,handoff
from web.session import WebSession
from scripts.reproduce_plan_demo import session,selection,SAMPLE,ROOT
from scripts.verify_plan_output import verify
class PlanTests(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name);self.s=session(self.d/'web');self.s.set_selection(selection(self.s))
 def preview(self,s=None):
  s=s or self.s;self.assertTrue(s.rehearse_plan(),s.rehearsal_error);return s.rehearsal['id']
 def adopt(self,s=None):
  s=s or self.s;self.assertTrue(s.adopt_plan(s.rehearsal['id'],acknowledged=True),s.rehearsal_error)
 def test_old_same_transaction_and_old_rehearse_still_refuse(self):
  with self.assertRaisesRegex(DemoError,'分轮'):fix_document(self.s.input_path,self.d/'bad.docx',self.s.confirmed,selected_keys=self.s.selected,**self.s._rules_arguments())
  self.assertFalse(self.s.rehearse());self.assertIn('分轮',self.s.rehearsal_error);self.assertFalse(self.s.history)
 def test_draft_covers_all_selection_and_does_not_authorize(self):
  p=self.s.correction_plan();self.assertTrue(p['two_steps']);self.assertFalse(p['blocked']);self.assertEqual(p['selected_count'],10);self.assertEqual([len(x['keys']) for x in p['steps']],[6,4]);self.assertEqual(set(k for x in p['steps'] for k in x['keys']),set(self.s.selected));self.assertIsNone(self.s.rehearsal);self.assertIsNone(self.s.result)
 def test_preview_two_actual_transactions_without_formal_publication(self):
  import web.session as api
  with mock.patch('web.session.fix_document',wraps=api.fix_document) as fix:
   self.preview();self.assertEqual(fix.call_count,2);self.assertEqual(str(fix.call_args_list[1].args[0]),self.s.rehearsal['transactions'][0]['result']['output'])
  self.assertEqual(self.s.generation_count,0);self.assertEqual(self.s.current_round,0);self.assertFalse(self.s.history);self.assertIsNone(self.s.result);self.assertFalse(self.s.downloads());self.assertEqual(len(self.s.rehearsal['transactions']),2)
 def test_exact_coordinates_distinguish_repeated_text(self):
  self.preview();r=self.s.rehearsal;targets=r['resolved'];same=[t for t in targets if t['text']=='[1]' and t['paragraph']==3];self.assertEqual(len(same),2);self.assertNotEqual(same[0]['start'],same[1]['start']);self.assertNotEqual(same[0]['new_key'],same[1]['new_key']);self.assertTrue(all(t['status']=='待修正' for t in targets))
 def test_independent_manual_two_round_path_same_bytes(self):
  self.preview();p=self.s.correction_plan();one=fix_document(self.s.input_path,self.d/'manual1.docx',self.s.confirmed,selected_keys=p['steps'][0]['keys'],**self.s._rules_arguments());new=check_document(one['output'],one['output_body_manifest'],mode='academic',classification_manifest=one['output_classification_manifest']);coords={(t['paragraph'],t['start'],t['end']) for t in p['targets']};keys=[f['key'] for f in new['findings'] if f['rule_id']=='R33' and (f['locator']['paragraph'],f['locator']['start'],f['locator']['end']) in coords];two=fix_document(one['output'],self.d/'manual2.docx',one['output_body_manifest'],mode='academic',classification_manifest=one['output_classification_manifest'],selected_keys=keys)
  for r,t in zip((one,two),self.s.rehearsal['transactions']):self.assertEqual(Path(r['output']).read_bytes(),Path(t['result']['output']).read_bytes())
 def test_independent_character_and_zip_whitelist_nonvacuous(self):
  original=self.s.input_path.read_bytes();self.preview();tx=self.s.rehearsal['transactions'];proof=verify(self.s.input_path,tx[0]['result']['output'],tx[1]['result']['output']);self.assertTrue(proof['step2_exact_selected_character_superscript_only']);self.assertEqual(original,self.s.input_path.read_bytes())
 def test_new_unselected_R07_remains_visible_and_not_repaired(self):
  self.preview();v=self.s.rehearsal_view();rows=v['steps'][0]['impact']['records'];self.assertTrue(any(r['kind']=='new_problem' and r['rule_id']=='R07' and r['locator']['paragraph']==3 for r in rows));p=Package(self.s.rehearsal['transactions'][1]['result']['output']);self.assertEqual(p.paragraphs[2].find('w:pPr/w:ind',NS).get(q('firstLine')),'560');self.assertTrue(any(r['rule_id']=='R07' and r['locator'].get('paragraph')==3 and r['status']=='review' for r in self.s.rehearsal['transactions'][1]['result']['after']['findings']))
 def test_total_counts_not_sum_and_unknown_alignment_not_resolved(self):
  self.preview();v=self.s.rehearsal_view();self.assertEqual(v['engine_calls'],2);self.assertEqual(v['actual_change_records'],10);self.assertEqual(v['overall_impact']['remaining_summary'],self.s.rehearsal['transactions'][-1]['result']['after']['summary']);self.assertGreater(v['overall_impact']['counts']['unaligned'],0);self.assertTrue(any(r['kind']=='new_problem' for r in v['steps'][0]['impact']['records']))
 def test_second_step_failure_leaves_no_formal_or_orphan(self):
  import web.session as api
  original=api.fix_document;calls=[]
  def fail(*a,**kw):
   calls.append(1)
   if len(calls)==2:raise DemoError('second transaction refused')
   return original(*a,**kw)
  with mock.patch('web.session.fix_document',side_effect=fail):self.assertFalse(self.s.rehearse_plan())
  self.assertEqual(self.s.generation_count,0);self.assertFalse(self.s.history);self.assertIsNone(self.s.result);self.assertFalse(list(self.s.task_dir.glob('rehearsal-*')))
 def test_resolver_changed_paragraph_hash_refuses(self):
  self.preview();r=self.s.rehearsal;one=r['transactions'][0]['result'];p=Package(one['output']);p.paragraphs[2].findall(q('r'))[0].find(q('t')).text='changed'
  with self.assertRaisesRegex(DemoError,'身份'):resolve_targets(p,one['output_classification_manifest'],r['draft']['targets'],r['transactions'][1]['result']['before'])
 def test_fresh_review_or_unsafe_scope_refuses(self):
  self.preview();r=self.s.rehearsal;one=r['transactions'][0]['result'];fresh=deepcopy(r['transactions'][1]['result']['before']);target=next(f for f in fresh['findings'] if f['rule_id']=='R33');target['status']='review';target['fixable']=False
  with self.assertRaisesRegex(DemoError,'待复核'):resolve_targets(Package(one['output']),one['output_classification_manifest'],r['draft']['targets'],fresh)
 def test_noop_target_returns_no_key_to_execute(self):
  self.preview();r=self.s.rehearsal;one=r['transactions'][0]['result'];fresh=deepcopy(r['transactions'][1]['result']['before'])
  for f in fresh['findings']:
   if f['rule_id']=='R33' and f['status']=='problem':f['status']='pass'
  out=resolve_targets(Package(one['output']),one['output_classification_manifest'],r['draft']['targets'],fresh);self.assertTrue(all(t['status']=='无需修改' for t in out))
 def test_handoff_rejects_text_or_scope_relocation(self):
  self.preview();one=self.s.rehearsal['transactions'][0]['result'];p=Package(one['output']);p.paragraphs[0].findall(q('r'))[0].find(q('t')).text='other'
  with self.assertRaises(DemoError):handoff(Package(self.s.input_path),p,one['output_classification_manifest'])
 def test_complex_citation_cannot_join_by_confirmation(self):
  bad=next(f for f in self.s.report['findings'] if f['rule_id']=='R33' and f['status']=='review');self.s.selected.append(bad['key']);self.assertFalse(self.s.rehearse_plan());self.assertFalse(self.s.history)
 def test_adopt_requires_ack_then_zero_refix_and_double_click_once(self):
  i=self.preview();self.assertFalse(self.s.adopt_plan(i));self.assertFalse(self.s.history)
  with mock.patch('web.session.fix_document',side_effect=AssertionError('refix')):
   self.adopt();self.assertTrue(self.s.adopt_plan(i,acknowledged=True));self.s.downloads();self.s.result_package()
  self.assertEqual(self.s.generation_count,2);self.assertEqual(len(self.s.history),2);self.assertEqual(self.s.current_round,0);self.assertEqual(self.s.result['plan']['summary']['fix_calls_at_adoption'],0);self.assertEqual([h['result']['round']['input_round'] for h in self.s.history],[0,1]);self.assertFalse(list(self.s.task_dir.glob('rehearsal-*')))
 def test_cancel_selection_and_scope_invalidate(self):
  i=self.preview();self.s.set_selection(self.s.selected[:-1]);self.assertIsNone(self.s.rehearsal);self.assertFalse(self.s.adopt_plan(i,acknowledged=True));self.preview();self.s.material_exclusions['18']='new exclusion reason';self.assertIsNone(self.s.rehearsal_view());self.assertFalse(self.s.history)
 def test_cancel_only_owned_directory(self):
  self.preview();foreign=self.s.task_dir/'foreign';foreign.mkdir();(foreign/'keep').write_text('keep');self.s.cancel_rehearsal();self.assertTrue((foreign/'keep').exists());self.assertFalse(self.s.history)
 def test_external_intermediate_change_rejected(self):
  i=self.preview();Path(self.s.rehearsal['transactions'][0]['result']['output']).write_bytes(b'changed');self.assertFalse(self.s.adopt_plan(i,acknowledged=True));self.assertFalse(self.s.history);self.assertEqual(self.s.generation_count,0)
 def test_external_input_and_rule_change_rejected(self):
  i=self.preview();self.s.input_path.write_bytes(b'changed');self.assertFalse(self.s.adopt_plan(i,acknowledged=True));self.assertFalse(self.s.history)
  s=session(self.d/'other');s.set_selection(selection(s));rp=self.d/'rules.json';rp.write_bytes(s.rules_path.read_bytes());s.rules_path=rp;self.preview(s);rp.write_bytes(rp.read_bytes()+b' ');self.assertFalse(s.adopt_plan(s.rehearsal['id'],acknowledged=True))
 def test_report_plan_and_execution_tamper_rejected(self):
  i=self.preview();self.s.rehearsal['view']['engine_calls']=0;self.assertFalse(self.s.adopt_plan(i,acknowledged=True));self.assertFalse(self.s.history)
  i=self.preview();Path(self.s.rehearsal['transactions'][1]['record']).write_text('{}');self.assertFalse(self.s.adopt_plan(i,acknowledged=True))
  i=self.preview()
  with mock.patch('web.rehearsal_session.execution_hash',return_value='changed'):self.assertFalse(self.s.adopt_plan(i,acknowledged=True))
 def test_archive_second_step_failure_rolls_back_whole_plan(self):
  i=self.preview();before=set(self.s.task_dir.iterdir());real=WebSession._archive_round;calls=[]
  def fail(staged,r):
   calls.append(1);real(staged,r)
   if len(calls)==2:raise OSError('full disk at second archive')
  with mock.patch.object(WebSession,'_archive_round',fail):self.assertFalse(self.s.adopt_plan(i,acknowledged=True))
  self.assertEqual(before,set(self.s.task_dir.iterdir()));self.assertFalse(self.s.history);self.assertEqual(self.s.generation_count,0);self.assertIsNone(self.s.result);self.adopt()
 def test_archive_summary_corruption_refuses_all(self):
  i=self.preview();import web.plan_session as module
  real=module.write_new
  def corrupt(path,data,*a,**kw):
   p=real(path,data,*a,**kw)
   if p.name=='plan-summary.json':p.write_bytes(b'{}')
   return p
  with mock.patch('web.plan_session.write_new',side_effect=corrupt):self.assertFalse(self.s.adopt_plan(i,acknowledged=True))
  self.assertFalse(self.s.history);self.assertFalse(list(self.s.task_dir.glob('fixed-plan-*')))
 def test_binding_race_during_archival_no_partial_publication(self):
  i=self.preview();real=WebSession._archive_round
  def race(staged,r):real(staged,r);self.s.selected=[]
  with mock.patch.object(WebSession,'_archive_round',race):self.assertFalse(self.s.adopt_plan(i,acknowledged=True))
  self.assertFalse(self.s.history);self.assertEqual(self.s.generation_count,0);self.assertFalse(list(self.s.task_dir.glob('fixed-plan-*')))
 def test_post_publication_cleanup_failure_does_not_rollback(self):
  self.preview()
  with mock.patch('web.plan_session.shutil.rmtree',side_effect=OSError('busy')):self.adopt()
  self.assertEqual(len(self.s.history),2);self.assertTrue(self.s.downloads());self.assertIn('临时目录',self.s.rehearsal_error)
 def test_single_step_uses_original_rehearsal(self):
  self.s.set_selection([k for k in self.s.selected if k.startswith('R05')]);self.assertFalse(self.s.correction_plan()['two_steps']);self.assertTrue(self.s.rehearse_plan(),self.s.rehearsal_error);self.assertNotIn('kind',self.s.rehearsal);self.assertEqual(self.s.rehearsal_view()['impact']['change_record_count'],4)
 def test_pending_project_restore_intent_not_authorization(self):
  i=self.preview();raw=self.s.prepare_project();z=zipfile.ZipFile(BytesIO(raw));self.assertFalse(any('rehearsal-plan' in n for n in z.namelist()));t=WebSession(self.d/'restore');t.stage_project(raw);r=t.restore_project(acknowledged=True);self.assertEqual(r.selected,self.s.selected);self.assertIsNone(r.rehearsal);self.assertTrue(r.report);self.assertTrue(r.correction_plan()['two_steps']);self.assertFalse(r.adopt_plan(i,acknowledged=True));self.assertTrue(r.rehearse_plan(),r.rehearsal_error)
 def test_formal_project_parent_relations_recheck_and_continue(self):
  self.preview();self.adopt();raw=self.s.prepare_project();t=WebSession(self.d/'restore');t.stage_project(raw);r=t.restore_project(acknowledged=True);self.assertEqual(len(r.history),2);self.assertIsNone(r.rehearsal);self.assertEqual([h['result']['round']['input_round'] for h in r.history],[0,1]);self.assertTrue(r.history[0]['saved_record']['plan']);self.assertTrue(r.continue_history(r.history[-1]['stem'],acknowledged=True));self.assertEqual(r.current_round,2);self.assertTrue(r.report);r.set_selection([f['key'] for f in r.eligible()][:1]);self.assertTrue(r.generate(),r.error);self.assertEqual(r.generation_count,3)
 def test_final_download_parent_is_middle_and_explicit_next(self):
  self.preview();self.adopt();steps=self.s.plan_step_downloads();self.assertEqual(self.s.downloads()['round-input.docx'],steps[0]['fixed.docx']);self.assertEqual(self.s.downloads()['fixed.docx'],steps[-1]['fixed.docx']);self.s.next_round();self.assertEqual(self.s.current_round,2);self.assertEqual(self.s.input_bytes,steps[-1]['fixed.docx']);self.assertEqual(self.s.material_exclusions,{'18':'人工排除：合成程序代码，保留制表与换行'})
 def test_all_report_formats_and_result_zip_keep_step_records(self):
  self.preview();self.adopt();files=self.s.prepare_reading_export();d=json.loads(files['report.json']);self.assertEqual(d['plan']['summary']['formal_rounds'],2);self.assertIn('整计划最终影响',files['report.html'].decode());self.assertIn('<td>1</td><td>1</td><td>0</td>',files['report.html'].decode());self.assertIn('<td>2</td><td>2</td><td>1</td>',files['report.html'].decode());self.assertIn('分步计划',files['report.md'].decode());z=zipfile.ZipFile(BytesIO(self.s.result_package()));self.assertEqual(z.read('fixed.docx'),self.s.plan_step_downloads()[-1]['fixed.docx']);self.assertTrue(all(f'steps/step-{i}-recheck.md' in z.namelist() for i in (1,2)));self.assertEqual(len([n for n in z.namelist() if n.endswith('.docx')]),1);self.assertNotIn(str(self.s.task_dir),z.read('plan-summary.json').decode())
 def test_modified_formal_middle_rejects_final_package_even_if_cached(self):
  self.preview();self.adopt();self.s.result_package();Path(self.s.history[0]['result']['output']).write_bytes(b'bad');
  with self.assertRaises(DemoError):self.s.result_package()
 def test_session_isolation(self):
  i=self.preview();other=session(self.d/'b');other.set_selection(selection(other));self.preview(other);self.assertFalse(other.adopt_plan(i,acknowledged=True));self.assertTrue(self.s.rehearsal_view());self.adopt();self.assertFalse(other.history);self.assertEqual(other.generation_count,0)
 def test_other_native_scopes_and_story_transaction_survive_handoff(self):
  from scripts.reproduce_scope_demo import ROOT,prepare,old_check
  from lxml import etree as E
  p=Package(ROOT/'samples/phase26/composite.docx')
  r=p.paragraphs[16].findall(q('r'))[0]
  from core.engine import _ensure
  _ensure(_ensure(r,'rPr'),'sz').set(q('val'),'28')
  foot=E.fromstring(p.parts['word/footnotes.xml']);r=next(r for r in foot.iter(q('r')) if r.find(q('t')) is not None);_ensure(_ensure(r,'rPr'),'sz').set(q('val'),'28');p.story_roots['word/footnotes.xml']=foot
  src=self.d/'all-scopes.docx';src.write_bytes(p.bytes(True));s=WebSession(self.d/'all');s.set_mode('academic');s.load(src.read_bytes(),'全范围合成.docx');prepare(s);old_check(s)
  keys=[f['key'] for f in s.eligible() if f['rule_id'] in ('R26','R36') or f['rule_id'] in ('R05','R33') and f['locator'].get('paragraph')==17];self.assertTrue(any(k.startswith('R36') for k in keys));s.set_selection(keys);self.preview(s);self.adopt(s)
  for field in ('table_scope','front_scope','toc_scope','citation_scope','note_scope','caption_scope'):
   value=s.result['output_classification_manifest'][field];self.assertEqual(value['input_sha256'],s.result['after']['input_sha256']);self.assertTrue(value['confirmed'])
  self.assertEqual(s.result['output_classification_manifest']['material_exclusions'],s.classification_confirmed['material_exclusions']);self.assertTrue(s.downloads());self.assertEqual(src.read_bytes(),p.bytes(True))
 def test_previous_step_archive_tampered_while_preparing_second_refuses(self):
  i=self.preview();real=WebSession._archive_round
  def corrupt(staged,r):
   real(staged,r)
   if len(staged.history)==2:(staged.task_dir/(staged.history[0]['stem']+'.json')).write_bytes(b'{}')
  with mock.patch.object(WebSession,'_archive_round',corrupt):self.assertFalse(self.s.adopt_plan(i,acknowledged=True))
  self.assertFalse(self.s.history);self.assertEqual(self.s.generation_count,0);self.assertFalse(list(self.s.task_dir.glob('fixed-plan-*')))
 def test_R11_preserves_effective_title_format_with_plan(self):
  from core.engine import _ensure
  from core.extended import formatting_snapshot,snapshots_equal
  from core.citations import inventory
  p=Package(SAMPLE/'errors.docx');_ensure(_ensure(p.paragraphs[1],'pPr'),'pStyle').set(q('val'),'Normal')
  s=WebSession(self.d/'heading');s.set_mode('academic');s.load(p.bytes(True),'标题保护合成.docx');ds=json.loads((SAMPLE/'scope.json').read_text());s.set_types(ds['roles']);s.exclude_materials([18],ds['material_exclusions']['18']);s.enable_citations(True);d=deepcopy(s.citation_draft);d['objects']={r['id']:'excluded' if r['text']=='[8]' else 'citation' for r in s.citation_inventory()['objects']};s.edit_citations(d);s.confirm_citations();self.assertTrue(s.confirm_and_check());keys=selection(s)+[f['key'] for f in s.eligible() if f['rule_id']=='R11'];self.assertTrue(any(k.startswith('R11') for k in keys));s.set_selection(keys);self.preview(s);self.adopt(s)
  output=Package(s.result['output']);self.assertTrue(snapshots_equal(formatting_snapshot(p,p.paragraphs[1]),formatting_snapshot(output,output.paragraphs[1])));self.assertEqual(p.parts['word/styles.xml'],output.parts['word/styles.xml'])

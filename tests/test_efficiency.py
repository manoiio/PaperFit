"""Stage12验证实际数据/保护；mock渲染只测调用与绑定，不作为视觉证据。"""
import unittest,json,zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from io import BytesIO
from unittest.mock import patch
from web.session import WebSession
from core.package import DemoError,sha256,Package
from core import check_document
ROOT=Path(__file__).resolve().parents[1]
class EfficiencyAcceptance(unittest.TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def model(self,extended=False):
  s=WebSession(self.root);s.set_mode('extended' if extended else 'basic');p=ROOT/('samples/extended-correct.docx' if extended else 'samples/errors.docx');s.load(p.read_bytes(),'../../private.docx')
  if extended:s.set_types(json.loads(p.with_suffix('.types.json').read_text())['paragraph_types'])
  else:s.set_body([4,5,6,11,14,15])
  s.confirm();s.check();return s
 def fixed(self):
  s=self.model();s.set_selection([f['key'] for f in s.eligible()]);self.assertTrue(s.generate());return s
 def test_check_cache_same_as_independent_engine(self):
  s=self.model()
  with patch('web.session.check_document',wraps=check_document) as c:
   self.assertTrue(s.check());self.assertEqual(c.call_count,0);self.assertEqual(s.report,check_document(s.input_path,s.confirmed));self.assertTrue(s.check(force=True));self.assertEqual(c.call_count,1)
 def test_cache_report_deepcopy_not_mutable_xml(self):
  s=self.model();gold=deepcopy(s.report);s.report['findings'].clear();s.check();self.assertEqual(s.report,gold);self.assertFalse(any(isinstance(v,Package) for v in s.readonly_cache.values()))
 def test_fix_does_not_pollute_original_analysis(self):
  s=self.fixed();s.check();self.assertEqual(s.report['summary']['problem_count'],11);self.assertEqual(s.original_bytes,s.input_path.read_bytes())
 def test_different_scope_invalidates_cache(self):
  s=self.model();s.set_body([4]);self.assertFalse(s.readonly_cache);self.assertIsNone(s.confirmed);self.assertIsNone(s.report);s.confirm();s.check();self.assertEqual(s.report['coverage']['body_paragraphs'],[4])
 def test_mode_invalidates_all_results(self):
  s=self.fixed();s.result_package();s.set_mode('extended');self.assertIsNone(s.result);self.assertIsNone(s.package_cache);self.assertFalse(s.readonly_cache)
 def test_new_file_invalidates_package_and_readonly(self):
  s=self.fixed();s.result_package();s.load((ROOT/'samples/correct.docx').read_bytes(),'next.docx');self.assertIsNone(s.package_cache);self.assertFalse(s.readonly_cache)
 def test_external_input_change_refuses_cached_check(self):
  s=self.model();s.input_path.write_bytes(b'changed');self.assertFalse(s.check());self.assertIsNone(s.report)
 def test_external_output_change_refuses_download_and_pack(self):
  s=self.fixed();s.result_package();Path(s.result['output']).write_bytes(b'changed')
  with self.assertRaises(DemoError):s.result_package()
 def test_missing_output_refuses_package(self):
  s=self.fixed();s.result_package();Path(s.result['output']).unlink()
  with self.assertRaises((DemoError,OSError)):s.result_package()
 def test_input_rule_file_change_refuses_old_pack(self):
  s=self.fixed();p=self.root/'rules.json';p.write_bytes(s.rules_path.read_bytes());s.rules_path=p;s.result_package();data=json.loads(p.read_text());data['name']='changed';p.write_text(json.dumps(data))
  with self.assertRaises(DemoError):s.result_package()
 def test_width_and_center_share_readonly_result(self):
  from core.widths import check_widths
  s=self.model()
  with patch('core.widths.check_widths',wraps=check_widths) as c:
   w=s.width_report('input');s.current_bundle();self.assertEqual(c.call_count,1);self.assertEqual(w,s.width_report('input'));w['objects'].clear();self.assertTrue(s.width_report('input')['objects'])
 def test_pagination_cache_bound_to_classification(self):
  from core.layout import suggest_pagination_aids
  s=self.model(True)
  with patch('core.layout.suggest_pagination_aids',wraps=suggest_pagination_aids) as c:
   s.layout_proposals('input');s.layout_proposals('input');self.assertEqual(c.call_count,1)
   s.batch_types([16],'other');s.confirm();s.layout_proposals('input');self.assertEqual(c.call_count,2)
 def test_batch_stable_ids_independent_of_order(self):
  s=self.model(True);old=deepcopy(s.paragraph_types);s.batch_types([20,8],'other');self.assertEqual(s.paragraph_types['8'],'other');self.assertEqual(s.paragraph_types['20'],'other');self.assertEqual(s.paragraph_types['10'],old['10']);self.assertIsNone(s.confirmed)
 def test_batch_filter_does_not_select(self):
  s=self.model(True);old=deepcopy(s.paragraph_types);self.assertTrue(s.classification_candidates(['body']));self.assertEqual(s.paragraph_types,old);self.assertIsNotNone(s.confirmed)
 def test_invalid_batch_ids_refused_atomically(self):
  s=self.model(True);old=deepcopy(s.paragraph_types)
  for ids in ([0],[True],[8,999],[8,8],[]):
   with self.assertRaises(DemoError):s.batch_types(ids,'body')
  self.assertEqual(old,s.paragraph_types)
 def test_range_parsing_bounded(self):
  s=self.model(True);self.assertEqual(s.parse_paragraph_ranges('8-10,20'),[8,9,10,20])
  for value in ('0','1-999999999','20-8','1-2-3','x'):
   with self.assertRaises(DemoError):s.parse_paragraph_ranges(value)
 def test_restore_requires_explicit_confirmation(self):
  s=self.model(True);s.batch_types([8],'other');old=deepcopy(s.paragraph_types);self.assertIn(8,s.initial_adjustments())
  with self.assertRaises(DemoError):s.restore_types()
  self.assertEqual(old,s.paragraph_types);s.restore_types(confirmed=True);self.assertEqual(s.paragraph_types['8'],next(p['suggested_type'] for p in s.suggestions['paragraphs'] if p['index']==8));self.assertIsNone(s.confirmed)
 def test_shortcut_same_as_split_checks(self):
  for ext in (False,True):
   s=self.model(ext);gold=s.report;s.invalidate();self.assertTrue(s.confirm_and_check());self.assertEqual(s.report,gold)
 def test_shortcut_failed_confirmation_does_not_check(self):
  s=self.model();s.set_body([])
  with patch.object(s,'check') as c:self.assertFalse(s.confirm_and_check());c.assert_not_called()
 def test_preview_ordinary_views_dont_probe_environment(self):
  s=self.model();meta=self.fake(s);s.preview_environment=({},'cfg');t=s.preview_targets()['input'];s.preview_cache[s._preview_binding(t,probe=False)]=meta
  with patch('web.preview_session.configuration',side_effect=AssertionError('unexpected probe')):
   self.assertIsNotNone(s.get_preview('input',verify_environment=False));s.current_bundle();s.current_bundle()
 def fake(self,s):
  p=self.root/'page.png';p.write_bytes(b'not visual evidence');return {'document_sha256':s.inventory['input_sha256'],'render_config_sha256':'cfg','pages':[str(p)],'artifact_sha256':{str(p):sha256(p.read_bytes())}}
 def test_preview_explicit_click_revalidates_environment_without_repeat_render(self):
  s=self.model();meta=self.fake(s)
  with patch('web.preview_session.configuration',return_value=({},'cfg')) as c,patch('web.preview_session.render_preview',return_value=meta) as render:
   self.assertTrue(s.generate_preview('input'));self.assertTrue(s.generate_preview('input'));self.assertEqual(render.call_count,1);self.assertEqual(c.call_count,2)
 def test_refresh_changed_environment_hides_old_cache(self):
  s=self.model();meta=self.fake(s)
  with patch('web.preview_session.configuration',return_value=({},'cfg')),patch('web.preview_session.render_preview',return_value=meta):s.generate_preview('input')
  with patch('web.preview_session.configuration',return_value=({},'new')):s.refresh_preview_environment()
  self.assertIsNone(s.get_preview('input',verify_environment=False))
 def test_download_cached_reports_have_no_execution_side_effect(self):
  s=self.fixed();s.prepare_reading_export()
  with patch('web.session.fix_document',side_effect=AssertionError()),patch('web.preview_session.render_preview',side_effect=AssertionError()),patch('web.preview_session.configuration',side_effect=AssertionError()):
   first=s.reading_downloads();self.assertEqual(first,s.reading_downloads());s.result_package();s.result_package();self.assertEqual(s.generation_count,1)
 def test_html_bytes_built_only_once_for_matching_export(self):
  s=self.model();s.prepare_reading_export()
  with patch('web.center_session.html_report',side_effect=AssertionError('rebuilt')):s.reading_downloads();s.reading_downloads()
 def test_zip_matches_individual_files_and_independent_recheck(self):
  s=self.fixed();raw=s.result_package();files=s.downloads()
  with zipfile.ZipFile(BytesIO(raw)) as z:
   self.assertEqual(z.read('fixed.docx'),files['fixed.docx']);self.assertEqual(json.loads(z.read('report.json'))['format_summary'],s.result['after']['summary']);self.assertEqual(json.loads(z.read('scope.json')),s.result['output_body_manifest']);self.assertIn(b'11',z.read('changes.md'))
   out=self.root/'independent.docx';out.write_bytes(z.read('fixed.docx'));self.assertEqual(check_document(out,json.loads(z.read('scope.json')))['summary']['problem_count'],0)
 def test_zip_private_and_safe_names(self):
  s=self.fixed()
  with zipfile.ZipFile(BytesIO(s.result_package())) as z:
   self.assertNotIn('original.docx',z.namelist())
   for n in z.namelist():
    self.assertNotIn('/',n);self.assertNotIn('..',n)
    if not n.endswith('.docx'):
     text=z.read(n).decode();self.assertNotIn('/Volumes/',text);self.assertNotIn('/Users/',text);self.assertNotIn('DEEPSEEK_API_KEY=',text);self.assertNotIn('2026年',text)
 def test_package_volume_limit(self):
  s=self.fixed()
  with self.assertRaises(DemoError):s.result_package(max_bytes=100)
 def test_repeat_package_same_bytes_no_extra_round(self):
  s=self.fixed();one=s.result_package();self.assertEqual(one,s.result_package());self.assertEqual(len(s.history),1);self.assertEqual(s.generation_count,1)
 def test_sessions_isolated(self):
  a=self.fixed();b=self.model(True);a.result_package();self.assertIsNone(b.package_cache);self.assertNotEqual(a.task_dir,b.task_dir);a.batch_types([4],'other');self.assertIsNotNone(b.confirmed);self.assertNotEqual(a.readonly_cache,b.readonly_cache)
 def test_template_package_reloads_exact_rules_hash(self):
  s=self.model(True);template=(ROOT/'tests/fixtures/history/phase9/final/template-B-active.json').read_bytes();self.assertTrue(s.import_template(template));self.assertTrue(s.apply_template());s.confirm();s.check();s.set_selection([f['key'] for f in s.eligible()]);self.assertTrue(s.generate())
  with zipfile.ZipFile(BytesIO(s.result_package())) as z:
   path=self.root/'template.json';path.write_bytes(z.read('template.json'));self.assertEqual(z.read('rules.json'),z.read('template.json'));out=self.root/'out.docx';out.write_bytes(z.read('fixed.docx'));manifest=json.loads(z.read('scope.json'));after=check_document(out,None,mode='extended',classification_manifest=manifest,custom_rules_path=path);self.assertEqual(after['rules']['sha256'],s.result['after']['rules']['sha256']);self.assertEqual(after['summary'],s.result['after']['summary'])
 def test_pack_once_without_duplicate_zip_creation(self):
  s=self.fixed();s.result_package()
  with patch('web.efficiency.zipfile.ZipFile',side_effect=AssertionError('rebuilt ZIP')):s.result_package();s.result_package()
 def test_missing_previous_aux_input_refuses_pack(self):
  s=self.model(True);s.set_selection([f['key'] for f in s.eligible()]);s.generate();s.next_round();s.operation='width'
  # Base synthetic fits; use an existing confirmed safe title adjacency instead.
  proposals=s.layout_proposals('input');keys=[p['key'] for p in proposals['pairs'] if p['status']=='available'];self.assertTrue(s.generate_layout('input',keys[:1]));s.result_package();Path(s.result['round_input_path']).write_bytes(b'changed')
  with self.assertRaises(DemoError):s.result_package()
 def test_repeat_shortcut_no_duplicate_manifest(self):
  s=self.model(True);before=len(list(s.task_dir.glob('confirmed-types-*.json')));s.confirm_and_check();s.confirm_and_check();self.assertEqual(len(list(s.task_dir.glob('confirmed-types-*.json'))),before);self.assertEqual(s.generation_count,0)
 def test_active_template_apply_invalidates_cached_report(self):
  s=self.model(True);s.prepare_reading_export();self.assertTrue(s.readonly_cache);s.import_template((ROOT/'tests/fixtures/history/phase9/final/template-B-active.json').read_bytes());self.assertTrue(s.apply_template());self.assertIsNone(s.report);self.assertIsNone(s.confirmed);self.assertFalse(s.readonly_cache);self.assertFalse(s.reading_downloads());s.confirm_and_check();self.assertEqual(s.report['summary']['problem_count'],50)
if __name__=='__main__':unittest.main()

from tests.ui_navigation import show, click as ui_click
"""第十一阶段投影、状态与离线报告行为；只用合成论文，无外部API。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest.mock import patch
import unittest,json
from lxml import html as LH
from web.session import WebSession
from web.issues import project,filter_records,group_records,next_steps
from web.reading_report import portable,html_report,markdown_report
from core.package import DemoError,sha256
ROOT=Path(__file__).resolve().parents[1]
class CenterAcceptance(unittest.TestCase):
 def setUp(self):self.t=TemporaryDirectory();self.root=Path(self.t.name)
 def tearDown(self):self.t.cleanup()
 def model(self,correct=False,extended=False):
  s=WebSession(self.root/('jobs'+str(len(list(self.root.iterdir())))));name='extended-correct' if extended else 'correct' if correct else 'errors';p=ROOT/'samples'/f'{name}.docx'
  if extended:s.set_mode('extended')
  s.load(p.read_bytes(),'../软件演示.docx',None if extended else json.loads(p.with_suffix('.body.json').read_text()))
  if extended:s.set_types(json.loads(p.with_suffix('.types.json').read_text())['paragraph_types'])
  s.confirm();s.check();return s
 def generated(self):
  s=self.model();s.set_selection([f['key'] for f in s.eligible()]);self.assertTrue(s.generate(),s.error);return s
 def test_projection_retains_every_finding_and_original_status(self):
  s=self.model();raw=deepcopy(s.report);b=s.current_bundle();fs=[r for r in b['projection']['records'] if r['record_key'].startswith('R')]
  self.assertEqual([(r['record_key'],r['status'],r['raw']) for r in fs],[(f['key'],f['status'],f) for f in raw['findings']]);self.assertEqual(s.report,raw)
 def test_four_categories_and_no_aggregate_score(self):
  s=self.model(extended=True);b=s.current_bundle();cats={r['category'] for r in b['projection']['records']};self.assertEqual(cats,{'format','width','pagination','review'});self.assertNotIn('score',b)
 def test_suggestions_not_problems_and_review_never_executable(self):
  b=self.model(extended=True).current_bundle();rs=b['projection']['records'];self.assertTrue(any(r['status']=='available' for r in rs));self.assertFalse(any(r['category']=='pagination' and r['status']=='problem' for r in rs))
  for r in rs:
   if r['status']=='review':self.assertIn('不自动',r['action'])
 def test_filter_and_group_lossless_record_binding(self):
  b=self.model().current_bundle();rs=b['projection']['records'];groups=group_records(rs);self.assertEqual({r['id'] for g in groups.values() for r in g},{r['id'] for r in rs})
  for obj in {r['object'] for r in rs}:self.assertTrue(all(r['object']==obj for r in filter_records(rs,objects=[obj])))
  for status in {r['status'] for r in rs}:self.assertEqual(len(filter_records(rs,statuses=[status])),sum(r['status']==status for r in rs))
 def test_format_summary_matches_engine_without_width_double_count(self):
  s=self.model();b=s.current_bundle();self.assertEqual(b['projection']['format_summary'],s.report['summary']);self.assertEqual(b['format']['summary']['problem_count'],11)
 def test_mm_display_two_decimals_raw_precise(self):
  b=self.model(extended=True).current_bundle();r=next(r for r in b['projection']['records'] if r['record_key']=='W01:table=1');self.assertIn('160.02mm',r['actual']);self.assertEqual(r['raw']['declared_width_mm'],160.01999999999998)
 def test_pass_notapplicable_boundaries_and_notes_retained(self):
  s=self.model(correct=True);b=s.current_bundle();self.assertEqual(b['format']['summary']['problem_count'],0);self.assertTrue(filter_records(b['projection']['records'],statuses=['pass']));self.assertTrue(filter_records(b['projection']['records'],statuses=['not_applicable']));self.assertTrue(filter_records(b['projection']['records'],statuses=['boundary']))
  s.report['coverage_notes']=[{'locator':{'paragraph':4},'status':'review','detail':'合成覆盖待复核'}];b=s.current_bundle();self.assertIn('合成覆盖待复核',[r['reason'] for r in b['projection']['records']])
 def test_steps_from_dependencies_and_navigation_no_mutation(self):
  s=self.model();b=s.current_bundle();step=next(x for x in b['steps'] if x['area']=='format');state=(deepcopy(s.selected),s.generation_count,len(s.history),s.result)
  with patch('web.session.fix_document',side_effect=AssertionError('unexpected fix')):s.focus_operation(step['area'],b['target'],step['keys'])
  self.assertEqual((s.selected,s.generation_count,len(s.history),s.result),state);self.assertEqual(s.operation,'format')
 def test_page_change_step_requires_width_review_no_autoselect(self):
  s=self.model();s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R02']);self.assertTrue(s.generate());b=s.current_bundle();self.assertTrue(any(x['title']=='页边距已改，核对本轮宽度' for x in b['steps']));self.assertFalse(s.width_signature)
 def test_width_result_step_recommends_preview(self):
  s=self.model(extended=True);s.set_selection([]);p=s.width_report('input')
  # Default160mm table is in160mm body; use existing phase9B narrow page independently.
  from web.issues import next_steps
  fake={'kind':'width_adaptation','changes':[],'problem_delta':{'new_problem_causes':[]}}
  self.assertTrue(any(x['area']=='preview' and '换行' in x['title'] for x in next_steps(s.report,p,fake)))
 def test_current_result_and_input_round_not_mixed(self):
  s=self.generated();b=s.current_bundle();self.assertEqual(b['context']['round'],1);self.assertEqual(b['format']['summary']['problem_count'],0);self.assertEqual(s.current_round,0);self.assertEqual(b['context']['file_sha256'],s.result['output_body_manifest']['input_sha256'])
  self.assertTrue(s.next_round());self.assertEqual(s.current_bundle()['context']['round'],1)
 def test_history_view_does_not_switch_input(self):
  s=self.generated();before=(s.input_path,s.current_round,deepcopy(s.report),deepcopy(s.result));identity=s.history[0]['stem'];b=s.history_bundle(identity);files=s.history_reading_downloads(identity)
  self.assertEqual((s.input_path,s.current_round,s.report,s.result),before);self.assertEqual(sha256(files['fixed.docx']),b['context']['file_sha256'])
 def test_rule_mode_scope_change_marks_history_inapplicable(self):
  for field in ('scope','mode'):
   s=self.generated();s.prepare_reading_export()
   if field=='scope':s.set_body([4,5])
   else:s.set_mode('extended')
   self.assertIsNone(s.reading_export);self.assertFalse(s.history_rows()[0]['applicable']);self.assertIn('不适用',s.history_rows()[0]['status']);self.assertEqual(s.history_downloads(),[])
 def test_input_change_history_is_cleaned_tombstone_only(self):
  s=self.generated();old=s.task_dir;s.load((ROOT/'samples/correct.docx').read_bytes(),'另一个.docx');self.assertFalse(old.exists());r=s.history_rows()[0];self.assertFalse(r['downloadable']);self.assertIn('已清理',r['status']);self.assertEqual(s.history,[])
  with self.assertRaises(DemoError):s.history_reading_downloads(r['id'])
 def test_missing_and_changed_history_file_not_downloadable(self):
  for mode in ('missing','changed'):
   s=self.generated();p=Path(s.result['output']);identity=s.history[0]['stem'];p.unlink() if mode=='missing' else p.write_bytes(b'changed')
   self.assertFalse(s.history_rows()[0]['downloadable'])
   with self.assertRaises(DemoError):s.history_reading_downloads(identity)
 def test_changed_output_revokes_current_reading_download(self):
  s=self.generated();s.prepare_reading_export();Path(s.result['output']).write_bytes(b'changed')
  with self.assertRaises(DemoError):s.reading_downloads()
 def test_clear_selection_revokes_prepared_export(self):
  s=self.generated();s.prepare_reading_export();s.set_selection([]);self.assertEqual(s.reading_downloads(),{})
 def test_export_html_markdown_json_same_counts_records_and_raw_values(self):
  s=self.generated();files=s.prepare_reading_export();data=json.loads(files['report.json']);doc=LH.fromstring(files['report.html']);text=doc.text_content()
  self.assertEqual(data['format_summary']['problem_count'],s.result['after']['summary']['problem_count']);self.assertEqual(len(data['records']),len(s.current_bundle()['projection']['records']))
  self.assertIn('格式问题0',files['report.md'].decode());self.assertIn('全文排版合格',text)
  for f in s.result['after']['findings']:self.assertIn(f['key'],files['report.md'].decode())
 def test_html_offline_no_external_scripts_links_or_images(self):
  files=self.model().prepare_reading_export();doc=LH.fromstring(files['report.html']);self.assertEqual(doc.xpath('//script|//iframe|//img|//link|//form'),[]);self.assertTrue(doc.xpath('//meta[@http-equiv="Content-Security-Policy"]'))
 def test_all_untrusted_sources_and_text_escaped(self):
  s=self.model();s.report['findings'][0]['source']['quote']='<script>window.hacked=true</script>';s.report['findings'][0]['detail']='<img src=x onerror=alert(1)>';s.inventory['paragraphs'][3]['text']='<script>alert(2)</script>'
  data=portable(s.current_bundle(),display_name='<svg onload=alert(3)>.docx',include_excerpts=True);doc=LH.fromstring(html_report(data));self.assertEqual(doc.xpath('//script|//svg|//img'),[]);self.assertIn('<script>window.hacked=true</script>',doc.text_content())
 def test_default_privacy_no_paper_inventory_author_paths_or_key(self):
  s=self.model();s.display_name='作者姓名课程论文.docx';s.inventory['paragraphs'][3]['text']='私人正文，不应导出';s.report['findings'][0]['source']['quote']='规范 /Users/private/person/file API_KEY=sk-secret-demo';s.report['api_key']='secret-in-unknown-field'
  out=s.prepare_reading_export()['report.html'].decode()
  for text in ('作者姓名','私人正文','/Users/private','sk-secret-demo','secret-in-unknown-field'):self.assertNotIn(text,out)
 def test_excerpts_optional_bounded_and_default_proposals_text_hidden(self):
  s=self.model(extended=True);b=s.current_bundle();p=portable(b);self.assertFalse(any('excerpt' in r for r in p['records']));self.assertFalse(any('caption_text' in r['raw'] for r in p['records'] if r['record_key'].startswith('L')))
  e=portable(b,include_excerpts=True);self.assertTrue(all(len(r.get('excerpt',''))<=49 for r in e['records']));self.assertLessEqual(len({r['object'] for r in e['records'] if 'excerpt' in r}),20)
 def test_no_preview_or_word_reports_true_not_examined(self):
  p=portable(self.generated().current_bundle());self.assertEqual(p['preview']['status'],'未生成预览');self.assertEqual(p['word_status'],'未验收');self.assertIn('未记录',p['visual']['status'])
 def test_downloads_rerun_no_api_or_doc_modification(self):
  s=self.generated();s.prepare_reading_export();state=(s.generation_count,len(s.history),Path(s.result['output']).read_bytes())
  with patch('web.session.fix_document',side_effect=AssertionError('fix')),patch('ai.template_spec.parse_template_requirements',side_effect=AssertionError('API')):
   for _ in range(3):s.current_bundle();s.reading_downloads();s.history_reading_downloads(s.history[0]['stem'])
  self.assertEqual((s.generation_count,len(s.history),Path(s.result['output']).read_bytes()),state)
 def test_two_sessions_and_reset_are_isolated(self):
  a=self.generated();b=self.model();a.prepare_reading_export();self.assertIsNone(b.reading_export);self.assertEqual(b.history_rows(),[]);b.reset();self.assertTrue(Path(a.result['output']).exists())
 def test_raw_width_precision_stays_in_portable_json(self):
  s=self.model(extended=True);d=portable(s.current_bundle());row=next(r for r in d['records'] if r['record_key']=='W01:table=1');self.assertEqual(row['raw']['declared_width_mm'],160.01999999999998)
 def test_current_hash_change_blocks_projected_report(self):
  s=self.model();s.input_path.write_bytes(b'changed')
  with self.assertRaises(DemoError):s.current_bundle()
 def test_original_objects_and_fixed_template_unchanged_after_reading(self):
  s=self.generated();source=s.original_path.read_bytes();rules=(ROOT/'rules/scut_2015_demo.json').read_bytes();s.prepare_reading_export();s.history_rows();self.assertEqual(s.original_path.read_bytes(),source);self.assertEqual((ROOT/'rules/scut_2015_demo.json').read_bytes(),rules)
 def test_pagination_history_follows_ancestors_not_other_branches(self):
  s=self.model(extended=True);pairs=s.layout_proposals('input')['pairs'];key=next(p['key'] for p in pairs if p['status']=='available')
  self.assertTrue(s.generate_layout('input',[key]));self.assertEqual(len(s.current_bundle()['pagination_history']),1)
  self.assertTrue(s.next_round());p=portable(s.current_bundle());self.assertIsNone(p['pagination_applied']);self.assertEqual(p['pagination_history'][0]['round'],1);self.assertIn('历史',html_report(p))
  self.assertEqual(s.pagination_history(0),[])
 def test_title_caption_units_and_alignment_are_readable(self):
  from web.issues import field_value
  self.assertEqual(field_value(20.5,'R08',{'property':'size'},True),'20.5磅')
  self.assertEqual(field_value(1.25,'R09',{'property':'line'},True),'1.25倍')
  self.assertEqual(field_value('right','R10',{'property':'alignment'},True),'居右')
  self.assertEqual(field_value(9,'R12',{'property':'size'},True),'9磅')
 def test_new_bundled_renderer_available(self):
  from core.preview import configuration
  import subprocess
  from unittest.mock import patch
  with TemporaryDirectory() as td:
   p=Path(td);(p/'python/bin').mkdir(parents=True);(p/'python/bin/python3').write_text('mock runtime');script=p/'render.py';script.write_text('# mock renderer')
   with patch('core.preview.RUNTIME',p),patch('core.preview.RENDERER',script),patch('core.preview.FONT_DIRS',[]),patch('core.preview.subprocess.run',return_value=subprocess.CompletedProcess([],0,'Test renderer','')):
    c,h=configuration();self.assertEqual(c['renderer_version'],'Test renderer');self.assertEqual(len(h),64)

class CenterUIAcceptance(unittest.TestCase):
 def test_navigation_and_filters_preserve_selection_and_scope(self):
  from streamlit.testing.v1 import AppTest
  at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=25).run()
  click=lambda label:ui_click(at,label)
  try:
   click('使用错误样本');click('确认正文范围');click('开始检查');m=at.session_state['workflow'];scope=deepcopy(m.confirmed);count=m.generation_count
   click('先处理纸张与页边距');self.assertEqual(m.selected,[]);self.assertEqual(m.confirmed,scope);self.assertEqual(count,m.generation_count)
   next(x for x in at.selectbox if x.label=='问题类别').set_value('review').run();self.assertEqual(m.report['summary']['problem_count'],11)
   next(x for x in at.selectbox if x.label=='操作区域').set_value('width').run();self.assertEqual(m.operation,'width');self.assertEqual(m.selected,[]);self.assertFalse(at.exception)
  finally:at.session_state['workflow'].reset()

"""Stage22 supported properties, local evidence, exclusions, exact matching and protection."""
import unittest,json,zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest.mock import patch
from lxml import etree as E
from core import check_document,fix_document,load_rules
from core.package import Package,DemoError,q,NS,sha256
from core.backmatter import TYPES,defaults as back_defaults
from core.back_templates import V6_FIELDS,upgrade,validate,candidate,validate_draft,value
from core.templates import validate_template,compile_template
from core.classification import suggest_paragraph_types
from core.norms import selected_segments
from core.layout import suggest_pagination_aids,apply_pagination_layout
from core.toc import make_scope,correspond
from web.session import WebSession
from ai.academic_spec import parse_requirements
from ai.short_spec import Settings
ROOT=Path(__file__).resolve().parents[1];BAD=ROOT/'samples/backmatter-errors.docx';GOOD=ROOT/'samples/backmatter-correct.docx'
def manifest(p=BAD):return json.loads(p.with_suffix('.types.json').read_text())
class BackmatterAcceptance(unittest.TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def model(self,p=BAD):
  s=WebSession(self.root);s.set_mode('academic');s.load(p.read_bytes(),'synthetic.docx');s.set_types(manifest(p)['paragraph_types']);s.exclude_materials([11,12,13,14,16],'人工确认代码/数据/图表');return s
 def check(self,p=BAD,m=None,c=None):return check_document(p,mode='academic',classification_manifest=m or manifest(p),custom_rules_path=c)
 def custom(self,vals):
  s=self.model();s.start_academic_template();s.upgrade_back_template();s.academic_disable_missing();s.academic_defaults()
  for n,v in vals.items():s.edit_template(n,'manual',v,touched=True)
  s.apply_template();self.assertIsNone(s.template_error);return s
 def fix(self,ids=('R38','R39')):return fix_document(BAD,self.root/'out.docx',None,mode='academic',classification_manifest=manifest(),selected_rules=ids)
 def test_school_correct_and_default_ack_disabled(self):
  r=self.check(GOOD);self.assertFalse([f for f in r['findings'] if f['rule_id'] in ('R38','R39') and f['status']!='pass']);self.assertTrue(all(f['status']=='not_applicable' and 'physical_page' not in f['source'] and f['object_type'] in ('ack_title','ack_text') for f in r['findings'] if f['rule_id'] in ('R40','R41')))
 def test_independent_injected_late_run_properties(self):
  fs=[f for f in self.check()['findings'] if f['rule_id'] in ('R38','R39') and f['status']=='problem'];self.assertEqual(len(fs),14)
  gold=json.loads((ROOT/'samples/backmatter-expected-errors.json').read_text())
  for row in gold['objects']:
   for n in row.get('paragraphs',[row.get('paragraph')]):self.assertEqual({f['locator']['property'] for f in fs if f['locator'].get('paragraph')==n},set(row['properties']))
  self.assertEqual({f['locator'].get('run') for f in fs if f['locator'].get('paragraph')==10},{2})
 def test_optional_absence_not_required(self):
  m=manifest();m['paragraph_types']={n:'other' for n in m['paragraph_types']};r=self.check(m=m);self.assertFalse(any(f['rule_id'] in ('R38','R39','R40','R41') for f in r['findings']))
 def test_defaults_no_invented_properties(self):
  d=back_defaults();self.assertEqual({n:v for n,v in d.items() if n.startswith('appendix_text') and v is not None},{'appendix_text__font_cn':'宋体','appendix_text__font_size':12});self.assertTrue(all(v is None for n,v in d.items() if n.startswith('ack_')))
 def test_suggestion_titles_prose_and_mentions(self):
  rows=suggest_paragraph_types(BAD,include_sections=True)['paragraphs'];self.assertEqual([rows[n-1]['suggested_type'] for n in (8,15,18)],['appendix_title','appendix_title','ack_title']);self.assertNotIn(rows[6]['suggested_type'],TYPES);self.assertTrue(all(rows[n-1]['suggested_type']=='other' for n in (11,12,14,16)));self.assertTrue(rows[8]['ambiguous'])
 def test_legacy_suggestions_do_not_enable_roles(self):self.assertFalse(any(r['suggested_type'] in TYPES for r in suggest_paragraph_types(BAD)['paragraphs']))
 def test_confirmation_required(self):
  m=manifest();m['confirmed']=False
  with self.assertRaises(DemoError):self.check(m=m)
 def test_exact_unselected_xml_and_zip_bytes(self):
  out=self.fix();a,b=Package(BAD),Package(out['output']);self.assertEqual({k:v for k,v in a.parts.items() if k!='word/document.xml'},{k:v for k,v in b.parts.items() if k!='word/document.xml'});self.assertEqual(a.root.xpath('//w:t/text()',namespaces=NS),b.root.xpath('//w:t/text()',namespaces=NS))
  for n in [1,2,3,4,5,6,7,11,12,13,14,16,18,19,20]:self.assertEqual(E.tostring(a.paragraphs[n-1]),E.tostring(b.paragraphs[n-1]))
  self.assertEqual(a.root.xpath('//w:tbl',namespaces=NS)[0].getroottree().getpath(a.root.xpath('//w:tbl',namespaces=NS)[0]),b.root.xpath('//w:tbl',namespaces=NS)[0].getroottree().getpath(b.root.xpath('//w:tbl',namespaces=NS)[0]))
 def test_disk_xml_properties_and_readback(self):
  r=self.fix();p=Package(r['output']);self.assertTrue(all(c['verification']=='pass' for c in r['changes']))
  for n in (8,15):
   x=p.paragraphs[n-1];self.assertEqual(x.find('w:pPr/w:jc',NS).get(q('val')),'center');self.assertEqual(x.find('w:pPr/w:spacing',NS).get(q('line')),'240');self.assertEqual(x.find('w:r/w:rPr/w:sz',NS).get(q('val')),'36')
  self.assertEqual(self.check(Path(r['output']),r['output_classification_manifest'])['findings'],r['after']['findings'])
 def test_partial_only_selected_attribute(self):
  f=next(f for f in self.check()['findings'] if f['rule_id']=='R38' and f['locator'].get('property')=='alignment');r=fix_document(BAD,self.root/'partial.docx',None,mode='academic',classification_manifest=manifest(),selected_keys=[f['key']]);self.assertEqual(len(r['changes']),1);a,b=Package(BAD),Package(r['output']);self.assertEqual(E.tostring(a.paragraphs[7].find(q('r'))),E.tostring(b.paragraphs[7].find(q('r'))));self.assertTrue(any(f['status']=='problem' and f['rule_id']=='R38' for f in r['after']['findings']))
 def test_idempotent_and_original_retained(self):
  old=BAD.read_bytes();r=self.fix();p=Path(r['output']);r2=fix_document(p,self.root/'again.docx',None,mode='academic',classification_manifest=r['output_classification_manifest'],selected_rules=['R38','R39']);self.assertEqual(p.read_bytes(),Path(r2['output']).read_bytes());self.assertEqual(old,BAD.read_bytes())
 def test_all_nine_properties_real_custom(self):
  vals={'appendix_text__font_cn':'楷体','appendix_text__font_western':'Arial','appendix_text__font_size':14,'appendix_text__line_spacing':2,'appendix_text__alignment':'right','appendix_text__before':{'value':.5,'unit':'lines'},'appendix_text__after':{'value':6,'unit':'pt'},'appendix_text__first_line_indent':1,'appendix_text__bold':True,'ack_text__font_size':13}
  s=self.custom(vals);self.assertTrue(s.confirm_and_check(),s.error);s.set_selection([f['key'] for f in s.eligible()]);self.assertTrue(s.generate(),s.error);p=Package(s.result['output']);x=p.paragraphs[8];self.assertEqual(x.find('w:pPr/w:spacing',NS).get(q('beforeLines')),'50');self.assertEqual(x.find('w:pPr/w:spacing',NS).get(q('after')),'120');self.assertEqual(x.find('w:pPr/w:ind',NS).get(q('firstLineChars')),'100');self.assertEqual(x.find('w:r/w:rPr/w:b',NS).get(q('val')),'1');self.assertEqual([(f['rule_id'],f['locator']['paragraph']) for f in s.result['after']['findings'] if f['status']=='problem'],[('R39',10)]);self.assertTrue(s.next_round());s.set_selection([f['key'] for f in s.eligible()]);self.assertTrue(s.generate(),s.error);self.assertEqual(s.result['after']['summary']['problem_count'],0)
 def test_exclusions_block_bulk_and_release_requires_confirmation(self):
  s=self.model();s.batch_types([9,11,12],'appendix_text');self.assertEqual(s.paragraph_types['11'],'other');self.assertEqual(s.paragraph_types['9'],'appendix_text')
  with self.assertRaises(DemoError):s.release_materials([11])
  s.release_materials([11],acknowledged=True);s.batch_types([11],'appendix_text');self.assertEqual(s.paragraph_types['11'],'appendix_text')
 def test_exclusion_changes_invalidate(self):
  s=self.model();s.confirm_and_check();s.exclude_materials([10],'人工排除');self.assertIsNone(s.report);self.assertIsNone(s.confirmed);self.assertFalse(s.selected)
 def test_hash_bound_exclusions_reject_role_conflict(self):
  m=manifest();m['material_exclusions']['8']='代码'
  with self.assertRaises(DemoError):self.check(m=m)
 def test_new_input_clears_exclusions(self):
  s=self.model();s.load(GOOD.read_bytes(),'other.docx');self.assertEqual(s.material_exclusions,{})
 def test_new_round_retains_exclusions(self):
  s=self.model();s.confirm_and_check();s.set_selection([s.eligible()[0]['key']]);s.generate();self.assertTrue(s.next_round());self.assertEqual(s.material_exclusions['11'],'人工确认代码/数据/图表');self.assertEqual(s.classification_confirmed['input_sha256'],sha256(s.input_path.read_bytes()))
 def test_snapshot_draft_and_confirmed_restore_no_api(self):
  s=self.model();s.start_academic_template();s.upgrade_back_template();s.academic_disable_missing();s.academic_defaults();s.edit_template('ack_text__font_size','manual',13,touched=True);s.apply_template();s.confirm_and_check();raw=s.prepare_project();s.stage_project(raw)
  with patch('ai.academic_spec.parse_requirements',side_effect=AssertionError('no API')):n=s.restore_project(acknowledged=True)
  self.assertEqual(n.material_exclusions,s.material_exclusions);self.assertEqual(n.active_template,s.active_template);self.assertEqual(n.report['findings'],s.report['findings']);self.assertNotEqual(n.task_dir,s.task_dir)
 def test_material_draft_project_restore(self):
  s=self.model();s.stage_project(s.prepare_project());n=s.restore_project(acknowledged=True);self.assertEqual(n.material_exclusions,s.material_exclusions);self.assertIsNone(n.confirmed)
 def test_v4_upgrade_all_new_fields_disabled(self):
  from test_academic import template
  old=template();v=upgrade(old,load_rules());self.assertEqual(v['structure_version'],6);self.assertTrue(all(v['final_values'][n] is None for n in back_defaults()));self.assertEqual({n:v['final_values'][n] for n in old['final_values']},old['final_values'])
 def test_old_template_does_not_enable_school_new_rules(self):
  from test_academic import template
  c=self.root/'old.json';c.write_text(json.dumps(template()));r=self.check(c=c);self.assertFalse(any(f['rule_id'] in ('R38','R39','R40','R41') and f['status']!='not_applicable' for f in r['findings']))
 def test_new_template_roundtrip_sources(self):
  s=self.custom({'ack_text__font_size':13});v=s.active_template;self.assertEqual(validate_template(json.loads(s.template_download()),load_rules()),v);self.assertEqual(compile_template(v,load_rules())['back_config']['sources']['ack_text']['font_size']['kind'],'user_confirmed')
 def test_strict_values_and_unknown_field(self):
  for n,v in [('ack_text__font_size',True),('appendix_title__font_size',37),('appendix_text__font_cn','微软雅黑'),('ack_text__line_spacing',float('nan')),('ack_title__alignment','justify'),('ack_text__before',{'value':.5,'unit':'cm'})]:
   with self.subTest(n=n),self.assertRaises(DemoError):value(n,v)
  s=self.custom({});v=deepcopy(s.active_template);v['execute']='bad'
  with self.assertRaises(DemoError):validate(v,load_rules())
 def field(self,n,v,text):
  seg=selected_segments(text);return seg,{'value':v,'unit':V6_FIELDS[n][2],'quote':seg[0]['text'],'location':seg[0]['location'],'support':'supported'}
 def test_ai_new_objects_missing_stays_null(self):
  n='appendix_text__font_size';seg,f=self.field(n,12,'附录正文小四号。');d={n:None for n in V6_FIELDS};d.update(unsupported=[]);d[n]=f;got=validate_draft(d,seg);self.assertIsNone(got['font_size']);self.assertIsNone(got['ack_text__font_size']);self.assertEqual(got[n]['value'],12)
 def test_ai_title_not_heading_or_body(self):
  for text in ('附录 A 正文14pt。','附录A正文14pt。','附 录正文14pt。'):
   seg,f=self.field('font_size',14,text);d={n:None for n in V6_FIELDS};d.update(unsupported=[]);d['font_size']=f
   with self.assertRaises(DemoError):validate_draft(d,seg)
  seg,f=self.field('ack_title__font_size',18,'致谢标题18pt。');self.assertEqual(candidate('ack_title__font_size',f,seg)['value'],18)
  for n in ('heading1_font_size','font_size','abstract_cn_title__font_size'):
   from core.templates import validate_draft as vd
   d={n:None for n in V6_FIELDS};d.update(unsupported=[]);d[n]=f
   with self.assertRaises(DemoError):vd(d,seg)
 def test_ai_conflict_and_fake_quote_rejected(self):
  n='appendix_text__font_size';seg,f=self.field(n,12,'附录正文12pt。\n附录正文14pt。')
  with self.assertRaises(DemoError):candidate(n,f,seg)
  seg,f=self.field(n,12,'附录正文12pt。');f['quote']='附录正文14pt。'
  with self.assertRaises(DemoError):candidate(n,f,seg)
 def test_ai_code_scope_not_authorization(self):
  n='appendix_text__font_size';seg,f=self.field(n,12,'附录正文12pt。\n附录均为代码。')
  with self.assertRaises(DemoError):candidate(n,f,seg)
 def test_mock_api_payload_only_selected_norm(self):
  text='附录标题20pt。';seg,f=self.field('appendix_title__font_size',20,text);d={n:None for n in V6_FIELDS};d.update(unsupported=[]);d['appendix_title__font_size']=f;calls=[]
  def tx(req,t):
   payload=json.loads(req.data);calls.append(payload);self.assertIn('附录标题20pt',payload['messages'][1]['content']);self.assertNotIn('def demo',json.dumps(payload));return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(d,ensure_ascii=False)}}]}).encode()
  out=parse_requirements(seg,include_tables=True,include_backmatter=True,config=Settings('mock-only-key'),transport=tx);self.assertEqual(len(calls),1);self.assertEqual(out['receipt']['kind'],'mock_api');self.assertEqual(out['draft']['appendix_title__font_size']['value'],20)
 def test_toc_targets_include_optional_titles(self):
  m=manifest();sc=make_scope(BAD);sc.update(confirmed=True,objects={'d:4':'level1','d:5':'level1','d:6':'level1'},complete=True,headings_complete=True);m['toc_scope']=sc;r=self.check(m=m);self.assertEqual([x['status'] for x in r['toc']['rows']],['pass','pass','review'])
 def test_toc_duplicate_title_not_guessed(self):
  p=self.root/'duplicate.docx';pkg=Package(BAD);pkg.paragraphs[14].find('w:r/w:t',NS).text='附录A 文字说明';p.write_bytes(pkg.bytes(True));m=manifest();m['input_sha256']=sha256(p.read_bytes());sc=make_scope(p);sc.update(confirmed=True,objects={'d:4':'level1'},complete=False,headings_complete=False);m['toc_scope']=sc;r=self.check(p,m);self.assertEqual(r['toc']['rows'][0]['status'],'review');self.assertFalse(r['toc']['missing_candidates'])
 def test_l03_safe_matching_and_code_blocked(self):
  rows=suggest_pagination_aids(BAD,manifest())['pairs'];safe={r['paragraph']:r for r in rows if r.get('id')=='L03'};self.assertEqual(safe[8]['status'],'available');self.assertEqual(safe[18]['status'],'available');self.assertEqual(safe[15]['status'],'review')
 def test_l03_no_format_or_material_changes(self):
  inv=suggest_pagination_aids(BAD,manifest());key=next(r['key'] for r in inv['pairs'] if r.get('paragraph')==18 and r['status']=='available');r=apply_pagination_layout(BAD,self.root/'adjacent.docx',None,classification_manifest=manifest(),confirmed_keys=[key],mode='academic');a,b=Package(BAD),Package(r['output']);self.assertEqual([E.tostring(x) for x in a.paragraphs[17].findall(q('r'))],[E.tostring(x) for x in b.paragraphs[17].findall(q('r'))]);self.assertEqual(b.paragraphs[17].find('w:pPr/w:keepNext',NS).get(q('val')),'1');self.assertEqual(E.tostring(a.paragraphs[18]),E.tostring(b.paragraphs[18]))
 def test_two_sessions_do_not_share_exclusions(self):
  a=self.model();b=self.model(GOOD);a.exclude_materials([10],'额外排除');self.assertNotIn('10',b.material_exclusions);self.assertNotEqual(a.task_dir,b.task_dir)
 def test_full_exports_contain_new_records(self):
  s=self.model();s.confirm_and_check();s.set_selection([s.eligible()[0]['key']]);s.generate();data=s.prepare_reading_export();self.assertTrue(any(b'R38' in b for b in data.values()));self.assertTrue(s.result_package())
 def altered(self,fn):
  p=self.root/'altered.docx';pkg=Package(BAD);fn(pkg);p.write_bytes(pkg.bytes(True));m=manifest();m['input_sha256']=sha256(p.read_bytes());return p,m
 def test_special_superscript_only_protected_run(self):
  def change(pkg):
   r=pkg.paragraphs[8].find(q('r'));rp=r.find(q('rPr'));e=E.SubElement(rp,q('vertAlign'));e.set(q('val'),'superscript')
  p,m=self.altered(change);r=self.check(p,m);self.assertTrue(any(n['locator'].get('paragraph')==9 for n in r['coverage_notes']));self.assertFalse(any(f['fixable'] and f['locator'].get('paragraph')==9 for f in r['findings']));self.assertTrue(any(f['fixable'] and f['locator'].get('paragraph')==17 for f in r['findings']))
 def test_hyperlink_not_flattened_or_fixed(self):
  def change(pkg):
   p=pkg.paragraphs[8];h=E.SubElement(p,q('hyperlink'));h.set(q('anchor'),'demo');h.append(p.find(q('r')))
  p,m=self.altered(change);r=self.check(p,m);self.assertTrue(any(f['status']=='review' and f['rule_id']=='R39' and f['locator'].get('paragraph')==9 for f in r['findings']))
 def test_theme_font_resolves_and_source_retained(self):
  def change(pkg):
   r=pkg.paragraphs[8].find(q('r'));f=r.find('w:rPr/w:rFonts',NS);f.attrib.pop(q('eastAsia'),None);f.set(q('eastAsiaTheme'),'minorEastAsia')
  p,m=self.altered(change);r=self.check(p,m);f=next(f for f in r['findings'] if f['rule_id']=='R39' and f['locator'].get('paragraph')==9 and f['locator'].get('property')=='font_eastAsia');self.assertIn('font_evidence',f);self.assertIn(f['status'],('problem','review','pass'));self.assertTrue('theme' in str(f['font_evidence']).lower())
 def test_ai_editor_changed_value_sources_not_exact_quote(self):
  s=self.model();seg,f=self.field('ack_text__font_size',12,'致谢正文12pt。');d={n:None for n in V6_FIELDS};d.update(unsupported=[]);d['ack_text__font_size']=f;s.set_norm_text('致谢正文12pt。');s.confirm_norm_text();self.assertTrue(s.parse_template(parser=lambda _: {'draft':d,'receipt':{'kind':'mock_api','model':'deepseek-flash','timestamp_utc':'2026-10-15T00:00:00+00:00'}}));s.academic_disable_missing();s.academic_defaults();s.edit_template('ack_text__font_size','manual',13,touched=True);v=s.proposed_template();self.assertEqual(v['field_sources']['ack_text__font_size'],{'kind':'user_confirmed','quote':'致谢正文12pt。','location':'摘录:L1'});self.assertEqual(v['final_values']['ack_text__font_size'],13)
  from streamlit.testing.v1 import AppTest
  app=AppTest.from_string("from pathlib import Path\nimport streamlit as st\nfrom web.academic_ui import render_academic_templates\nrender_academic_templates(st.session_state['model'],Path.cwd())")
  app.session_state['model']=s;app.run();g=s.template_generation
  self.assertFalse(app.exception);app.selectbox(key=f'academic-field-{g}-ack_text').set_value('ack_text__font_size').run();self.assertFalse(app.exception)
  app.number_input(key=f'academic-value-{g}-ack_text__font_size').set_value(13.5).run();self.assertFalse(app.exception);self.assertEqual(app.selectbox(key=f'academic-mode-{g}-ack_text__font_size').value,'manual');self.assertEqual(s.proposed_template()['field_sources']['ack_text__font_size']['kind'],'user_confirmed')
 def test_switch_template_invalidates_old_new_object_results(self):
  s=self.model();s.confirm_and_check();s.set_selection([s.eligible()[0]['key']]);s.generate();s.start_academic_template();s.upgrade_back_template();s.academic_disable_missing();s.academic_defaults();s.apply_template();self.assertIsNone(s.report);self.assertIsNone(s.result);self.assertFalse(s.selected);self.assertIsNone(s.confirmed)
 def test_exclusions_validate_reason_and_current_ids(self):
  s=self.model()
  for nums,reason in [([999],'代码'),([8],'bad\nreason'),([True],'代码')]:
   with self.assertRaises(DemoError):s.exclude_materials(nums,reason)
 def test_restore_initial_suggestions_cannot_remove_material_locks(self):
  s=self.model();s.batch_types([9],'other');s.restore_types(confirmed=True);self.assertEqual(s.paragraph_types['11'],'other');self.assertIn('11',s.material_exclusions)
 def test_invalid_source_types_rejected(self):
  s=self.custom({'ack_text__font_size':13});v=deepcopy(s.active_template);v['field_sources']['ack_text__font_size']['kind']=[]
  with self.assertRaises(DemoError):validate(v,load_rules())
 def test_default_policy_change_invalidates_cache_and_report(self):
  from core.backmatter import PATH
  s=self.model();s.confirm_and_check();old=s.report['rules']['backmatter_sha256'];raw=s.prepare_project();
  from io import BytesIO
  with zipfile.ZipFile(BytesIO(raw)) as z:self.assertEqual(json.loads(z.read('project.json'))['state']['scope']['backmatter_policy_sha256'],old)
  p=self.root/'new-policy.json';d=json.loads(PATH.read_bytes());d['version']='changed';p.write_text(json.dumps(d,ensure_ascii=False))
  with patch('core.backmatter.PATH',p):
   with self.assertRaises(DemoError):s._current()
   self.assertIsNone(s.report);self.assertTrue(s.confirm_and_check(),s.error);self.assertNotEqual(s.report['rules']['backmatter_sha256'],old)
 def test_unknown_unicode_new_object_reviews_without_crash(self):
  def change(pkg):pkg.paragraphs[8].find('w:r/w:t',NS).text+=' العربية'
  p,m=self.altered(change);c=self.custom({'appendix_text__font_cn':'宋体'});r=self.check(p,m,c.custom_rules_path);self.assertTrue(any(f['rule_id']=='R39' and f['status']=='review' for f in r['findings']))
 def test_package_includes_actual_default_backmatter_policy(self):
  from io import BytesIO
  from core.backmatter import PATH
  s=self.model();s.confirm_and_check();s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R38']);self.assertTrue(s.generate(),s.error)
  with zipfile.ZipFile(BytesIO(s.result_package())) as z:self.assertEqual(z.read('backmatter-rules.json'),PATH.read_bytes());self.assertEqual(z.read('fixed.docx'),Path(s.result['output']).read_bytes())

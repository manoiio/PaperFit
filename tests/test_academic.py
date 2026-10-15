"""Stage15 actual properties, sources, preservation and snapshot acceptance. No real API."""
import unittest,json,zipfile,math
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest.mock import patch
from lxml import etree as E
from core import check_document,fix_document,load_rules,effective_rules
from core.package import Package,q,NS,DemoError,sha256
from core.engine import _ensure
from core.classification import suggest_paragraph_types
from core.academic_rules import FIELDS as EXTRA,flat_defaults
from core.academic_templates import V4_FIELDS,value,make,validate_draft,validate_candidate
from core.templates import defaults,make_template,validate_template,compile_template
from core.norms import selected_segments
from core.formats import Resolver,Unresolved
from core.paragraph_properties import space,bold,alignment
from core.report import markdown
from web.session import WebSession
from web.issues import project
from ai.academic_spec import parse_requirements
from ai.short_spec import Settings
ROOT=Path(__file__).resolve().parents[1]
GOOD=ROOT/'samples/academic-correct.docx';BAD=ROOT/'samples/academic-errors.docx'
MANIFEST=json.loads(GOOD.with_suffix('.types.json').read_text())
def template(extra=None):
 base=load_rules();base_template=make_template('用户确认的单文档演示规则',defaults(base,extended=True),{n:{'kind':'default_inherited','quote':'','location':None} for n in __import__('core.templates',fromlist=['ALL_FIELDS']).ALL_FIELDS},[],base)
 vals=flat_defaults();src={n:{'kind':'default_inherited' if v is not None else 'not_enabled','quote':'','location':None} for n,v in vals.items()}
 for n,v in (extra or {}).items():vals[n]=v;src[n]={'kind':'user_confirmed' if v is not None else 'not_enabled','quote':'','location':None}
 return make(base_template,vals,src,[],base)
class AcademicAcceptance(unittest.TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def check(self,p=GOOD,manifest=None,custom=None):
  m=manifest or deepcopy(MANIFEST);m['input_sha256']=sha256(Path(p).read_bytes());args={'mode':'academic','classification_manifest':m}
  if custom:args['custom_rules_path']=custom
  return check_document(p,**args)
 def altered(self,fn):
  p=self.root/'input.docx';p.write_bytes(GOOD.read_bytes());pkg=Package(p);fn(pkg);pkg.parts['word/styles.xml']=E.tostring(pkg.styles,xml_declaration=True,encoding='UTF-8',standalone=True);p.write_bytes(pkg.bytes(True));return p
 def config(self,changes):
  p=self.root/'template.json';p.write_text(json.dumps(template(changes),ensure_ascii=False));return p
 def model(self,error=True):
  s=WebSession(self.root);s.set_mode('academic');s.load((BAD if error else GOOD).read_bytes(),'software.docx');s.set_types(MANIFEST['paragraph_types']);self.assertTrue(s.confirm_and_check(),s.error);return s
 def test_correct_control_all_22_rules_no_problem_review(self):
  r=self.check();self.assertEqual((r['summary']['rule_count'],r['summary']['problem_count'],r['summary']['review_count']),(22,0,0))
 def test_error_list_independent_exact_properties_and_count(self):
  r=self.check(BAD);gold=json.loads((ROOT/'samples/academic-expected-errors.json').read_text());problems=[f for f in r['findings'] if f['status']=='problem'];self.assertEqual(len(problems),gold['expected_problem_records']);self.assertEqual(r['summary']['review_count'],0)
  for item in gold['objects']:
   if 'paragraphs' in item:
    for p in item['paragraphs']:
     self.assertEqual({f['locator']['property'] for f in problems if f['locator'].get('paragraph')==p},set(item['properties']))
   else:
    fs=[f for f in problems if f['locator'].get('paragraph')==item['paragraph'] and f['locator'].get('property')==item['property']];self.assertTrue(fs,item)
    if 'run' in item:self.assertEqual(fs[0]['locator']['run'],item['run'])
    if item['property'] in ('alignment','size','bold','font_eastAsia'):self.assertTrue(all(f['expected']==item['expected'] for f in fs))
 def test_types_normal_and_numeric_not_title(self):
  rows=suggest_paragraph_types(GOOD,include_sections=True)['paragraphs'];look={r['index']:r['suggested_type'] for r in rows}
  self.assertEqual({n:look[n] for n in (3,4,5,6,7,8,18,19,20,21)},{n:MANIFEST['paragraph_types'][str(n)] for n in (3,4,5,6,7,8,18,19,20,21)});self.assertEqual(look[12],'body');self.assertEqual(look[14],'body');self.assertEqual(look[10],'body')
 def test_same_text_old_algorithm_remains_excluded(self):
  rows=suggest_paragraph_types(GOOD)['paragraphs'];self.assertNotEqual(rows[2]['suggested_type'],'abstract_cn_title')
 def test_abstract_not_checked_as_body(self):
  r=self.check(BAD);self.assertFalse(any(f['rule_id'] in ('R03','R04','R05','R06','R07') and f['locator'].get('paragraph') in (4,7,19,20,21) for f in r['findings']))
 def test_unmentioned_bold_and_ref_indent_not_enabled(self):
  r=self.check();self.assertFalse(any(f.get('property')=='加粗' and f['object_type']!='keywords_en' for f in r['findings']));self.assertFalse(any(f['rule_id']=='R21' and f['locator'].get('property')=='first_line_indent' for f in r['findings']))
 def test_partial_keyword_label_cross_runs_contents_keep(self):
  r=self.check(BAD);selected=[f['key'] for f in r['findings'] if f['rule_id']=='R18' and f['locator'].get('part')=='label' and f['fixable']];out=fix_document(BAD,self.root/'fixed.docx',None,mode='academic',classification_manifest=json.loads(BAD.with_suffix('.types.json').read_text()),selected_keys=selected)
  self.assertEqual(len(out['changes']),2);self.assertTrue(all(c['verification']=='pass' for c in out['changes']));self.assertTrue(any(f['rule_id']=='R18' and f['locator'].get('part')=='content' and f['status']=='problem' for f in out['after']['findings']));self.assertTrue(out['preservation']['document_except_selected_format_attributes_equal'])
 def test_keyword_same_run_label_bold_split_not_content(self):
  r=self.check(BAD);f=next(f for f in r['findings'] if f['rule_id']=='R19' and f['fixable']);out=fix_document(BAD,self.root/'fixed.docx',None,mode='academic',classification_manifest=json.loads(BAD.with_suffix('.types.json').read_text()),selected_keys=[f['key']]);p=Package(out['output']).paragraphs[7];runs=p.findall(q('r'));self.assertEqual(''.join(p.xpath('.//w:t/text()',namespaces=NS)),'Keywords: synthetic document; paragraph format; human review');self.assertEqual(runs[0].find('w:rPr/w:b',NS).get(q('val')),'1');self.assertEqual(runs[1].find('w:rPr/w:b',NS).get(q('val')),'0')
 def test_style_inheritance_and_late_run_checked(self):
  r=self.check(BAD);self.assertTrue(any(f['locator'].get('paragraph')==4 and f['locator'].get('run')==2 and f['status']=='problem' for f in r['findings']));f=next(f for f in r['findings'] if f['rule_id']=='R21' and f['locator'].get('property')=='font_eastAsia');self.assertIn('DemoReference',str(f['font_evidence']))
 def test_all_selected_save_readback_and_media_parts_preserved(self):
  s=self.model();old=s.input_path.read_bytes();s.set_selection([f['key'] for f in s.eligible()]);self.assertTrue(s.generate(),s.error);self.assertEqual(s.result['after']['summary']['problem_count'],0);self.assertEqual(s.result['after']['summary']['review_count'],0);self.assertEqual(old,s.input_path.read_bytes());a=Package(s.input_path);b=Package(s.result['output']);self.assertEqual({k:v for k,v in a.parts.items() if k!='word/document.xml'},{k:v for k,v in b.parts.items() if k!='word/document.xml'});r=check_document(s.result['output'],mode='academic',classification_manifest=s.result['output_classification_manifest']);self.assertEqual(r['findings'],s.result['after']['findings'])
 def test_second_round_preserves_first_and_original(self):
  s=self.model();original=s.input_path.read_bytes();s.set_selection([s.eligible()[0]['key']]);s.generate();first=Path(s.result['output']);raw=first.read_bytes();self.assertTrue(s.next_round());s.set_selection([f['key'] for f in s.eligible()]);self.assertTrue(s.generate());self.assertEqual(s.result['after']['summary']['problem_count'],0);self.assertEqual(first.read_bytes(),raw);self.assertEqual(s.original_path.read_bytes(),original)
 def test_idempotent_fix_writes_same_bytes_when_no_problems(self):
  out=fix_document(GOOD,self.root/'fixed.docx',None,mode='academic',classification_manifest=MANIFEST,selected_rules=['R14']);self.assertEqual(Path(out['output']).read_bytes(),GOOD.read_bytes())
 def test_auto_spacing_review_not_fixable(self):
  p=self.altered(lambda pkg:_ensure(_ensure(pkg.paragraphs[2],'pPr'),'spacing').set(q('beforeAutospacing'),'1'));r=self.check(p);f=next(f for f in r['findings'] if f['rule_id']=='R14' and f['locator'].get('property')=='before');self.assertEqual((f['status'],f['fixable']),('review',False))
 def test_spacing_conflict_review_not_pass(self):
  p=self.altered(lambda pkg:_ensure(_ensure(pkg.paragraphs[2],'pPr'),'spacing').set(q('before'),'120'));r=self.check(p);self.assertTrue(any(f['status']=='review' and '冲突' in f['detail'] for f in r['findings']))
 def test_missing_spacing_not_zero(self):
  def fn(pkg):
   for pp in [pkg.paragraphs[2].find(q('pPr')),*pkg.styles.findall('w:style/w:pPr',NS),*pkg.styles.findall('w:docDefaults/w:pPrDefault/w:pPr',NS)]:
    for e in pp.findall(q('spacing')):
     for a in ('before','beforeLines','beforeAutospacing'):e.attrib.pop(q(a),None)
  r=self.check(self.altered(fn));self.assertTrue(any(f['rule_id']=='R14' and f['locator'].get('property')=='before' and f['status']=='review' for f in r['findings']))
 def test_explicit_zero_spacing_units_equivalent(self):
  custom=self.config({'abstract_cn_body__before':{'value':0,'unit':'pt'}});r=self.check(custom=custom);self.assertTrue(any(f['locator'].get('paragraph')==4 and f['locator'].get('property')=='before' and f['status']=='pass' for f in r['findings']))
  # Correctly inherited absence remains review, not automatic zero.
 def test_invalid_values_strict(self):
  for n,v in [('abstract_cn_title__font_size',True),('abstract_cn_title__font_size',37),('body__before',{'value':.5,'unit':'cm'}),('body__before',{'value':6.1,'unit':'pt'}),('body__bold','true'),('reference_item__line_spacing',float('nan')),('reference_item__first_line_indent',3),('abstract_en_body__font_western','Unknown')]:
   with self.subTest(n=n,v=v),self.assertRaises(DemoError):value(n,v)
 def test_v4_template_export_import_same_sources_and_rules(self):
  data=template({'abstract_cn_title__font_size':20,'keywords_cn__label_bold':True});validated=validate_template(json.loads(json.dumps(data)),load_rules());self.assertEqual(data,validated);self.assertEqual(compile_template(data,load_rules())['academic_config']['objects']['abstract_cn_title']['font_size'],20)
 def test_old_template_has_no_new_policy_in_academic_mode(self):
  base=__import__('core.academic_templates',fromlist=['base_v3']).base_v3(template());p=self.root/'old.json';p.write_text(json.dumps(base));r=self.check(custom=p);self.assertFalse(any(f['rule_id'] in ('R14','R15','R16','R17','R18','R19','R20','R21','R22') and f['status']!='not_applicable' for f in r['findings']))
 def test_new_custom_values_actually_change_properties(self):
  c=self.config({'abstract_cn_body__font_size':14,'abstract_cn_body__before':{'value':6,'unit':'pt'},'abstract_cn_body__alignment':'left','abstract_cn_body__bold':True,'reference_item__first_line_indent':0});r=self.check(custom=c);keys=[f['key'] for f in r['findings'] if f['fixable']];out=fix_document(GOOD,self.root/'fixed.docx',None,mode='academic',custom_rules_path=c,classification_manifest=MANIFEST,selected_keys=keys);self.assertEqual(out['after']['summary']['problem_count'],0);self.assertEqual(out['after']['summary']['review_count'],0);p=Package(out['output']).paragraphs[3];self.assertEqual(p.find('w:pPr/w:spacing',NS).get(q('before')),'120');self.assertTrue(all(r.find('w:rPr/w:sz',NS).get(q('val'))=='28' for r in p.findall(q('r'))));self.assertEqual(p.find('w:pPr/w:jc',NS).get(q('val')),'left')
 def test_content_counts_and_numbering_nonfixable(self):
  def fn(pkg):pkg.paragraphs[20].find('w:r/w:t',NS).text='[2] 软件演示条目重复'
  r=self.check(self.altered(fn));f=next(f for f in r['findings'] if f['rule_id']=='R22' and f['locator'].get('property')=='参考文献手工编号');self.assertEqual((f['status'],f['fixable']),('problem',False));self.assertFalse(any(f['rule_id']=='R22' and f['fixable'] for f in r['findings']))
 def test_empty_missing_section_is_review_no_generated_text(self):
  m=deepcopy(MANIFEST);m['paragraph_types']['4']='other';r=self.check(manifest=m);self.assertTrue(any(f['rule_id']=='R22' and f['status']=='review' for f in r['findings']))
 def test_hyperlink_complex_keyword_not_split(self):
  def fn(pkg):
   p=pkg.paragraphs[4];link=E.Element(q('hyperlink'));link.append(p.findall(q('r'))[-1]);p.append(link)
  r=self.check(self.altered(fn));self.assertTrue(any(f['rule_id']=='R18' and f['status']=='review' and not f['fixable'] for f in r['findings']))
 def test_font_slots_independent(self):
  c=self.config({'abstract_cn_body__font_western':'Arial'});r=self.check(custom=c);self.assertTrue(all(f['expected']=='宋体' for f in r['findings'] if f['rule_id']=='R15' and f['locator'].get('property')=='font_eastAsia'))
 def test_template_switch_scope_and_download_invalidate(self):
  s=self.model();s.set_selection([s.eligible()[0]['key']]);s.generate();self.assertTrue(s.downloads());s.import_template(json.dumps(template()).encode());s.apply_template();self.assertIsNone(s.report);self.assertIsNone(s.confirmed);self.assertIsNone(s.result);self.assertFalse(s.selected)
 def test_new_classification_change_invalidates(self):
  s=self.model();s.batch_types([4],'other');self.assertIsNone(s.report);self.assertIsNone(s.confirmed)
 def test_snapshot_preserves_v4_types_sources_rechecks_no_api(self):
  s=self.model();s.import_template(json.dumps(template()).encode());s.apply_template();s.confirm_and_check();s.set_selection([s.eligible()[0]['key']]);s.generate();s.next_round();raw=s.prepare_project();s.stage_project(raw)
  with patch('ai.academic_spec.parse_requirements',side_effect=AssertionError('No API')):n=s.restore_project(acknowledged=True)
  self.assertEqual(n.active_template,s.active_template);self.assertEqual(n.paragraph_types,s.paragraph_types);self.assertEqual(n.report['findings'],s.report['findings'])
 def test_two_sessions_do_not_share_new_configs(self):
  s=self.model();t=WebSession(self.root);t.set_mode('academic');t.load(GOOD.read_bytes(),'software.docx');s.import_template(json.dumps(template({'abstract_cn_title__font_size':20})).encode());s.apply_template();self.assertIsNone(t.active_template);self.assertNotEqual(t.task_dir,s.task_dir)
 def test_full_exports_and_package_include_new_results(self):
  s=self.model();s.set_selection([f['key'] for f in s.eligible()]);s.generate();b=s.current_bundle();self.assertTrue(any(r['raw'].get('rule_id')=='R19' for r in b['projection']['records']));self.assertIn('R22',markdown(s.result['after']));raw=s.result_package();self.assertTrue(raw)
 def test_ai_missing_stays_null_and_object_evidence(self):
  segments=selected_segments('中文摘要正文小四号，1.5倍行距。\n英文关键词标签Times New Roman12pt，加粗。');d={n:None for n in V4_FIELDS};d['unsupported']=[]
  for n,v in [('abstract_cn_body__font_size',12),('abstract_cn_body__line_spacing',1.5),('keywords_en__label_bold',True)]:
   seg=segments[1] if n.startswith('keywords') else segments[0];d[n]={'value':v,'unit':V4_FIELDS[n][2],'quote':seg['text'],'location':seg['location'],'support':'supported'}
  self.assertIsNone(validate_draft(d,segments)['font_size']);response=parse_requirements(segments,config=Settings('mock-only-key'),transport=lambda req,t:json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(d,ensure_ascii=False)}}]}).encode());self.assertEqual(response['receipt']['kind'],'mock_api')
 def test_ai_wrong_object_forged_quote_unknown_field_refused(self):
  segments=selected_segments('中文摘要正文12pt。');f={'value':12,'unit':'pt','quote':segments[0]['text'],'location':segments[0]['location'],'support':'supported'}
  with self.assertRaises(DemoError):validate_candidate('reference_item__font_size',f,segments)
  with self.assertRaises(DemoError):validate_candidate('abstract_cn_body__font_size',{**f,'quote':'中文摘要正文14pt'},segments)
  d={n:None for n in V4_FIELDS};d.update(unsupported=[],execute='bad')
  with self.assertRaises(DemoError):validate_draft(d,segments)
 def test_ai_keyword_whole_bold_not_label(self):
  segments=selected_segments('英文关键词加粗。');f={'value':True,'unit':'bool','quote':segments[0]['text'],'location':segments[0]['location'],'support':'supported'}
  with self.assertRaises(DemoError):validate_candidate('keywords_en__label_bold',f,segments)
 def test_ai_conflicts_not_choose_last_and_small_four_exact(self):
  segments=selected_segments('中文摘要正文12pt。\n中文摘要正文14pt。');f={'value':14,'unit':'pt','quote':segments[1]['text'],'location':segments[1]['location'],'support':'supported'}
  with self.assertRaises(DemoError):validate_candidate('abstract_cn_body__font_size',f,segments)
  segments=selected_segments('中文摘要正文小四号。');f.update(quote=segments[0]['text'],location=segments[0]['location'])
  with self.assertRaises(DemoError):validate_candidate('abstract_cn_body__font_size',f,segments)
 def test_ai_spacing_not_converted_to_pt(self):
  segments=selected_segments('中文摘要标题段前0.5行。');f={'value':{'value':6,'unit':'pt'},'unit':'spacing','quote':segments[0]['text'],'location':segments[0]['location'],'support':'supported'}
  with self.assertRaises(DemoError):validate_candidate('abstract_cn_title__before',f,segments)
  f['value']={'value':.5,'unit':'lines'};self.assertEqual(validate_candidate('abstract_cn_title__before',f,segments)['value']['unit'],'lines')
 def test_api_failure_default_still_checks(self):
  s=self.model(False);s.set_norm_text('中文摘要正文12pt。');s.confirm_norm_text();self.assertFalse(s.parse_template(parser=lambda segments:(_ for _ in ()).throw(DemoError('模拟超时'))));self.assertTrue(s.confirm_and_check());self.assertEqual(s.report['summary']['problem_count'],0)

 def test_selected_spacing_only_retains_unselected_bold_alignment_and_line(self):
  c=self.config({'body__before':{'value':6,'unit':'pt'},'body__bold':True});r=self.check(custom=c);fs=[f for f in r['findings'] if f['rule_id']=='R13' and f['locator'].get('property')=='before' and f['fixable']];out=fix_document(GOOD,self.root/'partial.docx',None,mode='academic',classification_manifest=MANIFEST,custom_rules_path=c,selected_keys=[f['key'] for f in fs]);self.assertTrue(all(x['verification']=='pass' for x in out['changes']));self.assertTrue(any(f['rule_id']=='R13' and f['locator'].get('property')=='bold' and f['status']=='problem' for f in out['after']['findings']));self.assertTrue(out['preservation']['document_except_selected_format_attributes_equal'])
 def test_inherited_spacing_and_alignment_effective(self):
  pkg=Package(GOOD);r=Resolver(pkg);p=pkg.paragraphs[3];layers=r.layers(p,kind='pPr');self.assertEqual(space(r,layers,'before')['value'],0);self.assertEqual(alignment(r,layers),'both')
 def test_zero_in_lines_lands_without_changing_line_spacing(self):
  c=self.config({'abstract_cn_title__before':{'value':0,'unit':'lines'}});r=self.check(custom=c);f=next(f for f in r['findings'] if f['rule_id']=='R14' and f['locator'].get('property')=='before');out=fix_document(GOOD,self.root/'zero.docx',None,mode='academic',classification_manifest=MANIFEST,custom_rules_path=c,selected_keys=[f['key']]);pp=Package(out['output']).paragraphs[2].find('w:pPr/w:spacing',NS);self.assertEqual(pp.get(q('beforeLines')),'0');self.assertEqual(pp.get(q('line')),'240')
 def test_bold_direct_and_style_error_after_half(self):
  def fn(pkg):
   _ensure(_ensure(pkg.paragraphs[3].findall(q('r'))[1],'rPr'),'b').set(q('val'),'1')
  p=self.altered(fn);c=self.config({'abstract_cn_body__bold':False});r=self.check(p,custom=c);bad=[f for f in r['findings'] if f['rule_id']=='R15' and f['locator'].get('property')=='bold' and f['status']=='problem'];self.assertEqual(len(bad),1);self.assertEqual(bad[0]['locator']['run'],2)
 def test_numbered_reference_keeps_numbering_and_still_checks_text(self):
  def fn(pkg):
   num=_ensure(_ensure(pkg.paragraphs[18],'pPr'),'numPr');_ensure(num,'numId').set(q('val'),'1');_ensure(num,'ilvl').set(q('val'),'0');_ensure(_ensure(pkg.paragraphs[18].findall(q('r'))[0],'rPr'),'sz').set(q('val'),'20')
  p=self.altered(fn);r=self.check(p);f=next(f for f in r['findings'] if f['rule_id']=='R21' and f['locator'].get('property')=='size' and f['status']=='problem');out=fix_document(p,self.root/'numbered.docx',None,mode='academic',classification_manifest={**MANIFEST,'input_sha256':sha256(p.read_bytes())},selected_keys=[f['key']]);self.assertEqual(Package(p).parts['word/numbering.xml'],Package(out['output']).parts['word/numbering.xml']);self.assertEqual(E.tostring(Package(p).paragraphs[18].find('w:pPr/w:numPr',NS)),E.tostring(Package(out['output']).paragraphs[18].find('w:pPr/w:numPr',NS)));self.assertTrue(any(f['rule_id']=='R21' and f['locator'].get('property')=='line_spacing' and f['status']=='review' for f in out['after']['findings']))
 def test_keyword_link_preserved_during_other_safe_fix(self):
  def fn(pkg):
   p=pkg.paragraphs[4];link=E.Element(q('hyperlink'));link.append(p.findall(q('r'))[-1]);p.append(link);_ensure(_ensure(pkg.paragraphs[3].findall(q('r'))[1],'rPr'),'sz').set(q('val'),'28')
  p=self.altered(fn);r=self.check(p);f=next(f for f in r['findings'] if f['rule_id']=='R15' and f['status']=='problem');out=fix_document(p,self.root/'linked.docx',None,mode='academic',classification_manifest={**MANIFEST,'input_sha256':sha256(p.read_bytes())},selected_keys=[f['key']]);self.assertEqual(E.tostring(Package(p).paragraphs[4]),E.tostring(Package(out['output']).paragraphs[4]))
 def test_point_indent_dependency_and_next_round_cause(self):
  def fn(pkg):
   p=pkg.paragraphs[3];e=_ensure(_ensure(p,'pPr'),'ind');e.set(q('firstLine'),'480');e.attrib.pop(q('firstLineChars'),None)
   # Remove inherited character ind for this fixture only.
   for e in pkg.styles.findall('w:style/w:pPr/w:ind',NS):e.attrib.pop(q('firstLineChars'),None)
  p=self.altered(fn);c=self.config({'abstract_cn_body__font_size':14});r=self.check(p,custom=c);self.assertTrue(r['modification_dependencies']);fs=[f['key'] for f in r['findings'] if f['rule_id']=='R15' and f['locator'].get('property')=='size' and f['fixable']];out=fix_document(p,self.root/'point.docx',None,mode='academic',classification_manifest={**MANIFEST,'input_sha256':sha256(p.read_bytes())},custom_rules_path=c,selected_keys=fs);self.assertTrue(any('点值缩进' in d['detail'] for d in out['problem_delta']['new_problem_causes']))
 def test_duplicate_spacing_and_malformed_bold_review(self):
  def fn(pkg):
   pp=pkg.paragraphs[2].find(q('pPr'));pp.append(deepcopy(pp.find(q('spacing'))));_ensure(_ensure(pkg.paragraphs[7].findall(q('r'))[0],'rPr'),'b').set(q('val'),'maybe')
  r=self.check(self.altered(fn));self.assertTrue(any(f['locator'].get('paragraph')==3 and f['status']=='review' for f in r['findings']));self.assertTrue(any(f['locator'].get('paragraph')==8 and f['status']=='review' for f in r['findings']))

 def test_keyword_cross_run_selector_labels_are_unique(self):
  from web.presentation import position,fmt
  r=self.check(BAD);fs=[f for f in r['findings'] if f['fixable']];labels=[f["rule_id"]+position(f['locator'])+fmt(f['actual'],f['rule_id']) for f in fs];self.assertEqual(len(labels),len(set(labels)));kw=[position(f['locator']) for f in fs if f['rule_id']=='R18' and f['locator'].get('part')=='label'];self.assertIn('字符1–1',kw[0]);self.assertIn('字符2–4',kw[1])

 def test_invalid_unhashable_enums_and_extreme_numbers(self):
  for n,v in [('body__alignment',[]),('body__alignment',{}),('abstract_cn_body__font_cn',[]),('abstract_en_body__font_western',{}),('reference_item__font_size',10**1000)]:
   with self.subTest(field=n),self.assertRaises(DemoError):value(n,v)

 def test_v4_versions_unknown_field_and_disabled_provenance(self):
  data=template();base=load_rules()
  for change in (lambda d:d.update(structure_version=4.0),lambda d:d['final_values'].update(run_code=True),lambda d:d['field_sources']['abstract_cn_body__bold'].update(kind='ai_extracted')):
   d=deepcopy(data);change(d)
   with self.assertRaises(DemoError):validate_template(d,base)
 def test_mock_v4_request_is_only_public_norm_one_request(self):
  segments=selected_segments('中文摘要标题段前0.5行。');d={n:None for n in V4_FIELDS};d['unsupported']=[];payloads=[]
  def tx(req,t):
   self.assertEqual(t,30);raw=req.data.decode();self.assertNotIn('not-a-real-key',raw);self.assertNotIn('本软件演示通过合成段落',raw);self.assertNotIn('/Volumes/',raw);payloads.append(json.loads(raw));return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(d)}}]}).encode()
  response=parse_requirements(segments,config=Settings('not-a-real-key'),transport=tx);self.assertEqual(len(payloads),1);self.assertEqual(payloads[0]['response_format'],{'type':'json_object'});self.assertEqual(response['receipt']['request_count'],1)
 def test_realistic_B_mock_fields_apply_reimport_recheck(self):
  from tests.academic_B_fixture import draft,segments,values
  response=parse_requirements(segments,config=Settings('fake-only'),transport=lambda req,t:json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(draft,ensure_ascii=False)}}]}).encode())
  s=self.model(False);s.set_norm_text('\n'.join(x['text'] for x in segments),segments=segments);s.confirm_norm_text();self.assertTrue(s.parse_template(parser=lambda x:deepcopy(response)),s.template_error);s.academic_defaults();s.edit_template('abstract_cn_body__font_size','manual',13.5,touched=True);cfg=s.proposed_template();self.assertEqual(cfg['field_sources']['abstract_cn_body__font_size']['kind'],'user_confirmed');self.assertEqual(cfg['field_sources']['font_size']['kind'],'default_inherited');self.assertEqual(cfg['field_sources']['abstract_cn_title__before']['kind'],'ai_extracted');self.assertFalse(cfg['confirmation']['imported']);self.assertTrue(s.apply_template(),s.template_error);self.assertTrue(s.confirm_and_check());s.set_selection([f['key'] for f in s.eligible()]);self.assertTrue(s.generate(),s.error);self.assertEqual(s.result['after']['summary']['problem_count'],0);self.assertEqual(s.result['after']['summary']['review_count'],0);raw=s.template_download();t=WebSession(self.root);t.set_mode('academic');t.load(GOOD.read_bytes(),'software.docx');t.set_types(MANIFEST['paragraph_types']);t.import_template(raw);t.apply_template();t.confirm_and_check();self.assertEqual([{k:f[k] for k in ('key','actual','expected','status','fixable')} for f in t.report['findings']],[{k:f[k] for k in ('key','actual','expected','status','fixable')} for f in s.result['before']['findings']])

 def test_reference_shortage_is_readonly_not_filled(self):
  m=deepcopy(MANIFEST)
  for n in range(22,29):m['paragraph_types'][str(n)]='other'
  r=self.check(manifest=m);f=next(f for f in r['findings'] if f['rule_id']=='R22' and f['locator'].get('property')=='参考文献条目数');self.assertEqual((f['actual'],f['status'],f['fixable']),(3,'problem',False));self.assertEqual(f['source']['physical_page'],16);self.assertTrue(r['coverage']['academic_unchecked_requirements']);self.assertNotIn(f['key'],[f['key'] for f in r['findings'] if f['fixable']])

 def test_missing_or_optional_bold_not_invented_false(self):
  for text in ('中文摘要正文12pt。','中文摘要正文不要求加粗。'):
   seg=selected_segments(text);f={'value':False,'unit':'bool','quote':seg[0]['text'],'location':seg[0]['location'],'support':'supported'}
   with self.assertRaises(DemoError):validate_candidate('abstract_cn_body__bold',f,seg)
 def test_explicit_single_multiple_and_zero_indent(self):
  for n,text,v in [('abstract_cn_title__line_spacing','中文摘要标题1.0倍行距。',1),('abstract_cn_title__line_spacing','中文摘要标题单倍行距。',1),('reference_item__first_line_indent','参考文献条目无首行缩进。',0),('abstract_cn_body__first_line_indent','中文摘要正文首行空两个汉字。',2)]:
   seg=selected_segments(text);f={'value':v,'unit':V4_FIELDS[n][2],'quote':seg[0]['text'],'location':seg[0]['location'],'support':'supported'};self.assertEqual(validate_candidate(n,f,seg)['value'],v)
 def test_unfilled_manual_extra_is_not_silently_disabled(self):
  s=self.model();s.start_academic_template();s.edit_template('body__bold','manual')
  with self.assertRaises(DemoError):s.proposed_template()
  s.edit_template('body__bold','manual',False,touched=True);self.assertFalse(s.proposed_template()['final_values']['body__bold'])
 def test_template_does_not_export_over_import_limit(self):
  d=template();quote='测试规范'+('测'*196);d['norm_excerpt']=[{'location':'摘录:L1','text':quote+'测'*11000}]
  for n,v in d['final_values'].items():
   if v is not None:d['field_sources'][n]={'kind':'user_confirmed','quote':quote,'location':'摘录:L1'}
  with self.assertRaisesRegex(DemoError,'64KB'):validate_template(d,load_rules())
 def test_contextual_spacing_review_not_simple_pt_pass(self):
  p=self.altered(lambda pkg:_ensure(_ensure(pkg.paragraphs[2],'pPr'),'contextualSpacing').set(q('val'),'1'));r=self.check(p);self.assertTrue(any(f['locator'].get('property')=='before' and f['status']=='review' for f in r['findings']))

 def test_keyword_count_not_misread_as_font_size(self):
  seg=selected_segments('中文关键词内容五个。');f={'value':10.5,'unit':'pt','quote':seg[0]['text'],'location':seg[0]['location'],'support':'supported'}
  with self.assertRaises(DemoError):validate_candidate('keywords_cn__content_font_size',f,seg)

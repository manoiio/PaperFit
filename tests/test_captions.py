"""Stage23 independent permutation/ZIP assertions; safe actions never rewrite numbering."""
import unittest,json,zipfile,time
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest.mock import patch
from lxml import etree as E
from core.package import Package,DemoError,q,NS,sha256,write_new
from core.captions import make_scope,inventory,analyze,validate_scope,school,template,parse_caption
from core.caption_move import apply_caption_positions
from core import check_document,fix_document
from core.toc import make_scope as toc_scope
from core.citations import make_scope as cite_scope,inventory as cites
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1];BAD=ROOT/'samples/phase23/caption-errors.docx';GOOD=ROOT/'samples/phase23/caption-correct.docx';RISKS=ROOT/'samples/phase23/caption-number-risks.docx'
def manifest(p=BAD):
 m=json.loads(p.with_suffix('.types.json').read_text());pkg=Package(p);s=make_scope(pkg);inv=inventory(pkg,m)
 s.update(captions={str(r['paragraph']):'normal' for r in inv['captions']},associations={str(r['paragraph']):r['nearby'][0] for r in inv['captions'] if len(r['nearby'])==1},confirmed=True,confirmation='独立人工核对合成范围',complete=True,chapters_complete=True);m['caption_scope']=s;return m

def canon(e):return E.tostring(e,method='c14n')
class CaptionAcceptance(unittest.TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def check(self,p=BAD,m=None):return check_document(p,mode='academic',classification_manifest=m or manifest(p))
 def plans(self,p=BAD,m=None):
  m=m or manifest(p);return analyze(Package(p),m['caption_scope'],m)['positions']
 def move(self,keys=None,m=None,p=BAD,name='out.docx'):
  return apply_caption_positions(p,self.root/name,mode='academic',classification_manifest=m or manifest(p),confirmed_keys=keys or [r['key'] for r in self.plans(p,m) if r['movable']])
 def mutation(self,fn,m=None):
  pkg=Package(BAD);m=deepcopy(m or manifest());fn(pkg);p=self.root/'mutated.docx';p.write_bytes(pkg.bytes(True));h=sha256(p.read_bytes());m['input_sha256']=h
  from core.table_text import rebind
  rebind(m,h);return p,m
 def model(self):
  s=WebSession(self.root/'web');s.set_mode('academic');s.load(BAD.read_bytes(),'软件演示.docx');m=manifest();s.set_types(m['paragraph_types']);s.adopt_caption_scope(m['caption_scope'],confirmed=True);self.assertTrue(s.confirm_and_check(),s.error);return s
 def test_baseline_no_silent_rules(self):
  m=manifest();m.pop('caption_scope');r=self.check(m=m);self.assertFalse(any(f['rule_id'] in ('R42','R43') for f in r['findings']))
 def test_number_and_title_components(self):self.assertEqual(parse_caption('表 2-3 实验结果'),{'type':'table','raw_number':'表 2-3','chapter':2,'sequence':3,'title':'实验结果'})
 def test_correct_numbers_and_positions(self):
  r=self.check(GOOD);self.assertTrue(all(f['status']=='pass' for f in r['findings'] if f['rule_id'] in ('R42','R43')));self.assertFalse(any(p['movable'] for p in self.plans(GOOD)))
 def test_two_reverse_ordinary_cases(self):self.assertEqual([(r['paragraph'],r['kind']) for r in self.plans() if r['movable']],[(5,'figure'),(8,'table')])
 def test_confirmation_not_fix_authorization(self):
  with self.assertRaises(DemoError):apply_caption_positions(BAD,self.root/'no.docx',mode='academic',classification_manifest=manifest())
 def test_unconfirmed_scope_rejected(self):
  m=manifest();m['caption_scope']['confirmed']=False
  with self.assertRaises(DemoError):self.check(m=m)
 def test_scope_unknown_type_hash_bool_rejected(self):
  for key,val in [('input_sha256','x'),('complete',1),('chapter_map',{'3':True}),('associations',{'5':'table:1'}),('captions',{'5':'unsafe'})]:
   s=deepcopy(manifest()['caption_scope']);s[key]=val
   with self.assertRaises(DemoError):validate_scope(Package(BAD),s,manifest())
 def test_template_strict_rejects_unknown_commands(self):
  for t in ({**school(),'code':'exec(1)'},{**school(),'position':'yes'},{**school(),'structure_version':2}):
   with self.assertRaises(DemoError):template(t)
 def test_numbering_risks_and_no_rewrite(self):
  r=self.check(RISKS);a=r['captions'];issues=[x for x in a['numbers'] if x['status']=='problem'];self.assertTrue(any('章号' in ' '.join(x['reasons']) for x in issues));self.assertTrue(any('缺少标题' in ' '.join(x['reasons']) for x in issues));self.assertTrue(any(x['fields'] and x['status']=='review' for x in a['numbers']));self.assertTrue(any('续表' in ' '.join(x['reasons']) for x in a['numbers'] if '续' in x['text']))
 def test_duplicates_in_same_chapter_and_type(self):
  m=manifest(RISKS);m['caption_scope']['chapter_map']={'3':1,'10':2};r=self.check(RISKS,m);self.assertTrue(any('重复' in ' '.join(x['reasons']) for x in r['captions']['numbers']))
 def test_partial_does_not_claim_missing_numbers(self):
  m=manifest();m['caption_scope']['captions']={'13':'normal'};m['caption_scope']['associations']={'13':'image:p:12'};m['caption_scope']['complete']=False;r=self.check(m=m);self.assertTrue(all(s['status']=='review' for s in r['captions']['sequences']))
 def test_unknown_chapter_not_heading_position(self):
  p,m=self.mutation(lambda pkg:setattr(pkg.paragraphs[2].find('w:r/w:t',NS),'text','无章号标题'));r=self.check(p,m);self.assertIsNone(r['captions']['numbers'][0]['confirmed_chapter']);self.assertEqual(r['captions']['numbers'][0]['status'],'review')
 def test_explicit_chapter_override(self):
  p,m=self.mutation(lambda pkg:setattr(pkg.paragraphs[2].find('w:r/w:t',NS),'text','无章号标题'));m['caption_scope']['chapter_map']={'3':1};r=self.check(p,m);self.assertEqual(r['captions']['numbers'][0]['chapter_evidence'],'用户明确确认的章号')
 def test_sequence_requires_complete_scope(self):
  p,m=self.mutation(lambda pkg:setattr(pkg.paragraphs[4].find('w:r/w:t',NS),'text','图1-3 示例曲线'));r=self.check(p,m);self.assertTrue(any(s['status']=='problem' for s in r['captions']['sequences']));m['caption_scope']['complete']=False;r=self.check(p,m);self.assertFalse(any(s['status']=='problem' for s in r['captions']['sequences']))
 def test_huge_numbers_not_expanded(self):
  start=time.monotonic();self.assertIsNone(parse_caption('图'+'9'*10000+'-1 数据'));self.assertLess(time.monotonic()-start,1)
 def test_only_selected_swap_exact_subtrees_and_relative_order(self):
  r=self.move(['L05:5:image:p:6']);a,b=Package(BAD),Package(r['output']);old=list(a.root.find(q('body')));new=list(b.root.find(q('body')));expected=list(old);expected[4],expected[5]=expected[5],expected[4];self.assertEqual(list(map(canon,expected)),list(map(canon,new)));self.assertEqual({k:v for k,v in a.parts.items() if k!='word/document.xml'},{k:v for k,v in b.parts.items() if k!='word/document.xml'});self.assertEqual(r['after']['captions']['positions'][1]['status'],'problem')
 def test_table_only_swap_does_not_change_paragraph_number(self):
  r=self.move(['L05:8:table:1']);self.assertEqual(r['range_mapping']['paragraphs']['8'],'8');a,b=Package(BAD),Package(r['output']);self.assertEqual(list(map(canon,a.paragraphs)),list(map(canon,b.paragraphs)))
 def test_all_selected_and_independent_fresh_check(self):
  r=self.move();self.assertEqual(self.check(Path(r['output']),r['output_classification_manifest'])['findings'],r['after']['findings']);self.assertTrue(all(x['status']=='pass' for x in r['after']['captions']['positions']));self.assertFalse(r['problem_delta']['new_keys'])
 def test_correct_repeat_cannot_move_again(self):
  r=self.move();m=r['output_classification_manifest'];self.assertFalse(any(x['movable'] for x in self.plans(Path(r['output']),m)));raw=Path(r['output']).read_bytes()
  with self.assertRaises(DemoError):self.move(['L05:5:image:p:6'],m,Path(r['output']),'repeat.docx')
  self.assertEqual(raw,Path(r['output']).read_bytes())
 def test_original_and_previous_round_unchanged(self):
  original=BAD.read_bytes();r=self.move(['L05:5:image:p:6']);first=Path(r['output']).read_bytes();self.move(['L05:8:table:1'],r['output_classification_manifest'],Path(r['output']),'two.docx');self.assertEqual(original,BAD.read_bytes());self.assertEqual(first,Path(r['output']).read_bytes())
 def test_block_original_or_existing_output(self):
  for path in (BAD,GOOD):
   with self.assertRaises(DemoError):apply_caption_positions(BAD,path,mode='academic',classification_manifest=manifest(),confirmed_keys=['L05:5:image:p:6'])
 def test_bookmark_inside_caption_blocked(self):
  def f(pkg):e=E.Element(q('bookmarkStart'));e.set(q('id'),'77');e.set(q('name'),'demo');pkg.paragraphs[4].insert(0,e)
  p,m=self.mutation(f);self.assertFalse(self.plans(p,m)[0]['movable'])
 def test_enclosing_bookmark_blocks_move(self):
  def f(pkg):
   b=E.SubElement(pkg.paragraphs[3],q('bookmarkStart'));b.set(q('id'),'1');b.set(q('name'),'range');e=E.SubElement(pkg.paragraphs[6],q('bookmarkEnd'));e.set(q('id'),'1')
  p,m=self.mutation(f);self.assertFalse(self.plans(p,m)[0]['movable']);self.assertIn('书签',self.plans(p,m)[0]['reason'])
 def test_enclosing_field_blocks_move(self):
  def f(pkg):
   for n,t in [(3,'begin'),(6,'end')]:E.SubElement(E.SubElement(pkg.paragraphs[n],q('r')),q('fldChar')).set(q('fldCharType'),t)
  p,m=self.mutation(f);self.assertFalse(self.plans(p,m)[0]['movable'])
 def test_forced_page_and_section_do_not_get_deleted(self):
  for name in ('pageBreakBefore','sectPr'):
   p,m=self.mutation(lambda pkg:E.SubElement(pkg.paragraphs[4].find(q('pPr')),q(name)));raw=p.read_bytes();self.assertFalse(self.plans(p,m)[0]['movable']);self.assertEqual(raw,p.read_bytes());p.unlink()
 def test_complex_hyperlink_caption_blocks(self):
  def f(pkg):
   p=pkg.paragraphs[4];link=E.SubElement(p,q('hyperlink'));link.set(q('anchor'),'x');link.append(p.findall(q('r'))[0])
  p,m=self.mutation(f);self.assertFalse(self.plans(p,m)[0]['movable'])
 def test_multimage_blocks(self):
  def f(pkg):p=pkg.paragraphs[5];p.append(deepcopy(p.findall(q('r'))[0]))
  p,m=self.mutation(f);self.assertFalse(self.plans(p,m)[0]['movable'])
 def test_far_association_and_ambiguous_many_captions(self):
  m=manifest();m['caption_scope']['associations']['5']='image:p:12';m['caption_scope']['associations']['13']='image:p:12';ps=self.plans(m=m);self.assertEqual(ps[0]['status'],'review');self.assertFalse(ps[0]['movable']);self.assertFalse(ps[2]['movable'])
 def test_pending_continuation_excluded_not_moved(self):
  for role in ('continuation','special','pending','excluded'):
   m=manifest();m['caption_scope']['captions']['5']=role;ps=self.plans(m=m);self.assertFalse(any(p['paragraph']==5 and p['movable'] for p in ps))
 def test_material_exclusion_identity_preserved(self):
  m=manifest();m['material_exclusions']={'6':'图片材料明确保护'};r=self.move(['L05:5:image:p:6'],m);self.assertEqual(r['output_classification_manifest']['material_exclusions'],{'5':'图片材料明确保护'});self.assertEqual(r['output_classification_manifest']['paragraph_types']['5'],'other')
 def test_toc_object_identity_remapped(self):
  m=manifest();s=toc_scope(BAD);s.update(objects={'d:6':'unknown'},confirmed=True,confirmation='确认图片段目录待复核定位');m['toc_scope']=s;r=self.move(['L05:5:image:p:6'],m);self.assertEqual(r['output_classification_manifest']['toc_scope']['objects'],{'d:5':'unknown'})
 def test_citation_offsets_confirmations_exclusions_kept(self):
  def f(pkg):pkg.paragraphs[3].find('w:r/w:t',NS).text+='[1]数组[2]'
  p,m=self.mutation(f);s=cite_scope(Package(p),[4]);ci=cites(p,[4]);s.update(objects={r['id']:'citation' if r['numbers']==[1] else 'excluded' for r in ci['objects']},confirmed=True,confirmation='确认引文和数组排除');m['citation_scope']=s;r=self.move(['L05:5:image:p:6'],m,p);self.assertEqual(r['output_classification_manifest']['citation_scope']['objects'],s['objects']);self.assertEqual(r['output_classification_manifest']['citation_scope']['input_sha256'],r['after']['input_sha256'])
 def test_after_move_existing_format_fix_at_right_object(self):
  r=self.move();p=Path(r['output']);m=r['output_classification_manifest'];before=Package(p);f=next(f for f in r['after']['findings'] if f['rule_id']=='R05' and f['status']=='problem');fixed=fix_document(p,self.root/'font.docx',None,mode='academic',classification_manifest=m,selected_keys=[f['key']]);after=Package(fixed['output']);self.assertEqual(before.paragraphs[3].xpath('.//w:t/text()',namespaces=NS),after.paragraphs[3].xpath('.//w:t/text()',namespaces=NS));self.assertEqual(after.paragraphs[3].find('w:r/w:rPr/w:sz',NS).get(q('val')),'24');self.assertTrue(all(p['status']=='pass' for p in fixed['after']['captions']['positions']))
 def test_web_rounds_selection_preview_binding_and_downloads(self):
  s=self.model();self.assertTrue(s.generate_caption_move(['L05:5:image:p:6']),s.error);self.assertEqual(s.generation_count,1);self.assertTrue(s.generate_caption_move(['L05:5:image:p:6']),s.error);self.assertEqual(s.generation_count,1);self.assertTrue(s.next_round(),s.error);self.assertEqual(s.paragraph_types['6'],'figure_caption');self.assertIsNone(s.preview_targets()['original']['classification']);self.assertTrue(s.generate_caption_move(['L05:8:table:1']),s.error);self.assertTrue(s.downloads());self.assertEqual(s.generation_count,2)
 def test_web_scope_change_invalidates_results(self):
  s=self.model();self.assertTrue(s.generate_caption_move(['L05:5:image:p:6']),s.error);d=deepcopy(s.caption_draft);d['complete']=False;s.edit_captions(d);self.assertIsNone(s.report);self.assertFalse(s.downloads());self.assertIsNone(s.caption_confirmed)
 def test_web_project_round_trip_uses_real_input_scope(self):
  s=self.model();s.generate_caption_move(['L05:5:image:p:6']);s.next_round();s.generate_caption_move(['L05:8:table:1']);s.next_round();data=s.prepare_project();self.assertTrue(data);z=s.project_download();new=WebSession(self.root/'new');new.stage_project(z);r=new.restore_project(acknowledged=True);self.assertEqual(r.current_round,2);self.assertEqual(r.report['captions']['positions'][0]['status'],'pass');self.assertEqual(r.paragraph_types['6'],'figure_caption');self.assertTrue(r.prepare_project());again=WebSession(self.root/'again');again.stage_project(r.project_download());rr=again.restore_project(acknowledged=True);self.assertEqual(rr.report['findings'],r.report['findings'])
 def test_web_sessions_and_stale_file(self):
  s=self.model();other=WebSession(self.root/'other');self.assertFalse(other.caption_enabled);s.generate_caption_move(['L05:5:image:p:6']);p=Path(s.result['output']);p.write_bytes(p.read_bytes()+b'changed')
  with self.assertRaises(DemoError):s.downloads()
 def test_exports_and_result_zip_have_scope_mapping(self):
  s=self.model();s.generate_caption_move(['L05:5:image:p:6']);s.prepare_reading_export();d=s.reading_downloads();self.assertIn('R43',d['report.html'].decode());self.assertIn('结构位置',d['report.md'].decode());raw=s.result_package()
  from io import BytesIO
  with zipfile.ZipFile(BytesIO(raw)) as z:self.assertIn('caption-supplement.json',z.namelist());self.assertIn('range-mapping.json',z.namelist());self.assertEqual(z.read('fixed.docx'),s.downloads()['fixed.docx'])
 def test_identical_caption_text_keeps_distinct_identity(self):
  def f(pkg):pkg.paragraphs[12].find('w:r/w:t',NS).text=pkg.paragraphs[4].find('w:r/w:t',NS).text
  p,m=self.mutation(f);r=self.move(['L05:5:image:p:6'],m,p);self.assertEqual(set(r['output_classification_manifest']['caption_scope']['captions']),{'6','8','13','15'});self.assertEqual(r['output_classification_manifest']['caption_scope']['associations']['6'],'image:p:5');self.assertEqual(r['output_classification_manifest']['caption_scope']['associations']['13'],'image:p:12')
 def test_wrong_caption_type_and_unselected_numbering_readonly(self):
  p,m=self.mutation(lambda pkg:setattr(pkg.paragraphs[4].find('w:r/w:t',NS),'text','表1-1 类型冲突'));r=self.check(p,m);self.assertTrue(any('类型冲突' in x for x in r['captions']['numbers'][0]['reasons']));self.assertTrue(all(not f['fixable'] for f in r['findings'] if f['rule_id'] in ('R42','R43')))
 def test_complex_merge_position_not_executed(self):
  def f(pkg):E.SubElement(pkg.root.find('w:body/w:tbl/w:tr/w:tc/w:tcPr',NS),q('gridSpan')).set(q('val'),'2')
  p,m=self.mutation(f);self.assertFalse(self.plans(p,m)[1]['movable'])
 def test_mode_change_invalidates_caption_results(self):
  s=self.model();s.generate_caption_move(['L05:5:image:p:6']);s.set_mode('basic');self.assertIsNone(s.report);self.assertFalse(s.downloads())
 def test_imported_template_reuse_no_api_and_bound_changes(self):
  s=self.model();raw=s.caption_template_bytes();s.import_caption_template(raw);self.assertEqual(template(json.loads(raw)),school());d=json.loads(raw);d['position']=False;s.import_caption_template(json.dumps(d).encode());self.assertIsNone(s.report);self.assertFalse(s.downloads());self.assertIsNone(s.caption_confirmed)
 def test_streamlit_move_result_uses_permutation_proof_and_downloads(self):
  from streamlit.testing.v1 import AppTest
  s=self.model();s.generate_caption_move(['L05:5:image:p:6']);app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=25);app.session_state['workflow']=s;app.run();self.assertFalse(app.exception);self.assertFalse(any('完整性结果异常' in x.value for x in app.error));self.assertTrue(any(x.label=='下载修正版DOCX' for x in app.get('download_button')));self.assertTrue(any('授权题注位置变化' in x.value for x in app.markdown))
 def test_streamlit_completeness_form_commits_both_fields(self):
  from streamlit.testing.v1 import AppTest
  s=self.model();d=deepcopy(s.caption_draft);d['complete']=d['chapters_complete']=False;s.edit_captions(d);app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=25);app.session_state['workflow']=s;app.run();next(x for x in app.checkbox if x.label=='我已核对本次图表题注范围完整').check();next(x for x in app.checkbox if x.label=='我已核对所属章及相关一级标题范围完整').check();next(x for x in app.button if x.label=='采用完整范围声明').click();app.run();self.assertFalse(app.exception);self.assertTrue(s.caption_draft['complete']);self.assertTrue(s.caption_draft['chapters_complete'])
 def test_unparsed_caption_remains_review_not_school_violation(self):
  p,m=self.mutation(lambda pkg:setattr(pkg.paragraphs[4].find('w:r/w:t',NS),'text','图一之一 未支持编号形式'));self.assertEqual(self.check(p,m)['captions']['numbers'][0]['status'],'review')
 def test_partial_chapter_range_cannot_prove_mismatch(self):
  p,m=self.mutation(lambda pkg:setattr(pkg.paragraphs[4].find('w:r/w:t',NS),'text','图9-1 示例曲线'));m['caption_scope']['chapters_complete']=False;self.assertEqual(self.check(p,m)['captions']['numbers'][0]['status'],'review')
 def test_disabled_position_supplement_cannot_authorize_move(self):
  m=manifest();m['caption_scope']['template']['position']=False;self.assertFalse(any(p['movable'] for p in self.plans(m=m)))
  with self.assertRaises(DemoError):self.move(['L05:5:image:p:6'],m)
 def test_duplicated_caption_properties_not_safe(self):
  p,m=self.mutation(lambda pkg:pkg.paragraphs[4].append(deepcopy(pkg.paragraphs[4].find(q('pPr')))));self.assertFalse(self.plans(p,m)[0]['movable'])
 def test_top_level_unknown_boundary_not_safe(self):
  p,m=self.mutation(lambda pkg:E.SubElement(pkg.root.find(q('body')),q('customXml')));self.assertFalse(self.plans(p,m)[0]['movable'])
 def test_multi_image_correct_order_is_not_definite_association(self):
  def f(pkg):p=pkg.paragraphs[11];p.append(deepcopy(p.findall(q('r'))[0]))
  p,m=self.mutation(f);row=self.plans(p,m)[2];self.assertEqual(row['status'],'review');self.assertFalse(row['movable'])
 def test_disabled_numbering_is_reported_unchecked(self):
  m=manifest();m['caption_scope']['template']['numbering']=False;r=self.check(m=m);self.assertIsNone(r['captions']['summary']['numbering_problems']);self.assertFalse(any(f['rule_id']=='R42' for f in r['findings']));self.assertEqual(r['summary']['rule_count'],23)
 def test_type_conflict_not_a_duplicate_for_correct_other_caption(self):
  p,m=self.mutation(lambda pkg:setattr(pkg.paragraphs[4].find('w:r/w:t',NS),'text','表1-1 类型冲突'));r=self.check(p,m);by={x['paragraph']:x for x in r['captions']['numbers']};self.assertFalse(any('重复' in x for x in by[8]['reasons']));self.assertFalse(r['captions']['scope_complete'])
 def test_complete_declaration_does_not_hide_unconfirmed_captions(self):
  m=manifest();m['caption_scope']['captions'].pop('13');m['caption_scope']['associations'].pop('13');r=self.check(m=m);self.assertFalse(r['captions']['scope_complete']);self.assertEqual(r['captions']['unconfirmed_captions'],[13]);self.assertTrue(any(n['locator'].get('paragraph')==13 and '未执行R42' in n['detail'] for n in r['coverage_notes']))
 def test_compact_project_cannot_rebind_moved_indices_back_to_original(self):
  s=self.model();s.generate_caption_move(['L05:5:image:p:6']);s.next_round();raw=s.prepare_project('current');new=WebSession(self.root/'compact');new.stage_project(raw);r=new.restore_project(acknowledged=True);self.assertEqual(r.history,[]);self.assertIsNone(r.preview_targets()['original']['classification']);self.assertIsNone(r.preview_targets()['original']['body']);self.assertIsNotNone(r.preview_targets()['input']['classification'])
 def test_problem_center_human_readable_number_and_order(self):
  from web.issues import field_value
  self.assertEqual(field_value(['caption','figure'],'R43',{}),'题注 → 图片');r=self.check();f=next(x for x in r['findings'] if x['rule_id']=='R42');label=field_value(f['actual'],'R42',f['locator']);self.assertIn('图1-1',label);self.assertIn('所属章 1',label)

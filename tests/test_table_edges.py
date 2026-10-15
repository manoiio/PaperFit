"""Stage20: independent XML/ZIP oracle, opt-in edges, actual header rows and state."""
from unittest import TestCase,mock
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from io import BytesIO
import json,zipfile
from lxml import etree as E
from core.package import Package,q,NS,DemoError
from core import check_document,fix_document
from core.table_text import tables,validate_scope
from core.table_edges import evidence,header_value
from core.layout import apply_pagination_layout,suggest_pagination_aids
from core.engine import _ensure
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'samples/phase20'
def manifest(p,headers=None,edges=True,types=None):
 pkg=Package(p)
 return {'input_sha256':pkg.hash,'paragraph_types':{str(i):'other' for i in range(1,len(pkg.paragraphs)+1)},'confirmed':True,'confirmation':'独立人工核对合成样本','table_scope':{'input_sha256':pkg.hash,'table_types':types or {str(i):'content' for i in range(1,len(tables(pkg))+1)},'confirmed':True,'confirmation':'独立表格用途核对','layout_options':{'version':1,'outer_edges':edges,'headers':headers or {}}}}
def findings(r):return [f for f in r['findings'] if f['rule_id']=='R35']
def check(p,m):return check_document(p,mode='academic',classification_manifest=m)
def independent_mask(raw,edges=(),headers=()):
 root=E.fromstring(raw);ts=root.find(q('body')).findall(q('tbl'))
 for n,side in edges:
  t=ts[n-1];targets=[t.find(q('tblPr'))]+[r.findall(q('tc'))[0 if side=='left' else -1].find(q('tcPr')) for r in t.findall(q('tr'))]
  for pr in targets:
   if pr is None:continue
   b=pr.find(q('tblBorders')) if pr.tag==q('tblPr') else pr.find(q('tcBorders'))
   if b is not None:
    for name in (side,'start' if side=='left' else 'end'):
     for e in b.findall(q(name)):b.remove(e)
 for n,count in headers:
  for r in ts[n-1].findall(q('tr'))[:count]:
   for e in r.findall('w:trPr/w:tblHeader',NS):e.getparent().remove(e)
 for e in reversed(list(root.iter())):
  if e.tag in {q(n) for n in ('tblBorders','tcBorders','tblPr','tcPr','trPr')} and not len(e) and not e.attrib and not e.text:e.getparent().remove(e)
 return E.tostring(root,method='c14n')
class TableEdgesTests(TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.d=Path(self.tmp.name);self.p=S/'errors.docx';self.m=manifest(self.p)
 def tearDown(self):self.tmp.cleanup()
 def fix(self,p=None,m=None,keys=None,name='out.docx'):
  return fix_document(p or self.p,self.d/name,None,mode='academic',classification_manifest=m or self.m,selected_keys=keys or (),selected_rules=['R35'] if keys is None else ())
 def alter(self,fn,p=None):
  pkg=Package(p or self.p);fn(pkg);pkg.parts['word/styles.xml']=E.tostring(pkg.styles);dst=self.d/'alter.docx';dst.write_bytes(pkg.bytes(True));return dst
 def model(self,p=None):
  p=p or self.p;m=manifest(p);s=WebSession(self.d/'web');s.set_mode('academic');self.assertTrue(s.load(p.read_bytes(),'演示.docx'));s.set_types(m['paragraph_types']);s.set_table_enabled(True);s.set_table_types(m['table_scope']['table_types']);s.set_table_layout_options(m['table_scope']['layout_options']);s.confirm_tables();self.assertTrue(s.confirm_and_check(),s.error);return s
 def test_independent_error_list_each_side(self):
  gold=json.loads((S/'independent-errors.json').read_text());got={str(i):[] for i in range(1,5)}
  for f in findings(check(self.p,self.m)):
   if f['status']=='problem':got[str(f['locator']['table'])].append(f['locator']['side'])
  self.assertEqual(got,gold['errors']);self.assertEqual(check(self.p,self.m)['summary']['rule_count'],24)
 def test_correct_control_all_edges_pass(self):
  p=S/'correct.docx';self.assertTrue(all(f['status']=='pass' for f in findings(check(p,manifest(p)))))
 def test_opt_in_old_scope_and_rule_count(self):
  m=deepcopy(self.m);m['table_scope'].pop('layout_options');self.assertFalse(findings(check(self.p,m)));self.assertEqual(check(self.p,m)['summary']['rule_count'],23)
 def test_cover_never_checked_or_changed(self):
  m=manifest(self.p,types={str(i):'cover' for i in range(1,5)});r=self.fix(m=m);self.assertEqual(findings(r['after'])[0]['status'],'not_applicable');self.assertEqual(Path(r['output']).read_bytes(),self.p.read_bytes())
 def test_partial_left_keeps_wrong_right_and_all_other_xml(self):
  key='R35:table=3:side=left';r=self.fix(keys=[key]);old=Package(self.p);new=Package(r['output'])
  self.assertEqual(independent_mask(old.parts['word/document.xml'],[(3,'left')]),independent_mask(new.parts['word/document.xml'],[(3,'left')]))
  self.assertEqual(next(f for f in findings(r['after']) if f['key']=='R35:table=3:side=right')['status'],'problem')
  for name,raw in old.parts.items():
   if name!='word/document.xml':self.assertEqual(raw,new.parts[name])
  self.assertEqual(old.raw,self.p.read_bytes());self.assertTrue(all(c['verification']=='pass' for c in r['changes']))
 def test_cell_override_and_table_both_suppressed(self):
  r=self.fix(keys=['R35:table=3:side=left']);t=tables(Package(r['output']))[2]
  self.assertEqual(t.find('w:tblPr/w:tblBorders/w:left',NS).get(q('val')),'nil')
  self.assertTrue(all(c.get(q('val'))=='nil' for c in t.findall('w:tr/w:tc[1]/w:tcPr/w:tcBorders/w:left',NS)))
 def test_all_fix_fresh_read_and_idempotent(self):
  r=self.fix();self.assertEqual(len(r['changes']),4);self.assertEqual(r['after'],check(r['output'],r['output_classification_manifest']));two=self.fix(r['output'],r['output_classification_manifest'],name='again.docx');self.assertEqual(two['changes'],[]);self.assertEqual(Path(two['output']).read_bytes(),Path(r['output']).read_bytes())
 def test_inherited_style_is_read_and_not_modified(self):
  def fn(p):
   s=E.SubElement(p.styles,q('style'),{q('type'):'table',q('styleId'):'DemoBase'});pr=E.SubElement(s,q('tblPr'));b=E.SubElement(pr,q('tblBorders'));E.SubElement(b,q('left'),{q('val'):'double'})
   s=E.SubElement(p.styles,q('style'),{q('type'):'table',q('styleId'):'DemoChild'});E.SubElement(s,q('basedOn'),{q('val'):'DemoBase'})
   t=tables(p)[3];_ensure(t.find(q('tblPr')),'tblStyle').set(q('val'),'DemoChild');t.find('w:tblPr/w:tblBorders',NS).remove(t.find('w:tblPr/w:tblBorders/w:left',NS))
  p=self.alter(fn);r=check(p,manifest(p));f=next(f for f in findings(r) if f['key']=='R35:table=4:side=left');self.assertEqual(f['status'],'problem');self.assertIn('DemoBase',str(f['actual']));out=self.fix(p,manifest(p),[f['key']]);self.assertEqual(Package(p).parts['word/styles.xml'],Package(out['output']).parts['word/styles.xml'])
 def test_direct_cell_wins_style_and_interior_unchanged(self):
  r=self.fix(keys=['R35:table=3:side=left']);self.assertIn('单元格直接',str(next(f for f in findings(r['before']) if f['key']=='R35:table=3:side=left')['actual']))
  a=tables(Package(self.p))[2];b=tables(Package(r['output']))[2]
  for tag in ('top','bottom','insideH','insideV','right'):self.assertEqual(E.tostring(a.find('w:tblPr/w:tblBorders/w:'+tag,NS)),E.tostring(b.find('w:tblPr/w:tblBorders/w:'+tag,NS)))
 def test_complex_conditions_nested_and_direction_review(self):
  p=S/'complex.docx';r=check(p,manifest(p));self.assertTrue(all(f['status']=='review' and not f['fixable'] for f in findings(r)))
 def test_missing_style_not_no_border(self):
  p=self.alter(lambda p:_ensure(tables(p)[0].find(q('tblPr')),'tblStyle').set(q('val'),'Missing'));self.assertEqual(findings(check(p,manifest(p)))[0]['status'],'review')
 def test_conditional_unknown_even_with_direct_edges(self):
  def fn(p):
   s=E.SubElement(p.styles,q('style'),{q('type'):'table',q('styleId'):'Conditional'});c=E.SubElement(s,q('tblStylePr'),{q('type'):'firstCol'});b=E.SubElement(E.SubElement(c,q('tcPr')),q('tcBorders'));E.SubElement(b,q('left'),{q('val'):'single'});_ensure(tables(p)[0].find(q('tblPr')),'tblStyle').set(q('val'),'Conditional')
  p=self.alter(fn);self.assertEqual(findings(check(p,manifest(p)))[0]['status'],'review')
 def test_start_end_conflict_review(self):
  p=self.alter(lambda p:E.SubElement(tables(p)[0].find('w:tblPr/w:tblBorders',NS),q('start'),{q('val'):'nil'}));self.assertEqual(findings(check(p,manifest(p)))[0]['status'],'review')
 def test_start_only_is_supported_and_fixed(self):
  def fn(p):tables(p)[0].find('w:tblPr/w:tblBorders/w:left',NS).tag=q('start')
  p=self.alter(fn);r=self.fix(p,manifest(p),['R35:table=1:side=left']);self.assertEqual(findings(r['after'])[0]['status'],'pass')
 def test_nonzero_spacing_and_row_spacing_review(self):
  for tag in ('tblPr','trPr'):
   def fn(p):
    x=tables(p)[0] if tag=='tblPr' else tables(p)[0].find(q('tr'));E.SubElement(_ensure(x,tag),q('tblCellSpacing'),{q('w'):'20',q('type'):'dxa'})
   p=self.alter(fn);self.assertEqual(findings(check(p,manifest(p)))[0]['status'],'review')
 def test_unknown_and_duplicate_border_review(self):
  for val in ('unknown',None):
   def fn(p):
    b=tables(p)[0].find('w:tblPr/w:tblBorders',NS)
    if val:b.find(q('left')).set(q('val'),val)
    else:E.SubElement(b,q('left'),{q('val'):'single'})
   p=self.alter(fn);self.assertEqual(findings(check(p,manifest(p)))[0]['status'],'review')
 def test_tampered_scope_and_invalid_options_rejected(self):
  for opts in ({'version':True,'outer_edges':True,'headers':{}},{'version':1,'outer_edges':True,'headers':{'1':True}},{'version':1,'outer_edges':True,'headers':{'1':4}},{'version':1,'outer_edges':True,'headers':{},'execute':'bad'}):
   m=deepcopy(self.m);m['table_scope']['layout_options']=opts
   with self.assertRaises(DemoError):check(self.p,m)
 def test_reject_overwrite_and_unsafe_keys(self):
  with self.assertRaises(DemoError):fix_document(self.p,self.p,None,selected_rules=['R35'],mode='academic',classification_manifest=self.m)
  p=S/'complex.docx'
  result=self.fix(p,manifest(p),['R35:table=1:side=left']);self.assertEqual(result['changes'],[]);self.assertIn('R35:table=1:side=left',result['skipped_review_keys'])
 def layout(self,p=None,m=None,keys=None,name='header.docx'):
  p=p or S/'long.docx';m=m or manifest(p,headers={'1':2});return apply_pagination_layout(p,self.d/name,mode='academic',classification_manifest=m,confirmed_keys=keys or ['L04:1:2'])
 def test_multi_header_only_selected_rows_preserved_independently(self):
  p=S/'long.docx';r=self.layout();a=Package(p);b=Package(r['output']);self.assertEqual(len(r['changes']),2)
  rows=tables(b)[0].findall(q('tr'));self.assertEqual([i for i,row in enumerate(rows,1) if row.find('w:trPr/w:tblHeader',NS) is not None],[1,2]);self.assertEqual(independent_mask(a.parts['word/document.xml'],headers=[(1,2)]),independent_mask(b.parts['word/document.xml'],headers=[(1,2)]))
  self.assertFalse(b.root.xpath('//w:trHeight[@w:hRule="exact"]|//w:pPr/w:keepNext|//w:br[@w:type="page"]',namespaces=NS));self.assertIn('不补续表',r['layout']['message'])
 def test_single_header_and_already_correct_no_changes(self):
  r=self.layout(self.p,manifest(self.p,headers={'1':1}),['L04:1:1']);two=self.layout(Path(r['output']),r['output_classification_manifest'],['L04:1:1'],name='again.docx');self.assertEqual(two['changes'],[]);self.assertEqual(Path(r['output']).read_bytes(),Path(two['output']).read_bytes())
 def test_unselected_existing_row_header_preserved(self):
  p=self.alter(lambda p:_ensure(_ensure(tables(p)[0].findall(q('tr'))[2],'trPr'),'tblHeader').set(q('val'),'1'))
  r=self.layout(p,manifest(p,headers={'1':1}),['L04:1:1']);self.assertTrue(header_value(tables(Package(r['output']))[0].findall(q('tr'))[2]))
 def test_cross_boundary_vmerge_blocked(self):
  def fn(p):
   for idx,val in [(0,'restart'),(1,'continue')]:_ensure(_ensure(tables(p)[0].findall(q('tr'))[idx].find(q('tc')),'tcPr'),'vMerge').set(q('val'),val)
  p=self.alter(fn);m=manifest(p,headers={'1':1});pro=suggest_pagination_aids(p,m);self.assertEqual(next(x for x in pro['pairs'] if x['id']=='L04')['status'],'review')
  with self.assertRaises(DemoError):self.layout(p,m,['L04:1:1'])
 def test_forced_break_not_removed_or_handled(self):
  def fn(p):E.SubElement(tables(p)[0].find('.//'+q('r')),q('br'),{q('type'):'page'})
  p=self.alter(fn)
  with self.assertRaises(DemoError):self.layout(p,manifest(p,headers={'1':1}),['L04:1:1'])
 def test_l04_does_not_claim_visual_success(self):
  r=self.layout();self.assertEqual(r['layout']['visual_status'],'not_reviewed');self.assertTrue(all(c['verification']=='pass' for c in r['layout']['checks']));self.assertIn('不保证',r['layout']['limitation'])
 def test_r23_width_l02_and_r35_can_coexist(self):
  from core.widths import check_widths
  s=self.model(S/'long.docx');s.set_table_layout_options({'version':1,'outer_edges':True,'headers':{'1':2}});s.confirm_tables();s.confirm_and_check();before=check_widths(s.input_path)
  s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R35']);self.assertTrue(s.generate(),s.error);out=s.result;self.assertEqual(before['objects'][0]['declared_width_mm'],check_widths(out['output'])['objects'][0]['declared_width_mm']);self.assertTrue(s.next_round());self.assertTrue(s.generate_layout('input',['L04:1:2']),s.layout_error)
 def test_scope_edit_invalidates_download_selection_preview(self):
  s=self.model();s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R35']);s.generate();s.set_table_layout_options({'version':1,'outer_edges':True,'headers':{'1':1}});self.assertIsNone(s.result);self.assertIsNone(s.report);self.assertEqual(s.selected,[]);self.assertIsNone(s.table_confirmed)
 def test_file_change_does_not_reuse_options(self):
  s=self.model();s.load((S/'correct.docx').read_bytes(),'new.docx');self.assertIsNone(s.table_layout_options);self.assertFalse(s.table_enabled)
 def test_rounds_project_restore_rechecks_and_preserves_sources(self):
  s=self.model();s.set_table_layout_options({'version':1,'outer_edges':True,'headers':{'3':1}});s.confirm_tables();s.confirm_and_check()
  for side in ('left','right'):
   s.set_selection([f'R35:table=3:side={side}']);self.assertTrue(s.generate(),s.error);s.next_round();s.check()
  raw=s.prepare_project();s.stage_project(raw)
  with mock.patch('web.project_session.check_document',wraps=check_document) as c:n=s.restore_project(acknowledged=True);self.assertGreater(c.call_count,0)
  self.assertEqual(n.table_layout_options,s.table_layout_options);self.assertEqual(n.current_round,2);self.assertEqual(len(n.history),2);self.assertEqual(findings(n.report),findings(s.report));self.assertTrue(n.generate_layout('input',['L04:3:1']),n.layout_error)
 def test_draft_restore_no_automatic_confirmation(self):
  s=self.model();s.set_table_layout_options({'version':1,'outer_edges':False,'headers':{'1':1}});s.stage_project(s.prepare_project());n=s.restore_project(acknowledged=True);self.assertEqual(n.table_layout_options,s.table_layout_options);self.assertIsNone(n.table_confirmed);self.assertIsNone(n.report)
 def test_dual_session_isolation(self):
  a=self.model();b=self.model();a.set_table_layout_options({'version':1,'outer_edges':False,'headers':{'1':2}});self.assertNotEqual(a.task_dir,b.task_dir);self.assertEqual(b.table_layout_options['headers'],{});self.assertIsNotNone(b.report)
 def test_zip_and_html_include_real_new_results_without_private_paths(self):
  s=self.model();s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R35']);s.generate();raw=s.result_package()
  with zipfile.ZipFile(BytesIO(raw)) as z:
   self.assertIn('table-layout-options.json',z.namelist());self.assertEqual(z.read('fixed.docx'),Path(s.result['output']).read_bytes());self.assertIn('R35',z.read('report.html').decode());self.assertNotIn(str(s.task_dir),z.read('report.html').decode());self.assertEqual(json.loads(z.read('scope.json'))['table_scope']['layout_options'],s.table_layout_options)
 def test_external_change_rejects_old_output_and_project(self):
  s=self.model();s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R35']);s.generate();Path(s.result['output']).write_bytes(b'changed')
  with self.assertRaises(DemoError):s.result_package()
 def test_border_filter_retains_correct_stable_record_keys(self):
  from web.issues import project,type_records,value
  r=check(self.p,self.m);rows=project(r)['records'];selected=type_records(rows,r['coverage'],'table_border')
  self.assertEqual({x['record_key'] for x in selected},{f['key'] for f in findings(r)});self.assertTrue(all(x['object'].startswith('table:') for x in selected));self.assertEqual(len(type_records(rows,r['coverage'],'body')),0)
  long=check(S/'long.docx',manifest(S/'long.docx'));self.assertLess(len(value(findings(long)[0]['actual'],'R35')),200)
 def test_option_export_reload_hash_and_strict_validation(self):
  s=self.model();raw=s.export_table_options();s.set_table_layout_options({'version':1,'outer_edges':False,'headers':{}});s.import_table_options(raw);self.assertTrue(s.table_layout_options['outer_edges']);self.assertIsNone(s.table_confirmed)
  data=json.loads(raw);data['input_sha256']='0'*64
  with self.assertRaises(DemoError):s.import_table_options(json.dumps(data).encode())
  with self.assertRaises(DemoError):s.import_table_options(b'{"input_sha256":"a","input_sha256":"b"}')
 def test_inherited_logical_physical_conflict_is_review(self):
  def fn(p):
   s=E.SubElement(p.styles,q('style'),{q('type'):'table',q('styleId'):'Logic'});b=E.SubElement(E.SubElement(s,q('tblPr')),q('tblBorders'));E.SubElement(b,q('start'),{q('val'):'double'});t=tables(p)[0];_ensure(t.find(q('tblPr')),'tblStyle').set(q('val'),'Logic')
  p=self.alter(fn);self.assertEqual(findings(check(p,manifest(p)))[0]['status'],'review')
 def test_nonvacuous_media_fields_bookmarks_relations_sections_preserved(self):
  protected=ROOT/'samples/phase19/protected.docx';p=self.alter(lambda pkg:pkg.root.find(q('body')).insert(0,deepcopy(tables(Package(self.p))[0])),protected)
  a=Package(p);self.assertTrue(any(n.startswith('word/media/') for n in a.parts));self.assertTrue(a.root.xpath('//w:fldChar|//w:fldSimple',namespaces=NS));self.assertTrue(a.root.xpath('//w:bookmarkStart',namespaces=NS));r=self.fix(p,manifest(p),['R35:table=1:side=left']);b=Package(r['output'])
  self.assertEqual(independent_mask(a.parts['word/document.xml'],[(1,'left')]),independent_mask(b.parts['word/document.xml'],[(1,'left')]))
  for n,raw in a.parts.items():
   if n!='word/document.xml':self.assertEqual(raw,b.parts[n])
 def test_width_adaptation_then_r23_edge_and_l02_l04_preserve_dimensions(self):
  from core.widths import check_widths,apply_width_adaptation
  from core import effective_rules
  def fn(p):
   p.sections[0].find(q('pgMar')).set(q('left'),'2000');p.sections[0].find(q('pgMar')).set(q('right'),'1800')
   _ensure(_ensure(tables(p)[0].find('.//'+q('r')),'rPr'),'sz').set(q('val'),'28')
  p=self.alter(fn,S/'long.docx');m=manifest(p,headers={'1':2});m['paragraph_types']['3']='table_caption';plan=check_widths(p,rules_sha256=effective_rules(mode='academic')['sha256']);self.assertTrue(plan['objects'][0]['fixable'])
  w=apply_width_adaptation(p,self.d/'width.docx',None,mode='academic',classification_manifest=m,plan=plan,selected_keys=['W01:table=1'])
  old=Package(w['output']);r=fix_document(w['output'],self.d/'fonts-edges.docx',None,mode='academic',classification_manifest=w['output_classification_manifest'],selected_rules=['R23','R35']);new=Package(r['output'])
  for path in ('w:tblGrid','w:tblPr/w:tblW','w:tblPr/w:tblLayout'):
   self.assertEqual(E.tostring(tables(old)[0].find(path,NS)),E.tostring(tables(new)[0].find(path,NS)))
  for a,b in zip(tables(old)[0].findall('w:tr/w:tc/w:tcPr/w:tcW',NS),tables(new)[0].findall('w:tr/w:tc/w:tcPr/w:tcW',NS)):self.assertEqual(E.tostring(a),E.tostring(b))
  out=self.layout(Path(r['output']),r['output_classification_manifest'],['L02:3:1','L04:1:2']);self.assertTrue(Package(out['output']).paragraphs[2].find('w:pPr/w:keepNext',NS) is not None);self.assertEqual(sum(c['rule_id']=='L04' for c in out['changes']),2)
 def test_streamlit_l04_result_renders_downloads_and_real_row_labels(self):
  from streamlit.testing.v1 import AppTest
  s=self.model(S/'long.docx');s.set_table_layout_options({'version':1,'outer_edges':True,'headers':{'1':2}});s.confirm_tables();s.confirm_and_check();self.assertTrue(s.generate_layout('input',['L04:1:2']),s.layout_error)
  app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20);app.session_state['workflow']=s;app.run();self.assertFalse(app.exception)
  self.assertTrue(any('下载修正版DOCX'==x.label for x in app.get('download_button')))
  changes=[df.value for df in app.dataframe if '分页属性' in getattr(df.value,'columns',[])];self.assertTrue(changes);self.assertTrue(all('表头' in v for v in changes[0]['分页属性']));self.assertEqual(list(changes[0]['位置']),['表 1 · 行1','表 1 · 行2'])
  self.assertEqual(s.table_header_preview(1,2)[1]['行'],2);self.assertIn('子表头',s.table_header_preview(1,2)[1]['简短文字'])
 def test_old_scope_cannot_select_new_inactive_rule(self):
  m=deepcopy(self.m);m['table_scope'].pop('layout_options')
  with self.assertRaises(DemoError):self.fix(m=m)

 def test_duplicate_style_layers_not_guessed(self):
  def fn(p):
   s=E.SubElement(p.styles,q('style'),{q('type'):'table',q('styleId'):'Duplicate'});E.SubElement(s,q('basedOn'),{q('val'):'TableNormal'});E.SubElement(s,q('basedOn'),{q('val'):'TableNormal'});_ensure(tables(p)[0].find(q('tblPr')),'tblStyle').set(q('val'),'Duplicate')
  p=self.alter(fn);self.assertEqual(findings(check(p,manifest(p)))[0]['status'],'review')
 def test_safe_patch_impact_is_visible_before_selection(self):
  r=check(S/'long.docx',manifest(S/'long.docx'));left=next(f for f in findings(r) if f['locator']['side']=='left');self.assertIn('行1–83',left['dependency_note']);self.assertIn('实际XML格1',left['dependency_note']);self.assertIn('内部线',left['dependency_note'])
 def test_complex_fixture_is_a_real_conditional_style_not_malformed(self):
  p=S/'complex.docx';r=check(p,manifest(p));f=findings(r)[0];self.assertIn('条件表格样式',f['actual']['unresolved']);self.assertEqual(len(Package(p).styles.xpath('//w:style[@w:styleId="DemoOuter"]/w:tblPr',namespaces=NS)),1)

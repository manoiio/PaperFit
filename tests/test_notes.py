from tests.ui_navigation import show, click as ui_click
"""Independent OOXML/ZIP oracles for opt-in footnote/endnote transactions."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase,mock
from io import BytesIO
import json,zipfile
from lxml import etree as E
from core import check_document,fix_document
from core.package import Package,DemoError,q,NS,parse
from core.notes import inventory,make_scope,template,validate_scope,school
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'samples/phase21'
def manifest(path):
 p=Package(path);s=make_scope(p);s.update(objects=[r['key'] for r in inventory(p)['objects']],confirmed=True,confirmation='构造者独立核对')
 return {'input_sha256':p.hash,'paragraph_types':{str(i):'other' for i in range(1,len(p.paragraphs)+1)},'confirmed':True,'confirmation':'独立范围','note_scope':s}
def check(p,m=None):return check_document(p,mode='academic',classification_manifest=m or manifest(p))
def findings(r):return [f for f in r['findings'] if f['rule_id'] in ('R36','R37')]
def rewrite(src,out,fn):
 p=Package(src);fn(p)
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  for name,b in p.parts.items():z.writestr(name,b)
 return out

def signature(p):
 # Independent allowed-attribute masking, no new checker/mask calls.
 out={}
 for name,b in Package(p).parts.items():
  if name not in ('word/footnotes.xml','word/endnotes.xml'):out[name]=b;continue
  r=parse(b)
  out[name]=[(''.join(n.xpath('.//w:t/text()',namespaces=NS)),n.get(q('id')),n.get(q('type')),[(x.tag,dict(x.attrib)) for x in n.iter() if x.tag in (q('footnoteRef'),q('endnoteRef'),q('separator'),q('continuationSeparator'))]) for n in r]
 return out
class NotesTests(TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.d=Path(self.tmp.name);self.p=S/'errors.docx';self.m=manifest(self.p)
 def tearDown(self):self.tmp.cleanup()
 def fix(self,keys=None,path=None,m=None,name='out.docx'):
  return fix_document(path or self.p,self.d/name,None,mode='academic',classification_manifest=m or self.m,selected_rules=['R36','R37'] if keys is None else (),selected_keys=keys or ())
 def session(self):
  s=WebSession(self.d/'web');s.set_mode('academic');s.load(self.p.read_bytes(),'合成注释.docx');s.set_types(self.m['paragraph_types']);s.enable_notes(True);s.edit_notes(self.m['note_scope']);s.confirm_notes();self.assertTrue(s.confirm_and_check(),s.error);return s
 def edit(self,fn):return rewrite(self.p,self.d/'edited.docx',fn)
 def test_inventory_actual_relationships_ids_systems_references(self):
  v=inventory(self.p);self.assertEqual(len(v['objects']),6);self.assertEqual(len(v['systems']),4);self.assertEqual(len(v['references']),6);self.assertFalse(v['issues']);self.assertEqual([r['paragraph'] for r in v['objects'][0]['references']],[3]);self.assertEqual(v['objects'][0]['key'],'footnote:1:3');self.assertEqual(len(Package(self.p).paragraphs),6)
 def test_independent_error_oracle_and_late_run_and_style(self):
  r=check(self.p);bad=[f for f in findings(r) if f['status']=='problem'];self.assertEqual(len(bad),json.loads((S/'independent-errors.json').read_text())['safe_problem_count']);self.assertEqual({f['locator']['run'] for f in bad if f['locator'].get('note_id')=='1' and f['property']=='font_size'},{3});self.assertTrue(any(f['actual']=={'eastAsia':'楷体'} for f in bad));self.assertEqual(sum(f['status']=='review' for f in findings(r)),3);self.assertTrue(any(f['property']=='protected_link' and not f['fixable'] for f in findings(r)))
 def test_correct_control_and_complex_granular_not_pass(self):
  fs=findings(check(S/'correct.docx'));self.assertFalse(any(f['status']=='problem' for f in fs));self.assertEqual(sum(f['status']=='review' for f in fs),3);self.assertTrue(any(f['property']=='protected_link' and not f['fixable'] for f in fs));self.assertTrue(any(f['locator'].get('note_id')=='3' and f['rule_id']=='R37' and f['property']=='font_size' and f['status']=='pass' for f in fs))
 def test_old_mode_optin_semantics(self):
  m=deepcopy(self.m);m.pop('note_scope');r=check(self.p,m);self.assertNotIn('notes',r);self.assertEqual(r['summary']['rule_count'],22)
 def test_no_notes_is_not_missing_requirement(self):
  p=ROOT/'samples/extended-correct.docx';r=check(p);self.assertEqual([f['status'] for f in findings(r)],['not_applicable','not_applicable']);self.assertEqual(r['notes']['selected'],[])
 def test_partial_one_property_independent_members_and_attributes(self):
  f=next(f for f in findings(check(self.p)) if f['rule_id']=='R36' and f['property']=='font_size' and f['status']=='problem');r=self.fix([f['key']]);a,b=Package(self.p),Package(r['output']);self.assertEqual(signature(self.p),signature(r['output']))
  for n,raw in a.parts.items():
   if n!='word/footnotes.xml':self.assertEqual(raw,b.parts[n],n)
  x,y=parse(a.parts['word/footnotes.xml']),parse(b.parts['word/footnotes.xml']);old=x.findall(q('footnote'))[2].findall(q('p'))[0].findall(q('r'))[2].find('w:rPr/w:sz',NS);new=y.findall(q('footnote'))[2].findall(q('p'))[0].findall(q('r'))[2].find('w:rPr/w:sz',NS);self.assertEqual((old.get(q('val')),new.get(q('val'))),('28','24'));old.set(q('val'),'24');self.assertEqual(E.tostring(x,method='c14n'),E.tostring(y,method='c14n'));self.assertTrue(r['preservation']['main_document_bytes_equal']);self.assertFalse(r['preservation']['other_zip_member_bytes_equal']);self.assertTrue(r['preservation']['unselected_zip_member_bytes_equal'])
 def test_all_safe_reread_and_markers_ids_order_preserved(self):
  r=self.fix();self.assertEqual(len(r['changes']),9);self.assertEqual(signature(self.p),signature(r['output']));self.assertFalse(any(f['status']=='problem' for f in findings(r['after'])));self.assertEqual(r['after'],check(r['output'],r['output_classification_manifest']));self.assertEqual(r['preservation']['selected_story_part_count'],2)
 def test_correct_repeat_is_byte_identical(self):
  r=self.fix();again=self.fix(path=r['output'],m=r['output_classification_manifest'],name='again.docx');self.assertEqual(again['changes'],[]);self.assertEqual(Path(r['output']).read_bytes(),Path(again['output']).read_bytes())
 def test_fixed_and_minimum_are_not_multiple(self):
  fs=findings(check(self.p));self.assertTrue(any(f['actual']=={'multiple':None,'line_rule':'exact','pt':20} for f in fs));self.assertTrue(any(f['actual']=={'multiple':None,'line_rule':'atLeast','pt':20} for f in fs))
 def test_missing_line_does_not_imply_single(self):
  def fn(p):
   root=parse(p.parts['word/footnotes.xml']);n=root.findall(q('footnote'))[2];pp=n.find('w:p/w:pPr',NS);pp.remove(pp.find(q('spacing')));pp.remove(pp.find(q('pStyle')));p.parts['word/footnotes.xml']=E.tostring(root)
   styles=parse(p.parts['word/styles.xml'])
   for e in styles.xpath('.//w:spacing',namespaces=NS):e.getparent().remove(e)
   p.parts['word/styles.xml']=E.tostring(styles)
  p=self.edit(fn);self.assertTrue(any(f['status']=='review' and '未设置' in f['detail'] for f in findings(check(p)) if f['property']=='line_multiple'))
 def test_marker_style_and_rpr_untouched(self):
  r=self.fix();a,b=Package(self.p),Package(r['output'])
  for n in ('word/footnotes.xml','word/endnotes.xml'):
   for x,y in zip(parse(a.parts[n]),parse(b.parts[n])):
    if x.get(q('type')):self.assertEqual(E.tostring(x),E.tostring(y));continue
    k='footnoteRef' if 'footnotes' in n else 'endnoteRef';self.assertEqual([E.tostring(e.getparent()) for e in x.iter(q(k))],[E.tostring(e.getparent()) for e in y.iter(q(k))])
 def test_mixed_marker_run_protects_only_that_run(self):
  def fn(p):
   r=parse(p.parts['word/footnotes.xml']);m=r.findall(q('footnote'))[2].find('w:p/w:r',NS);E.SubElement(m,q('t')).text='混合编号文字';p.parts['word/footnotes.xml']=E.tostring(r)
  p=self.edit(fn);fs=findings(check(p));self.assertTrue(any(f['property']=='protected_marker' and f['status']=='review' for f in fs));self.assertTrue(any(f['fixable'] and f['locator'].get('run')==3 for f in fs))
 def test_complex_field_note_text_readonly_others_actionable(self):
  fs=findings(check(S/'protected.docx'));complex_=[f for f in fs if f['rule_id']=='R36' and f['locator'].get('note_id')=='4'];self.assertTrue(complex_);self.assertFalse(any(f['fixable'] for f in complex_));self.assertTrue(any(f['fixable'] and f['locator'].get('note_id')=='1' for f in fs))
 def test_broken_relations_readonly_not_repaired(self):
  p=S/'broken.docx';r=check(p);self.assertTrue(r['notes']['inventory']['issues']);self.assertFalse(any(f['fixable'] for f in findings(r) if f['rule_id']=='R36' and f['locator'].get('note_id')=='1'));self.assertTrue(any(f['property']=='relationship' for f in findings(r)))
 def test_nonstandard_part_name_valid_via_relationship(self):
  def fn(p):
   p.parts['word/private-notes.xml']=p.parts.pop('word/footnotes.xml');rels=parse(p.parts['word/_rels/document.xml.rels']);ct=parse(p.parts['[Content_Types].xml'])
   for e in rels:
    if e.get('Target')=='footnotes.xml':e.set('Target','private-notes.xml')
   for e in ct:
    if e.get('PartName')=='/word/footnotes.xml':e.set('PartName','/word/private-notes.xml')
   p.parts['word/_rels/document.xml.rels']=E.tostring(rels);p.parts['[Content_Types].xml']=E.tostring(ct)
  p=self.edit(fn);r=self.fix(path=p,m=manifest(p));self.assertEqual(inventory(p)['parts']['footnote'],'word/private-notes.xml');self.assertIn('word/private-notes.xml',Package(r['output']).parts)
 def test_missing_relation_does_not_trust_filename(self):
  def fn(p):
   root=parse(p.parts['word/_rels/document.xml.rels'])
   for e in list(root):
    if e.get('Target')=='footnotes.xml':root.remove(e)
   p.parts['word/_rels/document.xml.rels']=E.tostring(root)
  p=self.edit(fn);v=inventory(p);self.assertNotIn('footnote',v['parts']);self.assertTrue(any('缺少' in r['reason'] for r in v['issues']))
 def test_wrong_content_type_is_not_executable(self):
  def fn(p):
   root=parse(p.parts['[Content_Types].xml'])
   for e in root:
    if e.get('PartName')=='/word/footnotes.xml':e.set('ContentType','text/xml')
   p.parts['[Content_Types].xml']=E.tostring(root)
  p=self.edit(fn);self.assertNotIn('footnote',inventory(p)['parts'])
 def test_duplicate_relationship_id_blocks_notes(self):
  def fn(p):
   r=parse(p.parts['word/_rels/document.xml.rels']);r[-1].set('Id',r[-2].get('Id'));p.parts['word/_rels/document.xml.rels']=E.tostring(r)
  p=self.edit(fn);self.assertFalse(inventory(p)['objects']);self.assertTrue(inventory(p)['issues'])
 def test_normal_zero_and_positive_system_types_not_id_sign(self):
  def fn(p):
   r=parse(p.parts['word/footnotes.xml']);r[1].set(q('id'),'50');r[2].set(q('id'),'0');p.parts['word/footnotes.xml']=E.tostring(r);p.root.find('.//w:footnoteReference',NS).set(q('id'),'0');p.parts['word/document.xml']=E.tostring(p.root)
  p=self.edit(fn);v=inventory(p);self.assertTrue(next(r for r in v['objects'] if r['kind']=='footnote' and r['note_id']=='0')['safe_relationship']);self.assertTrue(any(r['note_id']=='50' for r in v['systems']))
 def test_missing_marker_readonly(self):
  def fn(p):
   r=parse(p.parts['word/footnotes.xml']);e=r[2].find('.//w:footnoteRef',NS);e.getparent().remove(e);p.parts['word/footnotes.xml']=E.tostring(r)
  p=self.edit(fn);self.assertFalse(inventory(p)['objects'][0]['safe_relationship'])
 def test_custom_values_and_disabled_attributes_real_effect(self):
  m=deepcopy(self.m);s=m['note_scope']['template'];s['values']['footnote']={'font_cn':'仿宋','font_size':10.5,'line_multiple':None};s['sources']['footnote']={'font_cn':'user_confirmed','font_size':'user_confirmed','line_multiple':'not_enabled'};r=self.fix(m=m);self.assertTrue(any(f['expected']==10.5 and f['status']=='pass' for f in findings(r['after'])));self.assertFalse(any(f['property']=='line_multiple' and f['rule_id']=='R36' for f in findings(r['after'])));self.assertEqual(parse(Package(self.p).parts['word/footnotes.xml'])[2].find('w:p/w:pPr/w:spacing',NS).attrib,parse(Package(r['output']).parts['word/footnotes.xml'])[2].find('w:p/w:pPr/w:spacing',NS).attrib)
 def test_template_strict_types_ranges_sources(self):
  for prop,val in [('font_size',True),('font_size',float('nan')),('font_size',12.25),('font_size',25),('line_multiple',1.1),('font_cn','任意字体'),('font_cn',{'code':'exec'})]:
   s=school();s['values']['footnote'][prop]=val;s['sources']['footnote'][prop]='user_confirmed'
   with self.assertRaises(DemoError):template(s)
  s=school();s['values']['footnote']['font_size']=14
  with self.assertRaises(DemoError):template(s)
  s=school();s['execute']='code'
  with self.assertRaises(DemoError):template(s)
 def test_scope_system_unknown_hash_and_unconfirmed_rejected(self):
  for prop,val in [('input_sha256','0'*64),('objects',['footnote:-1:1']),('confirmed',False),('objects',[1])]:
   s=deepcopy(self.m['note_scope']);s[prop]=val
   with self.assertRaises(DemoError):validate_scope(Package(self.p),s)
 def test_whitelist_rejects_marker_text_and_unselected_attributes(self):
  from core.engine import _preservation
  f=next(f for f in findings(check(self.p)) if f['fixable']);p=Package(self.p);before=_preservation(p,[f]);root=parse(p.parts['word/footnotes.xml']);root[2].find('.//w:footnoteRef',NS).set(q('id'),'9');p.parts['word/footnotes.xml']=E.tostring(root);self.assertNotEqual(before,_preservation(p,[f]))
 def test_session_partial_multiround_and_previous_bytes(self):
  s=self.session();s.set_selection([f['key'] for f in s.eligible() if f['rule_id'] in ('R36','R37')][:1]);self.assertTrue(s.generate(),s.error);first=Path(s.result['output']);raw=first.read_bytes();self.assertTrue(s.next_round(),s.error);s.set_selection([f['key'] for f in s.eligible() if f['rule_id'] in ('R36','R37')]);self.assertTrue(s.generate(),s.error);self.assertEqual(first.read_bytes(),raw);self.assertEqual(len(s.history),2);self.assertTrue(s.note_confirmed)
 def test_scope_template_and_mode_invalidate(self):
  s=self.session();d=deepcopy(s.note_draft);d['objects']=d['objects'][:1];s.edit_notes(d);self.assertIsNone(s.report);self.assertIsNone(s.note_confirmed);self.assertFalse(s.confirm_and_check());s.confirm_notes();self.assertTrue(s.confirm_and_check());s.set_mode('extended');self.assertIsNone(s.report)
 def test_supplement_export_reload_and_sources(self):
  s=self.session();raw=s.note_template_bytes();s.import_note_template(raw);self.assertEqual(json.loads(raw),s.note_draft['template']);self.assertTrue(s.note_confirmed) # identical configuration does not invalidate
 def test_project_restores_actual_check_and_historical_parts(self):
  s=self.session();s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R36'][:1]);self.assertTrue(s.generate(),s.error);self.assertTrue(s.next_round(),s.error);s.prepare_project();other=WebSession(self.d/'web');other.stage_project(s.project_download());r=other.restore_project(acknowledged=True);self.assertTrue(r.report,r.error);self.assertEqual(r.note_draft,s.note_draft);self.assertEqual(r.report['notes'],s.report['notes']);self.assertEqual(len(r.history),1);r.set_selection([f['key'] for f in r.eligible() if f['rule_id'] in ('R36','R37')]);self.assertTrue(r.generate(),r.error)
 def test_project_draft_stays_unconfirmed(self):
  s=self.session();d=deepcopy(s.note_draft);d['confirmed']=False;d['objects']=d['objects'][:2];s.edit_notes(d);s.prepare_project();other=WebSession(self.d/'web');other.stage_project(s.project_download());r=other.restore_project(acknowledged=True);self.assertEqual(r.note_draft,d);self.assertIsNone(r.report);self.assertIsNone(r.note_confirmed)
 def test_zip_and_readable_reports_include_notes_without_full_content(self):
  s=self.session();s.set_selection([f['key'] for f in s.eligible() if f['rule_id'] in ('R36','R37')]);self.assertTrue(s.generate(),s.error);z=zipfile.ZipFile(BytesIO(s.result_package()));self.assertIn('note-supplement.json',z.namelist());h=z.read('report.html').decode();self.assertIn('脚注与尾注检查范围',h);self.assertNotIn('尾注一前段正常',h);self.assertNotIn('/Volumes/',h)
 def test_separate_sessions_and_external_change_rejected(self):
  s=self.session();other=WebSession(self.d/'web');self.assertFalse(other.note_enabled);self.assertIsNone(other.note_draft);s.input_path.write_bytes(b'broken');self.assertFalse(s.check());self.assertIsNone(s.report)
 def test_existing_output_and_original_refused(self):
  with self.assertRaises(DemoError):fix_document(self.p,self.p,None,selected_rules=['R36'],mode='academic',classification_manifest=self.m)
  out=self.d/'exists.docx';out.write_bytes(b'existing')
  with self.assertRaises(DemoError):fix_document(self.p,out,None,selected_rules=['R36'],mode='academic',classification_manifest=self.m)
 def test_theme_and_style_priority_uses_existing_resolver(self):
  def fn(p):
   root=parse(p.parts['word/footnotes.xml']);run=root[2].find('w:p',NS).findall(q('r'))[2];rf=run.find('w:rPr/w:rFonts',NS);rf.attrib.pop(q('eastAsia'));rf.set(q('eastAsiaTheme'),'minorEastAsia');E.SubElement(run.find(q('rPr')),q('lang'),{q('eastAsia'):'zh-CN'});p.parts['word/footnotes.xml']=E.tostring(root);settings=parse(p.parts['word/settings.xml']);settings.find(q('themeFontLang')).set(q('eastAsia'),'zh-CN');p.parts['word/settings.xml']=E.tostring(settings)
  p=self.edit(fn);f=next(f for f in findings(check(p)) if f['rule_id']=='R36' and f['locator'].get('note_id')=='1' and f['property']=='font_cn' and f['locator'].get('run')==3);self.assertIn(f['status'],('problem','pass'));self.assertTrue(f['font_evidence']['eastAsia']['font']);self.assertIn('theme',str(f['font_evidence']).lower())
 def test_unknown_note_language_does_not_force_size(self):
  def fn(p):
   root=parse(p.parts['word/footnotes.xml']);root[2].find('w:p',NS).findall(q('r'))[2].find(q('t')).text='العربية';p.parts['word/footnotes.xml']=E.tostring(root)
  p=self.edit(fn);self.assertTrue(any(f['property']=='protected_run' and '字符' in f['detail'] for f in findings(check(p))))
 def test_scope_exclusion_preserves_complete_other_note(self):
  m=deepcopy(self.m);m['note_scope']['objects']=['footnote:1:3'];r=self.fix(m=m);a,b=Package(self.p),Package(r['output']);self.assertEqual(a.parts['word/endnotes.xml'],b.parts['word/endnotes.xml']);self.assertEqual([E.tostring(x) for x in parse(a.parts['word/footnotes.xml'])][3:],[E.tostring(x) for x in parse(b.parts['word/footnotes.xml'])][3:]);self.assertEqual(len(r['changes']),3)
 def test_output_external_modification_disables_downloads(self):
  s=self.session();s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R36'][:1]);self.assertTrue(s.generate());Path(s.result['output']).write_bytes(b'modified')
  with self.assertRaises(DemoError):s.downloads()
 def test_note_rules_change_drops_previous_confirmation_and_preview(self):
  s=self.session();d=deepcopy(s.note_draft);d['template']['values']['endnote']['font_size']=14;d['template']['sources']['endnote']['font_size']='user_confirmed';s.edit_notes(d);self.assertIsNone(s.confirmed);self.assertFalse(s.preview_targets());self.assertEqual(s.selected,[])
 def test_cache_and_checked_reports_are_not_mutation_instances(self):
  s=self.session();old=deepcopy(s.report);inv=deepcopy(s.note_inventory());s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R36']);self.assertTrue(s.generate());self.assertEqual(s.report,old);self.assertEqual(s.note_inventory(),inv)
 def test_streamlit_notes_inventory_context_and_downloads(self):
  from streamlit.testing.v1 import AppTest
  s=self.session();app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20);app.session_state['workflow']=s;app.run();show(app,2,'note');self.assertFalse(app.exception);self.assertTrue(any(x.label=='启用脚注与尾注检查' and x.value for x in app.checkbox));self.assertTrue(any('复杂' in x.value for x in app.warning));self.assertTrue(any('ID' in getattr(x.value,'columns',[]) for x in app.dataframe))
 def test_combined_main_and_note_transaction_preserves_nonselected_parts(self):
  m=deepcopy(self.m);m['paragraph_types']['2']='body';r=fix_document(self.p,self.d/'combined.docx',None,selected_rules=['R07','R36'],mode='academic',classification_manifest=m);self.assertTrue(any(c['rule_id']=='R36' for c in r['changes']));self.assertEqual(Package(self.p).parts['word/endnotes.xml'],Package(r['output']).parts['word/endnotes.xml'])
 def test_malformed_relationship_xml_becomes_readonly_evidence(self):
  p=self.edit(lambda p:p.parts.update({'word/_rels/document.xml.rels':b'<broken'}));r=check(p);self.assertTrue(r['notes']['inventory']['issues']);self.assertFalse(any(f['fixable'] for f in findings(r)))
 def test_whitelist_does_not_hide_unselected_empty_format_removal(self):
  from core.engine import _preservation
  def fn(p):
   root=parse(p.parts['word/footnotes.xml']);E.SubElement(root[4].find('w:p',NS),q('rPr'));p.parts['word/footnotes.xml']=E.tostring(root)
  source=self.edit(fn);p=Package(source);f=next(f for f in findings(check(source)) if f['fixable']);before=_preservation(p,[f]);root=parse(p.parts['word/footnotes.xml']);e=root[4].find('w:p/w:rPr',NS);e.getparent().remove(e);p.parts['word/footnotes.xml']=E.tostring(root);self.assertNotEqual(before,_preservation(p,[f]))
 def test_duplicates_and_unknown_theme_remain_review(self):
  def fn(p):
   root=parse(p.parts['word/footnotes.xml']);pp=root[2].find('w:p/w:pPr',NS);E.SubElement(pp,q('spacing'),{q('line'):'360'});p.parts['word/footnotes.xml']=E.tostring(root)
  p=self.edit(fn);f=next(f for f in findings(check(p)) if f['rule_id']=='R36' and f['locator'].get('note_id')=='1' and f['property']=='line_multiple');self.assertEqual(f['status'],'review');self.assertIn('重复',f['detail'])
 def test_zip_markdown_does_not_embed_complete_note_previews(self):
  s=self.session();s.set_selection([f['key'] for f in s.eligible() if f['rule_id'] in ('R36','R37')]);self.assertTrue(s.generate());z=zipfile.ZipFile(BytesIO(s.result_package()))
  for n in ('report.html','report.json','recheck.md','changes.md'):self.assertNotIn('尾注一前段正常',z.read(n).decode())
 def test_preview_epoch_invalidation_on_note_scope_change(self):
  s=self.session();epoch=s.preview_epoch;d=deepcopy(s.note_draft);d['objects']=d['objects'][:1];s.edit_notes(d);self.assertGreater(s.preview_epoch,epoch);self.assertEqual(s.preview_jobs,{});self.assertEqual(s.selected,[])
 def test_cross_kind_shared_part_is_readonly(self):
  def fn(p):
   r=parse(p.parts['word/_rels/document.xml.rels']);r[-1].set('Target','footnotes.xml');p.parts['word/_rels/document.xml.rels']=E.tostring(r)
  p=self.edit(fn);self.assertFalse(inventory(p)['objects']);self.assertTrue(any('共享' in r['reason'] for r in inventory(p)['issues']))
 def test_formula_table_revision_protection_does_not_hide_other_runs(self):
  def fn(p):
   root=parse(p.parts['word/footnotes.xml']);n=root[2];paragraph=n.find(q('p'));E.SubElement(paragraph,'{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath');ins=E.SubElement(paragraph,q('ins'),{q('id'):'1',q('author'):'软件样本'});E.SubElement(E.SubElement(ins,q('r')),q('t')).text='保护修订';table=E.SubElement(n,q('tbl'));row=E.SubElement(table,q('tr'));cell=E.SubElement(row,q('tc'));cp=E.SubElement(cell,q('p'));cr=E.SubElement(cp,q('r'));E.SubElement(cr,q('t')).text='保护表格内容';p.parts['word/footnotes.xml']=E.tostring(root)
  p=self.edit(fn);r=self.fix(path=p,m=manifest(p));before=parse(Package(p).parts['word/footnotes.xml']);after=parse(Package(r['output']).parts['word/footnotes.xml']);self.assertEqual(E.tostring(before.find('.//w:tbl',NS)),E.tostring(after.find('.//w:tbl',NS)));self.assertEqual(E.tostring(before.find('.//w:ins',NS)),E.tostring(after.find('.//w:ins',NS)));self.assertTrue(any(f['status']=='review' for f in findings(r['after']) if f['locator'].get('note_id')=='1'));self.assertTrue(any(c['locator'].get('property')=='font_size' for c in r['changes']))

"""Qualified text only, immutable relationship/link structure, independent XML oracle."""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest import TestCase,mock
from io import BytesIO
import json,zipfile
from lxml import etree as E
from core import check_document,fix_document
from core.package import Package,DemoError,q,NS,parse,sha256
from core.text_runs import walk,select_run,relationship,R,REL
from core.formats import paragraph_unsafe
from scripts.reproduce_hyperlink_demo import session,selection,S
from scripts.verify_hyperlink_output import verify

class HyperlinkTests(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name);self.s=session(self.d/'web');self.p=Package(self.s.input_path)
 def fs(self,p=7):return [f for f in self.s.report['findings'] if f['locator'].get('paragraph')==p and not f.get('story_part')]
 def edit(self,fn):
  p=Package(S/'errors.docx');fn(p);p.parts['word/document.xml']=E.tostring(p.root)
  out=self.d/'edit.docx'
  with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
   for n,b in p.parts.items():z.writestr(n,b)
  return Package(out)
 def check(self,p):
  from core.table_text import rebind
  m=deepcopy(self.s.classification_confirmed);m['input_sha256']=p.hash;rebind(m,p.hash)
  return check_document(p.path,mode='academic',classification_manifest=m)
 def test_original_paragraph_unsafe_retained(self):self.assertTrue(paragraph_unsafe(self.p.paragraphs[6]));self.assertTrue(any(f['rule_id']=='R03' and f['status']=='problem' for f in self.fs()))
 def test_direct_numbers_not_inserted_link_numbers(self):
  r=walk(self.p,self.p.paragraphs[6]);self.assertEqual([x['locator'] for x in r['rows']],[{'run':1},{'link':1,'link_run':1},{'link':1,'link_run':2},{'run':2}]);self.assertEqual(select_run(self.p.paragraphs[6],{'run':2}).find(q('t')).text,' 链接后文 Word')
 def test_late_link_run_and_prefix_suffix_checked(self):
  fs=self.fs();self.assertTrue(any(f['rule_id']=='R05' and f['locator'].get('link_run')==2 and f['status']=='problem' for f in fs));self.assertEqual({f['locator'].get('run') for f in fs if f['rule_id']=='R05' and f['status']=='problem'},{None,1,2})
 def test_repeated_text_shared_id_unique_keys(self):
  fs=[f for f in self.fs(8) if f['rule_id']=='R05' and f['locator'].get('link') in (1,2)];self.assertEqual(len(fs),2);self.assertNotEqual(fs[0]['key'],fs[1]['key']);self.assertEqual([f['status'] for f in fs],['problem','pass'])
 def test_direct_character_style_and_theme_priority(self):
  fs=self.fs(8);self.assertTrue(all(f['status']=='pass' for f in fs if f['locator'].get('link')==3));self.assertTrue(any(f['actual']=={'pt':15.0} and f['locator'].get('link')==1 for f in fs));self.assertTrue(all(f['status']=='pass' for f in self.fs() if f['locator'].get('link_run')==1))
 def test_reference_only_configured_props_and_paragraph_stays_protected(self):
  fs=self.fs(10);self.assertEqual({f['locator']['property'] for f in fs if f['locator'].get('link_run')},{'font_eastAsia','size'});self.assertTrue(any(f['locator'].get('property')=='line_spacing' and f['status']=='review' and not f['fixable'] for f in fs))
 def test_body_paragraph_properties_never_qualify(self):
  fs=[f for f in self.fs() if f['rule_id'] in ('R06','R07')];self.assertEqual(len(fs),2);self.assertTrue(all(f['status']=='review' and not f['fixable'] for f in fs))
 def test_note_relationships_are_own_story_not_main(self):
  proofs=[]
  for kind in ('footnote','endnote'):
   part='word/'+kind+'s.xml';root=parse(self.p.parts[part]);p=next(n for n in root if n.get(q('id'))=='1').find(q('p'));r=walk(self.p,p,part);self.assertEqual(r['supported_links'],1);proofs.append(r['rows'][-1]['evidence'])
  self.assertNotEqual(proofs[0]['target_sha256'],proofs[1]['target_sha256']);self.assertTrue(all(x['target_opened'] is False for x in proofs));self.assertTrue(all('document.xml' not in x['relationship_part'] for x in proofs))
 def test_missing_own_note_relationship_never_falls_back(self):
  p=self.edit(lambda p:p.parts.pop('word/_rels/footnotes.xml.rels'));r=self.check(p);fs=[f for f in r['findings'] if f.get('story_part')=='word/footnotes.xml' and 'link' in f['locator']];self.assertTrue(fs);self.assertTrue(all(f['status']=='review' and not f['fixable'] for f in fs))
 def test_renamed_note_part_resolves_renamed_relationship(self):
  def change(p):
   p.parts['word/renamed.xml']=p.parts.pop('word/footnotes.xml');p.parts['word/_rels/renamed.xml.rels']=p.parts.pop('word/_rels/footnotes.xml.rels')
   for part,attr,old,new in [('word/_rels/document.xml.rels','Target','footnotes.xml','renamed.xml'),('[Content_Types].xml','PartName','/word/footnotes.xml','/word/renamed.xml')]:
    root=parse(p.parts[part])
    for e in root:
     if e.get(attr)==old:e.set(attr,new)
    p.parts[part]=E.tostring(root)
  p=self.edit(change);fs=[f for f in self.check(p)['findings'] if f.get('story_part')=='word/renamed.xml' and f['locator'].get('link_run')];self.assertTrue(fs);self.assertTrue(any(f['fixable'] for f in fs));self.assertTrue(all(f['link_evidence']['relationship_part']=='word/_rels/renamed.xml.rels' for f in fs))
 def test_duplicate_missing_wrong_relationships_block(self):
  for mode in ('duplicate','missing','type','internal','badurl'):
   with self.subTest(mode=mode):
    p=Package(S/'errors.docx');part='word/_rels/document.xml.rels';root=parse(p.parts[part]);e=next(e for e in root if e.get('Id')=='demoLink')
    if mode=='duplicate':root.append(deepcopy(e))
    elif mode=='missing':root.remove(e)
    elif mode=='type':e.set('Type',R+'/image')
    elif mode=='internal':e.attrib.pop('TargetMode')
    else:e.set('Target','javascript:alert(1)')
    p.parts[part]=E.tostring(root);w=walk(p,p.paragraphs[6]);self.assertEqual(w['supported_links'],0);self.assertTrue(w['issues'])
 def test_invalid_and_anchor_and_nested_complex_not_allowed(self):
  p=Package(S/'protected.docx');r=walk(p,p.paragraphs[7]);self.assertEqual(len(r['issues']),2);self.assertEqual(r['supported_links'],1)
  p.paragraphs[6].find(q('hyperlink')).set(q('anchor'),'bookmark');self.assertFalse(walk(p,p.paragraphs[6])['supported_links'])
 def test_fields_revision_sdt_toc_do_not_gain_permission(self):
  for mode in ('field','revision','sdt','toc'):
   with self.subTest(mode=mode):
    p=Package(S/'errors.docx');e=p.paragraphs[6]
    if mode=='field':E.SubElement(e.find(q('hyperlink'))[0],q('fldChar')).set(q('fldCharType'),'begin')
    elif mode in ('revision','sdt'):
     body=e.getparent();i=body.index(e);wrap=E.Element(q('ins' if mode=='revision' else 'sdt'));body.remove(e);body.insert(i,wrap);wrap.append(e)
    else:
     pp=e.find(q('pPr'))
     if pp is None:pp=E.Element(q('pPr'));e.insert(0,pp)
     E.SubElement(pp,q('pStyle')).set(q('val'),'TOC1')
    self.assertFalse(walk(p,e)['supported_links'])
 def test_rpr_order_and_nonordinary_children_block(self):
  for mode in ('late','duplicate','math'):
   p=Package(S/'errors.docx');r=p.paragraphs[6].find(q('hyperlink'))[0]
   if mode=='late':rp=r[0];r.remove(rp);r.append(rp)
   elif mode=='duplicate':r.append(E.Element(q('rPr')))
   else:r.append(E.Element('{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath'))
   self.assertFalse(walk(p,p.paragraphs[6])['supported_links'])
 def test_locator_only_bounded_integer_no_xpath(self):
  for loc in ({'link':'1][//w:r','link_run':1},{'link':True,'link_run':1},{'link':1,'link_run':0},{'link':1,'run':1,'link_run':1},{'link_run':1}):
   with self.assertRaises(DemoError):select_run(self.p.paragraphs[6],loc)
 def test_r33_link_paragraph_still_readonly_other_safe_paragraph_supported(self):
  self.assertTrue(any(f['rule_id']=='R33' and f['status']=='review' and not f['fixable'] for f in self.fs(7)));self.assertTrue(any(f['rule_id']=='R33' and f['status']=='problem' and f['fixable'] for f in self.fs(12)))
 def test_full_independent_oracle_and_control_same_bytes(self):
  r=fix_document(self.s.input_path,self.d/'all.docx',self.s.confirmed,selected_keys=selection(self.s),**self.s._rules_arguments());self.assertTrue(verify(self.s.input_path,r['output'])['only_selected_attributes_changed']);self.assertEqual(Path(r['output']).read_bytes(),(S/'correct.docx').read_bytes());self.assertEqual(r['after']['summary']['problem_count'],8)
 def test_one_link_size_only_preserves_neighbors_style_and_targets(self):
  e=next(x for x in json.loads((S/'independent-errors.json').read_text())['allowed_repairs'] if x.get('paragraph')==7 and x.get('link_run')==2 and x['property']=='size');f=next(f for f in self.fs() if f['rule_id']=='R05' and f['locator'].get('link_run')==2);r=fix_document(self.s.input_path,self.d/'one.docx',self.s.confirmed,selected_keys=[f['key']],**self.s._rules_arguments());self.assertTrue(verify(self.s.input_path,r['output'],[e])['only_selected_attributes_changed'])
 def test_note_only_keeps_main_and_other_story_bytes(self):
  fs=[f for f in self.s.eligible() if f.get('story_part')=='word/footnotes.xml' and f['locator'].get('link_run')];r=fix_document(self.s.input_path,self.d/'note.docx',self.s.confirmed,selected_keys=[f['key'] for f in fs],**self.s._rules_arguments());new=Package(r['output']);self.assertEqual(self.p.parts['word/document.xml'],new.parts['word/document.xml']);self.assertEqual(self.p.parts['word/endnotes.xml'],new.parts['word/endnotes.xml'])
 def test_idempotent_all_selected_correct_no_extra_writes(self):
  from core.table_text import rebind
  p=Package(S/'correct.docx');m=deepcopy(self.s.classification_confirmed);m['input_sha256']=p.hash;rebind(m,p.hash);r=check_document(p.path,mode='academic',classification_manifest=m);self.assertFalse(any(f['status']=='problem' and f['locator'].get('link_run') for f in r['findings']))
  out=fix_document(p.path,self.d/'stable.docx',None,mode='academic',classification_manifest=m,selected_rules=['R04']);self.assertEqual(p.path.read_bytes(),Path(out['output']).read_bytes())
 def test_rehearsal_adoption_zero_refix_and_doubleclick_once(self):
  self.s.set_selection(selection(self.s));self.assertTrue(self.s.rehearse(),self.s.rehearsal_error);i=self.s.rehearsal['id'];self.assertEqual(self.s.generation_count,0)
  with mock.patch('web.session.fix_document',side_effect=AssertionError('refix')):self.assertTrue(self.s.adopt_rehearsal(i,acknowledged=True),self.s.rehearsal_error);self.assertTrue(self.s.adopt_rehearsal(i,acknowledged=True))
  self.assertEqual(self.s.generation_count,1);self.assertEqual(self.s.downloads()['fixed.docx'],(S/'correct.docx').read_bytes())
 def test_two_step_plan_ordinary_links_and_safe_other_r33(self):
  chosen=selection(self.s)+[f['key'] for f in self.s.eligible() if f['locator'].get('paragraph')==12 and f['rule_id'] in ('R05','R33')];self.s.set_selection(chosen);self.assertTrue(self.s.correction_plan()['two_steps']);self.assertTrue(self.s.rehearse_plan(),self.s.rehearsal_error);self.assertEqual(self.s.rehearsal_view()['engine_calls'],2);self.assertEqual(self.s.rehearsal['transactions'][0]['result']['output'],self.s.rehearsal['transactions'][1]['input']);self.assertTrue(any(f['rule_id']=='R33' and f['status']=='review' for f in self.s.rehearsal['transactions'][1]['result']['after']['findings'] if f['locator'].get('paragraph')==7));self.assertTrue(self.s.adopt_plan(self.s.rehearsal['id'],acknowledged=True),self.s.rehearsal_error)
 def test_original_direct_conflict_not_weakened(self):
  keys=[f['key'] for f in self.s.eligible() if f['locator'].get('paragraph')==12 and f['rule_id'] in ('R05','R33')]
  with self.assertRaisesRegex(DemoError,'分轮'):fix_document(self.s.input_path,self.d/'no.docx',self.s.confirmed,selected_keys=keys,**self.s._rules_arguments())
 def test_whitelist_does_not_allow_target_style_or_unselected_font(self):
  from core.engine import _preservation
  f=next(f for f in self.fs() if f['rule_id']=='R05' and f['locator'].get('link_run')==2);p=Package(S/'errors.docx');r=select_run(p.paragraphs[6],f['locator']);r.find('w:rPr/w:rStyle',NS).set(q('val'),'Other');self.assertNotEqual(_preservation(self.p,[f]),_preservation(p,[f]))
  p=Package(S/'errors.docx');p.paragraphs[6].find(q('hyperlink')).set(q('tooltip'),'changed');self.assertNotEqual(_preservation(self.p,[f]),_preservation(p,[f]))
 def test_report_positions_and_unvisited_target_evidence(self):
  from web.presentation import position
  f=next(f for f in self.fs() if f['locator'].get('link_run')==2);self.assertIn('链接1',position(f['locator']));self.assertFalse(f['link_evidence']['target_opened']);self.assertNotIn('https:',json.dumps(f['link_evidence']));self.assertEqual(self.s.report['coverage']['hyperlink_text']['supported_text_locators'],11)
 def test_external_change_invalidate_adoption(self):
  self.s.set_selection(selection(self.s));self.s.rehearse();i=self.s.rehearsal['id'];Path(self.s.rehearsal['result']['output']).write_bytes(b'bad');self.assertFalse(self.s.adopt_rehearsal(i,acknowledged=True));self.assertFalse(self.s.history)
 def test_project_restore_rechecks_without_reusing_authorization(self):
  from web.session import WebSession
  self.s.set_selection(selection(self.s));self.s.rehearse();raw=self.s.prepare_project();t=WebSession(self.d/'restore');t.stage_project(raw);r=t.restore_project(acknowledged=True);self.assertIsNone(r.rehearsal);self.assertEqual(r.report['findings'],self.s.report['findings']);self.assertEqual(r.selected,self.s.selected)
 def test_sessions_never_share_mutable_roots_or_authorization(self):
  t=session(self.d/'other');self.s.set_selection(selection(self.s));self.s.rehearse();self.assertIsNone(t.rehearsal);self.assertFalse(t.history);self.assertEqual(self.s.input_bytes,t.input_bytes);self.assertEqual(t.report['summary']['problem_count'],24)
 def test_execution_binding_covers_new_controlled_walker(self):
  from web.rehearsal_session import execution_hash
  original=Path.read_bytes
  def changed(path):return original(path)+(b'changed' if path.name=='text_runs.py' else b'')
  before=execution_hash()
  with mock.patch.object(Path,'read_bytes',changed):self.assertNotEqual(before,execution_hash())
 def test_hansi_slot_selected_without_overwriting_ascii(self):
  p=self.edit(lambda p:setattr(p.paragraphs[6].find(q('hyperlink'))[1].find(q('t')),'text','后半 é'))
  m=deepcopy(self.s.classification_confirmed);m['input_sha256']=p.hash
  from core.table_text import rebind
  rebind(m,p.hash);m.pop('citation_scope');r=check_document(p.path,mode='academic',classification_manifest=m);f=next(f for f in r['findings'] if f['rule_id']=='R04' and f['locator'].get('paragraph')==7 and f['locator'].get('link_run')==2);self.assertEqual(f['actual'],{'hAnsi':'Arial'});out=fix_document(p.path,self.d/'hansi.docx',None,mode='academic',classification_manifest=m,selected_keys=[f['key']]);rr=Package(out['output']).paragraphs[6].find(q('hyperlink'))[1].find('w:rPr/w:rFonts',NS);self.assertEqual(rr.get(q('hAnsi')),'Times New Roman');self.assertIsNone(rr.get(q('ascii')));self.assertIsNone(rr.get(q('eastAsia')))
 def test_cross_paragraph_field_cache_not_qualified(self):
  p=Package(S/'errors.docx');r=E.SubElement(p.paragraphs[5],q('r'));E.SubElement(r,q('fldChar')).set(q('fldCharType'),'begin');E.SubElement(r,q('instrText')).text='TOC';self.assertFalse(walk(p,p.paragraphs[6])['supported_links']);self.assertIn('目录',walk(p,p.paragraphs[6])['context_reason'])
 def test_independent_whitelist_rejects_unselected_color(self):
  from core.engine import _preservation
  f=next(f for f in self.fs() if f['rule_id']=='R05' and f['locator'].get('link_run')==2);p=Package(S/'errors.docx');r=select_run(p.paragraphs[6],f['locator']);E.SubElement(r.find(q('rPr')),q('color')).set(q('val'),'FF0000');self.assertNotEqual(_preservation(self.p,[f]),_preservation(p,[f]))

 def test_protected_superscript_link_fragment_not_counted_as_supported_text(self):
  def change(p):
   part='word/footnotes.xml';root=parse(p.parts[part]);note=next(n for n in root if n.get(q('id'))=='1');r=note.find('w:p/w:hyperlink/w:r',NS);E.SubElement(r.find(q('rPr')),q('vertAlign')).set(q('val'),'superscript');p.parts[part]=E.tostring(root)
  p=self.edit(change);report=self.check(p);f=next(f for f in report['findings'] if f.get('story_part')=='word/footnotes.xml' and f['locator'].get('link_run')==1 and f.get('property')=='protected_run');self.assertEqual(f['status'],'review');self.assertFalse(f['fixable']);self.assertEqual(f['text_structure'],'受保护链接对象/片段');self.assertNotIn('直属普通run已核对',f['detail']);self.assertEqual(report['coverage']['hyperlink_text']['supported_text_locators'],10);self.assertEqual(report['coverage']['hyperlink_text']['protected_records'],2)

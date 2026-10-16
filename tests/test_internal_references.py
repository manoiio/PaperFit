"""R44 evidence + unchanged original protections. No Office/API/local history dependency."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase,mock
from lxml import etree as E
import json,zipfile
from core.package import Package,q,NS,DemoError
from core import check_document,fix_document
from core.internal_refs import inventory,resolve_target,configure,make_scope,template,field_target
from core.text_runs import walk
from scripts.reproduce_internal_reference_demo import session,selection,S
from scripts.verify_internal_reference_output import verify
from scripts.build_internal_reference_sample import write_parts,bookmark,R,REL,CT

class InternalReferenceTests(TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name);self.s=session(self.d/'s');self.pkg=Package(self.s.input_path)
 def altered(self,fn):
  p=Package(S/'errors.docx');fn(p);p.parts['word/document.xml']=E.tostring(p.root);out=self.d/'altered.docx';write_parts(out,p.parts);return Package(out)
 def report(self,p):
  from core.table_text import rebind
  m=deepcopy(self.s.classification_confirmed);m['input_sha256']=p.hash;rebind(m,p.hash);return check_document(p.path,mode='academic',classification_manifest=m)
 def test_author_target_oracle_and_fault_group_counts(self):
  r=inventory(self.pkg);oracle=json.loads((S/'independent-plan.json').read_text())
  for name,status in oracle['targets'].items():self.assertEqual(resolve_target(self.pkg,name)['state'],'pass' if status=='valid' else 'problem')
  bad=[g for g in r['groups'] if g['status']=='problem'];self.assertEqual(len(bad),1);self.assertEqual(len(bad[0]['references']),3);self.assertEqual(len([f for f in self.s.report['findings'] if f['rule_id']=='R44' and f['status']=='problem']),1)
 def test_readonly_index_never_writes_and_immutable_copy(self):
  raw=self.pkg.raw;r=inventory(self.pkg);r['bookmarks'].clear();self.assertEqual(len(inventory(self.pkg)['bookmarks']),4);self.assertEqual(self.pkg.path.read_bytes(),raw);self.assertFalse(self.pkg.story_roots)
  with self.assertRaises(TypeError):self.pkg._internal_reference_lookup['x']='bad'
 def test_default_old_config_has_no_r44_or_internal_text(self):
  m=deepcopy(self.s.classification_confirmed);m.pop('reference_scope');r=check_document(self.pkg.path,mode='academic',classification_manifest=m);self.assertFalse(any(f['rule_id']=='R44' for f in r['findings']));configure(self.pkg,m);self.assertEqual(walk(self.pkg,self.pkg.paragraphs[2])['supported_links'],0)
 def test_r44_does_not_authorize_text_without_separate_flag(self):
  p=self.pkg;configure(p,{'reference_scope':{**self.s.reference_manifest(),'template':{**self.s.reference_draft['template'],'internal_text':False}}});self.assertEqual(walk(p,p.paragraphs[2])['supported_links'],0)
 def test_simple_and_split_complex_fields_and_cache_not_truth(self):
  r=inventory(self.pkg);fields=r['fields'];self.assertEqual(next(f for f in fields if f['kind']=='REF')['target'],'_TocTarget');f=next(f for f in r['references'] if f['kind']=='PAGEREF');self.assertTrue(f['cached_result_present']);self.assertEqual(f['state'],'problem')
 def test_page_seq_styleref_not_bookmark_references(self):
  r=inventory(self.pkg);self.assertTrue({'PAGE','SEQ','STYLEREF'}<={f['kind'] for f in r['fields']});self.assertFalse(any(f['kind'] in ('PAGE','SEQ','STYLEREF') for f in r['references']))
 def test_missing_story_relation_downgrades_absence(self):
  def fn(p):
   root=E.fromstring(p.parts['word/_rels/document.xml.rels']);root.remove(next(e for e in root if e.get('Type')==R+'/footnotes'));p.parts['word/_rels/document.xml.rels']=E.tostring(root)
  p=self.altered(fn);self.assertFalse(inventory(p)['complete']);self.assertEqual(resolve_target(p,'MissingTarget')['state'],'review')
 def test_wrong_ct_and_orphan_part_do_not_fake_complete(self):
  def fn(p):
   root=E.fromstring(p.parts['[Content_Types].xml']);next(e for e in root if e.get('PartName')=='/word/footnotes.xml').set('ContentType','wrong');p.parts['[Content_Types].xml']=E.tostring(root)
  p=self.altered(fn);self.assertFalse(inventory(p)['complete']);self.assertEqual(resolve_target(p,'MissingTarget')['state'],'review')
 def test_note_renamed_part_and_own_story_evidence(self):
  def fn(p):
   p.parts['word/renamed-note.xml']=p.parts.pop('word/footnotes.xml');r=E.fromstring(p.parts['word/_rels/document.xml.rels']);next(e for e in r if e.get('Type')==R+'/footnotes').set('Target','renamed-note.xml');p.parts['word/_rels/document.xml.rels']=E.tostring(r);ct=E.fromstring(p.parts['[Content_Types].xml']);next(e for e in ct if e.get('PartName')=='/word/footnotes.xml').set('PartName','/word/renamed-note.xml');p.parts['[Content_Types].xml']=E.tostring(ct)
  p=self.altered(fn);r=resolve_target(p,'NoteTarget');self.assertEqual(r['state'],'pass');self.assertEqual(r['target_location']['part'],'word/renamed-note.xml');self.assertTrue(inventory(p)['complete'])
 def test_header_target_readonly_story_is_in_inventory(self):self.assertEqual(resolve_target(self.pkg,'HeaderTarget')['target_location']['part'],'word/header1.xml');self.assertFalse(any(f.get('story_part')=='word/header1.xml' and f['fixable'] for f in self.s.report['findings']))
 def test_duplicate_name_invalid_boundary_and_orphan_end_review(self):
  p=Package(S/'protected.docx');self.assertEqual(resolve_target(p,'_TocTarget')['state'],'review');self.assertTrue(any('孤立' in b['reason'] for b in inventory(p)['bookmarks']))
 def test_reversed_end_and_duplicate_ids_never_valid(self):
  def fn(p):
   para=p.paragraphs[1];end=para.find(q('bookmarkEnd'));para.remove(end);para.insert(0,end)
  p=self.altered(fn);self.assertEqual(resolve_target(p,'_TocTarget')['state'],'review')
 def test_case_not_guessed_and_underscore_not_filtered(self):
  self.assertEqual(resolve_target(self.pkg,'_toctarget')['state'],'review');self.assertEqual(resolve_target(self.pkg,'_TocTarget')['state'],'pass')
 def test_unknown_name_and_table_column_bounds_review(self):
  p=self.altered(lambda p:p.root.find('.//'+q('bookmarkStart')).set(q('colFirst'),'0'));self.assertEqual(resolve_target(p,'_TocTarget')['state'],'review');self.assertEqual(resolve_target(self.pkg,'中文目标')['state'],'review')
 def test_unknown_container_marks_inventory_incomplete(self):
  p=self.altered(lambda p:E.SubElement(p.paragraphs[-1],q('txbxContent')));self.assertFalse(inventory(p)['complete']);self.assertEqual(resolve_target(p,'MissingTarget')['state'],'review')
 def test_unknown_switch_and_target_forms_review(self):
  for instr in ('REF _TocTarget \\d ,','PAGEREF _TocTarget \\unknown','REF "two words"'):
   f={'instruction':instr,'balanced':True,'reliable':True};self.assertTrue(field_target(f)['reason'])
 def test_crossparagraph_complex_field_keeps_positions(self):
  def fn(p):
   a=p.paragraphs[7];runs=a.findall(q('r'));end=runs[-1];a.remove(end);p.paragraphs[8].append(end)
  r=inventory(self.altered(fn));f=next(f for f in r['fields'] if f['kind']=='REF');self.assertEqual(len(f['positions']),2);self.assertTrue(f['balanced'])
 def test_broken_field_is_review_not_cache_pass(self):
  def fn(p):
   a=p.paragraphs[7];a.remove(a.findall(q('r'))[-1])
  r=inventory(self.altered(fn));self.assertTrue(any(f['state']=='review' for f in r['references'] if f['kind']=='REF'))
 def test_nested_instruction_is_not_flattened_to_valid_target(self):
  from core.toc import parse_fields
  def fn(p):
   parent=p.paragraphs[7];r=E.Element(q('r'));e=E.SubElement(r,q('fldChar'));e.set(q('fldCharType'),'begin');parent.insert(2,r)
  r=inventory(self.altered(fn));self.assertTrue(any(f['state']=='review' for f in r['references']))
 def test_ordinary_internal_late_run_and_repeated_link_identity(self):
  fs=[f for f in self.s.report['findings'] if f['rule_id']=='R05' and f['locator'].get('link_run')];self.assertEqual(len(fs),4);self.assertEqual(len({f['key'] for f in fs}),4);self.assertTrue(next(f for f in fs if f['locator'].get('paragraph')==3 and f['locator'].get('link_run')==2)['fixable'])
 def test_target_missing_or_mixed_target_link_not_fixable(self):
  p=self.altered(lambda p:p.paragraphs[2].find(q('hyperlink')).set('{'+R+'}id','nonexistent'));configure(p,self.report(p)['coverage']);self.assertEqual(walk(p,p.paragraphs[2])['supported_links'],0);self.assertTrue(walk(p,p.paragraphs[5])['issues'])
 def test_bookmark_invalid_target_reverts_protection(self):
  p=Package(S/'protected.docx');r=self.report(p);self.assertFalse(any(f['fixable'] and f['locator'].get('paragraph')==3 and f['locator'].get('link_run') for f in r['findings']))
 def test_r33_and_paragraph_protections_unchanged(self):
  fs=[f for f in self.s.report['findings'] if f['locator'].get('paragraph')==3 and f['rule_id'] in ('R06','R07')];self.assertTrue(all(f['status']=='review' and not f['fixable'] for f in fs));from core.citations import inventory as ci
  row=next(r for r in ci(self.pkg,[3])['objects'] if r['text']=='[1]');self.assertFalse(row['safe_structure'])
 def test_sdt_and_field_cache_links_do_not_qualify(self):
  def fn(p):
   par=p.paragraphs[2];h=par.find(q('hyperlink'));par.remove(h);f=E.SubElement(par,q('fldSimple'));f.set(q('instr'),'TOC');f.append(h)
  p=self.altered(fn);configure(p,self.report(p)['coverage']);self.assertEqual(walk(p,p.paragraphs[2])['supported_links'],0)
 def test_note_and_body_selected_sizes_only_independent_zip_oracle(self):
  r=fix_document(self.pkg.path,self.d/'fixed.docx',self.s.confirmed,selected_keys=selection(self.s),**self.s._rules_arguments());self.assertTrue(verify(self.pkg.path,r['output'])['only_selected_attributes_changed']);self.assertEqual(Path(r['output']).read_bytes(),(S/'correct.docx').read_bytes());self.assertEqual(r['after']['internal_references'],r['before']['internal_references']|{'input_sha256':r['after']['input_sha256']})
 def test_note_only_main_bytes_unchanged(self):
  key=next(f['key'] for f in self.s.eligible() if f['rule_id']=='R36' and f['locator'].get('link_run'));r=fix_document(self.pkg.path,self.d/'note.docx',self.s.confirmed,selected_keys=[key],**self.s._rules_arguments());new=Package(r['output']);self.assertEqual(self.pkg.parts['word/document.xml'],new.parts['word/document.xml']);self.assertEqual(self.pkg.parts['word/endnotes.xml'],new.parts['word/endnotes.xml'])
 def test_repeated_correct_no_byte_change(self):
  from core.table_text import rebind
  p=Package(S/'correct.docx');m=deepcopy(self.s.classification_confirmed);m['input_sha256']=p.hash;rebind(m,p.hash);r=fix_document(p.path,self.d/'stable.docx',None,mode='academic',classification_manifest=m,selected_rules=['R05','R21','R36','R37']);self.assertEqual(p.raw,Path(r['output']).read_bytes())
 def test_rehearsal_zero_refix_and_single_round_adoption(self):
  self.s.set_selection(selection(self.s));self.assertTrue(self.s.rehearse());i=self.s.rehearsal['id']
  with mock.patch('web.session.fix_document',side_effect=AssertionError('refix')):self.assertTrue(self.s.adopt_rehearsal(i,acknowledged=True),self.s.rehearsal_error);self.assertTrue(self.s.adopt_rehearsal(i,acknowledged=True))
  self.assertEqual(self.s.generation_count,1)
 def test_project_restore_rechecks_and_no_preview_authorization(self):
  from web.session import WebSession
  raw=self.s.prepare_project();n=WebSession(self.d/'new');n.stage_project(raw);m=n.restore_project(acknowledged=True);self.assertTrue(m.reference_draft['template']['internal_text']);self.assertEqual(m.report['summary'],self.s.report['summary']);self.assertIsNone(m.rehearsal)
 def test_scope_preflight_readonly_and_changed_config_invalidates(self):
  before=(self.s.revision,deepcopy(self.s.report),self.pkg.raw);p=self.s.scope_preflight();self.assertTrue(p['ready']);self.assertEqual(before,(self.s.revision,self.s.report,self.pkg.path.read_bytes()));self.assertTrue(next(r for r in p['areas'] if r['area']=='reference')['confirmed'])
  d=deepcopy(self.s.reference_draft);d['template']['internal_text']=False;self.s.edit_references(d);self.assertIsNone(self.s.report);self.assertFalse(self.s.downloads())
 def test_strict_template_and_hash_validation(self):
  for key,val in [('integrity',1),('integrity',False),('internal_text','yes'),('structure_version',2),('source','school')]:
   d=deepcopy(self.s.reference_draft['template']);d[key]=val
   with self.assertRaises(DemoError):template(d)
  d=deepcopy(self.s.reference_draft);d['input_sha256']='0'*64
  with self.assertRaises(DemoError):self.s.edit_references(d)
 def test_scope_isolated_between_sessions(self):
  s=session(self.d/'two',text=False);self.assertTrue(self.s.reference_draft['template']['internal_text']);self.assertFalse(s.reference_draft['template']['internal_text']);self.assertNotEqual(self.s.task_dir,s.task_dir)
 def test_complete_html_json_zip_r44_and_no_external_script(self):
  self.s.set_selection(selection(self.s));self.s.rehearse();self.s.adopt_rehearsal(self.s.rehearsal['id'],acknowledged=True);files=self.s.prepare_reading_export();self.assertIn(b'R44',files['report.html']);self.assertNotIn(b'<script',files['report.html']);self.assertTrue(json.loads(files['report.json'])['internal_references']['inventory_complete']);from io import BytesIO
  with zipfile.ZipFile(BytesIO(self.s.result_package())) as z:self.assertIn('reference-supplement.json',z.namelist())
 def test_toc_uses_same_target_evidence_without_enabling_cache_edits(self):
  from tests.test_toc import manifest,SAMPLE
  p=Package(SAMPLE/'automatic.docx');m=manifest(p.path);s=make_scope(p);s['confirmed']=True;m['reference_scope']=s;r=check_document(p.path,mode='academic',classification_manifest=m);self.assertTrue(all(x['status']=='pass' for x in r['toc']['rows']));self.assertTrue(all('共用R44' in x['evidence'] for x in r['toc']['rows']));self.assertTrue(all(not f['fixable'] for f in r['findings'] if f['rule_id'] in ('R31','R32')))
 def test_malformed_quotes_and_adjacent_switch_review(self):
  for instr in ('REF "_TocTarget','REF "_TocTarget"\\h','PAGEREF _TocTarget"'):
   self.assertTrue(field_target({'instruction':instr,'balanced':True})['reason'])
 def test_duplicate_relationship_id_never_proves_missing(self):
  def fn(p):
   r=E.fromstring(p.parts['word/_rels/document.xml.rels']);r.append(deepcopy(r[0]));p.parts['word/_rels/document.xml.rels']=E.tostring(r)
  p=self.altered(fn);self.assertEqual(resolve_target(p,'MissingTarget')['state'],'review')
 def test_unassociated_comments_story_incomplete(self):
  def fn(p):
   ct=E.fromstring(p.parts['[Content_Types].xml']);E.SubElement(ct,'{'+CT+'}Override',PartName='/word/comments.xml',ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml');p.parts['[Content_Types].xml']=E.tostring(ct);p.parts['word/comments.xml']=E.tostring(E.Element(q('comments')))
  p=self.altered(fn);self.assertFalse(inventory(p)['complete']);self.assertEqual(resolve_target(p,'MissingTarget')['state'],'review')
 def test_notes_abnormal_reference_marks_target_review(self):
  p=self.altered(lambda p:p.root.find('.//'+q('footnoteReference')).set(q('id'),'9'));self.assertEqual(resolve_target(p,'NoteTarget')['state'],'review');self.assertFalse(inventory(p)['complete'])
 def test_internal_anchor_unknown_attribute_and_doclocation_protected(self):
  for attr in (q('docLocation'),q('unknown')):
   p=self.altered(lambda p:p.paragraphs[2].find(q('hyperlink')).set(attr,'x'));r=self.report(p);self.assertFalse(any(f['fixable'] and f['locator'].get('paragraph')==3 and f['locator'].get('link_run') for f in r['findings']))
 def test_font_slots_safe_fix_retains_style_and_other_rpr(self):
  def fn(p):
   rp=p.paragraphs[2].findall(q('hyperlink'))[0].findall(q('r'))[1].find(q('rPr'));rf=E.Element(q('rFonts'));rf.set(q('eastAsia'),'黑体');rf.set(q('ascii'),'Arial');rf.set(q('hAnsi'),'Calibri');rp.insert(1,rf)
  p=self.altered(fn);report=self.report(p);fs=[f for f in report['findings'] if f['rule_id'] in ('R03','R04') and f['locator'].get('paragraph')==3 and f['locator'].get('link_run')==2];self.assertEqual(len(fs),2)
  m=deepcopy(self.s.classification_confirmed);from core.table_text import rebind
  m['input_sha256']=p.hash;rebind(m,p.hash);r=fix_document(p.path,self.d/'font.docx',None,mode='academic',classification_manifest=m,selected_keys=[fs[0]['key']]);new=Package(r['output']);a=p.paragraphs[2].findall(q('hyperlink'))[0];b=new.paragraphs[2].findall(q('hyperlink'))[0];rf=b.findall(q('r'))[1].find('w:rPr/w:rFonts',NS);self.assertEqual(rf.get(q('eastAsia')),'宋体');self.assertEqual(rf.get(q('ascii')),'Arial');self.assertEqual(rf.get(q('hAnsi')),'Calibri');rf.set(q('eastAsia'),'黑体');self.assertEqual(E.tostring(a,method='c14n'),E.tostring(b,method='c14n'));self.assertEqual(p.parts['word/_rels/document.xml.rels'],new.parts['word/_rels/document.xml.rels'])
 def test_two_step_other_safe_r33_and_internal_link_step(self):
  def fn(p):
   for e in list(p.paragraphs[4]):
    if e.tag in (q('bookmarkStart'),q('bookmarkEnd')):p.paragraphs[4].remove(e)
   r=p.paragraphs[4].find(q('r'));r.find(q('t')).text+='[1]';from core.engine import _ensure
   _ensure(_ensure(r,'rPr'),'sz').set(q('val'),'28')
  p=self.altered(fn);s=session(self.d/'plan',checked=False,source=p.path);s.enable_citations(True);d=deepcopy(s.citation_draft);d['objects']={r['id']:'citation' for r in s.citation_inventory()['objects']};s.edit_citations(d);pre=s.scope_preflight();self.assertTrue(s.confirm_scopes_and_check(pre['signature'],acknowledged=True),s.error)
  fs=[f for f in s.eligible() if f['rule_id']=='R05' and f['locator'].get('paragraph') in (3,5) or f['rule_id']=='R33' and f['locator'].get('paragraph')==5];self.assertEqual(len(fs),3);s.set_selection([f['key'] for f in fs]);self.assertTrue(s.correction_plan()['two_steps']);self.assertTrue(s.rehearse_plan(),s.rehearsal_error);self.assertTrue(s.adopt_plan(s.rehearsal['id'],acknowledged=True),s.rehearsal_error);self.assertTrue(s.result['after']['coverage']['reference_scope']['template']['internal_text']);self.assertEqual(resolve_target(Package(s.result['output']),'MissingTarget')['state'],'problem')
 def test_draft_project_restores_flags_without_confirm_or_check(self):
  from web.session import WebSession
  s=session(self.d/'draft',checked=False);raw=s.prepare_project();n=WebSession(self.d/'restored');n.stage_project(raw);m=n.restore_project(acknowledged=True);self.assertTrue(m.reference_enabled);self.assertTrue(m.reference_draft['template']['internal_text']);self.assertIsNone(m.report);self.assertIsNone(m.reference_confirmed)
 def test_configuration_or_input_change_invalidates_rehearsal(self):
  self.s.set_selection(selection(self.s));self.s.rehearse();i=self.s.rehearsal['id'];d=deepcopy(self.s.reference_draft);d['template']['internal_text']=False;self.s.edit_references(d);self.assertFalse(self.s.adopt_rehearsal(i,acknowledged=True));self.assertEqual(self.s.generation_count,0)
 def test_l05_rebind_config_only_no_stale_index_authorization(self):
  from core.caption_move import remap_manifest
  from core.toc import nodes
  m=deepcopy(self.s.classification_confirmed);out,mapping=remap_manifest(self.pkg,m,list(self.pkg.paragraphs),nodes(self.pkg),self.pkg.hash);self.assertEqual(out['reference_scope'],m['reference_scope'])
 def test_incomplete_target_inventory_cannot_authorize_internal_fix(self):
  p=self.altered(lambda p:E.SubElement(p.paragraphs[-1],q('txbxContent')));self.assertEqual(resolve_target(p,'_TocTarget')['state'],'review');r=self.report(p);self.assertFalse(any(f['fixable'] and f['locator'].get('paragraph')==3 and f['locator'].get('link_run') for f in r['findings']))
 def test_capacity_is_explicit_rejection_not_partial_success(self):
  with mock.patch('core.internal_refs.MAX_OBJECTS',2),self.assertRaisesRegex(DemoError,'上限'):inventory(Package(S/'errors.docx'))

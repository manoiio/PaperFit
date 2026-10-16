"""Precise citation evidence and independent pPr/run preservation, not global superscript bypass."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase,mock
import json
from lxml import etree as E
from core import check_document,fix_document
from core.package import Package,q,NS,DemoError
from core.engine import _ensure
from core.table_text import rebind
from scripts.reproduce_citation_paragraph_demo import session,selection,SAMPLE
from scripts.verify_citation_paragraph_output import verify

def finding(r,n,rid,prop=None):return next(f for f in r['findings'] if f['rule_id']==rid and f['locator'].get('paragraph')==n and (prop is None or f.get('property')==prop))
def proof(r,n):return next(p for p in r['coverage']['citation_paragraph_evidence'] if p['paragraph']==n)
class CitationParagraphTests(TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name);self.s=session(self.d/'web')
 def altered(self,fn,manifest=None):
  p=Package(SAMPLE/'errors.docx');fn(p);p.parts['word/styles.xml']=E.tostring(p.styles,encoding='UTF-8',xml_declaration=True);path=self.d/'altered.docx';path.write_bytes(p.bytes(True));m=deepcopy(self.s._rules_arguments()['classification_manifest']);m['input_sha256']=Package(path).hash;rebind(m,m['input_sha256'])
  if manifest:manifest(m)
  return check_document(path,mode='academic',classification_manifest=m,custom_rules_path=self.s.custom_rules_path)
 def test_known_three_rule_groups_and_inline_protection(self):
  r=self.s.report;self.assertEqual(len(selection(self.s)),14)
  for n in (3,4):
   for rid,prop in [('R06',None),('R07',None),('R13','before'),('R13','after'),('R13','alignment')]:self.assertEqual(finding(r,n,rid,prop)['status'],'problem')
   self.assertTrue(proof(r,n)['structurally_safe']);self.assertIn('R07.first_line_indent',proof(r,n)['allowed_properties'])
  self.assertTrue(any('行内字体/字号继续保护' in n['detail'] for n in r['coverage_notes']));self.assertFalse(any(f['locator'].get('paragraph')==3 and f['locator'].get('run')==2 and f['rule_id']=='R05' for f in r['findings']))
 def test_partial_scope_sufficient_locally_never_marked_complete(self):
  self.assertTrue(proof(self.s.report,3)['structurally_safe']);self.assertFalse(self.s.citation_draft['complete']);self.assertFalse(proof(self.s.report,3)['scope_complete']);self.assertIn('部分',self.s.report['citations']['scope_state'])
 def test_v1_single_integer_and_v2_are_separate(self):
  from core.citations import CONFIG
  d=deepcopy(self.s.citation_draft);d['template']=deepcopy(CONFIG);self.s.edit_citations(d);self.s.confirm_citations();self.assertTrue(self.s.confirm_and_check());self.assertTrue(proof(self.s.report,3)['structurally_safe']);self.assertFalse(proof(self.s.report,4)['structurally_safe'])
 def test_unconfirmed_and_excluded_superscripts_stay_review(self):
  for purpose in ('pending','excluded'):
   d=deepcopy(self.s.citation_draft);d['objects']['c:3:6:9']=purpose;self.s.edit_citations(d);self.s.confirm_citations();self.assertTrue(self.s.confirm_and_check());self.assertEqual(finding(self.s.report,3,'R06')['status'],'review')
  self.assertEqual(finding(self.s.report,5,'R06')['status'],'review');self.assertEqual(finding(self.s.report,6,'R06')['status'],'review')
 def test_whole_run_super_including_outside_text_not_exempt(self):
  def change(pkg):
   p=pkg.paragraphs[2];tx=''.join(p.xpath('.//w:t/text()',namespaces=NS))
   for r in list(p.findall(q('r'))):p.remove(r)
   r=E.SubElement(p,q('r'));E.SubElement(r,q('t')).text=tx;_ensure(_ensure(r,'rPr'),'vertAlign').set(q('val'),'superscript')
  r=self.altered(change);self.assertFalse(proof(r,3)['structurally_safe']);self.assertIn('区间外',proof(r,3)['blockers'][0]);self.assertEqual(finding(r,3,'R07')['status'],'review')
 def test_baseline_whitespace_not_size_basis_but_upper_whitespace_blocks(self):
  def whitespace(pkg,upper=False):
   r=E.SubElement(pkg.paragraphs[2],q('r'));E.SubElement(r,q('t')).text='  ';_ensure(_ensure(r,'rPr'),'sz').set(q('val'),'60')
   if upper:_ensure(_ensure(r,'rPr'),'vertAlign').set(q('val'),'superscript')
  r=self.altered(whitespace);self.assertTrue(proof(r,3)['structurally_safe']);self.assertEqual(finding(r,3,'R07')['actual']['uniform_size_pt'],12);self.assertNotIn(4,proof(r,3)['ordinary_basis_runs'])
  r=self.altered(lambda p:whitespace(p,True));self.assertEqual(finding(r,3,'R06')['status'],'review')
 def test_empty_run_has_explicit_boundary(self):
  r=self.altered(lambda p:E.SubElement(p.paragraphs[2],q('r')));self.assertFalse(proof(r,3)['structurally_safe']);self.assertIn('普通w:t',proof(r,3)['blockers'][0])
 def test_other_superscript_unicode_and_subscript_block(self):
  for kind in ('unicode','subscript','super'):
   def fn(pkg):
    r=pkg.paragraphs[2].findall(q('r'))[-1]
    if kind=='unicode':r.find(q('t')).text+='²'
    else:_ensure(_ensure(r,'rPr'),'vertAlign').set(q('val'),'subscript' if kind=='subscript' else 'superscript')
   out=self.altered(fn);self.assertFalse(proof(out,3)['structurally_safe']);self.assertEqual(finding(out,3,'R06')['status'],'review')
 def test_partial_superscript_still_only_confirmed_ranges(self):
  out=self.altered(lambda p:_ensure(_ensure(p.paragraphs[3].findall(q('r'))[6],'rPr'),'vertAlign').set(q('val'),'baseline'));self.assertTrue(proof(out,4)['structurally_safe']);self.assertEqual(finding(out,4,'R06')['status'],'problem');self.assertTrue(any(f['rule_id']=='R33' and f['locator'].get('paragraph')==4 and f['status']=='problem' for f in out['findings']))
 def test_chars_point_and_direct_hanging_independent(self):
  for attrs,status in [({'firstLineChars':'200','firstLine':'0'},'pass'),({'firstLineChars':'200','firstLine':'480'},'pass'),({'firstLineChars':'200','firstLine':'520'},'problem'),({'firstLineChars':'100','firstLine':'0'},'problem'),({'firstLine':'480'},'pass'),({'firstLine':'460'},'problem'),({'firstLineChars':'200','hanging':'0'},'problem')]:
   def fn(pkg):
    e=pkg.paragraphs[2].find('w:pPr/w:ind',NS);e.attrib.clear()
    for k,v in attrs.items():e.set(q(k),v)
   r=self.altered(fn);self.assertEqual(finding(r,3,'R07')['status'],status,attrs)
 def test_inherited_hanging_not_repaired(self):
  def fn(pkg):
   normal=pkg.styles.xpath('./w:style[@w:styleId="Normal"]',namespaces=NS)[0];_ensure(_ensure(normal,'pPr'),'ind').set(q('hanging'),'0')
  r=self.altered(fn);self.assertEqual(finding(r,3,'R07')['status'],'review');self.assertFalse(finding(r,3,'R07')['fixable'])
 def test_citation_size_and_width_do_not_supply_body_basis(self):
  def fn(pkg):
   p=pkg.paragraphs[2];ind=p.find('w:pPr/w:ind',NS);ind.attrib.clear();ind.set(q('firstLine'),'480');rp=p.findall(q('r'))[1].find(q('rPr'));_ensure(rp,'sz').set(q('val'),'72');_ensure(rp,'w').set(q('val'),'50')
  r=self.altered(fn);f=finding(r,3,'R07');self.assertEqual(f['status'],'pass');self.assertEqual(f['actual']['uniform_size_pt'],12)
 def test_mixed_unknown_or_scaled_body_prevent_point_equivalence(self):
  for tag,value in [('sz','26'),('sz','bad'),('w','85'),('spacing','20')]:
   def fn(pkg):
    p=pkg.paragraphs[2];ind=p.find('w:pPr/w:ind',NS);ind.attrib.clear();ind.set(q('firstLine'),'480');_ensure(_ensure(p.findall(q('r'))[0],'rPr'),tag).set(q('val'),value)
   r=self.altered(fn);self.assertEqual(finding(r,3,'R07')['status'],'review',(tag,value));self.assertEqual(finding(r,3,'R06')['status'],'problem')
 def test_only_citation_point_unknown_character_units_still_readable(self):
  self.assertEqual(finding(self.s.report,7,'R07')['status'],'review');self.assertIsNone(finding(self.s.report,7,'R07')['actual']['uniform_size_pt']);self.assertEqual(finding(self.s.report,7,'R06')['status'],'problem')
  def fn(pkg):
   e=pkg.paragraphs[6].find('w:pPr/w:ind',NS);e.attrib.clear();e.set(q('firstLineChars'),'200');e.set(q('firstLine'),'0')
  self.assertEqual(finding(self.altered(fn),7,'R07')['status'],'pass')
 def test_line_modes_grid_and_missing_values_not_hidden(self):
  for rule,status in [('auto','problem'),('exact','problem'),('atLeast','problem'),('unknown','review')]:
   r=self.altered(lambda p:_ensure(_ensure(p.paragraphs[2],'pPr'),'spacing').set(q('lineRule'),rule));self.assertEqual(finding(r,3,'R06')['status'],status)
  for raw in ('bad','0','-1'):
   r=self.altered(lambda p:_ensure(_ensure(p.paragraphs[2],'pPr'),'spacing').set(q('line'),raw));self.assertEqual(finding(r,3,'R06')['status'],'review')
 def test_grid_only_selected_property_stays_review_and_override(self):
  def fn(pkg):_ensure(pkg.sections[0],'docGrid').set(q('type'),'linesAndChars')
  r=self.altered(fn);self.assertEqual(finding(r,3,'R06')['status'],'review');self.assertEqual(finding(r,3,'R13','after')['status'],'review');self.assertEqual(finding(r,3,'R13','alignment')['status'],'problem')
  def off(pkg):fn(pkg);_ensure(_ensure(pkg.paragraphs[2],'pPr'),'snapToGrid').set(q('val'),'0')
  self.assertEqual(finding(self.altered(off),3,'R06')['status'],'problem')
  for kind in ('unknown','duplicate'):
   def abnormal(pkg):
    if kind=='unknown':_ensure(pkg.sections[0],'docGrid').set(q('type'),'unsupported-grid')
    else:
     _ensure(pkg.sections[0],'docGrid').set(q('type'),'default');E.SubElement(pkg.sections[0],q('docGrid')).set(q('type'),'lines')
   r=self.altered(abnormal);self.assertEqual(finding(r,3,'R06')['status'],'review',kind);self.assertEqual(finding(r,4,'R07')['status'],'review',kind);self.assertEqual(finding(r,3,'R13','after')['status'],'review',kind);self.assertEqual(finding(r,3,'R13','alignment')['status'],'problem',kind)
 def test_spacing_units_automatic_contextual_and_conflicts(self):
  for attr,v,prop in [('beforeAutospacing','1','before'),('beforeAutospacing','invalid','before'),('beforeLines','50','before')]:
   r=self.altered(lambda p:_ensure(_ensure(p.paragraphs[2],'pPr'),'spacing').set(q(attr),v));self.assertEqual(finding(r,3,'R13',prop)['status'],'review');self.assertEqual(finding(r,3,'R13','alignment')['status'],'problem')
  r=self.altered(lambda p:_ensure(_ensure(p.paragraphs[2],'pPr'),'contextualSpacing').set(q('val'),'1'));self.assertEqual(finding(r,3,'R13','before')['status'],'review');self.assertEqual(finding(r,3,'R13','after')['status'],'review')
 def test_unknown_context_and_duplicate_inheritance_not_pass(self):
  for tag in ('contextualSpacing','snapToGrid'):
   r=self.altered(lambda p:_ensure(_ensure(p.paragraphs[2],'pPr'),tag).set(q('val'),'unknown'));self.assertEqual(finding(r,3,'R06')['status'],'review')
  def duplicate(pkg):pkg.paragraphs[2].find('w:pPr',NS).append(E.Element(q('spacing')))
  self.assertEqual(finding(self.altered(duplicate),3,'R06')['status'],'review')
 def test_styles_missing_cycles_and_character_super_inheritance(self):
  def missing(pkg):_ensure(_ensure(pkg.paragraphs[2].findall(q('r'))[0],'rPr'),'rStyle').set(q('val'),'MissingStyle')
  self.assertEqual(finding(self.altered(missing),3,'R06')['status'],'review')
  def inherited(pkg):
   style=E.SubElement(pkg.styles,q('style'),{q('type'):'character',q('styleId'):'CitationSuper31'});_ensure(_ensure(style,'rPr'),'vertAlign').set(q('val'),'superscript');rp=pkg.paragraphs[2].findall(q('r'))[1].find(q('rPr'));rp.remove(rp.find(q('vertAlign')));_ensure(rp,'rStyle').set(q('val'),'CitationSuper31')
  r=self.altered(inherited);self.assertTrue(proof(r,3)['structurally_safe']);self.assertIn('样式',proof(r,3)['recognized_superscript'][0]['source'])
 def test_complex_boundaries_and_hidden_runs_never_exempt(self):
  for kind in ('bookmark','link','field','SDT','revision','math','numbering','hidden'):
   def fn(pkg):
    p=pkg.paragraphs[2]
    if kind=='bookmark':E.SubElement(p,q('bookmarkStart')).set(q('id'),'700')
    elif kind=='numbering':_ensure(_ensure(_ensure(p,'pPr'),'numPr'),'numId').set(q('val'),'1')
    elif kind=='hidden':_ensure(_ensure(p.findall(q('r'))[1],'rPr'),'vanish').set(q('val'),'1')
    elif kind=='math':
     m='{http://schemas.openxmlformats.org/officeDocument/2006/math}';e=E.SubElement(p,m+'oMath');E.SubElement(E.SubElement(e,m+'r'),m+'t').text='x'
    else:
     tag={'link':'hyperlink','field':'fldSimple','SDT':'sdt','revision':'ins'}[kind];r=p.findall(q('r'))[0];pos=p.index(r);p.remove(r);e=E.Element(q(tag));p.insert(pos,e);e.append(r)
   r=self.altered(fn);self.assertEqual(finding(r,3,'R06')['status'],'review',kind);self.assertFalse(proof(r,3)['structurally_safe'],kind)
 def test_partial_rehearsal_exact_pPr_only_and_zero_adopt_refix(self):
  s=self.s;s.set_selection([finding(s.report,3,'R06')['key']]);self.assertTrue(s.rehearse(),s.rehearsal_error);self.assertFalse(s.history)
  with mock.patch('web.session.fix_document',side_effect=AssertionError('no refix')):self.assertTrue(s.adopt_rehearsal(s.rehearsal['id'],acknowledged=True))
  self.assertTrue(verify(SAMPLE/'errors.docx',s.result['output'],only_line=True)['no_inline_or_citation_format_changes'])
 def test_all_selected_pPr_two_rounds_independent_and_repeat_stable(self):
  s=self.s;s.set_selection([finding(s.report,3,'R06')['key']]);self.assertTrue(s.generate());p=Path(s.result['output']);saved=p.read_bytes();self.assertTrue(s.next_round());s.set_selection(selection(s));self.assertTrue(s.generate(),s.error);self.assertEqual(p.read_bytes(),saved);self.assertTrue(verify(SAMPLE/'errors.docx',s.result['output'])['all_run_subtrees_byte_equivalent']);self.assertEqual(s.result['after']['findings'],check_document(s.result['output'],s.result['output_body_manifest'],**{**s._rules_arguments(),'classification_manifest':s.result['output_classification_manifest']})['findings'])
  m=s.result['output_classification_manifest'];out=fix_document(s.result['output'],self.d/'repeat.docx',None,selected_rules=['R06','R07','R13'],mode='academic',classification_manifest=m,custom_rules_path=s.custom_rules_path);self.assertEqual(Path(out['output']).read_bytes(),Path(s.result['output']).read_bytes())
 def test_range_change_and_restore_recheck_not_old_authority(self):
  from web.session import WebSession
  s=self.s;scope=deepcopy(s.citation_draft);scope['objects']['c:3:6:9']='pending';s.edit_citations(scope);self.assertIsNone(s.report);self.assertIsNone(s.citation_confirmed);s.confirm_citations();self.assertTrue(s.confirm_and_check());self.assertEqual(finding(s.report,3,'R06')['status'],'review');s.prepare_project();o=WebSession(self.d/'other');o.stage_project(s.project_download());restored=o.restore_project(acknowledged=True);self.assertEqual(restored.report['findings'],s.report['findings']);self.assertIsNone(restored.rehearsal)
 def test_only_property_proof_in_report_and_exports(self):
  s=self.s;exp=s.prepare_reading_export();self.assertIn('确认引文上标与指定段落属性',exp['report.html'].decode());self.assertIn('citation_paragraphs',json.loads(exp['report.json']));self.assertFalse(any('bold' in p for p in proof(s.report,3)['allowed_properties']));self.assertTrue(any(n['locator'].get('paragraph')==3 and '上角标' in n['detail'] for n in s.report['coverage_notes']))
 def test_old_unconfirmed_body_and_classification_conflicts_stay_protected(self):
  args=self.s._rules_arguments();m=deepcopy(args['classification_manifest']);m.pop('citation_scope');r=check_document(self.s.input_path,mode='academic',classification_manifest=m,custom_rules_path=self.s.custom_rules_path);self.assertNotIn('citation_paragraph_evidence',r['coverage']);self.assertEqual(finding(r,3,'R06')['status'],'review')
  m['citation_scope']=deepcopy(self.s.citation_draft);m['citation_scope']['confirmed']=False
  with self.assertRaises(DemoError):check_document(self.s.input_path,mode='academic',classification_manifest=m)
 def test_two_step_R33_recheck_does_not_append_new_indent_fix(self):
  from scripts.reproduce_plan_demo import session as oldsession,selection as oldselection
  s=oldsession(self.d/'plan');s.set_selection(oldselection(s));self.assertTrue(s.rehearse_plan(),s.rehearsal_error);tx=s.rehearsal['transactions'];f=finding(tx[-1]['result']['after'],3,'R07');self.assertEqual(f['status'],'problem');self.assertTrue(f['fixable']);self.assertEqual(f['actual']['first_line_pt'],28);self.assertFalse(any(c['rule_id']=='R07' for t in tx for c in t['result']['changes']));self.assertEqual(s.rehearsal_view()['engine_calls'],2)
 def test_two_sessions_and_external_mutation(self):
  other=session(self.d/'other');d=deepcopy(self.s.citation_draft);d['objects']['c:3:6:9']='excluded';self.s.edit_citations(d);self.assertTrue(proof(other.report,3)['structurally_safe']);self.s.input_path.write_bytes(b'changed');self.assertFalse(self.s.check());self.assertIsNone(self.s.report)

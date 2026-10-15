"""Citation checks plus independent per-character rPr and ZIP preservation probes."""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest import TestCase,mock
import json,zipfile,time
from lxml import etree as E
from core import check_document,fix_document
from core.package import Package,DemoError,q,NS
from core.citations import inventory,make_scope,validate_scope,template,CONFIG,reference_evidence
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'samples/phase19'
def manifest(p,complex_confirm=True):
 pkg=Package(p);scan=[3,4,5,6] if 'risks' not in str(p) else [3,4,5,6,7,8]
 types={str(i):'body' if i in scan else 'reference_item' if (8<=i<=17 if len(scan)==4 else 10<=i<=20) else 'other' for i in range(1,len(pkg.paragraphs)+1)}
 s=make_scope(pkg,scan);s.update(confirmed=True,confirmation='独立核对',complete=True,references_complete=True)
 s['objects']={r['id']:'excluded' if r['text']=='[8]' or not complex_confirm and r['paragraph']==6 else 'citation' for r in inventory(pkg,scan)['objects']}
 return {'input_sha256':pkg.hash,'paragraph_types':types,'confirmed':True,'confirmation':'独立核对','citation_scope':s}
def run(p,m):return check_document(p,mode='academic',classification_manifest=m)
def fs(r,rid='R33'):return [f for f in r['findings'] if f['rule_id']==rid]
def rewrite(src,dst,fn):
 p=Package(src);fn(p)
 with zipfile.ZipFile(dst,'w') as z:
  for n,v in p.parts.items():z.writestr(n,E.tostring(p.root,encoding='UTF-8',xml_declaration=True) if n=='word/document.xml' else v)
 return dst

def characters(pkg):
 # Independent oracle: records each literal character with c14n rPr excluding vertAlign.
 out=[]
 for p in pkg.paragraphs:
  chars=[]
  for r in p.findall(q('r')):
   rp=deepcopy(r.find(q('rPr')));v=rp.find(q('vertAlign')) if rp is not None else None
   vert=v.get(q('val')) if v is not None else None
   if v is not None:rp.remove(v)
   attrs=E.tostring(rp,method='c14n') if rp is not None and (len(rp) or rp.attrib) else b''
   for t in r.findall(q('t')):
    for ch in t.text or '':chars.append((ch,attrs,vert,tuple(sorted(r.attrib.items()))))
  out.append(chars)
 return out
class CitationTests(TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.d=Path(self.tmp.name);self.p=S/'errors.docx';self.m=manifest(self.p)
 def tearDown(self):self.tmp.cleanup()
 def fix(self,keys=None,m=None,p=None,name='out.docx'):
  return fix_document(p or self.p,self.d/name,None,selected_keys=keys or (),selected_rules=['R33'] if keys is None else (),mode='academic',classification_manifest=m or self.m)
 def session(self):
  s=WebSession(self.d/'web');s.set_mode('academic');s.load(self.p.read_bytes(),'合成引文.docx');s.set_types(self.m['paragraph_types']);s.enable_citations(True);s.edit_citations(self.m['citation_scope']);s.confirm_citations();self.assertTrue(s.confirm_and_check(),s.error);return s
 def test_independent_known_errors_repeated_and_cross_runs(self):
  r=run(self.p,self.m);self.assertEqual(len([f for f in fs(r) if f['status']=='problem']),json.loads((S/'independent-errors.json').read_text())['fixable_citations']);self.assertEqual([f['actual'] for f in fs(r)][:3],['baseline','baseline','mixed']);self.assertNotEqual(fs(r)[0]['key'],fs(r)[1]['key']);self.assertEqual(fs(r)[3]['actual'],'superscript');self.assertTrue(fs(r)[3]['vertical_evidence'])
 def test_correct_control_stays_correct_and_complex_review(self):
  p=S/'correct.docx';r=run(p,manifest(p));self.assertFalse(any(f['status']=='problem' for f in fs(r)));self.assertEqual(sum(f['status']=='review' for f in fs(r)),1)
 def test_opt_in_old_counts_and_cli_meaning(self):
  m=deepcopy(self.m);m.pop('citation_scope');r=run(self.p,m);self.assertEqual(r['summary']['rule_count'],22);self.assertNotIn('citations',r)
 def test_partial_fix_only_selected_characters_and_members(self):
  before=Package(self.p);r=run(self.p,self.m);f=fs(r)[1];result=self.fix([f['key']]);after=Package(result['output']);a=characters(before);b=characters(after)
  self.assertEqual(before.root.xpath('//w:t/text()',namespaces=NS).__len__()+2,after.root.xpath('//w:t/text()',namespaces=NS).__len__())
  for n,(old,new) in enumerate(zip(a,b),1):
   self.assertEqual(len(old),len(new))
   for i,(v,w) in enumerate(zip(old,new)):
    self.assertEqual((v[0],v[1],v[3]),(w[0],w[1],w[3]))
    self.assertEqual(w[2],'superscript' if n==3 and f['locator']['start']<=i<f['locator']['end'] else v[2])
  self.assertEqual(''.join(before.root.xpath('//w:t/text()',namespaces=NS)),''.join(after.root.xpath('//w:t/text()',namespaces=NS)))
  for n,v in before.parts.items():
   if n!='word/document.xml':self.assertEqual(v,after.parts[n])
  for tag in ('fldSimple','bookmarkStart','bookmarkEnd','sectPr','tbl','drawing'):
   self.assertEqual([E.tostring(e) for e in before.root.iter(q(tag))],[E.tostring(e) for e in after.root.iter(q(tag))])
  self.assertEqual(self.p.read_bytes(),before.raw);self.assertEqual(sum(f['status']=='problem' for f in fs(result['after'])),3)
 def test_all_safe_fix_reread_and_idempotence(self):
  r=self.fix();self.assertEqual(len(r['changes']),4);self.assertTrue(all(c['verification']=='pass' for c in r['changes']));self.assertEqual(r['after'],run(r['output'],r['output_classification_manifest']));again=self.fix(p=r['output'],m=r['output_classification_manifest'],name='again.docx');self.assertEqual(again['changes'],[]);self.assertEqual(Path(r['output']).read_bytes(),Path(again['output']).read_bytes())
 def test_existing_body_keeps_rest_and_protects_citation(self):
  r=self.fix();self.assertTrue(any(f['rule_id']=='R03' and f['locator'].get('paragraph')==3 and f['status']=='pass' for f in r['after']['findings']));self.assertTrue(any(n['locator'].get('paragraph')==3 and '上角标' in n['detail'] for n in r['after']['coverage_notes']))
  from core.engine import _ensure
  from core.table_text import rebind
  def adjacent(pkg):_ensure(_ensure(pkg.paragraphs[2].find(q('r')),'rPr'),'sz').set(q('val'),'28')
  source=rewrite(r['output'],self.d/'adjacent-font.docx',adjacent);m=deepcopy(r['output_classification_manifest']);m['input_sha256']=Package(source).hash;rebind(m,m['input_sha256']);m['confirmation']='人工核对合成相邻文字变更后的新文件'
  before=characters(Package(source));out=self.d/'ordinary-fix.docx';fixed=fix_document(source,out,None,selected_rules=['R05'],mode='academic',classification_manifest=m);self.assertEqual(len(fixed['changes']),1);after=characters(Package(out));self.assertEqual([[c[2] for c in p] for p in before],[[c[2] for c in p] for p in after]);self.assertFalse(any(f['status']=='problem' for f in fs(fixed['after'])))
 def test_complex_citation_and_relation_readonly(self):
  r=run(self.p,self.m);f=fs(r)[-1];self.assertEqual(f['status'],'review');self.assertFalse(f['fixable']);self.assertEqual([f for f in fs(r,'R34') if f['locator'].get('paragraph')==6][0]['status'],'review');self.assertEqual(fs(r,'R34')[-1]['status'],'review')
 def test_unique_references_and_repeat_not_order_error(self):
  m=manifest(self.p,False);r=run(self.p,m);self.assertEqual(r['citations']['order'],[1,2,3]);self.assertEqual(fs(r,'R34')[-1]['status'],'pass');self.assertEqual([x['number'] for x in r['citations']['unreferenced']],list(range(4,11)))
 def test_missing_unique_duplicate_and_order(self):
  p=S/'risks.docx';m=manifest(p)
  # Exclude unsupported/complex candidates to establish a fully decidable selected scope.
  for row in inventory(p,m['citation_scope']['scan'])['objects']:
   if not row['fixable']:m['citation_scope']['objects'][row['id']]='excluded'
  r=run(p,m);self.assertEqual(fs(r,'R34')[-1]['status'],'problem');dup=next(x for x in r['citations']['rows'] if x['numbers']==[4]);self.assertEqual(dup['status'],'review');self.assertEqual(len(dup['references']),2)
  def remove_number(pkg):pkg.paragraphs[9].find(q('r')).find(q('t')).text='[99] 合成替代条目'
  target=rewrite(self.p,self.d/'missing.docx',remove_number);m=manifest(target,False);r=run(target,m);self.assertTrue(any(f['status']=='problem' and f['locator'].get('property')=='correspondence' for f in fs(r,'R34')))
 def test_partial_range_never_claims_full_missing(self):
  m=manifest(self.p,False);m['citation_scope']['references_complete']=False;r=run(self.p,m);self.assertEqual(fs(r,'R34')[-1]['status'],'review');self.assertIn('部分',r['citations']['scope_state'])
 def test_undecided_and_incomplete_scan_not_full(self):
  m=manifest(self.p,False);m['citation_scope']['objects'].pop(next(iter(m['citation_scope']['objects'])));r=run(self.p,m);self.assertTrue(r['citations']['undecided']);self.assertEqual(fs(r,'R34')[-1]['status'],'review')
 def test_unknown_automatic_reference_reuses_r22(self):
  def auto(pkg):
   pp=E.SubElement(pkg.paragraphs[7],q('pPr'));np=E.SubElement(pp,q('numPr'));E.SubElement(np,q('numId')).set(q('val'),'1')
  p=rewrite(self.p,self.d/'auto.docx',auto);m=manifest(p,False);r=run(p,m);self.assertIsNone(r['citations']['references'][0]['number']);self.assertEqual(next(f for f in fs(r,'R22') if f['locator'].get('property')=='参考文献手工编号')['status'],'review');self.assertTrue(any(f['locator'].get('property')=='参考文献其他编号' for f in fs(r,'R22')));self.assertEqual(fs(r,'R34')[-1]['status'],'review')
 def test_unsupported_grammar_and_huge_digits_no_expand(self):
  def bad(pkg):pkg.paragraphs[2].find(q('r')).find(q('t')).text='[1,3] [1–999999999999] ［2］ ['+'9'*10000+']'
  p=rewrite(self.p,self.d/'large.docx',bad);start=time.monotonic();rows=inventory(p,[3])['objects'];self.assertLess(time.monotonic()-start,2);self.assertTrue(all(not r['fixable'] for r in rows[:4]));self.assertTrue(all(not r['numbers'] for r in rows[:4]))
 def test_scope_hash_offsets_roles_and_template_validation(self):
  for field,value in [('input_sha256','0'*64),('objects',{'c:3:0:3':'citation'}),('scan',[True]),('complete',1),('objects',{next(iter(self.m['citation_scope']['objects'])):'execute'})]:
   s=deepcopy(self.m['citation_scope']);s[field]=value
   with self.assertRaises(DemoError):validate_scope(Package(self.p),s)
  for field,value in [('superscript',1),('extra','exec'),('structure_version',2),('source',{})]:
   c=deepcopy(CONFIG);c[field]=value
   with self.assertRaises(DemoError):template(c)
 def test_scan_rejects_nonbody(self):
  m=deepcopy(self.m);m['paragraph_types']['3']='reference_item'
  with self.assertRaises(DemoError):run(self.p,m)
 def test_bookmark_and_subscript_and_hidden_protection(self):
  def change(pkg):
   p=pkg.paragraphs[2];E.SubElement(p,q('bookmarkStart')).set(q('id'),'9')
  p=rewrite(self.p,self.d/'bookmark.docx',change);self.assertTrue(all(not r['fixable'] for r in inventory(p,[3])['objects']))
 def test_mix_split_and_run_format_requires_explicit_rounds(self):
  def size(pkg):pkg.paragraphs[2].findall(q('r'))[1].find('w:rPr',NS).append(E.Element(q('sz'),{q('val'):'30'}))
  p=rewrite(self.p,self.d/'mixed.docx',size);m=manifest(p);r=run(p,m);keys=[f['key'] for f in r['findings'] if f['fixable'] and f['locator'].get('paragraph')==3]
  with self.assertRaisesRegex(DemoError,'分轮'):self.fix(keys,m=m,p=p)
  self.assertFalse((self.d/'out.docx').exists())
 def test_mask_catches_extra_font_and_text_changes(self):
  from core.engine import _preservation
  p=Package(self.p);f=fs(run(self.p,self.m))[0];before=_preservation(p,[f]);p.paragraphs[2].find(q('r')).find(q('t')).text='被篡改';self.assertNotEqual(before,_preservation(p,[f]))
 def test_session_multiround_and_original_unchanged(self):
  s=self.session();keys=[f['key'] for f in s.eligible() if f['rule_id']=='R33'];s.set_selection(keys[:1]);self.assertTrue(s.generate(),s.error);p=Path(s.result['output']);b=p.read_bytes();self.assertTrue(s.next_round(),s.error);s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R33']);self.assertTrue(s.generate(),s.error);self.assertEqual(p.read_bytes(),b);self.assertEqual(len(s.history),2)
 def test_scope_change_and_type_change_invalidate(self):
  s=self.session();scope=deepcopy(s.citation_draft);scope['complete']=False;s.edit_citations(scope);self.assertIsNone(s.report);self.assertIsNone(s.citation_confirmed);s.confirm_citations();self.assertTrue(s.confirm_and_check());types=deepcopy(s.paragraph_types);types['8']='other';s.set_types(types);self.assertIsNone(s.report);self.assertIsNone(s.citation_confirmed)
 def test_supplement_roundtrip(self):
  s=self.session();self.assertEqual(template(json.loads(s.citation_template_bytes())),s.citation_draft['template'])
 def test_project_restore_and_continue_fresh_reports(self):
  s=self.session();s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R33'][:1]);self.assertTrue(s.generate(),s.error);self.assertTrue(s.next_round(),s.error);snapshot=s.prepare_project();raw=s.project_download();other=WebSession(self.d/'web');other.stage_project(raw);restored=other.restore_project(acknowledged=True);self.assertTrue(restored.report,restored.error);self.assertEqual(restored.report['citations'],s.report['citations']);self.assertEqual(restored.citation_draft,s.citation_draft);self.assertEqual(len(restored.history),1);restored.set_selection([f['key'] for f in restored.eligible() if f['rule_id']=='R33']);self.assertTrue(restored.generate(),restored.error)
 def test_draft_restore_without_ai_or_confirmation(self):
  s=self.session();d=deepcopy(s.citation_draft);d['objects'][next(iter(d['objects']))]='pending';s.edit_citations(d);s.prepare_project();other=WebSession(self.d/'web');other.stage_project(s.project_download());r=other.restore_project(acknowledged=True);self.assertEqual(r.citation_draft,d);self.assertIsNone(r.report);self.assertIsNone(r.citation_confirmed)
 def test_downloads_html_zip_bind_real_results(self):
  s=self.session();s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R33']);self.assertTrue(s.generate(),s.error);raw=s.result_package();z=zipfile.ZipFile(__import__('io').BytesIO(raw));self.assertIn('citation-supplement.json',z.namelist());html=z.read('report.html').decode();self.assertIn('引文对应',html);self.assertNotIn('/Volumes/',html);self.assertNotIn('数组索引',html)
 def test_session_isolation_and_external_mutation_refusal(self):
  s=self.session();other=WebSession(self.d/'web');self.assertFalse(other.citation_enabled);self.assertIsNone(other.report);s.input_path.write_bytes(b'broken');self.assertFalse(s.check());self.assertIsNone(s.report)
 def test_subscript_style_is_detected_and_only_vert_changes(self):
  def change(pkg):
   rp=pkg.paragraphs[2].findall(q('r'))[1].find(q('rPr'));E.SubElement(rp,q('vertAlign')).set(q('val'),'subscript')
  p=rewrite(self.p,self.d/'sub.docx',change);m=manifest(p);r=run(p,m);self.assertEqual(fs(r)[0]['actual'],'subscript');v=self.fix([fs(r)[0]['key']],m=m,p=p);self.assertEqual(fs(v['after'])[0]['actual'],'superscript')
  def inherited_baseline(pkg):
   style=pkg.styles.xpath('./w:style[@w:styleId="CitationBaseline"]',namespaces=NS)[0];E.SubElement(style,q('basedOn')).set(q('val'),'CitationSuper');rp=style.find(q('rPr'))
   if rp is None:rp=E.SubElement(style,q('rPr'))
   E.SubElement(rp,q('vertAlign')).set(q('val'),'baseline');pkg.parts['word/styles.xml']=E.tostring(pkg.styles,encoding='UTF-8',xml_declaration=True)
  styled=rewrite(self.p,self.d/'style-baseline.docx',inherited_baseline);m=manifest(styled);r=run(styled,m);target=next(f for f in fs(r) if f['locator']['paragraph']==5 and f['actual']=='baseline');self.assertIn('样式',target['vertical_evidence'][0]['source']);v=self.fix([target['key']],m=m,p=styled,name='style-fixed.docx');self.assertEqual(Package(styled).parts['word/styles.xml'],Package(v['output']).parts['word/styles.xml']);self.assertEqual(next(f for f in fs(v['after']) if f['key']==target['key'])['actual'],'superscript')
 def test_conflicting_vertical_style_is_review(self):
  def change(pkg):
   rp=pkg.paragraphs[2].findall(q('r'))[1].find(q('rPr'));E.SubElement(rp,q('vertAlign')).set(q('val'),'superscript');E.SubElement(rp,q('vertAlign')).set(q('val'),'baseline')
  p=rewrite(self.p,self.d/'conflict.docx',change);r=run(p,manifest(p));self.assertEqual(fs(r)[0]['status'],'review');self.assertFalse(fs(r)[0]['fixable'])
 def test_link_boundary_is_readonly(self):
  def change(pkg):
   p=pkg.paragraphs[2];r=p.findall(q('r'))[1];p.remove(r);h=E.SubElement(p,q('hyperlink'));h.set(q('anchor'),'missing');h.append(r)
  p=rewrite(self.p,self.d/'link.docx',change);r=run(p,manifest(p));self.assertTrue(all(f['status']=='review' and not f['fixable'] for f in fs(r) if f['locator']['paragraph']==3))
 def test_partition_rejects_unnecessary_split(self):
  from core.citations import partition_guard
  from core.academic import isolate
  before=Package(self.p);after=Package(self.p);f=fs(run(self.p,self.m))[0];isolate(after.paragraphs[2],1,2)
  with self.assertRaises(DemoError):partition_guard(before,after,[f])
 def test_unselected_vert_change_detected_by_whitelist(self):
  from core.engine import _preservation,_ensure
  before=Package(self.p);after=Package(self.p);f=fs(run(self.p,self.m))[0];_ensure(_ensure(after.paragraphs[2].findall(q('r'))[2],'rPr'),'vertAlign').set(q('val'),'superscript');self.assertNotEqual(_preservation(before,[f]),_preservation(after,[f]))
 def test_no_confirmed_citations_never_claim_order_pass(self):
  m=deepcopy(self.m);m['citation_scope']['objects']={};r=run(self.p,m);self.assertFalse(any(f['status']=='pass' for f in fs(r,'R34')))
 def test_config_disable_is_explicit_and_report_rule_count(self):
  m=deepcopy(self.m);m['citation_scope']['template']['superscript']=False;r=run(self.p,m);self.assertFalse(fs(r));self.assertEqual(r['summary']['rule_count'],23)
 def test_project_rejects_stale_char_range(self):
  from core.project import stage
  import io
  s=self.session();s.prepare_project();z=zipfile.ZipFile(io.BytesIO(s.project_download()));items={n:z.read(n) for n in z.namelist()};data=json.loads(items['project.json']);data['state']['scope']['citation_scope']['objects']={'c:3:0:1':'citation'};items['project.json']=json.dumps(data).encode();out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as dst:
   for n,v in items.items():dst.writestr(n,v)
  with self.assertRaises(DemoError):stage(out.getvalue(),self.d/'staging')
  self.assertTrue(s.check())
 def test_output_tamper_cannot_download_or_package(self):
  s=self.session();s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R33']);self.assertTrue(s.generate(),s.error);Path(s.result['output']).write_bytes(b'bad')
  with self.assertRaises(DemoError):s.result_package()
 def test_full_exports_preserve_raw_rows_paging_independent(self):
  from core.report import markdown
  r=run(self.p,self.m);self.assertIn('正文引文上标',markdown(r));self.assertEqual(len(r['citations']['rows']),6);s=self.session();bundle=s.current_bundle();records=[r for r in bundle['projection']['records'] if r['raw'].get('object_type') in ('citation','citation_relation')];self.assertEqual(len(records),len(fs(s.report))+len(fs(s.report,'R34')))
 def test_nonvacuous_media_merge_bookmark_sections_and_field_preservation(self):
  p=S/'protected.docx';m=manifest(p);a=Package(p);v=self.fix(m=m,p=p);b=Package(v['output']);self.assertTrue(any(n.startswith('word/media/') for n in a.parts));self.assertGreater(len(a.sections),1);self.assertTrue(a.root.findall('.//'+q('bookmarkStart')))
  for n,data in a.parts.items():
   if n!='word/document.xml':self.assertEqual(data,b.parts[n])
  for tag in ('tbl','sectPr','drawing','bookmarkStart','bookmarkEnd','fldSimple'):
   self.assertEqual([E.tostring(x) for x in a.root.iter(q(tag))],[E.tostring(x) for x in b.root.iter(q(tag))])
 def test_two_round_project_resave_restore_keeps_relations(self):
  s=self.session();keys=[f['key'] for f in s.eligible() if f['rule_id']=='R33'];s.set_selection(keys[:1]);self.assertTrue(s.generate());self.assertTrue(s.next_round());s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R33']);self.assertTrue(s.generate());self.assertTrue(s.next_round());s.prepare_project();x=WebSession(self.d/'restore');x.stage_project(s.project_download());a=x.restore_project(acknowledged=True);self.assertEqual(a.current_round,2);self.assertEqual(len(a.history),2);a.prepare_project();y=WebSession(self.d/'restore2');y.stage_project(a.project_download());b=y.restore_project(acknowledged=True);self.assertEqual(a.report["findings"],b.report["findings"]);self.assertEqual(a.report["summary"],b.report["summary"]);self.assertEqual(a.citation_draft,b.citation_draft)
 def test_disabled_relation_is_explicit_not_false_unreferenced(self):
  m=deepcopy(self.m);m['citation_scope']['template']['correspondence']=False;r=run(self.p,m);self.assertFalse(fs(r,'R34'));self.assertIn('未检查',r['citations']['scope_state']);self.assertEqual(r['citations']['unreferenced'],[])
 def test_no_candidates_reports_upper_scope_not_applicable(self):
  m=deepcopy(self.m);m['citation_scope']['objects']={};r=run(self.p,m);self.assertEqual(fs(r)[0]['status'],'not_applicable');self.assertFalse(fs(r)[0]['fixable'])
 def test_cross_paragraph_field_cache_and_dangling_field_never_edit(self):
  for balanced in (True,False,'orphan'):
   def field(pkg):
    if balanced!='orphan':
     start=E.SubElement(pkg.paragraphs[1],q('r'));E.SubElement(start,q('fldChar')).set(q('fldCharType'),'begin');instr=E.SubElement(pkg.paragraphs[1],q('r'));E.SubElement(instr,q('instrText')).text=' REF Target ';sep=E.SubElement(pkg.paragraphs[1],q('r'));E.SubElement(sep,q('fldChar')).set(q('fldCharType'),'separate')
    if balanced is True or balanced=='orphan':
     end=E.SubElement(pkg.paragraphs[3],q('r'));E.SubElement(end,q('fldChar')).set(q('fldCharType'),'end')
   p=rewrite(self.p,self.d/('cross-'+str(balanced)+'.docx'),field);m=manifest(p);r=run(p,m);f=[f for f in fs(r) if f['locator'].get('paragraph')==3];self.assertTrue(all(x['status']=='review' and not x['fixable'] for x in f));self.assertTrue(all('跨段域' in x['detail'] for x in f));v=self.fix(m=m,p=p,name='cross-out-'+str(balanced)+'.docx');self.assertEqual(E.tostring(Package(p).paragraphs[2]),E.tostring(Package(v['output']).paragraphs[2]))

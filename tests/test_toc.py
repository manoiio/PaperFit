"""Synthetic TOC behavior and whole-package whitelist protection, no real paper."""
from pathlib import Path
from copy import deepcopy
from tempfile import TemporaryDirectory
from unittest import TestCase
import json,zipfile,io
from lxml import etree as E
from core import check_document,fix_document
from core.package import Package,DemoError,q,NS
from core.toc import make_scope,inventory,IDS
from core.toc_template import school,loads,validate,validate_draft
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1];SAMPLE=ROOT/'samples/phase18'

def manifest(path,automatic=False):
 pkg=Package(path);s=make_scope(path);s.update(confirmed=True,confirmation='独立构造清单人工确认',objects={'d:2':'title','d:3':'level1','d:4':'level2','d:5':'level3'})
 types={str(i):'other' for i in range(1,len(pkg.paragraphs)+1)}
 for i,p in enumerate(pkg.paragraphs,1):
  sty=p.find('w:pPr/w:pStyle',NS)
  if sty is not None and sty.get(q('val')) in ('Heading1','Heading2','Heading3'):types[str(i)]='heading'+sty.get(q('val'))[-1]
  if ''.join(p.xpath('.//w:t/text()',namespaces=NS)).startswith(('这是一份','选择格式属性','自动目录保存')):types[str(i)]='body'
 return {'input_sha256':pkg.hash,'paragraph_types':types,'confirmed':True,'confirmation':'独立构造清单人工确认','toc_scope':s}
def toc_findings(r):return [f for f in r['findings'] if f['rule_id'] in IDS]
def run(path,m):return check_document(path,mode='academic',classification_manifest=m)
def rewrite(path,target,fn):
 pkg=Package(path);fn(pkg.root)
 with zipfile.ZipFile(target,'w') as z:
  for n,b in pkg.parts.items():z.writestr(n,E.tostring(pkg.root,encoding='UTF-8',xml_declaration=True) if n=='word/document.xml' else b)
 return target
class TocTests(TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.d=Path(self.tmp.name);self.p=SAMPLE/'manual-errors.docx';self.m=manifest(self.p)
 def tearDown(self):self.tmp.cleanup()
 def test_known_errors_all_runs_and_character_inheritance(self):
  r=run(self.p,self.m);errors=[f for f in toc_findings(r) if f['status']=='problem'];gold=json.loads((SAMPLE/'independent-errors.json').read_text())['manual-errors']
  self.assertEqual(len(errors),6)
  for g in gold:self.assertEqual(len([f for f in errors if f['locator']['toc_object']==int(g['object'][2:]) and f['property']==g['property'] and f['locator'].get('run')==g.get('run')]),1)
  self.assertTrue(next(f for f in errors if f['property']=='font_cn' and f['locator']['toc_object']==4)['font_evidence'])
 def test_correct_control_and_level_difference(self):
  p=SAMPLE/'manual-correct.docx';r=run(p,manifest(p));self.assertTrue(all(f['status']=='pass' for f in toc_findings(r)));self.assertEqual(r['summary']['rule_count'],25)
  self.assertEqual({f['expected'] for f in toc_findings(r) if f['property']=='font_size'}, {12,14,18})
 def test_opt_in_old_counts_unchanged(self):
  m=deepcopy(self.m);m.pop('toc_scope');r=run(self.p,m);self.assertEqual(r['summary']['rule_count'],22);self.assertNotIn('toc',r)
 def test_partial_fix_preserves_unselected_and_original(self):
  b=Package(self.p);r=run(self.p,self.m);selected=next(f for f in toc_findings(r) if f['status']=='problem' and f['property']=='font_size')
  out=self.d/'partial.docx';result=fix_document(self.p,out,None,selected_keys=[selected['key']],mode='academic',classification_manifest=self.m)
  self.assertEqual(result['changes'][0]['verification'],'pass');self.assertEqual(len([f for f in toc_findings(result['after']) if f['status']=='problem']),5)
  self.assertEqual(Package(self.p).raw,b.raw);self.assertTrue(result['preservation']['document_except_selected_format_attributes_equal']);self.assertTrue(result['preservation']['other_zip_member_bytes_equal'])
  a={f['key']:f for f in r['findings']};c={f['key']:f for f in result['after']['findings']}
  for k in a:
   if k!=selected['key']:self.assertEqual(a[k]['actual'],c[k]['actual'])
 def test_full_fix_disk_reread_and_idempotence(self):
  r=run(self.p,self.m);out=self.d/'fixed.docx';res=fix_document(self.p,out,None,selected_rules=IDS,mode='academic',classification_manifest=self.m)
  self.assertEqual(res['after'],run(out,res['output_classification_manifest']));self.assertTrue(all(f['status']=='pass' for f in toc_findings(res['after'])))
  before=Package(self.p);after=Package(out)
  self.assertEqual(before.root.xpath('//w:t/text()',namespaces=NS),after.root.xpath('//w:t/text()',namespaces=NS));self.assertEqual(before.root.xpath('//w:tab',namespaces=NS).__len__(),after.root.xpath('//w:tab',namespaces=NS).__len__())
  two=self.d/'again.docx';again=fix_document(out,two,None,selected_rules=IDS,mode='academic',classification_manifest=res['output_classification_manifest']);self.assertEqual(again['changes'],[]);self.assertEqual(out.read_bytes(),two.read_bytes())
 def test_reject_overwrite(self):
  with self.assertRaises(DemoError):fix_document(self.p,self.p,None,selected_rules=IDS,mode='academic',classification_manifest=self.m)
 def test_sdt_auto_readonly_and_old_numbers(self):
  p=SAMPLE/'automatic.docx';pkg=Package(p);r=run(p,manifest(p));inv=inventory(p)
  self.assertEqual(len(inv['objects']),len(pkg.paragraphs)+3);self.assertEqual(inv['objects'][5]['locator']['paragraph'],3)
  entries=[f for f in toc_findings(r) if f['rule_id']!='R30'];self.assertTrue(all(not f['fixable'] for f in entries));self.assertTrue(all(f['status']=='review' for f in entries));self.assertEqual(len([f for f in inv['fields'] if f['instruction'].strip().startswith('PAGEREF')]),3)
  self.assertTrue(all(row['status']=='pass' for row in r['toc']['rows']));self.assertEqual([row['entry']['saved_page'] for row in r['toc']['rows']],['1','1','1']);self.assertEqual(r['toc']['page_status'],'未核对实际页码')
 def test_auto_domain_bookmarks_relationships_and_parts_preserved(self):
  p=SAMPLE/'automatic.docx';m=manifest(p);res=fix_document(p,self.d/'auto.docx',None,selected_rules=IDS,mode='academic',classification_manifest=m);self.assertEqual(res['changes'],[]);self.assertEqual(p.read_bytes(),Path(res['output']).read_bytes())
 def test_missing_target_and_cache_mismatch(self):
  p=rewrite(SAMPLE/'automatic.docx',self.d/'missing.docx',lambda root:root.xpath('//w:hyperlink',namespaces=NS)[0].set(q('anchor'),'missing'))
  r=run(p,manifest(p));self.assertIn('多个',r['toc']['rows'][0]['reason'])
  p=rewrite(SAMPLE/'automatic.docx',self.d/'wrong.docx',lambda root:setattr(root.xpath('//w:hyperlink//w:t',namespaces=NS)[0],'text','第一章 不同缓存文字'))
  r=run(p,manifest(p));self.assertEqual(r['toc']['rows'][0]['status'],'risk');self.assertIn('缓存文字',r['toc']['rows'][0]['reason'])
 def test_same_names_and_level_conflict(self):
  p=rewrite(self.p,self.d/'dupe.docx',lambda root:setattr(root.xpath('//w:body/w:p',namespaces=NS)[7].find('.//'+q('t')),'text','第一章 演示范围'))
  m=manifest(p);r=run(p,m);self.assertIn('多候选',r['toc']['rows'][0]['reason'])
  m=deepcopy(self.m);m['toc_scope']['objects']['d:3']='level2';r=run(self.p,m);self.assertEqual(r['toc']['rows'][0]['status'],'risk')
 def test_partial_scope_does_not_claim_missing(self):
  m=deepcopy(self.m);m['paragraph_types']['6']='other';r=run(self.p,m);self.assertEqual(r['toc']['missing_candidates'],[]);self.assertIn('范围不足',r['toc']['rows'][0]['reason'])
 def test_complete_two_levels_does_not_require_third(self):
  m=deepcopy(self.m);s=m['toc_scope'];s.update(complete=True,headings_complete=True,covered_levels=[1,2]);s['objects'].pop('d:5');r=run(self.p,m);self.assertEqual(r['toc']['missing_candidates'],[])
 def test_unknown_level_and_broken_field_review(self):
  m=deepcopy(self.m);m['toc_scope']['objects']['d:4']='unknown';r=run(self.p,m);self.assertTrue(any(f['property']=='structure' and f['status']=='review' for f in toc_findings(r)))
  def corrupt(root):
   last=root.xpath('//w:fldChar[@w:fldCharType="end"]',namespaces=NS)[-1];last.getparent().remove(last)
  p=rewrite(SAMPLE/'automatic.docx',self.d/'broken.docx',corrupt);r=run(p,manifest(p));self.assertTrue(all(row['status']=='review' for row in r['toc']['rows']))
 def test_range_hash_confirmation_conflict(self):
  m=deepcopy(self.m);m['toc_scope']['confirmed']=False
  with self.assertRaises(DemoError):run(self.p,m)
  m=deepcopy(self.m);m['paragraph_types']['3']='heading1'
  with self.assertRaises(DemoError):run(self.p,m)
  m=deepcopy(self.m);m['toc_scope']['input_sha256']='0'*64
  with self.assertRaises(DemoError):run(self.p,m)
 def test_keyword_not_automatic_confirmation(self):
  inv=inventory(self.p);row=next(r for r in inv['objects'] if r['text'].startswith('正文中提到'));self.assertIsNone(row['candidate']);self.assertEqual(make_scope(self.p)['objects'],{})
 def test_custom_template_acts_on_disk_and_missing_disabled(self):
  m=deepcopy(self.m);t=m['toc_scope']['template'];t['name']='用户确认的目录演示要求'
  for n in t['values']:
   if n.startswith('level3'):t['values'][n]=None;t['sources'][n]={'kind':'not_enabled','quote':'','location':None}
  t['values']['title__font_size']=22;t['sources']['title__font_size']={'kind':'user_confirmed','quote':'','location':None}
  res=fix_document(self.p,self.d/'custom.docx',None,selected_rules=IDS,mode='academic',classification_manifest=m)
  self.assertEqual({f['actual'] for f in toc_findings(res['after']) if f['rule_id']=='R30' and f['property']=='font_size'},{22});self.assertFalse(any(f['locator'].get('toc_object')==5 and f['status']!='not_applicable' for f in toc_findings(res['after'])))
 def test_template_roundtrip_and_unknown_fields_types(self):
  t=school();self.assertEqual(t,loads(json.dumps(t).encode()))
  for n,v in [('title__font_size',True),('title__font_size',10**500),('level1__font_size',37),('level2__line_multiple',float('nan')),('level1__font_cn','未知字体')]:
   d=deepcopy(t);d['name']='用户要求';d['values'][n]=v;d['sources'][n]={'kind':'user_confirmed','quote':'','location':None}
   with self.assertRaises(DemoError):validate(d)
  t['values']['code']='x'
  with self.assertRaises(DemoError):validate(t)
 def test_mock_ai_strict_missing_and_evidence(self):
  t='目录标题小二号黑体，居中，单倍行距。';d={'fields':{n:None for n in school()['values']},'unsupported':[]};d['fields']['title__font_size']={'value':18,'unit':'pt','quote':t,'location':'TEXT:1','support':'supported'}
  self.assertEqual(validate_draft(d,t)['fields']['level1__font_size'],None)
  with self.assertRaises(DemoError):
   bad=deepcopy(d);bad['fields']['title__font_size'].update(value=14,quote='目录标题小四号');validate_draft(bad,'目录标题小四号')
  for change in [{'quote':'伪造原文'},{'value':True},{'unit':'lines'},{'location':'/Users/private'},{'extra':'exec'}]:
   bad=deepcopy(d);bad['fields']['title__font_size'].update(change)
   with self.assertRaises(DemoError):validate_draft(bad,t)
 def session(self):
  s=WebSession(self.d/'web');s.set_mode('academic');s.load(self.p.read_bytes(),'合成目录.docx');s.set_types(self.m['paragraph_types']);s.enable_toc(True);s.edit_toc(self.m['toc_scope']);s.confirm_toc();self.assertTrue(s.confirm_and_check());return s
 def test_session_invalidation_selection_isolation(self):
  s=self.session();s.set_selection([f['key'] for f in toc_findings(s.report) if f['fixable']]);other=WebSession(self.d/'web');self.assertIsNone(other.report);self.assertFalse(other.toc_enabled)
  changed=deepcopy(s.toc_draft);changed['objects']['d:3']='level2';s.edit_toc(changed);self.assertIsNone(s.report);self.assertEqual(s.selected,[]);self.assertIsNone(s.toc_confirmed)
 def test_session_multiround_manifest_binding(self):
  s=self.session();keys=[f['key'] for f in toc_findings(s.report) if f['fixable']];s.set_selection(keys[:1]);self.assertTrue(s.generate());first=Path(s.result['output']);hash1=first.read_bytes();self.assertTrue(s.next_round());self.assertEqual(s.classification_confirmed['toc_scope']['input_sha256'],Package(s.input_path).hash)
  s.set_selection([f['key'] for f in toc_findings(s.report) if f['fixable']]);self.assertTrue(s.generate());self.assertEqual(first.read_bytes(),hash1);self.assertTrue(all(f['status']=='pass' for f in toc_findings(s.result['after'])))
  s.enable_toc(False);self.assertTrue(s.confirm_and_check());s.set_selection([f['key'] for f in s.report['findings'] if f['fixable']][:1]);self.assertTrue(s.generate());self.assertTrue(s.next_round());s.enable_toc(True);self.assertEqual(s.toc_draft['input_sha256'],s.inventory['input_sha256']);self.assertEqual(s.toc_draft['objects'],{});self.assertIsNone(s.toc_confirmed)
 def test_html_zip_projection_full_and_safe(self):
  s=self.session();s.set_selection([f['key'] for f in toc_findings(s.report) if f['fixable']]);s.generate();z=zipfile.ZipFile(io.BytesIO(s.result_package()));self.assertIn('toc-supplement.json',z.namelist());html=z.read('report.html').decode();self.assertIn('实际页码',html);self.assertIn('目录对应风险',html);self.assertNotIn('/Volumes/',html);self.assertEqual(z.read('fixed.docx'),Path(s.result['output']).read_bytes())

 def test_project_confirmed_and_draft_recheck(self):
  s=self.session();raw=s.prepare_project();other=WebSession(self.d/'import');other.stage_project(raw);new=other.restore_project(acknowledged=True)
  self.assertEqual(new.toc_draft,s.toc_draft);self.assertEqual(new.report['summary'],s.report['summary']);self.assertEqual(new.report['toc']['rows'],s.report['toc']['rows'])
  new.invalidate();raw=new.prepare_project();other=WebSession(self.d/'draft');other.stage_project(raw);draft=other.restore_project(acknowledged=True);self.assertEqual(draft.toc_draft,new.toc_draft);self.assertIsNone(draft.report);self.assertIsNone(draft.toc_confirmed)
 def test_two_round_project_restore_and_continue(self):
  s=self.session();s.set_selection([f['key'] for f in toc_findings(s.report) if f['fixable']][:1]);s.generate();s.next_round();s.set_selection([f['key'] for f in toc_findings(s.report) if f['fixable']]);s.generate();raw=s.prepare_project();other=WebSession(self.d/'import');other.stage_project(raw);new=other.restore_project(acknowledged=True)
  self.assertEqual(len(new.history),2);self.assertTrue(new.toc_enabled);self.assertTrue(new.continue_history(new.history[0]['stem'],acknowledged=True));self.assertEqual(new.current_round,1);self.assertEqual(len([f for f in toc_findings(new.report) if f['status']=='problem']),5)
 def test_sdt_manual_safe_and_bound_sdt_protected(self):
  def wrap(root):
   body=root.find(q('body'));p=body.findall(q('p'))[2];i=body.index(p);body.remove(p);sdt=E.Element(q('sdt'));content=E.SubElement(sdt,q('sdtContent'));content.append(p);body.insert(i,sdt)
  p=rewrite(self.p,self.d/'sdt.docx',wrap);m=manifest(p);r=run(p,m);self.assertTrue(any(f['fixable'] and f['locator']['toc_object']==3 for f in toc_findings(r)));result=fix_document(p,self.d/'sdtfixed.docx',None,selected_rules=IDS,mode='academic',classification_manifest=m);self.assertTrue(result['preservation']['document_except_selected_format_attributes_equal'])
  def lock(root):
   sdt=root.find('.//'+q('sdt'));pr=E.SubElement(sdt,q('sdtPr'));E.SubElement(pr,q('lock')).set(q('val'),'sdtContentLocked')
  p=rewrite(p,self.d/'locked.docx',lock);r=run(p,manifest(p));self.assertTrue(all(not f['fixable'] for f in toc_findings(r) if f['locator'].get('toc_object')==3))
 def test_duplicate_properties_stay_review(self):
  def dup(root):
   p=root.find(q('body')).findall(q('p'))[2];pp=p.find(q('pPr'));E.SubElement(pp,q('spacing')).set(q('line'),'360')
  p=rewrite(self.p,self.d/'duplicate.docx',dup);r=run(p,manifest(p));self.assertEqual(next(f['status'] for f in toc_findings(r) if f['locator'].get('toc_object')==3 and f['property']=='line_multiple'),'review')
 def test_preview_and_rule_mode_invalidation(self):
  s=self.session();old=s._history_binding();c=deepcopy(s.toc_draft);c['template']['name']='用户目录要求';c['template']['values']['title__font_size']=22;c['template']['sources']['title__font_size']={'kind':'user_confirmed','quote':'','location':None};s.edit_toc(c);self.assertNotEqual(old,s._history_binding());self.assertIsNone(s.report)
  s.set_mode('extended');self.assertTrue(s.confirm_and_check());self.assertNotIn('toc_scope',s.classification_confirmed);self.assertEqual(s.report['summary']['rule_count'],12)
 def test_selected_manual_title_does_not_touch_automatic_domains(self):
  def wrong(root):root.findall('w:body/w:p',NS)[1].find('w:r/w:rPr/w:sz',NS).set(q('val'),'32')
  p=rewrite(SAMPLE/'automatic.docx',self.d/'auto-title-error.docx',wrong);m=manifest(p);a=Package(p);r=fix_document(p,self.d/'auto-title-fixed.docx',None,selected_rules=['R30'],mode='academic',classification_manifest=m);b=Package(r['output']);self.assertEqual(len(r['changes']),1)
  for tag in ('sdt','fldChar','instrText','bookmarkStart','bookmarkEnd','hyperlink','tab','tbl','drawing'):
   self.assertEqual([E.tostring(e) for e in a.root.iter(q(tag))],[E.tostring(e) for e in b.root.iter(q(tag))])
  self.assertTrue(all(b.parts[n]==v for n,v in a.parts.items() if n!='word/document.xml'))
 def test_all_safe_format_items_does_not_execute_content_hints(self):
  r=run(self.p,self.m);keys=[f['key'] for f in r['findings'] if f['fixable']];result=fix_document(self.p,self.d/'all-safe.docx',None,selected_keys=keys,mode='academic',classification_manifest=self.m)
  self.assertEqual(set(c['key'] for c in result['changes']),set(keys));self.assertFalse(any(f['fixable'] for f in result['after']['findings']));self.assertTrue(any(f['rule_id']=='R22' and f['status']=='problem' and not f['fixable'] for f in result['after']['findings']))
 def test_special_superscript_not_forced_and_pagination_preserved(self):
  def special(root):
   p=root.findall('w:body/w:p',NS)[1];rp=p.findall(q('r'))[1].find(q('rPr'));E.SubElement(rp,q('vertAlign')).set(q('val'),'superscript');E.SubElement(p.find(q('pPr')),q('keepNext')).set(q('val'),'1')
  p=rewrite(self.p,self.d/'super.docx',special);m=manifest(p);r=run(p,m);self.assertTrue(any(f['status']=='review' and f['locator'].get('toc_object')==2 for f in toc_findings(r)))
  result=fix_document(p,self.d/'superfixed.docx',None,selected_rules=IDS,mode='academic',classification_manifest=m);a=Package(p);b=Package(result['output']);self.assertEqual(E.tostring(a.paragraphs[1]),E.tostring(b.paragraphs[1]))
 def test_numbering_evidence_is_readonly_not_display_number_proof(self):
  def number(root):
   p=root.findall('w:body/w:p',NS)[5];num=E.SubElement(p.find(q('pPr')),q('numPr'));E.SubElement(num,q('numId')).set(q('val'),'1');E.SubElement(num,q('ilvl')).set(q('val'),'0')
  p=rewrite(self.p,self.d/'number.docx',number);r=run(p,manifest(p));self.assertIn('显示序号未计算',r['toc']['rows'][0]['numbering_state']);res=fix_document(p,self.d/'numberfixed.docx',None,selected_rules=IDS,mode='academic',classification_manifest=manifest(p));self.assertEqual(Package(p).parts['word/numbering.xml'],Package(res['output']).parts['word/numbering.xml'])
 def test_unsupported_table_toc_is_visible_not_counted_as_covered(self):
  def put(root):
   p=root.find('.//w:tbl/w:tr/w:tc/w:p',NS);r=p.find(q('r'));r.find(q('t')).text='目录'
  p=rewrite(self.p,self.d/'tabletoc.docx',put);r=run(p,manifest(p));self.assertEqual(len(r['toc']['inventory']['unlisted_structures']),1);self.assertTrue(any('表格/文本框中的目录' in n['detail'] for n in r['coverage_notes']))
 def test_theme_font_and_missing_font_remain_distinct(self):
  def theme(root):
   p=root.findall('w:body/w:p',NS)[3];r=p.findall(q('r'))[1];rf=r.find('w:rPr/w:rFonts',NS);rf.attrib.pop(q('eastAsia'),None);rf.set(q('eastAsiaTheme'),'minorEastAsia');lang=E.SubElement(r.find(q('rPr')),q('lang'));lang.set(q('eastAsia'),'zh-CN')
  p=rewrite(SAMPLE/'manual-correct.docx',self.d/'theme.docx',theme);r=run(p,manifest(p));f=next(f for f in toc_findings(r) if f['locator'].get('toc_object')==4 and f['locator'].get('run')==2 and f['property']=='font_cn');self.assertEqual(f['status'],'problem');self.assertEqual(f['font_evidence']['eastAsia']['theme_basis']['script'],'Jpan');self.assertEqual(f['font_evidence']['eastAsia']['theme_basis']['theme_font_lang'],'ja-JP')
  pkg=Package(p);settings=E.fromstring(pkg.parts['word/settings.xml']);settings.find(q('themeFontLang')).set(q('eastAsia'),'zh-CN');target=self.d/'supported-theme.docx'
  with zipfile.ZipFile(target,'w') as z:
   for n,b in pkg.parts.items():z.writestr(n,E.tostring(settings) if n=='word/settings.xml' else b)
  r=run(target,manifest(target));f=next(f for f in toc_findings(r) if f['locator'].get('toc_object')==4 and f['locator'].get('run')==2 and f['property']=='font_cn');self.assertEqual(f['actual'],'宋体');self.assertEqual(f['status'],'pass');self.assertIn('theme',str(f['font_evidence']).lower())
  # Same original Japanese-theme input, now remove the actual script mapping:
  # missing theme evidence still stays read-only, rather than inventing a font.
  missing=self.d/'missing-jpan.docx';original=Package(p);member=next(n for n in original.parts if n.startswith('word/theme/') and n.endswith('.xml'));theme_root=E.fromstring(original.parts[member])
  for node in list(theme_root.iter()):
   if node.get('script')=='Jpan':node.getparent().remove(node)
  with zipfile.ZipFile(missing,'w') as z:
   for n,b in original.parts.items():z.writestr(n,E.tostring(theme_root) if n==member else b)
  r=run(missing,manifest(missing));f=next(f for f in toc_findings(r) if f['locator'].get('toc_object')==4 and f['locator'].get('run')==2 and f['property']=='font_cn');self.assertEqual(f['status'],'review');self.assertFalse(f['fixable'])


 def test_combined_supplement_history_bindings_restore(self):
  s=self.session();s.enable_front(True);s.confirm_front();s.confirm_toc();self.assertTrue(s.confirm_and_check(),s.error);s.set_selection([f['key'] for f in toc_findings(s.report) if f['fixable']][:1]);self.assertTrue(s.generate(),s.error)
  raw=s.prepare_project();other=WebSession(self.d/'combined');other.stage_project(raw);new=other.restore_project(acknowledged=True);self.assertEqual(new.history[0]['binding'],new._history_binding());self.assertTrue(new.front_enabled and new.toc_enabled)
 def test_bookmark_name_without_valid_boundary_not_proof(self):
  def broken(root):
   e=root.xpath('//w:bookmarkEnd',namespaces=NS)[0];e.getparent().remove(e)
  p=rewrite(SAMPLE/'automatic.docx',self.d/'broken-bookmark.docx',broken);r=run(p,manifest(p));self.assertEqual(r['toc']['rows'][0]['status'],'review');self.assertIn('书签边界',r['toc']['rows'][0]['reason'])
 def test_relationship_link_not_claimed_internal_by_text_only(self):
  def external(root):root.xpath('//w:hyperlink',namespaces=NS)[0].set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id','unresolved-id')
  p=rewrite(SAMPLE/'automatic.docx',self.d/'rel-link.docx',external);r=run(p,manifest(p));self.assertEqual(r['toc']['rows'][0]['status'],'review');self.assertIn('关系ID',r['toc']['rows'][0]['reason'])

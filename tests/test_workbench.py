from tests.ui_navigation import show, click as ui_click
import unittest,json,tempfile,zipfile
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from core import rule_bundle as rb,load_rules,check_document
from core.package import DemoError,Package,q,NS
from core.norms import selected_segments
from web.session import WebSession
from ai.workbench_spec import parse_requirements
from ai.short_spec import Settings
ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/'samples/phase24/unified-spec.txt').read_text()
SEGMENTS=selected_segments(TEXT)
def response(segments=SEGMENTS):
 d={m:{'fields':{},'issues':[]} for m in rb.MODULES}
 data={'main':{'font_cn':('宋体','正文中文字体宋体'),'font_western':('Times New Roman','正文西文字体Times New Roman'),'font_size':(12,'正文小四号'),'line_spacing':(1.5,'正文1.5倍行距'),'first_line_indent':(2,'正文首行缩进2字符'),'heading1_font_cn':('黑体','一级标题黑体'),'heading1_font_size':(18,'一级标题18pt'),'heading1_alignment':('center','一级标题居中'),'heading1_line_spacing':(1,'一级标题单倍行距'),'abstract_cn_body__font_cn':('宋体','中文摘要正文宋体'),'abstract_cn_body__font_size':(12,'中文摘要正文12pt'),'abstract_cn_body__line_spacing':(1.5,'中文摘要正文1.5倍行距'),'table_content__font_cn':('宋体','表内文字宋体'),'table_content__font_size':(10.5,'表内文字10.5pt'),'appendix_title__font_cn':('黑体','附录标题黑体'),'appendix_title__font_size':(18,'附录标题18pt'),'appendix_title__alignment':('center','附录标题居中'),'appendix_title__line_spacing':(1,'附录标题单倍行距'),'appendix_text__font_cn':('宋体','附录普通文字宋体'),'appendix_text__font_size':(12,'附录普通文字12pt')},'front':{'cover_title__font_cn':('黑体','封面论文标题黑体'),'cover_title__font_size':(22,'封面论文标题22pt'),'cover_title__bold':(True,'封面论文标题加粗'),'cover_title__alignment':('center','封面论文标题居中'),'header_distance_mm':(18,'页眉距离18mm'),'header_text__font_cn':('宋体','页眉中文字体宋体'),'header_text__font_size':(10.5,'页眉字号10.5pt'),'header_text__alignment':('center','页眉居中')},'toc':{'title__font_cn':('黑体','目录标题黑体'),'title__font_size':(18,'目录标题18pt'),'title__alignment':('center','目录标题居中'),'title__line_multiple':(1,'目录标题单倍行距'),'level1__font_cn':('黑体','目录一级条目黑体'),'level1__font_size':(14,'目录一级条目14pt'),'level1__alignment':('left','目录一级条目居左'),'level1__line_multiple':(1.5,'目录一级条目1.5倍行距')},'notes':{'footnote__font_cn':('宋体','脚注普通文字宋体'),'footnote__font_size':(10.5,'脚注普通文字10.5pt'),'footnote__line_multiple':(1.25,'脚注普通文字1.25倍行距'),'endnote__font_cn':('宋体','尾注普通文字宋体'),'endnote__font_size':(12,'尾注普通文字12pt'),'endnote__line_multiple':(2,'尾注普通文字2倍行距')}}
 for m,fields in data.items():
  for n,(v,quote) in fields.items():
   loc=next(s['location'] for s in segments if quote in s['text']);d[m]['fields'][n]={'value':v,'unit':rb.FIELDS[m][n][2],'quote':quote,'location':loc,'support':'supported'}
 d['main']['issues']=[{'fields':[],'quote':'打印使用双面打印','location':segments[-1]['location'],'reason':'printing'}]
 return d
RECEIPT={'kind':'mock_api','model':'deepseek-flash','timestamp_utc':'2026-10-15T00:00:00+00:00'}
def parsed(segments):return {'draft':response(segments),'receipt':RECEIPT}
def make_session(root):
 s=WebSession(root);s.set_mode('academic');assert s.load((ROOT/'samples/phase24/combined-errors.docx').read_bytes(),'合成.docx'),s.error
 return s
def draft(s):
 s.workbench_text(TEXT);s.confirm_workbench_excerpt();s.parse_workbench(parser=parsed);s.workbench_policy('keep',acknowledged=True)
def scopes(s):
 ds=json.loads((ROOT/'samples/phase24/independent-scope.json').read_text());s.set_types(ds['roles']);s.exclude_materials([13],ds['excluded']['13'])
 s.enable_front(True);d=deepcopy(s.front_draft);d['objects']=ds['cover'];d['section_roles']={'1':'mixed'};s.edit_front(d);s.confirm_front()
 s.enable_toc(True);d=deepcopy(s.toc_draft);d['objects']=ds['toc'];s.edit_toc(d);s.confirm_toc()
 s.enable_notes(True);d=deepcopy(s.note_draft);d['objects']=[r['key'] for r in s.note_inventory()['objects']];s.edit_notes(d);s.confirm_notes()
 s.set_table_enabled(True);s.set_table_types(ds['table']);s.confirm_tables();s.confirm_front();s.confirm_toc();s.confirm_notes();s.confirm_classification();s.check();assert s.report,s.error
class WorkbenchTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=make_session(Path(self.tmp.name));self.base=load_rules()
 def test_one_request_payload_and_all_modules(self):
  calls=[]
  def transport(req,timeout):calls.append((req,timeout));return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(response(),ensure_ascii=False)}}]})
  r=parse_requirements(SEGMENTS,transport=transport,config=Settings('not-recorded'))
  self.assertEqual(len(calls),1);self.assertEqual(calls[0][1],30);self.assertEqual(r['receipt']['request_count'],1)
  body=json.loads(calls[0][0].data);self.assertEqual(body['messages'][-1]['content'],rb.marked_text(SEGMENTS));self.assertNotIn('合成.docx',calls[0][0].data.decode());self.assertNotIn('not-recorded',calls[0][0].data.decode())
 def test_missing_fields_not_invented(self):
  draft(self.s);d=self.s.workbench['draft'];self.assertIsNone(d['fields']['main']['margin_top']['candidate']);self.assertEqual(d['fields']['front']['footer_distance_mm']['mode'],'keep');self.assertIsNone(self.s.proposed_rule_bundle()['modules']['front']['values']['footer_distance_mm'])
 def test_actual_all_module_application_and_roundtrip(self):
  draft(self.s);self.s.workbench_edit('front','cover_title__font_size','manual',24);b=self.s.apply_workbench(acknowledged=True)
  self.assertEqual(b['provenance']['front']['cover_title__font_size']['kind'],'user_confirmed');scopes(self.s)
  for rid in ('R05','R08','R15','R23','R24','R26','R30','R31','R36','R37','R38','R39'):self.assertTrue(any(f['rule_id']==rid and f['status']=='problem' for f in self.s.report['findings']),rid)
  self.s.set_selection([f['key'] for f in self.s.eligible()]);self.assertTrue(self.s.generate(),self.s.error)
  self.assertFalse([f for f in self.s.result['after']['findings'] if f['status']=='problem' and f['fixable']])
  out=Package(self.s.result['output']);self.assertEqual(out.paragraphs[0].find('w:r/w:rPr/w:sz',NS).get(q('val')),'48')
  # Independent ZIP check: body text, notes markers/IDs/relationships are byte-preserved or unchanged XML.
  orig=Package(self.s.input_path)
  self.assertEqual(orig.root.xpath('//w:t/text()',namespaces=NS),out.root.xpath('//w:t/text()',namespaces=NS))
  self.assertEqual(orig.parts['word/_rels/document.xml.rels'],out.parts['word/_rels/document.xml.rels'])
  for part in ('word/footnotes.xml','word/endnotes.xml'):
   from lxml import etree as E
   a=E.fromstring(orig.parts[part]);c=E.fromstring(out.parts[part]);self.assertEqual(a.xpath('//w:t/text()',namespaces=NS),c.xpath('//w:t/text()',namespaces=NS));self.assertEqual(a.xpath('//@w:id',namespaces=NS),c.xpath('//@w:id',namespaces=NS))
  raw=self.s.rule_bundle_download();other=make_session(Path(self.tmp.name)/'other');other.import_rule_bundle(raw);self.assertIsNone(other.active_template);other.apply_workbench(acknowledged=True);scopes(other)
  self.assertEqual(rb.flat('front',other.current_rule_bundle()['modules']['front']),rb.flat('front',b['modules']['front']))
 def test_draft_no_active_mutation_and_apply_invalidation(self):
  scopes(self.s);old=self.s.rules_hash;draft(self.s);self.assertEqual(old,self.s.rules_hash);self.assertIsNotNone(self.s.report);self.s.apply_workbench(acknowledged=True);self.assertIsNone(self.s.report);self.assertIsNone(self.s.front_confirmed);self.assertEqual(self.s.front_draft['objects'],{'p:1':'title'})
 def test_atomic_invalid_module_rolls_back(self):
  draft(self.s);old=(self.s.rules_hash,self.s.custom_rules_path,self.s.workbench['active']);self.s.workbench['draft']['fields']['toc']['title__font_size'].update(mode='manual',value=200)
  with self.assertRaises(DemoError):self.s.apply_workbench(acknowledged=True)
  self.assertEqual(old,(self.s.rules_hash,self.s.custom_rules_path,self.s.workbench['active']))
 def test_atomic_storage_failure_rolls_back(self):
  draft(self.s);old=self.s.rules_hash
  with patch('web.workbench_session.write_new',side_effect=OSError('disk failure')):
   with self.assertRaises(OSError):self.s.apply_workbench(acknowledged=True)
  self.assertEqual(old,self.s.rules_hash);self.assertIsNone(self.s.custom_rules_path)
 def test_no_apply_without_acknowledgement(self):
  draft(self.s)
  with self.assertRaises(DemoError):self.s.apply_workbench()
 def test_nonfinite_and_unknown_and_forged_source(self):
  for m,n,change in [('main','font_size',{'value':True}),('main','font_size',{'value':float('nan')}),('notes','footnote__font_size',{'value':50}),('front','header_distance_mm',{'location':'TEXT:1'}),('toc','title__font_size',{'quote':'伪造的原文'})]:
   d=response();d[m]['fields'][n].update(change)
   with self.subTest(m=m,change=change),self.assertRaises(DemoError):rb.validate_draft(d,SEGMENTS)
  d=response();d['toc']['fields']['execute']='anything'
  with self.assertRaises(DemoError):rb.validate_draft(d,SEGMENTS)
 def test_cross_module_proof_rejected(self):
  d=response();d['notes']['fields']['footnote__font_size'].update(quote='正文小四号',location=SEGMENTS[1]['location'],value=12)
  with self.assertRaises(DemoError):rb.validate_draft(d,SEGMENTS)
 def test_conflict_cannot_carry_value(self):
  d=response();d['toc']['issues']=[{'fields':['title__font_size'],'quote':'目录标题18pt','location':SEGMENTS[9]['location'],'reason':'conflict'}]
  with self.assertRaises(DemoError):rb.validate_draft(d,SEGMENTS)
 def test_conflict_elsewhere_not_ignored(self):
  for m,extra in [('front','封面论文标题24pt。'),('toc','目录标题22pt。'),('notes','脚注普通文字12pt。')]:
   seg=SEGMENTS+[{'location':'摘录:L99','text':extra}]
   with self.subTest(m=m),self.assertRaises(DemoError):rb.validate_draft(response(),seg)
 def test_disable_legacy_property_no_default_execution(self):
  draft(self.s);self.s.workbench_edit('main','font_size','disabled');self.s.workbench_edit('main','margin_left','disabled');self.s.apply_workbench(acknowledged=True);scopes(self.s)
  self.assertFalse(any(f['rule_id']=='R05' for f in self.s.report['findings']));self.assertIn('font_size',self.s.report['coverage']['explicitly_not_checked_fields'])
 def test_duplicate_json_key_unknown_module_version_rejected(self):
  draft(self.s);d=self.s.proposed_rule_bundle()
  for obj in [dict(d,version=2),dict(d,modules={**d['modules'],'evil':{}}),dict(d,modules={'main':d['modules']['main']})]:
   with self.assertRaises(DemoError):rb.loads(rb.raw(obj),self.base)
  with self.assertRaises(DemoError):rb.loads(b'{"version":1,"version":1}',self.base)
 def test_no_duplicate_request_rerun_edit_export(self):
  draft(self.s)
  with self.assertRaises(DemoError):self.s.parse_workbench(parser=lambda _:self.fail('second request'))
  self.s.workbench_edit('front','cover_title__font_size','manual',24);self.s.apply_workbench(acknowledged=True);self.s.rule_bundle_download();self.s.rule_bundle_download();self.assertTrue(self.s.workbench['parse_attempted'])
 def test_failed_api_keeps_active_template(self):
  old=self.s.rules_hash;self.s.workbench_text(TEXT);self.s.confirm_workbench_excerpt()
  with self.assertRaises(TimeoutError):self.s.parse_workbench(parser=lambda _:(_ for _ in ()).throw(TimeoutError()))
  self.assertEqual(old,self.s.rules_hash);self.s.confirm_classification();self.s.check();self.assertIsNotNone(self.s.report)
 def test_project_restores_applied_and_unapplied_draft(self):
  draft(self.s);self.s.apply_workbench(acknowledged=True);scopes(self.s);self.s.start_workbench_draft();self.s.workbench_edit('notes','footnote__font_size','manual',11);self.s.workbench_policy('keep',acknowledged=True)
  raw=self.s.prepare_project();n=WebSession(Path(self.tmp.name)/'restore');n.stage_project(raw);n=n.restore_project(acknowledged=True)
  self.assertEqual(n.workbench['draft']['fields']['notes']['footnote__font_size']['value'],11)
  self.assertEqual(n.workbench['active']['modules']['notes']['values']['footnote']['font_size'],10.5);self.assertIsNotNone(n.report);self.assertEqual(n.workbench['origin'],'restored')
 def test_bundle_has_no_document_locators(self):
  draft(self.s);self.s.apply_workbench(acknowledged=True);scopes(self.s);d=json.loads(self.s.rule_bundle_download())
  for needle in ('input_sha256','paragraph_types','objects','note_id','section_roles','task_dir','DEEPSEEK_API_KEY'):
   self.assertNotIn('"'+needle+'"',json.dumps(d,ensure_ascii=False))
 def test_external_rule_change_download_rejected(self):
  draft(self.s);self.s.apply_workbench(acknowledged=True);self.s.custom_rules_path.write_bytes(b'{}')
  with self.assertRaises(DemoError):self.s.rule_bundle_download()
 def test_native_edit_synchronizes_canonical(self):
  draft(self.s);self.s.apply_workbench(acknowledged=True);self.s.enable_toc(True);d=deepcopy(self.s.toc_draft);d['template']['values']['title__font_size']=20;d['template']['sources']['title__font_size']={'kind':'user_confirmed','quote':'','location':None};self.s.edit_toc(d)
  self.assertEqual(self.s.current_rule_bundle()['modules']['toc']['values']['title__font_size'],20);self.assertEqual(json.loads(self.s.custom_rules_path.read_bytes())['modules']['toc']['values']['title__font_size'],20)
 def test_old_v6_import_keeps_other_modules_unconfigured(self):
  t=rb.defaults(self.base)['main']['template'];self.s.import_rule_bundle(rb.raw(t));self.s.workbench_policy('keep',acknowledged=True);p=self.s.proposed_rule_bundle();self.assertIsNone(p['modules']['toc']);self.assertEqual(p['modules']['main']['template']['final_values'],t['final_values'])
 def test_two_sessions_are_private(self):
  draft(self.s);n=make_session(Path(self.tmp.name)/'other');self.assertIsNone(n.workbench['draft']);self.s.apply_workbench(acknowledged=True);self.assertIsNone(n.workbench['active']);self.assertNotEqual(n.task_dir,self.s.task_dir)
 def test_form_edit_uses_submitted_value_and_provenance(self):
  from streamlit.testing.v1 import AppTest
  draft(self.s);app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);app.session_state['workflow']=self.s;app.run();show(app,1,rules=True);self.assertFalse(app.exception)
  next(x for x in app.selectbox if x.label=='查看与编辑模块').set_value('front');app.run()
  next(x for x in app.selectbox if x.label=='编辑字段').set_value('cover_title__font_size');app.run()
  next(x for x in app.text_input if x.label.startswith('最终值（')).set_value('24')
  next(x for x in app.button if x.label=='采用此字段到草稿').click();app.run();self.assertFalse(app.exception)
  self.assertEqual(self.s.workbench['draft']['fields']['front']['cover_title__font_size']['value'],24)
  self.assertEqual(self.s.proposed_rule_bundle()['provenance']['front']['cover_title__font_size']['kind'],'user_confirmed')
 def test_front_object_form_keeps_user_selection(self):
  from streamlit.testing.v1 import AppTest
  self.s.enable_front(True);app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);app.session_state['workflow']=self.s;app.run();show(app,2,'front')
  next(x for x in app.selectbox if x.label=='此对象代表的封面字段').set_value('title')
  next(x for x in app.button if x.label=='应用此封面定位草稿').click();app.run();self.assertFalse(app.exception);self.assertEqual(self.s.front_draft['objects'],{'p:1':'title'})
 def test_keep_uses_live_value_and_never_claims_new_ai(self):
  draft(self.s);self.s.apply_workbench(acknowledged=True);self.s.start_workbench_draft();self.s.workbench_policy('keep',acknowledged=True)
  self.s.enable_toc(True);d=deepcopy(self.s.toc_draft);d['template']['values']['title__font_size']=20;d['template']['sources']['title__font_size']={'kind':'user_confirmed','quote':'','location':None};self.s.edit_toc(d)
  p=self.s.proposed_rule_bundle();self.assertEqual(p['modules']['toc']['values']['title__font_size'],20);self.assertEqual(p['provenance']['main']['font_cn']['kind'],'user_confirmed')
 def test_module_scope_mismatch_is_rejected(self):
  draft(self.s);self.s.apply_workbench(acknowledged=True);scopes(self.s);m=deepcopy(self.s.classification_confirmed);m['toc_scope']['template']['values']['title__font_size']=20;m['toc_scope']['template']['sources']['title__font_size']={'kind':'user_confirmed','quote':'','location':None}
  with self.assertRaises(DemoError):check_document(self.s.input_path,custom_rules_path=self.s.custom_rules_path,mode='academic',classification_manifest=m)
 def test_legacy_import_versions_keep_values_and_disabled_new_fields(self):
  from core import templates as t,academic_templates as a,table_templates as tt
  b=self.base
  v2=t.make_template('旧正文模板',t.defaults(b),{n:{'kind':'default_inherited','quote':'','location':None} for n in t.FIELDS},[],b)
  v3=t.upgrade_template(v2,b);v4=a.make(v3,{n:None for n in a.EXTRA},{n:deepcopy(rb.EMPTY) for n in a.EXTRA},[],b);v5=tt.make(v4,{n:None for n in tt.EXTRA},{n:deepcopy(rb.EMPTY) for n in tt.EXTRA},b);v6=rb.back.upgrade(v5,b)
  for original in (v2,v3,v4,v5,v6):
   with self.subTest(version=original['structure_version']):
    self.s.import_rule_bundle(rb.raw(original));self.s.workbench_policy('keep',acknowledged=True);p=self.s.proposed_rule_bundle();vals=rb.flat('main',p['modules']['main']);self.assertTrue(all(vals[n]==v for n,v in original['final_values'].items()));self.assertIsNone(p['modules']['notes']);self.assertTrue(all(vals[n] is None for n in rb.back.EXTRA))
 def test_truncated_response_only_one_request(self):
  calls=[]
  def transport(req,timeout):calls.append(1);return json.dumps({'choices':[{'finish_reason':'length','message':{'content':'{}'}}]})
  with self.assertRaises(DemoError):parse_requirements(SEGMENTS,transport=transport,config=Settings('not-recorded'))
  self.assertEqual(len(calls),1)
 def test_explicit_disabled_margin_not_modified(self):
  draft(self.s);self.s.workbench_edit('main','margin_left','disabled');self.s.workbench_edit('main','margin_right','manual',30);self.s.apply_workbench(acknowledged=True);scopes(self.s)
  self.s.set_selection([f['key'] for f in self.s.eligible() if f['rule_id']=='R02']);self.assertTrue(self.s.generate(),self.s.error)
  old=Package(self.s.input_path);new=Package(self.s.result['output']);a=old.sections[0].find(q('pgMar'));b=new.sections[0].find(q('pgMar'));self.assertEqual(a.get(q('left')),b.get(q('left')));self.assertEqual(b.get(q('right')),str(round(30*1440/25.4)))

 def test_unknown_front_font_does_not_pass_substring_match(self):
  seg=deepcopy(SEGMENTS);seg[7]['text']=seg[7]['text'].replace('封面论文标题黑体','封面论文标题方正黑体');d=response();d['front']['fields']['cover_title__font_cn']['quote']='封面论文标题方正黑体'
  with self.assertRaises(DemoError):rb.validate_draft(d,seg)
 def test_disabled_rule_count_without_body_is_accurate(self):
  draft(self.s);self.s.workbench_edit('main','font_size','disabled');self.s.apply_workbench(acknowledged=True)
  self.s.set_types({n:'other' for n in self.s.paragraph_types});self.s.confirm_classification();self.s.check();self.assertEqual(self.s.report['summary']['rule_count'],25)
 def test_unsafe_timestamp_is_not_a_private_path_channel(self):
  draft(self.s);b=self.s.proposed_rule_bundle();b['extraction']['timestamp_utc']='/Users/private/session'
  with self.assertRaises(DemoError):rb.validate(b,self.base)
 def test_restored_receipt_stays_historical_after_manual_edit(self):
  draft(self.s);self.s.apply_workbench(acknowledged=True);self.s.workbench['historical']=True;self.s.workbench_edit('front','cover_title__font_size','manual',24);self.assertTrue(self.s.workbench['historical'])
 def test_no_input_external_config_change_blocks_bundle_download(self):
  n=WebSession(Path(self.tmp.name)/'preinput');n.set_mode('academic');n.start_workbench_draft();n.workbench_policy('keep',acknowledged=True);n.apply_workbench(acknowledged=True);n.custom_rules_path.write_bytes(b'{}')
  with self.assertRaises(DemoError):n.rule_bundle_download()
 def test_legacy_front_original_marker_is_preserved_not_fabricated(self):
  self.s.enable_front(True);self.s.front_spec='封面论文标题黑体，封面论文标题22pt。';self.s.front_ai_receipt=RECEIPT
  d=deepcopy(self.s.front_draft);d['template']['name']='用户确认的封面要求';d['template']['values']['cover_title__font_cn']='黑体';d['template']['sources']['cover_title__font_cn']={'kind':'ai_extracted','quote':'封面论文标题黑体','location':'TEXT:1'};self.s.edit_front(d)
  b=self.s.current_rule_bundle();self.assertIn({'location':'TEXT:1','text':self.s.front_spec},b['excerpt']);self.assertEqual(b['provenance']['front']['cover_title__font_cn']['location'],'TEXT:1')

 def test_transaction_rejects_a_change_to_disabled_margin(self):
  draft(self.s);self.s.workbench_edit('main','margin_left','disabled');self.s.workbench_edit('main','margin_right','manual',30);self.s.apply_workbench(acknowledged=True);scopes(self.s)
  self.s.set_selection([f['key'] for f in self.s.eligible() if f['rule_id']=='R02'])
  from core.engine import _apply
  def corrupt(pkg,f):
   _apply(pkg,f)
   if f['rule_id']=='R02':
    e=pkg.sections[0].find(q('pgMar'));e.set(q('left'),str(int(e.get(q('left')))+1))
  with patch('core.engine._apply',side_effect=corrupt):self.assertFalse(self.s.generate())
  self.assertIsNone(self.s.result);self.assertIn('超出允许',self.s.error)

 def test_replacing_same_txt_line_numbers_keeps_exact_both_sources(self):
  segments=[{'location':'TXT:L'+str(i),'text':s['text']} for i,s in enumerate(SEGMENTS,1)]
  self.s.workbench_text(TEXT,segments);self.s.confirm_workbench_excerpt();self.s.parse_workbench(parser=parsed);self.s.workbench_policy('keep',acknowledged=True);self.s.apply_workbench(acknowledged=True)
  text2=TEXT.replace('正文小四号','正文14pt');segments2=[{'location':'TXT:L'+str(i),'text':s['text']} for i,s in enumerate(selected_segments(text2),1)]
  self.s.workbench_text(text2,segments2);self.s.confirm_workbench_excerpt()
  def parser(segs):
   d={m:{'fields':{},'issues':[]} for m in rb.MODULES};loc=next(x['location'] for x in segs if '正文14pt' in x['text']);d['main']['fields']['font_size']={'value':14,'unit':'pt','quote':'正文14pt','location':loc,'support':'supported'};return {'draft':d,'receipt':RECEIPT}
  self.s.parse_workbench(parser=parser);self.s.workbench_policy('keep',acknowledged=True);b=self.s.apply_workbench(acknowledged=True)
  self.assertEqual(rb.flat('main',b['modules']['main'])['font_size'],14);self.assertEqual(b['provenance']['main']['font_size']['kind'],'ai_extracted');self.assertEqual(b['provenance']['main']['font_cn']['kind'],'user_confirmed');self.assertTrue(any('正文小四号' in x['text'] for x in b['excerpt']));self.assertTrue(any('正文14pt' in x['text'] for x in b['excerpt']))
  other=make_session(Path(self.tmp.name)/'other');draft(other);other.apply_workbench(acknowledged=True);other.import_rule_bundle(rb.raw(b));loaded=other.apply_workbench(acknowledged=True);self.assertEqual(loaded['provenance'],b['provenance'])
 def test_same_request_cannot_hide_conflict_in_two_source_groups(self):
  from core.norms import qualify_segments
  a=qualify_segments([{'location':'TXT:L1','text':'正文12pt。'}]);b=qualify_segments([{'location':'TXT:L1','text':'正文14pt。'}]);d={m:{'fields':{},'issues':[]} for m in rb.MODULES};d['main']['fields']['font_size']={'value':12,'unit':'pt','quote':'正文12pt','location':a[0]['location'],'support':'supported'}
  with self.assertRaises(DemoError):rb.validate_draft(d,a+b)
 def test_namespace_hash_and_external_norm_file_are_checked(self):
  from core.norms import qualify_segments
  a=qualify_segments([{'location':'TXT:L1','text':'正文12pt。'}]);a[0]['text']='正文14pt。'
  with self.assertRaises(DemoError):rb.validate_draft({m:{'fields':{},'issues':[]} for m in rb.MODULES},a)
  self.s.load_norm(TEXT.encode(),'format.txt');self.s.select_norm_segments([s['location'] for s in self.s.norm_inventory['segments']]);self.s.workbench_text(self.s.norm_text,self.s.norm_segments);self.s.confirm_workbench_excerpt();self.s.norm_path.write_bytes(b'changed')
  with self.assertRaises(DemoError):self.s.parse_workbench(parser=lambda _:self.fail('API must not run'))
  self.assertFalse(self.s.workbench['parse_attempted'])

 def test_batch_policy_form_requires_ack_and_uses_submitted_strategy(self):
  from streamlit.testing.v1 import AppTest
  self.s.workbench_text(TEXT);self.s.confirm_workbench_excerpt();self.s.parse_workbench(parser=parsed)
  app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30);app.session_state['workflow']=self.s;app.run();show(app,1,rules=True)
  next(x for x in app.button if x.label=='采用未决定字段策略').click();app.run();self.assertFalse(app.exception);self.assertEqual(self.s.workbench['draft']['fields']['main']['margin_top']['mode'],'choose')
  next(x for x in app.radio if x.label=='这些字段的处理').set_value('disabled');next(x for x in app.checkbox if x.label=='已核对批量影响字段，采用以上策略').check();next(x for x in app.button if x.label=='采用未决定字段策略').click();app.run()
  self.assertFalse(app.exception);self.assertEqual(self.s.workbench['draft']['fields']['main']['margin_top']['mode'],'disabled');self.assertEqual(self.s.workbench['draft']['fields']['main']['font_size']['mode'],'ai');self.assertIsNone(self.s.workbench['active'])

 def test_project_cannot_substitute_a_different_valid_active_bundle(self):
  from io import BytesIO
  draft(self.s);self.s.apply_workbench(acknowledged=True);scopes(self.s);raw=self.s.prepare_project()
  with zipfile.ZipFile(BytesIO(raw)) as z:members={n:z.read(n) for n in z.namelist()}
  manifest=json.loads(members['project.json']);forged=manifest['state']['editor']['workbench']['active'];forged['modules']['main']['disabled_fields'].append('font_size');forged['provenance']['main']['font_size']=deepcopy(rb.EMPTY);rb.validate(forged,self.base)
  members['project.json']=rb.raw(manifest);out=BytesIO()
  with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
   for n,data in members.items():z.writestr(n,data)
  old=self.s.input_path
  with self.assertRaisesRegex(DemoError,'生效规则包与项目规则文件不一致'):self.s.stage_project(out.getvalue())
  self.assertEqual(self.s.input_path,old);self.assertTrue(old.exists())

 def test_unsupported_evidence_roundtrips_without_execution(self):
  draft(self.s);self.s.apply_workbench(acknowledged=True);raw=self.s.rule_bundle_download();b=rb.loads(raw,self.base);self.assertTrue(b['notices']['main']);self.assertEqual(b['notices']['main'][0]['reason'],'printing')
  other=make_session(Path(self.tmp.name)/'other');other.import_rule_bundle(raw);self.assertEqual(other.workbench['draft']['issues'],b['notices']);self.assertIsNone(other.workbench['active']);other.apply_workbench(acknowledged=True);self.assertEqual(other.current_rule_bundle()['notices'],b['notices'])

if __name__=='__main__':unittest.main()

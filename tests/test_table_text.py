"""Stage16 actual XML, scope, source, preservation and front/back adjacency acceptance."""
import unittest,json,zipfile
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from lxml import etree as E
from core import check_document,fix_document,load_rules
from core.package import Package,q,NS,sha256,DemoError
from core.engine import _ensure
from core.table_text import inventory,validate_scope,tables
from core.layout import suggest_pagination_aids,apply_pagination_layout
from core.table_templates import V5_FIELDS,EXTRA,make,validate,candidate,validate_draft,defaults,value
from core.academic_templates import default_values
from core.templates import validate_template
from web.session import WebSession
from tests.test_academic import template as v4_template

ROOT=Path(__file__).resolve().parents[1];GOOD=ROOT/'samples/table-text-correct.docx';BAD=ROOT/'samples/table-text-errors.docx'
M=json.loads(GOOD.with_suffix('.types.json').read_text())
def v5(changes=None):
 vals={n:None for n in EXTRA};vals.update(changes or {});sources={n:{'kind':'user_confirmed' if v is not None else 'not_enabled','quote':'','location':None} for n,v in vals.items()}
 return make(v4_template(),vals,sources,load_rules())
class TableTextAcceptance(unittest.TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def manifest(self,p=GOOD,roles=None):
  m=deepcopy(M);h=sha256(Path(p).read_bytes());m['input_sha256']=h;m['table_scope']['input_sha256']=h
  if roles:m['table_scope']['table_types']=roles
  return m
 def check(self,p=GOOD,m=None,custom=None):return check_document(p,mode='academic',classification_manifest=m or self.manifest(p),**({'custom_rules_path':custom} if custom else {}))
 def config(self,data):
  p=self.root/'template.json';p.write_text(json.dumps(data,ensure_ascii=False));return p
 def alter(self,fn):
  p=self.root/'input.docx';p.write_bytes(GOOD.read_bytes());pkg=Package(p);fn(pkg);pkg.parts['word/styles.xml']=E.tostring(pkg.styles,xml_declaration=True,encoding='UTF-8',standalone=True);p.write_bytes(pkg.bytes(True));return p
 def model(self):
  s=WebSession(self.root);s.set_mode('academic');self.assertTrue(s.load(BAD.read_bytes(),'software.docx'));s.set_types(M['paragraph_types']);s.set_table_enabled(True);s.set_table_types(M['table_scope']['table_types']);s.confirm_tables();self.assertTrue(s.confirm_and_check(),s.error);return s
 def test_inventory_actual_section_position_and_roles(self):
  inv=inventory(GOOD);self.assertEqual(len(inv['tables']),7);self.assertTrue(inv['tables'][3]['merged']);self.assertTrue(inv['tables'][5]['nested']);self.assertEqual(inv['tables'][0]['section'],1)
 def test_correct_control_and_complex_review_counts(self):
  r=self.check();self.assertEqual((r['summary']['problem_count'],r['summary']['review_count']),(0,9));self.assertEqual(r['summary']['rule_count'],23)
 def test_independent_error_gold_exact_all_late_runs(self):
  r=self.check(BAD);gold=json.loads((ROOT/'samples/table-text-expected-errors.json').read_text());errors=[f for f in r['findings'] if f['status']=='problem'];self.assertEqual(len(errors),5)
  self.assertEqual([{**f['locator'],'expected':f['expected']} for f in errors],gold['errors']);self.assertTrue(any(f['locator']['cell_paragraph']==1 and f['locator']['run']==2 for f in errors))
 def test_cover_not_checked_or_changed(self):
  r=self.check(BAD);self.assertFalse(any(f['locator'].get('table')==1 for f in r['findings']));out=fix_document(BAD,self.root/'fixed.docx',None,mode='academic',classification_manifest=self.manifest(BAD),selected_rules=['R23']);self.assertEqual(E.tostring(tables(Package(BAD))[0]),E.tostring(tables(Package(out['output']))[0]))
 def test_merged_actual_cells_once(self):
  fs=[f for f in self.check()['findings'] if f['locator'].get('table')==4];self.assertEqual(len(fs),10);self.assertEqual(len({f['key'] for f in fs}),len(fs));self.assertTrue(any(f['locator']['cell_paragraph']==2 for f in fs))
 def test_multi_paragraph_cell_is_checked(self):
  self.assertTrue(any(f['locator'].get('table')==2 and f['locator'].get('cell_paragraph')==2 for f in self.check()['findings']))
 def test_paragraph_and_character_style_inheritance(self):
  f=next(f for f in self.check(BAD)['findings'] if f['locator'].get('table')==3 and f['status']=='problem' and f['property']=='font_cn');self.assertIn('DemoTableWrong',str(f['font_evidence']))
 def test_whole_table_style_before_explicit_paragraph_and_run(self):
  def fn(pkg):
   t=tables(pkg)[2];style=E.SubElement(pkg.styles,q('style'),{q('type'):'table',q('styleId'):'PlainTable'});rp=E.SubElement(style,q('rPr'));E.SubElement(rp,q('rFonts'),{q('eastAsia'):'黑体'});E.SubElement(rp,q('sz'),{q('val'):'24'});_ensure(_ensure(t,'tblPr'),'tblStyle').set(q('val'),'PlainTable')
  r=self.check(self.alter(fn));fs=[f for f in r['findings'] if f['locator'].get('table')==3];self.assertTrue(all(f['status']=='pass' for f in fs))
 def test_conditions_review_unless_unique_direct_override(self):
  fs=[f for f in self.check()['findings'] if f['locator'].get('table')==7];self.assertEqual(sum(f['status']=='review' for f in fs),6);self.assertTrue(all(not f['fixable'] for f in fs));self.assertEqual(sum(f['status']=='pass' for f in fs),2)
 def test_special_superscript_formula_and_nested_preserved(self):
  r=self.check(BAD);self.assertTrue(any(n['locator'].get('table')==5 and '上角标' in n['detail'] for n in r['coverage_notes']));self.assertTrue(any(f['locator'].get('table')==6 and f['status']=='review' for f in r['findings']))
  def wrapped(pkg):
   t=tables(pkg)[5];holder=E.Element(q('sdt'));t.addprevious(holder);t.getparent().remove(t);holder.append(t)
  p=self.alter(wrapped);m=self.manifest(p,{'1':'cover',**{str(i):'content' for i in range(2,7)}});report=self.check(p,m);self.assertEqual(len(inventory(p)['unlisted_tables']),1);self.assertTrue(any('未列入可确认清单' in n['detail'] for n in report['coverage_notes']))
 def test_selected_readback_structure_geometry_and_other_slots(self):
  old=Package(BAD);out=fix_document(BAD,self.root/'fixed.docx',None,mode='academic',classification_manifest=self.manifest(BAD),selected_rules=['R23']);new=Package(out['output']);self.assertEqual(out['after']['summary']['problem_count'],0);self.assertEqual(out['after']['summary']['review_count'],9)
  self.assertEqual({k:v for k,v in old.parts.items() if k!='word/document.xml'},{k:v for k,v in new.parts.items() if k!='word/document.xml'});self.assertTrue(out['preservation']['document_except_selected_format_attributes_equal']);self.assertEqual(BAD.read_bytes(),old.raw)
  for a,b in zip(old.root.xpath('//w:tblPr|//w:tblGrid|//w:tcPr|//w:trPr',namespaces=NS),new.root.xpath('//w:tblPr|//w:tblGrid|//w:tcPr|//w:trPr',namespaces=NS)):self.assertEqual(E.tostring(a),E.tostring(b))
  self.assertEqual(old.root.xpath('//w:t/text()',namespaces=NS),new.root.xpath('//w:t/text()',namespaces=NS));self.assertEqual(old.root.xpath('//w:rFonts/@w:ascii',namespaces=NS),new.root.xpath('//w:rFonts/@w:ascii',namespaces=NS))
 def test_partial_font_keeps_size_and_other_errors(self):
  f=next(f for f in self.check(BAD)['findings'] if f['rule_id']=='R23' and f['status']=='problem');out=fix_document(BAD,self.root/'fixed.docx',None,mode='academic',classification_manifest=self.manifest(BAD),selected_keys=[f['key']]);self.assertEqual(len(out['changes']),1);self.assertEqual(out['after']['summary']['problem_count'],4)
 def test_repeat_repair_no_extra_byte_changes(self):
  out=fix_document(BAD,self.root/'one.docx',None,mode='academic',classification_manifest=self.manifest(BAD),selected_rules=['R23']);two=fix_document(out['output'],self.root/'two.docx',None,mode='academic',classification_manifest=out['output_classification_manifest'],selected_rules=['R23']);self.assertEqual(Path(out['output']).read_bytes(),Path(two['output']).read_bytes());self.assertEqual(two['changes'],[])
 def test_scope_hash_and_confirmation_rejected(self):
  m=self.manifest();m['table_scope']['confirmed']=False
  with self.assertRaises(DemoError):self.check(m=m)
  m=self.manifest();m['table_scope']['input_sha256']='0'*64
  with self.assertRaises(DemoError):self.check(m=m)
 def test_scope_unknown_duplicate_or_type_rejected(self):
  for types in ({'1':'content'},{**M['table_scope']['table_types'],'8':'content'},{**M['table_scope']['table_types'],'1':True}):
   with self.assertRaises(DemoError):validate_scope(Package(GOOD),{**M['table_scope'],'table_types':types})
 def test_old_modes_and_no_scope_rule_count_unchanged(self):
  m=self.manifest();m.pop('table_scope');self.assertEqual(self.check(m=m)['summary']['rule_count'],22)
  with self.assertRaises(DemoError):fix_document(GOOD,self.root/'wrong-mode.docx',None,mode='extended',classification_manifest=self.manifest(),selected_rules=['R23'])
 def test_old_v4_does_not_silently_enable_table_format(self):
  r=self.check(BAD,custom=self.config(v4_template()));self.assertFalse(any(f['rule_id']=='R23' and f['status']!='not_applicable' for f in r['findings']))
 def test_v5_custom_font_and_size_real_changes_and_reimport(self):
  d=v5({'table_content__font_cn':'楷体','table_content__font_size':11.5});self.assertEqual(validate_template(json.loads(json.dumps(d)),load_rules()),d);p=self.config(d);r=self.check(custom=p);keys=[f['key'] for f in r['findings'] if f['rule_id']=='R23' and f['fixable']];out=fix_document(GOOD,self.root/'fixed.docx',None,mode='academic',classification_manifest=self.manifest(),custom_rules_path=p,selected_keys=keys);self.assertEqual(out['after']['summary']['problem_count'],0)
 def test_v5_invalid_types_ranges_unknown_version(self):
  for n,v in [('table_content__font_cn','未知'),('table_content__font_size',True),('table_content__font_size',25),('table_content__font_size',11.3),('table_content__font_size',float('nan'))]:
   with self.assertRaises(DemoError):value(n,v)
  d=v5();d['structure_version']=6
  with self.assertRaises(DemoError):validate_template(d,load_rules())
 def test_AI_table_body_caption_not_interchangeable(self):
  for text in ['表题五号宋体','正文小四宋体','封面表格文字五号宋体']:
   with self.assertRaises(DemoError):candidate('table_content__font_size',{'value':10.5,'unit':'pt','quote':text,'location':'TXT:L1','support':'supported'},[{'text':text,'location':'TXT:L1'}])
 def test_AI_missing_conflict_quote_and_units(self):
  seg=[{'location':'TXT:L1','text':'表内文字五号宋体。表内文字小四宋体。'}]
  with self.assertRaises(DemoError):candidate('table_content__font_size',{'value':10.5,'unit':'pt','quote':'表内文字五号宋体','location':'TXT:L1','support':'supported'},seg)
  draft={n:None for n in V5_FIELDS};draft['unsupported']=[];self.assertEqual(validate_draft(draft,seg)['table_content__font_size'],None)
 def test_AI_valid_public_table_text_and_payload(self):
  from ai.academic_spec import parse_requirements
  from ai.short_spec import Settings
  seg=[{'location':'TXT:L1','text':'表内文字宋体五号。'}];draft={n:None for n in V5_FIELDS};draft['unsupported']=[]
  draft['table_content__font_cn']={'value':'宋体','unit':'font','quote':'表内文字宋体五号','location':'TXT:L1','support':'supported'}
  draft['table_content__font_size']={'value':10.5,'unit':'pt','quote':'表内文字宋体五号','location':'TXT:L1','support':'supported'}
  def transport(req,timeout):
   payload=json.loads(req.data);self.assertEqual(timeout,30);self.assertEqual(len(payload['messages']),2);self.assertNotIn('合成数据',str(payload));return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(draft,ensure_ascii=False)}}]}).encode()
  r=parse_requirements(seg,transport=transport,config=Settings('local-test-key','https://api.deepseek.com','deepseek-flash'),include_tables=True);self.assertEqual(r['draft'],draft)
 def test_web_confirmation_filter_and_invalidations(self):
  s=self.model();s.set_selection([f['key'] for f in s.eligible()]);self.assertTrue(s.generate(),s.error);roles=dict(s.table_types);roles['2']='cover';s.set_table_types(roles);self.assertIsNone(s.report);self.assertIsNone(s.result);self.assertIsNone(s.table_confirmed);self.assertFalse(s.confirm_and_check())
 def test_rules_mode_input_change_cancel_table_confirmation(self):
  s=self.model();s.set_mode('extended');self.assertIsNone(s.table_confirmed);self.assertIsNone(s.report);s.load(GOOD.read_bytes(),'second.docx');self.assertFalse(s.table_enabled)
 def test_next_round_rebind_and_previous_file_unchanged(self):
  s=self.model();raw=s.input_path.read_bytes();s.set_selection([s.eligible()[0]['key']]);self.assertTrue(s.generate(),s.error);first=Path(s.result['output']);bytes_=first.read_bytes();self.assertTrue(s.next_round(),s.error);self.assertEqual(s.table_confirmed['scope']['input_sha256'],s.inventory['input_sha256']);s.set_selection([f['key'] for f in s.eligible()]);self.assertTrue(s.generate(),s.error);self.assertEqual(first.read_bytes(),bytes_);self.assertEqual(s.original_path.read_bytes(),raw)
 def test_project_confirmed_v5_and_table_sources_restore_recheck(self):
  s=self.model();cfg=v5({'table_content__font_cn':'宋体','table_content__font_size':10.5});self.assertTrue(s.import_template(json.dumps(cfg,ensure_ascii=False).encode()),s.template_error);self.assertTrue(s.apply_template(),s.template_error);s.confirm_tables();s.confirm_and_check();s.set_selection([s.eligible()[0]['key']]);s.generate();s.next_round();raw=s.prepare_project();n=WebSession(self.root/'restore');self.assertTrue(n.stage_project(raw));rules,rows=n.project_review();self.assertTrue(any(row['规则'].startswith('R23') and '10.5pt' in row['要求'] for row in rules));self.assertTrue(any(row['编号']=='表格2' and row['类型']=='论文内容表格' for row in rows));restored=n.restore_project(acknowledged=True);self.assertEqual(restored.table_types,s.table_types);self.assertEqual(restored.active_template['field_sources'],s.active_template['field_sources']);self.assertEqual(restored.report['summary'],s.report['summary']);self.assertEqual(restored.current_round,1)
 def test_project_unconfirmed_table_draft_stays_unconfirmed(self):
  s=self.model();roles=dict(s.table_types);roles['3']='pending';s.set_table_types(roles);raw=s.prepare_project();n=WebSession(self.root/'restore');n.stage_project(raw);r=n.restore_project(acknowledged=True);self.assertEqual(r.table_types,roles);self.assertIsNone(r.table_confirmed);self.assertIsNone(r.report)
 def test_double_session_scope_isolation(self):
  a=self.model();b=WebSession(self.root/'b');b.set_mode('academic');b.load(GOOD.read_bytes(),'b.docx');self.assertFalse(b.table_enabled);a.table_types['1']='content';self.assertEqual(b.table_types['1'],'pending')
 def test_results_package_full_scope_and_rules_no_repair_on_download(self):
  s=self.model();s.set_selection([f['key'] for f in s.eligible()]);s.generate();n=s.generation_count;a=s.result_package();self.assertEqual(a,s.result_package());self.assertEqual(n,s.generation_count)
  from io import BytesIO
  with zipfile.ZipFile(BytesIO(a)) as z:self.assertIn('table-rules.json',z.namelist());self.assertIn('table_scope',json.loads(z.read('scope.json')));self.assertIn(b'R23',z.read('recheck.md'))
 def test_front_back_pairs_only_confirmed_exact_successors(self):
  p=ROOT/'samples/academic-correct.docx';m=json.loads(p.with_suffix('.types.json').read_text());pairs=suggest_pagination_aids(p,m)['pairs'];keys={x['key'] for x in pairs if x['status']=='available'};self.assertTrue({'L03:3:4','L03:6:7','L03:18:19'}<=keys)
 def test_mismatching_successor_not_applied(self):
  p=ROOT/'samples/academic-correct.docx';m=json.loads(p.with_suffix('.types.json').read_text());m['paragraph_types']['7']='body';row=next(x for x in suggest_pagination_aids(p,m)['pairs'] if x['key']=='L03:6:7');self.assertEqual(row['status'],'review')
  with self.assertRaises(DemoError):apply_pagination_layout(p,self.root/'fixed.docx',mode='academic',classification_manifest=m,confirmed_keys=['L03:6:7'])
 def test_blank_and_forced_break_not_crossed(self):
  for what in ['blank','break']:
   p=self.root/(what+'.docx');p.write_bytes((ROOT/'samples/academic-correct.docx').read_bytes());pkg=Package(p)
   if what=='blank':pkg.paragraphs[5].addnext(E.Element(q('p')))
   else:_ensure(_ensure(pkg.paragraphs[6],'pPr'),'pageBreakBefore').set(q('val'),'1')
   p.write_bytes(pkg.bytes(True));types={str(i):'other' for i in range(1,len(pkg.root.find(q('body')).findall(q('p')))+1)};types['6']='abstract_en_title';types['8' if what=='blank' else '7']='abstract_en_body';m={'input_sha256':sha256(p.read_bytes()),'paragraph_types':types,'confirmed':True,'confirmation':'test'};row=next(x for x in suggest_pagination_aids(p,m)['pairs'] if x.get('paragraph')==6);self.assertEqual(row['status'],'review')
 def test_adjacency_only_heading_not_whole_abstract_chain(self):
  p=ROOT/'samples/academic-correct.docx';m=json.loads(p.with_suffix('.types.json').read_text());out=apply_pagination_layout(p,self.root/'fixed.docx',mode='academic',classification_manifest=m,confirmed_keys=['L03:6:7']);pkg=Package(out['output']);self.assertEqual(pkg.paragraphs[5].find('w:pPr/w:keepNext',NS).get(q('val')),'1');self.assertIsNone(pkg.paragraphs[6].find('w:pPr/w:keepNext',NS));self.assertEqual(out['before']['findings'],out['after']['findings']);self.assertEqual(out['layout']['visual_status'],'not_reviewed')
 def test_B_actual_hash_rule_file_and_safe_properties_preserved(self):
  p=ROOT/'work/phase15/final-current/browser-custom-B.docx';m=json.loads(p.with_suffix('.types.json').read_text());cfg=ROOT/'work/phase15/final-current/live-edited-B-template.json';before=check_document(p,mode='academic',classification_manifest=m,custom_rules_path=cfg);out=apply_pagination_layout(p,self.root/'B.docx',mode='academic',classification_manifest=m,custom_rules_path=cfg,confirmed_keys=['L03:6:7']);self.assertEqual(before['findings'],out['after']['findings']);self.assertEqual(out['after']['summary']['problem_count'],0);self.assertTrue(out['preservation']['document_except_selected_format_attributes_equal'])
 def test_paragraph_edit_preserves_independent_confirmed_table_scope(self):
  s=self.model();old=deepcopy(s.table_confirmed);s.batch_types([2],'other');self.assertEqual(s.table_confirmed,old)
 def test_table_policy_changed_rejects_old_download(self):
  s=self.model();s.set_selection([s.eligible()[0]['key']]);s.generate();path=self.root/'changed-policy.json';path.write_text('{}')
  with patch('core.table_text.PATH',path),self.assertRaises(DemoError):s.downloads()
  self.assertIsNone(s.result)
 def test_table_conditional_duplicate_and_missing_style_review(self):
  def fn(pkg):
   style=next(x for x in pkg.styles if x.get(q('styleId'))=='DemoConditional');rp=style.find('w:tblStylePr/w:rPr',NS);E.SubElement(rp,q('sz')).set(q('val'),'21')
  r=self.check(self.alter(fn));self.assertTrue(all(f['status']=='review' for f in r['findings'] if f['locator'].get('table')==7))
  for tag in ('pPr','rPr'):
   def repeated(pkg):
    p=tables(pkg)[1].find('w:tr/w:tc/w:p',NS);e=p if tag=='pPr' else p.find(q('r'));_ensure(e,tag);e.append(E.Element(q(tag)))
   report=self.check(self.alter(repeated));self.assertTrue(any('重复' in n['detail'] for n in [*report['findings'],*report['coverage_notes']]))
 def test_table_geometry_from_real_width_adaptation_retained(self):
  from core.widths import check_widths,apply_width_adaptation
  p=self.alter(lambda pkg:pkg.sections[0].find(q('pgMar')).set(q('left'),'2100'));m=self.manifest(p);plan=check_widths(p,rules_sha256=__import__('core',fromlist=['effective_rules']).effective_rules(mode='academic')['sha256'])
  row=next(r for r in plan['objects'] if r['key']=='W01:table=2');self.assertTrue(row['fixable'])
  resized=apply_width_adaptation(p,self.root/'width.docx',None,mode='academic',classification_manifest=m,plan=plan,selected_keys=[row['key']],confirmed_fixed_keys=[row['key']]);after=fix_document(resized['output'],self.root/'text.docx',None,mode='academic',classification_manifest=resized['output_classification_manifest'],selected_rules=['R23'])
  a=Package(resized['output']);b=Package(after['output']);self.assertEqual(E.tostring(tables(a)[1].find(q('tblGrid'))),E.tostring(tables(b)[1].find(q('tblGrid'))));self.assertEqual(E.tostring(tables(a)[1].find(q('tblPr'))),E.tostring(tables(b)[1].find(q('tblPr'))));self.assertEqual(after['output_classification_manifest']['table_scope']['input_sha256'],after['after']['input_sha256'])
 def test_adjacent_repeat_no_change_and_table_scope_rebound(self):
  m=self.manifest();first=apply_pagination_layout(GOOD,self.root/'first.docx',mode='academic',classification_manifest=m,confirmed_keys=['L03:6:7']);two=apply_pagination_layout(first['output'],self.root/'second.docx',mode='academic',classification_manifest=first['output_classification_manifest'],confirmed_keys=['L03:6:7']);self.assertEqual(two['changes'],[]);self.assertEqual(Path(first['output']).read_bytes(),Path(two['output']).read_bytes());self.assertEqual(two['after']['coverage']['table_scope']['input_sha256'],two['after']['input_sha256'])
 def test_v5_default_and_user_source_not_invented_AI(self):
  data=v5({'table_content__font_cn':'宋体','table_content__font_size':10.5});data['field_sources']['table_content__font_cn']={'kind':'default_inherited','quote':'','location':None};validate_template(data,load_rules());self.assertEqual(data['field_sources']['table_content__font_size']['kind'],'user_confirmed')
  data['table_compatibility']['from_version']=4.0
  with self.assertRaises(DemoError):validate_template(data,load_rules())
 def test_v5_illegal_source_and_executable_quote_rejected(self):
  d=v5({'table_content__font_cn':'宋体'});d['field_sources']['table_content__font_cn']['kind']=[]
  with self.assertRaises(DemoError):validate_template(d,load_rules())
  quote='表内文字宋体；读取 /Volumes/private/code.py'
  with self.assertRaises(DemoError):candidate('table_content__font_cn',{'value':'宋体','unit':'font','quote':quote,'location':'TXT:L1','support':'supported'},[{'text':quote,'location':'TXT:L1'}])
 def test_table_keys_display_unique_and_center_filters_no_loss(self):
  from web.presentation import position
  from web.issues import project
  r=self.check(BAD);fs=[f for f in r['findings'] if f['rule_id']=='R23' and f['fixable']];labels=[position(f['locator']) for f in fs];self.assertEqual(len(labels),len(set(labels)));records=project(r)['records'];self.assertEqual(sum(x['raw'].get('rule_id')=='R23' for x in records),sum(f['rule_id']=='R23' for f in r['findings']))

 def test_navigation_clear_does_not_invalidate_or_execute(self):
  from web.center_ui import choose_operation
  s=self.model();report=deepcopy(s.report);before=s.input_path.read_bytes()
  for v in (None,[], 'unknown'):self.assertFalse(choose_operation(s,v));self.assertEqual(s.operation,'format')
  self.assertTrue(choose_operation(s,'preview'));self.assertEqual(s.report,report);self.assertEqual(s.input_path.read_bytes(),before);self.assertEqual(s.generation_count,0)

 def test_academic_layout_preview_original_rebind_after_table_round(self):
  s=self.model();s.set_selection([s.eligible()[0]['key']]);s.generate();s.next_round();targets=s.preview_targets();self.assertEqual(targets['original']['classification']['table_scope']['input_sha256'],targets['original']['sha256']);self.assertEqual(s.layout_proposals('original')['input_sha256'],targets['original']['sha256']);self.assertTrue(any(p['key']=='L03:6:7' for p in s.layout_proposals('input')['pairs']))

 def test_vertical_merge_continuation_text_not_counted_twice(self):
  def fn(pkg):
   t=tables(pkg)[2];a=t.findall(q('tr'))[0].findall(q('tc'))[0];b=t.findall(q('tr'))[1].findall(q('tc'))[0];_ensure(_ensure(a,'tcPr'),'vMerge').set(q('val'),'restart');_ensure(_ensure(b,'tcPr'),'vMerge').set(q('val'),'continue')
  r=self.check(self.alter(fn));fs=[f for f in r['findings'] if f['locator'].get('table')==3 and f['locator'].get('row')==2 and f['locator'].get('cell')==1];self.assertEqual(len(fs),1);self.assertEqual(fs[0]['status'],'review');self.assertFalse(fs[0]['fixable'])

 def test_fixed_table_defaults_cannot_be_changed_as_school_rule(self):
  from core.table_text import load_policy,PATH
  data=json.loads(PATH.read_text());data['font_size']=12
  with self.assertRaises(DemoError):load_policy(json.dumps(data).encode())
 def test_zero_problem_can_explicitly_continue_without_new_output(self):
  s=self.model();s.set_selection([f['key'] for f in s.eligible()]);s.generate();output=Path(s.result['output']);old=output.read_bytes();count=s.generation_count;self.assertTrue(s.next_round());self.assertEqual(s.input_path,output);self.assertEqual(s.generation_count,count);self.assertEqual(output.read_bytes(),old);self.assertEqual(s.report['summary']['problem_count'],0)

 def test_table_history_continue_uses_saved_academic_scope(self):
  s=self.model();s.set_selection([s.eligible()[0]['key']]);s.generate();identity=s.history[0]['stem'];s.set_table_enabled(False);self.assertTrue(s.continue_history(identity,acknowledged=True));self.assertEqual(s.mode,'academic');self.assertTrue(s.table_enabled);self.assertEqual(s.report['summary']['rule_count'],23);self.assertEqual(s.report['summary']['problem_count'],4)

 def test_table_confirmation_ui_projection_old_template_not_default_pass(self):
  s=self.model();self.assertEqual(s.table_requirements(),{'font_cn':'宋体','font_size':10.5});s.import_template(json.dumps(v4_template(),ensure_ascii=False).encode());s.apply_template();self.assertEqual(s.table_requirements(),{'font_cn':None,'font_size':None});s.import_template(json.dumps(v5({'table_content__font_cn':'楷体','table_content__font_size':11.5}),ensure_ascii=False).encode());s.apply_template();self.assertEqual(s.table_requirements(),{'font_cn':'楷体','font_size':11.5})

from pathlib import Path
from copy import deepcopy
from tempfile import TemporaryDirectory
from unittest import TestCase
import json,zipfile
from lxml import etree as E
from core.package import Package,DemoError,q,NS
from core import rule_bundle as rb
from core.paragraph_values import line,indent,twips,line_xml,read_line,line_equal,apply,mask
from core.formats import Resolver
from web.session import WebSession
from web.onepass_session import start
from ai.semantic_spec import request_for,adapt,parse_requirements
from ai.short_spec import Settings
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'samples/phase47';TEXT=(S/'requirements.txt').read_text().strip();EXPECTED=json.loads((S/'expected.json').read_text())['fields']
def response(text=TEXT):
 r=request_for(text)
 return {'version':r['version'],'items':[{'field':fid,'value':EXPECTED[f['name']],'source':next(s['id'] for s in r['sources'] if {'abstract_cn_body__line_spacing':'中文摘要正文','reference_item__line_spacing':'参考文献','reference_item__first_line_indent':'参考文献','footnote__line_multiple':'脚注','heading1_line_spacing':'一级标题','heading1__before':'一级标题','heading1__after':'一级标题','figure_caption__alignment':'图题','figure_caption__before':'图题'}.get(f['name'],'正文') in s['text'])} for fid,f in r['fields'].items()],'issues':[]}
def parser(t):return parse_requirements(t,config=Settings('synthetic'),transport=lambda *_:json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(response(t),ensure_ascii=False)}}]}))
def model(path):
 s=WebSession(path);s.set_mode('academic');s.load((S/'errors.docx').read_bytes(),'合成段落.docx');s.set_types(json.loads((S/'roles.json').read_text()));s.confirm_classification();return s
class ParagraphModes(TestCase):
 def test_units_precision_and_no_type_coercion(self):
  self.assertEqual(line_xml(1.15),{'line':'276','lineRule':'auto'});self.assertEqual(twips({'value':.74,'unit':'cm'}),420)
  for v in (True,'20',{'mode':'exact','value':20.03},{'mode':'atLeast','value':20},0,121):
   with self.assertRaises(DemoError):line(v)
  with self.assertRaises(DemoError):indent({'kind':'hanging','unit':'chars','value':2})
 def test_exact_full_source_proof_and_missing_modes(self):
  d=adapt(response(),TEXT);self.assertEqual({n:f['value'] for n,f in d['fields'].items()},EXPECTED)
  for t in ('正文行距20磅','全文固定20磅','正文固定20磅行距；正文最小20磅行距'):
   with self.assertRaises(DemoError):adapt(response() if t==TEXT else {'version':request_for(TEXT)['version'],'items':[],'issues':[]},t)
 def test_real_engines_combined_and_repeat_is_stable(self):
  with TemporaryDirectory() as d:
   s=model(Path(d)/'a');before=s.input_path.read_bytes();state={};start(s,state,TEXT,spec_parser=parser,structure_runner=lambda *_:self.fail('confirmed scope must not request AI'))
   self.assertEqual(state['status'],'done',state.get('error'));self.assertEqual(s.input_path.read_bytes(),before)
   out=Path(d)/'fixed.docx';out.write_bytes(s.downloads()['fixed.docx']);p=Package(out);ps=p.paragraphs
   self.assertEqual(ps[1].find('w:pPr/w:spacing',NS).get(q('lineRule')),'exact');self.assertEqual(ps[1].find('w:pPr/w:ind',NS).get(q('firstLine')),'420')
   self.assertEqual(ps[9].find('w:pPr/w:ind',NS).get(q('hangingChars')),'200')
   self.assertEqual(ps[9].find('w:pPr/w:spacing',NS).get(q('lineRule')),'atLeast')
   self.assertEqual([E.tostring(r) for r in Package(S/'errors.docx').paragraphs[12].iter(q('r'))],[E.tostring(r) for r in ps[12].iter(q('r'))])
   bundle=s.rule_bundle_download();t=model(Path(d)/'b');t.import_rule_bundle(bundle);t.apply_workbench(acknowledged=True);self.assertEqual(rb.flat('main',s.current_rule_bundle()['modules']['main']),rb.flat('main',t.current_rule_bundle()['modules']['main']))
   self.assertTrue(s.next_round());self.assertTrue(s.confirm_and_check(),s.error)
   self.assertFalse([f for f in s.eligible() if f['rule_id'] in ('R06','R07')])
 def test_single_property_mask_preserves_other_attributes(self):
  p=E.fromstring('<w:p xmlns:w="'+NS['w']+'"><w:pPr><w:spacing w:line="360" w:lineRule="auto" w:before="120" w:after="80"/><w:ind w:left="140" w:firstLineChars="200"/></w:pPr><w:r><w:t>文本</w:t></w:r></w:p>');old=deepcopy(p)
  apply(p,'line_spacing',{'mode':'minimum','value':20});self.assertEqual(p.find('w:pPr/w:spacing',NS).get(q('before')),'120');mask(old,'line_spacing');mask(p,'line_spacing');self.assertEqual(E.tostring(old),E.tostring(p))
 def test_all_object_mounts_native_rule_reuse_recovery_and_run_preservation(self):
  with TemporaryDirectory() as d:
   s=model(Path(d)/'matrix');s.start_workbench_draft();s.workbench_policy('keep',acknowledged=True)
   changes={'figure_caption__line_spacing':{'mode':'exact','value':22},'table_caption__line_spacing':{'mode':'minimum','value':20},'heading2_line_spacing':1.15,'heading3_line_spacing':1.2,'abstract_en_body__line_spacing':{'mode':'exact','value':20},'abstract_cn_body__first_line_indent':{'kind':'first','unit':'mm','value':7.4},'reference_item__first_line_indent':{'kind':'hanging','unit':'pt','value':18},'appendix_text__line_spacing':1.75,'ack_text__line_spacing':{'mode':'minimum','value':20},'keywords_cn__line_spacing':1.15,'reference_item__before':{'value':.5,'unit':'lines'}}
   for n,v in changes.items():s.workbench_edit('main',n,'manual',v)
   for k in ('footnote','endnote'):
    for p,v in {'line_multiple':{'mode':'exact','value':14},'before':{'value':6,'unit':'pt'},'after':{'value':.5,'unit':'lines'},'alignment':'right'}.items():s.workbench_edit('notes',k+'__'+p,'manual',v)
   s.apply_workbench(acknowledged=True);s.set_types(json.loads((S/'roles.json').read_text()));s.enable_notes(True);note=deepcopy(s.note_draft);note['objects']=[r['key'] for r in s.note_inventory()['objects']];s.edit_notes(note);s.confirm_notes();self.assertTrue(s.confirm_and_check(),s.error)
   self.assertEqual(s.current_rule_bundle()['modules']['main']['template']['structure_version'],7)
   wanted=[f for f in s.eligible() if f['rule_id'] in ('R06','R07') or f['locator'].get('property') in ('line','line_spacing','line_multiple','before','after','alignment','first_line_indent')]
   self.assertTrue(any(f.get('object_type')=='footnote' for f in wanted));s.set_selection([f['key'] for f in wanted]);self.assertTrue(s.generate(),s.error)
   raw=s.downloads()['fixed.docx'];p=Package(s.input_path);out=Package(s.result['output'])
   for part in ('word/document.xml','word/footnotes.xml','word/endnotes.xml'):
    x,y=E.fromstring(p.parts[part]),E.fromstring(out.parts[part]);self.assertEqual([E.tostring(r) for r in x.iter(q('r'))],[E.tostring(r) for r in y.iter(q('r'))])
   self.assertEqual(out.paragraphs[4].find('w:pPr/w:spacing',NS).get(q('lineRule')),'exact');self.assertEqual(out.paragraphs[2].find('w:pPr/w:spacing',NS).get(q('line')),'276')
   self.assertEqual(out.paragraphs[9].find('w:pPr/w:ind',NS).get(q('hanging')),'360')
   for part in p.parts:
    if part not in ('word/document.xml','word/footnotes.xml','word/endnotes.xml'):self.assertEqual(p.parts[part],out.parts[part])
   bundle=s.rule_bundle_download();t=model(Path(d)/'reuse');t.import_rule_bundle(bundle);t.apply_workbench(acknowledged=True);self.assertEqual(t.current_rule_bundle()['modules'],s.current_rule_bundle()['modules'])
   saved=s.prepare_project();t.stage_project(saved);restored=t.restore_project(acknowledged=True);self.assertEqual(restored.current_rule_bundle()['modules'],s.current_rule_bundle()['modules']);self.assertEqual(restored.note_draft['template']['structure_version'],2)
 def test_shared_inheritance_complex_guards_and_conflict_isolation(self):
  from core.paragraph_values import read_indent
  from core.paragraph_conflicts import isolate
  from core.formats import Unresolved
  pkg=Package(S/'errors.docx');r=Resolver(pkg);p=deepcopy(pkg.paragraphs[1]);pp=p.find(q('pPr'));sp=pp.find(q('spacing'));sp.set(q('lineRule'),'atLeast');sp.set(q('line'),'400')
  self.assertTrue(line_equal(read_line(r,r.layers(p,kind='pPr')),{'mode':'minimum','value':20}));self.assertFalse(line_equal(read_line(r,r.layers(p,kind='pPr')),{'mode':'exact','value':20}))
  pp.append(deepcopy(sp))
  with self.assertRaises(Unresolved):read_line(r,r.layers(p,kind='pPr'))
  fs=[{'rule_id':rid,'locator':{'paragraph':1,'property':prop},'expected':v,'status':'problem','fixable':True} for rid,prop,v in [('R06','line',1.5),('R13','line_spacing',{'mode':'exact','value':20})]]
  report={'findings':fs,'summary':{},'coverage_notes':[]};isolate(report);self.assertTrue(all(f['status']=='review' and not f['fixable'] for f in fs))
 def test_file_native_positions_and_whole_input_conflicts(self):
  from core.norms import extract_norm
  from ai.file_spec import request_for as file_request,adapt as file_adapt
  e=extract_norm((TEXT+'\n').encode(),'txt');r=file_request(e);byname={n:f for f,n in [(f,v['name']) for f,v in r['fields'].items()]}
  d={'version':r['version'],'items':[{'field':byname[n],'value':v,'source':next(x['id'] for x in r['sources'] if x['text'] in TEXT and any(f['name']==n for f in request_for(x['text'])['fields'].values()))} for n,v in EXPECTED.items()],'background':[],'issues':[]}
  result=file_adapt(d,e);self.assertFalse(result['notices']);self.assertEqual({n:f['value'] for n,f in result['draft']['fields'].items()},EXPECTED);self.assertEqual({f['location'] for f in result['draft']['fields'].values()},{'TXT:L1'})
 def test_dynamic_followup_uses_existing_explicit_preview_and_adoption(self):
  from scripts.build_smart_dynamic_fixture import build
  from web.dynamic_session import preview,adopt
  from web.onepass_session import current,register_dynamic_followup
  from unittest.mock import patch
  with TemporaryDirectory() as d:
   source,m=build(Path(d)/'dynamic');s=WebSession(Path(d)/'session');s.set_mode('academic');s.load(source.read_bytes(),'动态合成.docx');s.set_table_enabled(False);s.set_types(m['paragraph_types']);s.confirm_classification();state={}
   start(s,state,structure_runner=lambda *_:self.fail('human scope is authoritative'));self.assertEqual(state['status'],'done',state.get('error'))
   old=state['post'];parent=s.result['after']['input_sha256'] if s.result else s.inventory['input_sha256'];count=s.generation_count;original=s.input_path.read_bytes();dyn={}
   with self.assertRaises(DemoError):preview(s,dyn,complete=False)
   preview(s,dyn,complete=True);self.assertEqual(s.generation_count,count);self.assertEqual(s.input_path.read_bytes(),original)
   adopt(s,dyn);self.assertFalse(current(s,state,''));register_dynamic_followup(s,state,old,parent)
   self.assertTrue(current(s,state,''));self.assertEqual(s.generation_count,count+1);self.assertEqual(s.input_path.read_bytes(),original);self.assertEqual(state['audit']['dynamic_followup']['numeric_changes'],5)
   with patch('core.dynamic.rehearse',side_effect=AssertionError('no second execution')):adopt(s,dyn)
   self.assertEqual(s.generation_count,count+1)
   with self.assertRaises(DemoError):register_dynamic_followup(s,state,old,'0'*64)
 def test_note_overlay_never_seeds_unmentioned_school_values(self):
  from web.onepass_session import overlay
  with TemporaryDirectory() as d:
   s=model(Path(d)/'no-notes');before=s.current_rule_bundle();self.assertIsNone(before['modules']['notes'])
   result=parser(TEXT);overlay(s,TEXT,result);after=s.current_rule_bundle()
   for n,v in rb.flat('notes',after['modules']['notes']).items():
    if n=='footnote__line_multiple':self.assertEqual(v,{'mode':'exact','value':12})
    else:self.assertIsNone(v);self.assertEqual(after['provenance']['notes'][n],rb.EMPTY)
   self.assertEqual(before['modules']['front'],after['modules']['front']);self.assertEqual(before['modules']['toc'],after['modules']['toc'])
 def test_new_physical_indent_keeps_grid_guard_and_fixed_font_is_not_line(self):
  from ai.smart_spec import coverage
  from web.onepass_session import overlay
  from core import check_document
  from core.paragraph_values import prove
  with self.assertRaises(DemoError):coverage('正文字号固定20磅')
  with self.assertRaises(DemoError):prove('line_spacing',{'mode':'exact','value':20},'正文字号固定20磅',['正文字号固定20磅'])
  with TemporaryDirectory() as d:
   source=Package(S/'errors.docx');sec=source.sections[0];grid=sec.find(q('docGrid'))
   if grid is None:grid=E.SubElement(sec,q('docGrid'))
   grid.set(q('type'),'lines');grid.set(q('linePitch'),'360');path=Path(d)/'grid.docx';path.write_bytes(source.bytes(True))
   s=WebSession(Path(d)/'session');s.set_mode('academic');s.load(path.read_bytes(),'网格合成.docx');overlay(s,TEXT,parser(TEXT));s.set_types(json.loads((S/'roles.json').read_text()));self.assertTrue(s.confirm_and_check(),s.error)
   for rid in ('R06','R07'):
    f=next(f for f in s.report['findings'] if f['rule_id']==rid and f['locator'].get('paragraph')==2);self.assertEqual(f['status'],'review');self.assertFalse(f['fixable'])

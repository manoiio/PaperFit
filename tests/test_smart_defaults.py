"""Actual output, explicit null/old intent and isolated original confirmations."""
from unittest import TestCase
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from copy import deepcopy
import json
from core.package import Package,q,NS,DemoError
from core import load_rules,rule_bundle as rb
from web.session import WebSession
from web.page_ui import smart_seed
from web.onepass_session import start,current
from web.smart_defaults import prepare_rules,prepare_scopes,QUOTE
ROOT=Path(__file__).resolve().parents[1]
class SmartDefaultsTests(TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def session(self,name='s',old=False):
  s=WebSession(self.root/name);s.set_mode('academic');s.load((ROOT/'samples/phase56/source.docx').read_bytes(),'公开合成.docx')
  seed=smart_seed(s);seed['enabled']=False;seed['explicit']=True;seed['word_updates']=False
  if old:seed.pop('smart_defaults',None)
  s.page_layout_draft={**seed,'input_sha256':s.inventory['input_sha256'],'regions':[]};return s
 def run_command(self,s):
  state={}
  with patch('ai.structure.http_post',side_effect=AssertionError('No paid API')):
   start(s,state,structure_runner=lambda *_:(_ for _ in ()).throw(DemoError('受控离线无API')))
  self.assertEqual(state['status'],'done',state.get('error') or state.get('questions'));return state
 def test_actual_captions_correct_and_protected_structure_and_offset_warning(self):
  s=self.session();before=Package(s.input_path);state=self.run_command(s);after=Package(s.result['output']);exp=json.loads((ROOT/'samples/phase56/expected.json').read_text())
  for n in exp['captions']:self.assertEqual(after.paragraphs[int(n)-1].find('w:pPr/w:jc',NS).get(q('val')),'center')
  from lxml import etree as E
  self.assertEqual(E.tostring(before.paragraphs[7]),E.tostring(after.paragraphs[7]))
  self.assertEqual(before.paragraphs[4].find('w:pPr/w:ind',NS).attrib,after.paragraphs[4].find('w:pPr/w:ind',NS).attrib)
  self.assertTrue(any('视觉中心' in n['detail'] for n in s.result['after']['coverage_notes']))
  self.assertTrue(any(f['rule_id']=='R44' and f['status']=='problem' and not f['fixable'] for f in s.result['after']['findings']))
  self.assertIn('R13',state['audit']['coverage']['executed_rules']);self.assertEqual(s.current_round,0)
  counts=s.generation_count;data=s.downloads()['fixed.docx'];start(s,state);self.assertEqual(s.generation_count,counts);self.assertEqual(data,s.downloads()['fixed.docx'])
 def test_untouched_sources_implicit_notes_and_only_format_limits(self):
  s=self.session();before=s.current_rule_bundle();prepare_rules(s);after=s.current_rule_bundle();a=rb.flat('main',before['modules']['main']);b=rb.flat('main',after['modules']['main'])
  for n in a:
   if n in ('figure_caption__alignment','table_caption__alignment'):continue
   self.assertEqual(a[n],b[n],n);self.assertEqual(before['provenance']['main'][n],after['provenance']['main'][n],n)
  from core.notes import make_scope
  self.assertTrue(any(v is not None for ps in s.seed_workbench_module('notes',make_scope(Package(s.input_path)))['template']['values'].values() for v in ps.values()))
  state=self.run_command(s);self.assertNotIn('assembly',s.result);self.assertNotIn('field_update',state['audit']);self.assertTrue(all(h['result'].get('kind','format')=='format' for h in s.history))
 def test_saved_rules_explicit_left_disabled_and_new_session_reuse(self):
  s=self.session();prepare_rules(s);s.start_workbench_draft();s.workbench_policy('keep',acknowledged=True);s.workbench_edit('main','figure_caption__alignment','manual','left');s.workbench_edit('main','table_caption__alignment','disabled');s.apply_workbench(acknowledged=True);expected=s.current_rule_bundle();st=self.run_command(s)
  self.assertEqual(s.current_rule_bundle()['provenance'],expected['provenance']);p=Package(s.result['output']);self.assertEqual(p.paragraphs[2].find('w:pPr/w:jc',NS).get(q('val')),'left');self.assertEqual(p.paragraphs[6].find('w:pPr/w:jc',NS).get(q('val')),'left')
  other=self.session('other');other.import_rule_bundle(s.rule_bundle_download());other.apply_workbench(acknowledged=True);self.assertEqual(prepare_rules(other)['applied'],[]);self.assertEqual(rb.flat('main',other.current_rule_bundle()['modules']['main'])['table_caption__alignment'],None)
 def test_product_sources_roundtrip_project_restore_no_old_grant_or_shared_state(self):
  s=self.session();state=self.run_command(s);raw=s.prepare_project();other=WebSession(self.root/'restored');other.stage_project(raw);other=other.restore_project(acknowledged=True)
  self.assertEqual(rb.flat('main',other.current_rule_bundle()['modules']['main'])['figure_caption__alignment'],'center');self.assertEqual(other.current_rule_bundle()['provenance']['main']['figure_caption__alignment']['quote'],QUOTE);self.assertIsNone(other.rehearsal)
  old=self.session('old',True);self.run_command(old);self.assertFalse(old.reference_enabled);self.assertIsNone(rb.flat('main',old.current_rule_bundle()['modules']['main'])['figure_caption__alignment'])
 def test_existing_closed_scopes_and_materials_are_not_automatic(self):
  s=self.session();s.enable_references(True);s.enable_references(False);s.enable_captions(True);s.enable_captions(False);s.exclude_materials([7],'人工材料保护');self.run_command(s);self.assertFalse(s.reference_enabled);self.assertFalse(s.caption_enabled);self.assertEqual(s.material_exclusions['7'],'人工材料保护')
 def test_rules_change_invalidates_command_and_default_source_is_not_school(self):
  s=self.session();state=self.run_command(s);self.assertTrue(current(s,state,''));self.assertTrue(any(f.get('source',{}).get('label','').startswith('PaperFit项目默认') for f in s.result['after']['findings'] if f.get('property')=='alignment'))
  s.page_layout_draft['smart_defaults']=0;self.assertFalse(current(s,state,''))

 def test_complete_safe_table_outer_edges_are_selected_but_internal_lines_preserved(self):
  s=self.session();s.page_layout_draft['enabled']=True;s.page_layout_draft['policy']['pages']='keep';s.page_layout_draft['policy']['dynamic']=False
  st=self.run_command(s);self.assertTrue(any(c['rule_id']=='R35' for h in s.history for c in h['result']['changes']))
  a=Package(s.input_path);b=Package(s.result['output'])
  for t in b.root.findall('.//'+q('tbl')):
   for side in ('left','right'):self.assertEqual(t.find('w:tblPr/w:tblBorders/w:'+side,NS).get(q('val')),'nil')
   for side in ('top','bottom','insideH','insideV'):self.assertEqual(t.find('w:tblPr/w:tblBorders/w:'+side,NS).get(q('val')),'single')
  self.assertTrue(st['audit']['coverage']['areas']);self.assertEqual(a.parts['word/styles.xml'],b.parts['word/styles.xml'])
  # Both caption source overrides must not drop an unrelated complete-plan
  # decision. Imported old rules without a current grant remain conservative.
  other=self.session('overridden');other.page_layout_draft['enabled']=True;grant=prepare_rules(other)
  other.start_workbench_draft();other.workbench_policy('keep',acknowledged=True)
  for n in ('figure_caption__alignment','table_caption__alignment'):other.workbench_edit('main',n,'manual','left')
  other.apply_workbench(acknowledged=True)
  self.assertFalse(any(v.get('quote')==QUOTE for v in other.current_rule_bundle()['provenance']['main'].values()))
  from web.smart_session import suggest
  from web.structure_session import prepare
  from web.auto_ranges import apply
  proposal=suggest(other);apply(other,proposal,prepare(other,include_tables=True));prepare_scopes(other,proposal,defaults_applied=bool(grant['applied']))
  self.assertTrue(proposal['draft']['table_layout_options']['outer_edges'])
  other.table_layout_options={'version':1,'outer_edges':False,'headers':{}}
  proposal=suggest(other);apply(other,proposal,prepare(other,include_tables=True));prepare_scopes(other,proposal,defaults_applied=True)
  self.assertNotIn('table_layout_options',proposal['draft'])

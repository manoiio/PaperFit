"""New command adapter tests, never native Word/AI in the offline suite."""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest.mock import patch
import unittest,json,time
from core.package import Package,q,NS,DemoError
from core.page_policy import DEFAULT,validate,merge,extract
from web.session import WebSession
from web import auxiliary_session as aux
ROOT=Path(__file__).resolve().parents[1]
POLICY={**DEFAULT,'version':3,'targets':['cover','front','body'],'auxiliaries':'safe-layout-v1','pages':'front-body','footer':'chapter','dynamic':True}

class LayoutAssemblyTests(unittest.TestCase):
 def setUp(self):self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
 def model(self,name='one'):
  s=WebSession(self.root/name);s.set_mode('academic');s.load((ROOT/'samples/phase51/source.docx').read_bytes(),'公开合成.docx');s.page_layout_draft={'explicit':True,'enabled':True,'policy':deepcopy(POLICY),'input_sha256':s.inventory['input_sha256'],'regions':[]};return s
 def start(self,s):
  from web.onepass_session import start
  state={};start(s,state,'',structure_runner=lambda *a:self.fail('fixture has no AI candidates'));self.assertEqual(state['status'],'done',state.get('error'));return state
 def test_new_policy_is_explicit_and_merge_preserves_grant(self):
  self.assertFalse(aux.enabled(DEFAULT));self.assertTrue(aux.enabled(validate(POLICY)))
  p,_,e=extract('正文从5开始，后面每章连续');self.assertTrue(aux.enabled(merge(POLICY,p,e)))
  from web.assembly_session import regions_from
  partial={**POLICY,'targets':['front']};s=self.model('partial')
  regions=regions_from(s,json.loads((ROOT/'samples/phase51/roles.json').read_text()),partial)
  self.assertEqual([r['role'] for r in regions],['keep','front','keep'])
  bad=deepcopy(POLICY);bad['auxiliaries']='anything'
  with self.assertRaises(DemoError):validate(bad)
 def test_real_chain_remaps_then_uses_final_sections_and_skips_satisfied(self):
  s=self.model();state=self.start(s);steps=state['audit']['assembly_steps'];self.assertEqual([r['kind'] for r in steps],['format','caption_position','section_pages','width_adaptation','pagination_layout'])
  for a,b in zip(steps,steps[1:]):self.assertEqual(a['output_sha256'],b['input_sha256'])
  self.assertEqual(s.current_round,0);self.assertEqual(len(s.history),5)
  width=s.history[3]['result'];self.assertEqual(width['widths']['selected_keys'],['W02:paragraph=10','W01:table=2']);self.assertTrue(all(r['status']=='pass' for r in width['widths']['after']['objects'] if r['key'] in width['widths']['selected_keys']))
  pagination=state['audit']['auxiliaries'][-1];self.assertTrue(any(o['key']=='L04:2:1' and o['status']=='satisfied' for o in pagination['objects']))
  self.assertFalse(any(c['rule_id']=='L04' for c in s.history[-1]['result']['changes']))
  self.assertEqual(s.history[1]['result']['range_mapping']['paragraphs']['10'],'11')
  self.assertFalse(s.result['output_classification_manifest']['caption_scope']['complete'])
  from web.onepass_session import start
  start(s,state,'');self.assertEqual(len(s.history),5)
  raw=s.prepare_project();restored=WebSession(self.root/'restored');restored.stage_project(raw);restored=restored.restore_project(acknowledged=True);self.assertEqual(len(restored.history),5);self.assertIsNone(restored.result);self.assertEqual(restored.current_rule_bundle()['assembly'],POLICY)
 def test_explicit_body_only_does_not_expand_to_layout_or_word(self):
  from web.onepass_session import start
  s=self.model();s.field_updates_enabled=True;state={}
  with patch.object(aux,'execute',side_effect=AssertionError('narrowed command cannot run auxiliaries')),patch('web.field_session.submit',side_effect=AssertionError('narrowed command cannot update fields')):
   start(s,state,'保留现在的页码，只统一正文格式')
  self.assertEqual(state['status'],'done',state.get('error'));self.assertEqual(len(s.history),1);self.assertTrue(all(c['rule_id'] in ('R03','R04','R05','R06','R07','R13') for c in s.result['changes']));self.assertEqual(Package(s.result['output']).root.find(q('body')).findall(q('tbl'))[1].find('w:tblGrid/w:gridCol',NS).get(q('w')),'4989')
 def test_legacy_policy_never_calls_new_adapter(self):
  s=self.model();s.page_layout_draft['policy']={**DEFAULT,'pages':'front-body','footer':'chapter'}
  with patch.object(aux,'execute',side_effect=AssertionError('old authorization cannot enable auxiliaries')):self.start(s)
  self.assertFalse(any(h['result'].get('kind') in ('caption_position','width_adaptation','pagination_layout') for h in s.history))
 def confirmed(self):
  s=self.model();s.set_types(json.loads((ROOT/'samples/phase51/roles.json').read_text()));s.set_table_enabled(True);s.set_table_types({'1':'cover','2':'content','3':'pending'});s.confirm_tables();s.confirm_classification();s.confirm();self.assertTrue(s.check());return s
 def test_unknown_autofit_and_manual_exclusion_are_not_promoted(self):
  s=self.confirmed();ctx=__import__('web.dynamic_session',fromlist=['context']).context(s)[0];m,_,keys,rows=aux.inventory(ctx,'width');self.assertEqual(keys,[]) # reverse image is not yet associated correctly
  p=Package(ctx['input']);[sp.find(q('pgMar')).set(q(k),'1417') for sp in p.sections for k in ('left','right')];p.root.find(q('body')).findall(q('tbl'))[1].find('w:tblPr/w:tblLayout',NS).set(q('type'),'autofit');path=self.root/'autofit.docx';path.write_bytes(p.bytes(True));ctx['input']=str(path);ctx['classification']['input_sha256']=Package(path).hash;__import__('core.table_text',fromlist=['rebind']).rebind(ctx['classification'],Package(path).hash)
  _,_,keys,rows=aux.inventory(ctx,'width');self.assertFalse(keys);self.assertTrue(any('另行明确授权' in r['reason'] for r in rows))
  m=aux.classification(ctx);m['caption_scope']['template']['position']=False;ctx['classification']=m
  self.assertFalse(aux.inventory(ctx,'position')[2])
  ctx['current_scope']['caption_draft']=deepcopy(m['caption_scope']);ctx['classification'].pop('caption_scope');self.assertFalse(aux.inventory(ctx,'position')[2])
 def test_explicit_header_uses_original_helper_and_preserves_other_rows(self):
  s=self.confirmed();s.set_table_layout_options({'version':1,'outer_edges':False,'headers':{'2':2}});s.confirm_tables();s.confirm_classification();s.confirm();s.check()
  st={};r=aux.rehearse(s,st,'pagination');self.assertTrue(any(c['rule_id']=='L04' for c in r['changes']));p=Package(r['output']);table=p.root.find(q('body')).findall(q('tbl'))[1];self.assertEqual([len(row.findall('w:trPr/w:tblHeader',NS)) for row in table.findall(q('tr'))][:3],[1,1,0]);aux.adopt(s,st);self.assertEqual(s.generation_count,1);aux.adopt(s,st);self.assertEqual(s.generation_count,1)
 def test_failed_archive_or_tampered_output_never_publishes(self):
  s=self.confirmed();st={};aux.rehearse(s,st,'position')
  with patch.object(WebSession,'_archive_round',side_effect=OSError('full')):
   with self.assertRaises(OSError):aux.adopt(s,st)
  self.assertEqual(s.generation_count,0);self.assertFalse(s.history)
  Path(st['result']['output']).write_bytes(b'changed')
  with self.assertRaises(DemoError):aux.adopt(s,st)
  self.assertFalse(s.history)
 def test_later_integrity_fault_does_not_publish_early_rounds(self):
  s=self.model();from web.onepass_session import start
  original=aux.execute
  def broken(model,state,kind,emit):
   if kind=='width':raise DemoError('injected preservation failure')
   return original(model,state,kind,emit)
  state={}
  with patch.object(aux,'execute',side_effect=broken):start(s,state,'')
  self.assertEqual(state['status'],'failed');self.assertIsNone(s.result);self.assertFalse(s.history);self.assertEqual(s.generation_count,0)
 def test_entire_word_stage_receives_final_auxiliary_parent(self):
  from core import word_fields as wf
  from web.onepass_session import start,poll_fields
  calls=[]
  def calculator(raw,codes,targets,update=True):
   pth=self.root/'calculator.docx';pth.write_bytes(raw);p=Package(pth);calls.append(raw)
   for f in p.root.iter(q('fldSimple')):
    code=f.get(q('instr'),'').split()
    if code and code[0]=='PAGEREF' and update:
     for t in f.xpath('.//w:t',namespaces=NS):t.text='3'
   return {'raw':p.bytes(True),'pages':{n:{'adjusted':3,'physical':3} for n in targets},'seconds':0,'backend':'controlled'}
  s=self.model();s.field_updates_enabled=True;state={}
  with patch('core.word_native.calculate',side_effect=calculator):
   start(s,state,'');self.assertEqual(state['status'],'updating',state.get('error'));self.assertIsNone(s.result)
   for _ in range(300):
    poll_fields(s,state)
    if state['status']!='updating':break
    time.sleep(.02)
  self.assertEqual(state['status'],'done');self.assertEqual(state['audit']['field_update']['status'],'updated',state['audit']['field_update']);self.assertEqual(state['audit']['assembly_steps'][-1]['kind'],'field_update');self.assertEqual(len(s.history),6);self.assertEqual(len(s.result['assembly']['steps']),6);self.assertEqual(s.result['assembly']['total_changes'],223)
  # The identical source now resolves Japanese and ASCII/HAnsi theme slots.
  # Old resolver replay gives 129; all 94 additions are proven font slots,
  # including 74 table runs. No new layout/dynamic authorisation was added.
  fonts=[c for c in s.history[0]['result']['changes'] if c['rule_id'] in ('R03','R04') or c.get('locator',{}).get('property') in ('font_cn','font_ascii','font_hAnsi','font_eastAsia')]
  self.assertEqual(len(fonts),94)
  self.assertEqual(sum(c['rule_id']=='R23' and c['locator']['property']=='font_cn' for c in fonts),74)
  p=Package(s.history[4]['result']['output']);self.assertTrue(p.paragraphs[9].find('w:pPr/w:keepNext',NS) is not None);self.assertTrue(calls)

"""Focused reference geometry and one explicit target set; no Word/HTTP."""
import json,unittest
from pathlib import Path
from copy import deepcopy
from tempfile import TemporaryDirectory
from lxml import etree as E
from core.package import Package,q,NS,DemoError
from core import word_fields as wf
from core.toc_targets import DEFAULT,select,tc,owned_tc
from core.toc_appearance import prepare
ROOT=Path(__file__).resolve().parents[1]
class TocPolicyTests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.src=ROOT/'samples/phase57/source.docx';self.pkg=Package(self.src)
  self.m={'input_sha256':self.pkg.hash,'paragraph_types':json.loads((ROOT/'samples/phase57/roles.json').read_text()),'confirmed':True,'confirmation':'independent author roles'}
 def test_reference_geometry_overrides_old_direct_and_inheritance(self):
  f=wf.fields(self.pkg)[0][0];pr=E.Element(q('pPr'));E.SubElement(pr,q('pStyle')).set(q('val'),'Normal');sp=E.SubElement(pr,q('spacing'));sp.set(q('line'),'240');sp.set(q('beforeLines'),'100');ind=E.SubElement(pr,q('ind'));ind.set(q('left'),'60')
  out,rec=prepare(self.pkg,f,{1:pr,2:pr,3:pr},[1,2,3],'reference')
  for level,p in out.items():
   self.assertEqual(p.find(q('ind')).get(q('left')),str((level-1)*480));self.assertEqual(p.find(q('ind')).get(q('firstLine')),'0');self.assertEqual(p.find(q('spacing')).get(q('lineRule')),'exact');self.assertEqual(p.find(q('spacing')).get(q('line')),'474');self.assertEqual(p.find(q('spacing')).get(q('beforeLines')),'0');self.assertEqual(p.find(q('spacing')).get(q('after')),'0');self.assertEqual(p.find('w:tabs/w:tab[@w:val="right"]',NS).get(q('leader')),'dot')
  self.assertIn('非SCUT',rec['source'])
 def test_shared_target_set_abstract_roles_self_exclusion_depth_and_dedup(self):
  f=wf.fields(self.pkg)[0][0];rows,notes=select(self.pkg,self.m,DEFAULT,f,wf.paragraph_level)
  self.assertEqual([r['paragraph'] for r in rows],[1,3,5,8,10,12,14]);self.assertFalse(notes);self.assertEqual(self.m['paragraph_types']['1'],'abstract_cn_title')
  policy={**DEFAULT,'depth':2,'self':False};rows,_=select(self.pkg,self.m,policy,f,wf.paragraph_level);self.assertEqual([r['paragraph'] for r in rows],[1,3,8,10,14]);self.assertEqual(len(rows),len({r['paragraph'] for r in rows}))
 def mock(self,raw,codes,targets,update=True):
  path=self.root/'calculator.docx';path.write_bytes(raw);pkg=Package(path)
  pnums={1:(1,1),3:(2,2),5:(3,3),8:(5,4),10:(5,4),12:(5,4),14:(5,4)}
  pages={anchor:{'adjusted':pnums[int(anchor.rsplit('_',1)[1])][0],'physical':pnums[int(anchor.rsplit('_',1)[1])][1]} for anchor in targets}
  if update:
   for f in pkg.root.iter(q('fldSimple')):
    code=f.get(q('instr'),'')
    if code.strip().startswith('PAGEREF '):
     anchor=code.split()[1];n=int(anchor.rsplit('_',1)[1]);f.find('w:r/w:t',NS).text={1:'i',3:'ii',5:'iii'}.get(n,'5')
  return {'raw':pkg.bytes(True),'pages':pages,'numbering':{},'seconds':0}
 def test_actual_backfill_and_refresh_keep_roles_numbering_parts_and_markers(self):
  result=wf.update(self.src,self.root/'fixed.docx',self.m,wf.plan(self.src,self.m,appearance='reference',toc_policy=DEFAULT),calculator=self.mock,artifact_dir=self.root/'first')
  p=Package(result['output']);rows=wf.field_block(p,next(f for f in wf.fields(p)[0] if f['instruction'].strip().startswith('TOC')))
  self.assertEqual(len(rows),7);self.assertEqual([wf.ordered_text(next(x.iter(q('hyperlink')))).rsplit('\t',1)[1] for x in rows],['i','ii','iii','5','5','5','5'])
  for n in (1,3):self.assertEqual(result['classification']['paragraph_types'][result['proof']['paragraph_map'][str(n)]],self.m['paragraph_types'][str(n)])
  for name in self.pkg.parts:
   if name!='word/document.xml':self.assertEqual(self.pkg.parts[name],p.parts[name])
  self.assertEqual(len(result['proof']['added_TC_markers']),4)
  # A refresh must reuse exact original marker groups, never append duplicates.
  r2=wf.update(result['output'],self.root/'again.docx',result['classification'],wf.plan(result['output'],result['classification'],appearance='reference',toc_policy=DEFAULT),calculator=self.mock,artifact_dir=self.root/'second')
  self.assertEqual(r2['proof']['added_TC_markers'],[]);self.assertEqual(p.parts['word/document.xml'],Package(r2['output']).parts['word/document.xml'])
 def test_preserve_old_policy_and_explicit_closed_scopes(self):
  t=wf.plan(self.src,self.m);self.assertEqual(t['appearance'],'preserve');self.assertNotIn('toc_policy',t)
  policy={**DEFAULT,'abstracts':False,'back':False};rows,_=select(self.pkg,self.m,policy,wf.fields(self.pkg)[0][0],wf.paragraph_level);self.assertEqual([r['paragraph'] for r in rows],[5,8,10,12])
  with self.assertRaises(DemoError):wf.plan(self.src,self.m,toc_policy={**DEFAULT,'depth':4})
  # Only documented equivalent TC default spelling is accepted; no arbitrary switches.
  self.assertEqual(wf.toc_code_key(' TOC \\o "1-3" \\f C \\h '),wf.toc_code_key(' TOC \\o "1-3" \\h \\f '));self.assertIsNone(wf.toc_levels(' TOC \\o "1-3" \\t "Normal,1" '))
 def test_reference_and_policy_saved_draft_restore_without_execution(self):
  from web.session import WebSession
  from core.page_policy import DEFAULT as PAGE
  from unittest.mock import patch
  s=WebSession(self.root/'session');s.set_mode('academic');s.load(self.src.read_bytes(),'public.docx')
  s.page_layout_draft={'enabled':True,'policy':dict(PAGE),'toc_appearance':'reference','toc_policy':{**DEFAULT,'depth':2,'self':True},'input_sha256':s.inventory['input_sha256'],'regions':[]}
  raw=s.prepare_project();r=WebSession(self.root/'restored');r.stage_project(raw)
  with patch('core.word_native.calculate',side_effect=AssertionError('restore cannot run Word')):r=r.restore_project(acknowledged=True)
  self.assertEqual(r.page_layout_draft,s.page_layout_draft);self.assertIsNone(r.rehearsal);self.assertFalse(r.history)
 def test_pdf_freeze_only_accepts_our_no_result_tc_not_broken_reference(self):
  from core.word_native import no_result_tc
  self.assertTrue(no_result_tc(' TC "目录" \\f C \\l "1" '));self.assertTrue(no_result_tc(' TC "摘 要" \\f C \\l "1" '))
  for code in (' REF Missing ',' TC "目录" \\f C \\l "2" ',' TC "LINK external" \\f C \\l "1" '):self.assertFalse(no_result_tc(code))

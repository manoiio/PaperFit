from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import json,unittest
from lxml import etree as E
from core.package import Package,q,NS,DemoError
from core import word_fields as wf
from core.numbering import heading_numbering
ROOT=Path(__file__).resolve().parents[1]
class ContainerTocTests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.path=ROOT/'samples/phase52/source.docx';self.pkg=Package(self.path);self.m={'input_sha256':self.pkg.hash,'paragraph_types':json.loads((ROOT/'samples/phase52/roles.json').read_text()),'confirmed':True,'confirmation':'独立作者标注'}
 def mock(self,raw,codes,targets,update=True):
  f=self.root/'mock.docx';f.write_bytes(raw);p=Package(f);numbers={5:'1',15:'1.1',25:'1.1.1',35:'5'};levels={5:1,15:2,25:3,35:1};pages={n:{'adjusted':int(n.rsplit('_',1)[1])//10+1,'physical':int(n.rsplit('_',1)[1])//10+1} for n in targets};numbering={n:{'display':numbers[int(n.rsplit('_',1)[1])],'level':levels[int(n.rsplit('_',1)[1])]} for n in targets}
  if update:
   for par in p.root.iter(q('p')):
    for link in par.findall(q('hyperlink')):
     anchor=link.get(q('anchor'))
     if anchor in numbering:
      tx=link.find('w:r/w:t',NS);title=wf.text(p.paragraphs[int(anchor.rsplit('_',1)[1])-1]);tx.text=numbering[anchor]['display']+'\t'+title
      for fld in link.findall(q('fldSimple')):fld.find('w:r/w:t',NS).text=str(pages[anchor]['adjusted'])
  return {'raw':p.bytes(True),'pages':pages,'numbering':numbering,'seconds':0}
 def test_container_read_only_and_stable_top_level_identity(self):
  before=self.path.read_bytes();inv=wf.inventory(self.path);self.assertEqual(len(self.pkg.paragraphs),44);self.assertEqual(inv['objects'][0]['container'],1);self.assertTrue(inv['objects'][0]['safe']);self.assertEqual(before,self.path.read_bytes())
 def test_backfill_shell_numbering_and_all_unselected_parts(self):
  r=wf.update(self.path,self.root/'fixed.docx',self.m,wf.plan(self.path,self.m),calculator=self.mock,artifact_dir=self.root/'calc');b=Package(r['output']);self.assertEqual(len(b.paragraphs),44);self.assertEqual(r['proof']['paragraph_map'],{str(i):str(i) for i in range(1,45)})
  for part in self.pkg.parts:
   if part!='word/document.xml':self.assertEqual(self.pkg.parts[part],b.parts[part])
  a_sdt=self.pkg.root.find('w:body/w:sdt',NS);b_sdt=b.root.find('w:body/w:sdt',NS);self.assertEqual(wf.canon(a_sdt.find(q('sdtPr'))),wf.canon(b_sdt.find(q('sdtPr'))));self.assertEqual(wf.canon(a_sdt.find('w:sdtContent/w:p',NS)),wf.canon(b_sdt.find('w:sdtContent/w:p',NS)));self.assertEqual([x['display'] for x in r['proof']['heading_numbering']],['1\t研究方法','1.1\t实现步骤','1.1.1\t参数设置','5\t研究方法'])
 def test_locked_bound_nested_broken_remain_held(self):
  for tag in ('lock','dataBinding','sdt'):
   a=Package(self.path);shell=a.root.find('w:body/w:sdt',NS)
   E.SubElement(shell.find(q('sdtPr')) if tag!='sdt' else shell.find(q('sdtContent')),q(tag));path=self.root/(tag+'.docx');path.write_bytes(a.bytes(True));self.assertFalse(wf.inventory(path)['objects'][0]['safe'])
  a=Package(self.path);ends=a.root.xpath('.//w:fldChar[@w:fldCharType="end"]',namespaces=NS);ends[-1].getparent().remove(ends[-1]);path=self.root/'broken.docx';path.write_bytes(a.bytes(True));self.assertFalse(wf.inventory(path)['objects'][0]['safe'])
 def test_numbering_definition_direct_style_restart_and_old_guards(self):
  from core.numbering import numbering_info
  from core.formats import Resolver
  for n,origin in ((5,'style'),(15,'direct'),(25,'direct'),(35,'direct')):
   result=heading_numbering(self.pkg,self.pkg.paragraphs[n-1]);self.assertEqual(result['origin'],origin);self.assertEqual(result['status'],'resolved');self.assertFalse(result['continuity_checked'])
  self.assertEqual(numbering_info(self.pkg,Resolver(self.pkg),self.pkg.paragraphs[4])['status'],'review')
 def test_numbering_missing_measurement_or_wrong_level_blocks_publication(self):
  def wrong(*a,**kw):
   result=self.mock(*a,**kw);result['numbering']={};return result
  with self.assertRaisesRegex(DemoError,'显示编号'):wf.update(self.path,self.root/'bad.docx',self.m,wf.plan(self.path,self.m),calculator=wrong,artifact_dir=self.root/'wrong')
  self.assertFalse((self.root/'bad.docx').exists())
 def test_multiple_equal_codes_keep_container_identity(self):
  a=Package(self.path);body=a.root.find(q('body'));shell=deepcopy(body.find(q('sdt')));shell.find('w:sdtPr/w:id',NS).set(q('val'),'52002');body.insert(4,shell);path=self.root/'two.docx';path.write_bytes(a.bytes(True));m={**self.m,'input_sha256':Package(path).hash};inv=wf.inventory(path);self.assertEqual([r['container'] for r in inv['objects']],[1,2]);t=wf.plan(path,m,['field:1']);r=wf.update(path,self.root/'two-fixed.docx',m,t,calculator=self.mock,artifact_dir=self.root/'twocalc');b=Package(r['output']);self.assertEqual(wf.canon(shell),wf.canon(b.root.find(q('body')).findall(q('sdt'))[1]))
 def test_structure_uses_numbered_heading_and_not_ordinary_list(self):
  from core.classification import suggest_paragraph_types
  from core.structure_evidence import index
  rows=suggest_paragraph_types(self.path,include_sections=True)['paragraphs'];self.assertEqual(rows[4]['suggested_type'],'heading1');self.assertTrue(rows[4]['structure_boundary']);self.assertEqual(index(rows)['body_start'],5)
 def test_page_boundary_only_allows_balanced_heading_toc_targets(self):
  from core.page_layout import safe_boundary
  safe_boundary(self.pkg,5)
  a=Package(self.path);bm=a.paragraphs[4].find(q('bookmarkStart'));bm.set(q('name'),'PrivateUnknownTarget')
  with self.assertRaisesRegex(DemoError,'书签'):safe_boundary(a,5)
  a=Package(self.path);bm=a.paragraphs[4].find(q('bookmarkStart'));end=a.paragraphs[4].find('w:bookmarkEnd[@w:id="'+bm.get(q('id'))+'"]',NS);a.paragraphs[4].remove(end);a.paragraphs[5].append(end)
  with self.assertRaisesRegex(DemoError,'书签'):safe_boundary(a,5)
 def test_same_container_equal_instruction_selection_is_exact(self):
  a=Package(self.path);content=a.root.find('w:body/w:sdt/w:sdtContent',NS);old=list(content)[1:];copied=[deepcopy(p) for p in old]
  for p in copied:content.append(p)
  path=self.root/'same.docx';path.write_bytes(a.bytes(True));m={**self.m,'input_sha256':Package(path).hash}
  r=wf.update(path,self.root/'same-fixed.docx',m,wf.plan(path,m,['field:1']),calculator=self.mock,artifact_dir=self.root/'samecalc');b=Package(r['output']);actual=list(b.root.find('w:body/w:sdt/w:sdtContent',NS))[-len(copied):];self.assertEqual([wf.canon(p) for p in copied],[wf.canon(p) for p in actual])
 def test_locked_container_coexists_with_selected_safe_directory(self):
  a=Package(self.path);body=a.root.find(q('body'));shell=deepcopy(body.find(q('sdt')));E.SubElement(shell.find(q('sdtPr')),q('lock')).set(q('val'),'sdtContentLocked');body.insert(4,shell);path=self.root/'mixed.docx';path.write_bytes(a.bytes(True));m={**self.m,'input_sha256':Package(path).hash};rows=wf.inventory(path)['objects'];self.assertEqual([r['safe'] for r in rows],[True,False]);r=wf.update(path,self.root/'mixed-fixed.docx',m,wf.plan(path,m),calculator=self.mock,artifact_dir=self.root/'mixedcalc');b=Package(r['output']);self.assertEqual(wf.canon(shell),wf.canon(b.root.find(q('body')).findall(q('sdt'))[1]))
 def test_unknown_cache_and_cross_container_field_are_not_executable(self):
  a=Package(self.path);a.root.xpath('.//w:fldChar[@w:fldCharType="begin"]',namespaces=NS)[0].set(q('fldLock'),'on');path=self.root/'locked-on.docx';path.write_bytes(a.bytes(True));self.assertFalse(wf.inventory(path)['objects'][0]['safe'])
  a=Package(self.path);a.root.find('w:body/w:sdt/w:sdtContent/w:p[2]',NS).append(E.Element(q('customXml')));path=self.root/'unknown.docx';path.write_bytes(a.bytes(True));self.assertFalse(wf.inventory(path)['objects'][0]['safe'])
  # Same top-level paragraph ordinals cannot hide a body container in between.
  a=Package(ROOT/'samples/phase50/errors.docx');body=a.root.find(q('body'));p=E.Element(q('p'));r=E.SubElement(p,q('r'));E.SubElement(r,q('fldChar')).set(q('fldCharType'),'begin');r=E.SubElement(p,q('r'));E.SubElement(r,q('instrText')).text=' TOC \\o "1-3" \\h ';r=E.SubElement(p,q('r'));E.SubElement(r,q('fldChar')).set(q('fldCharType'),'separate');end=E.Element(q('p'));r=E.SubElement(end,q('r'));E.SubElement(r,q('fldChar')).set(q('fldCharType'),'end');body.insert(0,end);body.insert(0,E.Element(q('sdt')));body.insert(0,p);path=self.root/'cross.docx';path.write_bytes(a.bytes(True));self.assertFalse(wf.inventory(path)['objects'][0]['safe'])
if __name__=='__main__':unittest.main()

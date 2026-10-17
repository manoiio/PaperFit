"""Raw ZIP/XML author oracle. Does not import page planner, formatter or resolver."""
from pathlib import Path
from copy import deepcopy
from lxml import etree as E
import zipfile,json,hashlib
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main';N={'w':W};R='http://schemas.openxmlformats.org/officeDocument/2006/relationships';P='http://schemas.openxmlformats.org/package/2006/relationships';C='http://schemas.openxmlformats.org/package/2006/content-types'
def q(n):return '{'+W+'}'+n
def parts(path):
 with zipfile.ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}
def canon(x):return E.tostring(x,method='c14n')
def verify(source,formatted,numeric,final):
 a,b,c,d=map(parts,(source,formatted,numeric,final))
 # Ordinary stage author oracle: exact declared values and a narrow attribute mask.
 assert set(a)==set(b)
 for n in a:
  if n!='word/document.xml':assert a[n]==b[n],n
 aa=E.fromstring(a['word/document.xml']);bb=E.fromstring(b['word/document.xml'])
 ap=aa.find(q('body')).findall(q('p'));bp=bb.find(q('body')).findall(q('p'))
 def mask_pair(x,y,attrs,expected):
  assert y is not None
  for k,v in expected.items():assert y.get(q(k))==v,(k,v)
  for e in (x,y):
   if e is not None:
    for k in attrs:e.attrib.pop(q(k),None)
    if not e.attrib and not len(e) and e.getparent() is not None:e.getparent().remove(e)
 for n in (3,5,6,7,8,9,10,11,12):
  x,y=ap[n-1],bp[n-1]
  size='36' if n in (3,5,9) else '21' if n in (7,11) else '24'
  mask_pair(x.find('w:r/w:rPr/w:sz',N),y.find('w:r/w:rPr/w:sz',N),['val'],{'val':size})
  if n in (3,5,9):
   expected={'line':'240','lineRule':'auto','afterAutospacing':'0','afterLines':'50','after':'0'}
   if n!=3:expected.update(beforeAutospacing='0',beforeLines='50',before='0')
   mask_pair(x.find('w:pPr/w:spacing',N),y.find('w:pPr/w:spacing',N),list(expected),expected)
   if n!=3:mask_pair(x.find('w:pPr/w:jc',N),y.find('w:pPr/w:jc',N),['val'],{'val':'center'})
  elif n in (6,8,10,12):
   mask_pair(x.find('w:pPr/w:spacing',N),y.find('w:pPr/w:spacing',N),['line','lineRule'],{'line':'360','lineRule':'auto'})
   mask_pair(x.find('w:pPr/w:ind',N),y.find('w:pPr/w:ind',N),['firstLineChars','firstLine'],{'firstLineChars':'200','firstLine':'0'})
 for x,y in zip(aa.xpath('.//w:sectPr',namespaces=N),bb.xpath('.//w:sectPr',namespaces=N)):
  mask_pair(x.find(q('pgSz')),y.find(q('pgSz')),['w','h'],{'w':'11906','h':'16838'})
  mask_pair(x.find(q('pgMar')),y.find(q('pgMar')),['top','right','bottom','left'],dict.fromkeys(['top','right','bottom','left'],'1417'))
 for root in (aa,bb):
  for e in list(root.iter())[::-1]:
   if e.tag in (q('rPr'),q('pPr')) and not len(e) and not e.attrib:e.getparent().remove(e)
 assert canon(aa)==canon(bb),'ordinary stage changed an unauthorized object/attribute'
 # Exact handwritten numeric slots; no searching or parser-created expected text.
 x=E.fromstring(b['word/document.xml']);ps=x.find(q('body')).findall(q('p'))
 for n,tx in {6:'依据图1-1和图2-1核对纯文本引用。',7:'图1-1 合成曲线',11:'图2-1 合成结果曲线'}.items():
  ts=ps[n-1].findall('w:r/w:t',N);assert len(ts)==1;ts[0].text=tx
 assert canon(x)==canon(E.fromstring(c['word/document.xml']))
 assert {n:v for n,v in b.items() if n!='word/document.xml'}=={n:v for n,v in c.items() if n!='word/document.xml'}
 # Structural stage: old members preserved except exactly three necessary OPC members.
 assert set(c)<=set(d)
 for n in c:
  if n not in ('word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'):assert c[n]==d[n],n
 old=E.fromstring(c['word/document.xml']);new=E.fromstring(d['word/document.xml']);op=old.find(q('body')).findall(q('p'));np=new.find(q('body')).findall(q('p'));assert len(op)==len(np)==12
 for x,y in zip(op,np):
  # Every main run, bookmark, image and non-section pPr byte subtree unchanged.
  for p in (x,y):
   pp=p.find(q('pPr'))
   if pp is not None:
    sec=pp.find(q('sectPr'))
    if sec is not None:pp.remove(sec)
  assert canon(x)==canon(y)
 oldsec=E.fromstring(c['word/document.xml']).xpath('./w:body/w:p/w:pPr/w:sectPr|./w:body/w:sectPr',namespaces=N);newsec=E.fromstring(d['word/document.xml']).xpath('./w:body/w:p/w:pPr/w:sectPr|./w:body/w:sectPr',namespaces=N);assert len(oldsec)==len(newsec)==4
 rels=E.fromstring(d['word/_rels/document.xml.rels']);oldrels=E.fromstring(c['word/_rels/document.xml.rels']);assert len({r.get('Id') for r in rels})==len(rels)
 for r in oldrels:assert any(canon(r)==canon(s) for s in rels)
 ct=E.fromstring(d['[Content_Types].xml']);oldct=E.fromstring(c['[Content_Types].xml'])
 for e in oldct:assert any(canon(e)==canon(f) for f in ct)
 expected=[(None,None),("lowerRoman","1"),("decimal","1"),("decimal",None)]
 for i,(os,ns) in enumerate(zip(oldsec,newsec)):
  pg=ns.find(q('pgNumType'));assert (pg.get(q('fmt')) if pg is not None else None,pg.get(q('start')) if pg is not None else None)==expected[i]
  for variant in ('default','first','even'):
   refs=[e for e in ns.findall(q('footerReference')) if e.get(q('type'))==variant];assert len(refs)==1
   rid=refs[0].get('{'+R+'}id');matches=[r for r in rels if r.get('Id')==rid];assert len(matches)==1;target='word/'+matches[0].get('Target');assert target in d
   assert [e.get('ContentType') for e in ct if e.get('PartName')=='/'+target]==['application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml']
   fr=E.fromstring(d[target]);fields=fr.findall('.//'+q('fldSimple'));assert len(fields)==(0 if i==0 else 1)
   if fields:assert fields[0].get(q('instr')).strip()=='PAGE';assert ''.join(fields[0].itertext())==''
   if i>=2:assert '第'+str(i-1)+'章' in ''.join(fr.itertext())
   assert '原有' in ''.join(fr.itertext())
  # Exact allowed differences in each sectPr: footer references and pgNumType only.
  for s in (os,ns):
   for e in list(s):
    if e.tag in (q('footerReference'),q('pgNumType')):s.remove(e)
  assert canon(os)==canon(ns)
 return {'only_authored_ordinary_attributes':True,'only_authored_numeric_slots':True,'main_text_objects_and_runs_preserved_by_structure_stage':True,'all_old_header_footer_and_unselected_parts_byte_equal':True,'all_existing_relationships_and_content_types_preserved':True,'PAGE_empty_cache_not_fabricated':True,'four_sections_variants_and_numbering_verified':True,'physical_page_numbers':'not proved by XML; see actual page images and Word record','new_parts':sorted(set(d)-set(c))}
def verify_single(numeric,final):
 """Author-specified insertion positions, independent of the new section mapper."""
 a,b=parts(numeric),parts(final)
 for n,v in a.items():
  if n not in ('word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'):assert b[n]==v,n
 old,new=E.fromstring(a['word/document.xml']),E.fromstring(b['word/document.xml']);ob,nb=old.find(q('body')),new.find(q('body'));op,np=ob.findall(q('p')),nb.findall(q('p'));assert len(op)==len(np)==12
 original=ob.find(q('sectPr'));sections=new.xpath('./w:body/w:p/w:pPr/w:sectPr|./w:body/w:sectPr',namespaces=N);assert len(sections)==4
 for sec in sections:
  left,right=deepcopy(original),deepcopy(sec)
  for node in (left,right):
   for e in list(node):
    if e.tag in (q('footerReference'),q('pgNumType'),q('type')):node.remove(e)
  assert canon(left)==canon(right),'new section changed paper/header/columns/note/grid settings'
 for n in (2,4,8):
  section=np[n-1].find('w:pPr/w:sectPr',N);assert section is not None;section.getparent().remove(section)
 for n in (3,5,9):
  e=op[n-1].find('w:pPr/w:pageBreakBefore',N)
  assert e is not None;e.getparent().remove(e)
 for body in (ob,nb):
  body.remove(body.find(q('sectPr')))
  for e in list(body.iter())[::-1]:
   if e.tag==q('pPr') and not len(e) and not e.attrib:e.getparent().remove(e)
 assert canon(ob)==canon(nb),'single section stage changed an unauthorized paragraph/object'
 return {'new_boundaries_after_paragraphs':[2,4,8],'only_duplicate_start_pageBreakBefore_removed':[3,5,9],'original_section_settings_cloned_except_explicit_page_footer_type':True,'no_new_paragraph_or_object':True,'unselected_old_parts_byte_equal':True}

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('formatted');p.add_argument('numeric');p.add_argument('final');a=p.parse_args();print(json.dumps(verify(a.source,a.formatted,a.numeric,a.final),ensure_ascii=False,indent=2))

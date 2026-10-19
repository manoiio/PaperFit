"""Independent ZIP/XML oracle for the authored Stage57 inputs (no initial TC).
Does not import TOC generation, parser, policy, classification or Word adapter.
"""
from pathlib import Path
from copy import deepcopy
from zipfile import ZipFile
from lxml import etree as E
import argparse,json,hashlib,re
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}';N={'w':W[1:-1]}
def read(path):
 with ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}
def canonical(e):return E.tostring(e,method='c14n')
def directory(root):
 body=root.find(W+'body');rows=[];inside=False;depth=0
 for p in body:
  if p.tag!=W+'p':continue
  simple=p.find(W+'fldSimple')
  if simple is not None and simple.get(W+'instr','').strip().startswith('TOC '):rows.append(p);continue
  code=''.join(p.xpath('.//w:instrText/text()',namespaces=N))
  if code.strip().startswith('TOC '):assert not inside;inside=True
  if inside:
   rows.append(p)
   for f in p.iter(W+'fldChar'):
    if f.get(W+'fldCharType')=='begin':depth+=1
    if f.get(W+'fldCharType')=='end':depth-=1
   if depth==0:inside=False
 assert rows and not inside
 return rows

def verify(source,final):
 a,b=read(source),read(final);assert set(a)==set(b)
 for n in a:
  if n!='word/document.xml':assert a[n]==b[n],n
 x,y=E.fromstring(a['word/document.xml']),E.fromstring(b['word/document.xml']);old=directory(x);new=directory(y);body=y.find(W+'body');idx=body.index(new[0]);section=next((p.find('w:pPr/w:sectPr',N) for p in list(body)[idx:] if p.tag==W+'p' and p.find('w:pPr/w:sectPr',N) is not None),body.find(W+'sectPr'));size=section.find(W+'pgSz');margin=section.find(W+'pgMar');width=int(size.get(W+'w'))-sum(int(margin.get(W+k,'0')) for k in ('left','right','gutter'))
 targets=[];titles=[];pages=[];levels=[]
 for p in new:
  spacing=p.find('w:pPr/w:spacing',N);ind=p.find('w:pPr/w:ind',N);tab=p.find('w:pPr/w:tabs/w:tab[@w:val="right"]',N)
  assert spacing.get(W+'line')=='474' and spacing.get(W+'lineRule')=='exact' and spacing.get(W+'before')==spacing.get(W+'after')=='0'
  left=int(ind.get(W+'left'));assert left in (0,480,960);levels.append(1+left//480)
  assert tab.get(W+'leader')=='dot' and int(tab.get(W+'pos'))==width
  link=p.find(W+'hyperlink');anchor=link.get(W+'anchor');bm=y.xpath('.//w:bookmarkStart[@w:name=$name]',namespaces=N,name=anchor);assert len(bm)==1
  target=bm[0].getparent();title=''.join(link.xpath('./w:r/w:t/text()',namespaces=N));assert title==''.join(target.xpath('./w:r/w:t/text()',namespaces=N))
  page=link.find(W+'fldSimple');assert page.get(W+'instr').split()==['PAGEREF',anchor,'\\h'];pages.append(''.join(page.xpath('.//w:t/text()',namespaces=N)));titles.append(title);targets.append(body.index(target))
 assert titles[:3]==['摘要','Abstract','目录'] and pages[:3]==['i','ii','iii'];assert targets==sorted(set(targets))
 # Reverse only the exact directory blocks, new bounded bookmark pairs, and
 # three-run no-result TC markers on the explicitly named special titles.
 for tree,rows in ((x,old),(y,new)):
  for p in rows:tree.find(W+'body').remove(p)
 assert not any(re.match(r'^\s*TC\b',v) for v in x.xpath('.//w:instrText/text()',namespaces=N)),'input outside this authored oracle'
 old_names={e.get(W+'name') for e in x.iter(W+'bookmarkStart')};new_ids=set()
 for e in list(y.iter(W+'bookmarkStart')):
  if e.get(W+'name') not in old_names:
   assert e.get(W+'name').startswith('PFToc_');new_ids.add(e.get(W+'id'));e.getparent().remove(e)
 for e in list(y.iter(W+'bookmarkEnd')):
  if e.get(W+'id') in new_ids:e.getparent().remove(e)
 removed=0
 for p in y.find(W+'body').findall(W+'p'):
  cs=list(p)
  for i,r in enumerate(cs):
   code=r.find(W+'instrText')
   if code is None or not re.fullmatch(r' TC "(摘要|Abstract|目录|参考文献|致谢|附录)" \\f C \\l "1" ',code.text or ''):continue
   assert len(r)==1 and len(cs[i-1])==len(cs[i+1])==1
   assert cs[i-1][0].tag==cs[i+1][0].tag==W+'fldChar' and cs[i-1][0].get(W+'fldCharType')=='begin' and cs[i+1][0].get(W+'fldCharType')=='end'
   for e in (cs[i-1],r,cs[i+1]):p.remove(e)
   removed+=1
 assert canonical(x)==canonical(y),'non-TOC content/format or structure changed'
 return {'toc_entries_before':len(old),'toc_entries_after':len(new),'levels_present':sorted(set(levels)),'native_right_tab_matches_section_width':True,'exact_spacing_and_indent':True,'abstract_pages':pages[:2],'self_page':pages[2],'new_TC_markers':removed,'all_other_content_and_objects_equal':True,'all_other_parts_byte_equal':True,'final_sha256':hashlib.sha256(Path(final).read_bytes()).hexdigest()}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('final');args=p.parse_args();print(json.dumps(verify(args.source,args.final),ensure_ascii=False,indent=2))

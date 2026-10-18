"""Independent ZIP/XML oracle. No planner, resolver, field or numbering imports."""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
from lxml import etree as E
import json,sys
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+N['w']+'}'
def c(e):return E.tostring(e,method='c14n')
def read(path):
 with ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}
def verify(source,before,final,expected):
 a,b,f=map(read,(source,before,final));ar,br,fr=[E.fromstring(p['word/document.xml']) for p in (a,b,f)]
 assert set(b)==set(f)
 for n in b:
  if n!='word/document.xml':assert b[n]==f[n],n
 assert a['word/numbering.xml']==f['word/numbering.xml'],'numbering definitions changed'
 ab=ar.find('w:body',N);bb=br.find('w:body',N);fb=fr.find('w:body',N)
 aps=ab.findall('w:p',N);fps=fb.findall('w:p',N);assert len(aps)==len(fps)==44
 for h in expected['headings']:
  x,y=aps[h['paragraph']-1],fps[h['paragraph']-1]
  assert x.xpath('.//w:t/text()',namespaces=N)==y.xpath('.//w:t/text()',namespaces=N)
  for path in ('w:pPr/w:numPr','w:pPr/w:pStyle'):
   u,v=x.find(path,N),y.find(path,N);assert (c(u) if u is not None else None)==(c(v) if v is not None else None)
 shell=fb.find('w:sdt',N);old=bb.find('w:sdt',N)
 assert dict(shell.attrib)==dict(old.attrib)
 for key in ('sdtPr','sdtEndPr'):
  x,y=shell.find(W+key),old.find(W+key);assert (c(x) if x is not None else None)==(c(y) if y is not None else None)
 assert c(shell.find('w:sdtContent/w:p',N))==c(old.find('w:sdtContent/w:p',N)),'outside-field directory title changed'
 entries=[]
 for link in shell.xpath('./w:sdtContent/w:p/w:hyperlink',namespaces=N):
  anchor=link.get(W+'anchor');found=fr.xpath('.//w:bookmarkStart[@w:name=$n]',namespaces=N,n=anchor);assert len(found)==1
  par=found[0].getparent();n=fps.index(par)+1;h=next(h for h in expected['headings'] if h['paragraph']==n)
  raw=''.join((e.text or '') if e.tag==W+'t' else '\t' if e.tag==W+'tab' else '' for e in link.iter());prefix=h['display']+'\t'+h['text']+'\t';assert raw.startswith(prefix),raw
  page=raw[len(prefix):];assert page.isdigit() and int(page)>0
  entries.append({'paragraph':n,'number':h['display'],'title':h['text'],'page':page,'anchor':anchor})
 assert len(entries)==4 and [x['paragraph'] for x in entries]==[5,15,25,35]
 # Remove only the exact new heading bookmark pairs; restore only the authorised
 # SDT cache paragraphs. The rest of the full document, including the shell,
 # other bookmarks, every paragraph and pPr/rPr, must be canonical-byte equal.
 names=set(br.xpath('.//w:bookmarkStart/@w:name',namespaces=N))
 for bm in list(fr.iter(W+'bookmarkStart')):
  name=bm.get(W+'name')
  if name in names:continue
  assert name.startswith('PFToc_')
  assert bm.getparent() in fps and fps.index(bm.getparent())+1 in (5,15,25,35)
  ends=fr.xpath('.//w:bookmarkEnd[@w:id=$i]',namespaces=N,i=bm.get(W+'id'));assert len(ends)==1 and ends[0].getparent() is bm.getparent()
  bm.getparent().remove(bm);ends[0].getparent().remove(ends[0])
 newcontent=shell.find(W+'sdtContent');oldcontent=old.find(W+'sdtContent')
 for p in list(newcontent)[1:]:newcontent.remove(p)
 from copy import deepcopy
 for p in list(oldcontent)[1:]:newcontent.append(deepcopy(p))
 assert c(fr)==c(br),'unauthorised document subtree changed'
 return {'passed':True,'final_sha256':sha256(Path(final).read_bytes()).hexdigest(),'numbering_xml_byte_equal':True,'all_other_field_stage_parts_byte_equal':True,'sdt_shell_and_outside_title_preserved':True,'top_level_identity_preserved':True,'heading_numPr_styles_and_text_preserved':True,'exact_reverse_mask_document_equal':True,'entries':entries}
if __name__=='__main__':
 folder=Path(sys.argv[1]);print(json.dumps(verify(folder/'source.docx',folder/'before-update.docx',folder/'fixed.docx',json.loads((folder/'expected.json').read_text())),ensure_ascii=False,indent=2))

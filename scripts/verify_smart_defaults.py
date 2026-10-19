"""Author-known public fixture oracle: raw ZIP/XML, no new defaults/planner imports."""
from pathlib import Path
from copy import deepcopy
from io import BytesIO
import zipfile,json,hashlib,argparse
from lxml import etree as E
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}';N={'w':W[1:-1]}
def parts(p):
 with zipfile.ZipFile(p) as z:return {n:z.read(n) for n in z.namelist()}
def canon(e):return E.tostring(e,method='c14n')
def prune(r):
 for n in list(r.iter())[::-1]:
  if n.tag in (W+'pPr',W+'rPr',W+'tcPr',W+'tcBorders') and not n.attrib and not len(n):n.getparent().remove(n)
def verify(source,final,baseline=None,formatted=None):
 a,b=parts(source),parts(final);x,y=E.fromstring(a['word/document.xml']),E.fromstring(b['word/document.xml'])
 assert ''.join(x.xpath('//w:t/text()',namespaces=N))==''.join(y.xpath('//w:t/text()',namespaces=N))
 for name in a:
  if name not in ('word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'):assert a[name]==b[name],name
 # The independently known public plan adds one centered PAGE footer. Every
 # old relationship/content-type entry must remain, with only this dependency.
 assert set(b)-set(a)=={'word/footerPF1.xml'} and set(a)<=set(b)
 for name,key in (('word/_rels/document.xml.rels','Id'),('[Content_Types].xml','PartName')):
  old=E.fromstring(a[name]);new=E.fromstring(b[name]);oldrows={e.get(key,canon(e)):e for e in old};newrows={e.get(key,canon(e)):e for e in new}
  assert oldrows.keys()<=newrows.keys()
  for ident,e in oldrows.items():assert canon(e)==canon(newrows[ident]),name
  added=[e for ident,e in newrows.items() if ident not in oldrows];assert len(added)==1
  e=added[0]
  if key=='Id':assert set(e.attrib)=={'Id','Type','Target'} and e.get('Type').endswith('/footer') and e.get('Target')=='footerPF1.xml'
  else:assert e.attrib=={'PartName':'/word/footerPF1.xml','ContentType':'application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml'}
 footer=E.fromstring(b['word/footerPF1.xml']);assert footer.tag==W+'ftr' and len(footer)==1
 p=footer[0];assert p.tag==W+'p' and len(p)==2 and p.find('w:pPr/w:jc',N).get(W+'val')=='center'
 field=p.find(W+'fldSimple');assert field.get(W+'instr').strip()=='PAGE' and not ''.join(footer.itertext()).strip()
 ap=x.find(W+'body').findall(W+'p');bp=y.find(W+'body').findall(W+'p');assert len(ap)==len(bp)==9
 for n in (3,4,5,7):assert bp[n-1].find('w:pPr/w:jc',N).get(W+'val')=='center'
 assert canon(ap[7])==canon(bp[7]),'SEQ object changed'
 assert canon(ap[4].find('w:pPr/w:ind',N))==canon(bp[4].find('w:pPr/w:ind',N)),'unauthorized offset cleanup'
 assert [canon(e) for e in x.iter(W+'fldSimple')]==[canon(e) for e in y.iter(W+'fldSimple')]
 for t in y.iter(W+'tbl'):
  for side in ('left','right'):assert t.find('w:tblPr/w:tblBorders/w:'+side,N).get(W+'val')=='nil'
  for side in ('top','bottom','insideH','insideV'):assert t.find('w:tblPr/w:tblBorders/w:'+side,N).get(W+'val')=='single'
 for tag in ('drawing','bookmarkStart','bookmarkEnd','hyperlink'):
  assert [canon(e) for e in x.iter(W+tag)]==[canon(e) for e in y.iter(W+tag)],tag
 precise=False
 if baseline and formatted:
  a,b=parts(baseline),parts(formatted);assert a.keys()==b.keys()
  for n in a:
   if n!='word/document.xml':assert a[n]==b[n],n
  x,y=E.fromstring(a['word/document.xml']),E.fromstring(b['word/document.xml']);ap=x.find(W+'body').findall(W+'p');bp=y.find(W+'body').findall(W+'p')
  for n in (3,5,7):
   for p in (ap[n-1],bp[n-1]):
    e=p.find('w:pPr/w:jc',N)
    if e is not None:e.getparent().remove(e)
  for t in [*x.iter(W+'tbl'),*y.iter(W+'tbl')]:
   for side in ('left','right','start','end'):
    e=t.find('w:tblPr/w:tblBorders/w:'+side,N)
    if e is not None:e.getparent().remove(e)
   for cell in t.iter(W+'tc'):
    for side in ('left','right','start','end'):
     e=cell.find('w:tcPr/w:tcBorders/w:'+side,N)
     if e is not None:e.getparent().remove(e)
  prune(x);prune(y);assert canon(x)==canon(y),'unselected changes beyond the independently listed caption/outer-edge attributes'
  precise=True
 return {'oracle':'author positions and raw ZIP/XML; no smart default classifier','captions_centered':4,'previously_correct_caption_kept':True,'offset_kept':True,'protected_SEQ_REF_kept':True,'all_text_equal':True,'media_styles_numbering_notes_and_old_parts_equal':True,'old_relationships_and_content_types_kept':True,'new_footer_dependency_explicitly_checked':True,'new_defaults_exact_reverse_mask':precise,'final_sha256':hashlib.sha256(Path(final).read_bytes()).hexdigest()}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('final');a=p.parse_args();print(json.dumps(verify(a.source,a.final),ensure_ascii=False,indent=2))

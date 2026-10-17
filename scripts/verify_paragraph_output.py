"""Hand-authored declaration oracle and raw ZIP/XML whitelist, independent of new code."""
from pathlib import Path
from copy import deepcopy
import zipfile,json,hashlib,argparse
from lxml import etree as E
N='http://schemas.openxmlformats.org/wordprocessingml/2006/main';NS={'w':N}
def q(n):return '{'+N+'}'+n
def canon(e):return E.tostring(e,method='c14n')
def parts(p):
 with zipfile.ZipFile(p) as z:return {n:z.read(n) for n in z.namelist()}
def verify(source,output):
 a,b=parts(source),parts(output);assert list(a)==list(b)
 changed=[n for n in a if a[n]!=b[n]];assert set(changed)<=set(('word/document.xml','word/footnotes.xml','word/endnotes.xml'))
 roots={n:(E.fromstring(a[n]),E.fromstring(b[n])) for n in changed}
 x,y=map(E.fromstring,(a['word/document.xml'],b['word/document.xml']));ps=y.find(q('body')).findall(q('p'))
 # Independently specified expected XML, not a parser/compiler result.
 for index,mode,value in [(2,'exact','400'),(1,'exact','480'),(10,'atLeast','400'),(7,'auto','360')]:
  e=ps[index-1].find('w:pPr/w:spacing',NS);assert e.get(q('lineRule'))==mode and e.get(q('line'))==value,(index,mode,value)
 assert ps[1].find('w:pPr/w:ind',NS).get(q('firstLine'))=='420'
 assert ps[1].find('w:pPr/w:ind',NS).get(q('firstLineChars')) is None
 assert ps[9].find('w:pPr/w:ind',NS).get(q('hangingChars'))=='200'
 assert ps[9].find('w:pPr/w:ind',NS).get(q('firstLineChars')) is None
 assert ps[0].find('w:pPr/w:jc',NS).get(q('val'))=='center'
 assert ps[7].find('w:pPr/w:jc',NS).get(q('val'))=='both'
 for i in (2,3):
  e=ps[i].find('w:pPr/w:spacing',NS);assert e.get(q('line'))=='240' and e.get(q('lineRule'))=='auto';assert e.get(q('beforeLines'))=='50' and e.get(q('afterLines'))=='50'
 sp=ps[0].find('w:pPr/w:spacing',NS);assert sp.get(q('before'))=='240' and sp.get(q('after'))=='120'
 assert ps[4].find('w:pPr/w:jc',NS).get(q('val'))=='center'
 assert ps[4].find('w:pPr/w:spacing',NS).get(q('before'))=='120'
 fn=E.fromstring(b['word/footnotes.xml'])
 for n in fn.findall(q('footnote')):
  if n.get(q('type'),'normal')!='normal':continue
  for p in n.findall(q('p')):
   s=p.find('w:pPr/w:spacing',NS);assert s.get(q('line'))=='240' and s.get(q('lineRule'))=='exact'
 for name,data in a.items():
  if name not in changed:assert data==b[name]
 # Explicit per-object whitelist, separate for selected paragraph and safe ordinary run properties.
 main_attrs={1:{'jc':('val',),'spacing':('line','lineRule','before','beforeLines','beforeAutospacing','after','afterLines','afterAutospacing')},2:{'spacing':('line','lineRule'),'ind':('firstLine','firstLineChars','hanging','hangingChars')},3:{'spacing':('line','lineRule','before','beforeLines','beforeAutospacing','after','afterLines','afterAutospacing')},4:{'spacing':('line','lineRule','before','beforeLines','beforeAutospacing','after','afterLines','afterAutospacing')},5:{'spacing':('before','beforeLines','beforeAutospacing'),'jc':('val',)},6:{},7:{'ind':('firstLine','firstLineChars','hanging','hangingChars')},8:{'jc':('val',),'ind':('firstLine','firstLineChars','hanging','hangingChars')},9:{},10:{'spacing':('line','lineRule'),'ind':('firstLine','firstLineChars','hanging','hangingChars')},11:{},12:{},13:{},14:{}}
 def clean(p,attrs,fonts=False):
  for tag,keys in attrs.items():
   node=p.find('w:pPr/w:'+tag,NS)
   if node is not None:
    for key in keys:node.attrib.pop(q(key),None)
  if fonts:
   for run in p.findall(q('r')):
    if run.find(q('footnoteRef')) is not None or run.find(q('endnoteRef')) is not None:continue
    rp=run.find(q('rPr'))
    if rp is None:continue
    for tag,keys in [('rFonts',('eastAsia','eastAsiaTheme','ascii','asciiTheme')),('sz',('val',))]:
     node=rp.find(q(tag))
     if node is not None:
      for key in keys:node.attrib.pop(q(key),None)
  for node in reversed(list(p.iter())):
   if node.tag in {q(t) for t in ('rFonts','sz','spacing','ind','jc','rPr','pPr')} and not len(node) and not node.attrib and not node.text:node.getparent().remove(node)
 for name,(x,y) in roots.items():
  assert ''.join(x.xpath('//w:t/text()',namespaces=NS))==''.join(y.xpath('//w:t/text()',namespaces=NS))
  for tag in ('hyperlink','bookmarkStart','bookmarkEnd','fldChar','fldSimple','instrText','drawing','pict','tbl','sectPr','footnoteReference','endnoteReference','footnoteRef','endnoteRef','separator','continuationSeparator'):
   assert [canon(e) for e in x.iter(q(tag))]==[canon(e) for e in y.iter(q(tag))],(name,tag)
  if name=='word/document.xml':
   for i,(p,p2) in enumerate(zip(x.find(q('body')).findall(q('p')),y.find(q('body')).findall(q('p'))),1):
    if i==9:
     # Original SCUT keyword-label font patch permits only its exact four characters.
     assert ''.join(p2.xpath('./w:r/w:t/text()',namespaces=NS))=='关键词：格式；安全；验证'
     assert p2.findall(q('r'))[0].find('w:rPr/w:rFonts',NS).get(q('eastAsia'))=='黑体'
     for para in (p,p2):
      offset=0
      for run in list(para.findall(q('r'))):
       value=''.join(run.xpath('./w:t/text()',namespaces=NS));pos=para.index(run);para.remove(run)
       for k,char in enumerate(value):
        r=deepcopy(run);t=r.find(q('t'));t.text=char;t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
        if offset+k<4:
         e=r.find('w:rPr/w:rFonts',NS)
         for key in ('eastAsia','eastAsiaTheme'):e.attrib.pop(q(key),None)
        para.insert(pos+k,r)
       offset+=len(value)
    if i==13:assert canon(p)==canon(p2)
    attrs=main_attrs[i];clean(p,attrs,i in (1,3,4,5,6));clean(p2,attrs,i in (1,3,4,5,6))
   for r in (x,y):
    sect=r.find('w:body/w:sectPr',NS)
    for tag,keys in [('pgSz',('w','h','orient')),('pgMar',('top','bottom','left','right'))]:
     e=sect.find(q(tag))
     if e is not None:
      for k in keys:e.attrib.pop(q(k),None)
  else:
   for note,note2 in zip(x,y):
    if note.get(q('type'),'normal')!='normal':assert canon(note)==canon(note2);continue
    for p,p2 in zip(note.findall(q('p')),note2.findall(q('p'))):
     # Footnote lines selected by requirement; endnote line retains default school 1.5.
     attrs={'spacing':('line','lineRule')};clean(p,attrs,True);clean(p2,attrs,True)
  assert canon(x)==canon(y),name+' outside author whitelist'
 return {'source_sha256':hashlib.sha256(Path(source).read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(Path(output).read_bytes()).hexdigest(),'changed_members':changed,'authored_declarations_verified':True,'all_text_order_and_protected_subtrees_preserved':True,'unselected_parts_byte_equal':True,'code_exclusion_preserved':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args();print(json.dumps(verify(a.source,a.output),ensure_ascii=False,indent=2))

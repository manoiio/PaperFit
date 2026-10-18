"""Independent ZIP/XML oracle. No planner/Word/format engine imports."""
from pathlib import Path
from copy import deepcopy
import zipfile,hashlib,json,argparse
from lxml import etree as E
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main';N={'w':W};Q=lambda n:'{'+W+'}'+n

def read(path):
 with zipfile.ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def blocks(root):
 result=[]
 for owner in [root.find(Q('body')),*root.findall('.//w:sdtContent',N)]:
  start=None;level=0;code='';current=[]
  for p in list(owner):
   if p.tag!=Q('p'):continue
   simple=p.find(Q('fldSimple'))
   if simple is not None and simple.get(Q('instr'),'').strip().startswith('TOC '):result.append((owner,[p]));continue
   for r in p.findall(Q('r')):
    for x in r:
     if x.tag==Q('fldChar'):
      typ=x.get(Q('fldCharType'))
      if typ=='begin':
       if level==0:start=p;code='';current=[]
       level+=1
      elif typ=='end':level-=1
     elif x.tag==Q('instrText') and level==1:code+=x.text or ''
   if start is not None:
    current.append(p)
    if level==0:
     if code.strip().startswith('TOC '):result.append((owner,current))
     start=None;current=[]
 return result

def verify(before,after):
 a=read(before);b=read(after);assert set(a)==set(b),'ZIP members changed'
 assert all(a[n]==b[n] for n in a if n!='word/document.xml'),'Unselected ZIP member differs'
 ra=E.fromstring(a['word/document.xml']);rb=E.fromstring(b['word/document.xml']);ba=blocks(ra);bb=blocks(rb);assert ba and len(ba)==len(bb)
 entries=[]
 for owner,ps in bb:
  for p in ps:
   link=p.find(Q('hyperlink'));assert link is not None
   tab=p.find('w:pPr/w:tabs/w:tab[@w:val="right"]',N);assert tab is not None and tab.get(Q('leader'))=='dot'
   assert len(link.findall('w:r/w:tab',N))==1,'A native tab is required'
   anchor=link.get(Q('anchor'));target=rb.findall('.//w:bookmarkStart[@w:name="'+anchor+'"]',N);assert len(target)==1
   page=link.find('w:fldSimple',N);assert page is not None and 'PAGEREF '+anchor in page.get(Q('instr'),'')
   entries.append({'text':''.join(link.xpath('./w:r/w:t/text()',namespaces=N)),'page':''.join(page.xpath('.//w:t/text()',namespaces=N)),'right_twips':int(tab.get(Q('pos'))),'left_twips':(int(p.find('w:pPr/w:ind',N).get(Q('left'),'0')) if p.find('w:pPr/w:ind',N) is not None else None)})
 # Remove precisely the original/new TOC cache blocks and new dedicated destinations.
 for root,items in ((ra,ba),(rb,bb)):
  for owner,ps in items:
   at=owner.index(ps[0]);marker=E.Element('authorised-toc-cache')
   for p in ps:owner.remove(p)
   owner.insert(at,marker)
 oldnames={n.get(Q('name')) for n in ra.iter(Q('bookmarkStart'))}
 for start in list(rb.iter(Q('bookmarkStart'))):
  if start.get(Q('name')) not in oldnames:
   assert start.get(Q('name'),'').startswith('PFToc_');ident=start.get(Q('id'));ends=rb.findall('.//w:bookmarkEnd[@w:id="'+ident+'"]',N);assert len(ends)==1
   start.getparent().remove(start);ends[0].getparent().remove(ends[0])
 def canonical(e):return E.tostring(e,method='c14n')
 assert canonical(ra)==canonical(rb),'Unselected document tree differs'
 return {'before_sha256':digest(Path(before).read_bytes()),'after_sha256':digest(Path(after).read_bytes()),'other_zip_parts_byte_equal':True,'unselected_document_subtrees_equal':True,'native_tabs_and_links_valid':True,'entries':entries}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('before');p.add_argument('after');p.add_argument('--output');a=p.parse_args();r=verify(a.before,a.after);out=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
 if a.output:Path(a.output).write_text(out)
 else:print(out)

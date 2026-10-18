"""Raw ZIP/XML author oracle. Never imports classifiers, planners or format engines."""
from pathlib import Path
from copy import deepcopy
import zipfile,json,hashlib,argparse
from lxml import etree as E
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}';N={'w':W[1:-1]};XML='{http://www.w3.org/XML/1998/namespace}';R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
def read(p):
 with zipfile.ZipFile(p) as z:return {n:z.read(n) for n in z.namelist()}
def canon(x):return E.tostring(x,method='c14n',exclusive=True)
def root(p):return E.fromstring(p['word/document.xml'])
def ps(r):return r.find(W+'body').findall(W+'p')
def prune(r):
 for e in list(r.iter())[::-1]:
  if e.tag in (W+'pPr',W+'rPr') and not len(e) and not e.attrib:e.getparent().remove(e)
def same_parts(a,b,allowed=('word/document.xml',)):
 assert set(a)==set(b)
 for n in a:
  if n not in allowed:assert a[n]==b[n],n

def mask_pair(a,b,path,attrs,expected):
 x=a.find(path,N);y=b.find(path,N);assert y is not None,(path,expected)
 for k,v in expected.items():assert y.get(W+k)==v,(path,k,y.attrib,v)
 for e in (x,y):
  if e is not None:
   for k in attrs:e.attrib.pop(W+k,None)
   if not e.attrib and not len(e):e.getparent().remove(e)

def verify(folder,*,ordinary_fonts=False):
 folder=Path(folder);paths=[folder/'source.docx',*[folder/'stages'/n for n in ('01-format.docx','02-position.docx','03-pages.docx','04-width.docx','05-pagination.docx')],folder/'fixed.docx'];parts=list(map(read,paths))
 a,b=parts[:2];same_parts(a,b);x,y=root(a),root(b);ap,bp=ps(x),ps(y)
 for n,size in {3:'36',4:'24',8:'36',9:'24',10:'21',12:'24',13:'21',14:'24',15:'21',16:'24',17:'36',18:'24',20:'24'}.items():mask_pair(ap[n-1],bp[n-1],'w:r/w:rPr/w:sz',['val'],{'val':size})
 for n in (3,4,8,9,12,14,16,17,18,20):
  v={'line':'240' if n in (3,8,17) else '360','lineRule':'auto'}
  if n in (3,8,17):v.update(afterAutospacing='0',afterLines='50',after='0')
  if n in (8,17):v.update(beforeAutospacing='0',beforeLines='50',before='0')
  mask_pair(ap[n-1],bp[n-1],'w:pPr/w:spacing',list(v),v)
 for n in (9,12,14,16,18,20):mask_pair(ap[n-1],bp[n-1],'w:pPr/w:ind',['firstLineChars','firstLine'],{'firstLineChars':'200','firstLine':'0'})
 for n in (8,17):mask_pair(ap[n-1],bp[n-1],'w:pPr/w:jc',['val'],{'val':'center'})
 at=x.find(W+'body').findall(W+'tbl')[1];bt=y.find(W+'body').findall(W+'tbl')[1]
 for aa,bb in zip(at.findall('.//'+W+'r'),bt.findall('.//'+W+'r')):mask_pair(aa,bb,'w:rPr/w:sz',['val'],{'val':'21'})
 for aa,bb in zip(x.iter(W+'sectPr'),y.iter(W+'sectPr')):
  mask_pair(aa,bb,'w:pgSz',['w','h'],{'w':'11906','h':'16838'});mask_pair(aa,bb,'w:pgMar',['top','right','bottom','left'],dict.fromkeys(['top','right','bottom','left'],'1417'))
 if ordinary_fonts:
  # Author-known phase54 rules, not generated from the planner or change list.
  for n in (3,4,8,9,10,12,13,14,15,16,17,18,20):
   font='黑体' if n in (3,8,17) else '宋体'
   for aa,bb in zip(ap[n-1].findall('w:r',N),bp[n-1].findall('w:r',N)):
    af=aa.find('w:rPr/w:rFonts',N);bf=bb.find('w:rPr/w:rFonts',N)
    if bf is not None:
     for attr,target in [('eastAsia',font),('ascii',font if n in (10,13,15) else 'Times New Roman'),('hAnsi',font if n in (10,13,15) else 'Times New Roman')]:
      if (af.get(W+attr) if af is not None else None)!=bf.get(W+attr):
       assert bf.get(W+attr)==target,(n,attr,bf.attrib)
       for e in (af,bf):
        if e is not None:e.attrib.pop(W+attr,None)
     for e in (af,bf):
      if e is not None and not e.attrib:e.getparent().remove(e)
  for aa,bb in zip(at.findall('.//'+W+'r'),bt.findall('.//'+W+'r')):
   af=aa.find('w:rPr/w:rFonts',N);bf=bb.find('w:rPr/w:rFonts',N)
   if bf is not None and (af.get(W+'eastAsia') if af is not None else None)!=bf.get(W+'eastAsia'):
    assert bf.get(W+'eastAsia')=='宋体'
    for e in (af,bf):
     if e is not None:
      e.attrib.pop(W+'eastAsia',None)
      if not e.attrib:e.getparent().remove(e)
 prune(x);prune(y);assert canon(x)==canon(y),'ordinary unselected changes'
 # Exact authored permutation; includes table ordering, subtree and all run properties.
 a,b=parts[1:3];same_parts(a,b);x,y=root(a),root(b);body=x.find(W+'body');c,img=ps(x)[9:11];i=list(body).index(c);body.remove(c);body.insert(i+1,c);assert canon(x)==canon(y),'position changed anything except the adjacent pair'
 # Controlled structural stage: immutable old parts, exact known boundaries and inherited properties.
 a,b=parts[2:4];allowed={'word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'}
 assert set(a)<=set(b)
 for name in a:
  if name not in allowed:assert a[name]==b[name],name
 added=set(b)-set(a);assert all(n.startswith('word/footerPF') and n.endswith('.xml') for n in added)
 x,y=root(a),root(b);os=deepcopy(x.find(W+'body').find(W+'sectPr'));sections=list(y.iter(W+'sectPr'));assert len(sections)==4
 expected=[(None,None),('lowerRoman','1'),('decimal','1'),('decimal',None)]
 rel=E.fromstring(b['word/_rels/document.xml.rels']);oldrel=E.fromstring(a['word/_rels/document.xml.rels']);ct=E.fromstring(b['[Content_Types].xml']);oldct=E.fromstring(a['[Content_Types].xml'])
 for e in oldrel:assert any(canon(e)==canon(v) for v in rel)
 for e in oldct:assert any(canon(e)==canon(v) for v in ct)
 assert len({e.get('Id') for e in rel})==len(rel)
 for i,s in enumerate(sections):
  pg=s.find(W+'pgNumType');assert (pg.get(W+'fmt') if pg is not None else None,pg.get(W+'start') if pg is not None else None)==expected[i]
  clone=deepcopy(s);base=deepcopy(os)
  for e in (clone,base):
   for c in list(e):
    if c.tag in (W+'footerReference',W+'pgNumType',W+'type'):e.remove(c)
  assert canon(clone)==canon(base),'paper/header/note/grid inheritance altered'
  for ref in s.findall(W+'footerReference'):
   rr=[e for e in rel if e.get('Id')==ref.get(R+'id')];assert len(rr)==1;name='word/'+rr[0].get('Target');assert name in added
   f=E.fromstring(b[name]);fields=f.findall('.//'+W+'fldSimple');assert len(fields)==(0 if i==0 else 1)
   if fields:assert fields[0].get(W+'instr').strip()=='PAGE';assert not fields[0].findall('.//'+W+'t')
   if i>=2:assert '第'+str(i-1)+'章' in ''.join(f.itertext())
 for p in ps(y):
  pp=p.find(W+'pPr')
  if pp is not None:
   for e in pp.findall(W+'sectPr'):pp.remove(e)
 # At the authored abstract boundary the original redundant pageBreakBefore is
 # replaced by next-page sectPr. Restore only this exact approved flag.
 assert ps(y)[2].find('w:pPr/w:pageBreakBefore',N) is None
 oldflag=ps(x)[2].find('w:pPr/w:pageBreakBefore',N);assert oldflag is not None
 ps(y)[2].find(W+'pPr').insert(0,deepcopy(oldflag))
 by=y.find(W+'body');by.replace(by.find(W+'sectPr'),os);prune(x);prune(y);assert canon(x)==canon(y),'section transaction changed main objects'
 # Width: exact final 9072twips; only coherent tblW/grid/cell width and two image extents.
 a,b=parts[3:5];same_parts(a,b);x,y=root(a),root(b);at=x.find(W+'body').findall(W+'tbl')[1];bt=y.find(W+'body').findall(W+'tbl')[1]
 mask_pair(at,bt,'w:tblPr/w:tblW',['w'],{'w':'9072'})
 for aa,bb in zip(at.findall('w:tblGrid/w:gridCol',N),bt.findall('w:tblGrid/w:gridCol',N)):
  assert bb.get(W+'w')=='4536';aa.attrib.pop(W+'w');bb.attrib.pop(W+'w')
 for aa,bb in zip(at.findall('w:tr/w:tc',N),bt.findall('w:tr/w:tc',N)):mask_pair(aa,bb,'w:tcPr/w:tcW',['w'],{'w':'4536'})
 for tag in ('{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}extent','{http://schemas.openxmlformats.org/drawingml/2006/main}ext'):
  aa=next(x.iter(tag));bb=next(y.iter(tag));assert bb.attrib=={'cx':'5760720','cy':'1440180'};assert int(aa.get('cx'))*int(bb.get('cy'))==int(aa.get('cy'))*int(bb.get('cx'))
  for e in (aa,bb):e.attrib.pop('cx');e.attrib.pop('cy')
 assert canon(x)==canon(y),'width changed crop/media/other object'
 # Adjacency: only five author-listed flags; original header remains exact.
 a,b=parts[4:6];same_parts(a,b);x,y=root(a),root(b)
 for n,tag in ((3,'keepNext'),(3,'keepLines'),(10,'keepNext'),(11,'keepLines'),(13,'keepNext')):mask_pair(ps(x)[n-1],ps(y)[n-1],'w:pPr/w:'+tag,['val'],{'val':'1'})
 prune(x);prune(y);assert canon(x)==canon(y),'pagination changed an unauthorised property'
 header=root(b).find(W+'body').findall(W+'tbl')[1].findall(W+'tr');assert len(header[0].findall('w:trPr/w:tblHeader',N))==1;assert not any(r.findall('w:trPr/w:tblHeader',N) for r in header[1:])
 # Actual final cache only; target pages are independently authored/Word-observed 1 and4.
 a,b=parts[5:];same_parts(a,b);x,y=root(a),root(b);ob=x.find(W+'body');nb=y.find(W+'body');old=ps(x)[5];rows=ps(y)[5:7]
 for row,(title,page,n) in zip(rows,[('第1章 合成方法','1',8),('第2章 合成结果','4',17)]):
  link=row.find(W+'hyperlink');assert ''.join(link.xpath('.//w:t/text()',namespaces=N))==title+page;name=link.get(W+'anchor');assert name=='PFToc_'+hashlib.sha256(paths[5].read_bytes()).hexdigest()[:12]+'_'+str(n)
  targets=y.xpath('.//w:bookmarkStart[@w:name=$n]',namespaces=N,n=name);assert len(targets)==1;start=targets[0];ident=start.get(W+'id');assert ''.join(start.getparent().xpath('.//w:t/text()',namespaces=N))==title;start.getparent().remove(start);end=y.xpath('.//w:bookmarkEnd[@w:id=$i]',namespaces=N,i=ident);assert len(end)==1;end[0].getparent().remove(end[0])
 for r in rows:nb.remove(r)
 nb.insert(list(ob).index(old),deepcopy(old))
 original=[f for f in x.iter(W+'fldSimple') if f.get(W+'instr','').strip()=='PAGEREF ResultTarget \\h'][0];updated=[f for f in y.iter(W+'fldSimple') if f.get(W+'instr','').strip()=='PAGEREF ResultTarget \\h'][0];assert ''.join(updated.xpath('.//w:t/text()',namespaces=N))=='4';updated.getparent().replace(updated,deepcopy(original));assert x.nsmap==y.nsmap;assert canon(x)==canon(y),'cache stage changed unselected object'
 # Identity tables, complex table, links/media and all non-authorised ZIP objects held through chain.
 for i in (0,2):assert canon(root(parts[0]).find(W+'body').findall(W+'tbl')[i])==canon(root(parts[-1]).find(W+'body').findall(W+'tbl')[i])
 return {'author_oracle':'raw XML only; no engine/planner imports','all_stages_exact_authorised_reverse_masks':True,'original_cover_and_merged_tables_byte_subtrees_equal':True,'width_final_twips':9072,'image_final_emu':[5760720,1440180],'image_aspect_and_media_preserved':True,'five_pagination_properties_only':True,'existing_header_preserved':True,'TOC_pages':['1','4'],'PAGEREF':'4','physical_pages':'separately observed in native Word','final_sha256':hashlib.sha256(paths[-1].read_bytes()).hexdigest()}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('folder');a=p.parse_args();print(json.dumps(verify(a.folder),ensure_ascii=False,indent=2))

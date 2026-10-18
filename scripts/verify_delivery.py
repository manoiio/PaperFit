"""Independent ZIP/XML starter check. No format/check/planning engines."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys,json,hashlib,argparse,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def verify(stages):
 from scripts.verify_layout_assembly import verify as oracle,read,root,canon,W,N,ps,prune,same_parts,mask_pair
 source=ROOT/'samples/start-here';stages=Path(stages)
 with TemporaryDirectory() as d:
  folder=Path(d);(folder/'stages').mkdir();shutil.copyfile(source/'complete/原稿.docx',folder/'source.docx');shutil.copyfile(source/'complete/修正版.docx',folder/'fixed.docx')
  for name in ('01-format','02-position','03-pages','04-width','05-pagination'):shutil.copyfile(stages/('complete-'+name+'.docx'),folder/'stages'/(name+'.docx'))
  complete=oracle(folder,ordinary_fonts=True)
 a,b=read(source/'basic/原稿.docx'),read(source/'basic/修正版.docx');same_parts(a,b);x,y=root(a),root(b);ap,bp=ps(x),ps(y)
 for n in (3,7,9,10,13):
  for aa,bb in zip(ap[n-1].findall('w:r',N),bp[n-1].findall('w:r',N)):
   size='36' if n in (3,13) else '30' if n==7 else '21'
   if aa.find('w:rPr/w:sz',N) is not None or bb.find('w:rPr/w:sz',N) is not None:mask_pair(aa,bb,'w:rPr/w:sz',['val'],{'val':size})
   font='黑体' if n in (3,7,13) else '宋体'
   af=aa.find('w:rPr/w:rFonts',N);bf=bb.find('w:rPr/w:rFonts',N)
   if bf is not None:
    for attr,target in [('eastAsia',font),('ascii',font if n in (9,10) else 'Times New Roman'),('hAnsi',font if n in (9,10) else 'Times New Roman')]:
     if (af.get(W+attr) if af is not None else None)!=bf.get(W+attr):
      assert bf.get(W+attr)==target
      for e in (af,bf):
       if e is not None:e.attrib.pop(W+attr,None)
    for e in (af,bf):
     if e is not None and not e.attrib:e.getparent().remove(e)
 for n in (3,7,13):
  v={'line':'240','lineRule':'auto','beforeAutospacing':'0','beforeLines':'50','before':'0','afterAutospacing':'0','afterLines':'50','after':'0'}
  mask_pair(ap[n-1],bp[n-1],'w:pPr/w:spacing',list(v),v)
  if n!=7:mask_pair(ap[n-1],bp[n-1],'w:pPr/w:jc',['val'],{'val':'center'})
 for n in (4,5):mask_pair(ap[n-1],bp[n-1],'w:pPr/w:spacing',['line','lineRule'],{'line':'360','lineRule':'auto'})
 for n in (6,11):mask_pair(ap[n-1],bp[n-1],'w:pPr/w:ind',['firstLine','firstLineChars'],{'firstLine':'0','firstLineChars':'200'})
 for n,j in ((4,2),(14,2)):mask_pair(ap[n-1].findall(W+'r')[j-1],bp[n-1].findall(W+'r')[j-1],'w:rPr/w:sz',['val'],{'val':'24'})
 mask_pair(ap[4].find(W+'r'),bp[4].find(W+'r'),'w:rPr/w:rFonts',['eastAsia'],{'eastAsia':'宋体'})
 mask_pair(ap[13].findall(W+'r')[1],bp[13].findall(W+'r')[1],'w:rPr/w:rFonts',['ascii'],{'ascii':'Times New Roman'})
 at=x.find(W+'body').find(W+'tbl');bt=y.find(W+'body').find(W+'tbl')
 for aa,bb in zip(at.iter(W+'r'),bt.iter(W+'r')):mask_pair(aa,bb,'w:rPr/w:sz',['val'],{'val':'21'})
 for aa,bb in zip(x.iter(W+'sectPr'),y.iter(W+'sectPr')):
  mask_pair(aa,bb,'w:pgSz',['w','h'],{'w':'11906','h':'16838'});mask_pair(aa,bb,'w:pgMar',['top','right','bottom','left'],dict.fromkeys(['top','right','bottom','left'],'1417'))
 prune(x);prune(y);assert canon(x)==canon(y),'Basic unselected subtree changed'
 return {'basic':{'independent_XML':True,'all_non_document_parts_byte_equal':True,'only_authorized_attributes':True,'sha256':hashlib.sha256((source/'basic/修正版.docx').read_bytes()).hexdigest()},'complete':complete}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stages',required=True);a=p.parse_args();print(json.dumps(verify(a.stages),ensure_ascii=False,indent=2))

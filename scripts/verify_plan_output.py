"""Independent character/property/ZIP whitelist; never calls the plan or fix checker."""
from copy import deepcopy
from pathlib import Path
import json,sys,argparse
from lxml import etree as E
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.package import Package,q,NS,sha256
ROOT=Path(__file__).resolve().parents[1]
def canonical(x):return b'' if x is None else E.tostring(x,method='c14n')
def chars(p):
 out=[]
 for r in p.findall(q('r')):
  rp=deepcopy(r.find(q('rPr')));v=rp.find(q('vertAlign')) if rp is not None else None;vert=v.get(q('val')) if v is not None else None
  if v is not None:rp.remove(v)
  attrs=canonical(rp) if rp is not None and (len(rp) or rp.attrib) else b''
  for t in r.findall(q('t')):
   out.extend((ch,attrs,vert,tuple(sorted(r.attrib.items()))) for ch in t.text or '')
 return out

def verify(original,middle,final):
 a,b,c=map(Package,(original,middle,final))
 for pkg in (a,b,c):
  for r in pkg.root.iter(q('r')):
   if r.find(q('rPr')) is not None:assert r[0].tag==q('rPr'),'rPr must precede run contents'
 baseline=deepcopy(a.root);ps=baseline.find(q('body')).findall(q('p'))
 # Independently authorized ordinary changes, and nothing else.
 for n in (3,4):
  rp=ps[n-1].findall(q('r'))[0].find(q('rPr'));assert rp.find(q('sz')).get(q('val'))=='28'
  assert rp.find(q('rFonts')).get(q('eastAsia'))=='黑体'
  rp.find(q('sz')).set(q('val'),'24');rp.find(q('rFonts')).set(q('eastAsia'),'宋体')
 for run in ps[2].findall(q('r'))[1:]:
  assert run.find('w:rPr/w:sz',NS).get(q('val'))=='28';run.find('w:rPr/w:sz',NS).set(q('val'),'24')
 assert canonical(baseline)==canonical(b.root),'Step1 changed something outside six authorized attributes'
 ranges=json.loads((ROOT/'samples/phase28/scope.json').read_text())['selected_citations']
 by={}
 for t in ranges:by.setdefault(t['paragraph'],set()).update(range(t['start'],t['end']))
 assert len(b.paragraphs)==len(c.paragraphs)
 for n,(before,after) in enumerate(zip(b.paragraphs,c.paragraphs),1):
  if n not in by:assert canonical(before)==canonical(after),f'Unselected paragraph changed {n}';continue
  assert canonical(before.find(q('pPr')))==canonical(after.find(q('pPr')))
  for x,y in zip(chars(before),chars(after)):
   assert (x[0],x[1],x[3])==(y[0],y[1],y[3]),'Adjacent text or nonvertical formatting changed'
  aa,bb=chars(before),chars(after);assert len(aa)==len(bb)
  for offset,(x,y) in enumerate(zip(aa,bb)):
   assert y[2]==('superscript' if offset in by[n] else x[2]),(n,offset,'Unselected or selected vertAlign mismatch')
 for tag in ('fldSimple','fldChar','instrText','bookmarkStart','bookmarkEnd','hyperlink','sectPr','tbl','drawing'):
  assert [canonical(x) for x in a.root.iter(q(tag))]==[canonical(x) for x in c.root.iter(q(tag))],tag
 assert a.root.xpath('//w:t/text()',namespaces=NS)==b.root.xpath('//w:t/text()',namespaces=NS)
 assert ''.join(b.root.xpath('//w:t/text()',namespaces=NS))==''.join(c.root.xpath('//w:t/text()',namespaces=NS))
 for n,v in a.parts.items():
  if n!='word/document.xml':assert v==b.parts[n]==c.parts[n],n
 assert a.parts.keys()==b.parts.keys()==c.parts.keys()
 assert a.paragraphs[2].find('w:pPr/w:ind',NS).get(q('firstLine'))==c.paragraphs[2].find('w:pPr/w:ind',NS).get(q('firstLine'))=='560'
 assert a.parts.get('word/styles.xml') and a.root.xpath('//w:tbl',namespaces=NS) and a.root.xpath('//w:drawing',namespaces=NS),'nonvacuous preservation probe'
 return {'input_sha256':a.hash,'middle_sha256':b.hash,'final_sha256':c.hash,'step1_exactly_six_authorized_attributes':True,'step2_exact_selected_character_superscript_only':True,'all_text_and_order_preserved':True,'all_unselected_parts_byte_equal':True,'tables_media_fields_links_numbering_sections_preserved':True,'unselected_28pt_indent_preserved':True,'code_whitespace_preserved':True,'not_visual_or_Word_acceptance':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('original');p.add_argument('middle');p.add_argument('final');a=p.parse_args();print(json.dumps(verify(a.original,a.middle,a.final),ensure_ascii=False,indent=2))

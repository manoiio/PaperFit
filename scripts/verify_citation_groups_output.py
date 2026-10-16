"""Independent ZIP/XML and literal author oracle. No core/parser/fixer imports."""
from pathlib import Path
from copy import deepcopy
import json,zipfile,hashlib,sys,argparse
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def q(n):return '{'+NS['w']+'}'+n
def canon(x):return b'' if x is None else E.tostring(x,method='c14n')
def parts(path):
 with zipfile.ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}
def chars(p):
 out=[]
 for r in p.findall(q('r')):
  rp=deepcopy(r.find(q('rPr')));va=rp.find(q('vertAlign')) if rp is not None else None;v=va.get(q('val')) if va is not None else None
  if va is not None:rp.remove(va)
  other=canon(rp) if rp is not None and (len(rp) or rp.attrib) else b''
  for t in r.findall(q('t')):out.extend((c,other,v,tuple(sorted(r.attrib.items()))) for c in t.text or '')
 return out
def boundaries(p):
 n=0;out=[]
 for r in p.findall(q('r')):n+=sum(len(t.text or '') for t in r.findall(q('t')));out.append(n)
 return out
def verify(original,middle,final,*,browser=False):
 a,b,c=map(parts,(original,middle,final));ra,rb,rc=[E.fromstring(v['word/document.xml']) for v in (a,b,c)];pa,pb,pc=[r.find(q('body')).findall(q('p')) for r in (ra,rb,rc)];assert len(pa)==len(pb)==len(pc)
 authorized={3:[1,3] if browser else [1],4:[1,3]};expected=deepcopy(ra)
 for n,rs in authorized.items():
  p=expected.find(q('body')).findall(q('p'))[n-1]
  for i in rs:
   rp=p.findall(q('r'))[i-1].find(q('rPr'));assert rp.find(q('sz')).get(q('val'))=='28';assert rp.find(q('rFonts')).get(q('eastAsia'))=='黑体';rp.find(q('sz')).set(q('val'),'24');rp.find(q('rFonts')).set(q('eastAsia'),'宋体')
 assert canon(expected)==canon(rb),'ordinary transaction changed unselected properties'
 spans=json.loads((ROOT/'samples/phase30/independent-errors.json').read_text())['selected_spans'];by={}
 for span in spans:by.setdefault(span['paragraph'],[]).append(span)
 for n,(before,after) in enumerate(zip(pb,pc),1):
  aa,bb=chars(before),chars(after);assert len(aa)==len(bb)
  for span in by.get(n,[]):assert ''.join(x[0] for x in aa[span['start']:span['end']])==span['raw']
  offsets={j for span in by.get(n,[]) for j in range(span['start'],span['end'])}
  if not offsets:assert canon(before)==canon(after);continue
  assert canon(before.find(q('pPr')))==canon(after.find(q('pPr')))
  for i,(x,y) in enumerate(zip(aa,bb)):
   assert (x[0],x[1],x[3])==(y[0],y[1],y[3]);assert y[2]==('superscript' if i in offsets else x[2]),(n,i)
  wanted=set(boundaries(before))
  # Already-correct groups do not require run splitting; only actual changed spans.
  for span in by.get(n,[]):
   if not all(x[2]=='superscript' for x in aa[span['start']:span['end']]):wanted.update([span['start'],span['end']])
  wanted.discard(0);assert boundaries(after)==sorted(wanted),'unnecessary run boundary'
 for pkg,root in zip((a,b,c),(ra,rb,rc)):
  assert pkg.keys()==a.keys()
  for name,data in a.items():
   if name!='word/document.xml':assert data==pkg[name],name
  assert ''.join(root.xpath('//w:t/text()',namespaces=NS))==''.join(ra.xpath('//w:t/text()',namespaces=NS))
  for tag in ('fldSimple','fldChar','instrText','bookmarkStart','bookmarkEnd','hyperlink','sectPr','tbl','drawing'):
   assert [canon(e) for e in root.iter(q(tag))]==[canon(e) for e in ra.iter(q(tag))],tag
  for r in root.iter(q('r')):
   if r.find(q('rPr')) is not None:assert r[0].tag==q('rPr')
 assert any(n.startswith('word/media/') for n in a) and ra.findall('.//'+q('tbl')) and ra.findall('.//'+q('fldSimple'))
 return {'input_sha256':hashlib.sha256(Path(original).read_bytes()).hexdigest(),'middle_sha256':hashlib.sha256(Path(middle).read_bytes()).hexdigest(),'final_sha256':hashlib.sha256(Path(final).read_bytes()).hexdigest(),'ordinary_exact_authorized_attributes':8 if browser else 6,'selected_whole_spans_superscript_only':True,'necessary_run_boundaries_only':True,'all_text_objects_and_unselected_parts_preserved':True,'literal_group_count':len(spans),'literal_expected_numbers':[x['expected_numbers'] for x in spans],'not_visual_or_Word_acceptance':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('original');p.add_argument('middle');p.add_argument('final');p.add_argument('--browser',action='store_true');x=p.parse_args();print(json.dumps(verify(x.original,x.middle,x.final,browser=x.browser),ensure_ascii=False,indent=2))

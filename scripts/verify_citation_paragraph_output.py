"""Independent whole-tree pPr whitelist; no engine, proof builder or masking imports."""
from pathlib import Path
from copy import deepcopy
import zipfile,json,hashlib,argparse
from lxml import etree as E
N='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def q(n):return '{'+N+'}'+n
def canon(x):return E.tostring(x,method='c14n')
def read(p):
 with zipfile.ZipFile(p) as z:return {n:z.read(n) for n in z.namelist()}
def verify(original,output,*,only_line=False):
 a,b=map(read,(original,output));ra,rb=[E.fromstring(d['word/document.xml']) for d in (a,b)];ps=ra.find(q('body')).findall(q('p'));expected=deepcopy(ra);es=expected.find(q('body')).findall(q('p'))
 attrs={}
 for n in ((3,) if only_line else (3,4,7)):
  pp=es[n-1].find(q('pPr'));sp=pp.find(q('spacing'));sp.set(q('line'),'360');sp.set(q('lineRule'),'auto');attrs[n]=['spacing.line','spacing.lineRule']
  if only_line:continue
  sp.set(q('before'),'120');sp.set(q('beforeAutospacing'),'0');sp.set(q('after'),'0');sp.set(q('afterLines'),'50');sp.set(q('afterAutospacing'),'0');pp.find(q('jc')).set(q('val'),'both');attrs[n]+=['spacing.before','spacing.beforeAutospacing','spacing.after','spacing.afterLines','spacing.afterAutospacing','jc.val']
  if n in (3,4):pp.find(q('ind')).set(q('firstLineChars'),'200');pp.find(q('ind')).set(q('firstLine'),'0');attrs[n]+=['ind.firstLineChars','ind.firstLine']
 assert canon(expected)==canon(rb),'change outside author-defined pPr attribute whitelist'
 assert list(a)==list(b)
 for name,data in a.items():
  if name!='word/document.xml':assert data==b[name],name
 for n,(p,p2) in enumerate(zip(ps,rb.find(q('body')).findall(q('p'))),1):
  assert [canon(r) for r in p.findall(q('r'))]==[canon(r) for r in p2.findall(q('r'))],('run subtree changed',n)
 for tag in ('fldSimple','fldChar','instrText','bookmarkStart','bookmarkEnd','hyperlink','sectPr','tbl','drawing'):
  assert [canon(x) for x in ra.iter(q(tag))]==[canon(x) for x in rb.iter(q(tag))],tag
 assert ''.join(ra.itertext())==''.join(rb.itertext())
 assert any(n.startswith('word/media/') for n in a) and ra.findall('.//'+q('tbl'))
 return {'input_sha256':hashlib.sha256(Path(original).read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(Path(output).read_bytes()).hexdigest(),'authorized_pPr_attributes':attrs,'all_run_subtrees_byte_equivalent':True,'all_text_whitespace_and_order_preserved':True,'all_unselected_parts_byte_equal':True,'fields_tables_media_numbering_sections_preserved':True,'no_inline_or_citation_format_changes':True,'not_visual_or_Word_acceptance':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('original');p.add_argument('output');p.add_argument('--only-line',action='store_true');a=p.parse_args();print(json.dumps(verify(a.original,a.output,only_line=a.only_line),ensure_ascii=False,indent=2))

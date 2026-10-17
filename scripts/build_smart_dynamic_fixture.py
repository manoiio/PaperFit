"""Existing synthetic phase23 source, author-defined chain edits; no private input."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.package import Package,q,NS
from core.table_text import rebind
from lxml import etree as E

def build(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    source=ROOT/'samples/phase23/caption-errors.docx';pkg=Package(source)
    # The phase23 author manifest pins every role, not inferred by our new planner.
    m=json.loads(source.with_suffix('.types.json').read_text())
    # First chapter's existing figure1-1 ->1-2, second chapter figure2-1 ->2-3.
    for n,old,new in [(5,'图1-1','图1-2'),(13,'图2-1','图2-3')]:
        t=pkg.paragraphs[n-1].find('w:r/w:t',NS);assert t is not None and old in t.text;t.text=t.text.replace(old,new,1)
    # An explicit confirmed-body reference, with its numeric text across runs.
    p=pkg.paragraphs[3]
    for e in list(p):
        if e.tag!=q('pPr'):p.remove(e)
    for tx in ['依据图1-','2与图2-','3，可比较合成结果。再次参见图1-2。']:
        r=E.SubElement(p,q('r'));rp=E.SubElement(r,q('rPr'));E.SubElement(rp,q('color')).set(q('val'),'2468AC');E.SubElement(r,q('t')).text=tx
    path=output/'errors.docx';path.write_bytes(pkg.bytes(True));fresh=Package(path);m['input_sha256']=fresh.hash;rebind(m,fresh.hash)
    (output/'scope.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    (output/'independent-errors.json').write_text(json.dumps({'source':'phase23 synthetic author fixture','caption_numbers':{'5':['图1-2','图1-1'],'13':['图2-3','图2-1']},'body_paragraph':4,'expected_body':'依据图1-1与图2-1，可比较合成结果。再次参见图1-1。','not_authorized':['positions','fonts','colors','styles','tables','images','fields','other paragraphs and parts'],'word_com':'not run'},ensure_ascii=False,indent=2)+'\n')
    return path,m
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();build(a.output)

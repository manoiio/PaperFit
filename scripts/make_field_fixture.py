"""Public combined field fixture; expected labels are written independently."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.package import Package,q,NS
from lxml import etree as E

def field(code,value,locked=False):
 f=E.Element(q('fldSimple'));f.set(q('instr'),code)
 if locked:f.set(q('fldLock'),'1')
 r=E.SubElement(f,q('r'));E.SubElement(r,q('t')).text=value;return f

def build(destination):
 pkg=Package(ROOT/'samples/phase48/existing.docx');ps=pkg.paragraphs;parent=ps[3].getparent();ps[3].find('w:r/w:t',NS).text='目录'
 p=E.Element(q('p'));p.append(field(' TOC \\o "1-2" \\h ','旧章节……99'));parent.insert(parent.index(ps[3])+1,p)
 boundary=E.Element(q('p'));pr=E.SubElement(boundary,q('pPr'));sect=ps[3].find('w:pPr/w:sectPr',NS)
 if sect is not None:sect.getparent().remove(sect);pr.append(sect)
 parent.insert(parent.index(p)+1,boundary)
 for ident,n,name in ((102,10,'ChapterTwo'),(103,7,'CaptionOne')):
  p=ps[n-1];start=E.Element(q('bookmarkStart'));start.set(q('id'),str(ident));start.set(q('name'),name);p.insert(1 if p.find(q('pPr')) is not None else 0,start);E.SubElement(p,q('bookmarkEnd')).set(q('id'),str(ident))
 p=E.Element(q('p'));parent.insert(parent.index(ps[11]),p);r=E.SubElement(p,q('r'));E.SubElement(r,q('t')).text=' 正文引用：'
 for code,value,lock in [(' REF CaptionOne \\h ','图1-9 旧缓存',False),(' PAGEREF ChapterTwo \\h ','99',False),(' REF MissingTarget \\h ','保持缺失目标缓存',False),(' REF ChapterOne \\h ','保持锁定缓存',True),(' SEQ figure ','66',False)]:p.append(field(code,value,lock))
 Path(destination).write_bytes(pkg.bytes(True))
if __name__=='__main__':build(sys.argv[1])

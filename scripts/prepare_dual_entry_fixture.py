"""Combine existing synthetic note/table content. Never reads private historical files."""
from pathlib import Path
from copy import deepcopy
import zipfile,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.package import Package,q,NS
from core.table_text import tables
from lxml import etree as E

def build(output):
    output=Path(output)
    if output.exists():raise SystemExit('Refuse existing output')
    pkg=Package(ROOT/'samples/phase21/errors.docx');body=pkg.root.find(q('body'));original=tables(pkg)[0]
    cover=deepcopy(original)
    for t,value in zip(cover.xpath('.//w:t',namespaces=NS),['姓名：合成同学','学号：20260001234','学院：合成学院','指导教师：示例']):t.text=value
    body.insert(body.index(original),cover)
    cells=original.findall('.//'+q('tc'))
    for tc,value in zip(cells,['方案','耗时（秒）','方案甲','12']):
        p=tc.find(q('p'));r=p.find(q('r'));r.find(q('t')).text=value
        pr=r.find(q('rPr'))
        if pr is None:pr=E.Element(q('rPr'));r.insert(0,pr)
        fonts=E.SubElement(pr,q('rFonts'));fonts.set(q('eastAsia'),'楷体')
        sz=E.SubElement(pr,q('sz'));sz.set(q('val'),'28')
    complex_=deepcopy(tables(Package(ROOT/'samples/table-text-errors.docx'))[5]);body.insert(body.index(original)+1,complex_)
    raw=E.tostring(pkg.root,xml_declaration=True,encoding='UTF-8',standalone=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for n,v in pkg.parts.items():z.writestr(n,raw if n=='word/document.xml' else v)
if __name__=='__main__':build(sys.argv[1])

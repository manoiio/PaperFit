"""Public combination fixture, reuses the real Word-authored phase52 structure."""
from pathlib import Path
import sys,json
from copy import deepcopy
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.package import Package,q,NS,write_new
from core.engine import _ensure

def build(folder):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);p=Package(ROOT/'samples/phase52/source.docx');roles=json.loads((ROOT/'samples/phase52/roles.json').read_text())
 style=E.SubElement(p.styles,q('style'),{q('type'):'character',q('styleId'):'PublicEffects'});E.SubElement(style,q('name'),{q('val'):'Public effects'});rp=E.SubElement(style,q('rPr'))
 for tag,val in [('shadow','1'),('outline','1'),('w','85'),('spacing','20'),('position','2')]:E.SubElement(rp,q(tag),{q('val'):val})
 r=p.paragraphs[5].find(q('r'));_ensure(_ensure(r,'rPr'),'rStyle').set(q('val'),'PublicEffects')
 for index,tag,style_id in ((6,'emboss','PublicEmboss'),(7,'imprint','PublicImprint')):
  st=E.SubElement(p.styles,q('style'),{q('type'):'character',q('styleId'):style_id});E.SubElement(st,q('name'),{q('val'):style_id});E.SubElement(E.SubElement(st,q('rPr')),q(tag))
  _ensure(_ensure(p.paragraphs[index].find(q('r')),'rPr'),'rStyle').set(q('val'),style_id)
 cit=E.SubElement(p.paragraphs[5],q('r'));E.SubElement(E.SubElement(cit,q('rPr')),q('vertAlign'),{q('val'):'superscript'});E.SubElement(cit,q('t')).text='[1]'
 body=p.root.find(q('body'));end=body.find(q('sectPr'))
 for i in range(3):
  para=E.Element(q('p'));pp=E.SubElement(para,q('pPr'));E.SubElement(pp,q('pageBreakBefore'));run=E.SubElement(para,q('r'));E.SubElement(run,q('t')).text='公开长文分页核对 '+str(i+1)+'。只用于Word原生PDF及第10页之后页图的测试。';body.insert(body.index(end),para);roles[str(len(roles)+1)]='body'
 # Package writer keeps all other existing parts, including original numbering.
 p.story_roots['word/styles.xml']=p.styles
 write_new(folder/'source.docx',p.bytes(True))
 (folder/'roles.json').write_text(json.dumps(roles,ensure_ascii=False,indent=2)+'\n')
 text='正文不使用阴影和轮廓、浮雕和印入，字符缩放100%，标准字符间距，基线偏移0磅；二级标题黑体，不使用阴影和轮廓，字符缩放100%，标准字符间距；三级标题黑体。'
 (folder/'requirements.txt').write_text(text+'\n')
 expected={'body__shadow':False,'body__outline':False,'body__emboss':False,'body__imprint':False,'body__scale':100,'body__character_spacing':0,'body__baseline':0,'heading2_font_cn':'黑体','heading2__shadow':False,'heading2__outline':False,'heading2__scale':100,'heading2__character_spacing':0,'heading3_font_cn':'黑体'}
 headings=[{k:h[k] for k in ('paragraph','display','text')} for h in json.loads((ROOT/'samples/phase52/expected.json').read_text())['headings']]
 (folder/'expected.json').write_text(json.dumps({'fields':expected,'protected_superscript':'[1]','numbering_definition_unchanged':True,'top_level_paragraphs':47,'headings':headings},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':build(sys.argv[1])

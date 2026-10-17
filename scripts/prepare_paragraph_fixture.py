"""One combined public fixture; author-written roles and expected declarations."""
from pathlib import Path
import sys,json,zipfile
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.package import q,NS,Package
from copy import deepcopy
OUT=ROOT/'samples/phase47'
def build():
 OUT.mkdir(exist_ok=True);pkg=Package(ROOT/'samples/phase21/errors.docx');body=pkg.root.find(q('body'));old=list(body);sect=deepcopy(body.find(q('sectPr')))
 for x in old:body.remove(x)
 definitions=[('heading1','1 研究概况'),('body','本段讨论公开合成材料的排版方法，所有文字、空格和编号均须保留。正文以不同的行距和物理首行缩进呈现，作为完整处理的对照。'),('heading2','1.1 研究方法'),('heading3','1.1.1 实施方案'),('figure_caption','图1-1 系统结构'),('table_caption','表1-1 实验数据'),('abstract_cn_body','本研究摘要使用合成文字说明处理流程，摘要正文应按单独要求排版，不继承论文正文的固定行距和物理缩进。'),('abstract_en_body','This synthetic abstract describes a local formatting workflow. Its text and spacing are independently checked.'),('keywords_cn','关键词：格式；安全；验证'),('reference_item','[1] 合成作者. 公开的排版试验材料. 2026.'),('appendix_text','附录普通文字只描述公开的试验条件，不包括程序代码和数据输出。'),('ack_text','感谢公开软件测试资料的维护者，本段仅供格式验收。'),('other','代码：  x = [1, 2]\t# 保持空格'),('body','正文引用的脚注和尾注编号保留。')]
 for i,(role,text) in enumerate(definitions,1):
  p=E.SubElement(body,q('p'));pp=E.SubElement(p,q('pPr'))
  if role.startswith('heading'):E.SubElement(pp,q('pStyle'),{q('val'):'Heading'+role[-1]})
  E.SubElement(pp,q('spacing'),{q('line'):'360',q('lineRule'):'auto',q('before'):'0',q('after'):'0'});E.SubElement(pp,q('ind'),{q('firstLineChars'):'100'});E.SubElement(pp,q('jc'),{q('val'):'left'})
  r=E.SubElement(p,q('r'));rp=E.SubElement(r,q('rPr'));E.SubElement(rp,q('rFonts'),{q('eastAsia'):'宋体',q('ascii'):'Times New Roman',q('hAnsi'):'Times New Roman'});E.SubElement(rp,q('sz'),{q('val'):'24'});E.SubElement(r,q('t')).text=text
  if i==14:
   for x in ('footnoteReference','endnoteReference'):
    for ident in ('1','2','3'):
     r=E.SubElement(p,q('r'));E.SubElement(r,q(x),{q('id'):ident})
 body.append(sect)
 pkg.parts['word/document.xml']=E.tostring(pkg.root,xml_declaration=True,encoding='UTF-8',standalone=True)
 with zipfile.ZipFile(OUT/'errors.docx','w',zipfile.ZIP_DEFLATED) as z:
  for n,b in pkg.parts.items():z.writestr(n,b)
 (OUT/'roles.json').write_text(json.dumps({str(i):r for i,(r,t) in enumerate(definitions,1)},ensure_ascii=False,indent=2)+'\n')
 text='正文小四，固定20磅行距，首行缩进0.74厘米；一级标题固定24磅行距，段前12磅、段后6磅；图题居中，段前6磅；中文摘要正文1.5倍行距；参考文献最小20磅行距，悬挂缩进两字符；脚注固定12磅行距。'
 (OUT/'requirements.txt').write_text(text+'\n')
 expected={'font_size':12,'line_spacing':{'mode':'exact','value':20},'first_line_indent':{'kind':'first','unit':'cm','value':.74},'heading1_line_spacing':{'mode':'exact','value':24},'heading1__before':{'value':12,'unit':'pt'},'heading1__after':{'value':6,'unit':'pt'},'figure_caption__alignment':'center','figure_caption__before':{'value':6,'unit':'pt'},'abstract_cn_body__line_spacing':1.5,'reference_item__line_spacing':{'mode':'minimum','value':20},'reference_item__first_line_indent':{'kind':'hanging','unit':'chars','value':2},'footnote__line_multiple':{'mode':'exact','value':12}}
 (OUT/'expected.json').write_text(json.dumps({'kind':'hand-authored-before-live-request','fields':expected,'xml':{'body_line':['exact','400'],'body_firstLine':'420','heading1_line':['exact','480'],'reference_line':['atLeast','400'],'reference_hangingChars':'200','footnote_line':['exact','240']}},ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':build()

"""Synthetic structure/context benchmark; labels authored before any live request."""
from pathlib import Path
import zipfile,json,sys
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.package import q,NS

def paragraph(text,size=16):
 p=E.Element(q('p'));r=E.SubElement(p,q('r'));pr=E.SubElement(r,q('rPr'));E.SubElement(pr,q('rFonts'),{q('eastAsia'):'楷体'});E.SubElement(pr,q('sz'),{q('val'):str(size*2)});E.SubElement(r,q('t')).text=text;return p

def main():
 out=ROOT/'samples/phase44';out.mkdir(exist_ok=True,parents=True)
 with zipfile.ZipFile(ROOT/'samples/phase43/errors.docx') as z:parts={n:z.read(n) for n in z.namelist()}
 root=E.fromstring(parts['word/document.xml']);body=root.find(q('body'));tables=body.findall(q('tbl'));t=tables[1]
 body.insert(body.index(t),paragraph('1 实验设计',14));body.insert(body.index(t),paragraph('本节比较两种算法在同一公开测试集上的运行时间和准确率，下面的数据用于呈现实验对比结果。'))
 grid=t.find(q('tblGrid'))
 for c in list(grid):grid.remove(c)
 for _ in range(3):E.SubElement(grid,q('gridCol'),{q('w'):'1800'})
 for r in list(t.findall(q('tr'))):t.remove(r)
 for cells in [('算法','运行时间（秒）','准确率（%）'),('基线方法','12.8','87.1'),('改进方法','9.4','90.5')]:
  r=E.SubElement(t,q('tr'))
  for text in cells:
   c=E.SubElement(r,q('tc'));c.append(paragraph(text,14))
 def append(e):body.insert(len(body)-1,e)
 append(paragraph('结果解读',14));append(paragraph('从上述对比可见，改进方法在保持准确率的同时降低了运行时间，这里仅作合成数据的格式验收。'))
 append(paragraph('2 其他材料',14));append(paragraph('下面两列记录的用途尚未确定，不能仅凭作者预期判断它是论文内容表还是排版占位。'))
 small=E.Element(q('tbl'));E.SubElement(small,q('tblPr'));grid=E.SubElement(small,q('tblGrid'))
 for _ in range(2):E.SubElement(grid,q('gridCol'),{q('w'):'2000'})
 r=E.SubElement(small,q('tr'))
 for text in ('甲','乙'):
  c=E.SubElement(r,q('tc'));c.append(paragraph(text))
 append(small)
 code=E.fromstring(E.tostring(small));code.find('.//'+q('t')).text='print(data)';append(code)
 parts['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
 with zipfile.ZipFile(out/'errors.docx','w',zipfile.ZIP_DEFLATED) as z:
  for n,data in parts.items():z.writestr(n,data)
 paras=body.findall(q('p'));labels={'kind':'independent-visible-evidence-labels-before-live-call','tables':{'1':{'acceptable':['cover'],'basis':'identity labels; withheld locally'},'2':{'acceptable':['content'],'basis':'chapter experimental comparison and metric columns/rows, no caption'},'3':{'acceptable':['pending'],'basis':'nested protected; not sent'},'4':{'acceptable':['pending','other'],'basis':'two labels without semantic purpose; abstention appropriate'},'5':{'acceptable':['other'],'basis':'code protection; not sent'}},'paragraphs':{str(i):{'text':''.join(p.xpath('.//w:t/text()',namespaces=NS)),'acceptable':['heading2','heading3','pending'] if ''.join(p.xpath('.//w:t/text()',namespaces=NS))=='结果解读' else ['body','other','pending'] if i==2 else []} for i,p in enumerate(paras,1)},'protected':['tables 1,3,5','all body/note markers, fields, links, system notes, relationships and other parts']}
 (out/'labels.json').write_text(json.dumps(labels,ensure_ascii=False,indent=2)+'\n')
 # A second zero-ambiguity paper tests a multi-object supplement without a second structure POST.
 from docx import Document
 from docx.shared import Pt
 d=Document()
 for text in ['1 研究概况','本研究使用公开的合成实验材料进行格式验证。所有文字均用于软件测试，描述不对应任何真实研究结论。','1.1 研究方法','首先整理数据并比较结果，随后检查论文的普通文字和标题样式；这些内容必须在格式修改前后完全保留。','1.1.1 实施方案','本段为第三级标题后的普通文字，字体、字号和首行缩进是本次受控格式测试的对象。']:
  level=text.split(' ')[0].count('.')+1 if text[0].isdigit() else None
  p=d.add_paragraph(text,style='Heading'+str(level) if level else None);r=p.runs[0];r.font.name='楷体';r.font.size=Pt(15);r._r.get_or_add_rPr().rFonts.set(q('eastAsia'),'楷体')
  if level is None:
   pr=p._p.get_or_add_pPr();E.SubElement(pr,q('spacing'),{q('beforeLines'):'0',q('after'):'0',q('line'):'240',q('lineRule'):'auto'});E.SubElement(pr,q('jc'),{q('val'):'right'});E.SubElement(pr,q('ind'),{q('firstLineChars'):'0'})
 d.save(out/'supplement.docx')
if __name__=='__main__':main()

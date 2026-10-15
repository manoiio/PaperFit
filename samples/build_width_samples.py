"""第十阶段仅合成材料。输出存在时拒绝覆盖；规范/论文旧样本不改。"""
from pathlib import Path
from io import BytesIO
import json
from docx import Document
from docx.shared import Mm,Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from core.package import Package,sha256,new_path
ROOT=Path(__file__).resolve().parents[1]
pkg=Package(ROOT/'samples/extended-correct.docx');picture=next(b for n,b in pkg.parts.items() if n.startswith('word/media/'))
p=ROOT/'samples/width-demo-final.docx';new_path(p)
d=Document();s=d.sections[0];s.page_width=Mm(210);s.page_height=Mm(297);s.top_margin=Mm(25);s.bottom_margin=Mm(25);s.left_margin=Mm(35);s.right_margin=Mm(30)
normal=d.styles['Normal'];normal.font.name='Times New Roman';normal.font.size=Pt(12);normal.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'宋体');normal.paragraph_format.line_spacing=1.5
normal.paragraph_format.first_line_indent=Mm(0)
title=d.add_paragraph('页面宽度软件演示样本',style='Title')
from docx.shared import RGBColor
for run in title.runs:run.font.color.rgb=RGBColor(0,0,0)
# 默认Word模板的Title继承边线不用于本样本。
for sty in [d.styles['Title'],d.styles['Normal']]:
 pp=sty.element.find(qn('w:pPr'))
 if pp is not None:
  for e in list(pp):
   if e.tag==qn('w:pBdr'):pp.remove(e)
d.add_paragraph('本文件是脱敏合成案例。只验证声明宽度及选项保护，不能证明全文排版合格。')
def table(caption,width,rows,text):
 d.add_paragraph(caption);t=d.add_table(rows=rows,cols=2);t.style='Table Grid'
 for col in t.columns:col.width=Mm(width/2)
 for i,row in enumerate(t.rows):
  for j,c in enumerate(row.cells):c.width=Mm(width/2);c.text=f'项目{i+1}-{j+1} '+text
 return t
# 刻意自动调整，需明确确认转fixed；长文本在缩小后自然换行。
table('表1 超宽及换行示例（180mm）',180,5,'这是用于观察换行及行高增长的合成文字，缩小列宽后仍应完整可读。')
table('表2 正常表格（100mm，不应修改）',100,2,'正常对象保留。')
d.add_paragraph('图1 下方图片为超宽内嵌图（180mm）')
d.add_picture(BytesIO(picture),width=Mm(180))
d.add_paragraph('图2 下方图片为正常内嵌图（60mm）')
d.add_picture(BytesIO(picture),width=Mm(60))
t=table('表3 复杂合并示例（待复核，不强行适配）',180,2,'合并保留。');t.cell(0,0).merge(t.cell(0,1))
d.save(p)
m={'input_sha256':sha256(p.read_bytes()),'paragraph_types':{str(i):'other' for i in range(1,len(d.paragraphs)+1)},'confirmed':True,'confirmation':'人工独立标记：软件演示文字及对象说明，不作为论文正文；本样本专用于宽度辅助'}
p.with_suffix('.types.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
(ROOT/'samples/width-expected.json').write_text(json.dumps({'independent_manual_design':True,'page_mm':210,'margins_mm':{'left':35,'right':30},'body_mm':145,'tables':[{'index':1,'width_mm':180,'auto':True,'fixable':True},{'index':2,'width_mm':100,'must_preserve':True},{'index':3,'width_mm':180,'merged':True,'review':True}],'images':[{'width_mm':180,'fixable':True},{'width_mm':60,'must_preserve':True}],'B':{'input':'work/phase9/final/B-fixed.docx','table_width_mm':160.02,'body_width_mm':145.0093}},ensure_ascii=False,indent=2))

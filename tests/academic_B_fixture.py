from pathlib import Path
import json
from core.academic_templates import V4_FIELDS,validate_draft,EXTRA
from core.norms import selected_segments
ROOT=Path(__file__).resolve().parents[1]
values={}
def add(obj,**fields):values.update({obj+'__'+k:v for k,v in fields.items()})
S=lambda x,u='lines':{'value':x,'unit':u}
for obj,fontKey,font in [('abstract_cn_title','font_cn','楷体'),('abstract_en_title','font_western','Arial'),('reference_title','font_cn','宋体')]:add(obj,**{fontKey:font,'font_size':20,'alignment':'left','line_spacing':1.25,'before':S(1),'after':S(.25)})
add('abstract_cn_body',font_cn='仿宋',font_size=14,line_spacing=2,first_line_indent=1,before=S(6,'pt'),after=S(0,'pt'),alignment='both',bold=False)
add('abstract_en_body',font_western='Arial',font_size=14,line_spacing=2,first_line_indent=1,before=S(6,'pt'),after=S(0,'pt'),alignment='both')
add('keywords_cn',label_font_cn='黑体',label_font_size=14,label_bold=True,content_font_cn='楷体',content_font_size=12,content_bold=False)
add('keywords_en',label_font_western='Arial',label_font_size=14,label_bold=True,content_font_western='Arial',content_font_size=12,content_bold=False)
add('reference_item',font_cn='楷体',font_size=11,line_spacing=1,first_line_indent=0,before=S(0,'pt'),after=S(3,'pt'))
add('body',before=S(0,'pt'),after=S(3,'pt'),alignment='both',bold=False)
add('heading1',before=S(1),after=S(.5));add('heading2',before=S(.5),after=S(.5));add('heading3',before=S(.5),after=S(.25))
segments=selected_segments((ROOT/'samples/norm15-B.txt').read_text());draft={n:None for n in V4_FIELDS};draft['unsupported']=[]
labels={'abstract_cn_title':'中文摘要标题','abstract_cn_body':'中文摘要正文','abstract_en_title':'英文摘要标题','abstract_en_body':'英文摘要正文','reference_title':'参考文献标题','reference_item':'参考文献条目','body':'正文段前','heading1':'一级标题','heading2':'二级标题','heading3':'三级标题'}
for n,v in values.items():
 _,obj,prop=EXTRA[n];label=labels.get(obj)
 if obj.startswith('keywords'):label=('中文' if obj.endswith('cn') else '英文')+'关键词'+('标签' if prop.startswith('label_') else '内容')
 seg=next(s for s in segments if s['text'].startswith(label));draft[n]={'value':v,'unit':V4_FIELDS[n][2],'quote':seg['text'],'location':seg['location'],'support':'supported'}
validate_draft(draft,segments)

"""Presentation adapters constrained by existing field schemas and validators."""
import streamlit as st
from core import rule_bundle as rb
from core.classification import TYPES
from core.templates import CN,WEST,ALIGNMENTS

DECISIONS={'manual':'手动指定','keep':'保留当前生效值','disabled':'不检查','ai':'采用提取值','choose':'尚未决定','imported':'沿用导入草稿'}
REASONS={'unsupported':'超出已有支持范围','conflict':'要求相互冲突','ambiguous':'对象或要求不明确','out_of_range':'数值超出支持范围','title':'标题级别不明确','fixed_spacing':'固定行距未支持','minimum_spacing':'最小行距未支持','unknown_font':'字体未支持','landscape':'页面方向未支持','printing':'打印要求须人工核对','semantic':'内容语义须人工核对','indent_unit':'缩进单位未支持'}

def group(module,name):
 if module=='main':
  if name in ('figure_caption__line_spacing','table_caption__line_spacing'):return TYPES[name.split('__')[0]]
  from core.academic_rules import FIELDS as academic
  from core.backmatter import FIELDS as back
  if name in academic:return TYPES.get(academic[name][1],'整篇只读提示')
  if name in back:return TYPES[back[name][1]]
  if name.startswith('table_content__'):return '论文内容表格'
  if name=='paper' or name.startswith('margin_'):return '页面'
  for obj in ('heading1','heading2','heading3','figure_caption','table_caption'):
   if name.startswith(obj+'_'):return TYPES[obj]
  return '正文'
 obj=name.split('__')[0]
 return {'cover_title':'封面论文标题','header_text':'普通页眉文字','footer_text':'普通页脚文字','title':'目录标题','level1':'目录一级条目','level2':'目录二级条目','level3':'目录三级条目','footnote':'脚注普通文字','endnote':'尾注普通文字'}.get(obj,'页眉页脚距离')

def label(module,name):
 raw=rb.FIELDS[module][name][1]
 if module in ('main','notes') and name.endswith(('line_spacing','line_multiple')):return '行距'
 if '__' in name:
  prop=name.split('__',1)[1]
  labels={'font_cn':'中文字体','font_western':'西文字体','font_size':'字号','alignment':'对齐','line_multiple':'行距','line_spacing':'行距','first_line_indent':'段落缩进','before':'段前间距','after':'段后间距','bold':'加粗'}
  for prefix,title in (('label_','标签'),('content_','内容')):
   if prop.startswith(prefix):return title+labels.get(prop[len(prefix):],prop)
  return labels.get(prop,raw)
 for obj in ('heading1','heading2','heading3','figure_caption','table_caption'):
  if name.startswith(obj+'_'):return raw.removeprefix(TYPES[obj]).strip()
 return raw.removeprefix('正文').strip() if group(module,name)=='正文' else raw

def accepts(module,name,value):
 try:rb.validate_value(module,name,value);return True
 except Exception:return False

def spec(module,name):
 unit=rb.FIELDS[module][name][2]
 unit={'font_cn':'font','font_western':'font'}.get(unit,unit)
 candidates={'font':WEST if 'western' in name else CN,'alignment':tuple(ALIGNMENTS),'paper':('A4 portrait',),'bool':(True,False),'bold':(True,False),'multiple':(1.,1.25,1.5,2.),'chars':(0,1,2)}
 if module in ('main','notes') and name.endswith(('line_spacing','line_multiple')):return {'kind':'line','unit':unit}
 if module=='main' and name.endswith('first_line_indent'):return {'kind':'indent','unit':unit}
 if unit in candidates:return {'kind':'choice','unit':unit,'options':[v for v in candidates[unit] if accepts(module,name,v)]}
 if unit=='spacing':return {'kind':'spacing','unit':unit}
 if unit in ('pt','mm'):
  # UI bounds are a projection of actual validators, not a new execution policy.
  values=[x/2 for x in range(0,101) if accepts(module,name,x/2)]
  return {'kind':'number','unit':unit,'min':min(values),'max':max(values),'step':.5 if unit=='pt' else .1}
 return {'kind':'unsupported','unit':unit}

def value_control(module,name,seed,key,touch):
 s=spec(module,name);unit=s['unit'];title=label(module,name)
 if seed is not None and not accepts(module,name,seed):
  st.error('已有草稿值不在当前支持范围，未替换为默认选项。请明确修复或选择不检查。');st.text(str(seed));return None
 if s['kind'] in ('line','indent'):
  from core.paragraph_values import line,indent
  if s['kind']=='line':
   d=line(seed) if seed is not None else None;options=['multiple','exact','minimum']
   mode=st.selectbox(title+'模式',options,index=options.index(d['mode']) if d else None,format_func=lambda x:{'multiple':'倍数','exact':'固定（磅）','minimum':'最小（磅）'}[x],key=key+'-mode',on_change=touch,placeholder='尚未配置')
   x=st.number_input(title+'数值',value=float(d['value']) if d else None,min_value=.05,max_value=120.,step=.05,key=key,on_change=touch,placeholder='尚未配置')
   st.caption('倍数0.5–5；固定/最小1–120磅，均0.05步长。固定值可能裁切，需预览。')
   return {'mode':mode,'value':x} if mode is not None and x is not None else None
  d=indent(seed,hanging=True) if seed is not None else None;options=['first','hanging'] if name=='reference_item__first_line_indent' else ['first']
  kind=st.selectbox('缩进类型',options,index=options.index(d['kind']) if d else None,format_func=lambda x:'首行缩进' if x=='first' else '悬挂缩进',key=key+'-kind',on_change=touch,placeholder='尚未配置')
  units=['chars','pt','mm','cm'];u=st.selectbox('缩进单位',units,index=units.index(d['unit']) if d else None,format_func=lambda x:{'chars':'字符','pt':'磅','mm':'毫米','cm':'厘米'}[x],key=key+'-unit',on_change=touch,placeholder='尚未配置')
  x=st.number_input(title+'数值',value=float(d['value']) if d else None,min_value=0.,max_value=144.,step=.01,key=key,on_change=touch,placeholder='尚未配置')
  st.caption('字符与物理距离不互换；物理值取最邻近twip，误差不超过0.025磅。')
  return {'kind':kind,'unit':u,'value':x} if kind is not None and u is not None and x is not None else None
 if s['kind']=='choice':
  options=s['options']
  def display(v):
   if unit=='alignment':return ALIGNMENTS[v]
   if unit in ('bool','bold'):return '要求加粗' if v and 'bold' in name else '要求不加粗' if 'bold' in name else '启用只读提示' if v else '不启用只读提示'
   if unit=='paper':return 'A4竖向'
   return str(v)+(' 倍' if unit=='multiple' else ' 字符' if unit=='chars' else '')
  return st.selectbox(title,options,index=options.index(seed) if seed is not None else None,format_func=display,placeholder='尚未配置，请明确选择',key=key,on_change=touch)
 if s['kind']=='number':
  return st.number_input(title+('（磅 / pt）' if unit=='pt' else '（毫米 / mm）'),min_value=float(s['min']),max_value=float(s['max']),value=float(seed) if seed is not None else None,step=s['step'],key=key,on_change=touch,placeholder='尚未配置')
 if s['kind']=='spacing':
  a,b=st.columns([2,1]);u=b.selectbox('间距单位',['pt','lines'],index=['pt','lines'].index(seed['unit']) if seed else None,format_func=lambda x:'磅（pt）' if x=='pt' else '行',placeholder='请选择单位',key=key+'-unit',on_change=touch)
  # Keep the entered value on unit changes; final validation rejects conflicts.
  v=a.number_input(title+'数值',min_value=0.,max_value=72.,value=float(seed['value']) if seed else None,step=.25,key=key,on_change=touch,placeholder='尚未配置')
  st.caption('支持0–72磅，0.5磅步长；或0–3行，0.25行步长。行与磅不自动换算。')
  return {'value':v,'unit':u} if v is not None and u is not None else None
 st.warning('此字段仍需使用原兼容编辑器；未生成默认值。');return None

def friendly_error(message):
 out=str(message)
 names={n:(m,group(m,n)+' · '+label(m,n)) for m in rb.MODULES for n in rb.FIELDS[m]}
 for n in sorted(names,key=len,reverse=True):out=out.replace(n,names[n][1])
 for m in rb.MODULES:out=out.replace(m+'.',rb.LABELS[m]+' · ')
 return out

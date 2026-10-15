"""Opt-in v4 editor: tables by object and one selected field per group."""
import json
import streamlit as st
from core.academic_templates import V4_FIELDS,EXTRA,KINDS,default_values
from core.academic_rules import NEW_TYPES,GENERIC_TYPES,LABELS
from core.backmatter import TYPES as BACK_TYPES,FIELDS as BACK_FIELDS
from core.back_templates import V6_FIELDS
from core.templates import CN,WEST,ALIGNMENTS
from core import load_rules
from .session import public_error
from .template_ui import display_value

OBJECTS={'body':'正文','heading1':'一级标题','heading2':'二级标题','heading3':'三级标题','figure_caption':'图题','table_caption':'表题',**NEW_TYPES,**BACK_TYPES,'document':'只读内容提示','table_content':'论文内容表格（与表题分开）'}
def obj(n):
 if n in BACK_FIELDS:return BACK_FIELDS[n][1]
 if n.startswith('table_content__'):return 'table_content'
 if n in EXTRA:return EXTRA[n][1]
 from core.templates import split_field
 return split_field(n)[0]
def label(n):
 if n in BACK_FIELDS:return LABELS[BACK_FIELDS[n][2]]
 if n.startswith('table_content__'):return '中文字体' if n.endswith('font_cn') else '普通字号'
 if n not in EXTRA:return V4_FIELDS[n][1]
 p=(BACK_FIELDS[n] if n in BACK_FIELDS else EXTRA[n])[2];part='标签 ' if p.startswith('label_') else '内容 ' if p.startswith('content_') else ''
 return part+LABELS.get(p.removeprefix('label_').removeprefix('content_'),p)
def show(n,v):
 if v is None:return '未启用'
 if n.startswith('table_content__'):return str(v)+('磅' if n.endswith('font_size') else '')
 if n not in EXTRA and n not in BACK_FIELDS:return display_value(n,v)
 p=(BACK_FIELDS[n] if n in BACK_FIELDS else EXTRA[n])[2]
 if isinstance(v,bool):return ('启用只读提示' if v else '不启用只读提示') if n=='content_checks' else ('加粗' if v else '不加粗')
 if isinstance(v,dict):return f"{v['value']:g}"+('行' if v['unit']=='lines' else '磅')
 if p=='alignment':return ALIGNMENTS[v]
 return str(v)+('磅' if 'font_size' in p else '倍' if p=='line_spacing' else '字符' if p=='first_line_indent' else '')

def render_academic_templates(model,root):
 def guard(fn):
  try:fn()
  except Exception as exc:model.template_error=public_error(exc)
 with st.expander('单文档规范与模板 · 摘要、关键词、参考文献与表格（v4/v5/v6）'):
  st.caption('只有单文档扩展模式执行章节规则；R38–R41仅在已确认附录/致谢类型按配置执行。旧模板新增属性未启用；缺失字段须明确选默认、人工值或未启用。论文处理在本机；解析只发送已核对的规范摘录。')
  def demo(name):
   if model.load_norm((root/'samples'/name).read_bytes(),name):model.select_norm_segments([s['location'] for s in model.norm_inventory['segments']])
  a,b=st.columns(2)
  a.button('导入单文档规范A',on_click=lambda:guard(lambda:demo('norm15-A.txt')))
  b.button('导入单文档规范B',on_click=lambda:guard(lambda:demo('norm15-B.txt')))
  encoding=st.selectbox('规范TXT编码',['auto','utf-8-sig','utf-16','gb18030'],key='academic-encoding')
  nk='academic-norm-upload-'+str(st.session_state.get('upload_generation',0))
  def upload_norm():
   f=st.session_state.get(nk)
   if f:model.load_norm(f.getvalue(),f.name,encoding=encoding)
  st.file_uploader('上传格式要求TXT/DOCX（与论文分开，最大2MB）',type=['txt','docx'],max_upload_size=2,key=nk,on_change=upload_norm)
  g=model.template_generation
  if model.norm_inventory:
   rows=model.norm_inventory['segments'];st.dataframe(rows,hide_index=True,width='stretch')
   positions=st.multiselect('选择发送的规范来源',options=[x['location'] for x in rows],default=[x['location'] for x in rows],key=f'academic-segments-{g}')
   st.button('使用所选规范摘录',on_click=lambda:guard(lambda:model.select_norm_segments(positions)))
  key=f'academic-text-{g}'
  st.text_area('核对规范摘录（最多12000字符）',value=model.norm_text,key=key,on_change=lambda:model.set_norm_text(st.session_state[key]),height=130)
  a,b=st.columns(2)
  a.button('确认待发送规范摘录',on_click=lambda:guard(model.confirm_norm_text),disabled=not model.norm_text.strip())
  def parse():
   with st.spinner('一次请求：按对象提取并在本机校验…'):model.parse_template()
  b.button('解析单文档要求',on_click=parse,disabled=model.norm_confirmed_hash is None or model.template_draft is not None,type='primary')
  if model.template_receipt:
   r=model.template_receipt;st.caption(('恢复的历史解析，本次请求0次' if r.get('historical_reuse') else '真实API解析记录' if r['kind']=='real_api' else '模拟API解析（自动验收）')+' · '+r['model']+' · '+r['timestamp_utc'])
  ik='academic-template-import-'+str(st.session_state.get('upload_generation',0))
  def imported():
   f=st.session_state.get(ik)
   if f:model.import_template(f.getvalue())
  st.file_uploader('导入JSON模板（v2/v3/v4/v5/v6，最大64KB）',type=['json'],key=ik,on_change=imported)
  if not model.template_import and not model.template_draft:st.button('创建可编辑v4草稿（不调用AI）',on_click=lambda:guard(model.start_academic_template))
  if model.template_import:st.caption('导入历史模板：本次API请求0次。文件所报AI来源只作历史记录，不证明本次实时解析；须核对后应用。')
  if model.template_import and model.template_import['structure_version']<4:
   st.info('旧模板保留R01–R12含义；新增类型/属性全部未启用。升级需明确核对。')
   st.button('保留旧值并升级v4草稿',on_click=lambda:guard(model.start_academic_template))
  elif len(model.template_fields)>26 and (model.template_draft or model.template_import):
   if 'table_content__font_cn' not in model.template_fields:st.button('保留旧值并升级v5表格草稿（新字段未启用）',on_click=lambda:guard(model.upgrade_table_template))
   if not any(n in BACK_FIELDS for n in model.template_fields):st.button('保留旧值并升级v6附录致谢草稿（新字段未启用）',on_click=lambda:guard(model.upgrade_back_template))
   st.info('待编辑草稿尚未改变当前检查。标签与内容分开；未明确加粗的内容保持未启用。')
   if model.template_draft:
    for note in model.template_draft['unsupported']:st.warning(note['location']+' · '+note['quote']+' · '+note['reason'])
   name_key=f'academic-name-{g}'
   st.text_input('自定义模板名称',value=model.template_name,key=name_key,on_change=lambda:setattr(model,'template_name',st.session_state[name_key]))
   a,b=st.columns(2)
   a.button('未提及字段明确沿用演示默认',on_click=lambda:guard(model.academic_defaults))
   b.button('未提及新增字段保持未启用',on_click=lambda:guard(model.academic_disable_missing))
   for kind,title in OBJECTS.items():
    names=[n for n in model.template_fields if obj(n)==kind]
    if not names:continue
    with st.expander(title+' · 值、依据与选择'):
     rows=[]
     for n in names:
      f=model.template_draft.get(n) if model.template_draft else None;s=model.template_import['field_sources'][n] if model.template_import else None
      rows.append({'字段':label(n),'提取/导入':show(n,f['value']) if f else show(n,s and model.template_import['final_values'][n]),'采用':show(n,model.template_values[n]),'选择':model.template_modes[n],'原文':f['quote'] if f else s['quote'] if s else '未提及','来源位置':f['location'] if f else s['location'] if s else '—'})
     st.dataframe(rows,hide_index=True,width='stretch')
     chosen=st.selectbox(title+'编辑字段',names,format_func=label,key=f'academic-field-{g}-{kind}')
     edit_field(model,chosen,g)
   try:
    cfg=model.proposed_template();can=True
    with st.expander('最终完整配置 · 确认前核对',expanded=True):
     st.dataframe([{'对象':OBJECTS[obj(n)],'字段':label(n),'最终值':show(n,v),'来源':KINDS[cfg['field_sources'][n]['kind']]} for n,v in cfg['final_values'].items()],hide_index=True,width='stretch',height=340)
     st.caption('模板v4/v5/v6；附录代码/数据须明确排除；致谢默认未配置；表内文字仅确认范围执行；旧版本缺失字段未启用。R11结构检查固定。间距保留行/磅单位。R22只读，不扩写摘要或补文献。未启用字段不检查。')
   except Exception as exc:can=False;st.info(public_error(exc))
   st.button('确认并应用单文档模板',on_click=model.apply_template,disabled=not can,type='primary')
  if model.template_error:st.error(model.template_error)
  if model.active_template:
   st.success('当前应用：'+model.active_template['name']+' · v'+str(model.active_template['structure_version']))
   if model.active_template['structure_version'] in (4,5,6):
    with st.expander('生效值及逐字段来源'):
     st.dataframe([{'对象':OBJECTS[obj(n)],'属性':label(n),'值':show(n,v),'来源':KINDS[model.active_template['field_sources'][n]['kind']]} for n,v in model.active_template['final_values'].items()],hide_index=True,width='stretch')
   raw=model.template_download()
   if raw:st.download_button('保存已确认JSON模板',raw,file_name='confirmed-template.json',mime='application/json',on_click='ignore')
  else:st.caption('当前为只读学校2015演示配置；只在单文档模式启用已核对的新增属性。')
  st.button('恢复默认学校演示规则',on_click=model.use_default_rules,disabled=model.active_custom_data is None)

def edit_field(model,name,g):
 f=model.template_draft.get(name) if model.template_draft else None
 options=['choose','manual','default']+(['disabled'] if name in EXTRA or name in BACK_FIELDS or name.startswith('table_content__') else [])+(['ai'] if f else [])+(['imported'] if model.template_import else [])
 mk=f'academic-mode-{g}-{name}'
 # Numeric/value edits explicitly change provenance; keep the source widget honest.
 if mk in st.session_state and st.session_state[mk]!=model.template_modes[name]:st.session_state[mk]=model.template_modes[name]
 st.selectbox(label(name)+'来源',options,index=options.index(model.template_modes[name]),format_func=lambda v:{'choose':'未决定','manual':'用户确认值','default':'沿用演示默认','disabled':'未启用','ai':'AI提取值','imported':'导入历史值'}[v],key=mk,on_change=lambda:model.edit_template(name,st.session_state[mk]))
 if model.template_modes[name] in ('choose','default','disabled'):return
 value=model.template_values[name]
 p=(BACK_FIELDS[name] if name in BACK_FIELDS else EXTRA[name])[2] if name in EXTRA or name in BACK_FIELDS else name
 seed=model.academic_values()[name]
 if value is None:value=seed if seed is not None else {'value':0,'unit':'pt'} if p in ('before','after') else False if p.endswith('bold') or p=='enabled' else '宋体' if 'font_cn' in p else 'Times New Roman' if 'font_western' in p else 'left' if p=='alignment' else 1.5 if p=='line_spacing' else 0 if p=='first_line_indent' else 12
 key=f'academic-value-{g}-{name}'
 if isinstance(value,dict):
  a,b=st.columns(2);u=a.selectbox(label(name)+'单位',['pt','lines'],index=['pt','lines'].index(value['unit']),key=key+'-unit');v=b.number_input(label(name)+'数值',min_value=0.,max_value=72. if u=='pt' else 3.,value=float(value['value']),step=.5 if u=='pt' else .25,key=key+'-number')
  if st.button('采用此间距',key=key+'-apply'):model.edit_template(name,'manual',{'value':v,'unit':u},touched=True);st.rerun()
 else:
  choices=list(CN) if 'font_cn' in p else list(WEST) if 'font_western' in p else list(ALIGNMENTS) if p.endswith('alignment') else [1.,1.25,1.5,2.] if p.endswith('line_spacing') else [0,1,2] if p=='first_line_indent' else [False,True] if isinstance(value,bool) else ['A4 portrait'] if p=='paper' else None
  def change():model.edit_template(name,'manual',st.session_state[key],touched=True)
  if choices:st.selectbox(label(name)+'采用值',choices,index=choices.index(value),key=key,on_change=change,format_func=lambda v:show(name,v))
  else:st.number_input(label(name)+'采用值',min_value=10. if p.startswith('margin_') else 8.,max_value=50. if p.startswith('margin_') else 36. if 'title' in obj(name) or obj(name).startswith('heading') else 24.,value=float(value),step=.5,key=key,on_change=change)
  if model.template_modes[name]=='manual' and model.template_values[name] is None and st.button('采用显示的值',key=key+'-adopt'):
   model.edit_template(name,'manual',st.session_state[key],touched=True);st.rerun()

"""Explicit cover fields/section roles and supplemental template; no hidden edits."""
from copy import deepcopy
import json
import streamlit as st
from core.front import FIELDS,ROLES,LABELS
from core.front_template import FIELDS as CONFIG,CN,WEST,ALIGN,loads,school
from .session import public_error

def render_front(model):
 if model.mode!='academic':return
 def guard(fn):
  try:fn()
  except Exception as e:model.error=public_error(e)
 with st.expander('封面、页眉页脚与页码 · 明确确认后检查（可选）',expanded=model.front_enabled):
  st.caption('补充R24–R29，不改变旧模式。封面信息仅在本机，不发送AI；缺少候选不等于缺少实际字段。PAGE只读，字段存在不证明页码准确。')
  key=f'front-enable-{model.task_dir.name}'
  st.checkbox('启用封面与节用途检查',value=model.front_enabled,key=key,on_change=lambda:guard(lambda:model.enable_front(st.session_state[key])))
  if not model.front_enabled:return
  inv=model.front_inventory();d=model.front_draft;token=f'{model.task_dir.name}-{model.current_round}-{model.revision}'
  st.caption('节的XML对象范围不是物理页码；封面表格只检查明确的标题段落，不套R23。已定位封面段落请在分类中核对为其他；不允许与正文/标题或论文内容表格范围重叠。')
  with st.expander('确认封面字段与论文标题',expanded=True):
   opts=inv['cover_objects'];st.dataframe([{'对象':r['id'],'简短文字':r['text'][:55],'标签候选':[FIELDS[x] for x in r['candidates']],'已指定':FIELDS.get(d['objects'].get(r['id']), '未指定'),'特殊结构':r['special'] or ''} for r in opts],hide_index=True,width='stretch',height=220)
   if opts:
    with st.form('front-object-form-'+token):
     obj=st.selectbox('封面对象定位',[r['id'] for r in opts],format_func=lambda k:k+' · '+next(r['text'][:35] for r in opts if r['id']==k),key='front-object-'+token)
     typ=st.selectbox('此对象代表的封面字段',['none',*FIELDS],index=['none',*FIELDS].index(d['objects'].get(obj,'none')),format_func=lambda x:'不指定' if x=='none' else FIELDS[x],key='front-type-'+token+'-'+obj)
     def assign():
      s=deepcopy(model.front_draft)
      if typ=='none':s['objects'].pop(obj,None)
      else:s['objects'][obj]=typ
      model.edit_front(s)
     if st.form_submit_button('应用此封面定位草稿'):guard(assign);st.rerun()
  with st.expander('真实分节、用途与页眉页脚关系',expanded=True):
   st.dataframe([{'节':s['index'],'XML对象范围':str(s['body_objects']),'顶层段落范围':str(s['paragraphs']),'纸张mm':str({k:round(int(v)*25.4/1440,2) if v.isdigit() and k in ('w','h') else v for k,v in s['page'].items()}),'页边距及距离mm':str({k:round(int(v)*25.4/1440,2) if v.isdigit() else v for k,v in s['margins'].items()}),'首页不同':s['first_page_different'],'奇偶不同':s['odd_even_different'],'用途':ROLES[d['section_roles'][str(s['index'])]]} for s in inv['sections']],hide_index=True,width='stretch')
   if inv['sections']:
    sn=st.selectbox('明确选择节编号',[s['index'] for s in inv['sections']],key='front-section-'+token)
    role=st.selectbox('此节的用途',list(ROLES),index=list(ROLES).index(d['section_roles'][str(sn)]),format_func=ROLES.get,key='front-role-'+token+'-'+str(sn))
    def set_role():
     s=deepcopy(model.front_draft);s['section_roles'][str(sn)]=role;model.edit_front(s)
    st.button('应用此节用途草稿',on_click=lambda:guard(set_role))
    sec=next(s for s in inv['sections'] if s['index']==sn)
    st.dataframe([{'故事':k,'链接前节':v.get('linked_previous'),'定义于节':v.get('defined_section'),'普通文字':v.get('ordinary_text'),'复杂对象':v.get('complex_objects'),'域数':len(v.get('fields',[])),'关系提示':v.get('error','')} for k,v in sec['references'].items()],hide_index=True,width='stretch')
    with st.expander('域指令、保存结果与原始节设置（不代表实际页码）'):st.json({'fields':{k:v.get('fields',[]) for k,v in sec['references'].items()},'page_numbering':sec['page_numbering'],'errors':sec['errors']})
  with st.expander('封面与页眉页脚补充模板 · v1（旧模板不自动升级）'):
   if model.workbench['active']:
    st.caption('规则已在统一工作台确认；此处只核对论文对象，不重复配置相同格式。编辑或导入规则请使用上方工作台。')
    from .workbench_ui import rows as rule_rows
    st.dataframe([r for r in rule_rows(model.current_rule_bundle()) if r['模块']==__import__('core.rule_bundle',fromlist=['LABELS']).LABELS['front']],hide_index=True,width='stretch',height=220)
   else:
    st.caption('独立补充模板与原v2–v6正文/章节模板组合，来源及哈希单独记录。标题二号=22pt。未配置字体不继承正文要求。页码位置在学校页19/20存在冲突，保持人工核对。')
    cfg=d['template'];st.dataframe([{'字段':n,'采用值':str(v) if v is not None else '未启用','来源':cfg['sources'][n]['kind'],'依据':cfg['sources'][n]['quote']} for n,v in cfg['values'].items()],hide_index=True,width='stretch',height=240)
    n=st.selectbox('编辑补充字段',list(CONFIG),key='front-config-'+token);v=cfg['values'][n];p=CONFIG[n]
    enabled=st.checkbox('启用此属性',value=v is not None,key='front-prop-enabled-'+token+'-'+n)
    if p in ('font_cn','font_western','alignment','bold'):
     choices=list(CN) if p=='font_cn' else list(WEST) if p=='font_western' else list(ALIGN) if p=='alignment' else [False,True]
     v2=st.selectbox('采用值',choices,index=choices.index(v) if v in choices else 0,key='front-value-'+token+'-'+n)
    else:v2=st.number_input('采用值（mm或pt）',min_value=0. if p=='mm' else 8.,max_value=50. if p=='mm' else 36. if n.startswith('cover') else 24.,step=.5,value=float(v if v is not None else 15 if p=='mm' else 12),key='front-value-'+token+'-'+n)
    def apply_value():
     s=deepcopy(model.front_draft);s['template']['name']='用户确认的封面页眉页脚演示要求';s['template']['values'][n]=v2 if enabled else None;s['template']['sources'][n]={'kind':'user_confirmed' if enabled else 'not_enabled','quote':'','location':None};model.edit_front(s)
    st.button('采用此补充属性',on_click=lambda:guard(apply_value))
    def defaults():
     s=deepcopy(model.front_draft);s['template']=school();model.edit_front(s)
    st.button('恢复学校补充要求（仍须确认对象）',on_click=lambda:guard(defaults))
    up=st.file_uploader('导入封面页眉页脚补充模板JSON',type=['json'],key='front-template-upload-'+model.task_dir.name)
    if st.button('校验并载入补充模板草稿',disabled=up is None):
     def load():
      s=deepcopy(model.front_draft);s['template']=loads(up.getvalue());model.edit_front(s)
     guard(load);st.rerun()
    if model.front_confirmed:st.download_button('保存已确认补充模板JSON',model.front_template_bytes(),file_name='front-supplement.json',mime='application/json',on_click='ignore')
    with st.expander('可选AI解析公开规范摘录（不含封面资料）'):
     sk='front-spec-'+model.task_dir.name
     st.text_area('仅粘贴公开格式规范，最多2000字符',value=model.front_spec,key=sk,on_change=lambda:guard(lambda:model.set_front_spec(st.session_state[sk])))
     ack=st.checkbox('已核对只发送规范摘录，不含论文、个人资料或页眉内容',key='front-ack-'+model.task_dir.name)
     st.button('解析封面页眉页脚要求',disabled=not ack or not model.front_spec or model.front_ai_draft is not None,on_click=lambda:guard(model.parse_front))
     if model.front_ai_draft:
      st.dataframe([{'字段':n,'草稿':str(v)} for n,v in model.front_ai_draft.items()],hide_index=True,width='stretch')
      st.button('将解析草稿载入编辑（缺失属性未启用）',on_click=lambda:guard(model.use_front_ai_draft))
  st.button('已核对封面对象、补充规则与节用途并确认',on_click=lambda:guard(model.confirm_front),type='primary')
  if model.front_confirmed:st.success('封面与节范围已绑定当前文件和规则；继续核对段落分类后检查。')
  st.caption('打印颜色、纸张材质、单/双面、装订仅人工清单。修改只执行勾选属性；共享故事影响未选节时禁止改写，不自动断开链接。')

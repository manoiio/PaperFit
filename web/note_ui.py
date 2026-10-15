"""Explicit paged Word-note scope; never sends note text to a service."""
from copy import deepcopy
import streamlit as st
from core.notes import KINDS,FIELDS,DEFAULT
from .session import public_error

def render_notes(model):
 if model.mode!='academic':return
 def guard(fn):
  try:fn()
  except Exception as e:model.error=public_error(e)
 with st.expander('脚注与尾注范围 · 可选',expanded=model.note_enabled):
  st.caption('R36脚注、R37尾注只检查确认的Word普通注释文字：中文字体、字号、倍数行距。自动编号标记和系统分隔线只读；没有注释不等于缺项。')
  key='note-enable-'+model.task_dir.name
  st.checkbox('启用脚注与尾注检查',value=model.note_enabled,key=key,on_change=lambda:guard(lambda:model.enable_notes(st.session_state[key])))
  if not model.note_enabled:return
  inv=model.note_inventory();d=model.note_draft;token=model.task_dir.name+'-'+str(model.revision)
  for issue in inv['issues']:st.warning(KINDS[issue['kind']]+'关系待复核：'+issue['reason'])
  kind=st.selectbox('注释类型筛选',['all',*KINDS],format_func=lambda x:'全部' if x=='all' else KINDS[x],key='note-kind-'+model.task_dir.name)
  word=st.text_input('注释ID或局部文字筛选',key='note-word-'+model.task_dir.name)
  rows=[r for r in inv['objects'] if (kind=='all' or r['kind']==kind) and (not word or word in r['note_id'] or word in r['preview'])]
  page=st.number_input('注释清单页',min_value=1,max_value=max(1,(len(rows)+19)//20),value=1,key='note-page-'+token+'-'+kind+'-'+word)
  shown=rows[(page-1)*20:page*20]
  st.caption(f"普通注释{len(inv['objects'])}条，筛选{len(rows)}条；草稿明确选择{len(d['objects'])}条。编号是注释ID，不是页码；正文引用位置沿用顶层段落编号。")
  st.dataframe([{'对象':r['key'],'类型':KINDS[r['kind']],'ID':r['note_id'],'短预览':r['preview'],'引用段落':', '.join(str(x['paragraph']) if x['paragraph'] else x['location'] for x in r['references']),'普通段落数':r['paragraphs'],'复杂结构':r['complex'],'原因':r['reason']} for r in shown],hide_index=True,width='stretch',height=240)
  for r in shown:
   if r['complex'] or not r['safe_relationship']:st.warning(f"{KINDS[r['kind']]} ID {r['note_id']}：{r['reason']}。复杂域、链接、公式等不强制统一；只有可证明安全的普通片段可执行。")
  chosen=st.multiselect('明确选择本页注释',[r['key'] for r in shown],default=[r['key'] for r in shown if r['key'] in d['objects']],format_func=lambda x:x+' · '+next(r['preview'][:35] for r in shown if r['key']==x),key='note-selected-'+token+'-'+kind+'-'+word+'-'+str(page))
  def select(ids,replace=False):
   s=deepcopy(d);s['objects']=sorted(set(ids) if replace else set(s['objects'])|set(ids));s['confirmed']=False;model.edit_notes(s)
  def page_selection():select((set(d['objects'])-{r['key'] for r in shown})|set(chosen),True)
  a,b,c=st.columns(3)
  a.button('采用本页明确选择',on_click=lambda:guard(page_selection))
  b.button('选择当前筛选的注释',on_click=lambda:guard(lambda:select([r['key'] for r in rows])),disabled=not rows)
  c.button('清空注释范围',on_click=lambda:guard(lambda:select([],True)))
  st.caption('筛选不等于选中；范围确认不等于授权修正。跨页保留选择，修改草稿后需重新确认和检查。')
  with st.expander('注释要求与补充配置'):
   if model.workbench['active']:
    st.caption('规则已在统一工作台确认；此处只核对论文对象，不重复配置相同格式。编辑或导入规则请使用上方工作台。')
    from .workbench_ui import rows as rule_rows
    st.dataframe([r for r in rule_rows(model.current_rule_bundle()) if r['模块']==__import__('core.rule_bundle',fromlist=['LABELS']).LABELS['notes']],hide_index=True,width='stretch',height=220)
   else:
    values={};sources={}
    for k,label in KINDS.items():
     st.markdown('**'+label+'普通文字**');values[k]={};sources[k]={}
     for p,title in [('font_cn','中文字体'),('font_size','字号（pt）'),('line_multiple','倍数行距')]:
      old=d['template']['values'][k][p];origin=d['template']['sources'][k][p]
      mode=st.selectbox(label+title+'来源',['school_default','user_confirmed','not_enabled'],index=['school_default','user_confirmed','not_enabled'].index(origin),format_func=lambda x:{'school_default':'沿用2015演示材料值','user_confirmed':'用户确认值','not_enabled':'不检查此属性'}[x],key='note-mode-'+token+k+p)
      if mode=='user_confirmed':
       if p=='font_size':v=st.number_input(label+title,min_value=8.,max_value=24.,step=.5,value=float(old or DEFAULT[p]),key='note-value-'+token+k+p)
       else:
        opts=['宋体','黑体','楷体','仿宋'] if p=='font_cn' else [1.,1.25,1.5,2.]
        v=st.selectbox(label+title,opts,index=opts.index(old) if old in opts else opts.index(DEFAULT[p]),key='note-value-'+token+k+p)
      else:v=DEFAULT[p] if mode=='school_default' else None
      values[k][p]=v;sources[k][p]=mode
    def config():
     s=deepcopy(d);s['template'].update(values=values,sources=sources);s['confirmed']=False;model.edit_notes(s)
    st.button('应用注释要求草稿',on_click=lambda:guard(config))
    st.dataframe([{'对象':KINDS[k],'属性':p,'当前采用值':str(d['template']['values'][k][p]),'来源':d['template']['sources'][k][p]} for k in KINDS for p in FIELDS],hide_index=True,width='stretch')
    up=st.file_uploader('导入注释补充配置JSON',type=['json'],key='note-import-'+model.task_dir.name)
    st.button('校验载入注释配置草稿',disabled=up is None,on_click=lambda:guard(lambda:model.import_note_template(up.getvalue())))
    if model.note_confirmed:st.download_button('导出注释补充配置',model.note_template_bytes(),file_name='note-supplement.json',on_click='ignore')
  with st.expander('系统对象与支持边界'):
   st.dataframe(inv['systems'],hide_index=True,width='stretch')
   for limit in inv['limits']:st.caption(limit)
   st.caption('学校依据：项目所附2015材料物理页16允许页末注/篇末注，物理页18要求注释正文小四宋体、1.5倍。只解释到确认的Word脚注/尾注普通文字。')
  st.button('已核对注释范围与要求并确认',on_click=lambda:guard(model.confirm_notes),type='primary')
  if model.note_confirmed:st.success('注释范围与要求已确认。继续核对完整分类并开始检查；尚未执行修正。')

"""Explicit opt-in read-only target inventory and supported internal text capability."""
from copy import deepcopy
import streamlit as st
from .session import public_error

def render_references(model):
 if model.mode!='academic':return
 def guard(fn):
  try:fn()
  except Exception as e:model.error=public_error(e)
 with st.expander('内部书签、超链接与交叉引用 · 可选产品检查',expanded=model.reference_enabled):
  st.caption('R44只读检查内部目标结构，非学校格式要求。目标存在不证明域缓存新鲜、实际页码正确或真实跳转已验收。')
  token=model.task_dir.name;key='reference-enable-'+token
  st.checkbox('启用R44内部引用结构检查',value=model.reference_enabled,key=key,on_change=lambda:guard(lambda:model.enable_references(st.session_state[key])))
  if not model.reference_enabled:return
  d=model.reference_draft;inv=model.reference_inventory()
  flag='reference-text-'+token+'-'+str(model.revision)
  def change():
   s=deepcopy(d);s['template']['internal_text']=st.session_state[flag];s['confirmed']=False;model.edit_references(s)
  st.checkbox('同时允许安全内部链接文字格式检查与选项修正',value=d['template']['internal_text'],key=flag,on_change=lambda:guard(change))
  st.caption('仅确认的正文、参考文献、脚注/尾注普通文字；不开放链接段落属性、R33、目录缓存、表格或页眉页脚文字。未选择修正不会改变文档。')
  st.write(f"书签边界对象 {len(inv['bookmarks'])}；引用位置 {len(inv['references'])}；目标/解析组 {len(inv['groups'])}；非通过组 {sum(g['status']!='pass' for g in inv['groups'])}。数量不相加为独立缺陷数。")
  for issue in inv['issues']:st.warning(issue['reason'])
  kind=st.selectbox('内部引用清单',['引用位置','书签边界','字段指令'],key='reference-kind-'+token)
  state=st.selectbox('内部引用状态',['全部','pass','problem','review'],key='reference-state-'+token)
  word=st.text_input('按目标名称筛选',key='reference-word-'+token)
  rows=inv[{'引用位置':'references','书签边界':'bookmarks','字段指令':'fields'}[kind]]
  rows=[r for r in rows if (state=='全部' or r.get('state')==state) and (not word or word in str(r.get('target',r.get('name',''))))]
  page=st.number_input('内部引用清单页',min_value=1,max_value=max(1,(len(rows)+19)//20),value=1,key='reference-page-'+token+kind+state+word)
  shown=rows[(page-1)*20:page*20]
  st.caption(f'筛选{len(rows)}项，本页{len(shown)}项；位置来自XML，不是实际页面。')
  st.dataframe([{'位置':str(r['location']),'目标':r.get('target',r.get('name')),'类型':r.get('kind','bookmark'),'状态':r.get('state','只读指令'),'原因':r.get('reason',r.get('parse_reason')),'保存结果存在':r.get('cached_result_present'),'指令':r.get('instruction'),'关联故障组':r.get('fault_key')} for r in shown],hide_index=True,width='stretch')
  with st.expander('覆盖及补充配置'):
   st.dataframe(inv['stories'],hide_index=True,width='stretch')
   for limit in inv['limits']:st.caption(limit)
   up=st.file_uploader('导入内部引用补充JSON',type=['json'],key='reference-import-'+token)
   st.button('校验载入内部引用配置草稿',disabled=up is None,on_click=lambda:guard(lambda:model.import_reference_template(up.getvalue())))
   if model.reference_confirmed:st.download_button('导出内部引用补充配置',model.reference_template_bytes(),file_name='internal-reference-supplement.json',on_click='ignore')
  st.button('已核对内部引用检查开关并确认',type='primary',on_click=lambda:guard(model.confirm_references))
  if model.reference_confirmed:st.success('开关已确认；仍需原有正文、参考文献或注释范围确认。R44不执行修正。')

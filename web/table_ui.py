"""Table roles use stable top-level table IDs, independent of paragraph IDs."""
import streamlit as st
from core.table_text import TYPES
from .session import public_error

def render_tables(model):
 if model.mode!='academic':return
 with st.expander('核对表格范围 · 表内文字R23（可选）',expanded=model.table_enabled):
  st.caption('表格独立编号，不属于顶层段落编号。仅明确确认的论文内容表格检查中文字体与普通字号；封面/表单不套正文或表内规则。')
  def enable():
   try:model.set_table_enabled(st.session_state[ek])
   except Exception as exc:model.error=public_error(exc)
  ek=f'table-enabled-{model.task_dir.name}'
  st.checkbox('启用表内普通文字检查',value=model.table_enabled,key=ek,on_change=enable)
  if not model.table_enabled:return
  requirements=model.table_requirements()
  st.caption('当前表内要求：中文字体 '+(requirements['font_cn'] or '未配置')+'；普通字号 '+(str(requirements['font_size'])+'pt' if requirements['font_size'] is not None else '未配置')+'。其余文字槽位与段落属性不套正文规则。')
  if any(v is None for v in requirements.values()):st.warning('当前模板有未启用的表格字段；确认用途不会补学校默认值。旧v2–v4须明确升级v5并选择值；未配置字段不检查，不代表符合。')
  inv=model.table_inventory();rows=inv['tables']
  if inv.get('unlisted_tables'):st.warning('另有'+str(len(inv['unlisted_tables']))+'个包裹/文本框表格不在普通顶层清单；不会自动处理，请人工复核。')
  st.dataframe([{'表格编号':r['index'],'节':r['section'] or '待复核','文档对象位置':r['body_object'],'行/网格列':f"{r['rows']}/{r['columns']}",'合并':r['merged'],'嵌套':r['nested'],'简短内容':r['text'],'核对类型':TYPES[model.table_types[str(r['index'])]]} for r in rows],hide_index=True,width='stretch')
  if rows:
   n=st.selectbox('明确选择表格编号',[r['index'] for r in rows],key=f'table-id-{model.task_dir.name}-{model.current_round}')
   tk=f'table-kind-{model.task_dir.name}-{model.current_round}-{model.revision}-{n}'
   def changed():
    items=dict(model.table_types);items[str(n)]=st.session_state[tk];model.set_table_types(items)
   st.selectbox('此表格的用途',list(TYPES),index=list(TYPES).index(model.table_types[str(n)]),format_func=lambda x:TYPES[x],key=tk,on_change=changed)
  st.divider()
  st.markdown('**表格外侧边框R35与重复表头L04（分别启用）**')
  opts=model.table_layout_options or {'version':1,'outer_edges':False,'headers':{}}
  bk=f'table-edges-{model.task_dir.name}-{model.current_round}-{model.revision}'
  def edge_changed():
   try:model.set_table_layout_options({**opts,'outer_edges':st.session_state[bk]})
   except Exception as exc:model.error=public_error(exc)
  st.checkbox('启用已确认内容表格的左右外侧边框检查',value=opts['outer_edges'],key=bk,on_change=edge_changed)
  st.caption('仅左右外侧；内部竖线、顶底边框保持。重复表头不是续表标题、编号或“（续）”，不代表完成全部续表规范。')
  if rows:
   from .issues import value
   records=model.table_edge_inventory();record=next(x for x in records if x['table']==n)
   st.write(f"表格{n}：实际XML单元格{record['cells']}个；当前重复表头行：{record['current_headers'] or '无'}")
   reasons={side:record[side]['unresolved'] for side in ('left','right') if 'unresolved' in record[side]}
   if reasons:
    if len(reasons)==2 and reasons['left']==reasons['right']:st.warning('左右外侧待复核：'+reasons['left']+'；不可自动修正。')
    else:
     for side,why in reasons.items():st.warning(('左侧' if side=='left' else '右侧')+'待复核：'+why+'；不可自动修正。')
   st.dataframe([{'侧':'左侧' if side=='left' else '右侧','当前证据':value(record[side],'R35'),'可执行性':'待复核' if 'unresolved' in record[side] else '可检查；修正前须明确选择'} for side in ('left','right')],hide_index=True,width='stretch')
   with st.expander('边框原始来源与影响单元格'):st.json(record)
   if model.table_types[str(n)]=='content':
    hn=st.number_input('从首行开始的连续表头行数（0为不提出辅助）',min_value=0,max_value=max(0,rows[[r['index'] for r in rows].index(n)]['rows']-1),value=opts['headers'].get(str(n),0),step=1,key=f'table-header-count-{model.task_dir.name}-{model.current_round}-{n}-{model.revision}')
    if hn:st.dataframe(model.table_header_preview(n,int(hn)),hide_index=True,width='stretch')
    st.caption('数值输入尚未应用；点击保存草稿后旧检查、选择和下载失效，仍需确认范围。')
    if st.button('已核对这些表头行，保存为辅助草稿'):
     headers=dict(opts['headers'])
     if hn:headers[str(n)]=int(hn)
     else:headers.pop(str(n),None)
     model.set_table_layout_options({**opts,'headers':headers});st.rerun()
    st.caption('仅保存草稿，不修改DOCX。确认表格及段落范围并检查后，在“分页辅助”明确选择L04生成新副本。跨边界合并、嵌套、修订等仍会阻止。')
  if model.table_layout_options:
   st.download_button('下载表格边框/表头补充配置',model.export_table_options(),'table-layout-options.json','application/json')
  imported=st.file_uploader('载入本文件的表格补充配置JSON',type=['json'],key=f'table-options-import-{model.task_dir.name}')
  if imported and st.button('核对哈希并载入表格补充草稿'):
   try:model.import_table_options(imported.getvalue());st.rerun()
   except Exception as exc:st.error(public_error(exc))
  def confirm():
   try:model.confirm_tables()
   except Exception as exc:model.error=public_error(exc)
  st.button('已核对表格用途并确认范围',on_click=confirm)
  st.caption('确认后仍须核对段落分类并检查。改变输入、规则或用途会使旧检查和下载失效。嵌套、条件样式及特殊文字可能待复核，不因确认绕过保护。')
  if model.table_confirmed:st.success('表格范围已确认；绑定当前文件与规则。')

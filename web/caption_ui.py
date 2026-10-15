"""Paged explicit caption scope and independent position transaction controls."""
from copy import deepcopy
import streamlit as st
from core.captions import ROLES,LIMITS
from .session import public_error

def order_text(order):return ' → '.join({'figure':'图片','table':'表格','caption':'题注'}.get(x,x) for x in order)
def object_text(oid):return ('图片段'+oid[8:]) if oid.startswith('image:p:') else ('表格'+oid[6:]) if oid.startswith('table:') else oid
ORDER={'correct_adjacent':'正确紧邻','reverse_adjacent':'反向紧邻','separated':'隔有其他对象','unconfirmed':'关联未确认'}

def render_captions(model):
 if model.mode!='academic':return
 def guard(fn):
  try:fn()
  except Exception as e:model.error=public_error(e)
 with st.expander('题注编号、章节与图表关联 · 可选',expanded=model.caption_enabled):
  st.caption('R42编号只读，R43检查XML结构位置；L05位置纠正需单独选择执行。位置正确与L01/L02属性不代表实际同页。先核对下方完整段落分类，再确认这里的题注范围。')
  key='caption-enable-'+model.task_dir.name
  st.checkbox('启用题注编号与位置核对',value=model.caption_enabled,key=key,on_change=lambda:guard(lambda:model.enable_captions(st.session_state[key])))
  if not model.caption_enabled:return
  d=model.caption_draft;inv=model.caption_inventory();token=model.task_dir.name+'-'+str(model.revision)
  with st.expander('章节与章号核对',expanded=True):
   st.caption('仅已分类为一级标题的对象。显示章号来源；自动编号不能推算时可人工指定，不用标题排列位置代替章号。')
   heads=[{'段落':h['paragraph'],'标题':h['text'],'程序读取章号':h['number'],'依据':h['reason'],'人工确认章号':d['chapter_map'].get(str(h['paragraph']))} for h in inv['chapters']]
   edited=st.data_editor(heads,disabled=['段落','标题','程序读取章号','依据'],column_config={'人工确认章号':st.column_config.NumberColumn(min_value=1,max_value=999,step=1)},hide_index=True,width='stretch',key='caption-chapters-'+token)
   def chapters():
    s=deepcopy(d);s['chapter_map']={str(r['段落']):int(r['人工确认章号']) for r in edited if r['人工确认章号'] is not None};s['confirmed']=False;model.edit_captions(s)
   st.button('采用章号核对草稿',on_click=lambda:guard(chapters),disabled=not heads)
  search=st.text_input('题注编号或局部文字筛选',key='caption-search-'+model.task_dir.name)
  rows=[r for r in inv['captions'] if not search or search in r['text'] or search==str(r['paragraph'])]
  page=st.number_input('题注范围页',min_value=1,max_value=max(1,(len(rows)+19)//20),value=1,key='caption-page-'+token+'-'+search)
  shown=rows[(page-1)*20:page*20];opts=['未关联']+[o['id'] for o in inv['objects']]
  st.caption(f"确认分类题注{len(inv['captions'])}项；筛选{len(rows)}项；当前草稿明确列出{len(d['captions'])}项。筛选不代表授权。")
  data=[{'段落':r['paragraph'],'题注':r['text'],'结构位置':r['body_object'],'相邻对象建议':'、'.join(r['nearby']) or '无唯一证据','用途':ROLES[d['captions'].get(str(r['paragraph']),'pending')],'关联':d['associations'].get(str(r['paragraph']),'未关联')} for r in shown]
  edited_rows=st.data_editor(data,disabled=['段落','题注','结构位置','相邻对象建议'],column_config={'用途':st.column_config.SelectboxColumn(options=list(ROLES.values())),'关联':st.column_config.SelectboxColumn(options=opts)},hide_index=True,width='stretch',key='caption-editor-'+token+'-'+search+'-'+str(page))
  def selected_page(use_suggestions=False):
   s=deepcopy(d)
   for r in edited_rows:
    n=str(r['段落']);role=next(k for k,v in ROLES.items() if v==r['用途']);s['captions'][n]='normal' if use_suggestions else role
    nearby=next(x['nearby'] for x in shown if x['paragraph']==r['段落']);oid=nearby[0] if use_suggestions and len(nearby)==1 else r['关联']
    if oid!='未关联':s['associations'][n]=oid
    else:s['associations'].pop(n,None)
   s['confirmed']=False;model.edit_captions(s)
  a,b=st.columns(2)
  a.button('采用本页题注编辑',on_click=lambda:guard(selected_page),disabled=not shown)
  b.button('明确采用本页普通题注与唯一相邻建议',on_click=lambda:guard(lambda:selected_page(True)),disabled=not shown,help='这是范围与关联草稿，不会执行移动或修正。续表、分图等请逐项改用途，不应批量采用。')
  st.dataframe([{'对象':o['id'],'XML位置':o['body_object'],'概况':o['summary']} for o in inv['objects']],hide_index=True,width='stretch',height=170)
  def completeness():
   s=deepcopy(d);s.update(complete=st.session_state['caption-complete-'+token],chapters_complete=st.session_state['caption-headings-complete-'+token],confirmed=False);model.edit_captions(s)
  with st.form('caption-completeness-'+token):
   st.checkbox('我已核对本次图表题注范围完整',value=d['complete'],key='caption-complete-'+token)
   st.checkbox('我已核对所属章及相关一级标题范围完整',value=d['chapters_complete'],key='caption-headings-complete-'+token)
   st.form_submit_button('采用完整范围声明',on_click=lambda:guard(completeness))
  with st.expander('题注补充配置与边界'):
   for line in LIMITS:st.caption(line)
   st.caption('此能力单独启用；旧模式、模板与CLI不会静默增加R42/R43。补充配置不包含论文题注或章号。')
   up=st.file_uploader('载入题注补充配置JSON',type=['json'],key='caption-config-'+model.task_dir.name)
   st.button('校验题注补充配置',disabled=up is None,on_click=lambda:guard(lambda:model.import_caption_template(up.getvalue())))
   if model.caption_confirmed:st.download_button('下载题注补充配置',model.caption_template_bytes(),file_name='caption-supplement.json',on_click='ignore')
  st.button('已核对题注、章号及关联并确认',on_click=lambda:guard(model.confirm_captions),type='primary')
  if model.caption_confirmed:st.success('题注范围已确认；接着核对完整分类并检查。尚未授权任何位置移动。')

def render_caption_report(model):
 report=model.result['after'] if model.result else model.report
 if not report or not report.get('captions'):return
 with st.expander('题注编号、位置与实际分页 · 分别核对',expanded=True):
  a=report['captions'];
  if a.get('unconfirmed_captions'):st.warning('已分类但未纳入本次题注确认：'+', '.join(map(str,a['unconfirmed_captions']))+'；范围完整声明不能代替这些对象的核对。')
  st.write(f"编号只读问题 {a['summary']['numbering_problems'] if a['enabled']['numbering'] else '未启用'} · 结构位置问题 {a['summary']['position_problems'] if a['enabled']['position'] else '未启用'} · 复杂对象/范围待复核 {a['summary']['complex_or_scope_reviews']} · 实际分页未核对");st.caption(a['actual_pagination']);st.caption('完整序列检查已具备范围依据' if a['scope_complete'] else '仅部分范围或存在未解析形式，未判定完整序列')
  word=st.text_input('题注结果段落或编号筛选',key='caption-report-search-'+str(model.report_revision))
  rows=[r for r in a['numbers'] if not word or word in r['text'] or word==str(r['paragraph'])]
  page=st.number_input('题注核对结果页',min_value=1,max_value=max(1,(len(rows)+19)//20),key='caption-result-page-'+str(model.report_revision)+'-'+word)
  shown=rows[(page-1)*20:page*20]
  st.dataframe([{'段落':r['paragraph'],'原题注':r['text'],'解析编号':r['parsed']['raw_number'] if r['parsed'] else '不可确定','标题':r['parsed']['title'] if r['parsed'] else '待复核','所属章':r['confirmed_chapter'],'章号依据':r['chapter_evidence'],'状态':{'pass':'符合','problem':'发现问题','review':'待复核'}[r['status']] if a['enabled']['numbering'] else 'R42未启用','原因':'；'.join(r['reasons'])} for r in shown],hide_index=True,width='stretch')
  ids={r['paragraph'] for r in shown}
  st.dataframe([{'题注段落':p['paragraph'],'图表对象':object_text(p.get('object','未确认')),'结构位置':ORDER[p['order']],'状态':{'pass':'位置正确','problem':'反向紧邻','review':'待复核'}[p['status']] if a['enabled']['position'] else 'R43未启用','可单独纠正':p['movable'],'原因':p['reason'],'实际同页':p['actual_pages']} for p in a['positions'] if p['paragraph'] in ids],hide_index=True,width='stretch')
  for s in (a['sequences'] if a['enabled']['numbering'] else []):st.caption(('图' if s['type']=='figure' else '表')+str(s['chapter'])+'章序列 '+str(s['observed'])+'：'+s['reason'])
  if any(p['movable'] for p in a['positions']) and not model.result:
   if st.button('进入题注位置纠正操作'):model.operation='pagination';st.rerun()

def render_caption_move(model):
 if model.mode!='academic' or not model.report or not model.report.get('captions'):return
 with st.expander('L05 · 题注位置纠正（独立一轮）',expanded=True):
  st.caption(f'输入：第{model.current_round}轮（0为原稿）。只移动选定题注，保留原分页属性；下一轮重新提供L01/L02，不自动设置。')
  plans=model.report['captions']['positions'];safe=[p for p in plans if p['movable']]
  if not safe:st.info('当前输入无可安全纠正的反向紧邻对象；查看关联及复杂结构原因。');return
  lookup={p['key']:p for p in safe}
  keys=st.multiselect('明确选择要移动的题注',list(lookup),format_func=lambda k:f"段落{lookup[k]['paragraph']} → {object_text(lookup[k]['object'])} · {order_text(lookup[k]['current_order'])} 改为 {order_text(lookup[k]['target_order'])}",key='caption-move-keys-'+model.task_dir.name+'-'+str(model.report_revision))
  st.dataframe([{'唯一移动题注':lookup[k]['paragraph'],'关联对象':object_text(lookup[k]['object']),'当前顺序':order_text(lookup[k]['current_order']),'目标顺序':order_text(lookup[k]['target_order']),'范围':'段落、目录、封面、材料排除和引文按XML对象身份重绑；旧计划、选择与预览失效'} for k in keys],hide_index=True,width='stretch')
  confirmed=st.checkbox('已核对全部选中位置变化，授权仅移动这些题注',key='caption-move-consent-'+str(model.report_revision)+'-'+str(keys))
  if st.button('生成题注位置纠正副本',disabled=not keys or not confirmed,type='primary'):
   if model.generate_caption_move(keys):st.rerun()
   else:st.error(model.error)
  if model.result and model.result.get('kind')=='caption_position':st.info('副本已生成。请下载复查，或点击“以本轮修正版开始下一轮”后再处理剩余对象；这里的输入仍是本轮原输入。')

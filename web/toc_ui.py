"""Bulk explicit TOC scope; pageable read-only saved-result correspondence."""
from copy import deepcopy
import streamlit as st
from core.toc import ROLES
from core.toc_template import FIELDS,CN,ALIGN,LINES,loads,school
from .session import public_error

def render_toc(model):
 if model.mode!='academic':return
 def guard(fn):
  try:fn()
  except Exception as e:model.error=public_error(e)
 with st.expander('目录范围、层级与补充格式 · 可选',expanded=model.toc_enabled):
  st.caption('R30目录标题、R31一级条目、R32二/三级条目。手工普通文字可选择修正；自动TOC缓存只读。保存页码不是实际页码。')
  ek='toc-enable-'+model.task_dir.name
  st.checkbox('启用目录格式与对应核对',value=model.toc_enabled,key=ek,on_change=lambda:guard(lambda:model.enable_toc(st.session_state[ek])))
  if not model.toc_enabled:return
  inv=model.toc_inventory();d=model.toc_draft;token=model.task_dir.name+'-'+str(model.current_round)+'-'+str(model.revision)
  conflicts=[{'目录对象':r['id'],'原顶层段号':r['locator']['paragraph'],'当前分类':model.paragraph_types[str(r['locator']['paragraph'])],'影响':'须人工调整分类草稿并重新确认，否则阻止检查；不静默移出正文/标题'} for r in inv['objects'] if r['id'] in d['objects'] and 'paragraph' in r['locator'] and model.paragraph_types.get(str(r['locator']['paragraph'])) not in ('other','pending')]
  if conflicts:
   st.warning(f'目录草稿与现有正文/标题等分类重叠{len(conflicts)}个对象；请在下方批量分类中核对，不会自动调整。')
   st.dataframe(conflicts[:20],hide_index=True,width='stretch')
  st.caption(inv['indexing']+'。建议尚未应用；核对后批量指定目录对象。目录对象不可同时确认为正文标题；冲突会阻止检查，须明确调整原分类。')
  candidates_only=st.checkbox('仅查看目录候选',value=True,key='toc-candidates-'+model.task_dir.name)
  rows=[r for r in inv['objects'] if not candidates_only or r['candidate'] or r['automatic'] or r['broken'] or r['id'] in d['objects']]
  page=st.number_input('目录清单页',min_value=1,max_value=max(1,(len(rows)+19)//20),value=1,key='toc-list-page-'+str(len(rows))+'-'+model.task_dir.name)
  shown=rows[(page-1)*20:page*20]
  st.caption(f'筛选共{len(rows)}个对象；每页20个，不改变检查范围。')
  st.dataframe([{'对象':r['id'],'原顶层段号':str(r['locator'].get('paragraph','—')),'短文本':r['text'],'结构':r['structure'],'建议':ROLES.get(r['candidate'],'无'),'当前草稿':ROLES.get(d['objects'].get(r['id']),'未指定'),'理由':r['reason'],'特殊结构':r['special'] or ''} for r in shown],hide_index=True,width='stretch',height=250)
  with st.expander('批量设置目录类型（明确选中的对象）',expanded=True):
   ids=st.multiselect('明确选择目录对象',[r['id'] for r in shown],format_func=lambda k:k+' · '+next(r['text'][:45] for r in inv['objects'] if r['id']==k),key='toc-objects-'+token+'-'+str(page)+'-'+str(candidates_only))
   target=st.selectbox('所选目录对象类型',['none',*ROLES],format_func=lambda x:'移出目录范围' if x=='none' else ROLES[x],key='toc-role-'+token)
   st.caption(f'将修改{len(ids)}个明确对象；不会自动改变正文分类。')
   def batch():
    s=deepcopy(model.toc_draft)
    for k in ids:
     if target=='none':s['objects'].pop(k,None)
     else:s['objects'][k]=target
    model.edit_toc(s)
   st.button('应用所选目录类型草稿',disabled=not ids,on_click=lambda:guard(batch))
   if st.button('载入全部候选为待核对草稿'):
    s=deepcopy(d);s['objects']={r['id']:r['candidate'] or 'unknown' for r in inv['objects'] if r['candidate'] or r['automatic']};guard(lambda:model.edit_toc(s));st.rerun()
   st.caption('载入候选不是确认；未知级别仍待复核，不会自动修正。')
  levels=st.multiselect('已核对目录覆盖层级',[1,2,3],default=d['covered_levels'],key='toc-levels-'+token)
  complete=st.checkbox('已核对整份目录范围（否则按部分范围）',value=d['complete'],key='toc-complete-'+token)
  hc=st.checkbox('已核对正文标题完整范围（否则不判整篇缺项）',value=d['headings_complete'],key='toc-headings-'+token)
  def coverage():
   s=deepcopy(model.toc_draft);s.update(covered_levels=levels,complete=complete,headings_complete=hc);model.edit_toc(s)
  st.button('应用覆盖范围草稿',on_click=lambda:guard(coverage))
  with st.expander('目录完整配置、字段来源与模板保存/重载'):
   if model.workbench['active']:
    st.caption('规则已在统一工作台确认；此处只核对论文对象，不重复配置相同格式。编辑或导入规则请使用上方工作台。')
    from .workbench_ui import rows as rule_rows
    st.dataframe([r for r in rule_rows(model.current_rule_bundle()) if r['模块']==__import__('core.rule_bundle',fromlist=['LABELS']).LABELS['toc']],hide_index=True,width='stretch',height=220)
   else:
    cfg=d['template'];st.dataframe([{'对象属性':n,'采用值':str(v) if v is not None else '未启用','来源':cfg['sources'][n]['kind'],'原文依据':cfg['sources'][n]['quote']} for n,v in cfg['values'].items()],hide_index=True,width='stretch')
    n=st.selectbox('编辑目录属性',list(FIELDS),key='toc-field-'+token);prop=FIELDS[n];v=cfg['values'][n]
    enabled=st.checkbox('启用所选目录属性',value=v is not None,key='toc-prop-'+token+'-'+n)
    if prop in ('font_cn','alignment','line_multiple'):
     opts=list(CN if prop=='font_cn' else ALIGN if prop=='alignment' else LINES)
     v2=st.selectbox('目录属性采用值',opts,index=opts.index(v) if v in opts else 0,key='toc-value-'+token+'-'+n)
    else:v2=st.number_input('目录字号pt',min_value=8.,max_value=36.,step=.5,value=float(v or 12),key='toc-value-'+token+'-'+n)
    def edit():
     s=deepcopy(d);s['template']['name']='用户确认的目录演示要求';s['template']['values'][n]=v2 if enabled else None;s['template']['sources'][n]={'kind':'user_confirmed' if enabled else 'not_enabled','quote':'','location':None};model.edit_toc(s)
    st.button('采用目录属性草稿',on_click=lambda:guard(edit))
    up=st.file_uploader('导入目录补充模板JSON',type=['json'],key='toc-upload-'+model.task_dir.name)
    def load():
     s=deepcopy(d);s['template']=loads(up.getvalue());model.edit_toc(s)
    st.button('校验载入目录模板草稿',disabled=up is None,on_click=lambda:guard(load))
    if model.toc_confirmed:st.download_button('保存目录补充模板JSON',model.toc_template_bytes(),file_name='toc-supplement.json',mime='application/json',on_click='ignore')
  st.button('已核对目录范围、级别与配置并确认',on_click=lambda:guard(model.confirm_toc),type='primary')
  if model.toc_confirmed:st.success('目录范围已确认；继续核对完整段落分类并检查。实际页码未核对。')
  for obj in inv['unlisted_structures']:st.warning(obj['reason'])
  for note in inv['limits']:st.caption(note)

def render_toc_report(report):
 data=report.get('toc')
 if not data:return
 with st.expander('目录与正文并排对应 · 缓存/实际页码分开',expanded=True):
  st.warning('实际页码未核对。保存数字及PAGEREF只作为证据，预览物理页顺序不能证明印刷页码正确；必要时在Word人工更新，更新后重新上传。')
  st.caption(data['scope_state']+f"；明确对应风险{data['risk_count']}项，对应待复核{data['review_count']}项。与格式问题独立统计。")
  status=st.selectbox('对应核对状态',['all','pass','risk','review'],format_func=lambda x:{'all':'全部','pass':'文字/级别对应明确','risk':'明确对应风险','review':'待复核'}[x],key='toc-match-filter-'+report['input_sha256'])
  word=st.text_input('筛选目录或候选标题关键词',key='toc-match-word-'+report['input_sha256'])
  rows=[r for r in data['rows'] if (status=='all' or r['status']==status) and (not word or word in str(r))]
  page=st.number_input('对应表页',min_value=1,max_value=max(1,(len(rows)+19)//20),value=1,key='toc-match-page-'+report['input_sha256']+'-'+str(len(rows)))
  st.caption(f'筛选{len(rows)}条，当前{(page-1)*20+1 if rows else 0}–{min(page*20,len(rows))}；完整下载保留全部记录。')
  st.dataframe([{'目录对象':r['id'],'目录原文':r['entry']['original'],'层级':ROLES[r['level']],'保存页码':r['entry']['saved_page'] or '未可靠拆分','候选已确认标题（含附录/致谢）':'；'.join(f"段{h['paragraph']}（{h['level']}级） {h['text']}" for h in r['candidates']),'依据':r['evidence'],'状态':{'pass':'文字/级别一致','risk':'对应风险','review':'待复核'}[r['status']],'原因':r['reason'],'编号边界':r['numbering_state']} for r in rows[(page-1)*20:page*20]],hide_index=True,width='stretch')
  if data['missing_candidates']:st.warning('存在完整范围内待核对的缺项候选；不自动生成条目。');st.dataframe(data['missing_candidates'],hide_index=True)
  if data['hierarchy_notes']:st.dataframe(data['hierarchy_notes'],hide_index=True)
  with st.expander('只读TOC/PAGEREF域与结构证据'):st.json(data['inventory']['fields'],expanded=False)

"""One primary rule entry; object confirmation deliberately remains outside this panel."""
from copy import deepcopy
import json
import streamlit as st
from core import rule_bundle as rb
from core.norms import marked_text
from .session import public_error
from .rule_fields_ui import group,label,value_control,DECISIONS,REASONS,friendly_error

ORIGINS={'ai_extracted':'AI提取（可能为历史来源）','user_confirmed':'用户确认值','default_inherited':'沿用演示默认','school_demo':'2015演示原文','school_default':'2015注释演示原文','legacy_fixed':'旧版本固定要求','not_enabled':'不检查'}

def text(v):
 if v is None:return '不检查 / 未配置'
 if isinstance(v,dict):return str(v.get('value'))+('行' if v.get('unit')=='lines' else '磅')
 if isinstance(v,bool):return '是' if v else '否'
 return {'left':'居左','center':'居中','right':'居右','both':'两端对齐','A4 portrait':'A4竖向'}.get(v,str(v))
def rows(bundle):
 return [{'模块':rb.LABELS[m],'字段':rb.FIELDS[m][n][1],'字段ID':n,'最终采用':text(v),'来源':ORIGINS[bundle['provenance'][m][n]['kind']],'依据':bundle['provenance'][m][n]['quote'],'位置':bundle['provenance'][m][n]['location'] or '—'} for m,c in bundle['modules'].items() if c for n,v in rb.flat(m,c).items()]
def render_workbench(model,root):
 w=model.workbench
 task_key=model.task_dir.name if model.task_dir else 'no-document'
 def guard(fn):
  try:fn();model.template_error=None
  except Exception as e:model.template_error=public_error(e)
 with st.expander('统一规范工作台 · 一次解析、整体确认、规则包',expanded=True):
  st.caption('单文档主要规则入口。论文处理在本机；本规范入口仅点击解析时发送已核对的公开规范摘录；智能处理中的可选结构识别另行明确发送有限论文摘录。规则包跨文档复用要求，不含论文；项目包用于继续工作，包含论文。')
  try:current=model.current_rule_bundle()
  except Exception as e:st.error(public_error(e));return
  summary=[]
  for m,c in current['modules'].items():
   enabled=sum(v is not None for v in rb.flat(m,c).values()) if c else 0
   ready=(model.classification_confirmed is not None if m=='main' else getattr(model,{'front':'front_confirmed','toc':'toc_confirmed','notes':'note_confirmed'}[m]) is not None)
   summary.append({'模块':rb.LABELS[m],'已配置属性':enabled,'状态':'未配置' if c is None else '未启用任何属性' if not enabled else '可参与检查（已确认对象）' if ready else '已配置 · 等待对象确认'})
  with st.expander('模块配置、范围状态与支持边界'):
   st.dataframe(summary,hide_index=True,width='stretch')
   st.caption('R11及原有西文检查保持；自动目录与实际页码仍只读。旧单模块缺少内容须明确保留或不检查。')
  st.write('当前生效：**'+current['name']+'**')
  st.caption('规则不确认论文对象，不选择修正或执行排版辅助。')
  with st.expander('当前生效配置及来源（完整）'):st.dataframe(rows(current),hide_index=True,width='stretch',height=280)
  g=str(w['generation'])+'-'+task_key;key='wb-text-'+g
  with st.expander('公开规范导入与AI解析（仅明确点击才发送）',expanded=st.session_state.get('workspace-rule-entry')=='AI解析公开规范'):
   enc=st.selectbox('统一规范TXT编码',['auto','utf-8-sig','utf-16','gb18030'],key='wb-encoding')
   up=st.file_uploader('导入公开格式要求TXT/DOCX（非待检查论文，2MB）',type=['txt','docx'],max_upload_size=2,key='wb-norm-upload')
   if st.button('读取规范并预览',disabled=up is None):
    if model.load_norm(up.getvalue(),up.name,encoding=enc):
     # Reading is local only. Selecting/excerpt confirmation is separate.
     model.workbench_text('');st.rerun()
   if model.norm_inventory:
    segs=model.norm_inventory['segments'];st.dataframe(segs,hide_index=True,width='stretch',height=180)
    locs=st.multiselect('明确选择要交给AI的规范来源',[s['location'] for s in segs],key='wb-norm-locs')
    def selected():
     model.select_norm_segments(locs);model.workbench_text(model.norm_text,model.norm_segments)
    st.button('采用所选规范摘录（未发送）',disabled=not locs,on_click=lambda:guard(selected))
    for note in model.norm_inventory['notes']:st.caption(note)
   if st.button('载入公开组合演示规范（未发送）'):
    model.workbench_text((root/'samples/phase24/unified-spec.txt').read_text());st.rerun()
   st.text_area('待发送公开规范摘录（最多12000字符，可编辑）',value=w['text'],height=145,key=key,on_change=lambda:guard(lambda:model.workbench_text(st.session_state[key])))
   a,b=st.columns(2)
   a.button('核对并确认待发送摘录',disabled=not w['text'].strip(),on_click=lambda:guard(model.confirm_workbench_excerpt))
   def parse():
    with st.spinner('正在执行一次请求并校验四个模块…'):guard(model.parse_workbench)
   b.button('一次解析全部规范',disabled=w['confirmed_excerpt'] is None or w['parse_attempted'],on_click=parse,type='primary')
   if w['parse_attempted'] and not w['receipt'] and not model.diagnostic_store()['current']:
    st.warning('本次解析未形成可用草稿，当前生效配置保持；不会重运行或自动重试。')
    st.button('明确允许再次请求此摘录',on_click=lambda:w.update(parse_attempted=False))
   if w['confirmed_excerpt']:
    with st.expander('实际待发送摘录及准确来源标记'):st.text(marked_text(w['segments']))
   if w['receipt']:st.caption(('历史解析记录，当前动作0次API请求' if w.get('historical',False) else '真实统一解析' if w['receipt']['kind']=='real_api' else '模拟解析（仅测试）')+' · '+w['receipt']['model']+' · '+w['receipt']['timestamp_utc'])
  from .diagnostic_ui import render_diagnostics
  render_diagnostics(model,guard)
  with st.expander('导入已有规则包或兼容模板',expanded=w['draft'] is None,key='wb-import-panel-'+g):
   imp=st.file_uploader('导入完整规则包 / 旧v2–v6模板 / 独立补充JSON',type=['json'],max_upload_size=1,key='wb-import')
   st.button('校验导入为待确认草稿',disabled=imp is None,on_click=lambda:guard(lambda:model.import_rule_bundle(imp.getvalue())))
  if w['draft'] is None:st.button('从当前配置建立编辑草稿（不调用AI）',on_click=lambda:guard(model.start_workbench_draft))
  if w['draft']:
   d=w['draft'];st.info('这份草稿已应用；当前生效值见上方。再次编辑后仍需重新确认。' if w['origin']=='applied' else '待确认草稿尚未生效。导入AI来源仅为历史记录；不证明本次实时解析。' if d['imported'] else '待确认草稿尚未改变当前检查使用的规则。')
   nk='wb-name-'+g;st.text_input('规则包名称',value=d['name'],key=nk,on_change=lambda:d.update(name=st.session_state[nk]))
   pending=[{'模块':rb.LABELS[m],'字段':group(m,n)+' · '+label(m,n),'当前值':text(rb.flat(m,d['baseline']['modules'][m])[n]) if d['baseline']['modules'][m] else '未配置'} for m,fs in d['fields'].items() for n,f in fs.items() if f['mode']=='choose']
   if pending:
    st.warning(f'仍有 {len(pending)} 个未决定字段，尚不能整体应用；请逐项核对或明确采用下方策略。')
    with st.expander(f'未提及 / 待决定 {len(pending)} 个字段 · 明确批量策略',expanded=False):
     st.caption('该策略只作用于下表所列未决定字段；冲突字段可手动取舍或不检查，不会被当作AI提取。')
     st.dataframe(pending,hide_index=True,width='stretch',height=160)
     with st.container(key='wb-missing-policy-'+g):
      strategy=st.radio('这些字段的处理',['keep','disabled'],format_func=lambda p:'保留当前已生效值（未配置仍未配置）' if p=='keep' else '不检查这些属性',horizontal=True,key='wb-policy-'+g)
      ack=st.checkbox('已核对批量影响字段，采用以上策略',key='wb-policy-ack-'+g+'-'+rb.digest(pending)[:12])
      if st.button('采用未决定字段策略'):
       guard(lambda:model.workbench_policy(strategy,acknowledged=ack));st.rerun()
   a,b=st.columns(2)
   m=a.selectbox('查看与编辑模块',list(rb.MODULES),format_func=rb.LABELS.get,key='wb-module-'+g)
   fs=d['fields'][m]
   groups=list(dict.fromkeys(group(m,n) for n in fs))
   obj=b.selectbox('选择格式对象',groups,key='wb-object-'+g+'-'+m)
   for issue in d['issues'][m]:
    st.warning(REASONS.get(issue['reason'],issue['reason'])+' · '+issue['quote']+'；受影响：'+('、'.join(group(m,n)+' '+label(m,n) for n in issue['fields']) or '只读提示'))
   show_missing=st.checkbox('编辑未提及或保留字段',key='wb-show-missing-'+g+'-'+m)
   baseline=rb.flat(m,d['baseline']['modules'][m]) if d['baseline']['modules'][m] else {n:None for n in fs}
   active=rb.flat(m,current['modules'][m]) if current['modules'][m] else {n:None for n in fs}
   opts=[n for n,f in fs.items() if group(m,n)==obj and (show_missing or baseline[n] is not None or f['candidate'] or f['mode']=='manual')]
   from .object_rules_ui import render_object_editor
   dirty_key,editor_epoch=render_object_editor(model,m,obj,opts,g,active,baseline,current,text,ORIGINS)
   can=False
   try:
    proposed=model.proposed_rule_bundle();can=True
    diffs=[]
    for module,c in proposed['modules'].items():
     if c is None:continue
     now=rb.flat(module,current['modules'][module]) if current['modules'][module] else {n:None for n in rb.FIELDS[module]}
     for n,v in rb.flat(module,c).items():
      if v!=now[n] or proposed['provenance'][module][n]!=(current['provenance'][module][n] if current['provenance'][module] else rb.EMPTY):diffs.append({'模块':rb.LABELS[module],'对象':group(module,n),'属性':label(module,n),'当前 → 拟应用':text(now[n])+' → '+text(v),'最终来源':ORIGINS[proposed['provenance'][module][n]['kind']]})
    st.markdown('**整体差异 · '+str(len(diffs))+'项**');st.dataframe(diffs,hide_index=True,width='stretch',height=220)
    with st.expander('拟应用最终完整配置（包括未启用）'):st.dataframe(rows(proposed),hide_index=True,width='stretch',height=320)
   except Exception as e:st.warning('尚不能应用：'+friendly_error(public_error(e)))
   ack=st.checkbox('已核对整体差异与最终配置；仅应用规则，论文范围必须另行确认',key='wb-apply-ack-'+g+'-'+rb.digest({'draft':d,'rules':model.rules_hash,'editor_epoch':editor_epoch})[:20])
   st.button('核对并应用整份规则',disabled=not can or not ack or w['origin']=='applied' or bool(st.session_state[dirty_key]),on_click=lambda:guard(lambda:model.apply_workbench(acknowledged=True)),type='primary')
  if model.template_error:st.error(friendly_error(model.template_error))
  if st.button('准备完整规则包（不包含论文）'):guard(lambda:st.session_state.update(wb_rule_download=model.rule_bundle_download()))
  # Revalidate against current state on every explicit preparation; no stale stored download.
  prepared=st.session_state.get('wb_rule_download')
  if prepared:
   try:
    if prepared==model.rule_bundle_download():st.download_button('下载完整规则包JSON（跨文档复用）',prepared,file_name='confirmed-rule-bundle.json',mime='application/json',on_click='ignore')
    else:st.session_state.pop('wb_rule_download',None)
   except Exception:st.session_state.pop('wb_rule_download',None)
  st.button('恢复默认学校演示规则（全部模块）',on_click=model.use_default_rules)
  if st.checkbox('显示兼容模板高级入口',key='wb-legacy-entry'):
   st.caption('兼容模板入口与工作台共用生效配置；补充对象区显示当前规则并保留范围确认，避免重复编辑。')
   from .academic_ui import render_academic_templates
   if current['modules']['main']['disabled_fields']:st.info('当前有明确不检查的兼容字段，请在统一工作台编辑；避免将内部承载值误作生效要求。旧模板仍可在上方导入。')
   else:render_academic_templates(model,root)

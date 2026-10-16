"""Paginated untrusted-text diagnostics and explicit local repair forms."""
from copy import deepcopy
import json
import streamlit as st
from core import spec_diagnostics as sd,rule_bundle as rb

def render_diagnostics(model,guard):
 store=model.diagnostic_store();r=store['current']
 with st.expander('解析诊断与本地修复 · 不调用API',expanded=r is not None):
  st.caption('诊断不是生效规则。来源修复、提示取舍和手动值都会留下用户确认记录；只有全量校验后才转入原有差异及应用流程。')
  if st.button('载入合成失败夹具（0次API，替换规范草稿）'):
   guard(model.load_synthetic_diagnostic);st.rerun()
  up=st.file_uploader('导入诊断JSON（须先确认同哈希规范，最大1MB）',type=['json'],max_upload_size=1,key='diag-import')
  st.button('核对并导入历史诊断',disabled=up is None,on_click=lambda:guard(lambda:model.import_diagnostic(up.getvalue())))
  if r:
   a=model.diagnostic_analysis();g=rb.digest(r)[:14];s=a['summary']
   st.info(('合成/历史草稿，当前操作0次请求；' if model.workbench.get('historical') or r['kind']=='synthetic' else '本次请求有回执；')+'原始响应 '+('整体拒绝' if a['status']=='rejected' else '字段校验失败/隔离' if not r['edits'] and a['status']!='validated' else '本地修复后全量校验通过' if r['edits'] and a['status']=='validated' else '原始字段校验通过' if a['status']=='validated' else '本地修复仍有未决项'))
   st.caption('合格候选 '+str(s.get('qualified',0))+' · 隔离字段 '+str(s.get('isolated',0))+' · 人工决定 '+str(s.get('user_confirmed',0))+' · 未提及 '+str(s.get('missing',0))+' · 独立诊断 '+str(s['errors']))
   with st.expander('不可变原始响应与规范快照（不可信文本）'):
    st.caption('输入SHA256 '+r['input_sha256']+'；结束状态 '+str(r['finish_reason']))
    st.text('\n'.join(s['location']+' '+s['text'] for s in r['segments']));st.code(r['content'] or '响应未保留：超限、敏感内容或请求失败',language='text')
   if a['status']=='rejected':st.error(a['reason']+' 请明确发起新请求或采用已有规则；本地修复入口禁用。')
   else:
    modules=st.multiselect('诊断模块',list(rb.MODULES),default=list(rb.MODULES),format_func=rb.LABELS.get,key='diag-modules')
    states=st.multiselect('候选状态',['isolated','qualified','user_confirmed','missing'],default=['isolated','qualified','user_confirmed'],key='diag-states')
    rows=[{'字段':short,'状态':f['state'],'错误代码':'、'.join(f['codes']),'原始值':json.dumps(f['raw'],ensure_ascii=False),'最终候选':json.dumps(f['candidate'],ensure_ascii=False)} for short,f in a['fields'].items() if short.split('.')[0] in modules and f['state'] in states]
    pages=max(1,(len(rows)+19)//20);page=st.number_input('诊断对象页码',1,pages,1,key='diag-page-'+str(pages));start=(page-1)*20
    st.caption(f'筛选{len(rows)}字段；当前{start+1 if rows else 0}–{min(start+20,len(rows))}；完整诊断仍保留。')
    st.dataframe(rows[start:start+20],hide_index=True,width='stretch',height=220)
    paths=list(dict.fromkeys(x['path'] for x in a['records']))
    if paths:
     chosen=st.selectbox('查看诊断对象全部原因',paths,key='diag-detail')
     st.dataframe([{k:(json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v) for k,v in x.items()} for x in a['records'] if x['path']==chosen],hide_index=True,width='stretch')
    suggested=[{'字段':m+'.fields.'+n,'原标记':f['suggestion']['from'],'建议标记':f['suggestion']['to'],'原文':f['suggestion']['text']} for short,f in a['fields'].items() if f['suggestion'] and not any(e['path']==short.split('.')[0]+'.fields.'+short.split('.')[1] for e in r['edits']) for m,n in [short.split('.')]]
    if suggested:
     with st.expander('唯一来源映射建议（不会自动补前缀）',expanded=True):
      st.dataframe(suggested,hide_index=True,width='stretch',height=180)
      with st.container(key='diag-batch-'+g):
       all_=st.checkbox('明确选择上表全部唯一来源映射（含义/冲突仍逐项校验）')
       selected=st.multiselect('或明确选择部分字段',[x['字段'] for x in suggested])
       ack=st.checkbox('已逐项核对原标记、建议标记及连续原文')
       if st.button('采用明确选择的来源映射'):
        guard(lambda:model.repair_unique_sources([x['字段'] for x in suggested] if all_ else selected,acknowledged=ack));st.rerun()
    targets=[k for k,f in a['fields'].items() if f['raw'] is not None or f['state']=='isolated']
    if targets:
     with st.expander('逐字段修复原句 / 手动取舍 / 不检查'):
      short=st.selectbox('待修复字段',targets,key='diag-field');m,n=short.split('.');f=a['fields'][short];c=f['candidate'] if isinstance(f['candidate'],dict) else {}
      with st.container(key='diag-field-form-'+g+'-'+short):
       prefix='diag-edit-'+g+'-'+short
       action=st.radio('字段修复方式',['candidate','manual','disabled'],format_func=lambda x:{'candidate':'修复依据（仍校验全部规范）','manual':'手动指定值（不宣称原文精确支持）','disabled':'明确不检查这个问题字段'}[x],key=prefix+'-action')
       locs=[s['location'] for s in r['segments']];loc=st.selectbox('从真实规范选择来源',locs,index=locs.index(c.get('location')) if c.get('location') in locs else 0,key=prefix+'-location');st.caption(next(s['text'] for s in r['segments'] if s['location']==loc))
       quote=st.text_input('连续原句（不能概括或拼接）',value=str(c.get('quote','')),key=prefix+'-quote')
       val=st.text_input('最终值JSON或字体枚举',value=json.dumps(c.get('value'),ensure_ascii=False),key=prefix+'-value')
       unit=st.text_input('单位（不会自动换算）',value=str(c.get('unit',rb.FIELDS[m][n][2])),key=prefix+'-unit')
       reason=st.text_input('本地决定原因（必填）',key=prefix+'-reason')
       if st.button('记录字段修复并重新校验'):
        def repair():
         from core.rule_config import strict_json
         try:v=strict_json(val)
         except Exception:v=val
         data={'value':v,'unit':unit,'quote':quote,'location':loc,'support':'supported'} if action=='candidate' else v if action=='manual' else None
         model.repair_diagnostic(m+'.fields.'+n,action,data,reason)
        guard(repair);st.rerun()
    if a['issues']:
     with st.expander('提示关联修复（原始提示始终保留）',expanded=True):
      path=st.selectbox('待核对提示',list(a['issues']),key='diag-issue');issue=a['issues'][path];m=path.split('.')[0]
      st.text(json.dumps(issue['original'],ensure_ascii=False));st.caption('声明影响：'+('、'.join(issue['affected']) or '无明确字段；请核对原始结构'))
      with st.container(key='diag-issue-form-'+g+'-'+path):
       prefix='diag-edit-'+g+'-'+path
       choice=st.radio('关联决定',['retain','change','note'],format_func=lambda x:{'retain':'保留阻止关系（关联字段须手动取舍或不检查）','change':'修正关联字段','note':'与执行字段无关的只读说明'}[x],key=prefix+'-action')
       fields=st.multiselect('明确关联字段',list(rb.FIELDS[m]),default=issue['effective'].get('fields',[]) if isinstance(issue['effective'],dict) and isinstance(issue['effective'].get('fields'),list) and all(n in rb.FIELDS[m] for n in issue['effective']['fields']) else [],key=prefix+'-fields')
       locs=[s['location'] for s in r['segments']];savedloc=issue['effective'].get('location') if isinstance(issue['effective'],dict) else None
       loc=st.selectbox('提示来源位置',locs,index=locs.index(savedloc) if savedloc in locs else 0,key=prefix+'-location');quote=st.text_input('提示的连续原句',value=str(issue['effective'].get('quote','')) if isinstance(issue['effective'],dict) else '',key=prefix+'-quote')
       reasons=sorted(rb.main.REASONS);oldreason=issue['effective'].get('reason') if isinstance(issue['effective'],dict) else None;why=st.selectbox('提示原因',reasons,index=reasons.index(oldreason) if oldreason in reasons else 0,key=prefix+'-why');reason=st.text_input('用户决定与理由（必填）',key=prefix+'-reason')
       if st.button('记录提示决定并重新校验'):
        guard(lambda:model.repair_diagnostic(path,'issue',{'fields':[] if choice=='note' else issue['original'].get('fields',[]) if choice=='retain' else fields,'quote':quote,'location':loc,'reason':why},reason));st.rerun()
    st.caption('普通未提及策略不能处理隔离字段；必须在这里明确取舍。已修复字段最终标为用户确认，原AI内容保留历史。')
    st.button('全量重新校验诊断（0次API）',on_click=lambda:guard(model.diagnostic_analysis))
    ack=st.checkbox('已核对全部候选、诊断及本地决定；转入规则草稿仍需整体差异确认',key='diag-adopt-ack-'+g)
    st.button('核对并转入原规则草稿',disabled=a['status']!='validated' or not ack,on_click=lambda:guard(lambda:model.use_diagnostic_draft(acknowledged=True)))
   with st.expander('本地修复记录（原响应不改写）'):st.json(r['edits'])
  if r or store['history']:
   st.download_button('下载详细诊断JSON（含公开规范与不可信响应）',model.diagnostic_download(),file_name='spec-diagnostics.json',mime='application/json',on_click='ignore')
  if store['history']:
   st.caption('历史诊断 '+str(len(store['history']))+' 份，仅可查看/导出，不能绑定新摘录执行。')
   with st.expander('历史规范及原响应摘要'):
    for old in store['history']:st.text(old['kind']+' · '+old['input_sha256']+' · '+str(len(old['edits']))+'项修复')
   ack=st.checkbox('已另存所需诊断，明确清理这几份历史（不改当前诊断）',key='diag-clear-ack')
   st.button('清理已另存历史诊断',disabled=not ack,on_click=lambda:store.update(history=[]))

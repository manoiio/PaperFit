"""Paged local candidate decisions; selection never follows filtering implicitly."""
from copy import deepcopy
import json
import streamlit as st
from core.citations import template
from .session import public_error
from .presentation import fmt,LABELS as STATES
LABELS={'citation':'确认引文','excluded':'排除（数组/其他标记）','pending':'待确认'}
def render_citations(model):
 if model.mode!='academic':return
 def guard(fn):
  try:fn()
  except Exception as e:model.error=public_error(e)
 with st.expander('正文引文范围与用途 · 可选',expanded=model.citation_enabled):
  st.caption('R33只改所选普通文字引文的上标；R34对应与首次顺序只读。不核验文献真实性，不改编号。先核对下方正文和参考文献类型，再启用或同步扫描范围。')
  k='citation-enable-'+model.task_dir.name
  st.checkbox('启用正文引文检查',value=model.citation_enabled,key=k,on_change=lambda:guard(lambda:model.enable_citations(st.session_state[k])))
  if not model.citation_enabled:return
  d=model.citation_draft;inv=model.citation_inventory();token=model.task_dir.name+'-'+str(model.revision)
  body=sorted(int(n) for n,t in model.paragraph_types.items() if t=='body')
  st.caption('当前扫描正文段：'+', '.join(map(str,d['scan']))+'。段落编号是顶层XML编号，不是页码。')
  def rescan():
   s=deepcopy(d);s['scan']=body;s['objects']={};s.update(complete=False,references_complete=False);model.edit_citations(s)
  st.button('同步当前正文范围并清空旧引文草稿',on_click=lambda:guard(rescan))
  scope=st.multiselect('引文扫描正文段落（明确选取）',body,default=[n for n in d['scan'] if n in body],key='citation-scan-'+token)
  def scan():
   s=deepcopy(d);s['scan']=scope;s['objects']={};s.update(complete=False,references_complete=False);model.edit_citations(s)
  st.button('应用扫描范围草稿',on_click=lambda:guard(scan))
  word=st.text_input('引文局部关键词筛选',key='citation-word-'+model.task_dir.name)
  role=st.selectbox('引文用途筛选',['all',*LABELS],format_func=lambda v:'全部' if v=='all' else LABELS[v],key='citation-filter-'+model.task_dir.name)
  rows=[r for r in inv['objects'] if (not word or word in r['context'] or word in r['id']) and (role=='all' or d['objects'].get(r['id'],'pending')==role)]
  page=st.number_input('引文候选页',min_value=1,max_value=max(1,(len(rows)+19)//20),value=1,key='citation-page-'+token+'-'+role+'-'+word+'-'+str(len(rows)))
  shown=rows[(page-1)*20:page*20]
  st.caption(f'筛选{len(rows)}项；每页20；确认用途不等于授权修正。筛选不会自动选中。')
  st.dataframe([{'对象':r['id'],'段落':r['paragraph'],'字符范围':str(r['start'])+'–'+str(r['end']),'局部上下文':r['context'],'原始引文':r['text'],'编号':str(r['numbers']),'上标状态':fmt(r['vertical'],'R33'),'结构':r['structure'],'安全修正':r['fixable'],'用途':LABELS[d['objects'].get(r['id'],'pending')],'原因':r['reason']} for r in shown],hide_index=True,width='stretch',height=260)
  ids=st.multiselect('明确选择引文候选',[r['id'] for r in shown],format_func=lambda x:x+' · '+next(r['context'] for r in shown if r['id']==x),key='citation-ids-'+token+'-'+str(page)+'-'+role+'-'+word)
  target=st.selectbox('所选候选用途',list(LABELS),format_func=lambda x:LABELS[x],key='citation-target-'+token)
  def decide():
   s=deepcopy(d)
   for oid in ids:s['objects'][oid]=target
   model.edit_citations(s)
  st.button('应用所选引文用途草稿',disabled=not ids,on_click=lambda:guard(decide))
  st.caption('批量确认只作用于上方明确选中的稳定字符对象；数组标记请设为排除。组合/区间/全角编号只读。')
  complete=st.checkbox('已核对全部正文引文及排除项（否则为部分范围）',value=d['complete'],key='citation-full-'+token)
  refs=st.checkbox('已核对全部参考文献条目范围（否则不判全文缺失）',value=d['references_complete'],key='citation-refs-'+token)
  sup=st.checkbox('检查引文上标R33',value=d['template']['superscript'],key='citation-sup-'+token)
  rel=st.checkbox('检查引文对应及首次顺序R34',value=d['template']['correspondence'],key='citation-rel-'+token)
  def coverage():
   s=deepcopy(d);s.update(complete=complete,references_complete=refs);s['template'].update(superscript=sup,correspondence=rel);model.edit_citations(s)
  st.button('采用引文完整性声明与配置草稿',on_click=lambda:guard(coverage))
  with st.expander('引文补充模板保存/载入与支持范围'):
   up=st.file_uploader('导入引文补充配置JSON',type=['json'],key='citation-config-'+model.task_dir.name)
   def load():
    if len(up.getvalue())>16000:raise ValueError('配置过大')
    s=deepcopy(d);s['template']=template(json.loads(up.getvalue()));model.edit_citations(s)
   st.button('校验载入引文配置草稿',disabled=up is None,on_click=lambda:guard(load))
   if model.citation_confirmed:st.download_button('保存引文补充配置',model.citation_template_bytes(),file_name='citation-supplement.json',on_click='ignore')
   for note in inv['limits']:st.caption(note)
  st.button('已核对引文范围与用途并确认',on_click=lambda:guard(model.confirm_citations),type='primary')
  if model.citation_confirmed:st.success('引文用途已确认；继续核对完整分类并开始检查。确认尚未执行修正。')

def render_citation_report(report):
 c=report.get('citations')
 if not c:return
 with st.expander('正文引文与参考文献对应 · 只读',expanded=True):
  st.caption(c['scope_state']+'。'+c['r22_link'])
  if not c['enabled']['superscript']:st.info('R33未启用：上标未检查，数字0不代表通过。')
  if not c['enabled']['correspondence']:st.info('R34未启用：对应与首次顺序未检查。')
  sm=c['summary'];st.caption(f"上标问题{sm['superscript_problems']} · 对应问题{sm['correspondence_problems']} · 首次顺序问题{sm['order_problems']} · 引文相关待复核记录{sm['review_records']}（是总检查记录的子集，不另相加）")
  status=st.selectbox('引文对应状态',['all','pass','problem','review'],format_func=lambda x:{'all':'全部','pass':'唯一对应','problem':'完整范围内未找到','review':'待复核'}[x],key='citation-status-'+report['input_sha256'])
  number=st.text_input('引文编号筛选（精确数字，可留空）',key='citation-report-word-'+report['input_sha256'])
  paragraph=st.text_input('引文段落筛选（精确编号，可留空）',key='citation-report-paragraph-'+report['input_sha256'])
  rows=[r for r in c['rows'] if (status=='all' or status==r['status']) and (not number or number.strip() in [str(n) for n in r['numbers']]) and (not paragraph or paragraph.strip()==str(r['paragraph']))]
  p=st.number_input('引文对应页',min_value=1,max_value=max(1,(len(rows)+19)//20),value=1,key='citation-report-page-'+report['input_sha256']+'-'+str(len(rows)))
  st.caption(f'筛选{len(rows)}条；当前页{p}；完整报告保留全部。首次编号顺序：'+str(c['order']))
  st.dataframe([{'引文对象':r['id'],'原文':r['text'],'段落':r['paragraph'],'编号':str(r['numbers']),'参考文献位置':'、'.join(str(x['paragraph']) for x in r['references']) or '未找到唯一条目','条目短预览':'；'.join(x['preview'] for x in r['references']),'状态':STATES[r['status']],'原因':r['relation']} for r in rows[(p-1)*20:p*20]],hide_index=True,width='stretch')
  st.info(c['unreferenced_state']+'：'+str([r['number'] for r in c['unreferenced']]))
  if c['undecided']:st.warning(f"尚有{len(c['undecided'])}个用途待确认；部分确认不等于全文对应验收。")
  st.caption('编号对应不证明文献真实、引用准确或全文排版合格。合法引文上标仍由通用正文的特殊run保护保留，相关未检查范围会继续显示。')

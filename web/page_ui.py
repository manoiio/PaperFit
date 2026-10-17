"""Two existing entries, one optional assembly policy and the same page transaction."""
from copy import deepcopy
import streamlit as st
from core.page_policy import DEFAULT,validate
from core.package import Package,DemoError
from core import page_layout
from .session import public_error

def options(model,task,*,local=False):
 saved=getattr(model,'page_layout_draft',None) or {};portable=model.current_rule_bundle().get('assembly') if model.inventory else None
 seed=(saved.get('policy') if saved.get('enabled') or saved.get('explicit') else None) or portable or DEFAULT;key='assembly-'+task+('-local' if local else '-smart')
 def chosen():
  if model.inventory:
   if model.page_layout_draft is None:model.page_layout_draft={}
   model.page_layout_draft['explicit']=True
  st.session_state[key+'-preset-changed']=True
 if not saved.get('explicit') and portable:st.session_state[key+'-choice']='complete'
 choice=st.selectbox('本次整理方案',['current','complete','complete_chapters'],format_func={'current':'常规格式整理（保持原有页码与编号）','complete':'完整整理：格式＋安全编号同步＋页码方案','complete_chapters':'完整整理：格式、编号同步、分区页码和章节页脚'}.get,index=1 if saved.get('enabled') or portable else 0,key=key+'-choice',on_change=chosen)
 enabled=choice in ('complete','complete_chapters')
 if st.session_state.pop(key+'-preset-changed',False) and choice=='complete_chapters':
  seed={**DEFAULT,'pages':'front-body','footer':'chapter','dynamic':True}
  for suffix,value in (('pages','front-body'),('footer','chapter'),('roman','lowerRoman'),('front-start',1),('start',1),('restart',False),('align','center')):st.session_state[key+'-'+suffix]=value
 p=deepcopy(seed)
 if enabled:
  a,b=st.columns(2)
  p['pages']=a.selectbox('页码方案',['front-body','keep','chapter-footers'],format_func={'front-body':'封面无页码，前置罗马，正文重启','keep':'保持原有页码','chapter-footers':'仅章节页脚，保持已有编号方案'}.get,index=['front-body','keep','chapter-footers'].index(seed['pages']) if portable or saved.get('enabled') else 0,key=key+'-pages')
  p['footer']=b.selectbox('正文页脚',['page','chapter','text'],format_func={'page':'页码','chapter':'章节名称＋页码','text':'普通文字＋页码'}.get,index=['page','chapter','text'].index(seed['footer']),key=key+'-footer')
  p['dynamic']=True  # Meaning of this explicitly named preset; local advanced may turn it off.
  with st.expander('页码方案细节与保持区域'):
   p['roman']=st.selectbox('前置页码',['lowerRoman','upperRoman'],format_func={'lowerRoman':'小写罗马 i、ii','upperRoman':'大写罗马 I、II'}.get,index=0 if seed['roman']=='lowerRoman' else 1,key=key+'-roman')
   p['front_start']=int(st.number_input('前置起始显示页码数值',min_value=1,max_value=9999,value=seed['front_start'],key=key+'-front-start'))
   p['body_start']=int(st.number_input('正文起始显示页码',min_value=1,max_value=9999,value=seed['body_start'],key=key+'-start'))
   p['chapter_restart']=st.checkbox('每章重新编号（否则后续章节连续）',value=seed['chapter_restart'],key=key+'-restart')
   p['alignment']=st.selectbox('页脚对齐',['center','right'],format_func={'center':'居中','right':'居右'}.get,index=0 if seed['alignment']=='center' else 1,key=key+'-align')
   if p['footer']=='text':p['text']=st.text_input('页脚普通文字',value=seed['text'],max_chars=80,key=key+'-text')
   if local:p['dynamic']=st.checkbox('按本次方案同步安全编号与纯文本引用',value=seed['dynamic'] if saved.get('enabled') or portable else True,key=key+'-dynamic')
   st.caption('这是可选产品方案，不是学校官方唯一解释。新增分节可能改变分页；不刷新目录或REF/PAGEREF。')
  st.caption(('页脚居中。' if p['alignment']=='center' else '页脚居右。')+'点击开始授权：先整理格式，再同步可证明完整的安全编号组，最后生成PAGE及章节页脚；复杂组保留，不自动切换输入。')
 if model.inventory:
  new={'explicit':bool((getattr(model,'page_layout_draft',None) or {}).get('explicit',False)),'enabled':enabled,'policy':validate(p),'input_sha256':model.inventory['input_sha256'],'regions':deepcopy(saved.get('regions',[])) if saved.get('input_sha256')==model.inventory['input_sha256'] else []}
  if new!=saved and (enabled or new['explicit'] or saved):model.page_layout_draft=new
 return validate(p) if enabled else None

def render_local(model):
 with st.expander('分节页码与章节页脚 · 本地零API'):
  st.caption('这里配置当前文件的明确边界；查看和保存草稿不执行。先确认分类及检查，再预演/采用。')
  if not model.inventory:return
  try:
   p=options(model,model.task_dir.name,local=True)
   if not p:return
   draft=model.page_layout_draft
   if st.button('依据已确认分类准备分区草稿',key='pages-prepare'):
    if not model.classification_confirmed:raise DemoError('请先确认当前分类和范围')
    from .assembly_session import regions_from
    draft['regions']=regions_from(model,model.classification_confirmed['paragraph_types'],p);st.rerun()
   if draft['regions']:
    rows=st.data_editor(draft['regions'],key='pages-regions-'+model.task_dir.name,num_rows='dynamic',hide_index=True,column_config={'start':st.column_config.NumberColumn('起点段落',min_value=1,step=1),'role':st.column_config.SelectboxColumn('用途',options=['cover','front','body','keep']),'format':st.column_config.SelectboxColumn('页码格式',options=['decimal','lowerRoman','upperRoman','keep']),'restart':st.column_config.NumberColumn('重启值（空值为连续）',min_value=1,step=1),'footer':st.column_config.SelectboxColumn('页脚内容',options=['page','chapter','text']),'text':'页脚文字/已确认章节名','alignment':st.column_config.SelectboxColumn('对齐',options=['center','right'])},width='stretch')
    if st.button('保存分区草稿',key='pages-save'):
     draft['regions']=page_layout.regions_validate(Package(model.input_path),rows);st.success('已保存分区草稿，尚未执行。')
    st.caption('keep区域保持原有页码/页脚；分区起点是XML段落，不是物理页码。')
   bulk=st.session_state.setdefault('pages-bulk-'+model.task_dir.name,{})
   ackbulk=st.checkbox('按当前明确范围批量整理：格式、安全编号同步和本页页码方案；原稿保留',key='pages-bulk-ack-'+str(draft))
   if st.button('执行当前完整方案（本地零API）',disabled=not ackbulk,key='pages-bulk',type='primary'):
    from .assembly_session import execute_local
    execute_local(model,bulk,acknowledged=True);st.rerun()
   state=st.session_state.setdefault('pages-preview-'+model.task_dir.name,{})
   from .page_session import preview,adopt
   from .dynamic_session import valid,cancel
   if st.button('预演当前分节页码方案',key='pages-preview',disabled=not model.classification_confirmed or not draft['regions']):
    preview(model,state,p,draft['regions']);st.rerun()
   if state.get('result') and not state.get('adopted'):
    r=valid(model,state);st.write('已生成真实副本，尚未采用；'+str(len(r['changes']))+'项结构变化。')
    st.dataframe(r['page_layout']['plan']['records'],hide_index=True,width='stretch')
    ack=st.checkbox('已核对分区、保持区域及结构变化；采用此页码副本',key='pages-ack-'+state['binding'])
    if st.button('确认采用页码副本',disabled=not ack,type='primary',key='pages-adopt'):adopt(model,state);st.rerun()
    if st.button('取消页码预演',key='pages-cancel'):cancel(model,state);st.rerun()
   elif state.get('adopted'):st.success('已采用第'+str(state['adopted'])+'轮；当前输入未自动切换。')
  except Exception as exc:st.warning(public_error(exc))

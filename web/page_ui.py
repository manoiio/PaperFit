"""Two existing entries, one optional assembly policy and the same page transaction."""
from copy import deepcopy
import streamlit as st
from core.page_policy import DEFAULT,validate
from core.package import Package,DemoError
from core import page_layout
from .session import public_error

def legacy_options(model,task,*,local=False):
 saved=getattr(model,'page_layout_draft',None) or {};portable=model.current_rule_bundle().get('assembly') if model.inventory else None
 seed=(saved.get('policy') if saved.get('enabled') or saved.get('explicit') else None) or portable or DEFAULT;key='assembly-'+task+('-local' if local else '-smart')
 def chosen():
  if model.inventory:
   if model.page_layout_draft is None:model.page_layout_draft={}
   model.page_layout_draft['explicit']=True
  st.session_state[key+'-preset-changed']=True
 if not saved.get('explicit') and portable:st.session_state[key+'-choice']='complete_safe' if portable.get('version')==3 else 'complete'
 choice=st.selectbox('本次整理方案',['current','complete_safe','complete_safe_chapters','complete','complete_chapters'],format_func={'current':'常规格式整理（保持原有页码与编号）','complete_safe':'完整整理：格式、图表适配、相邻辅助、编号、页码和目录更新','complete_safe_chapters':'完整整理：安全图表与分页辅助＋分区页码和章节页脚','complete':'旧版完整整理：格式、编号同步、页码和目录更新','complete_chapters':'旧版完整整理：格式、编号、分区页码和章节页脚'}.get,index=(1 if seed.get('version')==3 else 3) if saved.get('enabled') or portable else 0,key=key+'-choice',on_change=chosen)
 enabled=choice in ('complete','complete_chapters','complete_safe','complete_safe_chapters')
 if st.session_state.pop(key+'-preset-changed',False) and choice in ('complete_chapters','complete_safe_chapters'):
  seed={**DEFAULT,'pages':'front-body','footer':'chapter','dynamic':True}
  for suffix,value in (('pages','front-body'),('footer','chapter'),('roman','lowerRoman'),('front-start',1),('start',1),('restart',False),('align','center')):st.session_state[key+'-'+suffix]=value
 p=deepcopy(seed)
 if enabled and choice.startswith('complete_safe'):
  p.update(version=3,auxiliaries='safe-layout-v1',targets=deepcopy(seed.get('targets',['cover','front','body'])))
 elif p.get('version')==3:
  p.pop('auxiliaries');p['version']=2
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
   st.caption('这是可选产品方案，不是学校官方唯一解释。新增分节可能改变分页；可选本机Word仅更新已验证的目录/REF/PAGEREF，不批量刷新其他域。')
  st.caption(('页脚居中。' if p['alignment']=='center' else '页脚居右。')+'点击开始授权：先整理格式，再同步可证明完整的安全编号组，最后生成PAGE及章节页脚，并在本机Word更新安全目录/引用；复杂组保留，不自动切换输入。')
 if enabled and choice.startswith('complete_safe'):st.caption('新版明确授权：安全题注位置纠正；仅缩小超宽固定内容表格及关联内嵌图片；唯一相邻属性和有据连续表头。未知、受保护和需改为固定列宽的对象保持。所有辅助完成后才由Word更新目录/引用。')
 model.field_updates_enabled=bool(enabled and saved.get('word_updates',True))
 if enabled:st.caption('本次完整整理还将使用本机Word更新安全自动目录和REF/PAGEREF，并复查回填文件；失败时保留已验证排版副本。')
 if model.inventory:
  new={'explicit':bool((getattr(model,'page_layout_draft',None) or {}).get('explicit',False)),'enabled':enabled,'policy':validate(p),'input_sha256':model.inventory['input_sha256'],'regions':deepcopy(saved.get('regions',[])) if saved.get('input_sha256')==model.inventory['input_sha256'] else [],**{k:saved[k] for k in ('toc_appearance','word_updates','smart_defaults','toc_policy') if k in saved}}
  if new!=saved and (enabled or new['explicit'] or saved):model.page_layout_draft=new
 return validate(p) if enabled else None

def smart_seed(model):
 """Old saved policies are intent, never an invitation to upgrade them."""
 saved=getattr(model,'page_layout_draft',None) or {}
 portable=model.current_rule_bundle().get('assembly') if model.inventory else None
 if saved:return deepcopy(saved)
 restored=bool(model.history) or (getattr(model,'workbench',None) or {}).get('origin')=='restored'
 if portable:return {'enabled':True,'explicit':False,'policy':deepcopy(portable),'toc_appearance':'preserve'}
 if restored:return {'enabled':False,'explicit':True,'policy':deepcopy(DEFAULT),'toc_appearance':'preserve'}
 return {'enabled':True,'explicit':False,'policy':{**DEFAULT,'version':3,'targets':['cover','front','body'],'auxiliaries':'safe-layout-v1','dynamic':True,'pages':'front-body'},'toc_appearance':'reference','smart_defaults':1,'toc_policy':deepcopy(__import__('core.toc_targets',fromlist=['DEFAULT']).DEFAULT)}

def word_seed(model,saved):
 # Old v1/v2 carriers cannot prove a grant for the later Word updater.
 if 'word_updates' in saved:return saved['word_updates']
 return saved['policy'].get('version')==3 or any(h.get('result',{}).get('kind')=='field_update' for h in model.history)

def options(model,task,*,local=False):
 if local:return legacy_options(model,task,local=True)
 saved=smart_seed(model);seed=saved['policy'];key='assembly-'+task+'-smart-v55'
 def changed():st.session_state[key+'-changed']=True
 with st.expander('调整处理内容'):
  if not saved.get('smart_defaults'):
   if st.checkbox('本任务采用新版智能缺省核对（保留已保存规则与关闭决定）',value=False,key=key+'-defaults',on_change=changed):saved['smart_defaults']=1
  else:st.caption('普通图题、表题缺省居中；新增内部目标与题注结构核对。已保存要求及人工关闭优先。')
  only=st.checkbox('仅整理文字格式',value=not saved['enabled'],key=key+'-only',on_change=changed)
  p=deepcopy(seed)
  enabled=not only
  if enabled:
   aids=st.checkbox('安全图表、分页相邻与编号同步',value=bool(seed.get('dynamic') or seed.get('version')==3),key=key+'-aids',on_change=changed)
   # Merely displaying an old strategy preserves its original operation set.
   if st.session_state.get(key+'-aids')!=bool(seed.get('dynamic') or seed.get('version')==3):
    if aids:p.update(version=3,auxiliaries='safe-layout-v1',targets=deepcopy(seed.get('targets',['cover','front','body'])),dynamic=True)
    else:
     p.pop('auxiliaries',None);p.update(version=2,targets=deepcopy(seed.get('targets',['cover','front','body'])),dynamic=False)
   pages=st.checkbox('设置分区页码与页脚',value=seed['pages']!='keep',key=key+'-page-enabled',on_change=changed)
   if pages:
    p['pages']=st.selectbox('页码安排',['front-body','chapter-footers'],index=0 if seed['pages']!='chapter-footers' else 1,format_func={'front-body':'封面无页码，前置罗马，正文重新编号','chapter-footers':'保留编号，只设置章节页脚'}.get,key=key+'-pages',on_change=changed)
    a,b=st.columns(2)
    p['body_start']=int(a.number_input('正文起始页码',min_value=1,max_value=9999,value=seed['body_start'],key=key+'-start',on_change=changed))
    p['footer']=b.selectbox('正文页脚',['page','chapter','text'],index=['page','chapter','text'].index(seed['footer']),format_func={'page':'页码','chapter':'章节名称＋页码','text':'普通文字＋页码'}.get,key=key+'-footer',on_change=changed)
    with st.expander('更多页码细节'):
     p['roman']=st.selectbox('前置页码',['lowerRoman','upperRoman'],index=0 if seed['roman']=='lowerRoman' else 1,format_func={'lowerRoman':'小写罗马 i、ii','upperRoman':'大写罗马 I、II'}.get,key=key+'-roman',on_change=changed)
     p['front_start']=int(st.number_input('前置起始数值',min_value=1,max_value=9999,value=seed['front_start'],key=key+'-front-start',on_change=changed))
     p['chapter_restart']=st.checkbox('每章重新编号',value=seed['chapter_restart'],key=key+'-restart',on_change=changed)
     p['alignment']=st.selectbox('页脚对齐',['center','right'],index=0 if seed['alignment']=='center' else 1,format_func={'center':'居中','right':'居右'}.get,key=key+'-align',on_change=changed)
     if p['footer']=='text':p['text']=st.text_input('页脚文字',value=seed['text'],max_chars=80,key=key+'-text',on_change=changed)
   else:p['pages']='keep'
   word=st.checkbox('本机Word更新目录和引用',value=word_seed(model,saved),key=key+'-word',on_change=changed)
   appearance=st.selectbox('目录外观',['reference','standard','preserve'],index=['reference','standard','preserve'].index(saved.get('toc_appearance','preserve')),format_func={'reference':'项目参考：23.7磅行距、分级缩进、右对齐点线','standard':'原项目默认：保留行距与已有缩进、补点线','preserve':'保留原目录段落格式'}.get,key=key+'-toc',on_change=changed) if word else saved.get('toc_appearance','preserve')
   targets=deepcopy(saved.get('toc_policy'))
   if word and targets is not None:
    targets['depth']=st.selectbox('正文目录层级',[1,2,3],index=targets['depth']-1,key=key+'-toc-depth',on_change=changed)
    targets['self']=st.checkbox('目录自身列入目录',value=targets['self'],key=key+'-toc-self',on_change=changed)
    st.caption('目录同时收录已确认的中英文摘要及后置独立标题；本地工作台可精细调整。')
   st.caption('项目参考外观不是学校强制要求。复杂对象保持；目录实际页码仅在Word成功更新和复查后确认。')
  else:word=False;appearance=saved.get('toc_appearance','preserve')
 explicit=saved.get('explicit',False) or st.session_state.pop(key+'-changed',False)
 model.field_updates_enabled=bool(enabled and word)
 if model.inventory:
  old=getattr(model,'page_layout_draft',None) or {}
  model.page_layout_draft={'explicit':explicit,'enabled':enabled,'policy':validate(p),'toc_appearance':appearance,'word_updates':bool(enabled and word),'smart_defaults':saved.get('smart_defaults',0),**({'toc_policy':targets if enabled and word else saved['toc_policy']} if 'toc_policy' in saved else {}),'input_sha256':model.inventory['input_sha256'],'regions':deepcopy(old.get('regions',[])) if old.get('input_sha256')==model.inventory['input_sha256'] else []}
 if saved.get('smart_defaults'):st.caption('新任务缺省普通图题、表题居中；完整整理另核对安全内容表格外侧边框与内部目标。已保存要求、材料保护和明确关闭优先。')
 if not enabled:st.caption('本次仅整理安全文字格式，保持原有编号、页码和目录及表格边框。')
 else:
  parts=['文字格式']
  if p.get('version')==3:parts.append('安全图表与分页相邻')
  if p['dynamic']:parts.append('安全编号及引用同步')
  if p['pages']!='keep':parts.append('分区页码与'+('章节页脚' if p['footer']=='chapter' else '页脚'))
  if word:parts.append('本机Word目录与引用更新'+('及项目参考目录外观（23.7磅行距、分级缩进）' if appearance=='reference' else '及原项目目录外观' if appearance=='standard' else ''))
  st.caption('本次将处理：'+'、'.join(parts)+'。不确定事项同页集中询问，原稿保留。')
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
   ackbulk=st.checkbox('按当前明确范围批量整理：格式、安全编号同步、本页页码方案及Word安全目录/引用更新；原稿保留',key='pages-bulk-ack-'+str(draft))
   if st.button('执行当前完整方案（本地零API）',disabled=not ackbulk,key='pages-bulk',type='primary'):
    from .assembly_session import execute_local
    from .smart_session import binding
    new_command=not bulk.get('done') or bulk.get('post')!=binding(model)
    execute_local(model,bulk,acknowledged=True)
    if new_command:
     from .field_session import submit
     auto={};st.session_state['pages-word-'+model.task_dir.name]=auto
     submit(model,auto)
    st.rerun()
   auto=st.session_state.get('pages-word-'+model.task_dir.name,{})
   if auto.get('identity') and not auto.get('adopted'):
    @st.fragment(run_every=2)
    def complete_word():
     from .field_session import receive,adopt
     status=receive(model,auto)
     if status['state']=='succeeded':
      adopt(model,auto)
      from .smart_session import binding
      bulk['post']=binding(model);st.rerun()
     elif status['state'] in ('queued','running'):st.info('本机Word更新和最终复查中；已有排版副本仍可下载。')
     else:st.warning('目录/引用更新未完成：'+status.get('error','任务未完成'))
    complete_word()
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

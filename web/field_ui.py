"""One local advanced tool: original queue, explicit scope, preview and adoption."""
import streamlit as st
from .session import public_error
from . import field_session
from .dynamic_session import context
from .scope_session import fingerprint
from core.word_fields import inventory

def render_local(model):
 with st.expander('本机Word · 目录与交叉引用更新（零API）'):
  st.caption('原检查仍只读。此处明确选择后在最终副本上重新分页、更新安全TOC/REF/PAGEREF；不刷新SEQ或外部域。')
  with st.expander('Word超时后的本机恢复'):
   if st.button('核对Word已退出并解除超时隔离',key='word-timeout-reset'):
    try:
     from core.word_native import clear_timeout_guard
     clear_timeout_guard();st.success('已核对Word进程退出，隔离标记已清除；不会自动重试。')
    except Exception as exc:st.warning(public_error(exc))
  try:
   ctx,_=context(model);inv=inventory(ctx['input']);rows=inv['objects'];labels={r['id']:r['kind']+' · 第'+str(r['start'])+'段 · '+r['instruction'].strip() for r in rows if r['safe']}
   selected=st.multiselect('本次更新对象',list(labels),default=list(labels),format_func=labels.get,key='word-fields-'+ctx['sha256'])
   for r in rows:
    if not r['safe']:st.caption(r['kind']+' 保持：'+str(r['reason']))
   creation=None
   with st.expander('受限创建/转换自动目录'):
    st.caption('仅可替换范围页已经确认的普通手工目录条目/空条目；目录标题不在替换范围。标题层级须已确认。')
    enable=st.checkbox('明确替换已确认的普通目录区域',key='word-create-'+ctx['sha256'])
    if enable:
     a,b=st.columns(2);start=int(a.number_input('目录首条段落',min_value=1,max_value=len(model.paragraph_types),value=1,key='word-create-start'));end=int(b.number_input('目录末条段落',min_value=1,max_value=len(model.paragraph_types),value=start,key='word-create-end'));level=st.selectbox('包含标题层级',[1,2,3],index=2,key='word-create-level');creation={'start':start,'end':end,'levels':list(range(1,level+1)),'confirmed':True}
   state=st.session_state.setdefault('word-local-'+model.task_dir.name,{})
   intent=fingerprint({'selected':selected,'creation':creation})
   if state.get('identity') and state.get('intent')!=intent:
    field_session.cancel(state);state.clear();st.info('本次选择或创建范围变化，旧预演不可采用；请重新预演。')
   if st.button('预演所选目录与引用更新',disabled=not selected and not creation,key='word-local-preview'):
    if state.get('identity'):field_session.cancel(state)
    state.clear();field_session.submit(model,state,selected=selected,creation=creation);state['intent']=intent;st.rerun()
   if state.get('identity'):
    @st.fragment(run_every=2)
    def task():
     try:
      status=field_session.receive(model,state)
      if status['state'] in ('queued','running'):
       st.info('Word更新排队中' if status['state']=='queued' else 'Word重新分页、更新并复查中')
       if st.button('取消接收更新结果',key='word-local-cancel'):field_session.cancel(state);st.rerun()
      elif status['state']=='succeeded':
       if state.get('adopted'):st.success('已采用第'+str(state['adopted'])+'轮；当前处理输入未自动切换。');return
       st.write('真实Word预演完成，尚未采用。')
       st.json(state['result']['field_update']['validation'],expanded=False)
       ack=st.checkbox('已核对更新清单、保持对象与最终页码复查；采用此副本',key='word-local-ack-'+state['binding'])
       if st.button('确认采用目录/引用副本',disabled=not ack,key='word-local-adopt',type='primary'):field_session.adopt(model,state);st.rerun()
      else:st.warning(status.get('error','更新未完成，原排版副本保持'))
     except Exception as exc:st.warning(public_error(exc))
    task()
  except Exception as exc:st.info(public_error(exc))

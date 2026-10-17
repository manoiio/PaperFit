"""One optional switch, explicit preview and adoption; no implicit Word execution."""
import streamlit as st
from core import dynamic
from core.package import Package
from .dynamic_session import context,preview,adopt,valid,cancel
from .session import public_error

def render_dynamic(model,*,on_adopt=None):
    with st.expander('可选：动态编号与引用同步（默认关闭）',key='dynamic-panel-'+model.task_dir.name,on_change='rerun'):
        enabled=st.checkbox('启用本次动态处理',key='dynamic-enable-'+model.task_dir.name)
        st.caption('与普通一键格式处理分开授权。只改明确章节的普通题注数字及唯一正文纯文本引用，不移动对象、不更新域或真实页码。')
        if not enabled:return
        capability=dynamic.word_capability();st.info(capability['reason'])
        slot='dynamic-state-'+model.task_dir.name;state=st.session_state.setdefault(slot,{})
        try:
            ctx,b=context(model)
            if model.eligible() and model.result is None:
                st.info('请先执行普通格式快捷方案；动态处理将以其实际输出继续，不切换当前输入。')
                return
            st.write('动态目标：'+('第'+str(ctx['parent'])+'轮正式副本' if model.result else '当前处理输入')+'；不切换当前输入。')
            complete=st.checkbox('我已核对本次相关章节的图表题注范围完整；允许按文档顺序分别连续编号',key='dynamic-complete-'+b)
            if complete:
                plan=dynamic.propose(ctx['input'],ctx['classification'],complete=True)
                st.write(f"可纳入题注 {len(plan['accepted_captions'])} 个 · 数字改动 {len(plan['edits'])} 处 · 阻止关联组 {len(plan['blocked_groups'])} 个")
                st.dataframe([{k:e[k] for k in ('paragraph','start','end','before','after','kind','target_paragraph')} for e in plan['edits']],hide_index=True,width='stretch',height=220)
                with st.expander('章节与目标依据'):st.dataframe(plan['chapter_evidence'],hide_index=True,width='stretch')
                for item in plan['blocked_groups']:st.warning('关联组 '+str(item['group'])+'：'+'；'.join(item['reasons']))
                for limit in plan['limits']:st.caption(limit)
                if st.button('生成动态修复预演',disabled=not plan['edits'],key='dynamic-preview-button',width='stretch'):
                    with st.spinner('仅在独立副本同步数字并验证…'):preview(model,state,complete=True)
                    st.rerun()
            if state.get('result') and not state.get('adopted'):
                result=valid(model,state)
                st.write('动态预演已完成，尚未采用。实际数字变化 '+str(len(result['changes']))+' 处。')
                st.dataframe(result['changes'],hide_index=True,width='stretch',height=180)
                st.warning('域缓存未刷新、实际页码未核对。未知差异会阻止采用；本操作不补续表、重建目录或证明全文合格。')
                if st.button('确认采用动态副本',key='dynamic-adopt-button',type='primary',width='stretch'):
                    adopt(model,state)
                    if on_adopt is not None:on_adopt()
                    st.rerun()
                if st.button('取消动态预演',key='dynamic-cancel-button'):cancel(model,state);st.rerun()
            elif state.get('adopted'):
                if state['adopted_binding']==b:st.success('动态副本已采用为第'+str(state['adopted'])+'轮；处理前副本和当前输入保留。')
                else:st.info('此前动态副本已采用；当前绑定已变化，不能沿用旧预演授权。')
        except Exception as exc:st.warning('动态处理未执行/已失效：'+public_error(exc))

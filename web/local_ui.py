"""Former local shortcuts inside the five-step workbench. No implicit API path."""
import streamlit as st
from .smart_session import suggest,accept_scope,shortcut_plan,execute,binding
from .session import public_error
from .presentation import position

def scope_tools(model):
    state=st.session_state.setdefault('smart-'+model.task_dir.name,{})
    try:
        now=binding(model)
        if not state and model.report is None:state['proposal']=suggest(model)
        with st.expander('本地批量范围建议（不调用AI）',expanded=model.report is None):
            st.caption('仅依据本地证据准备建议，人工调整和材料保护优先。可核对整体摘要直接检查，也可使用下方逐区域编辑。')
            if st.button('分析范围建议（不修改论文）',key='smart-prepare'):
                state['proposal']=suggest(model);st.rerun()
            p=state.get('proposal')
            if p and p['source_binding']!=now:
                st.warning('此前范围摘要已失效，请重新分析。')
            elif p:
                st.write('当前生效要求：'+str(p['rules']['name']))
                if p.get('structure_ai'):st.caption('当前建议含您明确调用的AI补充；尚未确认。可重新分析恢复为纯本地建议。')
                st.dataframe([{'区域':r['name'],'纳入':r['selected'],'待核对':r['pending'],'启用':r['enabled']} for r in p['preflight']['areas']],hide_index=True,height=210)
                with st.expander('核对全部建议、保护和未纳入事项'):
                    if st.toggle('查看完整本地范围技术记录',key='local-scope-record'):st.json(p['draft'],expanded=False)
                    for r in p['excluded']:st.caption('段落'+str(r['paragraph'])+'：'+r['reason'])
                    for r in p['limits']:st.caption(r)
                for r in p['preflight']['blockers']:st.error(r['entry']+'：'+r['reason'])
                st.caption('点击表示接受本次部分范围及排除摘要，经原合法接口确认并检查；不修正文档、不声明全文完整。')
                if st.button('接受此范围并检查',key='smart-confirm-scope',disabled=not p['preflight']['ready'],type='primary',width='stretch'):
                    accept_scope(model,p)
                    from .workflow_ui import go
                    go(3);st.rerun()
        if st.checkbox('显示可选联网结构工具（本地流程无需使用）',key='local-ai-tools'):
            from .structure_ui import render_structure
            render_structure(model,state)
    except Exception as exc:st.error('本地范围未完成：'+public_error(exc))


def repair_tools(model):
    if not model.report:return
    state=st.session_state.setdefault('smart-'+model.task_dir.name,{})
    coverage=(model.result['after'] if model.result else model.report)['coverage'];types=coverage.get('paragraph_types')
    n=sum(t in ('other','pending') for t in types.values()) if types else len(coverage['unconfirmed_paragraphs'])
    scope=(model.classification_confirmed or {});names={'table_scope':'表格','front_scope':'封面分节','toc_scope':'目录','citation_scope':'引文','note_scope':'注释','caption_scope':'题注关联','reference_scope':'内部引用'}
    st.caption('未套普通段落规则：'+str(n)+'段；未纳入模块：'+('、'.join(v for k,v in names.items() if k not in scope) or '无')+'。未配置和复杂结构不计为通过。')
    with st.expander('本地批量修正当前安全项（也可下方逐项选择）'):
        try:
            plan=shortcut_plan(model);st.write('当前输入可安全处理 '+str(len(plan['keys']))+' 项。此操作范围与手工已选清单不同，点击前请核对。')
            st.dataframe([{'位置':position(f['locator']),'属性':f['rule_name'],'实际':str(f['actual']),'要求':str(f['expected'])} for f in plan['items']],hide_index=True,height=210)
            if plan['plan']:st.caption(plan['plan']['reason'])
            st.caption('点击授权上述全部安全格式项，内部执行原真实单/两步预演、复查并采用。不会追加新问题，不调用AI、不切换输入；宽度/分页/移动/动态另行授权。')
            if st.button('按此方案本地修正',key='smart-execute',disabled=not plan['keys'] or model.result is not None,width='stretch'):
                with st.spinner('本地修正并验证副本…'):execute(model,plan,state)
                from .workflow_ui import go
                go(5);st.rerun()
        except Exception as exc:st.error('本地方案未完成：'+public_error(exc))

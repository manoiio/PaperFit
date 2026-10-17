"""Default short workflow; detailed five-step workspace remains available."""
import streamlit as st
from .session import public_error
from .smart_session import suggest,accept_scope,shortcut_plan,execute,binding
from core.classification import TYPES
from .presentation import position

def render_legacy_smart(model,root,load_builtin,upload_changed,render_results):
    st.header('智能处理')
    st.write('载入论文与要求 → 接受范围摘要 → 一键智能修正 → 下载与剩余事项')
    st.caption('AI解析规范，程序执行排版。沿用当前已生效要求；检查修正在本机执行；可选AI结构识别仅在明确点击后发送有限脱敏摘录，不自动调用AI或生成页面。')
    if model.inventory is None:
        a,b=st.columns([1.5,1])
        with a:
            key='upload-'+str(st.session_state.upload_generation)
            st.file_uploader('上传自己的DOCX（最大10MB）',type=['docx'],max_upload_size=10,key=key,on_change=upload_changed,args=(key,))
        with b:
            st.button('使用错误样本',on_click=load_builtin,args=('errors',),width='stretch')
            st.button('使用正确对照',on_click=load_builtin,args=('correct',),width='stretch')
        from .project_ui import render_project
        render_project(model)
        return
    from .workflow_ui import detail_go
    a,b=st.columns(2)
    a.button('选择要求 / 导入规范',on_click=detail_go,args=(1,),width='stretch')
    b.button('详细调整范围与例外',on_click=detail_go,args=(2,),width='stretch')
    st.caption('当前模式：'+{'basic':'基础检查','extended':'正文及标题题注','academic':'单文档扩展'}[model.mode]+'。不会因进入智能处理而改变模式、规则或处理输入。')
    slot='smart-'+model.task_dir.name
    state=st.session_state.setdefault(slot,{})
    try:
        now=binding(model)
        if not state and model.report is None:
            # First load prepares a read-only suggestion, never a confirmation.
            state['proposal']=suggest(model)
        if model.report:
            report=model.result['after'] if model.result else model.report
            coverage=report['coverage'];types=coverage.get('paragraph_types')
            excluded=sum(t in ('other','pending') for t in types.values()) if types else len(coverage['unconfirmed_paragraphs'])
            scope=model.result.get('output_classification_manifest',{}) if model.result else model.classification_confirmed or {}
            modules={'table_scope':'表格','front_scope':'封面分节','toc_scope':'目录','citation_scope':'引文','note_scope':'注释','caption_scope':'题注编号关联','reference_scope':'内部引用'}
            missing='、'.join(name for key,name in modules.items() if key not in scope)
            st.caption(f'未套普通段落规则：{excluded}个顶层段落（专门对象另按已确认模块处理）；未纳入模块：{missing or "无"}。未配置和复杂结构仍以原报告为准，不计为通过。')
        if state.get('completed') and state.get('binding')==now:
            r=state['completed']
            st.success('已完成本次快捷方案；当前处理输入仍未切换。' if r['status']=='adopted' else r['message'])
            if model.result:
                st.write(f"本次方案 {r['selected']} 项 · 实际修改记录 {r['changes']} 条 · 正式副本 {r['rounds']} 轮；采用时0次重复修正。")
                render_results()
            elif model.report:
                if st.button('准备本次检查阅读报告',key='smart-no-change-report'):state['reading']=model.prepare_reading_export()
                if state.get('reading'):
                    st.download_button('下载检查阅读报告HTML',state['reading']['report.html'],file_name='检查报告.html',on_click='ignore')
        elif model.result:
            st.info('已有正式输出。查看不会切换输入；如需继续，请明确使用副本。')
            render_results()
        from .structure_ui import render_structure
        render_structure(model,state)
        if st.button('分析范围建议（不修改论文）',key='smart-prepare',type='primary' if not model.report else 'secondary'):
            previous=state.get('structure');state.clear()
            if previous:state['structure']=previous
            state['proposal']=suggest(model);st.rerun()
        proposal=state.get('proposal')
        if proposal:
            if proposal['source_binding']!=now:
                if not model.report:st.warning('此前范围摘要已失效，请重新分析。')
            else:
                st.subheader('本次要求与范围摘要')
                st.write('使用当前生效要求：'+str(proposal['rules']['name']))
                if proposal.get('structure_ai'):
                    ai=proposal['structure_ai']
                    st.write(f'范围来源：本地直接纳入 {ai["local_included"]} 个；AI补充 {ai["accepted"]} 个；冲突/拒绝 {ai["rejected"]} 个，未返回 {ai["omitted"]} 个仍沿用本地状态。')
                p=proposal['preflight']
                st.dataframe([{'区域':r['name'],'本次启用':r['enabled'],'草稿纳入':r['selected'],'未纳入/待核对':r['pending'],'已有要求':r['configured']} for r in p['areas']],hide_index=True,width='stretch',height=250)
                with st.expander('全部对象、排除原因和范围限制'):
                    st.dataframe([{'段落':n,'本次类型':TYPES[t],'本轮纳入':int(n) in proposal['draft']['body'] if model.mode=='basic' else t not in ('pending','other'),'保护说明':model.material_exclusions.get(n,'')} for n,t in proposal['draft']['paragraph_types'].items()],hide_index=True,width='stretch',height=240)
                    st.dataframe(proposal['excluded'],hide_index=True,width='stretch',height=200)
                    for text in proposal['limits']:st.write(text)
                    for text in p['warnings']:st.caption(text['entry']+'：'+text['reason'])
                for item in p['blockers']:st.error(item['entry']+'：'+item['reason'])
                st.caption('点击下方按钮表示接受上述本次要求、部分范围和排除项，调用原合法范围确认与检查；不执行修正。')
                if st.button('接受此范围并检查',key='smart-confirm-scope',disabled=not p['ready'],type='primary',width='stretch'):
                    with st.spinner('正在确认摘要并检查…'):state['plan']=accept_scope(model,proposal)
                    st.rerun()
        if model.report and not (state.get('completed') and state.get('binding')==now) and not model.result:
            plan=shortcut_plan(model);state['plan']=plan
            s=model.report['summary'];st.subheader('安全格式快捷方案')
            st.write(f"发现问题 {s['problem_count']} · 待复核 {s['review_count']} · 本方案 {len(plan['keys'])} 项 · 最多 {plan['plan']['expected_rounds_max'] if plan['plan'] else 0} 轮")
            st.caption('只处理下列真实可修正项；排除对象移动、宽度、分页、边框辅助及动态编号。新出现问题仅展示，不自动追加。')
            with st.expander('核对完整快捷方案与未处理事项',expanded=False):
                st.dataframe([{'位置':position(f['locator']),'规则':f['rule_id'],'实际':str(f['actual']),'要求':str(f['expected'])} for f in plan['items']],hide_index=True,width='stretch',height=240)
                st.dataframe(plan['excluded'],hide_index=True,width='stretch',height=220)
                if plan['plan']:st.write(plan['plan']['reason'])
            st.caption('点击即授权当前展示的全部安全格式方案。内部真实预演、读回复查通过后采用；不会额外选择新问题、切换输入或调用AI。')
            if st.button('一键智能修正',key='smart-execute',type='primary',width='stretch'):
                with st.spinner('正在执行真实修正、落盘验证和采用…'):execute(model,plan,state)
                st.rerun()
        if model.report:
            from .dynamic_ui import render_dynamic
            render_dynamic(model)
        from .project_ui import render_project
        render_project(model)
    except Exception as exc:st.error('未完成：'+public_error(exc))


def render_smart(model,root,load_builtin,upload_changed,render_results):
    if st.session_state.get('smart-legacy',False):
        if st.button('返回一站式智能排版',key='onepass-home'):
            st.session_state['smart-legacy']=False;st.rerun()
        return render_legacy_smart(model,root,load_builtin,upload_changed,render_results)
    from .onepass_ui import render_onepass
    return render_onepass(model,root,load_builtin,upload_changed,render_results)

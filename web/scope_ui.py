"""One scope overview, original editor navigation, explicit snapshot acknowledgement."""
import streamlit as st
from .scope_session import AREAS
from .session import public_error


def render_scope_overview(model):
    with st.container(key='scope-overview'):
        st.subheader('2 统一范围核对与检查前预检')
        st.caption('规则已配置、模块已启用、对象已确认是三个不同状态。此处读取现有草稿，不自动接受建议或声明范围完整。')
        pre=model.scope_preflight()
        s=pre['summary']
        if s:st.write(f"当前输入：{'原稿' if s['round']==0 else '第'+str(s['round'])+'轮副本'} · {s['rules_name']} · 版本{s['rules_version']} · {s['page_scope']}")
        st.dataframe([{'区域':r['name'],'启用':'是' if r['enabled'] else '否','格式要求':'有可用要求' if r['configured'] else '未配置',
                       '检测数量':str(r['detected']) if r['detected'] is not None else '未知','数量口径':r['unit'],'草稿纳入':r['selected'],'排除/保护':r['excluded'],
                       '待核对':str(r['pending']) if r['pending'] is not None else '未知','当前确认':'有效' if r['confirmed'] else '未确认或已失效','预检':r['status']} for r in pre['areas']],hide_index=True,width='stretch')
        st.caption('检测数量是本模块清单/线索数量：封面是可定位对象而非已填写字段；目录是候选线索而非确认条目；引文只扫描当前草稿正文。不同口径不能相加，也不是覆盖率。')
        links={a:'scope-'+a for a in AREAS}
        st.markdown(' · '.join(f'[{name}](#{links[a]})' for a,name in AREAS.items() if a=='paragraph' or model.mode=='academic'))
        st.caption('定位入口只滚动到原编辑区域。准备/编辑草稿仍使用原控件；不会覆盖人工调整、材料保护、章号、关联或完整声明。')
        if pre['blockers']:
            st.error(f"预检发现{len(pre['blockers'])}项阻止记录，请先修改草稿；尚未执行格式检查。")
            st.dataframe([{'区域':p['entry'],'原因':p['reason'],'代码':p['code']} for p in pre['blockers']],hide_index=True,width='stretch')
        else:st.info('预检未发现阻止项。请核对下方范围摘要后明确确认；未纳入、未配置和复杂对象不会因此变成通过。')
        with st.expander(f"范围摘要、提醒与支持边界（提醒{len(pre['warnings'])}项）",expanded=True):
            for r in pre['areas']:
                labels={'complete':'当前区域完整范围','headings_complete':'正文标题完整范围','references_complete':'文献完整范围','chapters_complete':'章节完整范围','covered_levels':'目录覆盖层级'}
                declaration='；'.join(labels[k]+'：'+('仅部分范围' if v is False else '已明确声明完整' if v is True else str(v)) for k,v in r['declarations'].items()) or '无完整范围声明'
                st.write(f"{r['name']}：{'纳入本轮' if r['enabled'] else '未启用'}；草稿纳入{r['selected']} {r['unit']}；排除/保护{r['excluded']}；{declaration}")
            with st.expander('核对具体对象编号、类型和主动排除（不含论文正文）'):
                st.dataframe(model.scope_draft_rows(),hide_index=True,width='stretch',height=280)
            st.caption('保留现有保守失效策略：部分草稿编辑会使多个区域确认一起失效；表中如实显示，未自动恢复确认标志。')
            for warning in pre['warnings']:st.caption(warning['entry']+'：'+warning['reason'])
            for limit in pre['limits']:st.caption(limit)
        token=f"{model.task_dir.name}-{pre['signature']}"
        ack=st.checkbox('我已核对以上所有已启用区域的完整草稿、主动排除和部分范围声明；确认这些范围用于本轮检查',key='scope-ack-'+token,disabled=not pre['ready'])
        def confirm():
            try:
                with st.spinner('正在校验全部范围并检查；不执行任何修正…'):
                    if not model.confirm_scopes_and_check(pre['signature'],acknowledged=ack):st.error(model.error)
            except Exception as exc:st.error(public_error(exc))
        st.button('确认这些范围并开始检查',on_click=confirm,disabled=not ack or not pre['ready'],type='primary',width='stretch')
        st.caption('调整任一区域后，请返回此处核对新摘要。旧勾选不授权新草稿；原分区域确认和独立检查入口仍保留。')
        if model.report:
            from .scope_session import report_scope_summary
            summary=report_scope_summary(model.report,model.classification_confirmed)
            with st.expander('本轮实际参与范围（来自实际检查报告）'):
                st.dataframe([{'区域':r['name'],'实际参与':r['participates'],'数量':r['selected'],'口径':r['unit'],'说明':r['scope']} for r in summary['areas']],hide_index=True,width='stretch')
                st.caption(summary['review_explanation'])

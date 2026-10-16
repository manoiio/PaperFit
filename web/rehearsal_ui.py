"""Decision first, original real transaction and explicit acknowledgement unchanged."""
import streamlit as st
from core.rehearsal import LABELS
from .issues import locate,STATUS
from .reading_report import change_value
from .decision_ui import render_impact_summary,quick_changes,view_state,cancel_view

def render_rehearsal(model):
    if model.selected:
        from .plan_ui import render_plan
        if render_plan(model):return
    had=bool(model.rehearsal);view=model.rehearsal_view()
    state=view_state(model,view,had,'single')
    st.write('**单轮修正 · '+state+'**')
    if model.rehearsal_error:st.warning(model.rehearsal_error)
    def start():
        st.session_state.pop('decision-last-'+model.task_dir.name,None)
        with st.spinner('处理中：执行所选修正、完整性验证与落盘复查；不登记正式轮次…'):model.rehearse()
    if not view:
        st.button('预演所选修正',type='primary',disabled=not model.selected or model.result is not None,on_click=start,width='stretch')
        st.caption('生成真实预演副本；不切换输入、不增加正式轮次，不调用AI或渲染。')
        return
    adopted=model.rehearsal.get('adopted_round')
    with st.container(key='rehearsal-results'):
        st.subheader('修正预演与关联影响')
        imp=view['impact'];counts=imp['counts']
        render_impact_summary(imp,len(view['selected']),imp['change_record_count'],'single-impact')
        quick_changes(view['changes'])
        if adopted:
            from .workspace_status import output_relation
            st.success(f'此预演已登记为第{adopted}轮。')
            st.write(output_relation(model,adopted))
        else:
            st.caption('采用授权涵盖全部明确选择。请同时核对下方完整清单、风险及原始记录；不是视觉验收。')
            ack=st.checkbox('我已核对全部所选修改、关联影响及剩余事项，确认采用这一副本',key='rehearsal-ack-'+view['id']+'-'+view['binding'])
            def adopt():
                with st.spinner('处理中：重新核对绑定和事务，登记已验证副本…'):model.adopt_rehearsal(view['id'],acknowledged=True)
            st.button('确认采用此副本',disabled=not ack,on_click=adopt,type='primary',width='stretch')
        st.button('关闭已采用预演说明' if adopted else '取消预演',on_click=cancel_view,args=(model,),key='cancel-'+view['id'])
        with st.expander('完整影响、修改及来源记录'):
            st.caption('XML属性变动：'+str(imp['xml_attribute_change_count'])+'；'+imp['attribute_count_note'])
            # Default only relevant changes, with complete remaining rows available.
            categories=st.multiselect('预演变化类别',list(LABELS),default=[k for k in LABELS if k not in ('remaining_unselected','remaining_review') and counts[k]],format_func=LABELS.get,key='impact-categories-'+view['id'])
            rows=[r for r in imp['records'] if r['kind'] in categories]
            pages=max(1,(len(rows)+19)//20)
            page=st.number_input('预演详情页',min_value=1,max_value=pages,value=1,step=1,key='impact-page-'+view['id']+'-'+str(pages))
            st.caption(f'筛选记录 {len(rows)} 条 · 每页20条 · 第{page}/{pages}页；完整导出保留全部记录。')
            st.dataframe([{'类别':r['label'],'规则':r['rule_id'],'位置':locate(r['locator']),'原状态':STATUS.get(r['before_status'],r['before_status']),'读回状态':STATUS.get(r['after_status'],r['after_status']),'原值':change_value(r['before'],r['rule_id']),'读回值':change_value(r['after'],r['rule_id']),'说明':r['reason']} for r in rows[(page-1)*20:page*20]],hide_index=True,width='stretch')
            with st.expander('实际修改、所选项结果、范围与覆盖提示'):
                st.dataframe([{'规则':c['rule_id'],'位置':locate(c['locator']),'修改前':change_value(c['before'],c['rule_id']),'修改后':change_value(c['after'],c['rule_id']),'复查':STATUS.get(c['verification'],c['verification']),'来源':str(c['source'])} for c in view['changes']],hide_index=True,width='stretch')
                st.write({'明确范围':view['scope'],'所选项结果':imp['selected_outcomes'],'覆盖提示':imp['coverage_notes']})
            st.download_button('下载完整预演影响记录',model.rehearsal_download(),file_name='预演影响.json',mime='application/json',on_click='ignore',key='impact-download-'+view['id'])
        st.caption('改变选择、范围或规则后须重新预演；采用不代表分页或Word验收。')

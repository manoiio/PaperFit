"""Explicit selection → real preview transaction → acknowledged adoption."""
import streamlit as st
from core.rehearsal import LABELS
from .issues import locate,STATUS
from .reading_report import change_value

def render_rehearsal(model):
    if model.selected:
        from .plan_ui import render_plan
        if render_plan(model):return
    def start():
        with st.spinner('正在执行所选修正、完整性验证及落盘复查；尚不登记轮次…'):model.rehearse()
    view=model.rehearsal_view()
    if not view:st.button('预演所选修正',type='primary',disabled=not model.selected or model.result is not None,on_click=start,width='stretch')
    st.caption('预演会生成本机会话副本，不切换输入、不增加正式轮次；采用前核对关联影响。不会调用AI或生成页面预览。')
    if model.rehearsal_error:st.warning(model.rehearsal_error)
    if not view:return
    adopted=model.rehearsal.get('adopted_round')
    with st.container(border=True,key='rehearsal-results'):
        st.subheader('修正预演与关联影响')
        st.caption(f"输入：第{view['input_round']}轮（0为原稿） · 规则：{view['rules']['name']} v{view['rules']['version']} · "+(f'已采用为第{adopted}轮，输入尚须明确切换' if adopted else '本副本尚未成为正式轮次'))
        imp=view['impact'];counts=imp['counts']
        cols=st.columns(4)
        for col,label,n in zip(cols,['明确选择记录','实际修改记录','未选自然符合','新出现问题'],[len(view['selected']),imp['change_record_count'],counts['natural_resolved'],counts['new_problem']]):col.metric(label,n)
        st.caption('XML属性变动：'+str(imp['xml_attribute_change_count'] if imp['xml_attribute_change_count'] is not None else '无法一对一计数')+'；'+imp['attribute_count_note'])
        st.write('预演剩余：'+str(imp['remaining_summary']['problem_count'])+'问题，'+str(imp['remaining_summary']['review_count'])+'待复核（含覆盖提示）。')
        st.caption('；'.join(LABELS[k]+str(counts[k]) for k in LABELS))
        if counts['new_problem'] or counts['problem_to_review'] or counts['unaligned']:
            st.warning('请核对新增问题、转待复核及无法对齐记录；这些不算已解决，也不会自动加入修正。')
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
        st.caption('这不是视觉验收；目录页码、实际同页和Word显示仍需另行核对。')
        if adopted:st.success(f'此预演已登记为第{adopted}轮；下载在下方，重复点击不会再生成一轮。')
        else:
            ack=st.checkbox('我已核对全部所选修改、关联影响及剩余事项，确认采用这一副本',key='rehearsal-ack-'+view['id']+'-'+view['binding'])
            def adopt():
                with st.spinner('重新核对文件、配置、范围及原事务白名单，登记已验证副本…'):
                    model.adopt_rehearsal(view['id'],acknowledged=True)
            st.button('确认采用此副本',disabled=not ack,on_click=adopt,type='primary',width='stretch')
        st.button('关闭已采用预演说明' if adopted else '取消预演',on_click=model.cancel_rehearsal,key='cancel-'+view['id'])
        if adopted:st.caption('关闭说明不会撤销已经登记的副本或历史。')
        st.caption('返回上方更改选择会使本预演及确认失效，需要重新预演；当前输入保持。')

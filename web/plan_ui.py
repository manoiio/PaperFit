"""Known dependency draft, complete real rehearsal, then atomic explicit adoption."""
import streamlit as st
from core.package import DemoError
from core.rehearsal import LABELS
from .issues import locate,STATUS
from .reading_report import change_value

def impact_table(imp,key):
    st.write(f"剩余 {imp['remaining_summary']['problem_count']} 问题、{imp['remaining_summary']['review_count']} 待复核（含覆盖提示）。")
    st.caption('；'.join(LABELS[k]+str(v) for k,v in imp['counts'].items()))
    options=list(LABELS)
    cat=st.multiselect('查看影响类别',options,default=[k for k in options if imp['counts'][k] and k not in ('remaining_unselected','remaining_review')],format_func=LABELS.get,key='plan-cats-'+key)
    rows=[r for r in imp['records'] if r['kind'] in cat];pages=max(1,(len(rows)+19)//20)
    page=st.number_input('影响详情页',min_value=1,max_value=pages,value=1,key='plan-page-'+key+'-'+str(pages))
    st.caption(f'共{len(rows)}条；每页20条；完整导出保留全部。')
    st.dataframe([{'类别':r['label'],'规则':r['rule_id'],'位置':locate(r['locator']),'原状态':STATUS.get(r['before_status'],r['before_status']),'读回状态':STATUS.get(r['after_status'],r['after_status']),'修改前':change_value(r['before'],r['rule_id']),'读回后':change_value(r['after'],r['rule_id']),'原因':r['reason']} for r in rows[(page-1)*20:page*20]],hide_index=True,width='stretch')

def render_plan(model):
    try:p=model.correction_plan()
    except DemoError:return False  # Original controls explain any invalid binding.
    if not p['two_steps']:return False
    st.subheader('已知依赖：两步修正计划')
    st.write(p['reason'])
    st.caption(f"当前输入第{p['input_round']}轮 · {p['rules']['name']} v{p['rules']['version']} · 明确选择{p['selected_count']}条（含筛选外选择） · 最多{p['expected_rounds_max']}个正式副本。")
    st.info('第2步使用第1步实际副本和重新检查；两步仍是两个原事务。预演不增加正式轮次、不切换当前输入。')
    st.write(' → '.join(f"第{x['number']}步：{'普通格式' if x['number']==1 else '所选引文上标'}（{len(x['keys'])}条）" for x in p['steps']))
    with st.expander('核对完整选择、每步属性及范围',expanded=False):
        items=[{'步骤':step['number'],'key':x['key'],'规则':x['rule_id'],'位置':locate(x['locator']),'修改前':change_value(x['actual'],x['rule_id']),'拟修改属性及要求':change_value(x['expected'],x['rule_id']),'依据':str(x['source'])} for step in p['steps'] for x in step['items']]
        pages=max(1,(len(items)+19)//20);page=st.number_input('计划选择页',min_value=1,max_value=pages,value=1,key='plan-selected-page-'+p['binding']+str(pages))
        st.caption(f'完整选择{len(items)}条；当前第{page}/{pages}页。每步修改整条所选组合规则内的已声明属性。')
        st.dataframe(items[(page-1)*20:page*20],hide_index=True,width='stretch')
        st.write({'输入摘要':{'SHA256':p['input_sha256'],'轮次':p['input_round']},'确认范围':p['scope'],'原有待复核':model.report['summary']['review_count'],'边界':p['limits']})
    for x in p['blocked']:st.error(x['reason'])
    def start():
        with st.spinner('按顺序执行原修正事务、读回复查及准确引文定位；不登记正式历史…'):model.rehearse_plan()
    view=model.rehearsal_view()
    if not view:st.button('预演完整分步计划',on_click=start,type='primary',disabled=bool(p['blocked']) or model.result is not None,width='stretch')
    if model.rehearsal_error:st.warning(model.rehearsal_error)
    if not view or not model.rehearsal or model.rehearsal.get('kind')!='format_plan':return True
    adopted=model.rehearsal.get('adopted_rounds')
    with st.container(border=True):
        st.subheader('完整计划预演与关联影响')
        a,b,c,d=st.columns(4)
        a.metric('计划 / 步骤',f"1 / {len(view['steps'])}");b.metric('实际修正调用',view['engine_calls']);c.metric('实际修改记录',view['actual_change_records']);d.metric('已登记正式轮次',len(adopted) if adopted else 0)
        st.caption('各步独立计数；下方整计划影响只比较起始与最终，不累加中间问题。采用时0次完整修正。')
        for step in view['steps']:
            with st.expander(f"第{step['number']}步：{step['status']}"):
                st.caption(f"输入{step['input_sha256'][:12]} → 输出{step['output_sha256'][:12]}；实际修正调用{step['engine_calls']}次。")
                if step['impact']:impact_table(step['impact'],view['id']+'-step-'+str(step['number']))
                st.dataframe([{'规则':x['rule_id'],'位置':locate(x['locator']),'修改前':change_value(x['before'],x['rule_id']),'修改后':change_value(x['after'],x['rule_id']),'复查':STATUS.get(x['verification'],x['verification'])} for x in step['changes']],hide_index=True,width='stretch')
        st.write('整计划最终影响')
        impact_table(view['overall_impact'],view['id']+'-final')
        st.warning('新增问题、转待复核及无法对齐均须核对，不算已解决；不会追加修正。引文上标可能增加普通正文覆盖提示。')
        st.download_button('下载完整计划预演记录',model.rehearsal_download(),file_name='计划预演.json',mime='application/json',on_click='ignore')
        if adopted:
            st.success('完整计划已采用为第'+ '、'.join(map(str,adopted))+'轮；当前处理输入保持，点击下方“以计划最终副本继续”才切换。')
            for i,step in enumerate(model.plan_step_downloads(),1):
                st.download_button(f"下载第{i}步副本（第{step['round']}轮）",step['fixed.docx'],file_name=f'计划第{i}步.docx',mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',on_click='ignore',key='plan-docx-'+view['id']+str(i))
        else:
            ack=st.checkbox('我已核对完整选择、两步父子关系、每步及最终影响，确认采用全部已验证副本',key='plan-ack-'+view['id']+'-'+view['binding'])
            def adopt():
                with st.spinner('重新验证所有文件、范围、规则和原事务记录，准备全部归档后统一登记…'):model.adopt_plan(view['id'],acknowledged=True)
            st.button('确认采用完整计划',disabled=not ack,on_click=adopt,type='primary',width='stretch')
        st.button('关闭已采用计划说明' if adopted else '取消完整计划预演',on_click=model.cancel_rehearsal,key='cancel-plan-'+view['id'])
        st.caption('返回修改选择会使旧预演失效，须重新预演。计划确认不等于视觉、Word或目录页码验收。')
    return True

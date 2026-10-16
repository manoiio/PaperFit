"""Local user-triggered save/import, separate from the deliverable result ZIP."""
import streamlit as st
from .session import public_error

def render_project(model):
    with st.expander('保存项目 / 恢复项目（用于继续工作）',key='project-panel',on_change='rerun'):
        st.caption('项目包包含论文原稿、当前输入和所选历史副本，仅点击保存后在本机下载。与“本轮结果包”不同：项目包用于中断后继续工作；不含密钥、调用日志、运行任务和页面图片。')
        save,restore=st.columns(2)
        with save:
            policy=st.selectbox('保存历史范围',['完整历史（最多30轮）','仅原稿和当前输入（明确省略历史）'],key='project-policy')
            if policy.startswith('仅'):st.warning('将省略全部旧轮次及对应记录；当前轮次保留为检查点，之后的新轮次从原编号继续。')
            if st.button('保存项目',disabled=model.inventory is None,width='stretch'):
                try:
                    model.prepare_project('all' if policy.startswith('完整') else 'current')
                    st.success('项目包已准备；状态变化会使这份下载失效。')
                except Exception as exc:st.error(public_error(exc))
            if model.project_export:
                try:
                    raw=model.project_download()
                    if raw:st.download_button('下载项目包（含论文）',raw,file_name='论文有格_项目.zip',mime='application/zip',on_click='ignore',width='stretch')
                    else:st.info('当前状态已变化，请重新点击保存项目。')
                except Exception as exc:model.project_export=None;st.error(public_error(exc))
        with restore:
            uploaded=st.file_uploader('导入论文有格项目包ZIP（最大100MB）',type=['zip'],max_upload_size=100,key='project-upload-'+str(st.session_state.get('upload_generation',0)))
            if st.button('校验项目包并查看摘要',disabled=uploaded is None,width='stretch'):
                try:model.stage_project(uploaded.getvalue())
                except Exception as exc:st.error(public_error(exc))
            if model.project_pending:
                st.markdown('**恢复摘要（尚未替换当前工作）**')
                try:
                    summary=model.project_summary();rules,rows=model.project_review()
                except Exception as exc:
                    model.cancel_project_import();st.error(public_error(exc));return
                st.dataframe([{'项目':k,'恢复内容':str(v)} for k,v in summary.items()],hide_index=True,width='stretch')
                with st.expander('核对恢复的完整规则与段落、表格范围'):
                    st.dataframe(rules,hide_index=True,width='stretch')
                    st.dataframe(rows,hide_index=True,width='stretch',height=280)
                if model.inventory:st.warning('恢复会切换当前未保存的工作。请先在左侧保存，或取消恢复；当前任务文件不会被覆盖。')
                ack=st.checkbox('已核对恢复摘要、规则与范围；同意切换当前工作',key='project-ack-'+model.project_pending['directory'].name)
                if st.button('核对并恢复项目',disabled=not ack,width='stretch'):
                    try:
                        new=model.restore_project(acknowledged=True)
                        # New task plus new widget namespace; never transfer browser/session credentials.
                        generation=st.session_state.get('upload_generation',0)+1
                        for k in list(st.session_state):del st.session_state[k]
                        st.session_state.workflow=new;st.session_state.upload_generation=generation
                        st.session_state['check-mode']={'basic':'基础检查','extended':'正文及标题题注检查','academic':'单文档扩展检查'}[new.mode]
                        st.session_state['short-spec-text']=new.spec_text
                        st.rerun()
                    except Exception as exc:st.error(public_error(exc))
                if st.button('取消恢复，保留当前工作',width='stretch'):
                    model.cancel_project_import();st.rerun()
    if model.project_notice:st.info(model.project_notice)

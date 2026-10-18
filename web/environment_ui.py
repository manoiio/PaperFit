"""Explicit local diagnostics; never run Word or HTTP while merely rendering."""
import streamlit as st

def render_environment():
    with st.expander('环境自检与恢复'):
        st.caption('基础功能不要求API或Word。普通自检不联网、不控制Word、不安装依赖。')
        if st.button('检查本机环境',key='local-environment-check'):
            from local_tools import environment
            st.session_state['local-environment']=environment()
        for row in st.session_state.get('local-environment',[]):
            st.write(row['item']+' · '+row['state']);st.caption(row['detail'])
        if st.button('深入检测Word与PDF（公开样本）',key='local-word-check',help='只打开本项目公开样本的隔离副本，导出PDF并关闭该副本；不处理您的其他文档。'):
            try:
                from local_tools import deep_check
                with st.spinner('正在检测本机Word，DOCX功能仍可使用…'):record=deep_check()
                st.success(record['status']+' · '+str(record['seconds'])+'秒。本次探测不保证所有论文结构均支持。')
            except Exception as exc:
                from .session import public_error
                st.warning('Word深入检测未完成：'+public_error(exc))
        st.caption('Word超时后可能仍在执行。先自行检查任务文档和对话框，相关任务结束后再退出Word；不会强制关闭其他文档。')
        if st.button('检查并解除Word超时隔离',key='local-word-recover'):
            try:
                from core.word_native import clear_timeout_guard
                clear_timeout_guard();st.info('隔离标记已检查；没有关闭Word、删除论文或恢复旧授权。')
            except Exception as exc:st.warning(str(exc))
        st.markdown('[故障处理说明](https://github.com/manoiio/PaperFit/blob/main/docs/troubleshooting.md)')

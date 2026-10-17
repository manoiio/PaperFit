"""Ordinary-user entry: one explicit command, only necessary exceptions."""
import json
from contextlib import nullcontext
import streamlit as st
from .session import public_error
from .onepass_session import start,continue_command,current,cancel
from .scope_session import fingerprint


def render_onepass(model,root,load_builtin,upload_changed,render_results):
    st.header('智能排版')
    task=model.task_dir.name if model.task_dir else 'new'
    state=st.session_state.setdefault('onepass-'+task,{})
    completed=model.inventory is not None and state.get('status')=='done' and current(model,state,st.session_state.get('onepass-extra-'+task,''))
    if completed:render_success(model,state,render_results)
    else:st.write('上传论文，按要求整理，下载修改好的副本。原稿保留。')
    def recommended():
        # Only a new task from this entry. An advanced mode choice is authoritative.
        if model.inventory is None and 'check-mode' not in st.session_state:model.set_mode('academic')
    def uploaded(key):recommended();upload_changed(key)
    def builtin(kind):recommended();load_builtin(kind)
    task=model.task_dir.name if model.task_dir else 'new'
    if model.inventory is None:
        key='upload-'+str(st.session_state.upload_generation)
        st.file_uploader('上传论文DOCX（最大10MB）',type=['docx'],max_upload_size=10,key=key,on_change=uploaded,args=(key,))
        with st.expander('没有文件？使用内置合成样本'):
            a,b=st.columns(2);a.button('使用错误样本',on_click=builtin,args=('errors',));b.button('使用正确对照',on_click=builtin,args=('correct',))
    with st.expander('修改排版要求，再处理一次') if completed else nullcontext():
        if model.inventory:st.text('当前论文：'+model.display_name+' · 原稿及前轮副本保留')
        from core import effective_rules
        rules=effective_rules(**model._base_rules_arguments(),mode=model.mode)
        is_default=model.custom_rules_path is None and model.active_template is None
        st.write('排版要求：'+('SCUT本科工理类 · 2015年项目材料演示规则' if is_default else rules['name']))
        st.caption('规则版本：'+str(rules['version'])+('。2015年材料，不宣称现行通用校规。' if is_default else '。沿用已生效配置和来源。')+'未规定的属性不自动补齐。')
        extra=st.text_input('还有其他要求吗？（可选）',placeholder='例如：在SCUT要求基础上，正文改为四号、2倍行距',key='onepass-extra-'+task,max_chars=2000,
                            help='快捷补充先支持明确的正文常用字号、倍数行距。其他格式要求可在高级工作区设置。')
        st.caption('开始后，需要时将向DeepSeek发送有限的脱敏文字摘录辅助识别段落及普通表格用途；脚注尾注本地识别。有补充要求时另解析一次补充文字。文件排版在本机完成，原稿保留。脱敏不保证彻底匿名。')
        valid=model.inventory is not None and current(model,state,extra)
        def progress(name):status.update(label=name);status.write(name)
        if st.button('开始智能排版',key='onepass-start',type='primary',width='stretch',disabled=model.inventory is None or (valid and state.get('status') in ('done','waiting','running'))):
            with st.status('识别论文内容',expanded=True) as status:
                start(model,state,extra,emit=progress)
                status.update(label='有少量事项需要您决定' if state.get('status')=='waiting' else '整理完成' if state.get('status')=='done' else '本次未完成',state='error' if state.get('status')=='failed' else 'complete')
            st.rerun()
    if state and not valid and model.inventory:
        st.info('论文、要求或已有设置发生变化，请重新开始；旧处理结果不能用于本次操作。')
    if valid and state.get('status')=='waiting':
        st.subheader('请帮助确认这几处')
        st.caption('只询问影响修改、目前无法可靠判断的事项。回答后继续，不重新发送全部摘录。')
        decisions={}
        for q in state['questions']:
            with st.container(border=True):
                if q.get('context'):st.text('附近文字：'+q['context'])
                st.text('当前文字：'+q['text']);st.write(q['question'])
                key='onepass-answer-'+state['id']+'-'+q['id']
                answer=st.selectbox('您的选择',list(q['options']),format_func=q['options'].get,index=None,key=key,placeholder='请选择，或暂不处理')
                if answer is not None:decisions[q['id']]=answer
        a,b=st.columns([2,1])
        if a.button('确认并继续',key='onepass-continue',type='primary',disabled=len(decisions)!=len(state['questions']),width='stretch'):
            try:
                with st.status('继续整理',expanded=True) as status:
                    continue_command(model,state,extra,decisions,emit=progress)
                    status.update(label='整理完成' if state.get('status')=='done' else '已返回，请修改补充要求' if state.get('status')=='cancelled' else '本次未完成',state='error' if state.get('status')=='failed' else 'complete')
                st.rerun()
            except Exception as exc:st.error(public_error(exc))
        if b.button('取消本次处理',key='onepass-cancel',width='stretch'):cancel(model,state);st.rerun()
    if valid and state.get('status')=='running':
        st.info('本次正在处理；切换页面不会重新发起。若处理已中断，可取消后明确重试。')
        if st.button('取消当前处理',key='onepass-cancel-running'):cancel(model,state);st.rerun()
    if valid and state.get('status')=='failed':
        st.error('本次未能安全完成，没有发布新副本。请核对文件和要求，或查看高级详情。')
        if st.button('取消本次尝试，准备重新处理',key='onepass-clear-failure'):cancel(model,state);st.rerun()
    with st.expander('高级设置与项目恢复'):
        if state.get('status')=='failed':st.text(state.get('error','本次未完成'))
        if state.get('audit'):
            export={'status':state.get('status'),'current':valid,**state['audit']}
            st.download_button('下载处理记录（不含论文摘录）',json.dumps(export,ensure_ascii=False,indent=2).encode(),file_name='处理记录.json',on_click='ignore',key='onepass-audit')
            if state.get('status')!='done':st.json(export,expanded=False)
        from .workflow_ui import detail_go
        st.button('进入本地精细工作台',on_click=detail_go,args=(1,),key='onepass-detail')
        if model.inventory:
            with st.expander('查看可能发送的摘录（不发送、不处理）'):
                from .structure_session import prepare
                try:st.json(prepare(model,include_tables=True)['request'],expanded=False)
                except Exception as exc:st.caption(public_error(exc))
        st.caption('未开始处理的补充文字只保留在当前会话；项目只保存已经生效的规则和原有草稿，不恢复本次执行授权。')
        from .project_ui import render_project
        render_project(model)


def render_success(model,state,render_results):
    files=model.downloads() if model.result else {}
    st.subheader('修正版已准备好' if files else '本次整理检查已完成')
    report=model.result['after'] if model.result else model.report
    if files:
        st.download_button('下载修正版',files['fixed.docx'],file_name='论文有格_修正版.docx',mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',on_click='ignore',type='primary',width='stretch')
    else:
        st.info('本次没有需要安全修改的格式，未额外生成副本。')
        st.download_button('下载已检查文件',model.input_path.read_bytes(),file_name='论文有格_已检查.docx',on_click='ignore')
    n=state['outcome'].get('changes',0);summary=report['summary']
    st.write(f'已整理 {n} 处格式；原稿保留。修改后仍有 {summary["problem_count"]} 个问题、{summary["review_count"]} 项需要留意。')
    if model.result:
        groups={}
        for c in model.result['changes']:
            rid=c['rule_id'];label='页面与边距' if rid in ('R01','R02') else '正文文字与段落' if rid in ('R03','R04','R05','R06','R07','R13') else {'R23':'表内普通文字','R36':'脚注普通文字','R37':'尾注普通文字'}.get(rid,'标题、题注及其他已确认文字')
            groups[label]=groups.get(label,0)+1
        st.write('主要调整：'+'；'.join(f'{k} {v} 处' for k,v in groups.items()))
    scope=(model.result.get('output_classification_manifest') if model.result else model.classification_confirmed) or {}
    tables=scope.get('table_scope',{}).get('table_types',{});notes=scope.get('note_scope',{}).get('objects',[])
    st.write('参与范围：内容表格 '+str(sum(v=='content' for v in tables.values()))+' 张；脚注 '+str(sum(n.startswith('footnote:') for n in notes))+' 条；尾注 '+str(sum(n.startswith('endnote:') for n in notes))+' 条。与顶层段落分别计数，不代表全文覆盖率。')
    coverage=report['coverage'];types=coverage.get('paragraph_types',{})
    count=sum(t in ('other','pending') for t in types.values()) if types else len(coverage.get('unconfirmed_paragraphs',[]))
    st.write(f'还需留意：{count} 段用途未明确或不属普通文字，本次未套普通段落格式。实际分页、目录页码及复杂对象仍需查看。')
    if state.get('audit',{}).get('structure_fallback'):st.info('这次未能完成辅助识别，已整理可靠识别的部分；未确定内容保持。')
    st.caption('部分范围整理不等于全文排版合格。正在处理的输入仍为原文件，未自动切换。')
    with st.expander('更多下载、修改记录与处理详情'):
        if model.result:
            st.download_button('下载完整结果包',model.result_package(),file_name='论文有格_结果.zip',on_click='ignore')
        else:
            reading=model.prepare_reading_export();st.download_button('下载检查阅读报告',reading['report.html'],file_name='检查报告.html',on_click='ignore')
        st.json(state['audit'],expanded=False)
        if model.result:render_results()

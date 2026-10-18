"""Ordinary-user entry: one explicit command, only necessary exceptions."""
import json
from contextlib import nullcontext
import streamlit as st
from .session import public_error
from .onepass_session import start,continue_command,current,cancel
from .scope_session import fingerprint


def render_onepass(model,root,load_builtin,upload_changed,render_results):
    st.header('智能排版')
    st.write('整理文字格式、图表与分页，并在本机 Word 可用时更新目录。')
    task=model.task_dir.name if model.task_dir else 'new'
    state=st.session_state.setdefault('onepass-'+task,{})
    input_ui=st.session_state.get('requirements-ui-'+task,{})
    selected=input_ui.get('selected')
    prior_extra=st.session_state.get('onepass-extra-'+task,'') if input_ui.get('choice','current')=='current' else ''
    from .page_ui import options as assembly_options
    prior_done=model.inventory is not None and state.get('status')=='done' and current(model,state,prior_extra,selected)
    if model.inventory is not None:assembly_options(model,task)
    completed=model.inventory is not None and state.get('status')=='done' and current(model,state,prior_extra,selected)
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
    if model.inventory is None:
        assembly_options(model,task)
    with st.expander('修改排版要求，再处理一次') if completed else nullcontext():
        if model.inventory:st.text('当前论文：'+model.display_name+' · 原稿及前轮副本保留')
        from core import effective_rules
        rules=effective_rules(**model._base_rules_arguments(),mode=model.mode)
        is_default=model.custom_rules_path is None and model.active_template is None
        st.write('排版要求：'+('SCUT本科工理类 · 2015年项目材料演示规则' if is_default else rules['name']))
        st.caption('规则版本：'+str(rules['version'])+('。2015年材料，不宣称现行通用校规。' if is_default else '。沿用已生效配置和来源。')+'未规定的属性不自动补齐。')
        from .requirements_ui import render_requirements
        extra,requirements,requirements_ready=render_requirements(model,task,state)
        st.caption('开始即授权本方案的安全修改。需要AI时发送有限脱敏文字摘录或上传的要求，排版在本机完成；脱敏不保证彻底匿名。无API时保留可靠本地处理。')
        native_output=st.checkbox('同时生成Word原生预览和PDF',value=False,key='onepass-native-'+task,help='在最终DOCX完成后后台导出；不改DOCX，不更新额外域。Word不可用时DOCX仍可下载。')
        valid=model.inventory is not None and current(model,state,extra,requirements)
        def progress(name):status.update(label=name);status.write(name)
        if st.button('开始智能排版',key='onepass-start',type='primary',width='stretch',disabled=model.inventory is None or not requirements_ready or (valid and state.get('status') in ('done','waiting','running','updating'))):
            with st.status('识别论文内容',expanded=True) as status:
                state['native_output_requested']=native_output
                start(model,state,extra,requirements=requirements,requirements_cache=st.session_state.setdefault('requirements-cache-'+task,{}),emit=progress)
                state['native_output_requested']=native_output
                status.update(label='有少量事项需要您决定' if state.get('status')=='waiting' else '整理完成' if state.get('status')=='done' else '本次未完成',state='error' if state.get('status')=='failed' else 'complete')
            st.rerun()
    if (state.get('start') or state.get('post')) and not valid and model.inventory:
        st.info('论文、要求或已有设置发生变化，请重新开始；旧处理结果不能用于本次操作。')
    if valid and state.get('status')=='waiting':
        st.subheader('请帮助确认这几处')
        st.caption('只询问影响修改、目前无法可靠判断的事项。回答后继续，不重新发送全部摘录。')
        if state.get('audit',{}).get('requirements_not_applied'):
            st.write('文件中本次不会执行的内容：')
            for note in state['audit']['requirements_not_applied']:st.text((note.get('location') or '提取范围')+' · '+note['text']+' · '+note['reason'])
            with st.expander('本次可以执行的已验证要求'):
                for field in state['audit'].get('API',{}).get('requirements',{}).get('overrides',[]):st.write(field['object_property']+'：'+str(field['value'])+' '+field['unit'])
        decisions={}
        if any(q['id'].startswith('page_') for q in state['questions']):
            st.write('核对本次分区：同一正文起点同时用于分类、章节页脚和编号范围；不会再分别询问。')
        for q in state['questions']:
            with st.container(border=True):
                if q.get('context'):st.text('附近文字：'+q['context'])
                st.text('当前文字：'+q['text']);st.write(q['question'])
                key='onepass-answer-'+state['id']+'-'+q['id']
                choices=q.get('visible_options',list(q['options']))
                if q.get('visible_options'):
                    with st.expander('查看全部文本起点（不是物理页码）'):
                        all_rows=st.checkbox('显示完整起点清单',key=key+'-all')
                    if all_rows:choices=list(q['options'])
                answer=st.selectbox('您的选择',choices,format_func=q['options'].get,index=None,key=key,placeholder='请选择，或暂不处理')
                if answer is not None:decisions[q['id']]=answer
        a,b=st.columns([2,1])
        if a.button('确认并继续',key='onepass-continue',type='primary',disabled=len(decisions)!=len(state['questions']),width='stretch'):
            try:
                with st.status('继续整理',expanded=True) as status:
                    continue_command(model,state,extra,decisions,requirements=requirements,emit=progress)
                    status.update(label='整理完成' if state.get('status')=='done' else '已返回，请修改补充要求' if state.get('status')=='cancelled' else '本次未完成',state='error' if state.get('status')=='failed' else 'complete')
                st.rerun()
            except Exception as exc:st.error(public_error(exc))
        if b.button('取消本次处理',key='onepass-cancel',width='stretch'):cancel(model,state);st.rerun()
    if state.get('status')=='updating':
        from .field_session import JOBS
        @st.fragment(run_every=2)
        def word_progress():
            from .onepass_session import poll_fields
            poll_fields(model,state)
            if state.get('status')!='updating':st.rerun()
            job=state['field_job'];status=job['scheduler'].status(job['owner'],job['identity'])
            st.info('本机Word正在重新分页、更新目录与引用并复查；'+('排队中' if status['state']=='queued' else '正在执行')+'。您仍可查看已有结果。')
            if st.button('取消接收此次Word结果',key='onepass-word-cancel'):
                from .field_session import cancel as cancel_fields
                cancel_fields(job);state['audit']['field_update']={'status':'cancelled','reason':'停止接收结果，不表示Word进程已停止'}
                from .onepass_session import publish
                publish(model,state,state['pending_outcome'],lambda _:None,state['id']);st.rerun()
        word_progress()
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
    field=state.get('audit',{}).get('field_update')
    if field and field.get('status')!='updated':st.warning('目录/引用未完成更新；下载的是此前已验证的排版副本。具体原因及手动办法见完整摘要。')
    if field and field.get('status')=='updated':
        appearances=field.get('validation',{}).get('toc_appearance',[])
        if appearances:
            applied=sum(x['state']=='applied' for x in appearances);kept=sum(x['state']=='already_satisfied' for x in appearances)
            st.caption(f'目录页码已更新并复查；{applied}份目录设置标准外观，{kept}份已有合适外观保持。')
            for item in appearances:
                if item['state']=='kept':st.warning('目录外观保持：'+item.get('reason','无法可靠计算'))
    if state.get('audit',{}).get('page_skipped'):st.warning('页码方案未执行，原页码保持。原因见完整摘要。')
    from .native_output_ui import render_native_output
    render_native_output(model,state)
    from .result_overview import attention,changes_summary
    st.write('主要调整：'+changes_summary(model))
    summary=report['summary']
    st.write(f'剩余 {summary["problem_count"]} 个问题 · {summary["review_count"]} 项待复核。原稿已保留，部分整理不代表全文合格。')
    st.caption('当前处理输入：'+model.display_name+'；查看或下载成果不会自动切换输入。')
    groups=attention(report)
    nonempty=[f'{label} {len(rows)}条' for label,rows in groups.items() if rows]
    if nonempty:st.write('还需留意：'+'；'.join(nonempty)+'。按记录归类，非独立缺陷数。')
    with st.expander('按原因查看剩余记录（完整数量与依据）'):
        for label,rows in groups.items():
            if rows:
                st.write(label+' · '+str(len(rows))+'条')
                # Native table is bounded in height, not hundreds of per-record widgets.
                st.dataframe([{'位置':json.dumps(r.get('locator',{}),ensure_ascii=False),'状态':r.get('status','覆盖提示'),'原因':str(r.get('detail',r.get('reason',''))),'实际':json.dumps(r.get('actual'),ensure_ascii=False),'要求':json.dumps(r.get('expected'),ensure_ascii=False)} for r in rows],hide_index=True,height=min(350,80+len(rows)*35))
    with st.expander('完整处理摘要、范围与更多下载'):
        auxiliary=state.get('audit',{}).get('auxiliaries',[])
        if auxiliary:
            changed=sum(r.get('changes',0) for r in auxiliary);kept=sum(o['status']=='protected' for r in auxiliary for o in r['objects'])
            st.write(f'安全图表与分页辅助：实际修改{changed}项；{kept}条对象/属性保持或待核对。相邻属性不等于实际同页。')
            with st.expander('查看图表与分页处理范围及保持原因'):
                for r in auxiliary:
                    st.write({'position':'题注位置','width':'宽度适配','pagination':'相邻属性及表头'}[r['stage']]+' · '+str(r.get('changes',0))+'项修改')
                    for o in r['objects']:st.text(o['key']+' · '+{'selected':'已处理','protected':'保持/待核对','satisfied':'已满足'}.get(o['status'],o['status'])+' · '+o['reason'])
        n=state['outcome'].get('changes',0);summary=report['summary']
        field_status=state.get('audit',{}).get('field_update')
        if field_status:
            if field_status['status']=='updated':
                c=field_status['counts'];st.write('本机Word已更新目录 '+str(c['TOC'])+' 个、引用 '+str(c['REF']+c['PAGEREF'])+' 个；保持 '+str(field_status['kept_count'])+' 个不支持/受保护对象。最终回填副本经分页和结构复查。')
            else:st.warning('目录/引用未完成更新：'+field_status.get('reason','没有安全可更新对象')+'。下载为已经验证的排版副本。Word中可点入目录→更新目录；在可信文件中选定引用域后更新。')
        if state.get('audit',{}).get('page_skipped'):st.warning('本次未执行页码方案：'+state['audit']['page_skipped'])
        if state.get('audit',{}).get('dynamic_blocked_groups'):st.info('部分编号关联组不能完整安全同步，已保留；详情见处理记录。')
        if model.result and model.result.get('assembly'):
            st.write('本次已验证 '+str(len(model.result['assembly']['steps']))+' 个阶段；普通格式、数字同步和页码结构分别记录，目录/引用的实际更新状态见上方；未执行任意域刷新。')
            with st.expander('各阶段父子关系与未处理事项'):st.json(model.result['assembly'],expanded=False)
        if model.result and model.result.get('kind')=='dynamic_text':st.write('普通格式整理 '+str(n)+' 处；另已明确采用第'+str(model.result['round']['number'])+'轮动态副本，同步 '+str(len(model.result['changes']))+' 处数字。未更新域或真实页码。')
        assembly=model.result.get('assembly') if model.result else None
        if assembly:
            counts={k:sum(x['changes'] for x in assembly['steps'] if x['kind']==k) for k in ('format','dynamic_text','section_pages')}
            st.write('普通格式 '+str(counts['format'])+' 处；编号/文本引用数字 '+str(counts['dynamic_text'])+' 处；页码结构 '+str(counts['section_pages'])+' 项。原稿保留。')
            st.write(f'最终格式检查仍有 {summary["problem_count"]} 个问题、{summary["review_count"]} 项需要留意；不同操作数量不相加为合格分。')
        else:st.write(f'已整理 {n} 处格式；原稿保留。修改后仍有 {summary["problem_count"]} 个问题、{summary["review_count"]} 项需要留意。')
        if model.result and not assembly:
            groups={}
            for c in model.result['changes']:
                rid=c['rule_id'];label='动态题注/纯文本引用数字' if model.result.get('kind')=='dynamic_text' else '页面与边距' if rid in ('R01','R02') else '正文文字与段落' if rid in ('R03','R04','R05','R06','R07','R13') else {'R23':'表内普通文字','R36':'脚注普通文字','R37':'尾注普通文字'}.get(rid,'标题、题注及其他已确认文字')
                groups[label]=groups.get(label,0)+1
            st.write('主要调整：'+'；'.join(f'{k} {v} 处' for k,v in groups.items()))
        scope=(model.result.get('output_classification_manifest') if model.result else model.classification_confirmed) or {}
        tables=scope.get('table_scope',{}).get('table_types',{});notes=scope.get('note_scope',{}).get('objects',[])
        st.write('参与范围：内容表格 '+str(sum(v=='content' for v in tables.values()))+' 张；脚注 '+str(sum(n.startswith('footnote:') for n in notes))+' 条；尾注 '+str(sum(n.startswith('endnote:') for n in notes))+' 条。与顶层段落分别计数，不代表全文覆盖率。')
        coverage=report['coverage'];types=coverage.get('paragraph_types',{})
        count=sum(t in ('other','pending') for t in types.values()) if types else len(coverage.get('unconfirmed_paragraphs',[]))
        st.write(f'还需留意：{count} 段用途未明确或不属普通文字，本次未套普通段落格式。实际分页、目录页码及复杂对象仍需查看。')
        if state.get('audit',{}).get('structure_fallback'):st.info('这次未能完成辅助识别，已整理可靠识别的部分；未确定内容保持。')
        if state.get('audit',{}).get('requirements_not_applied') and not state['audit'].get('file_requirements_declined'):
            st.warning('本次仅执行您同意的已验证文件要求；另有 '+str(len(state['audit']['requirements_not_applied']))+' 项未执行/未提取，不代表已完整采用文件规范。')
        if state.get('audit',{}).get('file_requirements_declined'):st.info('本次按您选择沿用当前要求，未采用上传文件的覆盖。')
        st.caption('部分范围整理不等于全文排版合格。正在处理的输入仍为原文件，未自动切换。')
        st.download_button('保存这套排版要求',model.rule_bundle_download(),file_name='排版要求.json',mime='application/json',on_click='ignore',key='onepass-save-rules')
        st.caption('仅保存规则和规范来源，不含论文或修改授权；下次选择“使用已保存的要求”。')
        st.subheader('更多下载与处理详情')
        if model.result:
            binding=(model._history_binding(),model.result['after']['input_sha256'])
            cached=state.get('download_bundle')
            if st.button('准备完整结果包',key='smart-prepare-package'):
                state['download_bundle']={'binding':binding,'bytes':model.result_package()};cached=state['download_bundle']
            if cached and cached['binding']==binding:st.download_button('下载完整结果包',cached['bytes'],file_name='论文有格_结果.zip',on_click='ignore')
        else:
            reading=model.prepare_reading_export();st.download_button('下载检查阅读报告',reading['report.html'],file_name='检查报告.html',on_click='ignore')
        st.json(state['audit'],expanded=False)
        if model.result and st.checkbox('显示本轮详细工具与下一轮入口',key='smart-full-result-tools'):render_results()
    with st.expander('高级：继续处理题注与文本引用'):
        # Same optional component/transactions as the local workspace. Navigation and
        # ordinary Start never authorize numeric edits or a complete-range declaration.
        if model.report:
            from .dynamic_ui import render_dynamic
            from .onepass_session import register_dynamic_followup
            post=state['post'];parent=model.result['after']['input_sha256'] if model.result else model.inventory['input_sha256']
            render_dynamic(model,on_adopt=lambda:register_dynamic_followup(model,state,post,parent))

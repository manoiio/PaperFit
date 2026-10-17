import streamlit as st
from .issues import CATEGORIES,STATUS,filter_records,group_records,locate
from .center_session import OPERATIONS
from .session import public_error
from .problem_browser_ui import plain_label,full_groups,object_browser,record_browser,status_counts,position_label,attribute_label

ANCHORS={'format':'format-operations','width':'width-operations','pagination':'pagination-operations','preview':'preview-operations'}

def choose_operation(model,value):
    if type(value) is str and value in OPERATIONS:model.operation=value;return True
    return False

def task_header(model):
    if model.report is not None:
        try:
            model._current()
            if model.result is not None:model.downloads()
        except Exception as e:model.error=public_error(e)
    with st.container(key='task-state'):
        title='未选择文件' if model.inventory is None else model.display_name
        state='原稿' if model.current_round==0 else f'第{model.current_round}轮副本'
        rule=model.active_template['name'] if model.active_template else '用户确认的演示规则' if model.active_custom_data else '华工本科工理类2015演示规则'
        st.markdown('**当前任务** · '+title)
        mode_label={'basic':'基础R01–R07','extended':'扩展R01–R12','academic':'单文档R01–R22'}[model.mode]
        st.caption(f"输入：{state} · {mode_label} · {rule} · "+('检查结果有效（文件/规则绑定）' if model.report and model.confirmed else '需要确认范围并检查'))
        if model.inventory is None:st.info('下一步：选择内置样本或上传DOCX。')
        elif model.confirmed is None:st.info('下一步：核对正文或分类，并点击确认。')
        elif model.report is None:st.info('下一步：点击“开始检查”。')
        elif model.result:st.caption(f"本次查看结果：第{model.result['round']['number']}轮输出；当前处理输入仍为{state}，继续处理需明确切换。")
        else:st.caption('下一步：在问题中心查看需要处理的对象，再选择具体操作。')

def reset_filters(model):
    defaults={'category':'全部','status':'需要处理','order':'编号升序','range':'','search':'','type':'全部','page':1}
    for name,value in defaults.items():st.session_state['center-'+name+'-'+str(model.revision)]=value


def render_center(model,selection_renderer=None):
    if model.operation not in OPERATIONS:model.operation='format'
    try:b=model.current_bundle()
    except Exception as e:st.error(public_error(e));return
    from .decision_ui import compact_stats,comparison
    from .workflow_ui import go
    from .report_pages import object_page,selection_counts
    from core.package import sha256
    with st.container(key='issue-center'):
        c=b['context'];p=b['projection'];fs=p['format_summary'];w=p['width_summary'];a=p['pagination_summary']
        fixable=sum(f['status']=='problem' and f['fixable'] for f in b['format']['findings'])
        compact_stats([('发现问题',fs['problem_count']),('其中可修正',fixable),('只读问题',fs['problem_count']-fixable),('待复核',fs['review_count'])],'issues')
        if fs['problem_count']==0:
            st.write(f"已检查范围内未发现格式问题；仍有{fs['review_count']}项待复核。未配置、未检查及实际分页不据此通过。")
        cols=st.columns([1,1.3,.9,1.5])
        states=['需要处理','全部状态']+list(STATUS)
        status=cols[0].selectbox('状态筛选',states,format_func=lambda k:STATUS.get(k,k),key='center-status-'+str(model.revision))
        keyword=cols[1].text_input('关键词筛选',key='center-search-'+str(model.revision),placeholder='例如：字号、缩进、链接')
        with cols[3]:
            # The complete count is the existing selection, never inferred from a filter.
            from .selection_ui import render_selected_list
            render_selected_list(model)
            st.button('前往修正预演',on_click=go,args=(4,),disabled=not model.selected,type='primary',key='problems-to-preview',width='stretch')
        from core.classification import TYPES as PARAGRAPH_TYPES
        TYPES={**PARAGRAPH_TYPES,'footnote':'脚注','endnote':'尾注','table_content':'论文内容表格','table_border':'表格左右外侧边框','cover_title':'封面论文标题','cover_field':'封面字段','section_story':'节与页眉页脚','toc_title':'目录标题','toc_entry':'目录条目','toc_correspondence':'目录对应核对','caption_number':'题注编号','caption_position':'题注结构位置','citation':'正文引文','citation_relation':'引文对应/顺序','internal_reference':'内部引用结构（R44只读）'}
        with cols[2].popover('更多筛选',width='stretch'):
            ca,cb=st.columns(2)
            cat=ca.selectbox('问题类别',['全部']+list(CATEGORIES),format_func=lambda k:CATEGORIES.get(k,k),key='center-category-'+str(model.revision))
            chosen_type=cb.selectbox('确认对象类型筛选',['全部']+list(TYPES),format_func=lambda v:TYPES.get(v,v),key='center-type-'+str(model.revision))
            ca,cb=st.columns(2)
            paragraph_range=ca.text_input('段落编号筛选（如8或8-20）',key='center-range-'+str(model.revision))
            order=cb.selectbox('对象排序',['编号升序','编号降序'],key='center-order-'+str(model.revision))
            st.button('清除筛选',on_click=reset_filters,args=(model,),key='clear-popover-filters')
        from .issues import type_records
        records=type_records(p['records'],b['format']['coverage'],chosen_type)
        desired=['problem','risk','available','review','boundary'] if status=='需要处理' else [] if status=='全部状态' else [status]
        args={'categories':[] if cat=='全部' else [cat],'statuses':desired,'keyword':keyword,'paragraph_range':paragraph_range,'descending':order=='编号降序'}
        identity=(cat,status,order,paragraph_range,keyword,chosen_type)
        page_key='center-page-'+str(model.revision)
        if getattr(model,'center_filter_identity',None)!=identity:
            model.center_filter_identity=identity;st.session_state[page_key]=1
        try:
            first=object_page(records,**args)
            if st.session_state.get(page_key,1)>first['pages']:st.session_state[page_key]=first['pages']
            left,right=st.columns([3,1])
            with right:page=int(st.number_input('对象页码',min_value=1,max_value=first['pages'],value=1,step=1,key=page_key,label_visibility='collapsed',help='对象页码'))
            view=object_page(records,page=page,**args)
        except Exception as e:
            model.center_selection_view=None;st.warning(public_error(e))
            st.button('清除筛选',on_click=reset_filters,args=(model,));return
        model.center_selection_view={**view,'file_sha256':c['file_sha256'],'rules_sha256':c['rules_sha256']}
        counts=selection_counts(model.selected,view)
        left.caption(f"{view['record_count']} 条记录 / {view['object_count']} 个对象 · 第{view['page']}/{view['pages']}页 · 对象{view['start']}–{view['end']}（每页20个） · 本页已选 {counts['page']} · 筛选外仍保留 {counts['outside_filter']}")
        filters=[]
        if cat!='全部':filters.append(CATEGORIES.get(cat,cat))
        if status!='需要处理':filters.append(STATUS.get(status,status))
        if chosen_type!='全部':filters.append(TYPES.get(chosen_type,chosen_type))
        if order!='编号升序':filters.append(order)
        if keyword:filters.append('关键词：'+keyword)
        if paragraph_range:filters.append('段落：'+paragraph_range)
        if filters:st.caption('当前筛选：'+plain_label(' · '.join(filters))+'；清除入口在“更多筛选”，不会清空选择。')
        if view['objects']:
            groups=full_groups(p['records'])
            seed=f"{model.task_dir.name}-{model.revision}-{model.report_revision}-"+sha256(str((c['file_sha256'],c['rules_sha256'],identity,page)).encode())[:16]
            ls,ds=st.columns([1,1.65],gap='medium')
            same_input=c['file_sha256']==model.report['input_sha256']
            with ls:
                chosen=object_browser(view,groups,model.selected,seed,same_input)
            detail=groups[chosen]
            with ds:
                r=record_browser(detail,view['groups'][chosen],seed+'-'+sha256(chosen.encode())[:12])
                comparison(position_label(detail)+' · '+attribute_label(r),r['actual'],r['expected'],r['reason'],STATUS[r['status']],r['action'],key='current-problem')
                eligible={f['key'] for f in model.eligible()}
                if same_input and r['status']=='problem' and r['record_key'] in eligible:
                    selected=r['record_key'] in model.selected
                    st.caption('已加入修正；仅该具体属性。' if selected else '可自动修正；仅明确加入后进入预演，不自动选择同对象其他属性。')
                    st.button('移出修正' if selected else '加入修正',key='choose-record-'+seed+'-'+r['id'],on_click=lambda k=r['record_key'],v=selected:model.set_selection([x for x in model.selected if x!=k] if v else model.selected+[k]),type='secondary' if selected else 'primary')
                elif not same_input:st.caption('当前查看输出副本；须明确以此副本继续后再选择修正。')
                elif r['status'] in ('risk','available'):st.caption('本项不进入普通格式修正；可按处理方式进入原有宽度/排版辅助，仍需单独确认。')
                else:st.caption('只读问题或待复核，不能自动修正。' if r['status'] in ('problem','review','boundary') else '本记录无需格式修正。')
                with st.expander('当前检查项的依据与定位'):
                    st.text(r['position']);st.text(r['basis']);st.text(r['record_key'])
            with st.expander('此对象的全部记录与依据'):
                st.caption(f"对象 {chosen} 全部 {len(detail)} 条记录（包括当前筛选隐藏的状态）。切换顶部全部状态可逐项查看符合/不适用；技术表仅明确载入后生成。")
                if st.toggle('载入此对象完整技术记录',key='object-raw-'+seed):
                    st.dataframe([{'检查项':r['title'],'状态':STATUS[r['status']],'位置':r['position'],'实际':r['actual'],'要求/建议':r['expected'],'原因':r['reason'],'操作':r['action'],'依据':r['basis'],'记录key':r['record_key']} for r in detail],hide_index=True,width='stretch')
                for area,category in [('format','format'),('width','width'),('pagination','pagination')]:
                    actionable=[r for r in detail if r['category']==category and r['status'] in ('problem','risk','available') and '不自动' not in r['action']]
                    if actionable and st.button('查看此对象的'+OPERATIONS[area]+'步骤',key='detail-guide-'+area+'-'+seed):
                        model.focus_operation(area,b['target'],[r['record_key'] for r in actionable]);st.rerun()
        else:
            from .workflow_ui import empty_state
            empty_state('当前筛选没有记录', '可清除筛选查看其他对象。此处为空不表示文档没有问题或全文合格；筛选外的明确选择仍保留。')
            st.button('清除筛选',on_click=reset_filters,args=(model,),key='clear-empty-filters')
        if selection_renderer:selection_renderer()
        with st.expander('建议下一步与其他操作（不自动执行）'):
            for i,step in enumerate(b['steps']):
                if st.button(step['title'],key=f'guide-{model.task_dir.name}-{model.revision}-{model.generation_count}-{i}'):
                    model.focus_operation(step['area'],b['target'],step['keys']);st.rerun()
                st.caption(step['reason'])
            st.session_state[f'operation-{model.revision}-{model.generation_count}']=model.operation
            st.selectbox('操作区域',list(OPERATIONS),format_func=OPERATIONS.get,key=f'operation-{model.revision}-{model.generation_count}',on_change=lambda:choose_operation(model,st.session_state[f'operation-{model.revision}-{model.generation_count}']))
            if model.focus:st.info('查看对象：'+(', '.join(model.focus['keys']) or '本轮文件')+'；尚未勾选或执行。')
            if model.operation=='format' and model.result and b['format']['summary']['problem_count']:
                st.button('以本轮修正版继续处理',on_click=model.next_round,type='primary')
        with st.expander('统计口径、符合/不适用与支持边界'):
            st.caption(f"当前查看：{'原稿' if c['round']==0 else '第'+str(c['round'])+'轮副本'} · {b['format']['rules']['name']} v{b['format']['rules']['version']}")
            st.write((f"宽度风险 {w['risks']} / 宽度待复核 {w['reviews']}" if w else '宽度未检查')+' · '+(f"分页建议 {a['suggestions']} / 关联待复核 {a['reviews']}" if a else '分页建议未检查'))
            st.caption('格式待复核含覆盖提示；四类数量分别计数，不相加为合格分数。问题不等于可修正；建议不等于确定错误。')
            st.write('符合记录 '+str(sum(r['status']=='pass' for r in p['records']))+'；不适用记录 '+str(sum(r['status']=='not_applicable' for r in p['records'])))
            if b['format'].get('internal_references'):
                ir=b['format']['internal_references'];st.write(f"R44产品结构检查：{sum(g['status']=='problem' for g in ir['groups'])}个确定目标故障组、{len(ir['references'])}处引用；目标、缓存、跳转和实际页码分别核对。")
            if st.toggle('查看全部边界说明',key='show-boundaries-'+str(model.revision)):
                st.dataframe([{'边界':r['reason']} for r in p['records'] if r['status']=='boundary'],hide_index=True,width='stretch')
        with st.expander('导出可阅读报告（离线HTML）',key='reading-export'):render_reading_export(model)


def render_history(model):
    rows=model.history_rows()
    if not rows:return
    with st.container(key='history-center'):
        st.markdown('<span id="history-operations"></span>',unsafe_allow_html=True)
        st.subheader('处理历史 · 查看不会切换当前输入')
        st.dataframe([{'输入 → 输出':('原稿' if r.get('input_round')==0 else '第'+str(r.get('input_round','—'))+'轮')+' → 第'+str(r['round'])+'轮','操作':r['operation'],'状态':r['status'],'结果':'；'.join(f'{k} {v}' for k,v in r['counts'].items())} for r in rows],hide_index=True,width='stretch')
        if st.toggle('查看某轮详情与下载',key='history-view-'+str(model.revision)):
            lookup={r['id']:r for r in rows};identity=st.selectbox('查看历史轮次',list(lookup),key='history-object-'+model.task_dir.name,format_func=lambda k:f"第{lookup[k]['round']}轮 · {lookup[k]['operation']} · {lookup[k]['status']}")
            row=lookup[identity]
            if not row['downloadable']:st.warning(row['status']);return
            try:
                b=model.history_bundle(identity);data=model.history_reading_downloads(identity)
                st.write(f"正在查看：历史第{row['round']}轮记录；当前输入仍为"+('原稿' if model.current_round==0 else f'第{model.current_round}轮副本'))
                st.caption('历史配置：'+b['format']['rules']['name']+' v'+b['format']['rules']['version']+'；'+row['status'])
                st.write(f"历史格式剩余 {b['format']['summary']['problem_count']}，待复核 {b['format']['summary']['review_count']}；不是当前输入报告。")
                if b.get('saved_record'):
                    with st.expander('保存时记录（未作为本次完整性或视觉验收）'):st.json(b['saved_record'])
                for name,raw in data.items():st.download_button('下载历史第'+str(row['round'])+'轮 '+name,raw,file_name='论文有格_历史第'+str(row['round'])+'轮_'+name,on_click='ignore',key='history-new-'+identity+'-'+name)
                st.caption('查看历史不会切换当前输入。继续时将采用该轮保存的规则和范围，重新确认与检查。')
                ack=st.checkbox('我已核对该历史轮次的规则和范围',key='history-continue-ack-'+identity)
                def continue_saved():
                    try:
                        if model.continue_history(identity,acknowledged=True):
                            st.session_state['check-mode']={'basic':'基础检查','extended':'正文及标题题注检查','academic':'单文档扩展检查'}[model.mode]
                    except Exception as e:model.error=public_error(e)
                st.button('以历史第'+str(row['round'])+'轮继续处理',disabled=not ack,on_click=continue_saved,key='history-continue-'+identity)
            except Exception as e:st.warning(public_error(e))


def render_reading_export(model):
    st.caption('默认匿名显示名称、无论文原文、无私人路径；完整旧JSON/Markdown仍在高级下载。报告不证明Word或全文合格。')
    name=st.text_input('报告显示名称（建议脱敏）',value='待检查文档.docx',key='reading-name')
    excerpts=st.checkbox('包含少量短原文（可能含个人信息，默认关闭）',key='reading-excerpts')
    if st.button('准备可阅读报告',key='reading-prepare'):
        try:model.prepare_reading_export(name,excerpts)
        except Exception as e:st.error(public_error(e))
    try:downloads=model.reading_downloads()
    except Exception as e:st.warning(public_error(e));downloads={}
    for filename,data in downloads.items():
        st.download_button('下载阅读报告'+filename.removeprefix('report'),data,file_name='论文有格_'+filename,mime={'html':'text/html','md':'text/markdown','json':'application/json'}[filename.split('.')[-1]],on_click='ignore',key='reading-'+filename+'-'+str(model.revision)+'-'+str(model.generation_count))

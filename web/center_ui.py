import streamlit as st
from .issues import CATEGORIES,STATUS,filter_records,group_records,locate
from .center_session import OPERATIONS
from .session import public_error

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

def render_center(model):
    if model.operation not in OPERATIONS:model.operation='format'
    try:b=model.current_bundle()
    except Exception as e:st.error(public_error(e));return
    with st.container(key='issue-center'):
        st.subheader('统一问题中心')
        c=b['context'];st.caption(f"当前查看：{'原稿' if c['round']==0 else '第'+str(c['round'])+'轮副本'} · 规则 {b['format']['rules']['name']} v{b['format']['rules']['version']}")
        p=b['projection'];fs=p['format_summary'];w=p['width_summary'];a=p['pagination_summary']
        st.write(f"格式问题 {fs['problem_count']} · 格式待复核 {fs['review_count']}（含规则记录与覆盖提示） · "+(f"宽度风险 {w['risks']} / 宽度待复核 {w['reviews']}" if w else '宽度未检查')+' · '+(f"分页建议 {a['suggestions']} / 关联待复核 {a['reviews']}" if a else '分页建议未检查'))
        st.caption('数字分别来自各报告，不能相加为总问题数或合格分数；同一对象可有多种记录。建议不是确定错误，支持边界不计为新增问题。')
        with st.container(key='next-step'):
            st.markdown('**建议下一步（导航，不自动执行）**')
            for i,step in enumerate(b['steps']):
                if st.button(step['title'],key=f'guide-{model.task_dir.name}-{model.revision}-{model.generation_count}-{i}'):
                    model.focus_operation(step['area'],b['target'],step['keys']);st.rerun()
                st.caption(step['reason']+(' 本轮仍有格式问题，需点击“以本轮修正版继续处理”绑定新的输入。' if step['requires_next_round'] else ''))
        from .report_pages import object_page,selection_counts
        from core.package import sha256
        cols=st.columns(3)
        cat=cols[0].selectbox('问题类别',['全部']+list(CATEGORIES),format_func=lambda k:CATEGORIES.get(k,k),key='center-category-'+str(model.revision))
        states=['需要处理','全部状态']+list(STATUS)
        status=cols[1].selectbox('状态筛选',states,format_func=lambda k:STATUS.get(k,k),key='center-status-'+str(model.revision))
        order=cols[2].selectbox('对象排序',['编号升序','编号降序'],key='center-order-'+str(model.revision))
        range_col,search_col=st.columns(2)
        paragraph_range=range_col.text_input('段落编号筛选（如8或8-20）',key='center-range-'+str(model.revision))
        keyword=search_col.text_input('关键词筛选',key='center-search-'+str(model.revision))
        from core.classification import TYPES as PARAGRAPH_TYPES
        TYPES={**PARAGRAPH_TYPES,'footnote':'脚注','endnote':'尾注','table_content':'论文内容表格','table_border':'表格左右外侧边框','cover_title':'封面论文标题','cover_field':'封面字段','section_story':'节与页眉页脚','toc_title':'目录标题','toc_entry':'目录条目','toc_correspondence':'目录对应核对','caption_number':'题注编号','caption_position':'题注结构位置','citation':'正文引文','citation_relation':'引文对应/顺序'}
        chosen_type=st.selectbox('确认对象类型筛选',['全部']+list(TYPES),format_func=lambda v:TYPES.get(v,v),key='center-type-'+str(model.revision))
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
            page=int(st.number_input('对象页码',min_value=1,max_value=first['pages'],value=1,step=1,key=page_key))
            view=object_page(records,page=page,**args)
        except Exception as e:
            model.center_selection_view=None;st.warning(public_error(e));return
        model.center_selection_view={**view,'file_sha256':c['file_sha256'],'rules_sha256':c['rules_sha256']}
        st.caption(f"筛选共 {view['record_count']} 条记录 / {view['object_count']} 个对象；第{view['page']}/{view['pages']}页，显示对象{view['start']}–{view['end']}（每页20个）。原始结果与完整导出不受分页影响。")
        counts=selection_counts(model.selected,view)
        st.caption(f"本页已选 {counts['page']} · 全部已选 {counts['all']} · 当前筛选外仍保留 {counts['outside_filter']}；翻页或筛选不会授权新修正。")
        if view['objects']:
            summary=[]
            for obj in view['objects']:
                records=view['groups'][obj]
                summary.append({'对象':records[0]['position'].split(' · ')[0],'短文本':records[0]['excerpt'],
                    '格式问题':sum(r['category']=='format' and r['status']=='problem' for r in records),
                    '待复核/边界':sum(r['status'] in ('review','boundary') for r in records),
                    '宽度风险':sum(r['status']=='risk' for r in records),'分页建议':sum(r['status']=='available' for r in records),'筛选记录数':len(records)})
            st.dataframe(summary,hide_index=True,width='stretch',height=min(500,40+len(summary)*35))
            detail_key='object-detail-'+str(model.revision)+'-'+sha256(str(identity).encode())[:10]+'-'+str(page)
            chosen=st.selectbox('查看所选对象详情',view['objects'],format_func=lambda k:locate({'note_kind':k.split(':')[0],'note_id':k.split(':')[1]}) if k.startswith(('footnote:','endnote:')) else locate({k.split(':')[0]:k.split(':')[1]}) if ':' in k else '主文档',key=detail_key)
            detail=[r for r in p['records'] if r['object']==chosen]
            with st.expander('此对象的全部记录与依据',expanded=True):
                st.caption(f"对象 {chosen} 全部 {len(detail)} 条记录（包括当前筛选隐藏的状态）。")
                st.dataframe([{'检查项':r['title'],'状态':STATUS[r['status']],'位置':r['position'],'实际':r['actual'],'要求/建议':r['expected'],'原因':r['reason'],'操作':r['action'],'依据':r['basis'],'记录key':r['record_key']} for r in detail],hide_index=True,width='stretch')
                for area,category in [('format','format'),('width','width'),('pagination','pagination')]:
                    actionable=[r for r in detail if r['category']==category and r['status'] in ('problem','risk','available') and '不自动' not in r['action']]
                    if actionable and st.button('查看此对象的'+OPERATIONS[area]+'步骤',key='detail-guide-'+area+'-'+detail_key):
                        model.focus_operation(area,b['target'],[r['record_key'] for r in actionable]);st.rerun()
        else:st.info('当前筛选没有记录；不表示全文合格。符合、不适用与全部边界可通过状态筛选按页查看。')
        with st.expander('符合、不适用与全部支持边界'):
            st.caption('完整记录保留；选择对应状态后按页查看。')
            st.write('符合记录 '+str(sum(r['status']=='pass' for r in p['records']))+'；不适用记录 '+str(sum(r['status']=='not_applicable' for r in p['records'])))
            if st.toggle('查看全部边界说明',key='show-boundaries-'+str(model.revision)):
                st.dataframe([{'边界':r['reason']} for r in p['records'] if r['status']=='boundary'],hide_index=True,width='stretch')
        st.markdown('**当前操作**')
        st.session_state[f'operation-{model.revision}-{model.generation_count}']=model.operation
        st.selectbox('操作区域',list(OPERATIONS),format_func=OPERATIONS.get,index=list(OPERATIONS).index(model.operation),key=f'operation-{model.revision}-{model.generation_count}',on_change=lambda:choose_operation(model,st.session_state[f'operation-{model.revision}-{model.generation_count}']))
        if model.focus:
            st.info('查看对象：'+(', '.join(model.focus['keys']) or '本轮文件')+'；尚未勾选或执行。')
        if model.operation=='format' and model.result and b['format']['summary']['problem_count']:
            st.button('以本轮修正版继续处理',on_click=model.next_round,type='primary',help='明确把本轮输出设为下一轮输入，其他操作只查看，不切换输入。')
        st.markdown('[进入当前操作区域](#'+ANCHORS[model.operation]+')')
        with st.expander('导出可阅读报告（离线HTML）',key='reading-export'):
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


def render_history(model):
    rows=model.history_rows()
    if not rows:return
    with st.container(key='history-center'):
        st.markdown('<span id="history-operations"></span>',unsafe_allow_html=True)
        st.subheader('处理历史 · 查看不会切换当前输入')
        st.dataframe([{'轮次':r['round'],'操作':r['operation'],'输入轮次':r.get('input_round','—'),'状态':r['status'],'结果':'；'.join(f'{k} {v}' for k,v in r['counts'].items())} for r in rows],hide_index=True,width='stretch')
        if st.toggle('查看某轮详情与下载',key='history-view-'+str(model.revision)):
            lookup={r['id']:r for r in rows};identity=st.selectbox('查看历史轮次',list(lookup),format_func=lambda k:f"第{lookup[k]['round']}轮 · {lookup[k]['operation']} · {lookup[k]['status']}")
            row=lookup[identity]
            if not row['downloadable']:st.warning(row['status']);return
            try:
                b=model.history_bundle(identity);data=model.history_reading_downloads(identity)
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

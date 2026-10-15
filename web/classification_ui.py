"""建议可编辑；只有明确确认后的类型进入引擎。"""
import streamlit as st
from core.classification import TYPES
from .presentation import short
from .session import public_error

REVERSE={v:k for k,v in TYPES.items()}

def render_classification(model, run_check):
    def confirm():
        try:model.confirm_classification()
        except Exception as exc:model.error=public_error(exc)
    def edited(key,numbers):
        items=model.paragraph_types.copy()
        for row,patch in st.session_state[key].get('edited_rows',{}).items():
            if '核对类型' in patch:items[str(numbers[int(row)])]=REVERSE[patch['核对类型']]
        model.set_types(items)
    prefix=f'{model.task_dir.name}-{model.current_round}'
    def quick_change():
        items=model.paragraph_types.copy()
        items[str(st.session_state['type-index-'+prefix])]=REVERSE[st.session_state['type-value-'+prefix]]
        model.set_types(items)
    with st.container(key='classification'):
        st.subheader('2 核对段落分类')
        st.caption('编号是主文档顶层段落编号，含空段和图片段，不是页码；表格内段落不在此清单中。')
        st.info('当前分类已经人工确认并应用范围。调整后旧报告与下载失效；待确认项仍跳过。' if model.classification_confirmed else
                '以下是确定性建议，尚未自动应用。只有用户确认后的分类决定检查与修正范围；待确认项跳过并报告。没有概率置信度。')
        suggestions={p['index']:p for p in model.suggestions['paragraphs']}
        all_rows=st.toggle('查看全部段落',key='all-types-'+prefix)
        rows=[];numbers=[]
        for p in model.inventory['paragraphs']:
            n=p['index'];s=suggestions[n];typ=model.paragraph_types[str(n)]
            if not all_rows and not (s['ambiguous'] or typ!=s['suggested_type'] or typ.startswith('heading') or typ.endswith('_caption') or (model.mode=='academic' and typ in ('abstract_cn_title','abstract_cn_body','abstract_en_title','abstract_en_body','keywords_cn','keywords_en','reference_title','reference_item','appendix_title','appendix_text','ack_title','ack_text'))):continue
            rows.append({'编号':n,'简短文本':short(p['text'],48),'当前样式':p['style_id'] or '默认',
                         '建议类型':TYPES[s['suggested_type']],'核对类型':TYPES[typ],
                         '建议理由':s['reason'],'歧义':'需核对' if s['ambiguous'] else '未发现冲突'})
            numbers.append(n)
        key='classification-editor-'+prefix+'-'+str(model.revision)
        st.data_editor(rows,hide_index=True,width='stretch',height=min(650,max(170,len(rows)*36+40)),
                       disabled=['编号','简短文本','当前样式','建议类型','建议理由','歧义'],
                       column_config={'核对类型':st.column_config.SelectboxColumn('核对类型',options=list(TYPES.values()),required=True,width='small')},
                       key=key,on_change=edited,args=(key,numbers))
        st.caption('默认显示标题、题注、前后置章节、歧义及已调整项；打开“查看全部段落”可核对正文和排除范围。可直接编辑表中“核对类型”。')
        with st.expander('按编号快速调整分类'):
            options=[p['index'] for p in model.inventory['paragraphs']]
            st.selectbox('调整段落编号',options,format_func=lambda n:f"段 {n} · {short(model.inventory['paragraphs'][n-1]['text'],38) or '（空段或图片段）'}",key='type-index-'+prefix)
            st.selectbox('调整为',list(TYPES.values()),key='type-value-'+prefix)
            st.button('应用分类调整',on_click=quick_change)
        with st.expander('批量调整与恢复初始建议'):
            selected_types=st.multiselect('按当前类型筛选候选段落',list(TYPES),format_func=TYPES.get,key='batch-filter-'+prefix)
            ambiguous_only=st.checkbox('仅显示原建议有歧义的候选',key='batch-ambiguity-'+prefix)
            candidates=model.classification_candidates(selected_types,ambiguous_only)
            st.caption('筛选只缩小候选列表，不代表选中。按稳定编号处理，与表格排序无关。')
            chosen=st.multiselect('明确选择需要调整的段落',candidates,format_func=lambda n:f'段 {n} · '+short(model.inventory['paragraphs'][n-1]['text'],32),key='batch-numbers-'+prefix+'-'+str(model.revision))
            ranges=st.text_input('或输入编号范围（例如4-6,11）',key='batch-range-'+prefix+'-'+str(model.revision))
            try:numbers=sorted(set(chosen+model.parse_paragraph_ranges(ranges)))
            except Exception as exc:st.warning(public_error(exc));numbers=[]
            st.write(f'待修改 {len(numbers)} 个段落；仅更新分类草稿，仍需核对确认。')
            if numbers:st.dataframe([{'编号':n,'短文本':short(model.inventory['paragraphs'][n-1]['text'],40),'当前类型':TYPES[model.paragraph_types[str(n)]]} for n in numbers],hide_index=True,width='stretch')
            target=st.selectbox('批量目标类型',list(TYPES),index=None,format_func=TYPES.get,key='batch-target-'+prefix)
            if st.button('应用到明确选中的段落',disabled=not numbers or target is None):
                try:model.batch_types(numbers,target);st.rerun()
                except Exception as exc:st.error(public_error(exc))
            adjustments=model.initial_adjustments()
            st.caption('恢复将覆盖人工调整编号：'+(', '.join(map(str,adjustments)) or '无'))
            restore=st.checkbox('已核对上述覆盖范围，确认恢复初始建议',key='restore-types-'+prefix+'-'+str(model.revision))
            if st.button('恢复当前文件的初始建议',disabled=not restore or not adjustments):
                model.restore_types(confirmed=True);st.rerun()
        from .material_ui import render_materials
        render_materials(model)
        pending=[n for n,t in model.paragraph_types.items() if t=='pending']
        if pending:st.warning('仍为待确认的段落：'+', '.join(pending)+'；确认后这些段落也不会自动套格式。')
        ambiguous=[str(p['index']) for p in model.suggestions['paragraphs'] if p['ambiguous']]
        if ambiguous:st.caption('请特别核对原建议有歧义的段落：'+', '.join(ambiguous)+'。点击确认表示已核对整份当前分类。')
        st.caption('已确认分类，绑定当前文件与规则。' if model.classification_confirmed else '分类尚未确认；改分类、文件或模式后需重新确认。')
        st.caption('快捷按钮表示本人已核对整份当前分类，包括歧义与待确认项；这些提示不会因此变成通过。')
        st.button('核对完成并开始检查',on_click=model.confirm_and_check,type='primary',width='stretch')
        a,b=st.columns(2)
        a.button('确认分类并应用范围',on_click=confirm,width='stretch')
        b.button('开始检查',on_click=run_check,disabled=model.classification_confirmed is None,width='stretch')

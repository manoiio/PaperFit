"""Readable paragraph context; stable indices and existing model callbacks only."""
import streamlit as st
from core.classification import TYPES
from core.package import sha256
from .session import public_error
from .presentation import short

def render_detail(model,prefix,suggestions):
    paragraphs={p['index']:p for p in model.inventory['paragraphs']}
    feedback='classification-feedback-'+prefix
    if st.session_state.get(feedback):st.info(st.session_state[feedback])
    a,b=st.columns([1.2,1.8])
    with a:
        word=st.text_input('查找段落内容',key='class-word-'+prefix)
        kinds=st.multiselect('按当前草稿分类筛选',list(TYPES),format_func=TYPES.get,key='class-filter-'+prefix)
        ids=[n for n,p in paragraphs.items() if (not word or word.casefold() in p['text'].casefold()) and (not kinds or model.paragraph_types[str(n)] in kinds)]
        st.caption(f'筛选到{len(ids)}段；查看或筛选不改变分类。')
        if not ids:st.info('当前筛选没有段落，其他段落的草稿仍保留。');return
        pages=max(1,(len(ids)+19)//20)
        signature=(word,tuple(kinds))
        page_key='class-page-'+prefix
        identity='class-filter-identity-'+prefix
        if st.session_state.get(identity)!=signature:st.session_state[identity]=signature;st.session_state[page_key]=1
        if st.session_state.get(page_key,1)>pages:st.session_state[page_key]=pages
        page=st.number_input('段落列表页码',min_value=1,max_value=pages,value=1,key=page_key)
        visible=ids[(page-1)*20:page*20]
        n=st.selectbox('查看段落',visible,format_func=lambda n:f'段{n} · {TYPES[model.paragraph_types[str(n)]]} · '+(short(paragraphs[n]['text'],22) or '空段/特殊对象'),key='class-object-'+prefix+'-'+str(page)+'-'+sha256(repr(signature).encode())[:12])
        st.caption(f'第{page}/{pages}页 · 本页{len(visible)}段；编号始终对应当前DOCX顶层段落。')
    with b:
        p=paragraphs[n];suggestion=suggestions[n];current=model.paragraph_types[str(n)]
        st.markdown(f'**段 {n} · 完整文本**')
        st.text(p['text'] if p['text'] else '（此顶层段落没有可读取的文字，可能为空段或包含图片等对象。）')
        st.caption('这是文本上下文，不是Word页面预览。')
        x,y=st.columns(2);x.write('原建议：**'+TYPES[suggestion['suggested_type']]+'**');y.write('当前草稿：**'+TYPES[current]+'**')
        if str(n) in model.material_exclusions:st.warning('材料已保护：'+model.material_exclusions[str(n)]+'。需明确解除保护后才可纳入普通文字。')
        elif current!=suggestion['suggested_type']:st.caption('当前草稿与原建议不同；仍须最终范围确认。')
        if p['special']:st.caption('结构提示：'+str(p['special'])+'；用途确认不绕过引擎保护。')
        target=st.selectbox('本段草稿分类',list(TYPES),index=list(TYPES).index(current),format_func=TYPES.get,key='class-target-'+prefix+'-'+str(model.revision)+'-'+str(n))
        def save():
            try:
                model.batch_types([n],target)
                st.session_state[feedback]=f'已保存段{n}分类草稿：{TYPES[model.paragraph_types[str(n)]]}；未执行范围确认，实际状态见总览。'
            except Exception as e:model.error=public_error(e);return False
            return True
        def save_return():
            if save():st.session_state['workspace-scope-editor']=False
        st.button('保存本段分类草稿',on_click=save,disabled=str(n) in model.material_exclusions,key='class-save-'+prefix+'-'+str(n),type='primary')
        st.button('保存本段分类草稿并返回范围总览',on_click=save_return,disabled=str(n) in model.material_exclusions,key='class-return-'+prefix+'-'+str(n))
        with st.expander('相邻段落与建议依据'):
            st.write('原建议依据：'+suggestion['reason']);st.caption('当前样式：'+(p['style_id'] or '默认段落样式'))
            for k in (n-1,n+1):
                if k in paragraphs:
                    st.markdown(f'**相邻段 {k} · {TYPES[model.paragraph_types[str(k)]]}**');st.text(paragraphs[k]['text'] or '（无可读取文字）')

"""Presentation-only five-step navigation. No engine, scope or adoption decisions."""
from html import escape
import streamlit as st

STEPS={1:'文档与要求',2:'确认检查范围',3:'查看问题',4:'修正预演',5:'结果与下载'}
# Explicit editor-only keepalive. Never retain acknowledgements, actions, uploads,
# data-editor patches or execution authorization. Business drafts remain on model.
EDITOR_PREFIXES=('workspace-rule-entry','diag-edit-','diag-field','diag-issue','diag-detail','diag-modules','diag-states','diag-value-','diag-unit-','diag-quote-','diag-location-','diag-issue-','diag-reason-','wb-value-','wb-edit-mode-','wb-module-','wb-field-','wb-show-missing-',
 'wb-policy-','wb-name-','wb-text-','tpl-value-','tpl-mode-','template-name-',
 'norm-text-','norm-encoding','center-category-','center-status-','center-order-',
 'center-range-','center-search-','center-type-','center-page-','object-detail-',
 'batch-filter-','batch-numbers-','batch-range-','batch-target-','batch-ambiguity-',
 'front-object-','front-type-','front-section-','front-role-','front-value-','front-prop-enabled-',
 'note-kind-','note-word-','note-selected-','note-mode-','note-value-',
 'material-ids-','material-range-','material-reason-','material-release-',
 'toc-objects-','toc-role-','toc-field-','toc-value-','toc-prop-',
 'citation-word-','citation-filter-','citation-ids-','citation-target-',
 'caption-search-','caption-chapters-','reference-kind-','reference-state-','reference-word-',
 'table-id-','table-header-count-',
 'type-index-','type-value-','all-types-','reading-name','reading-excerpts')

def preserve_editors():
    # Documented Streamlit widget cleanup interruption; values stay session-local.
    for key in list(st.session_state):
        if key.startswith(EDITOR_PREFIXES) and 'ack' not in key:
            st.session_state[key]=st.session_state[key]

def go(step):
    if step in STEPS:
        st.session_state['workspace-step']=step
        if step==2:st.session_state['workspace-scope-editor']=False

def availability(model):
    return {1:True,2:model.inventory is not None,3:model.report is not None,
            4:model.report is not None,5:model.report is not None or bool(model.history)}

CSS='''<style>
.stApp {background:#f4f6f9;color:#182b41;}
.block-container {max-width:1200px;padding-top:4.5rem;padding-bottom:3rem;}
h1 {font-size:1.65rem !important;font-weight:700;color:#183650;}
h2 {font-size:1.4rem !important;color:#183650;}
h3 {font-size:1.12rem !important;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:12px;background:white;}
[data-testid="stExpander"] {background:white;border-radius:10px;}
[data-testid="stMetricValue"] {font-size:1.8rem;color:#204c79;}
[data-testid="stCaptionContainer"] {font-size:.88rem;color:#536477;}
.st-key-workspace-nav button {min-height:50px;border-radius:9px;font-size:.92rem;}
.st-key-file-summary {padding:.85rem 1rem;border:1px solid #dce3eb;border-radius:10px;background:white;margin-bottom:.8rem;}
.st-key-document-card {background:white;border-radius:12px;}
.st-key-workspace-nav {margin:.3rem 0 1rem;}
.report-scroll {overflow-x:auto;}
.report-table {border-collapse:collapse;width:100%;font-size:14px;line-height:1.6;}
.report-table td,.report-table th {padding:9px;border-bottom:1px solid #e1e7ee;text-align:left;overflow-wrap:anywhere;}
.report-table th {background:#edf2f7;color:#183650;}
[id^="scope-"] {scroll-margin-top:80px;}
</style>'''

def shell(model,restart):
    st.markdown(CSS,unsafe_allow_html=True)
    identity=(str(model.task_dir),model.current_round)
    if st.session_state.get('workspace-identity')!=identity:
        st.session_state['workspace-identity']=identity
        go(5 if model.result else 3 if model.report else 2 if model.inventory else 1)
        st.session_state['workspace-last-report']=id(model.report) if model.report else None
        st.session_state['workspace-last-result']=model.generation_count
    # Successful business callbacks can advance the view; failed calls never do.
    report_id=id(model.report) if model.report else None
    if report_id and report_id!=st.session_state.get('workspace-last-report'):go(3)
    if model.result and model.generation_count!=st.session_state.get('workspace-last-result'):go(5)
    st.session_state['workspace-last-report']=report_id
    st.session_state['workspace-last-result']=model.generation_count
    ready=availability(model)
    step=st.session_state.get('workspace-step',1)
    if not ready.get(step):step=2 if model.inventory else 1;go(step)
    title,reset=st.columns([8,1])
    title.title('论文有格')
    reset.button('重新开始',on_click=restart,width='stretch')
    with st.container(key='file-summary'):
        if model.inventory:
            current='原稿' if model.current_round==0 else f'第{model.current_round}轮副本'
            rule=model.current_rule_bundle()['name'] if model.mode=='academic' else model.active_template['name'] if model.active_template else '华工本科工理类2015演示规则'
            st.markdown('**'+escape(model.display_name)+'** · 当前输入：'+current)
            state=f"；另有第{model.result['round']['number']}轮输出，尚未切换" if model.result else '；预演待采用，正式轮次保持' if model.rehearsal else ''
            st.caption(f"{len(model.inventory['paragraphs'])} 个顶层段落 · {model.inventory['section_count']} 节 · {len(model.input_bytes)/1024:.1f} KB · 规则：{rule}{state}")
        else:st.write('本地处理 Word 论文 · 先选文档，再核对要求与范围')
    with st.container(key='workspace-nav'):
        for col,(n,label) in zip(st.columns(5),STEPS.items()):
            status='当前' if n==step else '暂不可用' if not ready[n] else '已检查' if n==2 and model.report else '已有结果' if n==5 and model.result else '可查看' if n<step else '待处理'
            col.button(f'{n} {label} · {status}',key=f'workspace-nav-{n}',disabled=not ready[n],type='primary' if step==n else 'secondary',on_click=go,args=(n,),width='stretch')
    return step

def render_rules(model,root):
    st.subheader('格式要求')
    st.caption('默认沿用当前生效规则。编辑草稿不会生效，只有明确确认应用才改变检查要求。')
    choice=st.radio('本次规则操作',['使用当前规则','导入规则包 / 编辑规则','AI解析公开规范'],key='workspace-rule-entry',horizontal=True)
    if choice!='使用当前规则':
        if model.mode=='academic':
            from .workbench_ui import render_workbench
            render_workbench(model,root)
        else:
            from .template_ui import render_templates
            render_templates(model,root)
            from .custom_ui import render_custom
            with st.expander('旧版简短规范兼容入口'):render_custom(model)


def render_scope_editors(model,run_check):
    from .scope_session import AREAS
    options=['paragraph']+([k for k in AREAS if k!='paragraph'] if model.mode=='academic' else [])
    selected=st.session_state.get('workspace-scope-area','paragraph')
    if selected not in options:selected='paragraph'
    st.session_state['workspace-scope-area']=selected
    area=st.selectbox('进入核对区域',options,format_func=AREAS.get,key='workspace-scope-area')
    st.markdown('<span id="scope-'+area+'"></span>',unsafe_allow_html=True)
    with st.container(border=True,key='scope-editor'):
        if area=='paragraph':
            from .classification_ui import render_classification
            render_classification(model,run_check,unified=True)
        else:
            from importlib import import_module
            modules={'table':('table_ui','render_tables'),'front':('front_ui','render_front'),'toc':('toc_ui','render_toc'),'citation':('citation_ui','render_citations'),'note':('note_ui','render_notes'),'caption':('caption_ui','render_captions'),'reference':('reference_ui','render_references')}
            mod,fn=modules[area];getattr(import_module('web.'+mod),fn)(model)


def finish_navigation():
    # A fixed, local UI-only script. No document values, generated CSS classes,
    # network access or business callbacks; run once per actual view transition.
    marker=(st.session_state.get('workspace-step'),st.session_state.get('workspace-scope-editor',False))
    if st.session_state.get('workspace-rendered-view')!=marker:
        st.session_state['workspace-rendered-view']=marker
        st.html("""<script>document.querySelector('[data-testid="stMain"]')?.scrollTo({top:0,behavior:'instant'});</script>""",unsafe_allow_javascript=True)

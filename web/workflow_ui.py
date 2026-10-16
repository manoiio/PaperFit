"""Presentation-only five-step navigation. No engine, scope or adoption decisions."""
from html import escape
import streamlit as st

STEPS={1:'文档与要求',2:'确认检查范围',3:'查看问题',4:'修正预演',5:'结果与下载'}
# Explicit editor-only keepalive. Never retain acknowledgements, actions, uploads,
# data-editor patches or execution authorization. Business drafts remain on model.
EDITOR_PREFIXES=('reader-mode-','reader-file-','reader-left-','reader-right-','reader-page-number-','reader-section-','class-word-','class-filter-','class-page-','class-object-','class-target-','wb-control-','wb-object-','workspace-rule-entry','diag-edit-','diag-field','diag-issue','diag-detail','diag-modules','diag-states','diag-value-','diag-unit-','diag-quote-','diag-location-','diag-issue-','diag-reason-','wb-value-','wb-edit-mode-','wb-module-','wb-field-','wb-show-missing-',
 'wb-policy-','wb-name-','wb-text-','tpl-value-','tpl-mode-','template-name-',
 'norm-text-','norm-encoding','center-category-','center-status-','center-order-',
 'problem-detail-','center-range-','center-search-','center-type-','center-page-','object-detail-',
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
.block-container {max-width:1200px;padding-top:3.7rem;padding-bottom:3rem;}
h1 {font-size:1.3rem !important;font-weight:700;color:#183650;}
h2 {font-size:1.2rem !important;color:#183650;}
h3 {font-size:1.12rem !important;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:12px;background:white;}
[data-testid="stExpander"] {background:white;border-radius:10px;}
[data-testid="stMetricValue"] {font-size:1.8rem;color:#204c79;}
[data-testid="stCaptionContainer"] {font-size:.88rem;color:#536477;}
.st-key-workspace-nav button {min-height:36px;border-radius:9px;font-size:.92rem;}
.st-key-file-summary {padding:.35rem .7rem;border:1px solid #dce3eb;border-radius:10px;background:white;margin-bottom:.2rem;}
.st-key-document-card {background:white;border-radius:12px;}
.st-key-workspace-nav {margin:0 0 .2rem;}
.report-scroll {overflow-x:auto;}
.report-table {border-collapse:collapse;width:100%;font-size:14px;line-height:1.6;}
.report-table td,.report-table th {padding:9px;border-bottom:1px solid #e1e7ee;text-align:left;overflow-wrap:anywhere;}
.report-table th {background:#edf2f7;color:#183650;}
[id^="scope-"] {scroll-margin-top:80px;}

.st-key-workspace-header {gap:.25rem;}
.st-key-workspace-header h1 {padding:0;margin:0;line-height:1.6;}
.st-key-workspace-header [data-testid="stHorizontalBlock"] {align-items:center;}
.compact-file {display:flex;gap:1rem;align-items:center;flex-wrap:wrap;font-size:14px;}
.compact-file .file-state {font-weight:600;color:#234f75;}
.compact-stats {display:flex;gap:1.2rem;justify-content:space-between;padding:.5rem .75rem;background:white;border:1px solid #dce3eb;border-radius:9px;margin:.2rem 0 .35rem;}
.compact-stats div {display:flex;gap:.45rem;align-items:baseline;}
.compact-stats span {font-size:14px;color:#3b5065;}
.compact-stats strong {font-size:21px;color:#204c79;}
.comparison-card {border:1px solid #dce3eb;border-radius:9px;padding:.65rem .8rem;background:white;font-size:15px;overflow-wrap:anywhere;}
.comparison-card > p {margin:.4rem 0 0;}
.comparison-card header {display:flex;justify-content:space-between;gap:.5rem;margin-bottom:.4rem;}
.comparison-card header span {font-size:13px;color:#4e6478;}
.value-pair {display:grid;grid-template-columns:1fr 22px 1fr;gap:.4rem;align-items:center;}
.value-pair p {margin:.15rem 0;font-weight:600;color:#183650;}
.value-pair small {color:#405970;font-size:13px;}
.change-reason {margin:.4rem 0;color:#2e4357;font-size:14px;}
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
    with st.container(key='workspace-header'):
        title,details,project,reset=st.columns([5,1,1.4,1.2])
        title.title('论文有格')
        with details.popover('文件详情',width='stretch'):
            st.text(model.display_name if model.inventory else '尚未载入文件')
            if model.inventory:
                st.write(f"{len(model.inventory['paragraphs'])} 个顶层段落 · {model.inventory['section_count']} 节 · {len(model.input_bytes)/1024:.1f} KB")
                st.write(model.current_rule_bundle()['name'] if model.mode=='academic' else model.active_template['name'] if model.active_template else '华工本科工理类2015演示规则')
                st.caption('完整规则、版本和来源见第1步；哈希和范围见完整报告。')
        def project_entry():
            go(1);st.session_state['project-panel']=True
        project.button('保存 / 恢复',on_click=project_entry,width='stretch')
        reset.button('重新开始',on_click=restart,width='stretch')
        if model.inventory:
            current='原稿' if model.current_round==0 else f'第{model.current_round}轮副本'
            rule=model.current_rule_bundle()['name'] if model.mode=='academic' else model.active_template['name'] if model.active_template else '2015学校演示规则'
            name=model.display_name if len(model.display_name)<=38 else model.display_name[:35]+'…'
            rule_short=rule if len(rule)<=22 else rule[:21]+'…'
            state='检查有效' if model.report and model.confirmed else '范围待核对 / 旧检查已失效'
            output=f" · 另有第{model.result['round']['number']}轮输出，尚未切换" if model.result else ' · 有预演副本，未采用' if model.rehearsal else ''
            st.html('<div class="compact-file"><b title="'+escape(model.display_name,quote=True)+'">'+escape(name)+'</b><span>当前输入：'+escape(current)+'</span><span title="'+escape(rule,quote=True)+'">规则：'+escape(rule_short)+'</span><span class="file-state">'+escape(state+output)+'</span></div>')
        else:st.caption('本地处理 Word 论文 · 文档 → 范围 → 问题 → 预演 → 结果')
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
    a,b=st.columns([2,1])
    area=a.selectbox('进入核对区域',options,format_func=AREAS.get,key='workspace-scope-area')
    b.button('返回范围总览',on_click=lambda:st.session_state.update({'workspace-scope-editor':False}),help='保留已保存草稿；不确认范围、不开始检查。',width='stretch')
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

"""Presentation-only five-step navigation. No engine, scope or adoption decisions."""
from html import escape
from .workspace_status import check_status, input_label, latest_output, pending_rehearsal, view_label
import streamlit as st

STEPS={1:'文档与要求',2:'确认检查范围',3:'查看问题',4:'修正预演',5:'结果与下载'}
# Explicit editor-only keepalive. Never retain acknowledgements, actions, uploads,
# data-editor patches or execution authorization. Business drafts remain on model.
EDITOR_PREFIXES=('onepass-extra-','wb-layout-','center-object-','center-record-','selected-list-page-','selected-list-item-','history-object-','history-view-','reader-mode-','reader-file-','reader-left-','reader-right-','reader-page-number-','reader-section-','class-word-','class-filter-','class-page-','class-object-','class-target-','wb-control-','wb-object-','workspace-rule-entry','diag-edit-','diag-field','diag-issue','diag-detail','diag-modules','diag-states','diag-value-','diag-unit-','diag-quote-','diag-location-','diag-issue-','diag-reason-','wb-value-','wb-edit-mode-','wb-module-','wb-field-','wb-show-missing-',
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

def detail_go(step):
    st.session_state['workspace-smart']=False
    go(step)

def availability(model):
    return {1:True,2:model.inventory is not None,3:model.report is not None,
            4:model.report is not None,5:model.report is not None or bool(model.history)}

CSS='''<style>
:root {--pf-ink:#182e45;--pf-muted:#4c6073;--pf-blue:#204c79;--pf-line:#d9e2ec;--pf-surface:#fff;--pf-radius:10px;}
.stApp {background:#f3f5f8;color:var(--pf-ink);}
.block-container {max-width:1200px;padding-top:3.5rem;padding-bottom:3rem;}
h1 {font-size:1.35rem !important;font-weight:750;color:var(--pf-ink);}
h2 {font-size:1.3rem !important;font-weight:700;color:var(--pf-ink);letter-spacing:.01em;}
h3 {font-size:1.08rem !important;color:var(--pf-ink);}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {font-size:.9rem;color:var(--pf-muted);line-height:1.6;}
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"] {border-radius:var(--pf-radius);background:var(--pf-surface);border-color:var(--pf-line);}
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button, [data-testid="stPopover"] button {min-height:40px;border-radius:8px;}
[data-testid="stBaseButton-primary"] {background:var(--pf-blue);border-color:var(--pf-blue);color:white;}
[data-testid="stMetricValue"] {font-size:1.8rem;color:var(--pf-blue);}
.st-key-workspace-nav button {min-height:38px;border-radius:8px;font-size:.9rem;}
.st-key-workspace-nav {margin:0 0 .3rem;}
.st-key-workspace-header {gap:.35rem;}
.st-key-workspace-header h1 {padding:0;margin:0;line-height:1.7;}
.st-key-workspace-header h1::before {content:"▤";display:inline-block;color:var(--pf-blue);margin-right:.5rem;font-size:1.25rem;}
.st-key-workspace-header [data-testid="stHorizontalBlock"] {align-items:center;}
.compact-file {display:flex;gap:.35rem 1rem;align-items:center;flex-wrap:wrap;font-size:14px;line-height:1.6;}
.compact-file .file-state {font-weight:650;border-radius:5px;padding:.1rem .45rem;background:#eaf0f7;color:#204c79;}
.compact-file .attention {color:#874b12;background:#fff1dc;}
.compact-file .neutral {color:#354c61;background:#e9edf2;}
.file-identities {font-size:14px;color:var(--pf-muted);display:flex;gap:.3rem 1rem;flex-wrap:wrap;}
.workspace-hint {font-size:14px;color:#344d65;padding:.35rem .6rem;border-left:3px solid #8ca8c4;background:#ecf1f7;line-height:1.5;}
.empty-state {border:1px solid var(--pf-line);border-left:3px solid #8ca8c4;border-radius:var(--pf-radius);background:white;padding:.85rem 1rem;margin:.15rem 0 .5rem;}
.empty-state strong {font-size:1rem;color:var(--pf-ink);}
.empty-state p {margin:.3rem 0 0;color:var(--pf-muted);line-height:1.65;font-size:.95rem;overflow-wrap:anywhere;}
.st-key-object-browser [data-testid="stRadio"] {width:100%;}
.st-key-object-browser [data-testid="stRadio"] label p {color:var(--pf-muted);}
.st-key-object-browser [data-testid="stRadio"] label {padding:.35rem .2rem;border-bottom:1px solid var(--pf-line);}
.st-key-object-browser [data-testid="stRadio"] label:has(input[type="radio"]:checked) {background:#eaf0f7;border-radius:8px;box-shadow:inset 3px 0 var(--pf-blue);}
.report-scroll {overflow-x:auto;}
.report-table {border-collapse:collapse;width:100%;font-size:14px;line-height:1.6;}
.report-table td,.report-table th {padding:9px;border-bottom:1px solid var(--pf-line);text-align:left;overflow-wrap:anywhere;}
.report-table th {background:#edf2f7;color:var(--pf-ink);}
[id^="scope-"] {scroll-margin-top:80px;}
.compact-stats {display:flex;gap:.5rem 1.2rem;flex-wrap:wrap;justify-content:space-between;padding:.55rem .8rem;background:white;border:1px solid var(--pf-line);border-radius:var(--pf-radius);margin:.2rem 0 .35rem;}
.compact-stats div {display:flex;gap:.45rem;align-items:baseline;}
.compact-stats span {font-size:14px;color:#3b5065;}
.compact-stats strong {font-size:21px;color:var(--pf-blue);}
.comparison-card {border:1px solid var(--pf-line);border-radius:var(--pf-radius);padding:.75rem .9rem;background:white;font-size:15px;overflow-wrap:anywhere;}
.comparison-card > p {margin:.4rem 0 0;}
.comparison-card header {display:flex;justify-content:space-between;gap:.5rem;margin-bottom:.4rem;}
.comparison-card header span {font-size:14px;color:var(--pf-muted);}
.value-pair {display:grid;grid-template-columns:1fr 22px 1fr;gap:.4rem;align-items:center;}
.value-pair p {margin:.15rem 0;font-weight:600;color:var(--pf-ink);}
.value-pair small {color:var(--pf-muted);font-size:13px;}
.change-reason {margin:.4rem 0;color:#2e4357;font-size:14px;}
</style>'''


def empty_state(title, detail):
    """Untrusted text stays text; no business action or implicit completion."""
    st.html('<div class="empty-state"><strong>'+escape(title)+'</strong><p>'+escape(detail)+'</p></div>')


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
    # Observed UI history never grants authority. New task/input/round starts unseen.
    seen_key=(str(model.task_dir),(model.inventory or {}).get('input_sha256'),model.current_round)
    if st.session_state.get('workspace-observed-input')!=seen_key:
        st.session_state['workspace-observed-input']=seen_key
        st.session_state['workspace-observed-check']=False
    if model.report is not None and model.confirmed is not None:
        st.session_state['workspace-observed-check']=True
    state,tone=check_status(model,st.session_state.get('workspace-observed-check',False))
    simple=st.session_state.get('workspace-smart',False) and not st.session_state.get('smart-legacy',False)
    if simple and model.inventory:
        state='可开始整理；已有设置会保留' if model.report or model.history else '已载入 · 可以开始整理'
        tone='neutral'
        from .onepass_session import current
        entry=st.session_state.get('onepass-'+model.task_dir.name,{})
        if entry and current(model,entry,st.session_state.get('onepass-extra-'+model.task_dir.name,entry.get('extra',''))):
            state={'done':'修正版已生成 · 原稿保留' if model.result else '本次整理检查已完成','waiting':'有少量事项需要确认','running':'正在整理','failed':'本次未完成'}.get(entry.get('status'),state)
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
            (detail_go if simple else go)(1);st.session_state['project-panel']=True
        project.button('保存 / 恢复',on_click=project_entry,width='stretch')
        reset.button('重新开始',on_click=restart,width='stretch')
        if model.inventory:
            current=input_label(model)
            rule='SCUT 2015演示规则' if model.custom_rules_path is None and model.active_template is None else model.current_rule_bundle()['name'] if model.mode=='academic' else model.active_template['name'] if model.active_template else '2015学校演示规则'
            name=model.display_name if len(model.display_name)<=38 else model.display_name[:35]+'…'
            rule_short=rule if len(rule)<=22 else rule[:21]+'…'
            st.html('<div class="compact-file"><b title="'+escape(model.display_name,quote=True)+'">'+escape(name)+'</b><span>当前输入：'+escape(current)+'</span><span title="'+escape(rule,quote=True)+'">规则：'+escape(rule_short)+'</span><span class="file-state '+tone+'">'+escape(state)+'</span></div>')
            output=latest_output(model)
            viewed=view_label(model,step,st.session_state)
            labels=([output['label']] if output else [])+(['查看目标：'+viewed] if viewed else [])
            if pending_rehearsal(model) and step!=4:labels.append('已有预演记录 · 尚未采用，采用前仍须核对')
            if labels:st.html('<div class="file-identities">'+''.join('<span>'+escape(label)+'</span>' for label in labels)+'</div>')
        else:st.caption('本地检查与选择修正 Word 格式 · 当前尚未载入文件')
    if simple:return step
    st.button('智能处理 · 返回快捷主流程',key='smart-entry',on_click=lambda:st.session_state.update({'workspace-smart':True,'smart-legacy':False}),width='stretch')
    with st.container(key='workspace-nav'):
        for col,(n,label) in zip(st.columns(5),STEPS.items()):
            status='当前' if n==step else ('需载入' if n==2 else '需检查' if n in (3,4) else '需记录') if not ready[n] else '已确认' if n==2 and model.confirmed else '有记录' if n==3 and model.report else '有记录' if n==5 and model.history else '可进入'
            missing='先载入DOCX。' if n==2 else '先核对范围并完成检查。' if n in (3,4) else '先完成检查，或恢复含历史的项目。'
            col.button(f'{n} {label} · {status}',key=f'workspace-nav-{n}',disabled=not ready[n],help=missing if not ready[n] else '仅切换查看区域，不确认、不执行、不切换输入。',type='primary' if step==n else 'secondary',on_click=detail_go,args=(n,),width='stretch')
    if st.session_state.get('workspace-observed-check') and model.inventory and model.report is None:
        st.html('<div class="workspace-hint">下一步：核对当前要求与范围，再明确确认并重新检查。旧记录不用于当前操作。</div>')
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

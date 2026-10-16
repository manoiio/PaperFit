"""论文有格第二阶段：127.0.0.1 Streamlit。所有文档操作直接调用core。"""
from pathlib import Path
import json
import streamlit as st
from core.package import DemoError
from web.issues import field_value
from web.session import WebSession, public_error
from web.presentation import short, position, original, fmt, finding_table
from web.custom_ui import render_custom
from web.template_ui import render_templates
from web.classification_ui import render_classification
from web.table_ui import render_tables
from web.front_ui import render_front

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='论文有格', page_icon='📄', layout='wide', initial_sidebar_state='collapsed')

CSS = '''
<style>
[id^="scope-"] {scroll-margin-top: 80px;}
html, body, [class*="css"], .stApp {font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;}
.block-container {max-width: 1320px; padding-top: 2rem; padding-bottom: 3rem;}
h1 {color: #173e68; font-size: 2.1rem !important; margin-bottom: 0 !important;}
h2 {color: #173e68; font-size: 1.3rem !important; padding-top: .6rem !important;}
h3 {font-size: 1.12rem !important;}
[data-testid="stMetricValue"] {font-size: 1.7rem; color:#173e68;}
.report-scroll {overflow-x:auto; margin: .4rem 0 1rem;}
.report-table {border-collapse:collapse; width:100%; min-width:1000px; font-size:14px; line-height:1.6;}
.report-table th {background:#edf3f9; color:#173e68; text-align:left; padding:10px 11px; font-weight:600;}
.report-table td {border-bottom:1px solid #e2e8f0; padding:10px 11px; vertical-align:top; overflow-wrap:anywhere;}
.report-table tbody tr:nth-child(even) {background:#fafbfd;}
.report-table th:nth-child(1) {width:10%;} .report-table th:nth-child(2) {width:8%;}
.report-table th:nth-child(3) {width:13%;} .report-table th:nth-child(4) {width:13%;}
.report-table th:nth-child(5) {width:12%;} .report-table th:nth-child(6) {width:7%;}
.report-table th:nth-child(7) {width:17%;} .report-table th:nth-child(8) {width:20%;}
.config-table th:nth-child(1) {width:20%;} .config-table th:nth-child(2) {width:22%;}
.config-table th:nth-child(3) {width:20%;} .config-table th:nth-child(4) {width:38%;}
[data-testid="stCaptionContainer"] {font-size: .9rem;}
[data-testid="stAppDeployButton"] {display:none;}
</style>
'''
st.markdown(CSS, unsafe_allow_html=True)

if 'workflow' not in st.session_state:
    st.session_state.workflow = WebSession(ROOT / 'work/web')
if 'upload_generation' not in st.session_state:
    st.session_state.upload_generation = 0
model = st.session_state.workflow
model.sync_rules()


def load_builtin(kind):
    st.session_state.upload_generation += 1  # Remove any old uploader display without assigning its read-only value.
    try:
        path = ROOT / 'samples' / (kind + '.docx')
        preset = json.loads(path.with_suffix('.body.json').read_text(encoding='utf-8')) if kind in ('errors','correct') else None
        model.load(path.read_bytes(), {'errors':'内置错误样本.docx','correct':'内置正确对照样本.docx','extended-errors':'扩展错误样本.docx','extended-correct':'扩展正确对照样本.docx','academic-errors':'前后置章节错误样本.docx','academic-correct':'前后置章节正确对照.docx','table-text-errors':'表格文字错误样本.docx','table-text-correct':'表格文字正确对照.docx'}[kind], preset)
    except (OSError, ValueError, DemoError) as exc:
        model.reset()
        model.error = public_error(exc)


def upload_changed(key):
    uploaded = st.session_state.get(key)
    if uploaded is None:
        model.reset()
    else:
        model.load(uploaded.getvalue(), uploaded.name)  # No preset, regardless of name or identical bytes.


def restart():
    try:
        model.reset()
        st.session_state.upload_generation += 1
        st.session_state['short-spec-text'] = ''
        st.session_state['check-mode'] = '基础检查'
    except Exception as exc:
        model.invalidate()
        model.error = public_error(exc)


def body_key(n):
    return f'body-{model.task_dir.name}-{model.current_round}-{model.revision}-{n}'


def body_changed():
    selected = [p['index'] for p in model.inventory['paragraphs'] if st.session_state.get(body_key(p['index']), False)]
    model.set_body(selected)


def confirm_body():
    try:
        model.confirm()
    except Exception as exc:
        model.error = public_error(exc)


def run_check():
    with st.spinner('正在读取格式并检查当前确认规则…'):
        model.check()


def selection_changed(key):
    model.set_selection(st.session_state.get(key, []))


def select_all(key):
    selected = [f['key'] for f in model.eligible()]
    st.session_state[key] = selected
    model.set_selection(selected)


def clear_selection(key):
    st.session_state[key] = []
    model.set_selection([])


def run_fix():
    with st.spinner('正在另存新文件，并从磁盘读回复查…'):
        model.generate()


def metrics(report, remaining=False):
    s = report['summary']
    labels=['启用规则数','实际适用规则数','剩余问题' if remaining else '问题数','剩余待复核' if remaining else '待复核数','已确认正文段落数']
    values=[s['rule_count'],s['applicable_rule_count'],s['problem_count'],s['review_count'],len(report['coverage']['body_paragraphs'])]
    cols=st.columns(5)
    for c,label,value in zip(cols,labels,values):c.metric(label,value)



def report_view(report, inventory):
    st.caption('字体项判断DOCX指定的字体，不检测电脑是否安装；实际替代字体由页面预览另查。自动编号符号单列，只读证据不验证编号连续性。')
    s = report['summary']
    st.write(f"格式问题 {s['problem_count']}；待复核 {s['review_count']}（规则{s['review_findings']}、覆盖{s['review_notes']}）。详细对象与依据请在问题中心按页查看，避免重复生成整份表格。")
    reviews=[f for f in report['findings'] if f['status']=='review']
    if reviews:
        st.caption(f'待复核示例（最多3条，完整{len(reviews)}条请按对象查看）：')
        st.markdown(finding_table(reviews[:3],inventory),unsafe_allow_html=True)
    # coverage_notes are independent of findings; always visible even when no review finding exists.
    st.markdown('**覆盖范围与提示**')
    coverage = report['coverage']
    st.caption(f"已确认正文：{', '.join(map(str, coverage['body_paragraphs']))}；全部 {coverage['section_count']} 节页面设置。"+
               (f"分类中的其他段落 {sum(t=='other' for t in coverage['paragraph_types'].values())} 个、待确认段落 {len(coverage['unconfirmed_paragraphs'])} 个不套正文/标题/题注规则。" if 'paragraph_types' in coverage else
                f"未确认的 {len(coverage['unconfirmed_paragraphs'])} 个顶层段落不套正文规则。"))
    if 'paragraph_types' in coverage:
        from core.classification import TYPES
        groups={t:[n for n,v in coverage['paragraph_types'].items() if v==t] for t in TYPES}
        st.caption('；'.join(TYPES[t]+'：'+', '.join(groups[t]) for t in groups if groups[t] and t not in ('body','other')))
        st.caption('表格、封面、目录、引文、注释及题注补充是否参与，见统一范围总览与报告；未启用、未配置及复杂结构仍需人工复核。')
    else:
        st.caption('标题、题注、表格格式、页眉页脚及文本框等未纳入正文规则；复杂对象的显示仍需人工复核。')
    if report['coverage_notes']:
        st.warning(f"覆盖提示 {len(report['coverage_notes'])} 条；在问题中心待复核类别按页查看，完整导出全部保留。")
        for note in report['coverage_notes'][:3]:st.warning('覆盖提示示例：'+note['detail'])
    else:st.caption('无额外覆盖提示；覆盖外对象仍需人工核对。')


head, reset_col = st.columns([7, 1])
with head:
    st.title('论文有格')
    st.write('检查Word格式并生成修正副本')
with reset_col:
    st.button('重新开始', on_click=restart, width='stretch')
from web.project_ui import render_project
render_project(model)
if model.rules_hash is None:
    st.error('当前规则不可用，请重新载入模板确认或恢复默认规则。')
elif model.workbench['active'] and model.custom_rules_path:
    st.caption('当前规则：'+model.current_rule_bundle()['name']+' · 完整规则包v1 / 主模板v6；封面、目录及注释按配置与人工范围参与，未配置不检查。')
elif model.active_template:
    st.caption('当前规则：'+model.active_template['name']+' · 模板版本'+str(model.active_template['structure_version'])+' · '+('仅执行R01–R07；标题题注未启用' if model.mode=='basic' else 'R01–R12；标题/图题/表题按确认模板，R11结构固定' if model.active_template['structure_version']==3 else 'R01–R22；新增对象与属性按已确认v4配置，仅单文档模式执行' if model.active_template['structure_version'] in (4,5) else 'R01–R22及已确认附录致谢R38–R41；按v6逐属性配置，未配置不检查' if model.active_template['structure_version']==6 else 'R08–R12沿用旧版本固定要求'))
elif model.active_custom_data:
    st.caption('当前应用：用户确认的演示规则 · 字号 '+fmt(model.active_custom_data['rules']['R05']['expected'],'R05',True)+
               ' · 行距 '+fmt(model.active_custom_data['rules']['R06']['expected'],'R06',True)+' · R01–R04、R07沿用默认')
else:
    st.caption('当前应用：华工本科工理类2015演示规则 · '+({'basic':'R01–R07','extended':'R01–R12','academic':'R01–R22'}[model.mode])+' · 不宣称当前学校现行标准')
st.caption('论文检查与修正在本机完成，规范解析会调用DeepSeek。')

def mode_changed():
    model.set_mode({'基础检查':'basic','正文及标题题注检查':'extended','单文档扩展检查':'academic'}[st.session_state['check-mode']])
if 'check-mode' not in st.session_state:st.session_state['check-mode']={'basic':'基础检查','extended':'正文及标题题注检查','academic':'单文档扩展检查'}[model.mode]
st.radio('检查模式',['基础检查','正文及标题题注检查','单文档扩展检查'],key='check-mode',horizontal=True,on_change=mode_changed)
if model.mode=='academic' and model.toc_enabled and model.toc_draft:
    st.caption('当前目录补充：'+model.toc_draft['template']['name']+' · 结构版本1；仅人工确认目录范围生效，实际页码未核对。')
st.caption('基础R01–R07；标题题注R01–R12；单文档扩展R01–R22，包含明确配置的间距、摘要、关键词和参考文献。附录/致谢R38–R41仅确认对应类型后按已配置属性执行。旧模板新增属性未启用。切换后旧报告与下载失效，请重新确认范围。')
from web.center_ui import task_header,render_center,render_history
task_header(model)

if model.mode=='academic':
    from web.workbench_ui import render_workbench
    render_workbench(model,ROOT)
else:render_templates(model,ROOT)
if model.mode!='academic':render_custom(model)

with st.container(key='input'):
    st.subheader('1 选择文档')
    sample_col, upload_col = st.columns([1, 1.3], gap='large')
    with sample_col:
        st.markdown('**内置软件演示样本**')
        a, b = st.columns(2)
        a.button('使用错误样本', on_click=load_builtin, args=('errors',), width='stretch')
        b.button('使用正确对照', on_click=load_builtin, args=('correct',), width='stretch')
        if model.mode!='basic':
            c,d=st.columns(2)
            c.button('使用扩展错误样本',on_click=load_builtin,args=('extended-errors',),width='stretch')
            d.button('使用扩展正确对照',on_click=load_builtin,args=('extended-correct',),width='stretch')
        if model.mode=='academic':
            e,f=st.columns(2)
            e.button('使用摘要参考文献错误样本',on_click=load_builtin,args=('academic-errors',),width='stretch')
            f.button('使用摘要参考文献正确对照',on_click=load_builtin,args=('academic-correct',),width='stretch')
            e,f=st.columns(2)
            e.button('使用表格文字错误样本',on_click=load_builtin,args=('table-text-errors',),width='stretch')
            f.button('使用表格文字正确对照',on_click=load_builtin,args=('table-text-correct',),width='stretch')
        st.caption('合成内容，无真实作者或课程论文。基础样本正文可预填；分类建议始终需要确认。')
    with upload_col:
        upload_key = f'upload-{st.session_state.upload_generation}'
        st.file_uploader('上传自己的DOCX（最大10MB）', type=['docx'], max_upload_size=10,
                         key=upload_key, on_change=upload_changed, args=(upload_key,))
        st.caption('文件仅发送到当前Mac上的本地服务，不调用外部服务。演示请使用脱敏文件。')

if model.error:
    st.error('处理未完成：' + model.error)
if model.inventory is None:
    st.info('选择内置样本或上传DOCX，随后确认哪些段落属于正文。')
    render_history(model)
    st.stop()

st.caption(f'当前文档：{model.display_name} · {len(model.inventory["paragraphs"])} 个顶层段落 · {model.inventory["section_count"]} 节')
st.caption('当前处理输入：原稿' if model.current_round==0 else f'当前处理输入：第{model.current_round}轮修正版（已明确切换，原稿仍保留）')
from web.scope_ui import render_scope_overview
render_scope_overview(model)
if model.mode!='basic':
    from web.citation_ui import render_citations
    st.markdown('<span id="scope-citation"></span>',unsafe_allow_html=True)
    render_citations(model)
    from web.reference_ui import render_references
    st.markdown('<span id="scope-reference"></span>',unsafe_allow_html=True)
    render_references(model)
    from web.note_ui import render_notes
    st.markdown('<span id="scope-note"></span>',unsafe_allow_html=True)
    render_notes(model)
    from web.toc_ui import render_toc
    st.markdown('<span id="scope-toc"></span>',unsafe_allow_html=True)
    render_toc(model)
    st.markdown('<span id="scope-front"></span>',unsafe_allow_html=True)
    render_front(model)
    st.markdown('<span id="scope-table"></span>',unsafe_allow_html=True)
    render_tables(model)
    from web.caption_ui import render_captions
    st.markdown('<span id="scope-caption"></span>',unsafe_allow_html=True)
    render_captions(model)
    st.markdown('<span id="scope-paragraph"></span>',unsafe_allow_html=True)
    render_classification(model,run_check)
else:
    st.markdown('<span id="scope-paragraph"></span>',unsafe_allow_html=True)
    with st.container(key='scope'):
        st.subheader('2 确认正文范围')
        st.caption('编号是主文档顶层段落编号，含空段和图片段，不是页码；表格内段落不在此清单中。')
        with st.expander('选择或调整正文段落', expanded=not bool(model.body), key=f'scope-picker-{model.task_dir.name}'):
            for p in model.inventory['paragraphs']:
                key = body_key(p['index'])
                if key not in st.session_state:
                    st.session_state[key] = p['index'] in model.body
                label = f"段 {p['index']} · {short(p['text'], 52) or '（空段或图片段）'}"
                hint = f"样式：{p['style_id'] or '默认段落样式'}"
                if p['special']:
                    hint += '；特殊结构：' + p['special']
                st.checkbox(label, key=key, on_change=body_changed, help=hint)
            st.caption('勾选代表人工选择，不自动推断标题、正文或题注。特殊结构由引擎检查后另行提示。')
        if model.body:
            st.markdown('**当前选中的正文段落（请核对后确认）**')
            rows = [{'编号': p['index'], '简短文本': short(p['text'], 68), '样式': p['style_id'] or '默认段落样式',
                     '特殊结构提示': p['special'] or '未发现段落级特殊结构'}
                    for p in model.inventory['paragraphs'] if p['index'] in model.body]
            st.dataframe(rows, hide_index=True, width='stretch', height=min(280, 36 * len(rows) + 38))
        else:
            st.info('尚未选择正文段落，请先勾选至少一个明确的正文段落。')
        if model.confirmed:
            st.caption(f'已确认 {len(model.body)} 个正文段落，确认绑定当前文件。调整范围会使报告及修正版失效。')
        else:
            st.caption('正文范围尚未确认。更改输入或段落选择后，需要重新确认。')
        st.caption('快捷按钮表示本人已核对完整的当前正文范围，确认成功才检查；不执行修正、AI或预览。')
        st.button('核对完成并开始检查',disabled=not model.body,on_click=model.confirm_and_check,type='primary',width='stretch')
        a, b = st.columns([1, 1])
        a.button('确认正文范围', disabled=not model.body, on_click=confirm_body, width='stretch')
        b.button('开始检查', disabled=model.confirmed is None, on_click=run_check, width='stretch')
if model.report is None:
    render_history(model)
    st.stop()
with st.container(key='report-before'):
    st.subheader('3 检查报告')
    metrics(model.report)
    with st.expander('原始格式检查及覆盖详情'):
        report_view(model.report, model.inventory)
render_center(model)
from web.caption_ui import render_caption_report,render_caption_move
render_caption_report(model)
if model.operation=="pagination":render_caption_move(model)
with st.expander('高级：重新检查当前输入'):
    st.caption('普通检查可复用同一文件、规则和确认范围的只读结果；重新检查明确跳过该缓存。')
    st.button('重新检查',on_click=lambda:model.check(force=True))

st.markdown('<span id="format-operations"></span>',unsafe_allow_html=True)
from web.citation_ui import render_citation_report
if model.report is not None:render_citation_report(model.result["after"] if model.result else model.report)
from web.toc_ui import render_toc_report
if model.report is not None:render_toc_report(model.result['after'] if model.result else model.report)

eligible = model.eligible()
if eligible and model.operation=='format':
    with st.container(key='selection'):
        st.subheader('4 选择要修正的问题')
        st.caption('默认不修正。仅允许选择“发现问题”且可修正的记录；每次从上方明确显示的当前输入生成新副本，不覆盖任何一轮文件。')
        from web.report_pages import object_page,merge_page_selection,selection_counts
        lookup={f['key']:f for f in eligible}
        view=getattr(model,'center_selection_view',None)
        if not view or view.get('file_sha256')!=model.report['input_sha256']:
            view=object_page([r for r in model.current_bundle()['projection']['records'] if r['record_key'] in lookup])
        visible=[k for k in view['page_keys'] if k in lookup]
        filtered=[k for k in view['filtered_keys'] if k in lookup]
        a,b,c=st.columns(3)
        a.button('选择本页可修正项',on_click=lambda:model.set_selection(model.selected+visible),width='stretch')
        b.button('选择当前筛选的可修正项',on_click=lambda:model.set_selection(model.selected+filtered),width='stretch')
        c.button('清空全部选择',on_click=lambda:model.set_selection([]),width='stretch')
        with st.expander('高级：全部可修正项（不是当前筛选）'):
            st.button('选择全部可修正问题',on_click=lambda:model.set_selection(list(lookup)))
            st.button('清空选择',on_click=lambda:model.set_selection([]))
        from core.package import sha256
        key=f'selection-{model.task_dir.name}-{model.revision}-{model.report_revision}-'+sha256(str(visible).encode())[:12]
        st.session_state[key]=[k for k in model.selected if k in visible]
        def label(k):
            f=lookup[k]
            return f"{f['rule_id']} · {position(f['locator'])} · {f['rule_name']}：{field_value(f['actual'], f['rule_id'], f['locator'])} → {field_value(f['expected'], f['rule_id'], f['locator'], True)}"
        def page_selection():model.set_selection(merge_page_selection(model.selected,visible,st.session_state.get(key,[])))
        st.multiselect('逐项选择修正',options=visible,format_func=label,key=key,on_change=page_selection,placeholder='仅本页可修正记录；其他页的明确选择保留')
        counts=selection_counts(model.selected,view)
        st.caption(f"已选 {len(model.selected)} 项可修正问题。")
        st.caption(f"本页已选 {counts['page']} · 全部已选 {counts['all']} · 当前筛选外仍保留 {counts['outside_filter']}")
        warnings=[w['detail'] for w in model.report.get('modification_dependencies',[]) if set(w['trigger_keys'])&set(model.selected)]
        warnings += [f['dependency_note'] for f in eligible if f['key'] in model.selected and f.get('dependency_note')]
        if warnings:
            st.warning(f"关联提示 {len(warnings)} 项："+'；'.join(warnings[:3]))
            if st.toggle('查看全部关联提示'):st.dataframe([{'提示':w} for w in warnings],hide_index=True,width='stretch')
        if model.selected:
            with st.expander(f'执行确认摘要：全部 {len(model.selected)} 项明确选择',expanded=True):
                st.caption('生成将执行下面全部选择，包括其他页和当前筛选外的项；不会自动加入待复核记录。')
                st.dataframe([{'key':k,'位置':position(lookup[k]['locator']),'规则':lookup[k]['rule_id'],'实际':field_value(lookup[k]['actual'],lookup[k]['rule_id'],lookup[k]['locator']),'要求':field_value(lookup[k]['expected'],lookup[k]['rule_id'],lookup[k]['locator'],True)} for k in model.selected],hide_index=True,width='stretch',height=240)
        from web.rehearsal_ui import render_rehearsal
        render_rehearsal(model)
        with st.expander('高级兼容：不经预演直接生成'):
            st.caption('直接使用相同修正器与保护，无法在生成正式轮次前核对实际关联影响。')
            st.button('生成修正版', disabled=not model.selected or model.result is not None,
                      on_click=run_fix, width='stretch')
        if model.result is not None:
            st.caption('当前选择已生成。下载或页面重运行不会再次修正；改变选择后可生成另一份新副本。')
elif not eligible:
    st.caption('没有可自动修正的问题，无需生成修正版。待复核项请人工核对。')

from web.width_ui import render_width_panel
if model.operation=='width':render_width_panel(model)

if model.result is not None:
    # Validate download binding before showing any success/download controls.
    try:
        files = model.downloads()
    except Exception as exc:
        model.result = model.result_signature = None
        model.error = public_error(exc)
        st.error('结果不可用：' + model.error)
        st.stop()
    if files:
        result, after = model.result, model.result['after']
        with st.container(key='result'):
            st.subheader('5 修正结果')
            if any(c['rule_id'] in ('R36','R37') for c in result['changes']):st.info('仅所选注释普通文字属性已修改。正文引用、内部自动编号、系统分隔线和未选部件保持。注释字体字号或行距可能改变分页，请主动预览；格式通过不代表注释内容正确。')
            if any(c['rule_id']=='R35' for c in result['changes']):st.info('仅所选左右外侧边框已修正；内部竖线及未选侧保留。0边框问题不代表表格整体合格。')
            if any(c['rule_id']=='L04' for c in result['changes']):st.info('已设置重复表头属性，不补续表题注、编号或（续）；请主动预览并核对第二页及之后的实际结果。')
            if any(c['rule_id']=='R33' for c in result['changes']):st.info('引文上标已按所选字符设置，字体字号与前后文字保持。通用正文继续保护上标run，会新增未检查覆盖提示；必要拆分可改变run编号/问题key及记录数，不代表未选格式被改变或全文通过。')
            if result.get('kind') in ('figure_layout','pagination_layout'):
                st.success(result['layout']['message']+'，并从落盘副本核对。')
                st.warning(result['layout']['limitation'])
            elif result.get('kind')=='width_adaptation':
                st.success(result['widths']['message']+'；不是可见排版验收。')
                st.warning(result['widths']['limitation'])
            else:
                st.success(f"已生成新DOCX：{len(result['changes'])} 项修改已保存，所选修改的落盘复查全部符合要求。")
            st.caption(f"第{result['round']['number']}轮输出；输入为"+('原稿' if result['round']['input_round']==0 else f"第{result['round']['input_round']}轮修正版"))
            delta=result['problem_delta']
            if result.get('impact'):
                ic=result['impact']['counts']
                st.write(f"稳定对应已解决 {ic['selected_resolved']+ic['natural_resolved']} 条 · 新出现问题 {ic['new_problem']} 条 · 转待复核 {ic['problem_to_review']} 条 · 无法可靠对齐 {ic['unaligned']} 条")
            else:
                st.write(f"已解决 {len(delta['resolved_keys'])} 个 · 原有剩余 {len(delta['remaining_keys'])} 个 · 新出现 {len(delta['new_keys'])} 个")
            if delta.get('unresolved_review_keys'):
                st.warning(f"另有 {len(delta['unresolved_review_keys'])} 个原有问题转为待复核，尚未验证解决。")
            for cause in delta['new_problem_causes']:st.warning(cause['detail'])
            st.caption('部分修正允许保留未选问题；下面显示新文件的实际剩余问题与待复核数。')
            metrics(after, remaining=True)
            checks = result['preservation']
            st.markdown('**完整性检查通过**')
            if result.get('kind')=='caption_position':
                st.write('原稿保持不变 · 仅授权题注位置变化 · 所有对象子树与未选部件逐字节核对通过；实际同页未核对')
                st.info('段落编号已按XML对象映射重绑；旧选择、布局计划及不匹配预览失效。原稿仅提供渲染预览，不套用移动后的段号。')
                with st.expander('范围映射与失效详情'):st.json(result['range_mapping'])
            else:st.write('原稿保持不变 · 未选格式与文档内容保留核对通过 · 未选包部件字节核对通过；选中故事部件只改格式')
            required=('original_sha256_unchanged','only_authorized_caption_permutation','all_object_subtrees_equal','remaining_objects_relative_order_equal') if result.get('kind')=='caption_position' else ('original_sha256_unchanged','document_except_selected_format_attributes_equal')
            if not all(checks.get(k) is True for k in required) or not checks.get('unselected_zip_member_bytes_equal',checks.get('other_zip_member_bytes_equal')):
                st.error('完整性结果异常，请重新开始。')
                st.stop()
            changes = [{'规则': c['rule_id'], '位置': position(c['locator']), '修改前': field_value(c['before'], c['rule_id'], c['locator']),
                        '修改后': field_value(c['after'], c['rule_id'], c['locator']), '落盘复查': '符合' if c['verification'] == 'pass' else c['verification'],
                        **({'分页属性':{'keepNext':'所选段落与后续对象相连','keepLines':'所选段落段内不拆分','tblHeader':'所选连续表头行在后续页重复（实际显示须预览）'}[c['property']]} if c.get('property') in ('keepNext','keepLines','tblHeader') else {})}
                       for c in result['changes']]
            with st.expander(f"查看 {len(changes)} 项修改前后值与复查结果"):
                st.dataframe(changes, hide_index=True, width='stretch', height=min(600, 36 * len(changes) + 38))
            if after['rules'].get('kind'):
                st.caption('复查使用：'+after['rules']['name']+'；结构版本'+str(after['rules'].get('template_structure_version',2))+'；标题题注仅在扩展模式按该轮确认模板执行，R11固定。' if after['rules']['kind']=='user_confirmed_template' else '复查使用：用户确认的演示规则；此兼容配置只自定义R05/R06，其余规则仍逐项检查。')
            st.markdown('**下载文件与记录**')
            st.caption('下载原稿用于保留原文件；未实现逐项撤销。')
            st.caption('本轮结果包包含修正版、修改/复查与离线阅读报告、规则及范围；默认不含原稿、页图、日志或论文摘录。单文件下载仍保留。')
            try:
                package=model.result_package()
                st.download_button('下载本轮结果包',package,file_name='论文有格_第'+str(result['round']['number'])+'轮结果.zip',mime='application/zip',on_click='ignore',key='package-'+str(model.revision)+'-'+str(model.generation_count),width='stretch')
            except Exception as exc:st.warning(public_error(exc))
            d1, d2, d3, d4 = st.columns(4)
            for col, label_text, name, download_name, mime in [
                (d1,'下载修正版DOCX','fixed.docx','论文有格_修正版.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                (d2,'下载原稿DOCX','original.docx','论文有格_原稿.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                (d3,'下载修改记录','changes.md','论文有格_修改记录.md','text/markdown'),
                (d4,'下载复查报告','recheck.md','论文有格_复查报告.md','text/markdown')]:
                col.download_button(label_text, files[name], file_name=download_name, mime=mime,
                                    on_click='ignore', key=f'download-{model.task_dir.name}-{Path(result["output"]).stem}-{name}', width='stretch')
        with st.container(key='report-after'):
            st.subheader('6 保存后复查')
            st.caption(f"第{result['round']['number']}轮输出的落盘复查")
            st.caption('以下结果由core在新文件保存后重新读取产生，不是内存中的预期格式。')
            if after['rules'].get('kind'):
                sizes=sorted({fmt(f['actual'],'R05') for f in after['findings'] if f['rule_id']=='R05' and f['status']!='not_applicable'})
                lines=sorted({fmt(f['actual'],'R06') for f in after['findings'] if f['rule_id']=='R06' and f['status']!='not_applicable'})
                st.write('已覆盖普通文字的落盘字号：'+'、'.join(sizes)+'；已覆盖正文的落盘行距：'+'、'.join(lines))
            if after['rules'].get('kind')=='user_confirmed_template':
                with st.expander('查看正文及页面模板落盘实际值'):
                    rows=[]
                    for rid in ('R01','R02','R03','R04','R05','R06','R07'):
                        records=[f for f in after['findings'] if f['rule_id']==rid and f['status']!='not_applicable']
                        rows.append({'规则':rid,'落盘实际值':'、'.join(sorted({fmt(f['actual'],rid) for f in records})) or '无适用记录','复查状态':'、'.join(sorted({{'pass':'符合','problem':'发现问题','review':'待复核'}[f['status']] for f in records})) or '不适用'})
                    st.dataframe(rows,hide_index=True,width='stretch')
            if after['rules'].get('mode')=='extended':
                with st.expander('查看标题、图题和表题落盘实际值'):
                    rows=[]
                    types=after['coverage']['paragraph_types']
                    for obj,label in [('heading1','一级标题'),('heading2','二级标题'),('heading3','三级标题'),('figure_caption','图题'),('table_caption','表题')]:
                        fs=[f for f in after['findings'] if types.get(str(f['locator'].get('paragraph')))==obj]
                        def actual(prop):
                            values=[fmt(f['actual'],f['rule_id']) for f in fs if f['locator'].get('property')==prop]
                            return '、'.join(sorted(set(values))) or '无适用记录'
                        review_notes=any(types.get(str(n['locator'].get('paragraph')))==obj for n in after['coverage_notes'])
                        statuses=sorted({{'pass':'符合','problem':'发现问题','review':'待复核','not_applicable':'不适用'}[f['status']] for f in fs}|({'待复核（覆盖提示）'} if review_notes else set()))
                        rows.append({'对象':label,'中文字体':actual('font_eastAsia'),'字号':actual('size'),'对齐':actual('alignment') if obj.startswith('heading') else '不检查','行距':actual('line') if obj.startswith('heading') else '不检查','属性记录状态':'、'.join(statuses) or '不适用'})
                    st.caption('取自本轮落盘文件的实际属性；标题/题注西文槽位及具体原因仍在完整报告中，不能据此推导可见版面通过。')
                    st.dataframe(rows,hide_index=True,width='stretch')
            with st.expander('保存后全部格式及覆盖详情'):
                report_view(after, model.inventory)
            if result.get('output'):
                st.button('以计划最终副本继续' if model.result.get('plan') else '以本轮修正版开始下一轮',on_click=model.next_round,type='primary',width='stretch',
                          help='明确切换输入，沿用结构保留核对通过且绑定新文件哈希的清单；原稿和各轮文件均保留。')

from web.preview_ui import render_preview_panel
if model.operation in ('preview','pagination'):render_preview_panel(model)
render_history(model)

with st.expander('高级详情与完整报告'):
    st.caption('包含原始格式值、文件路径、SHA256及覆盖信息；不纳入默认演示画面。')
    if st.toggle('显示原始完整JSON（长文按需加载）'):
        st.json(model.result if model.result is not None else model.report, expanded=False)
    if model.result is not None:
        for name, download_name in [('result.json','论文有格_完整报告.json'), ('fixed.body.json','论文有格_修正版正文清单.json')]+([('fixed.types.json','论文有格_修正版分类清单.json')] if 'fixed.types.json' in files else []):
            st.download_button('下载' + download_name, files[name], file_name=download_name, mime='application/json',
                               on_click='ignore', key=f'advanced-{model.task_dir.name}-{Path(model.result["output"]).stem}-{name}')


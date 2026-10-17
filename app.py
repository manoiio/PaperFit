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

if 'workflow' not in st.session_state:
    st.session_state.workflow = WebSession(ROOT / 'work/web')
if 'upload_generation' not in st.session_state:
    st.session_state.upload_generation = 0
model = st.session_state.workflow
model.sync_rules()
from web.workflow_ui import go, shell, preserve_editors, render_rules, render_scope_editors, empty_state
preserve_editors()


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


def render_basic_scope():
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
        with st.expander('高级：原分区域确认与独立检查'):
            st.caption('快捷按钮表示本人已核对完整的当前正文范围，确认成功才检查；不执行修正、AI或预览。')
            st.button('核对完成并开始检查',disabled=not model.body,on_click=model.confirm_and_check,type='primary',width='stretch')
            a, b = st.columns([1, 1])
            a.button('确认正文范围', disabled=not model.body, on_click=confirm_body, width='stretch')
            b.button('开始检查', disabled=model.confirmed is None, on_click=run_check, width='stretch')

def render_selection():
    from web.selection_ui import render_selection_tools
    render_selection_tools(model)


def render_results():
    if model.result is None:return
    try:files=model.downloads()
    except Exception as exc:
        model.result=model.result_signature=None;model.error=public_error(exc);st.error('结果不可用：'+model.error);return
    if not files:return
    result,after=model.result,model.result['after']
    checks=result['preservation']
    required=('original_sha256_unchanged','only_authorized_caption_permutation','all_object_subtrees_equal','remaining_objects_relative_order_equal') if result.get('kind')=='caption_position' else ('original_sha256_unchanged','document_except_selected_format_attributes_equal')
    if not all(checks.get(k) is True for k in required) or not checks.get('unselected_zip_member_bytes_equal',checks.get('other_zip_member_bytes_equal')):
        st.error('完整性结果异常，请重新开始。');return
    from web.decision_ui import compact_stats
    summary=after['summary'];n=result['round']['number']
    st.subheader(f'第{n}轮副本已生成')
    compact_stats([('实际修改',len(result['changes'])),('剩余问题',summary['problem_count']),('待复核',summary['review_count'])],'result-summary')
    verified=all(c['verification']=='pass' for c in result['changes'])
    if verified:
        message=f"所选修改的落盘复查全部符合要求 · 已保存{len(result['changes'])}项修改；仅代表所选属性。"
        if summary['problem_count'] or summary['review_count']:st.write(message)
        else:st.success(message)
    else:st.warning('部分修改的复查状态需要核对，请查看完整修改记录。')
    if summary['problem_count'] or summary['review_count']:
        st.warning(f"仍有 {summary['problem_count']} 个问题、{summary['review_count']} 项待复核。副本已生成，不代表全文合格。")
    from web.workspace_status import output_relation
    st.write(output_relation(model,n))
    a,b=st.columns(2)
    a.download_button('下载修正版DOCX',files['fixed.docx'],file_name='论文有格_修正版.docx',mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',on_click='ignore',type='primary',width='stretch',key=f'download-{model.task_dir.name}-{Path(result["output"]).stem}-fixed.docx')
    try:b.download_button('下载本轮结果包',model.result_package(),file_name=f'论文有格_第{n}轮结果.zip',mime='application/zip',on_click='ignore',width='stretch',key='package-'+str(model.revision)+'-'+str(model.generation_count))
    except Exception as exc:b.warning(public_error(exc))
    st.caption('结果包带走本轮DOCX与报告；保存项目用于中断后继续，包含原稿和历史。')
    from web.preview_ui import open_reader
    a,b=st.columns(2)
    a.button('查看本轮页面',on_click=open_reader,args=(model,'round-'+str(n),False),width='stretch',help='仅进入查看，不生成预览、不切换当前输入。')
    b.button('与原稿对比',on_click=open_reader,args=(model,'round-'+str(n),True),width='stretch',help='同页号人工对比；不自动渲染或切换输入。')
    st.button('以计划最终副本继续' if result.get('plan') else '以本轮修正版开始下一轮',on_click=model.next_round,width='stretch',help='以此副本继续处理：只有点击才明确切换输入，原稿和前轮保持。')
    with st.expander('更多文件与记录'):
        for label,name,filename,mime in [('下载原稿DOCX','original.docx','论文有格_原稿.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document'),('下载修改记录','changes.md','论文有格_修改记录.md','text/markdown'),('下载复查报告','recheck.md','论文有格_复查报告.md','text/markdown')]:
            st.download_button(label,files[name],file_name=filename,mime=mime,on_click='ignore',key=f'download-{model.task_dir.name}-{Path(result["output"]).stem}-{name}')
        if result.get('plan'):
            for i,item in enumerate(model.plan_step_downloads(),1):st.download_button(f'下载计划第{i}步DOCX',item['fixed.docx'],file_name=f'计划第{i}步.docx',on_click='ignore',key='result-step-'+str(i))
    with st.expander('完整变更、保护及落盘复查'):
        if result.get('layout'):
            st.info(result['layout']['message']);st.warning(result['layout']['limitation'])
        if result.get('widths'):
            st.info(result['widths']['message']);st.warning(result['widths']['limitation'])
        if any(c['rule_id'] in ('R36','R37') for c in result['changes']):st.info('仅所选注释普通文字属性已修改。正文引用、内部自动编号、系统分隔线和未选部件保持。注释字体字号或行距可能改变分页，请主动预览；格式通过不代表注释内容正确。')
        if any(c['rule_id']=='R35' for c in result['changes']):st.info('仅所选左右外侧边框已修正；内部竖线及未选侧保留。0边框问题不代表表格整体合格。')
        if any(c['rule_id']=='L04' for c in result['changes']):st.info('已设置重复表头属性，不补续表题注、编号或（续）；请主动预览并核对第二页及之后的实际结果。')
        if any(c['rule_id']=='R33' for c in result['changes']):st.info('引文上标已按所选字符设置，字体字号与前后文字保持。通用正文继续保护上标run，会新增未检查覆盖提示；必要拆分可改变run编号/问题key及记录数，不代表未选格式被改变或全文通过。')
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
    with st.expander('保存后复查 · 详细有效格式'):
        with st.container(key='report-after'):
            st.subheader('保存后复查')
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

def render_advanced():
    files=model.downloads() if model.result else {}
    with st.expander('高级详情与完整报告'):
        st.caption('包含原始格式值、文件路径、SHA256及覆盖信息；不纳入默认演示画面。')
        if st.toggle('显示原始完整JSON（长文按需加载）'):
            st.json(model.result if model.result is not None else model.report, expanded=False)
        if model.result is not None:
            for name, download_name in [('result.json','论文有格_完整报告.json'), ('fixed.body.json','论文有格_修正版正文清单.json')]+([('fixed.types.json','论文有格_修正版分类清单.json')] if 'fixed.types.json' in files else []):
                st.download_button('下载' + download_name, files[name], file_name=download_name, mime='application/json',
                                   on_click='ignore', key=f'advanced-{model.task_dir.name}-{Path(model.result["output"]).stem}-{name}')



from web.center_ui import render_center,render_history
from web.project_ui import render_project
if model.report is not None:
    try:model._current()
    except Exception as exc:model.error=public_error(exc)
step=shell(model,restart)
if model.error:st.error('处理未完成：'+model.error)
if step==1:
    st.header('文档与要求')
    if model.inventory is None:
        st.write('检查已有论文的格式，明确选择后另存修正版。先上传DOCX，或使用合成样本体验。')
        st.caption('确认要求和范围 → 检查 → 选择修正与预演 → 复查下载。复杂对象、实际分页仍需人工核对。')
    else:st.write('当前文件已载入。可沿用生效要求，或编辑草稿后明确应用；然后核对检查范围。')
    with st.expander('更换文档或选择内置样本',expanded=model.inventory is None,key='doc-loader-'+(model.task_dir.name if model.task_dir else 'empty')):
        with st.container(border=True,key='document-card'):
            a,b=st.columns([1.4,1])
            with a:
                upload_key=f'upload-{st.session_state.upload_generation}'
                st.file_uploader('上传自己的DOCX（最大10MB）',type=['docx'],max_upload_size=10,key=upload_key,on_change=upload_changed,args=(upload_key,))
            with b:
                st.markdown('**或使用内置合成样本**')
                st.button('使用错误样本',on_click=load_builtin,args=('errors',),width='stretch')
                st.button('使用正确对照',on_click=load_builtin,args=('correct',),width='stretch')
            st.caption('检查和修正在本机完成；只有明确解析公开规范时才调用DeepSeek。')
    render_project(model)
    with st.expander('检查模式与更多内置样本'):
        def mode_changed():
            model.set_mode({'基础检查':'basic','正文及标题题注检查':'extended','单文档扩展检查':'academic'}[st.session_state['check-mode']])
        st.session_state['check-mode']={'basic':'基础检查','extended':'正文及标题题注检查','academic':'单文档扩展检查'}[model.mode]
        st.radio('检查模式',['基础检查','正文及标题题注检查','单文档扩展检查'],key='check-mode',horizontal=True,on_change=mode_changed)
        st.caption('切换模式会使旧报告与确认失效；不会自动启用可选模块或确认范围。')
        if model.mode!='basic':
            c,d=st.columns(2)
            c.button('使用扩展错误样本',on_click=load_builtin,args=('extended-errors',),width='stretch')
            d.button('使用扩展正确对照',on_click=load_builtin,args=('extended-correct',),width='stretch')
        if model.mode=='academic':
            for kind,label in [('academic-errors','使用摘要参考文献错误样本'),('academic-correct','使用摘要参考文献正确对照'),('table-text-errors','使用表格文字错误样本'),('table-text-correct','使用表格文字正确对照')]:st.button(label,on_click=load_builtin,args=(kind,))
    render_rules(model,ROOT)
    st.button('下一步：核对检查范围',on_click=go,args=(2,),disabled=model.inventory is None,type='primary',width='stretch')
elif step==2:
    st.header('确认检查范围')
    if st.session_state.get('workspace-scope-editor',False):
        if model.mode=='basic':
            st.button('返回范围总览（保留已保存草稿，不确认范围）',on_click=lambda:st.session_state.update({'workspace-scope-editor':False}),width='stretch')
            render_basic_scope()
        else:render_scope_editors(model,run_check)
    else:
        st.caption('先进入需要调整的区域，再返回范围摘要统一确认。建议和筛选都不代表确认。')
        from web.scope_ui import render_scope_overview
        render_scope_overview(model,compact=True)
    if model.report:st.button('前往查看问题',on_click=go,args=(3,),type='primary',width='stretch')
elif step==3:
    st.header('查看问题')
    render_center(model,render_selection)
    with st.expander('格式覆盖、题注、引文及目录的完整明细'):
        report_view(model.report,model.inventory)
        from web.caption_ui import render_caption_report
        from web.citation_ui import render_citation_report
        from web.toc_ui import render_toc_report
        render_caption_report(model)
        render_citation_report(model.result['after'] if model.result else model.report)
        render_toc_report(model.result['after'] if model.result else model.report)
    with st.expander('高级：重新检查当前输入'):
        st.button('重新检查',on_click=lambda:model.check(force=True))
    if model.operation!='format':
        with st.container(border=True,key='existing-operations'):
            if model.operation=='width':
                from web.width_ui import render_width_panel
                render_width_panel(model)
            if model.operation=='pagination':
                from web.caption_ui import render_caption_move
                render_caption_move(model)
            if model.operation in ('preview','pagination'):
                from web.preview_ui import render_preview_panel
                render_preview_panel(model)
elif step==4:
    st.header('修正预演')
    st.write(f"当前输入：{'原稿' if model.current_round==0 else '第'+str(model.current_round)+'轮'} → 明确选择 {len(model.selected)} 项 → 预演副本（采用后才成为正式轮次）")
    st.button('返回问题与修改选择',on_click=go,args=(3,))
    if not model.selected:empty_state('尚未选择修正', '返回问题中心查看实际值与要求，再明确选择可修正项；不会默认全选或追加依赖项。')
    else:
        from web.rehearsal_ui import render_rehearsal
        render_rehearsal(model)
    if model.selected:
        with st.expander(f'本次明确选择：全部 {len(model.selected)} 项（含筛选外）',expanded=False):
            lookup={f['key']:f for f in model.eligible()}
            st.dataframe([{'位置':position(lookup[k]['locator']),'规则':lookup[k]['rule_id'],'将修改的属性及要求':field_value(lookup[k]['expected'],lookup[k]['rule_id'],lookup[k]['locator'],True)} for k in model.selected if k in lookup],hide_index=True,width='stretch',height=180)
        for warning in model.report.get('modification_dependencies',[]):
            if set(warning['trigger_keys']) & set(model.selected):st.warning(warning['detail'])
    with st.expander('高级兼容：不经预演直接生成'):
        st.caption('使用同一修正器；无法提前查看实际关联影响。')
        st.button('生成修正版',disabled=not model.selected or model.result is not None,on_click=run_fix,width='stretch')
elif step==5:
    from web.preview_ui import render_preview_panel,open_reader,view_seed
    seed=view_seed(model)
    if st.session_state.get('reader-open-'+seed):
        a,b=st.columns([3,1]);a.header('文档页面')
        b.button('返回结果与下载',on_click=lambda:st.session_state.update({'reader-open-'+seed:False}),width='stretch')
        render_preview_panel(model)
    else:
        st.header('结果与下载')
        if model.result is None:empty_state('当前没有可用的本轮正式输出', '可下载有效检查报告，查看历史，或返回问题中心选择修正。已有历史不会自动变成当前输入。')
        render_results()
        if model.result is None:
            st.button('查看论文页面',on_click=open_reader,args=(model,'input',False),width='stretch')
        with st.expander('阅读报告与原始检查记录'):
            from web.center_ui import render_reading_export
            render_reading_export(model)
            render_advanced()
        with st.expander('历史与中间副本（查看不会切换输入）'):
            render_history(model)
        render_project(model)

from web.workflow_ui import finish_navigation
finish_navigation()

"""Document reading UI; view state never submits rendering or authorizes edits."""
from html import escape
import streamlit as st
from .session import public_error

MODES=('单份查看','并排对比')
SECTIONS=('页面查看','排版辅助','预览详情与人工观察记录')
NAMES={'queued':'排队中','running':'正在运行','succeeded':'成功','failed':'失败','cancelled':'已取消接收结果','invalidated':'已失效','missing':'任务丢失'}
CSS='''<style>
.st-key-reader-canvas {background:#e9eef3;border:1px solid #dce3eb;border-radius:10px;padding:.8rem;}
.st-key-reader-paper-single {max-width:880px;margin-inline:auto;}
.st-key-reader-paper-single, .st-key-reader-paper-left, .st-key-reader-paper-right {background:white;border:1px solid #d8dfe7;border-radius:3px;box-shadow:0 2px 8px #18365014;min-height:260px;}
.reader-label {padding:.35rem .65rem;border-bottom:1px solid #e1e7ee;color:#183650;font-size:14px;overflow-wrap:anywhere;}
.st-key-reader-toolbar [data-testid="stHorizontalBlock"] {align-items:end;}
</style>'''

def view_seed(model):
    return model.task_dir.name

def open_reader(model,key=None,compare=False):
    """Navigation intent only. Called by explicit result-entry buttons."""
    seed=view_seed(model)
    st.session_state['reader-open-'+seed]=True
    st.session_state['reader-request-'+seed]={'target':key,'compare':compare}

def short_name(name):
    return name if len(name)<=38 else name[:35]+'…'

def target_label(model,targets,key,full=False):
    t=targets[key]
    role='原稿' if key=='original' else '当前处理输入 · '+('原稿' if t['round']==0 else f"第{t['round']}轮") if key=='input' else f"第{t['round']}轮副本"
    return role+' · '+(model.display_name if full else short_name(model.display_name))

def page_absence(meta,page):
    if not meta:return '尚未生成此文件的有效预览，请明确点击生成。'
    if page>meta['page_count']:return f"此文件实际{meta['page_count']}页，没有第{page}页。"
    if page>meta['preview_range'][1]:return f"第{page}页超出本次预览范围（仅第1–{meta['preview_range'][1]}页，默认最多10页）；未查看全文。"
    return None

@st.fragment(run_every='2s')
def task_status(model,identity,slot):
    state=model.preview_job_status(identity);status=state['state']
    st.write('预览任务：**'+NAMES.get(status,status)+'**'+f" · 已经过{state.get('elapsed',0):.1f}秒")
    record=model.preview_jobs.get(identity)
    if state.get('error'):
        from core.package import DemoError
        st.warning(public_error(DemoError(state['error'])))
    if status in ('queued','running'):
        st.caption('可继续查看已有页图、问题和下载；取消运行任务仅停止接收结果，不表示渲染进程已停止。')
        if st.button('取消此预览任务',key='cancel-preview-'+identity+'-'+slot):model.cancel_preview(identity);st.rerun()
    elif status=='succeeded' and record:
        if st.button('查看预览',key='view-preview-'+identity+'-'+slot):
            model.preview_view_request=record['key'];st.rerun()

def render_target_state(model,key,meta,seed,side):
    matches=[i for i,r in model.preview_jobs.items() if r['key']==key and r['epoch']==model.preview_epoch]
    active=model.active_preview_job(key)
    if meta and not active:
        st.caption(f"有效页图 · 实际{meta['page_count']}页 / 可看第1–{meta['preview_range'][1]}页 · 生成时环境；重新核对见详情")
        return
    a,b=st.columns([2,1])
    with a:
        if meta:st.caption(f"有效页图 · 实际{meta['page_count']}页 / 可看第1–{meta['preview_range'][1]}页 · 生成时环境，未重新探测")
        elif not matches:st.caption('尚无匹配预览；查看文件不会自动渲染。')
    with b:
        if st.button('核对并复用预览' if meta else '生成页面预览',key='reader-render-'+seed+'-'+side,disabled=bool(active),width='stretch'):
            with st.spinner('核对文件与环境并提交…'):request=model.submit_preview(key)
            if request['state']=='cached':st.info('已复用匹配页图，未创建渲染任务。')
            elif request.get('id'):st.rerun()
    if matches and (not meta or active):task_status(model,matches[-1],side)

def render_preview_panel(model):
    st.html(CSS)
    try:targets=model.preview_targets()
    except Exception as exc:st.warning(public_error(exc));return
    if not targets:st.info('请先确认范围并检查，才能选择绑定当前文件的预览目标。');return
    keys=list(targets);seed=view_seed(model)
    latest=keys[-1]
    request=st.session_state.pop('reader-request-'+seed,None)
    if model.preview_view_request in keys:
        key=model.preview_view_request;model.preview_view_request=None
        side='right' if st.session_state.get('reader-mode-'+seed)=='并排对比' else 'file'
        visible=[st.session_state.get('reader-'+name+'-'+seed) for name in ('left','right')] if side=='right' else [st.session_state.get('reader-file-'+seed)]
        if key not in visible:st.session_state['reader-'+side+'-'+seed]=key
        st.session_state['reader-section-'+seed]='页面查看'
    if request:
        target=request['target'] if request['target'] in keys else latest
        st.session_state['reader-mode-'+seed]='并排对比' if request['compare'] else '单份查看'
        st.session_state['reader-file-'+seed]=target
        st.session_state['reader-left-'+seed]='original';st.session_state['reader-right-'+seed]=target
        st.session_state['reader-section-'+seed]='页面查看'
    section=st.radio('预览工作区',SECTIONS,key='reader-section-'+seed,horizontal=True,label_visibility='collapsed')
    if section=='排版辅助':
        if model.mode=='basic':st.info('基础模式未启用图表/标题相邻辅助；不会因查看页面而启用。')
        else:render_layout(model,targets,keys,latest,seed)
        return
    label=lambda k:target_label(model,targets,k)
    with st.container(key='reader-toolbar'):
        a,b=st.columns([1,2])
        mode=a.radio('查看方式',MODES,horizontal=True,key='reader-mode-'+seed,label_visibility='collapsed')
        selected=[]
        if mode=='单份查看':
            k='reader-file-'+seed
            if st.session_state.get(k) not in keys:st.session_state[k]=latest
            selected=[b.selectbox('正在查看（不切换处理输入）',keys,format_func=label,key=k,help=model.display_name)]
        else:
            l,r=b.columns(2)
            for col,name,default in ((l,'left','original'),(r,'right',latest)):
                k='reader-'+name+'-'+seed
                if st.session_state.get(k) not in keys:st.session_state[k]=default
                selected.append(col.selectbox('左侧文件' if name=='left' else '右侧文件',keys,format_func=label,key=k,help=model.display_name))
    previews={}
    for key in dict.fromkeys(selected):
        try:previews[key]=model.get_preview(key,verify_environment=False)
        except Exception as exc:st.warning(public_error(exc));previews[key]=None
    if section=='预览详情与人工观察记录':
        render_details(model,targets,selected,previews,seed,label);return
    columns=st.columns(len(selected)) if len(selected)>1 else [st.container()]
    for col,key,side in zip(columns,selected,('left','right') if len(selected)>1 else ('single',)):
        with col:render_target_state(model,key,previews[key],seed,side)
    if model.preview_error:st.warning('最近一次预览请求未完成：'+model.preview_error)
    maximum=max([m['page_count'] for m in previews.values() if m] or [1])
    pk='reader-page-number-'+seed
    st.session_state[pk]=min(max(st.session_state.get(pk,1),1),maximum)
    def flip(delta):st.session_state[pk]=min(max(st.session_state[pk]+delta,1),maximum)
    a,b,c,d=st.columns([1,1,1,3])
    a.button('上一页',on_click=flip,args=(-1,),disabled=st.session_state[pk]==1,width='stretch',key='reader-prev-'+seed)
    page=b.number_input('页码',min_value=1,max_value=maximum,key=pk,label_visibility='collapsed')
    c.button('下一页',on_click=flip,args=(1,),disabled=page==maximum,width='stretch',key='reader-next-'+seed)
    d.caption(f'第{page}/{maximum}页 · 最多预览前10页。LibreOffice页图可能与Word不同，不回写DOCX。')
    font_notes=sum(len(m.get('font_notes',[])) for m in previews.values() if m)
    if font_notes:st.caption(f'字体/渲染提示{font_notes}项：可能影响分页；完整替代记录见“预览详情与人工观察记录”。')
    if mode=='并排对比':
        counts=[previews[k]['page_count'] if previews[k] else None for k in selected]
        comparison=('两侧实际页数不同：'+str(counts[0])+' / '+str(counts[1])+'页。' if counts[0]!=counts[1] else '') if all(counts) else '有一侧尚无有效预览，页数暂不能比较。'
        st.caption(comparison+'同页号仅供人工对比，不表示相同内容已自动对齐。')
    with st.container(key='reader-canvas'):
        columns=st.columns(len(selected)) if len(selected)>1 else [st.container()]
        for col,key,side in zip(columns,selected,('left','right') if len(selected)>1 else ('single',)):
            with col,st.container(key='reader-paper-'+side):
                anchor=' id="preview-operations"' if side in ('single','left') else ''
                st.html('<div'+anchor+' class="reader-label" title="'+escape(target_label(model,targets,key,True),quote=True)+'">'+escape(label(key))+f' · 第{page}页</div>')
                absence=page_absence(previews[key],page)
                if absence:st.info(absence)
                else:st.image(previews[key]['pages'][page-1],width='stretch')
    st.caption('正在查看的文件独立于当前处理输入；生成页图不代表已完成视觉验收。字体替代、环境和人工记录见“预览详情与人工观察记录”。')
    others=[i for i,r in model.preview_jobs.items() if r['epoch']==model.preview_epoch and r['key'] not in selected and not r['accepted'] and model.preview_job_status(i)['state'] in ('queued','running','succeeded')]
    if others:
        with st.expander('其他目标的预览任务（不自动切换文件）',expanded=True):
            for i in others:
                st.write(target_label(model,targets,model.preview_jobs[i]['key']) if model.preview_jobs[i]['key'] in targets else '旧目标，需重新核对')
                task_status(model,i,'other')

def render_details(model,targets,selected,previews,seed,label):
    st.caption('预览来自生成时环境，不是Microsoft Word验收。普通查看不探测字体；明确刷新仅重新核对环境，不自动渲染。最多1个任务执行、2个等待；45秒超时。')
    if st.button('刷新预览环境'):
        try:model.refresh_preview_environment();st.info('环境已核对，请返回页面查看；未自动渲染。')
        except Exception as exc:st.warning(public_error(exc))
    for key in dict.fromkeys(selected):
        st.markdown('**'+label(key)+'**');meta=previews[key]
        matches=[i for i,r in model.preview_jobs.items() if r['key']==key and r['epoch']==model.preview_epoch]
        if matches and (not meta or model.active_preview_job(key)):task_status(model,matches[-1],'details')
        if not meta:st.info('没有当前绑定的有效页图；可返回页面查看并明确请求生成。');continue
        st.write(meta.get('renderer','')+' · '+meta.get('renderer_version',''))
        st.caption('生成于 '+meta['generated_at']+' · 实际'+str(meta['page_count'])+'页 · 仅预览'+str(meta['preview_range']))
        for note in meta.get('font_notes',[]):st.warning(note)
        with st.expander('字体映射与完整技术记录'):
            st.dataframe(meta.get('fonts',[]),hide_index=True,width='stretch');st.json(meta,expanded=False)
        if st.button('核对环境并生成 / 复用预览',key='reader-reuse-'+seed+'-'+key):
            request=model.submit_preview(key)
            if request['state']=='cached':st.info('已核对环境并复用页图，没有新渲染。')
            elif request.get('id'):st.rerun()
    available=[k for k in dict.fromkeys(selected) if previews[k]]
    if available:
        st.caption('仅记录人工查看，不把“已查看”当作排版通过。')
        vkey=st.selectbox('已查看的文件',available,format_func=label,key='visual-target-'+seed)
        status=st.radio('人工查看记录',['已查看（不声明无问题）','发现问题'],key='visual-status-'+seed,horizontal=True)
        notes=st.text_input('人工观察（例如图题所在页、仍存在的问题）',max_chars=1000,key='visual-notes-'+seed)
        if st.button('记录人工查看',key='visual-save-'+seed):
            try:model.record_visual_review(vkey,'looked' if status.startswith('已查看') else 'issues',notes);st.info('已记录，不是自动视觉验收。')
            except Exception as exc:st.warning(public_error(exc))
        saved=model.visual_reviews.get(model._preview_binding(targets[vkey],probe=False))
        if saved:st.info('人工记录：'+('已查看（不声明无问题）' if saved['status']=='looked' else '发现问题')+' · '+saved['notes'])

def render_layout(model,targets,keys,latest,seed):
    # Reader preferences survive navigation; auxiliary selections retain the
    # original revision/round binding and are never reused as new authorization.
    seed=f'{model.task_dir.name}-{model.revision}-{model.generation_count}'
    label=lambda k:target_label(model,targets,k)
    with st.container(key='figure-layout'):
        st.markdown('<span id="pagination-operations"></span>',unsafe_allow_html=True)
        st.subheader('图题、表题与标题相邻 / 重复表头 · 产品辅助')
        st.caption('L01 图片与图题；L02 表题与紧接表格开始部分；L03 正文标题与紧接正文，或摘要/参考文献/附录/致谢标题与紧接已确认匹配普通文字。L04 用户明确确认的连续表头行重复。不跨空段串联，不改变内容、编号或尺寸。属性成功不等于可见排版已解决；重复表头不补续表标题、编号和（续）。')
        source=st.selectbox('本次辅助输入',keys,index=keys.index(latest),format_func=label,key='layout-input-'+seed)
        try:proposals=model.layout_proposals(source)
        except Exception as e:st.warning(public_error(e));return
        chosen=[]
        available=[p for p in proposals['pairs'] if p['status']=='available']
        reviews=[p for p in proposals['pairs'] if p['status']=='review']
        for pair in available:
            if st.checkbox('确认 '+pair['id']+'：'+pair['label'],key='pair-'+seed+'-'+targets[source]['sha256']+'-'+pair['key']):chosen.append(pair['key'])
            st.caption(pair['reason'])
        if not available:st.info('没有可安全执行的紧邻建议；请核对分类和原文结构。')
        if reviews:
            with st.expander(f'待复核关联（{len(reviews)}项，不执行）'):
                for pair in reviews:st.warning(pair['id']+' · '+pair['label']+'：'+pair['reason'])
        st.caption(proposals['limitation'])
        if st.button('确认关联并生成排版副本',disabled=not chosen,key='layout-run-'+seed,type='primary'):
            with st.spinner('设置所选分页属性、另存副本并独立读回复查…'):ok=model.generate_layout(source,chosen)
            if ok:st.rerun()
        if model.layout_error:st.error(model.layout_error)

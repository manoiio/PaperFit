from pathlib import Path
import json
import streamlit as st
from .session import public_error

@st.fragment(run_every='2s')
def task_status(model,identity,slot):
    from time import monotonic
    state=model.preview_job_status(identity)
    names={'queued':'排队','running':'运行','succeeded':'成功','failed':'失败','cancelled':'取消（停止接收结果）','invalidated':'已失效','missing':'任务丢失'}
    status=state['state'];st.caption('预览任务：'+names.get(status,status)+f" · 已经过 {state.get('elapsed',0):.1f}秒")
    record=model.preview_jobs.get(identity)
    if record:st.caption(f"目标 {record['key']} · 第{record['target']['round']}轮；与当前查看文件分别绑定。")
    if state.get('error'):st.warning(public_error(__import__('core.package',fromlist=['DemoError']).DemoError(state['error'])))
    if status in ('queued','running'):
        st.caption('后台独立渲染；可继续查看问题、历史和下载已有有效结果。')
        if st.button('取消此预览任务',key='cancel-preview-'+identity+'-'+slot):model.cancel_preview(identity);st.rerun()
    elif status=='succeeded':
        if st.button('查看预览',key='view-preview-'+identity+'-'+slot):
            model.preview_view_request=record['key'];st.rerun()

def render_preview_panel(model):
    st.caption('格式属性检查结果仅针对启用规则及覆盖范围；0问题、0待复核不代表分页和所有可见排版已经验收。')
    st.markdown('<span id="preview-operations"></span>',unsafe_allow_html=True)
    focus=getattr(model,'focus',None)
    with st.expander('本地页面预览、前后对比与排版辅助（可选）',key='page-preview',expanded=True):
        with st.container(key='preview-panel'):
            st.subheader('本地页面预览与排版复核')
            st.caption('主动提交后台渲染，最多1任务执行、2任务等待；渲染45秒超时，只预览前10页。Codex bundled LibreOffice / Poppler，不回写DOCX，不是Word最终排版。')
            st.caption('已有预览标明生成时环境；普通查看不探测字体。点击生成或刷新才核对当前环境，有效结果不重复渲染。')
            st.caption('服务重启不恢复待处理任务；任务丢失需重新生成。关闭本页不会立即终止正在执行的渲染。')
            if st.button('刷新预览环境'):
                try:model.refresh_preview_environment();st.info('已重新核对渲染器与字体环境；不自动渲染。')
                except Exception as exc:st.warning(public_error(exc))
            try:targets=model.preview_targets()
            except Exception as e:st.warning(public_error(e));return
            keys=list(targets)
            label=lambda k: ('原稿' if k=='original' else '当前处理输入' if k=='input' else f"第{targets[k]['round']}轮修正版")+' · '+model.display_name
            latest=focus['target'] if focus and focus['target'] in keys else keys[-1]
            seed=f'{model.task_dir.name}-{model.revision}-{model.generation_count}'
            if model.preview_view_request in keys:
                st.session_state['preview-right-'+seed]=model.preview_view_request
                model.preview_view_request=None
            left,right=st.columns(2)
            lkey=left.selectbox('左侧文件',keys,format_func=label,key='preview-left-'+seed)
            rkey=right.selectbox('右侧文件',keys,index=keys.index(latest),format_func=label,key='preview-right-'+seed)
            others=[identity for identity,record in model.preview_jobs.items() if record['epoch']==model.preview_epoch and record['key'] not in (lkey,rkey) and not record['accepted']
                    and model.preview_job_status(identity)['state'] in ('queued','running','succeeded')]
            if others:
                with st.expander('其他已提交目标的任务（不自动切换文件）',expanded=True):
                    for identity in others:task_status(model,identity,'other-'+identity)
            previews=[]
            for col,key,side in ((left,lkey,'left'),(right,rkey,'right')):
                with col:
                    t=targets[key];st.caption(f"轮次 {t['round']} · 当前规则 {t['context']['rules_name']} v{t['context']['rules_version']}")
                    active=model.active_preview_job(key)
                    if st.button('生成'+('左侧' if side=='left' else '右侧')+'页面预览',key='render-'+side+'-'+seed,disabled=bool(active)):
                        with st.spinner('核对当前文件与预览环境并提交…'):request=model.submit_preview(key)
                        if request['state']=='cached':st.info('已复用匹配预览，未创建后台渲染任务。')
                        elif request.get('id'):st.rerun()
                    matches=[i for i,r in model.preview_jobs.items() if r['key']==key and r['epoch']==model.preview_epoch]
                    if matches:task_status(model,matches[-1],side)
                    try:meta=model.get_preview(key,verify_environment=False)
                    except Exception as e:st.warning(public_error(e));meta=None
                    previews.append(meta)
                    if not meta:st.info('尚未生成匹配的预览。')
                    else:
                        st.caption(' '.join(meta['renderer_version'].split()[:2])+'（Codex bundled）')
                        st.caption('字体：'+'；'.join(f["target"]+' → '+f["resolved_family"] for f in meta['fonts']))
                        st.caption(f"实际 {meta['page_count']} 页 · 预览第1–{meta['preview_range'][1]}页 · 生成于 {meta['generated_at']}")
                        for note in meta['font_notes']:st.warning(note)
            if model.preview_error:st.error(model.preview_error)
            maximum=max([m['preview_range'][1] for m in previews if m] or [1])
            page=st.selectbox('对比页码',list(range(1,maximum+1)),key='preview-page-'+seed)
            a,b=st.columns(2)
            for col,key,meta in zip((a,b),(lkey,rkey),previews):
                with col:
                    st.markdown('**'+label(key)+f' · 第{page}页**')
                    if meta and page<=meta['preview_range'][1]:st.image(meta['pages'][page-1],width='stretch')
                    elif meta:st.info('此文件没有对应的预览页（可能页数不同或超出预览范围）。')
            if any(previews):
                with st.expander('预览记录及人工视觉结论'):
                    st.caption('以下按钮仅记录本人查看，不会让程序认定同页或学校验收通过。')
                    vkey=st.selectbox('已查看的文件',[k for k in (lkey,rkey) if model.get_preview(k,verify_environment=False)],format_func=label,key='visual-target-'+seed)
                    status=st.radio('人工查看记录',['已查看（不声明无问题）','发现问题'],key='visual-status-'+seed,horizontal=True)
                    notes=st.text_input('人工观察（例如图题所在页、仍存在的问题）',max_chars=1000,key='visual-notes-'+seed)
                    if st.button('记录人工查看',key='visual-save-'+seed):
                        model.record_visual_review(vkey,'looked' if status.startswith('已查看') else 'issues',notes);st.info('已记录人工观察，不是自动视觉验收。')
                    saved=model.visual_reviews.get(model._preview_binding(model.preview_targets()[vkey],probe=False))
                    if saved:st.info('人工记录：'+('已查看（不声明无问题）' if saved['status']=='looked' else '发现问题')+' · '+saved['notes'])
                    for meta in [m for m in previews if m]:st.json(meta,expanded=False)
            if model.mode!='basic':
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

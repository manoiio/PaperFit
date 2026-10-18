"""Optional native artifacts after DOCX publication. No new formatting authorization."""
from pathlib import Path
from io import BytesIO
import json,zipfile
import streamlit as st
from .session import public_error

def render_native_output(model,state):
    targets=model.preview_targets()
    if not targets:return
    key=list(targets)[-1];target=targets[key]
    request=state.get('native_output')
    if request and request.get('sha256')!=target['sha256']:
        state.pop('native_output',None);request=None
    # Only the Start command's recorded explicit output option can auto-submit.
    if state.get('native_output_requested') and not request:
        model.set_preview_engine('word');submitted=model.submit_preview(key)
        request=state['native_output']={'sha256':target['sha256'],'target':key,**submitted}
    if not request:st.caption('PDF / Word页面尚未生成；可按需生成，不影响DOCX下载。')
    a,b=st.columns(2)
    if a.button('查看最终Word页面',key='smart-view-word',width='stretch'):
        model.set_preview_engine('word');state['native_reader_open']=True
        from .preview_ui import view_seed
        st.session_state['reader-engine-'+view_seed(model)]='word'
    if b.button('生成 / 复用Word预览和PDF',key='smart-generate-word',width='stretch',disabled=bool(request and request.get('id') and model.preview_job_status(request['id'])['state'] in ('queued','running'))):
        model.set_preview_engine('word');submitted=model.submit_preview(key)
        request=state['native_output']={'sha256':target['sha256'],'target':key,**submitted};st.rerun()
    pending=bool(request and request.get('id') and model.preview_job_status(request['id'])['state'] in ('queued','running'))
    @st.fragment(run_every=2 if pending else None)
    def progress():
        request=state.get('native_output')
        if not request:return
        status=model.preview_job_status(request['id']) if request.get('id') else request
        if pending and status['state'] not in ('queued','running') and not request.get('terminal_seen'):
            request['terminal_seen']=True;st.rerun()  # Rebuild once without the polling timer.
        if status['state'] in ('queued','running'):st.info('Word PDF：'+('排队中' if status['state']=='queued' else '正在导出/生成页图')+'。DOCX已可下载，您可以继续查看结果。')
        elif status['state'] in ('failed','invalidated','missing','cancelled'):st.warning('Word PDF未完成：'+status.get('error',request.get('error','未接入结果'))+'。上方DOCX保持可用。')
        if request.get('id') and status['state'] in ('queued','running') and st.button('停止接收PDF结果',key='smart-cancel-pdf'):
            model.cancel_preview(request['id']);st.rerun()
        # Explicit engine lookup, independent of whichever preview is currently viewed.
        old=model.preview_engine;model.set_preview_engine('word')
        try:meta=model.get_preview(key,verify_environment=False)
        finally:model.set_preview_engine(old)
        if meta:
            st.caption('Word原生PDF · '+str(meta['page_count'])+'页 · 对应最终DOCX '+meta['document_sha256'][:12]+'。PDF不代表全文合格。')
            st.download_button('下载PDF',Path(meta['pdf']).read_bytes(),file_name='论文有格_修正版.pdf',mime='application/pdf',on_click='ignore',key='smart-download-pdf',width='stretch')
            if model.result and st.checkbox('结果包包含PDF及生成记录',key='smart-pdf-package'):
                package_key=(target['sha256'],meta['word_export']['pdf_sha256'],model._history_binding())
                package=state.get('native_bundle')
                if not package or package['binding']!=package_key:
                    buf=BytesIO()
                    with zipfile.ZipFile(BytesIO(model.result_package())) as source,zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as out:
                        for info in source.infolist():out.writestr(info,source.read(info))
                        out.writestr('Word预览.pdf',Path(meta['pdf']).read_bytes());out.writestr('Word输出记录.json',json.dumps({k:v for k,v in meta.items() if k not in ('pages','page_map','artifact_sha256','pdf')},ensure_ascii=False,indent=2))
                    package=state['native_bundle']={'binding':package_key,'bytes':buf.getvalue()}
                st.download_button('下载含PDF的结果包',package['bytes'],file_name='论文有格_成果.zip',on_click='ignore',key='smart-pdf-zip')
    progress()
    if state.get('native_reader_open'):
        with st.expander('最终页面（查看不切换处理输入）',expanded=True):
            from .preview_ui import render_preview_panel
            render_preview_panel(model)

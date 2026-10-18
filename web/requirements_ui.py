"""Simple source choice; extraction is local, start alone applies or calls AI."""
from copy import deepcopy
import streamlit as st
from core.package import sha256
from .requirements_input import file_input,saved_input
from .onepass_session import cancel
from .session import public_error

def render_requirements(model,task,state):
    ui=st.session_state.setdefault('requirements-ui-'+task,{'choice':'current','buffers':{},'selected':None})
    def changed(key=None):
        cancel(model,state)  # Invalidates only this command, not stored rounds or rules.
        if key and st.session_state.get(key) is None:ui['buffers'].pop(ui['choice'],None)
    key='requirements-choice-'+task
    if key not in st.session_state:st.session_state[key]=ui['choice']
    choice=st.radio('排版要求来源',['current','file','saved'],format_func={'current':'当前要求（可补充文字）','file':'上传格式要求文件','saved':'使用已保存的要求'}.get,key=key,horizontal=True,on_change=changed)
    ui['choice']=choice;extra='';source=None;ready=True
    if choice=='current':
        extra=st.text_input('还有其他要求吗？（可选）',placeholder='例如：正文宋体小四，首行缩进两字符；一级标题黑体三号居中；表内文字五号',key='onepass-extra-'+task,max_chars=2000,on_change=changed,
                            help='只覆盖明确提及的已有支持属性；冲突或不支持要求集中询问。')
    else:
        upload_key='requirements-upload-'+task+'-'+choice+'-'+str(ui.get('generation',0))
        file=st.file_uploader('格式要求文件TXT/DOCX（最大2MB）' if choice=='file' else '已保存的排版要求文件',type=['txt','docx'] if choice=='file' else ['json'],max_upload_size=2 if choice=='file' else 1,key=upload_key,on_change=changed,args=(upload_key,),disabled=model.inventory is None)
        encoding='auto'
        if choice=='file':
            with st.expander('TXT编码与提取范围'):
                encoding=st.selectbox('TXT编码',['auto','utf-8-sig','utf-16','gb18030'],format_func={'auto':'自动（UTF-8/BOM）','utf-8-sig':'UTF-8','utf-16':'UTF-16','gb18030':'GB18030（中文旧编码）'}.get,key='requirements-encoding-'+task,on_change=changed)
                st.caption('仅提取普通文本，不执行域或嵌入对象。超过一次请求预算会拒绝，不截取前几页。')
        try:
            if file is not None:
                data=file.getvalue();identity=(sha256(data),encoding)
                saved=ui['buffers'].get(choice)
                if not saved or saved['identity']!=identity:
                    source=file_input(model,data,file.name,encoding) if choice=='file' else saved_input(model,data,file.name)
                    ui['buffers'][choice]={'identity':identity,'source':source}
            source=deepcopy(ui['buffers'].get(choice,{}).get('source'));ready=source is not None
            if source:
                st.text('格式要求：'+source['name'])
                if choice=='file':
                    e=source['extraction'];st.caption(f'已提取 {len(e["segments"])} 个文本位置，共 {sum(len(s["text"]) for s in e["segments"])} 字符。仅明确支持的规定覆盖当前值，未提及要求沿用。')
                    if e['unextracted']:st.warning('有未提取内容；开始后会集中询问是否只按已验证部分处理。')
                    with st.expander('查看要求原文与位置（尚未发送）'):
                        for s in e['segments']:st.text(s['location']+' · '+s['text'])
                        for n in e['notes']:st.caption(n)
                        st.caption('文件SHA256：'+e['file_sha256'])
                else:
                    st.write('将使用：'+source['bundle']['name']);st.caption('已通过本地严格校验；点击开始才用于本次任务，不重发规范解析。结构识别仍可能需要AI。')
                if st.button('移除此要求文件',key='requirements-remove-'+task):
                    changed();ui['buffers'].pop(choice,None);ui['selected']=None;ui['generation']=ui.get('generation',0)+1;st.rerun()
            else:st.info(('请上传' if model.inventory else '请先上传待排版论文，再上传')+('老师提供的TXT/DOCX要求。' if choice=='file' else '之前保存的排版要求。'))
        except Exception as exc:
            ready=False;source=None;st.error(public_error(exc));st.caption('未发送API、未改变当前规则。请缩小到格式要求章节或更换文件。')
    ui['selected']=deepcopy(source)
    return extra,source,ready

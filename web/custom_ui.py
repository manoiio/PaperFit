"""可折叠规范草稿与完整确认配置；没有网络缓存或跨会话状态。"""
import streamlit as st
import json
import html
from pathlib import Path
from ai.short_spec import config_status
from core.package import DemoError
from core.rule_config import KINDS
from .presentation import fmt

EXAMPLES={'A':'正文小四号，1.5倍行距','B':'正文四号，2倍行距'}

def configuration_table(config):
    headers=['规则','最终要求','字段来源','依据']
    rows=[]
    for rid,cfg in config['rules'].items():
        source=cfg.get('source')
        cells=[rid+' '+cfg['name'],fmt(cfg['expected'],rid,True),source['label'] if source else '默认演示规则（保持）',
               source['quote'] if source else f"学校手册物理页{cfg['page']}：{cfg['quote']}"]
        rows.append('<tr>'+''.join('<td>'+html.escape(str(c))+'</td>' for c in cells)+'</tr>')
    return '<div class="report-scroll"><table class="report-table config-table"><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
MODES={'请选择处理方式':'choose','采用提取草稿（可编辑）':'ai','沿用默认值':'default','手动指定':'manual'}
REASONS={'title':'标题要求不在本阶段范围','fixed_spacing':'固定磅值行距不支持','minimum_spacing':'最小值行距不支持',
         'ambiguous':'含糊，需人工确认','conflict':'要求冲突，需人工确认','out_of_range':'超出本原型支持范围','unsupported':'本阶段未支持'}

def render_custom(model):
    def text_changed():model.set_spec_text(st.session_state['short-spec-text'])
    def example(kind):
        st.session_state['short-spec-text']=EXAMPLES[kind]
        model.set_spec_text(EXAMPLES[kind])
    def parse():
        with st.spinner('正在调用DeepSeek解析短规范（最多一次请求，无自动重试）…'):
            model.parse_spec()
    def mode_changed(rule,key):
        mode=MODES[st.session_state[key]]
        model.edit_draft(rule,mode)
        if mode=='default':
            st.session_state[f'draft-value-{model.draft_generation}-{rule}']=float(model.draft_values[rule])
    def value_changed(rule,key):model.edit_draft(rule,model.draft_modes[rule],st.session_state[key],touched=True)
    def apply():model.apply_draft()
    historical=Path(__file__).resolve().parents[1]/'work/phase3/final/real-api-record.json'
    def history():
        if model.load_historical_spec(historical):
            st.session_state['short-spec-text']=model.spec_text
    with st.expander('自定义格式要求（可选：仅R05、R06）',key='custom-format'):
        st.caption('论文检查与修正在本机完成，规范解析会调用DeepSeek。只发送你在下面输入的公开短格式要求，不发送文档、段落或路径。')
        st.caption('这个兼容入口只自定义正文普通文字字号和倍数行距；其他R01–R04、R07继续使用默认演示规则。支持边界不是学校通用规范。')
        a,b,_=st.columns([1,1,3])
        a.button('填入示例A',on_click=example,args=('A',),width='stretch')
        b.button('填入示例B',on_click=example,args=('B',),width='stretch')
        if 'short-spec-text' not in st.session_state:st.session_state['short-spec-text']=model.spec_text
        st.text_area('短格式要求（最多2000字符）',key='short-spec-text',max_chars=2000,height=90,on_change=text_changed,
                     placeholder='例如：正文四号，2倍行距')
        status=config_status()
        st.caption(status['message']+(' · '+status['model'] if status['model'] else ''))
        st.button('解析要求',on_click=parse,disabled=not model.spec_text.strip() or model.ai_busy or model.ai_draft is not None or not status['configured'])
        if historical.exists():
            with st.expander('历史验收解析记录（不发起新请求）'):
                st.caption('沿用第三阶段已记录的真实DeepSeek公开规范B结果。本次不调用API，不标成实时解析。')
                st.button('沿用已记录的真实解析B',on_click=history)
        if model.ai_error:st.error('规范未应用：'+model.ai_error)
        if model.ai_receipt:
            receipt=model.ai_receipt
            label=('历史真实DeepSeek解析结果（沿用记录，本次请求0次）' if receipt.get('historical_reuse') else '真实DeepSeek调用') if receipt['kind']=='real_api' else '模拟API响应（仅测试，不是真实调用）'
            st.caption(f"{label} · 模型 {receipt['model']} · 返回时间 {receipt['timestamp_utc']}；当前草稿已保留，不会自动再次请求。")
            st.download_button('下载规范解析记录',
                               (json.dumps({'draft':model.ai_draft,'receipt':receipt},ensure_ascii=False,indent=2)+'\n').encode(),
                               file_name='论文有格_规范解析记录.json',mime='application/json',on_click='ignore',
                               key='parse-record-'+str(model.draft_generation))
        else:
            st.caption('未解析字段保持空值；没有API配置时仍可明确手动指定或沿用默认，固定模板照常工作。')
        rows=[]
        for rid,name,label in [('R05','font_size','正文普通文字字号'),('R06','line_spacing','正文倍数行距')]:
            f=model.ai_draft[name] if model.ai_draft else None
            rows.append({'字段':label,'提取值':fmt(f['value'],rid,True) if f else '空值（未提取）',
                         '原文依据':f['quote'] if f else '无，不自动补默认','支持情况':'已通过本地校验，等待确认' if f else '请明确决定默认继承或手动指定'})
        st.dataframe(rows,hide_index=True,width='stretch')
        if model.ai_draft:
            for note in model.ai_draft['unsupported']:
                st.warning(f"未支持或需确认：{note['quote']} · {REASONS[note['reason']]}")
        st.markdown('**编辑规则草稿**')
        st.caption('编辑这里只改变待确认草稿。当前文档仍使用已应用的配置，直到点击“确认并应用”。')
        for rid,name,label in [('R05','font_size','正文字号'),('R06','line_spacing','正文行距')]:
            candidate=model.ai_draft[name] if model.ai_draft else None
            options=['采用提取草稿（可编辑）','沿用默认值','手动指定'] if candidate else ['请选择处理方式','沿用默认值','手动指定']
            mode_key=f'draft-mode-{model.draft_generation}-{rid}'
            if mode_key not in st.session_state:
                st.session_state[mode_key]=next(k for k,v in MODES.items() if v==model.draft_modes[rid])
            c1,c2=st.columns([1,1])
            c1.selectbox(label+'来源处理',options,key=mode_key,on_change=mode_changed,args=(rid,mode_key))
            value_key=f'draft-value-{model.draft_generation}-{rid}'
            if value_key not in st.session_state:st.session_state[value_key]=float(model.draft_values[rid])
            disabled=model.draft_modes[rid] in ('choose','default')
            if rid=='R05':
                c2.number_input('字号（pt，8–24，步长0.5）',min_value=8.0,max_value=24.0,step=0.5,key=value_key,
                                disabled=disabled,on_change=value_changed,args=(rid,value_key))
            else:
                c2.selectbox('倍数行距',options=[1.0,1.25,1.5,2.0],key=value_key,disabled=disabled,
                             on_change=value_changed,args=(rid,value_key))
        try:
            proposed=model.proposed_rules()
        except (DemoError,ValueError) as exc:
            proposed=None
            st.info(str(exc))
        with st.container(key='rule-confirmation'):
            st.markdown('**最终完整配置预览（尚未应用）**')
            if model.ai_receipt and model.ai_receipt.get('historical_reuse'):
                st.caption('沿用已记录的真实DeepSeek解析结果 · '+model.ai_receipt['model']+' · 原调用 '+model.ai_receipt['timestamp_utc']+' · 本次请求0次（历史结果，不是实时调用）')
            if proposed:
                preview=proposed
                if model.mode=='extended':
                    from core.extended import extend_rules
                    preview=extend_rules({**proposed,'sha256':'preview-only'})
                st.markdown(configuration_table(preview),unsafe_allow_html=True)
                st.caption('配置名称：用户确认的演示规则。编辑过的字段标为“用户确认值”，不会声称原文精确支持。')
            st.button('确认并应用',on_click=apply,type='primary',disabled=proposed is None or model.inventory is None)
        st.button('切换回默认演示规则',on_click=model.use_default_rules,disabled=model.active_custom_data is None)
        if model.custom_rules_path and model.active_template is None:
            st.success('当前使用：用户确认的演示规则。新配置已保存；请重新确认正文并检查。')
            st.download_button('下载当前自定义规则',model.custom_rules_path.read_bytes(),file_name='论文有格_用户确认规则.json',
                               mime='application/json',on_click='ignore',key='download-custom-'+model.custom_rules_path.stem)

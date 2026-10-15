"""规范导入与模板确认UI；只操作会话草稿，不复制检查器。"""
from pathlib import Path
import streamlit as st
from core.templates import FIELDS, ALL_FIELDS, EXT_FIELDS, ALIGNMENTS, CN, WEST, SOURCE_LABELS, local_review_notes, object_review_notes, defaults, split_field
from core.norms import marked_text
from core.package import DemoError
from .session import public_error


def display_value(name,value):
    if name=='paper':return 'A4竖向（210×297mm）'
    if name in ('font_cn','font_western') or name.endswith('_font_cn'):return str(value)
    if name.endswith('_alignment'):return ALIGNMENTS[value]
    if name.startswith('margin_'):return f'{value:g}mm'
    if name.endswith('font_size'):return f'{value:g}pt'
    if name.endswith('line_spacing'):return f'{value:g}倍'
    if name=='first_line_indent':return f'首行{value:g}字符' if value else '无首行缩进（0字符）'


def render_templates(model, root):
    if model.mode=="academic" or len(model.template_fields)>26 or (model.active_template and model.active_template["structure_version"]==4):
        from .academic_ui import render_academic_templates
        return render_academic_templates(model,root)
    def guarded(action):
        try:action()
        except Exception as exc:model.template_error=public_error(exc)
    with st.expander('规范文件与可复用模板（'+('R01–R12' if model.mode=='extended' else 'R01–R07')+'）',expanded=False):
        st.caption('格式要求与待检查论文是两份文件。文件解析、论文检查和修正在本机完成；只有点击解析时，将已核对的规范摘录交给DeepSeek。扩展模式可自定义各级标题与两类题注；R11结构与标题/题注西文槽位沿用固定规则。基础模式仅执行正文/页面要求。')
        st.markdown('**1. 导入规范或输入文字**')
        g=model.template_generation
        c1,c2,c3=st.columns([1,1,2])
        def demo(name):
            path=root/'samples'/name
            if model.load_norm(path.read_bytes(),name):
                model.select_norm_segments([s['location'] for s in model.norm_inventory['segments']])
        c1.button('导入演示规范A（TXT）',on_click=lambda:guarded(lambda:demo('norm-A.txt')))
        c2.button('导入演示规范B（DOCX）',on_click=lambda:guarded(lambda:demo('norm-B.docx')))
        def encoding_changed():
            file=st.session_state.get(f'norm-upload-{st.session_state.get("upload_generation",0)}')
            if file is not None:model.load_norm(file.getvalue(),file.name,encoding=st.session_state.get('norm-encoding','auto'))
        encoding=c3.selectbox('TXT解码',('auto','utf-8-sig','utf-16','gb18030'),format_func=lambda x:{'auto':'自动：UTF-8 / BOM UTF-16','utf-8-sig':'UTF-8（严格）','utf-16':'UTF-16（需BOM）','gb18030':'GB18030（明确选择）'}[x],key='norm-encoding',on_change=encoding_changed)
        def uploaded(key):
            file=st.session_state.get(key)
            if file is not None:
                model.load_norm(file.getvalue(),file.name,encoding=st.session_state.get('norm-encoding','auto'))
        norm_key=f'norm-upload-{st.session_state.get("upload_generation",0)}'
        st.file_uploader('上传格式要求文件（TXT/DOCX，最大2MB）',type=['txt','docx'],max_upload_size=2,key=norm_key,on_change=uploaded,args=(norm_key,))
        if model.mode=='extended':
            c1,c2=st.columns(2)
            c1.button('导入标题题注规范A',on_click=lambda:guarded(lambda:demo('norm9-A.txt')))
            c2.button('导入标题题注规范B',on_click=lambda:guarded(lambda:demo('norm9-B.txt')))
        if model.norm_inventory:
            st.caption('规范预览 · '+model.norm_inventory['kind'].upper()+' · 来源编号只用于定位规范文本，不是论文段落编号')
            rows=model.norm_inventory['segments']
            st.dataframe([{'来源位置':s['location'],'提取文本':s['text']} for s in rows],hide_index=True,width='stretch')
            for note in model.norm_inventory['notes']:st.caption(note)
            choose=st.multiselect('选择交给AI的规范段落或表格文字',options=[s['location'] for s in rows],default=[s['location'] for s in rows],format_func=lambda loc:loc+' · '+next(s['text'][:65] for s in rows if s['location']==loc),key=f'norm-segments-{g}')
            st.button('使用所选规范文字',on_click=lambda:guarded(lambda:model.select_norm_segments(choose)))
            st.caption('未点击解析不会发送；可删去无关条款。超限时须缩小范围，不会静默截断。')
        text_key=f'norm-text-{g}'
        def edit_text():model.set_norm_text(st.session_state[text_key])
        st.text_area('核对并编辑待发送规范（最多12000字符，含来源标记）',value=model.norm_text,height=150,key=text_key,on_change=edit_text)
        st.caption(f'规范正文 {len(model.norm_text)} 字符；手动编辑后使用“摘录:L…”来源标记。')
        c1,c2=st.columns(2)
        c1.button('已核对，确认待发送文本',on_click=lambda:guarded(model.confirm_norm_text),disabled=not model.norm_text.strip())
        def parse():
            with st.spinner('正在调用DeepSeek并按对象校验规则草稿（仅一次请求）…'):model.parse_template()
        c2.button('解析R01–R12要求' if model.mode=='extended' else '解析R01–R07要求',on_click=parse,disabled=model.norm_confirmed_hash is None or model.template_draft is not None or model.template_busy,type='primary')
        if model.norm_confirmed_hash:st.caption('待发送摘录已核对；请求只包含规范摘录和本地来源标记。')
        if model.template_error:st.error(model.template_error)
        if model.template_receipt:
            receipt=model.template_receipt
            st.caption(('项目恢复的历史解析（本次请求0次）' if receipt.get('historical_reuse') else '本次真实API解析' if receipt['kind']=='real_api' else '模拟API解析（自动验收）')+f' · {receipt["model"]} · {receipt["timestamp_utc"]}')
        st.markdown('**或导入已保存模板，不调用AI**')
        import_key=f'template-upload-{st.session_state.get("upload_generation",0)}'
        def load_template():
            file=st.session_state.get(import_key)
            if file is not None:model.import_template(file.getvalue())
        st.file_uploader('载入JSON模板（最大64KB）',type=['json'],max_upload_size=1,key=import_key,on_change=load_template)
        if model.template_error and model.template_import is None and model.template_draft is None:st.caption('失败不会替换当前生效规则；固定规则及已确认模板仍可使用。')
        if model.template_draft is not None or model.template_import is not None:
            with st.container(key='template-draft-preview'):
                st.markdown('**2. 编辑并确认完整模板**')
                if model.template_import:
                    st.info('这是导入模板，尚未应用；本次未调用AI。导入文件的来源记录不证明实时解析或学校认可，需重新核对完整配置。')
                fields=model.template_fields
                if model.template_import and model.template_import['structure_version']==2:
                    st.info('版本2保留原正文值；缺失标题题注字段继续沿用旧版本固定要求，不静默更换。下方确认按钮会确认这一完整含义；需要自定义时可明确升级。')
                    from core import load_rules
                    fixed=defaults(load_rules(model.rules_path),extended=True)
                    if model.mode=='extended':st.dataframe([{'字段':ALL_FIELDS[n][1],'旧版固定要求':display_value(n,fixed[n]),'来源':'沿用旧版本固定要求'} for n in EXT_FIELDS],hide_index=True,width='stretch')
                    st.button('升级到版本3并核对标题题注',on_click=lambda:guarded(model.upgrade_template_draft))
                elif model.template_import and model.template_import.get('compatibility'):
                    st.info('已明确进行版本2→3本地兼容转换：正文值不变，新增字段源为旧版固定要求。编辑后改记用户确认值。')
                preview=[]
                for name,(rid,label,unit) in fields.items():
                    if model.mode=='basic' and name in EXT_FIELDS:continue
                    f=model.template_draft[name] if model.template_draft else None
                    source=model.template_import['field_sources'][name] if model.template_import else None
                    preview.append({'规则':rid,'字段':label,'提取值/导入值':display_value(name,f['value']) if f else display_value(name,model.template_values[name]) if source else '空值（未提取）',
                                    '原文依据':f['quote'] if f else source['quote'] if source else '须明确选择沿用默认值或手动指定',
                                    '来源位置':f['location'] if f else source['location'] or '—' if source else '—','支持情况':'支持（待确认）' if f or source else '未提取或无法自动执行，不自动补齐'})
                st.dataframe(preview,hide_index=True,width='stretch')
                notes=list(model.template_draft['unsupported']) if model.template_draft else []
                notes+=object_review_notes(model.norm_segments) if model.template_fields is ALL_FIELDS else local_review_notes(model.norm_segments)
                grouped={}
                labels={'printing':'打印要求','title':'标题/摘要/题注','fixed_spacing':'固定值行距','minimum_spacing':'最小值行距','conflict':'冲突待确认','ambiguous':'含糊待确认','unknown_font':'未知字体','landscape':'横向纸张','indent_unit':'缩进单位不支持','unsupported':'未支持','out_of_range':'超出范围','semantic':'语义要求'}
                for note in notes:grouped.setdefault((note['location'],note['quote']),set()).add(labels[note['reason']])
                for (loc,quote),reasons in grouped.items():st.warning('本阶段不执行或需确认 · '+', '.join(sorted(reasons))+' · '+loc+'：'+quote)
                st.caption('提示包括AI返回及本地保守核对；不支持的条款不会进入可执行字段。')
            name_key=f'template-name-{g}'
            def named():model.template_name=st.session_state[name_key]
            st.text_input('模板名称（用户命名，不代表学校官方规范）',value=model.template_name,key=name_key,on_change=named)
            st.caption('未提到的字段不能称为AI结果。用户修改后的字段标为“用户确认值”，即使保留原文也不声称修改值精确受原文支持。')
            st.button('未提取字段全部沿用默认值（明确选择）',on_click=model.choose_missing_defaults)
            fields=model.template_fields
            groups=[('正文及页面','body'),('一级标题（R08）','heading1'),('二级标题（R09）','heading2'),('三级标题（R10）','heading3'),('图题（R12）','figure_caption'),('表题（R12）','table_caption')]
            for group,obj in groups:
                names=[n for n in fields if split_field(n)[0]==obj]
                if not names or (model.mode=='basic' and obj!='body'):continue
                with st.expander(group+' · 核对提取值及最终值',expanded=obj=='body'):
                    for name in names:
                        field_input(model,name,g)
            with st.container(key='template-final-configuration'):
                try:
                    cfg=model.proposed_template()
                    final=[{'字段':ALL_FIELDS[n][1],'最终值':display_value(n,cfg['final_values'][n]),'来源':SOURCE_LABELS[cfg['field_sources'][n]['kind']]} for n in model.template_fields if model.mode=='extended' or n not in EXT_FIELDS]
                    st.markdown('**确认后实际使用的完整配置**')
                    if model.template_receipt:
                        receipt=model.template_receipt
                        st.caption(('项目恢复的历史解析草稿（本次请求0次）' if receipt.get('historical_reuse') else '本次真实DeepSeek解析草稿，经用户核对/编辑' if receipt['kind']=='real_api' else '模拟解析草稿（非真实调用）')+' · '+receipt['model']+' · '+receipt['timestamp_utc'])
                    elif model.template_import:st.caption('导入模板待重新确认 · 本次没有API请求')
                    if cfg['structure_version']==3 and model.mode=='extended':
                        object_configuration(cfg)
                        with st.expander('完整逐字段来源及正文配置'):
                            st.dataframe(final,hide_index=True,width='stretch',height=650)
                    else:st.dataframe(final,hide_index=True,width='stretch')
                    st.caption('结构版本 '+str(cfg['structure_version'])+'；R11结构规则固定；标题西文/数字Times New Roman、题注西文槽位宋体仍固定。分页辅助不会随模板应用。保存模板不等于学校验收。')
                    if model.mode=='basic':
                        st.info('基础模式只执行R01–R07；标题与题注配置即使保存，也没有在本模式检查。')
                        if cfg['structure_version']==3:
                            with st.expander('完整模板中未启用的标题题注配置（仅保存）'):
                                st.dataframe([{'字段':ALL_FIELDS[n][1],'最终值':display_value(n,cfg['final_values'][n]),'来源':SOURCE_LABELS[cfg['field_sources'][n]['kind']]} for n in EXT_FIELDS],hide_index=True,width='stretch')
                    can_apply=True
                except DemoError as exc:
                    st.info(str(exc));can_apply=False
                st.button('确认并应用完整模板',on_click=model.apply_template,disabled=not can_apply,type='primary')
        st.markdown('**当前已应用的模板**')
        if model.active_template and model.rules_hash is not None:
            extraction=model.active_template['extraction']
            kind_label={'real_api':'真实API解析记录','mock_api':'模拟API解析记录（非真实调用）','none':'无API解析，人工指定/默认继承','unverified_import':'未验真的导入来源记录'}[extraction['kind']]
            st.caption('模板解析来源：'+kind_label+(' · '+extraction['model']+' · '+extraction['timestamp_utc'] if extraction['model'] else '')+'；导入时仅核对值和依据，不证明文件所报API来源。')
            st.success(model.active_template['name']+' · 已在本机确认并应用；论文范围须重新确认后检查。')
            if model.active_template['structure_version']==3 and model.mode=='extended':object_configuration(model.active_template)
            with st.expander('当前模板逐字段值及来源',expanded=model.mode=='basic'):
                st.dataframe([{'字段':ALL_FIELDS[n][1],'值':display_value(n,v),'来源':SOURCE_LABELS[model.active_template['field_sources'][n]['kind']]} for n,v in model.active_template['final_values'].items() if model.mode=='extended' or n not in EXT_FIELDS],hide_index=True,width='stretch')
            try:raw=model.template_download()
            except Exception as exc:
                raw=None;model.invalidate();model.template_error=public_error(exc);st.error(model.template_error)
            if raw:st.download_button('保存已确认JSON模板',data=raw,file_name='confirmed-template.json',mime='application/json',on_click='ignore')
        elif model.active_template:st.error('当前模板不可用，请重新载入确认或恢复默认规则。')
        else:st.caption('当前没有应用用户模板；待编辑草稿不会改变生效规则。')
        st.button('恢复默认学校演示规则',on_click=model.use_default_rules,disabled=model.active_custom_data is None)
        st.caption('默认“华工本科工理类2015演示规则”保持只读；不宣称为当前学校现行标准。')


def field_input(model,name,g):
    label=ALL_FIELDS[name][1]
    f=model.template_draft[name] if model.template_draft else None
    options=['choose','manual','default']
    if f:options.insert(1,'ai')
    if model.template_import:options.insert(1,'imported')
    labels={'choose':'未决定：请选择','ai':'使用AI提取值','manual':'手动指定（明确取舍）','default':'沿用默认值','imported':'沿用导入值（待确认）'}
    mode_key=f'tpl-mode-{g}-{name}';value_key=f'tpl-value-{g}-{name}'
    cols=st.columns([2,2])
    def mode_changed():
        model.edit_template(name,st.session_state[mode_key])
        val=model.template_values[name]
        st.session_state[value_key]=float(val) if name.endswith('font_size') or name.startswith('margin_') else val
    mode=cols[0].selectbox(label+'来源',options,index=options.index(model.template_modes[name]),format_func=labels.get,key=mode_key,on_change=mode_changed)
    def value_changed():model.edit_template(name,model.template_modes[name],st.session_state[value_key],touched=True)
    value=model.template_values[name]
    choices=['A4 portrait'] if name=='paper' else list(CN) if name=='font_cn' or name.endswith('_font_cn') else list(WEST) if name=='font_western' else list(ALIGNMENTS) if name.endswith('_alignment') else [1.,1.25,1.5,2.] if name.endswith('line_spacing') else [0,1,2] if name=='first_line_indent' else None
    if choices is not None:
        cols[1].selectbox(label+'值',choices,index=choices.index(value),key=value_key,on_change=value_changed,disabled=mode in ('choose','default'),format_func=lambda val:display_value(name,val))
    else:
        cols[1].number_input(label+'值',min_value=10. if name.startswith('margin_') else 8.,max_value=50. if name.startswith('margin_') else 36. if name.startswith('heading') else 24.,value=float(value),step=.5,key=value_key,on_change=value_changed,disabled=mode in ('choose','default'))
    if f:st.caption('提取：'+display_value(name,f['value'])+' · '+f['location']+'：'+f['quote']+(' · 最终值已编辑为用户确认值' if name in model.template_touched else ''))


def object_configuration(cfg):
    """Compact final comparison; original excerpt/provenance stays in per-field details."""
    values=cfg['final_values'];short={'ai_extracted':'AI提取','user_confirmed':'用户确认','default_inherited':'默认继承','legacy_fixed':'旧版固定'}
    def origin(obj,props):
        return '；'.join({'font_cn':'字体','font_size':'字号','alignment':'对齐','line_spacing':'行距'}[p]+':'+short[cfg['field_sources'][obj+'_'+p]['kind']] for p in props)
    st.dataframe([{'对象':f'{"一二三"[i-1]}级标题','中文字体':values[f'heading{i}_font_cn'],'字号':display_value('font_size',values[f'heading{i}_font_size']),
                   '对齐':ALIGNMENTS[values[f'heading{i}_alignment']],'行距':display_value('line_spacing',values[f'heading{i}_line_spacing']),
                   '字段来源':origin(f'heading{i}',('font_cn','font_size','alignment','line_spacing'))} for i in (1,2,3)],hide_index=True,width='stretch')
    st.dataframe([{'对象':label,'中文字体':values[obj+'_font_cn'],'字号':display_value('font_size',values[obj+'_font_size']),
                   '字段来源':origin(obj,('font_cn','font_size'))} for obj,label in (('figure_caption','图题'),('table_caption','表题'))],hide_index=True,width='stretch')

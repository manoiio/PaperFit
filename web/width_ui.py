import json
import streamlit as st
from .session import public_error
from core.widths import width_markdown

def _rows(report):
    for r in report['objects']:
        yield {'对象':r['key'],'所在节':r['section'],'声明宽度':f"{r['declared_width_mm']:.2f} mm" if 'declared_width_mm' in r else '待确定',
               '可用宽度':f"{r['available_mm']:.2f} mm" if 'available_mm' in r else '待确定','超出':f"{r.get('excess_mm',0):.2f} mm" if 'excess_mm' in r else '待确定',
               '状态':{'risk':'宽度风险','review':'待复核','pass':'尺寸范围内'}[r['status']],'可适配':'是' if r['fixable'] else '否'}

def render_width_panel(model):
    if model.confirmed is None:return
    st.markdown('<span id="width-operations"></span>',unsafe_allow_html=True)
    with st.container(key='width-summary'):
        st.subheader('页面可用宽度 · 独立布局检查')
        st.caption('W01表格 / W02内嵌图片；独立于R01–R12。格式0问题仍可能存在超宽风险。自动宽度是声明风险，不代表Word的最终可见位置。')
        try:targets=model.preview_targets()
        except Exception as e:st.warning(public_error(e));return
        keys=list(targets);latest=keys[-1];seed=f'{model.task_dir.name}-{model.revision}-{model.generation_count}'
        label=lambda k:('原稿' if k=='original' else '当前处理输入' if k=='input' else f"第{targets[k]['round']}轮副本")+' · '+model.display_name
        focus=getattr(model,'focus',None)
        if focus and focus['area']=='width' and focus['target'] in keys:latest=focus['target'];st.session_state['width-source-'+seed]=latest
        key=st.selectbox('宽度检查与适配输入',keys,index=keys.index(latest),format_func=label,key='width-source-'+seed)
        try:report=model.width_report(key)
        except Exception as e:st.warning(public_error(e));return
        st.write(f"布局宽度风险 {report['summary']['risks']} · 待复核对象 {report['summary']['reviews']} · 尺寸范围内 {report['summary']['passes']}")
        if report['objects']:st.dataframe(list(_rows(report)),hide_index=True,width='stretch')
        else:st.info('没有主文档顶层表格或图片对象；未检查页眉页脚及文本框内部尺寸。')
        with st.expander('尺寸依据与确认适配（可选）',key='width-plan',expanded=bool(focus and focus['area']=='width')):
            chosen=[];fixed=[]
            for row in report['objects']:
                st.markdown('**'+row['key']+' · '+{'risk':'宽度风险','review':'待复核','pass':'尺寸范围内'}[row['status']]+'**')
                st.caption(row['reason'])
                b=row['basis']
                if b:st.write(f"节{b['section']}：页面{b['page_width_mm']:.2f}mm − 左边距{b['left_margin_mm']:.2f}mm − 右边距{b['right_margin_mm']:.2f}mm − 装订线{b['gutter_mm']:.2f}mm = 正文区{b['body_width_mm']:.2f}mm"+(f"；对象缩进扣除{row['indent_twips']*25.4/1440:.2f}mm" if row.get('indent_twips') else ''))
                if not row['fixable']:continue
                p=row['plan'];widget=seed+'-'+targets[key]['sha256']+'-'+row['key']
                if row['kind']=='table':
                    st.write(f"表格：{row['declared_width_mm']:.2f} → {row['available_mm']:.2f} mm；{row['rows']}行/{row['columns']}列；不设置固定行高。")
                    st.dataframe([{'列':i,'原mm':round(a*25.4/1440,3),'目标mm':round(c*25.4/1440,3)} for i,(a,c) in enumerate(zip(p['columns_before_twips'],p['columns_after_twips']),1)],hide_index=True,width='stretch')
                    if p['autofit_to_fixed']:
                        agreed=st.checkbox('明确同意 '+row['key']+'：由自动调整改为固定列宽，可能增加文字换行和表格高度',key='width-fixed-'+widget)
                    else:agreed=True
                else:
                    st.write('图片宽×高：'+' × '.join(f'{v/36000:.2f}mm' for v in p['before_emu'])+' → '+' × '.join(f'{v/36000:.2f}mm' for v in p['after_emu'])+'；保持比例，不放大，不改变媒体和裁剪。');agreed=True
                if st.checkbox('确认适配 '+row['key'],disabled=not agreed,key='width-choose-'+widget) and agreed:
                    chosen.append(row['key'])
                    if p['autofit_to_fixed']:fixed.append(row['key'])
            st.warning(report['limitation'])
            if st.button('按确认尺寸生成新副本',disabled=not chosen,key='width-run-'+seed,type='primary'):
                with st.spinner('仅修改所选尺寸定义，保存新一轮副本并读回验证…'):ok=model.generate_width(key,report,chosen,fixed)
                if ok:st.rerun()
            if model.width_error:st.error(model.width_error)
            if model.result is not None:st.download_button('下载当前宽度检查报告',width_markdown(report).encode(),file_name='论文有格_宽度检查.md',on_click='ignore',key='width-report-'+seed+'-'+key)
        if model.result and model.result.get('widths'):
            with st.container(key='width-result'):
                w=model.result['widths'];st.success('本轮所选对象尺寸读回复查通过；可见排版尚需预览。')
                st.write(f"第{model.result['round']['number']}轮输出，输入第{model.result['round']['input_round']}轮；剩余宽度风险{w['after']['summary']['risks']}，待复核{w['after']['summary']['reviews']}。")
                st.dataframe(list(_rows(w['after'])),hide_index=True,width='stretch')
                st.download_button('下载宽度落盘复查',width_markdown(w['after']).encode(),file_name='论文有格_宽度复查.md',on_click='ignore',key='width-after-'+seed)

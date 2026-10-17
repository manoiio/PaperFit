"""Explicit excerpt disclosure, one request, then original smart scope summary."""
import streamlit as st
import json
from .structure_session import prepare,run,merge
from .session import public_error
from ai.short_spec import config_status
from core.classification import TYPES


def render_structure(model,state):
    with st.expander('可选：AI辅助识别结构（发送有限论文摘录）',expanded=False):
        st.write('沿用当前SCUT/已生效格式要求；AI仅协助尚未确认的结构歧义，不重复解析规范。也可以直接使用下方本地范围建议。')
        try:
            prepared=prepare(model)
            count=len(prepared['request']['candidates'])
            st.write(f'待分析 {count} 个歧义候选 · 因保护/人工决定不分析 {len(prepared["protected"])} 个 · 超预算未分析 {prepared["remaining"]} 个')
            st.caption('明确点击下方按钮才发送：候选短文本、有限邻段/章节锚点及样式信息。已尝试隐藏明显姓名、学号、邮箱、电话、路径；不是彻底匿名保证。不上传DOCX、图片或全文。最多40个候选、一次POST、无自动重试。')
            with st.expander('查看实际待发送内容与本地保护原因'):
                st.json(prepared['request'],expanded=False)
                st.dataframe(prepared['protected'],hide_index=True,height=160)
            store=state.setdefault('structure',{})
            config=config_status()
            if not config['configured']:st.info(config['message']+'；可继续本地流程。')
            if st.button('发送上述摘录 · AI辅助分析结构',key='structure-request',disabled=not count or not config['configured']):
                try:
                    with st.spinner('正在批量分析结构；仅本次一次请求…'):
                        result=run(model,prepared,store)
                        state['proposal']=merge(model,prepared,result)
                    st.rerun()
                except Exception as exc:st.warning('AI此次未完成：'+public_error(exc)+'。原本地建议和人工草稿保持，可直接继续。')
            if store.get('status')=='failed':st.caption(f'最近一次尝试未完成；没有自动重试。耗时 {store.get("elapsed_seconds","未知")} 秒。再次发送必须明确点击。')
            result=store.get('result')
            if result:
                r=result['receipt']
                current_valid=result.get('prepared_seal')==prepared['seal']
                origin='模拟测试' if r['kind']=='mock_api' else ('当前有效缓存' if store.get('cache_hit') else '本次真实调用记录') if current_valid else '本会话历史真实调用记录（当前不可采用）'
                st.caption(f'来源：{origin} · 模型 {r["model"]} · 该记录请求 {r["request_count"]} 次 · 请求及校验 {r["elapsed_seconds"]} 秒')
                st.write('服务端token用量：'+str(r.get('usage') or '未知（不以字符估算替代）'))
                st.caption('本次操作新增POST：0（缓存命中）' if store.get('cache_hit') else '本条记录对应1次POST；查看、检查、下载和重运行不增加请求。')
                compact={'format':'paperfit-structure-diagnostic','version':1,'receipt':r,'prepared_seal':result['prepared_seal'],'current':current_valid,'candidate_count':store['candidate_count'],'cache_hit':store.get('cache_hit',False),'suggestions':[{k:x[k] for k in ('id','role','accepted','decision_reason')} for x in result['suggestions']],'note':'诊断导出，不含原始请求摘录，不是可导入的范围授权'}
                st.download_button('导出结构识别回执（不含摘录）',json.dumps(compact,ensure_ascii=False,indent=2).encode(),file_name='structure-receipt.json',on_click='ignore',key='structure-receipt')
                if current_valid:
                    current=merge(model,prepared,result);a=current['structure_ai']
                    st.write(f'本地原纳入 {a["local_included"]} 个 · AI补充纳入 {a["accepted"]} 个 · 本地拒绝/仍待核对 {a["rejected"]} 个 · 未返回 {a["omitted"]} 个')
                    st.dataframe([{'段落':x['id'],'AI前':TYPES[model.paragraph_types[x['id'].split(':')[1]]],'AI建议':TYPES[x['role']],'本地结果':'可供整体接受' if x['accepted'] else '仍待核对','原因':x['decision_reason'],'AI结构理由':x['reason']} for x in a['rows']],hide_index=True,height=180)
                    st.caption('本地接受仅表示协议和保护边界校验通过，不保证语义分类正确；无明确编号的标题层级尤其需要核对。AI结果仅是待接受建议。本页“接受此范围并检查”才产生本轮范围确认；不会自动勾选修正。AI记录只留本会话，不进入项目/报告/日志，已接受的分类按原项目机制保存。')
                else:st.info('此前AI记录的输入、规则、范围或模式已变化，仅作本会话历史，不可用于当前摘要。重新调用需再次明确发送。')
        except Exception as exc:st.warning('AI候选未准备：'+public_error(exc)+'；仍可使用本地建议。')

"""Bounded, escaped presentation of existing records; never changes their meaning."""
from html import escape
import streamlit as st
from .issues import STATUS,locate
from .reading_report import change_value


def compact_stats(items,key):
    cells=''.join('<div><span>'+escape(str(label))+'</span><strong>'+escape(str(value))+'</strong></div>' for label,value in items)
    st.html('<div class="compact-stats" data-panel="'+escape(key,quote=True)+'">'+cells+'</div>')


def comparison(title,before,after,reason='',status='',action='',key=None):
    """All document/model strings are untrusted; no script or raw HTML input."""
    e=lambda v:escape(str(v))
    st.html('<article class="comparison-card"'+(' id="'+e(key)+'"' if key else '')+'><header><b>'+e(title)+'</b><span>'+e(status)+'</span></header><div class="value-pair"><div><small>实际 / 修改前</small><p>'+e(before)+'</p></div><span aria-label="变为">→</span><div><small>要求 / 读回值</small><p>'+e(after)+'</p></div></div>'+('<p class="change-reason">'+e(reason)+'</p>' if reason else '')+('<p><b>处理方式：</b>'+e(action)+'</p>' if action else '')+'</article>')


def render_impact_summary(imp,selected,actual,key):
    c=imp['counts'];s=imp['remaining_summary']
    compact_stats([('所选记录',selected),('实际修改',actual),('未选自然符合',c['natural_resolved']),('新问题',c['new_problem']),('剩余待复核',s['review_count'])],key)
    st.write(f"最终剩余 {s['problem_count']} 个问题、{s['review_count']} 项待复核；转待复核不算已解决。")
    risk=c['new_problem']+c['problem_to_review']+c['unaligned']
    if risk:
        st.warning(f"需核对：新问题 {c['new_problem']} · 问题转待复核 {c['problem_to_review']} · 无法可靠对齐 {c['unaligned']}。不会自动追加修正。")
        rows=[r for r in imp['records'] if r['kind'] in ('new_problem','problem_to_review','unaligned')]
        for r in rows[:2]:
            st.write('**'+r['label']+' · '+locate(r['locator'])+'** · '+r['reason'])
        if len(rows)>2:st.caption(f'另外 {len(rows)-2} 条风险在下方完整影响记录中逐页核对。')


def quick_changes(changes,limit=2):
    for c in changes[:limit]:
        comparison(locate(c['locator']),change_value(c['before'],c['rule_id']),change_value(c['after'],c['rule_id']),
                   status='落盘复查：'+STATUS.get(c['verification'],c['verification']))
    if len(changes)>limit:st.caption(f'另有 {len(changes)-limit} 项修改，完整明细按需展开；采用授权覆盖全部明确选择。')


def view_state(model,view,had,key):
    last='decision-last-'+model.task_dir.name
    if view:
        st.session_state[last]=view['id']
        return '已采用' if model.rehearsal.get('adopted_round') or model.rehearsal.get('adopted_rounds') else '预演成功 · 待采用'
    if had or (st.session_state.get(last) and not model.rehearsal):return '已失效 · 请重新预演'
    return '失败 · 可调整后重试' if model.rehearsal_error else '未预演'


def cancel_view(model):
    model.cancel_rehearsal()
    st.session_state.pop('decision-last-'+model.task_dir.name,None)

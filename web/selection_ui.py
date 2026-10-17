"""One original selected-key list, with bounded reading/removal and explicit batches."""
import streamlit as st
from core.package import sha256
from .issues import field_value
from .presentation import position
from .problem_browser_ui import plain_label,view_radio,attribute_label,display_position
from .report_pages import merge_page_selection,selection_counts


def selection_seed(model):
    return f'{model.task_dir.name}-{model.revision}-{model.report_revision}'


def selection_rows(model):
    eligible={f['key']:f for f in model.eligible()}
    rows=[]
    for k in model.selected:
        f=eligible.get(k)
        rows.append({'key':k,'位置':display_position({'position':position(f['locator']),'locator':f['locator']}) if f else '当前记录不可用',
                     '属性':attribute_label({'title':f['rule_id']+' '+f['rule_name'],'locator':f['locator']}) if f else '请重新检查',
                     '实际':field_value(f['actual'],f['rule_id'],f['locator']) if f else '—',
                     '要求':field_value(f['expected'],f['rule_id'],f['locator'],True) if f else '—'})
    return rows


def render_selected_list(model):
    rows=selection_rows(model);seed=selection_seed(model)
    with st.popover(f'已选 {len(rows)} 项 · 查看清单',width='stretch',key='selected-popover-'+seed):
        st.write(f'完整已选清单 · 共{len(rows)}项（当前处理输入）')
        st.caption('包含其他页和筛选外选择；查看不改变选择或筛选。预演会执行全部已选项。')
        if not rows:
            st.info('尚未选择修正。先查看对象和属性，再点击“加入修正”。');return
        page_key='selected-list-page-'+seed;pages=max(1,(len(rows)+7)//8)
        st.session_state[page_key]=min(max(st.session_state.get(page_key,1),1),pages)
        page=int(st.number_input('已选清单页码',min_value=1,max_value=pages,key=page_key))
        visible=rows[(page-1)*8:page*8];lookup={r['key']:r for r in visible}
        st.caption(f'第{page}/{pages}页 · 项{(page-1)*8+1}–{min(page*8,len(rows))}；每页8项')
        with st.container(height=255,border=True):
            chosen=view_radio('查看已选属性',list(lookup),'selected-list-item-'+seed+'-'+str(page),
                format_func=lambda k:plain_label(lookup[k]['位置']+' · '+lookup[k]['属性']),
                captions=[plain_label(r['实际']+' → '+r['要求']) for r in visible])
        st.caption('移除或清空将按原机制使相关预演/当前结果失效；不会修改文档。')
        st.button('移除此项选择',key='selected-remove-'+seed,on_click=lambda k=chosen:model.set_selection([x for x in model.selected if x!=k]),width='stretch')
        st.button('清空全部选择',key='selected-clear-'+seed,on_click=lambda:model.set_selection([]),width='stretch')


def render_selection_tools(model):
    eligible=model.eligible()
    if eligible and model.operation=='format':
        with st.container(key='selection'):
            st.subheader('批量选择修正')
            lookup={f['key']:f for f in eligible};view=model.center_selection_view
            same_input=bool(view and view.get('file_sha256')==model.report['input_sha256'])
            visible=[k for k in view['page_keys'] if k in lookup] if same_input else []
            filtered=[k for k in view['filtered_keys'] if k in lookup] if same_input else []
            if not same_input:st.info('当前查看输出副本，只读。已选清单仍属于当前处理输入；须明确继续后才能选择输出中的问题。')
            a,b,c=st.columns(3)
            a.button('选择本页可修正项',key='batch-page-'+selection_seed(model),on_click=lambda:model.set_selection(model.selected+visible),disabled=not same_input or not visible,width='stretch');a.caption(f'本页 {len(visible)} 项')
            b.button('选择当前筛选的可修正项',key='select-filter-action-'+selection_seed(model),on_click=lambda:model.set_selection(model.selected+filtered),disabled=not same_input or not filtered,width='stretch');b.caption(f'当前筛选全部页 {len(filtered)} 项')
            c.button('选择全部可修正问题',key='batch-all-'+selection_seed(model),on_click=lambda:model.set_selection(list(lookup)),disabled=not same_input,width='stretch');c.caption(f'当前输入全部 {len(lookup)} 项，含筛选外')
            st.button('清空全部选择',key='selection-clear-body',on_click=lambda:model.set_selection([]),disabled=not model.selected)
            if view:
                counts=selection_counts(model.selected,view)
                st.caption(f"本页已选 {counts['page'] if same_input else 0} · 全部已选 {counts['all']} · 当前筛选外仍保留 {counts['outside_filter'] if same_input else counts['all']}")
            warnings=[w['detail'] for w in model.report.get('modification_dependencies',[]) if set(w['trigger_keys'])&set(model.selected)]
            warnings += [f['dependency_note'] for f in eligible if f['key'] in model.selected and f.get('dependency_note')]
            if warnings:
                st.warning(f"关联提示 {len(warnings)} 项："+'；'.join(warnings[:3]))
                if st.toggle('查看全部关联提示'):st.dataframe([{'提示':w} for w in warnings],hide_index=True,width='stretch')
            with st.expander('高级：旧版逐项选择与原始清单'):
                legacy=visible[:100];key='selection-'+seed_key(model,legacy)
                st.session_state[key]=[k for k in model.selected if k in legacy]
                def label(k):
                    f=lookup[k]
                    return f"{f['rule_id']} · {position(f['locator'])} · {f['rule_name']}：{field_value(f['actual'],f['rule_id'],f['locator'])} → {field_value(f['expected'],f['rule_id'],f['locator'],True)}"
                st.multiselect('逐项选择修正',options=legacy,format_func=label,key=key,disabled=not same_input,
                    on_change=lambda:model.set_selection(merge_page_selection(model.selected,legacy,st.session_state.get(key,[]))))
                if len(visible)>100:st.caption('兼容列表仅本页前100项；其他属性可在对象详情按页选择，批量操作仍覆盖其标明的全部范围。')
                st.button('清空选择',on_click=lambda:model.set_selection([]))
                if st.toggle('查看完整执行清单（含key）',key='selected-raw-'+selection_seed(model)):
                    st.dataframe(selection_rows(model),hide_index=True,width='stretch',height=240)
    elif not eligible:st.info('当前没有可自动修正项；待复核仍须人工核对。')


def seed_key(model,visible):
    return selection_seed(model)+'-'+sha256(str(visible).encode())[:12]

"""Bounded display helpers. IDs identify views; only original model methods select."""
from collections import Counter,defaultdict
import re
import streamlit as st
from .issues import STATUS


def plain_label(value):
    # Native labels support Markdown: document strings must remain literal text.
    return re.sub(r'([\\`*_{}\[\]()#+.!|<>~])',r'\\\1',str(value))


def full_groups(records):
    groups=defaultdict(list)
    for record in records:groups[record['object']].append(record)
    return groups


def status_counts(records):
    counts=Counter(r['status'] for r in records)
    return ' · '.join(STATUS[k]+str(counts[k]) for k in STATUS if counts[k])


def position_label(records):
    return records[0]['position'].split(' · ')[0]


PROPERTY_NAMES={'font_cn':'中文字体','font_western':'西文字体','font_size':'字号','size':'字号','font_eastAsia':'中文字体','font_ascii':'西文/数字字体','font_hAnsi':'扩展西文字体','alignment':'对齐','line':'行距','line_multiple':'倍数行距','line_spacing':'行距','before':'段前间距','after':'段后间距','first_line_indent':'首行缩进','bold':'加粗','header_distance_mm':'页眉距离','footer_distance_mm':'页脚距离'}

def attribute_label(record):
    title=record['title'].split(' ',1)[-1]
    prop=PROPERTY_NAMES.get(record['locator'].get('property'))
    return title+(' · '+prop if prop and prop not in title else '')

def display_position(record):
    text=record['position'];prop=record['locator'].get('property')
    if prop in PROPERTY_NAMES and text.endswith(' · '+prop):text=text[:-len(prop)]+PROPERTY_NAMES[prop]
    return text


def view_radio(label, options, key, **kwargs):
    """A hidden/removed ID cannot leave stale detail after a filter or snapshot change."""
    if st.session_state.get(key) not in options:st.session_state[key]=options[0]
    return st.radio(label,options,key=key,**kwargs)


def object_browser(view, groups, selected, seed, same_input):
    chosen_keys=set(selected) if same_input else set()
    def caption(obj):
        records=groups[obj]
        excerpt=next((r['excerpt'] for r in records if r['excerpt']),None)
        description=excerpt or ('页面与页边距设置' if obj.startswith('section:') else '无普通段落文字；请查看对象记录')
        return plain_label(status_counts(records)+'\n'+(description[:30]+'…' if len(description)>30 else description))
    def label(obj):
        count=sum(r['record_key'] in chosen_keys for r in groups[obj])
        return plain_label(position_label(groups[obj])+(f' · 已选{count}项' if count else ''))
    with st.container(height=390,border=True,key='object-browser'):
        chosen=view_radio('本页对象（点击仅查看）',view['objects'],'center-object-'+seed,format_func=label,captions=[caption(o) for o in view['objects']],width='stretch')
    st.caption('每页最多20个对象；统计该对象的全部记录，含筛选隐藏的状态。查看不选择修正。')
    return chosen


def record_browser(detail, matches, seed):
    # The global state filter exposes pass/not-applicable records without a second filter.
    rows=matches
    page_key='center-record-page-'+seed
    pages=max(1,(len(rows)+3)//4)
    st.session_state[page_key]=min(max(st.session_state.get(page_key,1),1),pages)
    if pages>1:
        page=int(st.number_input('检查项页码',min_value=1,max_value=pages,key=page_key,help='每页4条检查项；不改变修正选择。'))
    else:page=1
    visible=rows[(page-1)*4:page*4]
    if len(rows)>4:st.caption(f'检查项{(page-1)*4+1}–{min(page*4,len(rows))} / {len(rows)}；完整原始记录仍可展开。')
    by_id={r['id']:r for r in visible}
    def label(key):
        r=by_id[key];tail=' · '.join(display_position(r).split(' · ')[1:])
        return plain_label(attribute_label(r)+(' · '+tail if tail else '')+' · '+STATUS[r['status']])
    chosen=view_radio('查看检查项（不勾选修正）',list(by_id),'center-record-'+seed+'-'+str(page),format_func=label,horizontal=True,width='stretch',label_visibility='collapsed')
    return by_id[chosen]

"""纯展示分页；原始记录不裁切，不改变引擎或选择授权。"""
from collections import OrderedDict
from math import ceil
from .issues import filter_records
from core.package import DemoError

def object_order(obj):
    kind,_,number=obj.partition(':')
    return ({'section':0,'paragraph':1,'table':2,'document':3}.get(kind,4),int(number) if number.isdigit() else 0)

def object_page(records,*,categories=(),statuses=(),objects=(),keyword='',paragraph_range='',page=1,page_size=20,descending=False):
    if type(page_size) is not int or not 1<=page_size<=50:raise DemoError('展示页大小必须为1–50个对象')
    rows=filter_records(records,categories,objects,statuses)
    if paragraph_range.strip():
        import re
        match=re.fullmatch(r'\s*(\d+)\s*(?:-\s*(\d+)\s*)?',paragraph_range)
        if not match:raise DemoError('段落编号筛选请用8或8-20')
        low=int(match[1]);high=int(match[2] or match[1])
        if low<1 or high<low:raise DemoError('段落编号范围无效')
        rows=[r for r in rows if low<=r['locator'].get('paragraph',-1)<=high]
    if keyword.strip():
        needle=keyword.strip().casefold()
        rows=[r for r in rows if needle in ' '.join(str(r.get(k,'')) for k in ('title','position','excerpt','actual','expected','reason','basis')).casefold()]
    groups=OrderedDict()
    for r in rows:groups.setdefault(r['object'],[]).append(r)
    keys=sorted(groups,key=object_order,reverse=descending);pages=max(1,ceil(len(keys)/page_size));page=min(pages,max(1,int(page)))
    visible=keys[(page-1)*page_size:page*page_size]
    def fixable(rs):return [r['record_key'] for r in rs if r['category']=='format' and r['status']=='problem' and r['raw'].get('fixable') is True]
    return {'records':rows,'record_count':len(rows),'object_count':len(keys),'pages':pages,'page':page,
            'start':(page-1)*page_size+1 if keys else 0,'end':min(page*page_size,len(keys)),
            'objects':visible,'groups':{k:groups[k] for k in visible},
            'page_keys':fixable([r for k in visible for r in groups[k]]),'filtered_keys':fixable(rows)}

def merge_page_selection(selected,visible_keys,new_keys):
    return sorted((set(selected)-set(visible_keys))|(set(new_keys)&set(visible_keys)))

def selection_counts(selected,view):
    chosen=set(selected)
    return {'page':len(chosen&set(view['page_keys'])),'all':len(chosen),'outside_filter':len(chosen-set(view['filtered_keys']))}

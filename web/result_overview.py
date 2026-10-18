"""Read-only grouping of existing final records. Counts are records, not defects."""
from collections import OrderedDict

def attention(report):
    groups=OrderedDict((label,[]) for label in ('需要人工判断的内容','不支持或受保护的复杂结构','仍可处理的格式问题','字体与渲染差异'))
    records=[dict(f,record_kind='检查记录') for f in report.get('findings',[]) if f.get('status') in ('problem','review')]
    records += [dict(n,record_kind='覆盖提示') if isinstance(n,dict) else {'detail':str(n),'record_kind':'覆盖提示'} for n in report.get('coverage_notes',[])]
    for row in records:
        text=str(row.get('detail',''))+' '+str(row.get('reason',''))
        if row.get('status')=='problem' and row.get('fixable'):label='仍可处理的格式问题'
        elif any(x in text for x in ('字体替代','字体缺失','渲染器','字体未安装')):label='字体与渲染差异'
        elif any(x in text for x in ('不支持','复杂','保护','域','修订','未知结构')):label='不支持或受保护的复杂结构'
        else:label='需要人工判断的内容'
        groups[label].append(row)
    return groups

def changes_summary(model):
    if not model.result:return '本次没有额外生成修改副本。'
    assembly=model.result.get('assembly')
    if assembly:
        labels={'format':'普通格式','dynamic_text':'编号与文本引用','section_pages':'分区页码','caption_position':'题注位置','width_adaptation':'图表宽度','pagination_layout':'相邻与表头','field_update':'目录与引用'}
        counts=OrderedDict()
        for step in assembly['steps']:
            key=labels.get(step['kind'],step['kind']);counts[key]=counts.get(key,0)+step['changes']
        return '；'.join(k+' '+str(v)+'项' for k,v in counts.items())+'。不同操作不相加为解决问题数。'
    return '本轮记录 '+str(len(model.result.get('changes',[])))+' 项修改；详细前后值见报告。'

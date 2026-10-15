"""Known two-step dependency only; original formatting transactions stay unchanged."""
from copy import deepcopy
from .package import Package,DemoError,sha256,NS
from .citations import inventory,text,validate_scope

VERSION='known-format-citation-plan-v1'

def draft(report,selected,pkg,classification):
    by={f['key']:f for f in report['findings']};items=[];blocked=[]
    for key in selected:
        f=by.get(key)
        if not f or f['status']!='problem' or not f['fixable'] or not f['rule_id'].startswith('R'):
            blocked.append({'key':key,'reason':'不是当前报告中可安全修正的格式问题，不进入计划'})
        else:items.append(f)
    ordinary=[f for f in items if f['rule_id']!='R33'];citations=[f for f in items if f['rule_id']=='R33']
    paragraphs={f['locator']['paragraph'] for f in citations}
    # Match the EXISTING engine's conservative conflict predicate exactly.
    conflicts=[f for f in ordinary if 'run' in f['locator'] and f['locator'].get('paragraph') in paragraphs]
    two=bool(conflicts and citations);targets=[]
    if two:
        try:
            if not classification or not classification.get('citation_scope'):raise DemoError('引文范围尚未确认')
            scope=validate_scope(pkg,classification['citation_scope'],classification)
            rows=inventory(pkg,scope['scan'])['objects']
            for f in citations:
                loc=f['locator'];matches=[r for r in rows if (r['paragraph'],r['start'],r['end'])==(loc['paragraph'],loc['start'],loc['end'])]
                if len(matches)!=1 or not matches[0]['fixable'] or scope['objects'].get(matches[0]['id'])!='citation':raise DemoError('所选引文不在已确认安全范围中')
                row=matches[0]
                targets.append({'origin_key':f['key'],'paragraph':loc['paragraph'],'start':loc['start'],'end':loc['end'],'text':row['text'],
                                'paragraph_sha256':sha256(text(pkg.paragraphs[loc['paragraph']-1]).encode())})
        except DemoError as exc:blocked.append({'key':'R33','reason':str(exc)})
    groups=[ordinary,citations] if two else [items]
    return {'version':VERSION,'two_steps':two,'selected_count':len(selected),'selected_keys':list(selected),
            'steps':[{'number':i,'keys':[f['key'] for f in fs],'items':[{'key':f['key'],'rule_id':f['rule_id'],'locator':deepcopy(f['locator']),'actual':deepcopy(f['actual']),'expected':deepcopy(f['expected']),'source':deepcopy(f['source'])} for f in fs],
                      'input':'当前处理输入' if i==1 else '第1步实际落盘副本（计划内部输入，不切换网页当前输入）'} for i,fs in enumerate(groups,1)],
            'targets':targets,'blocked':blocked,'expected_rounds_max':2 if two else 1,
            'reason':'同段普通run格式与R33拆分受原事务分轮保护；先普通格式，再重新定位并上标。' if two else '没有跨步依赖，复用原单轮预演。',
            'limits':['只处理明确选择，不加入新缩进或其他问题。','第2步已符合则不写属性、不凑正式轮次；不安全或无法定位则阻止整计划采用。','宽度、分页、L05和编号更新不参与计划。']}

def handoff(original,intermediate,scope):
    """Only an index-preserving ordinary-format transaction may carry scopes."""
    if len(original.paragraphs)!=len(intermediate.paragraphs) or any(text(a)!=text(b) for a,b in zip(original.paragraphs,intermediate.paragraphs)):
        raise DemoError('普通格式事务后段落身份或文字变化，不能继承计划范围')
    from .classification import validate_classification
    validate_classification(intermediate,scope)
    return deepcopy(scope)

def resolve_targets(pkg,classification,targets,report):
    """No old key/run reuse or text search; exact identity+offset+content proof."""
    scope=validate_scope(pkg,classification['citation_scope'],classification)
    rows=inventory(pkg,scope['scan'])['objects'];out=[]
    for t in targets:
        n=t['paragraph']
        if not 1<=n<=len(pkg.paragraphs) or sha256(text(pkg.paragraphs[n-1]).encode())!=t['paragraph_sha256']:
            raise DemoError('引文所在段落身份/文字不再对应，停止计划')
        matches=[r for r in rows if (r['paragraph'],r['start'],r['end'])==(n,t['start'],t['end'])]
        if len(matches)!=1:raise DemoError('引文准确字符范围不能唯一定位，停止计划')
        r=matches[0]
        if r['text']!=t['text'] or scope['objects'].get(r['id'])!='citation' or not r['safe_structure']:
            raise DemoError('引文文字、用途或安全结构变化，停止计划')
        fs=[f for f in report['findings'] if f['rule_id']=='R33' and (f['locator'].get('paragraph'),f['locator'].get('start'),f['locator'].get('end'))==(n,t['start'],t['end'])]
        if len(fs)!=1:raise DemoError('新检查没有唯一引文格式记录，停止计划')
        f=fs[0]
        if f['status']=='pass':state='无需修改'
        elif f['status']=='problem' and f['fixable']:state='待修正'
        else:raise DemoError('所选引文变为待复核或不可安全修正，停止计划')
        out.append({**deepcopy(t),'new_key':f['key'],'status':state,'evidence':'段落文字哈希、准确字符范围、原引文文字、确认用途及实际新检查均对应'})
    return out

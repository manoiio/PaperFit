"""可预测依赖与同规则读回后的问题变化；不自动追加未选修正。"""
def annotate_dependencies(report):
    fs=report['findings'];warnings=[]
    for indent in fs:
        if indent['rule_id']!='R07' or not isinstance(indent['actual'],dict):continue
        a=indent['actual'];pt=a.get('first_line_pt')
        if pt in (None,0):continue
        sizes=[f for f in fs if f['rule_id']=='R05' and f['status']=='problem' and f['locator'].get('paragraph')==indent['locator'].get('paragraph')]
        if not sizes:continue
        wanted=sizes[0]['expected']
        chars=indent['expected']
        label='两字符' if chars==2 else f'{chars:g}字符'
        detail=f'可能影响首行缩进：字号改为{wanted:g}pt后，现有{pt:g}pt点值缩进应重新核对；{label}等效点值为{wanted*chars:g}pt。未选R07不会自动修改。'
        item={'affected_key':indent['key'],'trigger_keys':[f['key'] for f in sizes],'locator':indent['locator'],'detail':detail}
        warnings.append(item)
        for f in sizes:f['dependencies']=[detail]
    for indent in fs:
        a=indent.get('actual');loc=indent['locator']
        if loc.get('property')!='first_line_indent' or not isinstance(a,dict) or a.get('pt') in (None,0):continue
        sizes=[f for f in fs if f['rule_id']==indent['rule_id'] and f['status']=='problem' and f['locator'].get('paragraph')==loc.get('paragraph') and f['locator'].get('property')=='size']
        if not sizes:continue
        chars=indent['expected']['chars'];wanted=sizes[0]['expected'];pt=a['pt']
        detail=f'可能影响首行缩进：本对象字号改为{wanted:g}pt后，{pt:g}pt缩进须复核；{chars:g}字符等效{wanted*chars:g}pt。不自动追加未选缩进。'
        warnings.append({'affected_key':indent['key'],'trigger_keys':[f['key'] for f in sizes],'locator':loc,'detail':detail})
        for f in sizes:f['dependencies']=[detail]
    report['modification_dependencies']=warnings
    report['summary']['applicable_rule_count']=len({f['rule_id'] for f in fs if f['status']!='not_applicable'})

def problem_delta(before,after):
    old={f['key']:f for f in before['findings'] if f['status']=='problem'}
    new={f['key']:f for f in after['findings'] if f['status']=='problem'}
    after_by_key={f['key']:f for f in after['findings']}
    causes=[]
    for key in new.keys()-old.keys():
        f=new[key]
        if f['rule_id']=='R07' and isinstance(f['actual'],dict):
            a=f['actual'];pt=a.get('first_line_pt');size=a.get('uniform_size_pt')
            previous=next((x for x in before['findings'] if x['key']==key),None)
            prior=previous['actual'].get('uniform_size_pt') if previous and isinstance(previous['actual'],dict) else None
            if pt is not None and size is not None and prior!=size:
                chars=f['expected'];label='两字符' if chars==2 else f'{chars:g}字符'
                cause=f'字号改为{size:g}pt后，{pt:g}pt缩进不再等效{label}（应为{size*chars:g}pt）；本轮未选择该缩进。'
            else:cause='其他所选格式变化后发现该问题，请核对实际值；本轮未自动追加修正。'
        elif f['locator'].get('property')=='first_line_indent' and isinstance(f['actual'],dict) and f['actual'].get('pt') is not None:
            pt=f['actual']['pt'];chars=f['expected']['chars'];cause=f'字号变化后，{pt:g}pt点值缩进与本对象要求的{chars:g}字符不再等效；未自动追加该缩进，需下一轮明确选择。'
        else:cause='修正后的同规则读回发现新问题，请核对实际值。'
        f['change_origin']='new';f['detail']=(f['detail']+'；' if f['detail'] else '')+cause
        causes.append({'key':key,'locator':f['locator'],'detail':cause})
    return {'resolved_keys':sorted(k for k in old if after_by_key.get(k,{}).get('status')=='pass'),
            'unresolved_review_keys':sorted(k for k in old if after_by_key.get(k,{}).get('status')=='review'),
            'not_applicable_keys':sorted(k for k in old if after_by_key.get(k,{}).get('status')=='not_applicable'),
            'remaining_keys':sorted(old.keys()&new.keys()),
            'new_keys':sorted(new.keys()-old.keys()),'new_problem_causes':causes}

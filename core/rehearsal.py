"""Read-only reconciliation and revalidation of an existing engine transaction.

No simulated formatting, no write path, no AI or renderer. Unknown record
alignment remains explicit rather than turning a vanished key into a pass.
"""
from copy import deepcopy
from collections import defaultdict
from pathlib import Path
from lxml import etree as ET
from .package import Package, DemoError, sha256, q, NS, parse

LABELS={'selected_resolved':'所选问题已解决','natural_resolved':'未选问题自然符合',
        'new_problem':'新出现的问题','problem_to_review':'问题转为待复核（未解决）',
        'review_to_determined':'待复核变为可判断','remaining_selected':'所选问题仍存在',
        'remaining_unselected':'仍存在的未选问题','remaining_review':'仍待复核的记录','unaligned':'无法可靠对齐的变化',
        'not_applicable':'问题转为不适用（不计解决）'}

def _identity(f, unstable):
    loc=f['locator']
    if 'run' in loc and loc.get('paragraph') in unstable and not any(k in loc for k in ('table','note_id','story')) and not f.get('story_part'):
        return None
    import json
    return (f['rule_id'],f.get('property'),f.get('object_type'),f.get('story_part'),json.dumps(loc,sort_keys=True,ensure_ascii=False))

def reconcile(result, original, output):
    """Exact locator + attribute only where ordinary-run partitions are unchanged."""
    before,after=result['before'],result['after'];selected={c['key'] for c in result['changes']}
    unstable={i for i,(a,b) in enumerate(zip(original.paragraphs,output.paragraphs),1)
              if len(a.findall(q('r')))!=len(b.findall(q('r')))}
    old=defaultdict(list);new=defaultdict(list);unknown=[]
    for side,fs,bucket in [('before',before['findings'],old),('after',after['findings'],new)]:
        for f in fs:
            ident=_identity(f,unstable)
            if ident is None:
                if f['status'] in ('problem','review'):unknown.append((side,f))
            else:bucket[ident].append(f)
    rows=[]
    def add(kind,a,b,reason=''):
        f=b or a
        if kind=='natural_resolved' and f['rule_id']=='R07' and isinstance(f['actual'],dict):
            v=f['actual'];reason=f"字号变化后，原{v.get('first_line_pt')}pt缩进重新等效{f['expected']}字符（读回字号{v.get('uniform_size_pt')}pt）；未修改缩进。"
        rows.append({'kind':kind,'label':LABELS[kind],'rule_id':f['rule_id'],'locator':deepcopy(f['locator']),
                     'before_key':a['key'] if a else None,'after_key':b['key'] if b else None,
                     'before_status':a['status'] if a else '无可对齐记录','after_status':b['status'] if b else '无可对齐记录',
                     'before':deepcopy(a['actual']) if a else None,'after':deepcopy(b['actual']) if b else None,
                     'expected':deepcopy(f['expected']),'selected':bool(a and a['key'] in selected),
                     'reason':reason or f.get('detail',''),'source':deepcopy(f['source'])})
    for ident in dict.fromkeys([*old,*new]):
        aa,bb=old.get(ident,[]),new.get(ident,[])
        if len(aa)>1 or len(bb)>1:
            for f in aa+bb:
                if f['status'] in ('problem','review'):add('unaligned',f if f in aa else None,f if f in bb else None,'相同定位存在多个记录，不以key消失判断解决。')
            continue
        a=aa[0] if aa else None;b=bb[0] if bb else None
        if a is None or b is None:
            if (a or b)['status'] in ('problem','review'):add('unaligned',a,b,'该对象属性没有唯一前后对应，记录保留，不计为解决。')
            continue
        x,y=a['status'],b['status']
        if x=='problem':
            if y=='pass':add('selected_resolved' if a['key'] in selected else 'natural_resolved',a,b,'所选属性经落盘读回符合。' if a['key'] in selected else '本项未修改；其他所选属性变化后，实际读回自然符合。')
            elif y=='review':add('problem_to_review',a,b)
            elif y=='problem':add('remaining_selected' if a['key'] in selected else 'remaining_unselected',a,b)
            else:add('not_applicable',a,b)
        elif x=='review' and y in ('pass','problem','not_applicable'):add('review_to_determined',a,b)
        elif x=='review' and y=='review':add('remaining_review',a,b)
        elif x!='problem' and y=='problem':add('new_problem',a,b)
    for side,f in unknown:add('unaligned',f if side=='before' else None,f if side=='after' else None,'普通run分区发生变化；保留原记录，未仅按run编号或消失的key推断通过。')
    # XML attributes are counted separately from findings. For split paragraphs,
    # there is no meaningful one-to-one XML attribute count; show that boundary.
    edits=[];split=bool(unstable)
    for name,data in original.parts.items():
        if data==output.parts[name] or not name.endswith('.xml'):continue
        a,b=parse(data),parse(output.parts[name])
        def attrs(root):return {(root.getroottree().getpath(e),k):v for e in root.iter() for k,v in e.attrib.items()}
        ax,bx=attrs(a),attrs(b)
        if not split:
            for path,key in dict.fromkeys([*ax,*bx]):
                if ax.get((path,key))!=bx.get((path,key)):
                    edits.append({'part':name,'xml_object':path,'attribute':ET.QName(key).localname,'before':ax.get((path,key)),'after':bx.get((path,key))})
    old_notes=before.get('coverage_notes',[]);new_notes=after.get('coverage_notes',[])
    added_notes=[deepcopy(n) for n in new_notes if n not in old_notes]
    removed_notes=[deepcopy(n) for n in old_notes if n not in new_notes]
    return {'coverage_changes':{'before_count':len(old_notes),'after_count':len(new_notes),'added':added_notes,'removed':removed_notes,'reason':'新增覆盖提示不算通过；引文上标/必要run拆分可使普通正文检查增加特殊片段提示。'},'version':1,'alignment':'实际对象定位及属性；run分区变化时不推断普通run记录对应',
            'counts':{k:sum(r['kind']==k for r in rows) for k in LABELS},'records':rows,
            'selected_record_count':len(selected),'change_record_count':len(result['changes']),
            'xml_attribute_change_count':None if split else len(edits),'xml_attribute_changes':edits,
            'attribute_count_note':'存在必要run拆分，不提供误导的一对一XML属性数量；实际修改以引文字符范围及事务白名单为准。' if split else 'XML属性变动数独立计数，包含有效格式保留所需属性；不等于问题记录变化数。',
            'selected_outcomes':[{'key':c['key'],'locator':deepcopy(c['locator']),'status':'已修正' if c['verification']=='pass' else '未通过','verification':c['verification']} for c in result['changes']],
            'remaining_summary':deepcopy(after['summary']),'coverage_notes':deepcopy(after.get('coverage_notes',[])),
            'limits':['预演是实际格式事务及读回复查；不是视觉、目录页码或Word兼容验收。','未选属性不自动修改；新增问题须另行选择进入下一轮。']}

def validate_existing_result(input_path, result, body, *, selected_keys, **args):
    """Re-run the ORIGINAL guards and checker without applying any formatting."""
    from .engine import _preservation, check_document
    from .table_text import rebind
    from .dependencies import problem_delta
    original=Package(input_path);saved=Package(result['output'])
    if original.hash!=result['before']['input_sha256'] or saved.hash!=result['output_body_manifest']['input_sha256']:
        raise DemoError('预演输入或副本哈希不匹配，拒绝采用')
    before=check_document(input_path,body,**args)
    if before!=result['before']:raise DemoError('预演前检查记录与当前实际检查不匹配')
    keys=set(selected_keys);findings=[f for f in before['findings'] if f['key'] in keys]
    if len(findings)!=len(keys) or any(f['status']!='problem' or not f['fixable'] for f in findings):raise DemoError('所选问题已失效')
    if {c['key'] for c in result['changes']}!=keys:raise DemoError('预演实际修改与明确选择不一致')
    if set(original.parts)!=set(saved.parts):raise DemoError('预演包成员发生变化')
    allowed={f['story_part'] for f in findings if f.get('story_part')}
    if any(saved.parts[n]!=v for n,v in original.parts.items() if n!='word/document.xml' and n not in allowed):raise DemoError('预演未选部件发生变化')
    if _preservation(original,findings)!=_preservation(saved,findings):raise DemoError('预演超出原格式事务白名单')
    if findings and all(f.get('story_part') for f in findings) and original.parts['word/document.xml']!=saved.parts['word/document.xml']:
        raise DemoError('独立故事修正时主文档必须字节保持')
    if any(f['rule_id']=='R33' for f in findings):
        from .citations import partition_guard
        partition_guard(original,saved,findings)
    out_body=deepcopy(body);out_body['input_sha256']=saved.hash
    expected_classification=deepcopy(args.get('classification_manifest'))
    out_args={**args}
    if expected_classification is not None:
        expected_classification['input_sha256']=saved.hash;rebind(expected_classification,saved.hash)
        if expected_classification!=result.get('output_classification_manifest'):raise DemoError('预演范围重绑不一致')
        out_args['classification_manifest']=expected_classification
    after=check_document(result['output'],out_body,**out_args);problem_delta(before,after)
    if after!=result['after']:raise DemoError('预演复查报告与落盘副本不一致')
    if any(next((f['status'] for f in after['findings'] if f['key']==c['key']),None)!='pass' for c in result['changes']):raise DemoError('所选项读回复查未通过')
    if sha256(Path(input_path).read_bytes())!=original.hash or sha256(Path(result['output']).read_bytes())!=saved.hash:raise DemoError('验证期间文件发生变化')
    return {'input_sha256':original.hash,'output_sha256':saved.hash,'white_list_revalidated':True,'readback_rechecked':True,
            'unselected_parts_byte_equal':True,'verification':'重新执行原完整性白名单及真实落盘检查；未再次修正'}

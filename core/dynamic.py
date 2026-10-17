"""Explicit opt-in text-number transaction. Never evaluates fields or starts Office.

Only exact pre-recorded w:t spans can change. Ordinary format preservation is
untouched; this independent verifier reconstructs the complete expected tree.
"""
from copy import deepcopy
from collections import Counter,defaultdict
from pathlib import Path
import re,json,sys
from lxml import etree as E
from .package import Package,DemoError,NS,q,sha256,write_new,new_path,parse
from .classification import validate_classification
from .captions import chapter_number,parse_caption,boundary_reason
from .layout import _ordinary_reason
from .table_text import rebind

VERSION='dynamic-text-v1'
NUMBER=re.compile(r'([图表])\s*([1-9][0-9]{0,2})-([1-9][0-9]{0,3})(?![0-9A-Za-z-])')
SOURCE={'label':'用户授权的产品动态处理','quote':'按已确认章节及完整题注范围连续编号；唯一纯文本引用同步，不是新增学校格式规定。'}
LIMITS=['只在本次明确完整的已确认题注范围内按章分别编图、表；不更新SEQ或其他域。',
        '纯文本引用仅限已确认正文；代码/数据、链接/域、注释和其他容器不自动改写。',
        'REF/PAGEREF、分页及目录页码尚未完成；必须在Word中更新并复核。',
        '不新建目录，不写updateFields，不以保存缓存或F9提示冒充实际页码。']

def digest(v):return sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
def text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=NS))
def word_capability():
    return {'available':False,'platform':sys.platform,'status':'not_run',
            'reason':'当前非Windows，无Word COM；未更新域、重新分页或核验目录页码。' if sys.platform!='win32' else 'Word COM动态适配尚未实机验收，本版不启用；请在Word更新并复核。'}

def safe_reason(pkg,p):
    reason=_ordinary_reason(pkg,p)
    if reason:return reason
    if any(c.tag not in (q('pPr'),q('r')) for c in p) or any(c.tag not in (q('rPr'),q('t')) for r in p.findall(q('r')) for c in r):return '只支持直属普通文字，不能跨制表符/换行/未知边界'
    return boundary_reason(pkg,p,p)

def spans(p,start,end,replacement):
    nodes=p.xpath('./w:r/w:t',namespaces=NS);offset=0;out=[];covered=0
    for i,node in enumerate(nodes):
        value=node.text or '';a=max(start,offset);b=min(end,offset+len(value))
        if a<b:
            out.append({'text_node':i,'start':a-offset,'end':b-offset,'before':value[a-offset:b-offset],
                        'after':replacement if not out else ''});covered+=b-a
        offset+=len(value)
    if covered!=end-start or not out:raise DemoError('编号范围不能精确映射到普通文字节点')
    return out

def propose(input_path,classification,*,complete=False,automatic=False):
    pkg=Package(input_path);m=validate_classification(pkg,classification)
    if complete is not True and automatic is not True:raise DemoError('连续编号须明确确认本次相关章节题注范围完整；部分范围不能猜序列')
    groups=defaultdict(list);blocked=[];heads=[];old=Counter();rows=[]
    for ns,typ in sorted(m['paragraph_types'].items(),key=lambda x:int(x[0])):
        n=int(ns);p=pkg.paragraphs[n-1]
        if typ=='heading1':
            num,reason,_=chapter_number(pkg,n)
            if ns in m.get('caption_scope',{}).get('chapter_map',{}):num=m['caption_scope']['chapter_map'][ns];reason='用户已明确确认的章号映射'
            heads.append((n,num,reason))
        if typ not in ('figure_caption','table_caption'):continue
        h=heads[-1] if heads else (None,None,'无明确前置一级标题');tx=text(p);parsed=parse_caption(tx)
        group=(h[0],typ);key=(parsed['type'],parsed['chapter'],parsed['sequence']) if parsed else None
        r={'paragraph':n,'group':group,'chapter':h[1],'chapter_evidence':h[2],'parsed':parsed,'key':key,'text':tx}
        rows.append(r);groups[group].append(r)
        if key:old[key]+=1
    edits=[];accepted=[]
    head_counts=Counter(h[1] for h in heads if h[1] is not None)
    for group,items in groups.items():
        reasons=[];plans=[];maps={}
        for seq,r in enumerate(items,1):
            n=r['paragraph'];p=pkg.paragraphs[n-1];cap=r['parsed'];why=safe_reason(pkg,p)
            if r['chapter'] is not None and head_counts[r['chapter']]>1:reasons.append('多处一级标题使用同一章号，章节目标不唯一')
            if not r['chapter']:reasons.append('章号不确定，不以标题排列位置猜章号')
            if not cap or not cap['title'] or '续' in r['text'] or re.search(r'分图|附录',r['text']):reasons.append('题注编号/标题或续表、分图、附录形式无法可靠解释')
            if cap and cap['type']!=('figure' if group[1]=='figure_caption' else 'table'):reasons.append('图表类型与确认分类冲突')
            if why:reasons.append(why)
            if cap and old[r['key']]!=1:reasons.append('旧编号对应多个题注，目标不唯一，整组不执行')
            if not cap or not r['chapter']:continue
            target=(cap['type'],r['chapter'],seq);maps[r['key']]=(target,n)
            match=NUMBER.match(r['text'].lstrip());leading=len(r['text'])-len(r['text'].lstrip())
            if match and r['key']!=target:
                # Change number digits only; preserve 图/表, spaces and hyphen.
                for a,b,v in [(match.start(2),match.end(2),str(target[1])),(match.start(3),match.end(3),str(target[2]))]:
                    if r['text'][leading+a:leading+b]!=v:plans.append({'paragraph':n,'start':leading+a,'end':leading+b,'before':r['text'][leading+a:leading+b],'after':v,'kind':'caption','target_paragraph':n})
        for ns,typ in m['paragraph_types'].items():
            if typ!='body':continue
            n=int(ns);p=pkg.paragraphs[n-1];tx=text(p)
            for match in NUMBER.finditer(tx):
                key=('figure' if match[1]=='图' else 'table',int(match[2]),int(match[3]))
                if key not in maps:continue
                target,dest=maps[key]
                if target==key:continue
                why=safe_reason(pkg,p)
                # Existing citation offsets cannot be blindly carried across changed text.
                if why or n in m.get('citation_scope',{}).get('scan',[]):reasons.append('关联正文引用不可安全同步：'+(why or '本段有已绑定引文字符范围，需重新确认'))
                for a,b,v in [(match.start(2),match.end(2),str(target[1])),(match.start(3),match.end(3),str(target[2]))]:
                    if tx[a:b]!=v:plans.append({'paragraph':n,'start':a,'end':b,'before':tx[a:b],'after':v,'kind':'reference','target_paragraph':dest})
        # Caption paragraphs with active character ranges are equally protected.
        if any(r['paragraph'] in m.get('citation_scope',{}).get('scan',[]) for r in items):reasons.append('题注与引文扫描范围重叠，禁止沿用旧字符定位')
        if reasons:
            blocked.append({'group':list(group),'paragraphs':[r['paragraph'] for r in items],'reasons':sorted(set(reasons))});continue
        edits.extend(plans);accepted.extend(r['paragraph'] for r in items)
    if len(edits)>10000:raise DemoError('动态文字改动超过10000处上限')
    ranges=defaultdict(list)
    for e in edits:
        ranges[e['paragraph']].append((e['start'],e['end']))
        e['spans']=spans(pkg.paragraphs[e['paragraph']-1],e['start'],e['end'],e['after'])
    for intervals in ranges.values():
        intervals.sort()
        if any(a[1]>b[0] for a,b in zip(intervals,intervals[1:])):raise DemoError('动态改动重叠，禁止执行')
    out={'version':VERSION,'input_sha256':pkg.hash,'scope_sha256':digest(m),'complete_authorized':True,
         'chapter_evidence':[{'paragraph':h[0],'number':h[1],'reason':h[2]} for h in heads],
         'edits':edits,'accepted_captions':accepted,'blocked_groups':blocked,'word':word_capability(),'limits':deepcopy(LIMITS)}
    if automatic:
        out['complete_authorized']=False
        # Independent full inventory proof, not an invented manual complete flag.
        reasons=[]
        for i,p in enumerate(pkg.paragraphs,1):
            typ=m['paragraph_types'][str(i)];tx=text(p)
            if NUMBER.search(tx) and typ not in ('body','figure_caption','table_caption') and str(i) not in m.get('material_exclusions',{}):reasons.append('有未纳入安全引用范围的图表编号文字')
        from .front import fields
        if any(re.match(r'\s*(REF|PAGEREF|SEQ)(?:\s|$)',f['instruction'],re.I) for f in fields(pkg.root)):reasons.append('文档含REF/PAGEREF/SEQ，关联无法完整同步')
        from .internal_refs import _stories
        stories,story_issues=_stories(pkg)
        if story_issues:reasons.append('相关故事清单不完整，不能证明全部关联已覆盖')
        for part,kind,story in stories:
            if part!='word/document.xml' and (NUMBER.search(text(story)) or any(re.match(r'\s*(REF|PAGEREF|SEQ)(?:\s|$)',f['instruction'],re.I) for f in fields(story))):reasons.append('注释或页眉页脚存在未覆盖的图表关联')
        top=set(pkg.paragraphs)
        if any(NUMBER.search(text(p)) for p in pkg.root.iter(q('p')) if p not in top):reasons.append('非顶层容器含图表编号，不能证明关联完整')
        out['automatic_scope']={'method':'full_supported_inventory','unresolved':sorted(set(reasons)),'not_manual_complete_confirmation':True}
        if reasons:
            out['blocked_groups']+= [{'group':['automatic_inventory'],'paragraphs':out['accepted_captions'],'reasons':sorted(set(reasons))}];out['accepted_captions']=[];out['edits']=[]
    out['seal']=digest(out);return out

def _patch(root,edits):
    ps=root.find(q('body')).findall(q('p'));by=defaultdict(list)
    for e in edits:by[e['paragraph']].append(e)
    for n,rows in by.items():
        ts=ps[n-1].xpath('./w:r/w:t',namespaces=NS);per=defaultdict(list)
        for e in rows:
            for s in e['spans']:per[s['text_node']].append(s)
        for i,changes in per.items():
            value=ts[i].text or ''
            for s in sorted(changes,key=lambda v:v['start'],reverse=True):
                if value[s['start']:s['end']]!=s['before']:raise DemoError('原始数字范围不再对应')
                value=value[:s['start']]+s['after']+value[s['end']:]
            ts[i].text=value

def validate_output(input_path,output_path,plan,classification):
    original=Package(input_path);saved=Package(output_path)
    if propose(input_path,classification,complete=True,automatic='automatic_scope' in plan)!=plan:raise DemoError('动态计划、范围或执行代码不对应')
    if set(original.parts)!=set(saved.parts):raise DemoError('包部件集合变化')
    if any(v!=saved.parts[k] for k,v in original.parts.items() if k!='word/document.xml'):raise DemoError('动态事务改动了未授权部件')
    expected=parse(original.parts['word/document.xml']);_patch(expected,plan['edits'])
    if E.tostring(expected,method='c14n')!=E.tostring(saved.root,method='c14n'):raise DemoError('除授权w:t数字外存在未知差异，拒绝采用')
    if sha256(Path(input_path).read_bytes())!=original.hash or sha256(Path(output_path).read_bytes())!=saved.hash:raise DemoError('验证期间文件变化')
    return {'input_sha256':original.hash,'output_sha256':saved.hash,'only_authorized_numeric_text':True,'all_run_properties_preserved':True,'unselected_parts_byte_equal':True,'field_instructions_and_cache_preserved':True,'word_pages_verified':False}

def rehearse(input_path,output_path,classification,plan,**rules_args):
    from . import check_document
    from .dependencies import problem_delta
    new_path(output_path,input_path);pkg=Package(input_path)
    if propose(input_path,classification,complete=True,automatic='automatic_scope' in plan)!=plan:raise DemoError('动态方案已变化')
    if not plan['edits']:raise DemoError('没有安全动态改动；未生成无意义副本')
    before=check_document(input_path,mode='academic',classification_manifest=classification,**rules_args)
    _patch(pkg.root,plan['edits']);write_new(output_path,pkg.bytes(True),input_path)
    try:
        proof=validate_output(input_path,output_path,plan,classification);saved=Package(output_path)
        outm=deepcopy(classification);outm['input_sha256']=saved.hash;rebind(outm,saved.hash);validate_classification(saved,outm)
        after=check_document(output_path,mode='academic',classification_manifest=outm,**rules_args)
        from . import effective_rules
        if (after['rules']['sha256']!=before['rules']['sha256'] or
            effective_rules(mode='academic',**rules_args)['sha256']!=before['rules']['sha256'] or
            after['input_sha256']!=proof['output_sha256'] or
            sha256(Path(input_path).read_bytes())!=proof['input_sha256'] or
            sha256(Path(output_path).read_bytes())!=proof['output_sha256']):
            raise DemoError('动态读回复查期间输入、输出或规则发生变化，已拒绝副本')
        changes=[{'key':'dynamic:'+str(i),'rule_id':'R42','locator':{'paragraph':e['paragraph'],'start':e['start'],'end':e['end']},'property':'caption_number' if e['kind']=='caption' else 'plain_caption_reference','before':e['before'],'after':e['after'],'verification':'pass','source':SOURCE} for i,e in enumerate(plan['edits'],1)]
        return {'kind':'dynamic_text','output':str(output_path),'before':before,'after':after,'changes':changes,'skipped_review_keys':[],
                'output_body_manifest':{'input_sha256':saved.hash,'body_paragraphs':after['coverage']['body_paragraphs'],'confirmation':'动态数字事务后范围重新验证'},
                'input_classification_manifest':deepcopy(classification),'output_classification_manifest':outm,'problem_delta':problem_delta(before,after),
                'dynamic':{'plan':plan,'validation':proof,'word':word_capability()},'preservation':{'original_sha256_unchanged':True,'only_authorized_numeric_text':True,'unselected_zip_member_bytes_equal':True}}
    except Exception:Path(output_path).unlink(missing_ok=True);raise

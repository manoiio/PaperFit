"""Session-local structure proposal, not a classification confirmation or persisted AI cache."""
from copy import deepcopy
import json,time
from ai.structure import VERSION,PROMPT,MAX_INPUT,MAX_CANDIDATES,roles,redact,withheld,analyze
from ai.short_spec import settings
from core.package import DemoError
from core.classification import title_number
from .scope_session import fingerprint
from .smart_session import binding,suggest,isolated


def prepare(model):
    start=binding(model);rows=model.suggestions['paragraphs'];candidates=[];protected=[];remaining=0
    fixed=bool(model.classification_confirmed or (model.mode=='basic' and model.body))
    # Already prepared optional scopes remain protected, not a new inference target.
    from core.package import Package,NS,q
    pkg=Package(model.input_path)
    from core.formats import Resolver,Unresolved
    resolver=Resolver(pkg);unsafe_ids=set()
    for i,p in enumerate(pkg.paragraphs,1):
        unsafe=any(c.tag not in (q('pPr'),q('r')) for c in p)
        try:
            for r in p.findall(q('r')):
                if resolver.special(r,resolver.layers(p,r)):unsafe=True
        except (Unresolved,ValueError):unsafe=True
        if unsafe:unsafe_ids.add(str(i))
    reserved=set()
    for scope in (model.front_draft if model.front_enabled else None,model.toc_draft if model.toc_enabled else None):
        for ident in (scope or {}).get('objects',{}):
            if ident.startswith('p:'):reserved.add(ident.split(':')[1])
    def snippet(r):return {'id':'p:'+str(r['index']),'text':redact(r['text'],85) if not withheld(r['text']) and str(r['index']) not in unsafe_ids and str(r['index']) not in model.material_exclusions and str(r['index']) not in reserved and not r['special'] else '[保护或个人信息片段不发送]'}
    for i,row in enumerate(rows):
        n=str(row['index']);current=model.paragraph_types[n];p=pkg.paragraphs[i]
        blocked=fixed or current!=row['suggested_type'] or n in model.material_exclusions or n in reserved or withheld(row['text'])
        # No links/fields/bookmarks/unknown structural grants. Plain paragraphs only.
        unsafe=bool(n in unsafe_ids or row['special'] or any(c.tag not in (q('pPr'),q('r')) for c in p) or p.xpath('.//w:fldChar|.//w:instrText|.//w:drawing|.//w:pict|.//w:footnoteReference|.//w:endnoteReference|.//w:vertAlign',namespaces=NS))
        if blocked or unsafe:
            protected.append({'id':'p:'+n,'reason':'人工确认/调整、明确材料保护或保留模块对象' if blocked else '复杂或特殊结构，不使用AI放开保护'})
            continue
        unresolved_zone=(model.mode=='academic' and current=='other' and row['reason']=='所在章节不属于本阶段正文范围' and any(r['ambiguous'] and title_number(r['text']) for r in rows[max(0,i-12):i]))
        if not row['text'].strip() or not (row['ambiguous'] or current=='pending' or unresolved_zone):continue
        if len(candidates)>=MAX_CANDIDATES:remaining+=1;continue
        anchors=[snippet(r) for r in rows[max(0,i-12):i] if r['suggested_type'].startswith('heading') or r['suggested_type'].endswith('_title') or title_number(r['text'])][-2:]
        item={**snippet(row),'text':redact(row['text']),'local_role':current,'local_reason':redact(row['reason'],90),
              'style':redact(row.get('style_name',''),40),'outline_level':row.get('outline_level'),
              'context':[snippet(r) for r in rows[max(0,i-1):min(len(rows),i+2)] if r is not row], 'anchors':anchors}
        trial=candidates+[item]
        req={'version':VERSION,'mode':model.mode,'allowed_roles':roles(model.mode),'candidates':trial}
        if len(json.dumps(req,ensure_ascii=False,sort_keys=True))>MAX_INPUT:remaining+=1;continue
        candidates.append(item)
    request={'version':VERSION,'mode':model.mode,'allowed_roles':roles(model.mode),'candidates':candidates}
    out={'binding':start,'request':request,'protected':protected,'remaining':remaining,'prompt_sha256':fingerprint(PROMPT)}
    out['seal']=fingerprint(out)
    if binding(model)!=start:raise DemoError('准备期间文件或范围变化')
    return out


def verify(model,prepared):
    if prepared.get('seal')!=fingerprint({k:v for k,v in prepared.items() if k!='seal'}) or prepared['binding']!=binding(model):raise DemoError('AI候选已失效；请核对当前文件与范围后重新准备')
    if prepared!=prepare(model):raise DemoError('AI候选或提示词版本已变化')


def run(model,prepared,store,*,transport=None,config=None):
    verify(model,prepared)
    if not prepared['request']['candidates']:raise DemoError('没有可分析候选，未发起请求')
    config=settings() if config is None else config
    identity=fingerprint({'prepared':prepared,'model':config.model,'base':config.base_url,'prompt':PROMPT})
    if store.get('identity')==identity and store.get('result'):
        store['cache_hit']=True;return deepcopy(store['result'])
    store.clear();store.update(identity=identity,cache_hit=False,attempts=1,status='requesting',candidate_count=len(prepared['request']['candidates']))
    started=time.monotonic()
    try:
        result=analyze(prepared['request'],transport=transport,config=config)
        verify(model,prepared)
        result['prepared_seal']=prepared['seal']
        store.update(result=deepcopy(result),status='validated')
        return result
    except Exception as exc:
        # Never retain raw excerpt/response, credentials, exception internals or raw server error.
        store.update(status='failed',elapsed_seconds=round(time.monotonic()-started,3))
        raise DemoError(str(exc) if isinstance(exc,DemoError) else 'AI结构请求未完成；未自动重试，本地流程仍可继续') from None


def merge(model,prepared,result):
    verify(model,prepared)
    if result.get('prepared_seal')!=prepared['seal']:raise DemoError('此前AI结果不能绑定新候选或新文件')
    # Validate again from this exact transmitted request; don't trust cached accepted flags.
    from ai.structure import validate
    raw={'suggestions':[{k:r[k] for k in ('id','role','evidence','reason')} for r in result['suggestions']]}
    checked=validate(raw,prepared['request']);proposal=suggest(model);types=proposal['draft']['paragraph_types']
    for row in checked:
        if row['accepted']:types[row['id'].split(':')[1]]=row['role']
    proposal['draft']['body']=sorted(int(n) for n,t in types.items() if t=='body')
    stage=isolated(model)
    for k,v in proposal['draft'].items():setattr(stage,k,deepcopy(v))
    proposal['preflight']=stage.scope_preflight()
    proposal['excluded']=[r for r in proposal['excluded'] if types[str(r['paragraph'])] in ('other','pending')]
    proposal['structure_ai']={'receipt':deepcopy(result['receipt']),'accepted':sum(r['accepted'] for r in checked),
                              'rejected':sum(not r['accepted'] for r in checked),'omitted':len(prepared['request']['candidates'])-len(checked),
                              'rows':checked,'remaining_budget':prepared['remaining'],'protected':len(prepared['protected']),
                              'local_included':sum(t not in ('other','pending') for n,t in suggest(model)['draft']['paragraph_types'].items())}
    proposal['limits'][-1]='本次AI仅提供已展示候选的结构建议；用户接受后才确认范围。格式要求仍来自当前本地规则，结构保护和未纳入模块不变。'
    proposal.pop('seal');proposal['seal']=fingerprint(proposal)
    return proposal

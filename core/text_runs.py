"""Opt-in hyperlink text traversal. Never changes paragraph_unsafe's callers.
Locators retain direct run numbers; link/link_run index only direct XML children.
No URL dereference, field evaluation, run splitting or arbitrary XPath.
"""
from pathlib import PurePosixPath
from urllib.parse import urlsplit
from collections import Counter
from .package import q,NS,parse,DemoError,sha256
from .formats import paragraph_unsafe
from lxml import etree as E
REL='http://schemas.openxmlformats.org/package/2006/relationships'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
LIMITS=['仅已确认正文、参考文献条目、脚注/尾注的安全普通链接文字；不涵盖表格、页眉页脚或其他容器。','含链接段落的行距、缩进、段距、对齐及样式切换不放宽；R33含链接段落仍只读。','只解析所在部件自己的关系，不访问链接；目标可达性和实际跳转未验收。','首版只支持明确http/https外部链接；内部anchor、复杂域/目录缓存、修订与嵌套内容继续待复核。']

def relationship(pkg,part,link):
    if link.get(q('anchor')) is not None or link.get(q('docLocation')) is not None:raise DemoError('内部anchor/docLocation首版只读，未核对书签目标')
    allowed={'{'+R+'}id',q('tooltip'),q('history'),q('tgtFrame')}
    if set(link.attrib)-allowed:raise DemoError('链接有未知属性，影响范围无法可靠解释')
    rid=link.get('{'+R+'}id')
    if not rid:raise DemoError('链接缺少r:id和可解释的对应关系')
    path=PurePosixPath(part);member=str(path.parent/'_rels'/(path.name+'.rels'));raw=pkg.parts.get(member)
    if raw is None:raise DemoError('所在部件自己的relationships缺失，不借用主文档关系')
    cache=getattr(pkg,'_hyperlink_relationship_cache',{});key=(member,sha256(raw))
    if key not in cache:
        try:root=parse(raw)
        except (DemoError,E.XMLSyntaxError):raise DemoError('链接relationships XML损坏/不安全') from None
        if root.tag!='{'+REL+'}Relationships' or any(c.tag!='{'+REL+'}Relationship' for c in root) or len(root)>10000:raise DemoError('链接relationships结构或容量不支持')
        ids=[e.get('Id') for e in root]
        if None in ids or any(n>1 for n in Counter(ids).values()):raise DemoError('所在部件relationships ID缺失或重复')
        cache[key]={e.get('Id'):dict(e.attrib) for e in root};pkg._hyperlink_relationship_cache=cache
    rel=cache[key].get(rid)
    if not rel or rel.get('Type')!=R+'/hyperlink':raise DemoError('r:id未唯一对应普通hyperlink关系')
    target=rel.get('Target','')
    try:url=urlsplit(target)
    except ValueError:raise DemoError('链接目标语法不能可靠解析') from None
    if rel.get('TargetMode')!='External' or url.scheme not in ('http','https') or not url.netloc or any(ord(c)<32 for c in target):raise DemoError('仅支持明确http/https外部目标；缺失或其他关系目标只读')
    return {'relationship_part':member,'relationship_id':rid,'target_mode':'External','target_scheme':url.scheme,'target_sha256':sha256(target.encode()),'target_opened':False}

def context_reason(pkg,p,part):
    if any(a.tag in {q(t) for t in ('sdt','ins','del','moveFrom','moveTo','tbl','txbxContent','fldSimple')} for a in p.iterancestors()):return '目录内容控件、修订、表格或其他未支持容器仍只读'
    if p.xpath('.//w:fldSimple|.//w:fldChar|.//w:instrText',namespaces=NS):return '域指令/缓存及边界只读，不因hyperlink放宽'
    if part=='word/document.xml':
        if not hasattr(pkg,'_hyperlink_field_paragraphs'):
            from .citations import field_paragraphs
            pkg._hyperlink_field_paragraphs=field_paragraphs(pkg)
        if any(p is pkg.paragraphs[n-1] for n in pkg._hyperlink_field_paragraphs):return '跨段域或自动目录缓存只读'
    ps=p.find('w:pPr/w:pStyle',NS)
    if ps is not None and (ps.get(q('val'),'').lower().startswith('toc') or ps.get(q('val'),'').startswith('目录')):return 'TOC类样式/目录候选不套正文链接文字规则'
    if len(p.findall(q('pPr')))>1 or p.find('w:pPr/w:pPrChange',NS) is not None or p.find('w:pPr/w:framePr',NS) is not None:return '重复段落属性、修订或浮动段落仍只读'
    allowed={q(t) for t in ('pPr','r','hyperlink','bookmarkStart','bookmarkEnd','proofErr')}
    if any(c.tag not in allowed for c in p):return '段落含未支持包裹，保留原整段保护'
    return None

def run_reason(r):
    rp=r.findall(q('rPr'))
    if len(rp)>1 or rp and r[0] is not rp[0]:return 'rPr重复或位于文字之后，不能证明Word有效格式'
    if any(c.tag not in {q(t) for t in ('rPr','t','tab','br','cr')} for c in r):return '非普通文字run：编号标记/域/公式/图片等继续保护'
    return None

def walk(pkg,p,part='word/document.xml'):
    """Only direct runs + validated direct hyperlink/direct runs, in XML order."""
    reason=context_reason(pkg,p,part);rows=[];issues=[];direct=0;link_index=0;links=0
    for child in p:
        if child.tag==q('r'):
            direct+=1;rows.append({'locator':{'run':direct},'node':child,'reason':reason or run_reason(child),'evidence':None})
        elif child.tag==q('hyperlink'):
            link_index+=1;loc={'link':link_index}
            try:
                if reason:raise DemoError(reason)
                proof=relationship(pkg,part,child)
                if not len(child) or any(c.tag!=q('r') for c in child):raise DemoError('链接含嵌套包裹/书签/修订或没有直属普通run')
                why=[run_reason(r) for r in child]
                if any(why):raise DemoError('链接中含不支持run：'+next(x for x in why if x))
                links+=1
                for j,r in enumerate(child,1):rows.append({'locator':{**loc,'link_run':j},'node':r,'reason':None,'evidence':proof})
            except DemoError as exc:issues.append({'locator':loc,'detail':str(exc)})
    return {'rows':rows,'issues':issues,'supported_links':links,'context_reason':reason}

def select_run(p,loc):
    def pick(items,n):
        if type(n) is not int or not 1<=n<=len(items):raise DemoError('受控文字定位超出当前XML对象范围')
        return items[n-1]
    if 'link' in loc:
        if 'run' in loc or 'link_run' not in loc:raise DemoError('链接与直属run定位冲突')
        return pick(pick(p.findall(q('hyperlink')),loc['link']).findall(q('r')),loc['link_run'])
    if 'link_run' in loc or 'run' not in loc:raise DemoError('链接与直属run定位不完整')
    return pick(p.findall(q('r')),loc['run'])

def executable_run(pkg,p,loc,part='word/document.xml'):
    row=next((x for x in walk(pkg,p,part)['rows'] if x['locator']=={k:loc[k] for k in ('run','link','link_run') if k in loc}),None)
    if row is None or row['reason']:raise DemoError('所选链接文字已不在可执行的受控结构中')
    return row['node']

def annotate(report):
    fs=[f for f in report['findings'] if 'link' in f['locator']]
    if not fs:return
    report['coverage']['hyperlink_text']={'finding_count':len(fs),'supported_text_locators':len({(f.get('story_part'),str({k:v for k,v in f['locator'].items() if k!='property'})) for f in fs if 'link_run' in f['locator']}),'limits':LIMITS}
    for f in fs:
        f['text_structure']='受控普通超链接文字' if 'link_run' in f['locator'] else '受保护链接对象'
        if 'link_run' in f['locator']:
            f['detail']=(f.get('detail','')+'；' if f.get('detail') else '')+'所在部件关系及直属普通run已核对；仅检查配置的文字属性，不访问目标，不验证跳转或段落排版。'

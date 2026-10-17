"""确定性段落建议；建议不是确认，不发送任何论文文本到网络。"""
import re
import json
from lxml import etree as ET
from pathlib import Path
from .package import Package, DemoError, q, NS, parse
from .formats import Resolver, Unresolved, paragraph_unsafe

TYPES = {'body':'正文','heading1':'一级标题','heading2':'二级标题','heading3':'三级标题',
         'figure_caption':'图题','table_caption':'表题','other':'其他','pending':'待确认'}
from .academic_rules import NEW_TYPES
TYPES.update(NEW_TYPES)
from .backmatter import TYPES as BACK_TYPES
TYPES.update(BACK_TYPES)
MARKERS = {'摘要':'abstract','中文摘要':'abstract','英文摘要':'abstract','abstract':'abstract',
           '目录':'toc','参考文献':'references','致谢':'acknowledgements','附录':'appendix'}

def validate_classification(pkg, manifest):
    if isinstance(manifest,(str,Path)):
        try:manifest=json.loads(Path(manifest).read_text(encoding='utf-8'))
        except (ValueError,OSError):raise DemoError('分类清单不可读取') from None
    if not isinstance(manifest,dict) or set(manifest)-{'table_scope','front_scope','toc_scope','citation_scope','note_scope','reference_scope','caption_scope','material_exclusions'}!={'input_sha256','paragraph_types','confirmed','confirmation'}:
        raise DemoError('须提供完整、人工确认的分类清单')
    if manifest['input_sha256']!=pkg.hash:raise DemoError('分类清单哈希不匹配，请重新确认')
    if manifest['confirmed'] is not True or not isinstance(manifest['confirmation'],str) or not manifest['confirmation'].strip():
        raise DemoError('分类建议尚未人工确认，禁止用于检查或修正')
    items=manifest['paragraph_types']
    if not isinstance(items,dict) or set(items)!={str(i) for i in range(1,len(pkg.paragraphs)+1)} or any(type(v) is not str or v not in TYPES for v in items.values()):
        raise DemoError('分类清单必须覆盖所有顶层段落且类型合法')
    if 'material_exclusions' in manifest:
        from .backmatter import validate_exclusions
        validate_exclusions(pkg,manifest['material_exclusions'],items)
    if 'table_scope' in manifest:
        from .table_text import validate_scope
        validate_scope(pkg,manifest['table_scope'])
    if 'front_scope' in manifest:
        from .front import validate_scope
        validate_scope(pkg,manifest['front_scope'])
        for ident in manifest['front_scope']['objects']:
            if ident.startswith('p:') and manifest['paragraph_types'][ident.split(':')[1]] not in ('other','pending'):
                raise DemoError('封面对象与正文/标题等分类重叠，请将该封面段落核对为其他；不会自动改分类或套两种规则')
            if ident.startswith('t:') and manifest.get('table_scope',{}).get('table_types',{}).get(ident.split(':')[1])=='content':
                raise DemoError('封面对象所在表格被确认成论文内容表格，请先核对用途；不能同时套R23与封面规则')
    if manifest.get('toc_scope'):
        from .toc import validate_scope, inventory
        validate_scope(pkg,manifest['toc_scope'])
        rows={r['id']:r for r in inventory(pkg)['objects']}
        for oid in manifest['toc_scope']['objects']:
            n=rows[oid]['locator'].get('paragraph')
            if n and items[str(n)] not in ('other','pending'):
                raise DemoError('目录范围与正文/标题分类重叠，请明确调整分类并重新确认；不会静默改范围')
            if n and 'p:'+str(n) in manifest.get('front_scope',{}).get('objects',{}):
                raise DemoError('目录对象与封面对象冲突，请明确核对范围')
    if manifest.get('citation_scope'):
        from .citations import validate_scope
        validate_scope(pkg,manifest['citation_scope'],manifest)
    if manifest.get('reference_scope'):
        from .internal_refs import validate_scope
        validate_scope(pkg,manifest['reference_scope'])
    if manifest.get('note_scope'):
        from .notes import validate_scope
        validate_scope(pkg,manifest['note_scope'])
    if manifest.get('caption_scope'):
        from .captions import validate_scope
        validate_scope(pkg,manifest['caption_scope'],manifest)
    return manifest

def title_number(text):
    if len(text)>60 or re.search(r'[。！？!?；;]',text):return None
    if re.match(r'^第[一二三四五六七八九十百零〇\d]+章\s*\S',text):return 1
    m=re.match(r'^(\d{1,2}(?:\.\d{1,2}){0,2})\s+([^\d\s].*)$',text)
    if not m:return None
    tail=m[2]
    if re.match(r'(?:倍|年|月|日|磅|pt|毫米|厘米|%|个|项)',tail,re.I):return None
    return m[1].count('.')+1

def numbering_heading_level(pkg, res, p):
    """Only a hierarchical decimal numbering clue, never a confirmed heading."""
    try:
        attrs={}
        for layer in res.layers(p,kind='pPr'):
            num=layer.find(q('numPr'))
            if num is not None:
                for e in num:attrs[e.tag]=e.get(q('val'))
        ident=attrs.get(q('numId'));level=int(attrs.get(q('ilvl'),'0'))
        if ident in (None,'0') or level not in (0,1,2):return None
        root=parse(pkg.parts.get('word/numbering.xml',b'<numbering/>'))
        nums=[e for e in root.findall(q('num')) if e.get(q('numId'))==ident]
        if len(nums)!=1 or nums[0].find(q('lvlOverride')) is not None:return None
        abstract=nums[0].find(q('abstractNumId')).get(q('val'))
        definitions=[e for e in root.findall(q('abstractNum')) if e.get(q('abstractNumId'))==abstract]
        if len(definitions)!=1:return None
        definition=definitions[0];multi=definition.find(q('multiLevelType'))
        if multi is None or multi.get(q('val')) not in ('multilevel','hybridMultilevel'):return None
        levels=[e for e in definition.findall(q('lvl')) if e.get(q('ilvl'))==str(level)]
        if len(levels)!=1:return None
        fmt=levels[0].find(q('numFmt'));pattern=levels[0].find(q('lvlText'))
        if fmt is None or fmt.get(q('val'))!='decimal' or pattern is None:return None
        if not re.fullmatch(r'%1[.、]?' if level==0 else ''.join('%'+str(i)+r'\.' for i in range(1,level+2))+'?',pattern.get(q('val'),'')):return None
        return level+1
    except (Unresolved,ValueError,AttributeError,DemoError,ET.XMLSyntaxError):return None

def suggest_paragraph_types(input_path, *, include_sections=False, body_start=None):
    pkg=Package(input_path);res=Resolver(pkg);rows=[];zone='front';main=False
    body_children=list(pkg.root.find(q('body')))
    if body_start is not None and (type(body_start) is not int or not 1<=body_start<=len(pkg.paragraphs)):raise DemoError('明确正文起点无效')
    heading_seen=False
    for n,p in enumerate(pkg.paragraphs,1):
        if n==body_start:zone='body';main=True;heading_seen=True
        text=''.join(p.xpath('.//w:t/text()',namespaces=NS)).strip()
        ps=p.find('w:pPr/w:pStyle',NS);sid=ps.get(q('val')) if ps is not None else None
        name=res.styles[sid].find(q('name')) if sid in res.styles else None
        style_name=name.get(q('val')) if name is not None else sid or '默认'
        outline=None;style_level=None
        try:
            raw=res.value(res.layers(p,kind='pPr'),'outlineLvl')
            outline=int(raw) if raw is not None else None
            if sid in ('Heading1','Heading2','Heading3') and style_name.lower() in (f'heading {sid[-1]}',f'标题 {sid[-1]}',f'标题{sid[-1]}'):
                style_level=int(sid[-1])
        except (Unresolved,ValueError):pass
        level=title_number(text)
        numbered=numbering_heading_level(pkg,res,p)
        marker_text=re.sub(r'\s','',text).lower()
        marker=MARKERS.get(marker_text)
        if marker is None:
            marker_text=re.sub(r'^(?:第[一二三四五六七八九十百零〇\d]+章|\d+(?:\.\d+){0,2})','',marker_text)
            marker=MARKERS.get(marker_text)
        special=paragraph_unsafe(p)
        ambiguous=False;kind='pending';reason='没有足够上下文，需人工核对'
        toc=re.search(r'\.{2,}|…{2,}|\t\s*\d+\s*$',text) or (sid and re.match(r'^TOC\d',sid,re.I))
        if zone=='toc' and re.search(r'\s+\d+\s*$',text):toc=True
        next_text=''.join(pkg.paragraphs[n].xpath('.//w:t/text()',namespaces=NS)).strip() if n<len(pkg.paragraphs) else ''
        main_start=(level==1 and len(next_text)>20 and bool(re.search(r'[。！？!?]',next_text)))
        references=re.match(r'^[\[［]\d+[\]］]',text)
        from .structure_evidence import heading
        boundary=heading({'text':text,'number_level':level,'style_id':sid,'outline_level':outline,'special':special,'toc_like':bool(toc),'narrative_after':main_start})
        if boundary==1:zone='main';main=True;heading_seen=True
        drawing=bool(p.xpath('.//w:drawing|.//w:pict',namespaces=NS))
        if marker:
            zone=marker;kind='other';reason='章节标记，摘要/目录/参考文献等不自动套正文或正文标题规则'
        elif not text or drawing:
            kind='other';reason='空段、分节段或图片段，不是普通正文'
        elif toc or references:
            kind='other';reason='目录条目或参考文献条目，排除标题和正文建议'
        elif special:
            kind='pending';ambiguous=True;reason=special+'；需确认，格式引擎仍会保护'
        elif re.match(r'^(图|表)\s*\d+(?:[-－—.]\d+)?\s+\S',text) and len(text)<=100:
            kind='figure_caption' if text.startswith('图') else 'table_caption'
            at=body_children.index(p)
            adjacent=any(c.tag==q('tbl') for c in body_children[max(0,at-1):at+2]) if kind=='table_caption' else any(c.xpath('.//w:drawing|.//w:pict',namespaces=NS) for c in body_children[max(0,at-1):at+2])
            reason='图表编号及短文本形式'+('，相邻图表支持' if adjacent else '；未找到相邻图表，需核对')
            ambiguous=not adjacent
        elif sid=='Title' or re.search(r'软件演示样本|作者[:：]|学号[:：]',text):
            kind='other';reason='封面/软件演示说明，不批量当正文'
        elif re.match(r'^\d+(?:\.\d+)?\s*(?:倍|年|月|日|磅|pt|毫米|厘米|%)',text,re.I) and (style_level or (outline is not None and 0<=outline<=2)):
            kind='pending';ambiguous=True;reason='数字/单位或年份句子与标题样式冲突，不能自动升级为标题'
        elif style_level or (outline is not None and 0<=outline<=2):
            proposed=style_level or outline+1
            if zone in ('references','abstract','acknowledgements','appendix') or (zone=='toc' and not main_start):
                kind='pending';ambiguous=True;reason='特殊章节内的标题样式，需确认是否正文标题'
            elif len(text)>60 or re.search(r'[。！？!?；;]',text) or (level is not None and level!=proposed) or (style_level and outline!=style_level-1):
                kind='pending';ambiguous=True;reason='标题样式/大纲与文本形态或编号层次不一致'
            else:
                kind=f'heading{proposed}';reason='标题样式/大纲级别与短文本一致；仍需人工确认'
                if zone=='toc':ambiguous=True;reason='目录之后的章标题及相邻叙述段支持正文起点；请特别核对'
                zone='main';main=True;heading_seen=True
        elif numbered and len(text)<=60 and not re.search(r'[。！？!?；;]',text) and zone not in ('abstract','toc','references','acknowledgements','appendix') and (main or (numbered==1 and len(next_text)>60 and re.search(r'[。！？!?]',next_text))):
            kind=f'heading{numbered}';ambiguous=True
            reason='多级十进制自动编号与短文本/相邻叙述段提供标题线索；也可能是列表，必须人工核对'
            zone='main';main=True
        elif level:
            kind=f'heading{level}';reason='章/节/条编号及短文本形式；可能为手工标题，需核对'
            ambiguous=True
            if zone in ('references','abstract','acknowledgements','appendix') or (zone=='toc' and not main_start):
                kind='pending';reason='处于目录/参考文献区域，编号不能直接升级成正文标题'
            else:zone='main';main=True;heading_seen=True
        elif zone in ('abstract','toc','references','acknowledgements','appendix'):
            kind='other';reason='所在章节不属于本阶段正文范围'
        elif main and (len(text)>35 or re.search(r'[。！？!?]',text)):
            kind='body';reason='正文章节内的连续叙述段；不是标题编号形式'
        else:
            kind='pending';ambiguous=True;reason='短文本或尚未找到正文起点，需人工确认'
        rows.append({'index':n,'text':text,'style_id':sid,'style_name':style_name,'outline_level':outline,
                     'suggested_type':kind,'reason':reason,'ambiguous':ambiguous,'special':special,'number_level':level,'toc_like':bool(toc),'narrative_after':main_start,'structure_boundary':boundary==1 or n==body_start,'section_marker':marker,'marker_name':marker_text if marker else None})
    if include_sections:
        from .section_classification import refine
        refine(rows)
        from .backmatter import refine as refine_back
        refine_back(rows, pkg.paragraphs)
    return {'input_sha256':pkg.hash,'algorithm':'deterministic-sections-2.0' if include_sections else 'deterministic-demo-2.0','confirmed':False,
            'indexing':'主文档顶层段落，包含空段和图片段，不含表格内段落；无概率置信度',
            'paragraphs':rows}

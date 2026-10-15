"""自动编号只读证据。编号符号与段落文字分开；本模块从不写numbering.xml。"""
from copy import deepcopy
from .package import q,NS,parse,DemoError
from .formats import Unresolved
from lxml import etree as ET

def numbering_info(pkg,res,p):
    result={'present':False,'status':'not_applicable','numbering_xml_modified':False,'reason':'没有有效自动编号'}
    try:
        props={};style_numbering=False
        for layer in res.layers(p,kind='pPr'):
            es=layer.findall(q('numPr'))
            if len(es)>1:raise Unresolved('重复numPr，编号来源不唯一')
            if es:
                result['present']=True
                if layer.getparent().tag==q('style'):style_numbering=True
                num=es[0]
                if set(e.tag for e in num)-{q('numId'),q('ilvl')}:raise Unresolved('编号修订或未支持numPr结构')
                for tag in ('numId','ilvl'):
                    vs=num.findall(q(tag))
                    if len(vs)>1:raise Unresolved('重复'+tag+'，编号来源不唯一')
                    if vs:props[tag]=vs[0].get(q('val'))
        if not result['present']:return result
        if props.get('numId')=='0':return {**result,'present':False,'status':'not_applicable','reason':'numId=0取消编号'}
        ident=props.get('numId');index=props.get('ilvl','0')
        if not ident or not ident.isdigit() or not index.isdigit() or not 0<=int(index)<=8:raise Unresolved('numId/ilvl缺失或非法')
        result.update(num_id=ident,ilvl=int(index))
        if style_numbering:raise Unresolved('样式中的numPr涉及层级绑定；本阶段不解析样式链接编号')
        root=parse(pkg.parts.get('word/numbering.xml',b'<numbering/>'))
        nums=[e for e in root.findall(q('num')) if e.get(q('numId'))==ident]
        if len(nums)!=1:raise Unresolved('numbering.xml对应numId缺失或重复')
        num=nums[0];refs=num.findall(q('abstractNumId'))
        if len(refs)!=1:raise Unresolved('abstractNumId缺失或重复')
        abstracts=[e for e in root.findall(q('abstractNum')) if e.get(q('abstractNumId'))==refs[0].get(q('val'))]
        if len(abstracts)!=1:raise Unresolved('抽象编号定义缺失或重复')
        abstract=abstracts[0];result['abstract_num_id']=refs[0].get(q('val'))
        if abstract.find(q('numStyleLink')) is not None or abstract.find(q('styleLink')) is not None:raise Unresolved('编号样式链接，不能唯一解析符号/层级')
        levels=[e for e in abstract.findall(q('lvl')) if e.get(q('ilvl'))==index]
        if len(levels)!=1:raise Unresolved('编号层级缺失或重复')
        level=levels[0];overrides=[e for e in num.findall(q('lvlOverride')) if e.get(q('ilvl'))==index]
        if len(overrides)>1:raise Unresolved('重复编号层级覆盖')
        if overrides:
            ov=overrides[0]
            if set(e.tag for e in ov)-{q('startOverride'),q('lvl')} or len(ov.findall(q('lvl')))>1 or len(ov.findall(q('startOverride')))>1:raise Unresolved('编号覆盖冲突或复杂结构')
            start=ov.find(q('startOverride'))
            if start is not None and (not start.get(q('val'),'').isdigit()):raise Unresolved('编号起点覆盖非法')
            replacement=ov.find(q('lvl'))
            if replacement is not None:
                if replacement.get(q('ilvl'))!=index:raise Unresolved('覆盖编号层级不一致')
                level=replacement;result['level_overridden']=True
            result['start_override']=start.get(q('val')) if start is not None else None
        if level.find(q('pStyle')) is not None or level.find(q('lvlPicBulletId')) is not None:raise Unresolved('编号绑定段落样式或图片编号，符号需人工复核')
        for tag in ('pPr','rPr','numFmt','lvlText'):
            if len(level.findall(q(tag)))>1:raise Unresolved('重复编号层级属性 '+tag)
        fmt=level.find(q('numFmt'));pattern=level.find(q('lvlText'))
        if fmt is None or fmt.get(q('val'))!='decimal' or pattern is None:raise Unresolved('当前只读符号解析仅支持明确十进制编号')
        import re
        if not re.fullmatch(r'(?:%[1-9][.、)]?)+',pattern.get(q('val'),'')):raise Unresolved('复杂编号文本模板，符号待复核')
        tokens=__import__('re').findall(r'%([1-9])',pattern.get(q('val'),''))
        if len(tokens)!=len(set(tokens)) or any(int(t)>int(index)+1 for t in tokens):raise Unresolved('编号模板层级引用冲突')
        result.update(status='resolved',reason='numPr→numId→abstractNumId→ilvl已只读核对；不计算编号序列或连续性',symbol_template=pattern.get(q('val')),
                      paragraph_properties=deepcopy(level.find(q('pPr'))),symbol_properties=deepcopy(level.find(q('rPr'))))
    except (Unresolved,DemoError,ET.XMLSyntaxError) as exc:result.update(status='review',reason=str(exc))
    return result

def public_numbering(info):
    return {k:v for k,v in info.items() if k not in ('paragraph_properties','symbol_properties')}

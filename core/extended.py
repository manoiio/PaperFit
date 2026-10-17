"""标题/题注格式使用同一Resolver和属性级补丁；不改共享样式文件。"""
from pathlib import Path
from copy import deepcopy
import json
import math
from lxml import etree as ET
from .package import q, NS, DemoError, sha256
from .formats import Resolver, Unresolved, scripts, paragraph_unsafe, same_font
from .classification import TYPES
from .numbering import numbering_info, public_numbering

EXTENDED_RULES=Path(__file__).resolve().parents[1]/'rules/scut_2015_extended.json'
EXT_IDS=tuple(f'R{i:02}' for i in range(8,13))
# Audited default values stay fixed; v3 customization only enters via validated template compilation.
EXPECTED={f'R{i+8:02}':{'font_cn':'黑体','font_latin':'Times New Roman','size_pt':size,'alignment':align,'line_multiple':1}
          for i,(size,align) in enumerate(((18,'center'),(15,'left'),(14,'left')))}
EXPECTED.update(R11={'heading_levels':[1,2,3]},R12={'font_cn':'宋体','font_latin':'宋体','size_pt':10.5})

def extend_rules(base):
    raw=EXTENDED_RULES.read_bytes();ext=json.loads(raw)
    if set(ext.get('rules',{}))!=set(EXT_IDS) or any(ext['rules'][r].get('expected')!=EXPECTED[r] for r in EXT_IDS):
        raise DemoError('标题题注扩展必须使用已核对的固定R08–R12')
    out=deepcopy(base)
    out['rules'].update(ext['rules'])
    custom=base.get('extension_config')
    if custom:
        # Produced only by strict confirmed-template compilation, never by AI directly.
        for rid,expected in custom['expected'].items():
            out['rules'][rid]['expected']=deepcopy(expected)
        for rid in ('R08','R09','R10'):
            out['rules'][rid]['property_sources']=deepcopy(custom['property_sources'][rid])
        out['rules']['R12']['caption_sources']={obj:deepcopy(custom['property_sources'][obj]) for obj in ('figure_caption','table_caption')}
    out.update(name=base['name']+'（正文及标题题注）',version=base['version']+'+'+ext['version'],
               body_config_sha256=base['sha256'],extension_sha256=sha256(raw),mode='extended')
    out['sha256']=sha256((base['sha256']+':'+sha256(raw)).encode())
    return out

def authentic(res,level):
    sid=f'Heading{level}';s=res.styles.get(sid)
    if s is None or s.get(q('type'))!='paragraph' or s.get(q('customStyle')) in ('1','true','on'):return False
    name=s.find(q('name'))
    if len(s.getparent().findall(f"w:style[@w:styleId='{sid}']",NS))!=1 or len(s.findall(q('name')))!=1:return False
    if name is None or name.get(q('val'),'').lower() not in (f'heading {level}',f'标题 {level}',f'标题{level}'):return False
    try:
        chain=res.chain(sid,'paragraph')
        if any(len(x.findall('w:pPr/w:outlineLvl',NS))>1 for x in chain):return False
        return res.value([x.find(q('pPr')) for x in chain if x.find(q('pPr')) is not None],'outlineLvl')==str(level-1)
    except Unresolved:return False

# Only the following inheritance changes can be explicitly preserved with known defaults.
DEFAULTS={k:{'val':'0'} for k in ('b','bCs','i','iCs','keepNext','keepLines','pageBreakBefore','contextualSpacing')}
DEFAULTS.update(widowControl={'val':'1'},jc={'val':'left'},color={'val':'auto'})
MERGE={'spacing','ind','rFonts'}

def effective_nodes(res,layers,kind):
    out={}
    for layer in layers:
        for child in layer:
            tag=ET.QName(child).localname
            if tag in ('pStyle','rStyle','outlineLvl','rPr','sectPr'):continue
            if tag in MERGE:
                current=out.get(tag)
                if current is None:out[tag]=deepcopy(child)
                else:current.attrib.update(child.attrib)
                if tag=='rFonts':
                    current=out[tag]
                    for slot in ('eastAsia','ascii','hAnsi'):
                        if child.get(q(slot+'Theme')) is not None:
                            current.attrib.pop(q(slot),None)
                        elif child.get(q(slot)) is not None:
                            current.attrib.pop(q(slot+'Theme'),None)
            else:out[tag]=deepcopy(child)
    # Style toggle properties can toggle twice; restrict to simple inheritance, not guess.
    for tag in ('b','bCs','i','iCs'):
        style_values=[x.find(q(tag)).get(q('val'),'1') for x in layers
                      if x.getparent() is not None and x.getparent().tag==q('style') and x.find(q(tag)) is not None]
        positive=[v not in ('0','false','off') for v in style_values]
        if sum(positive)>1 or (any(positive) and any(not v for v in positive)):
            raise Unresolved('多层切换型字符属性，不能证明标题样式依赖保留')
    return out

def node_value(tag,e):
    if e is None:return DEFAULTS.get(tag)
    if len(e):return ET.tostring(e,method='c14n').decode()
    attrs={ET.QName(k).localname:v for k,v in e.attrib.items()}
    if tag in DEFAULTS and 'val' not in attrs:attrs['val']='1'
    if tag in DEFAULTS and attrs.get('val') in ('false','off'):attrs['val']='0'
    if tag in DEFAULTS and attrs.get('val') in ('true','on'):attrs['val']='1'
    return attrs

def formatting_snapshot(pkg,p):
    res=Resolver(pkg)
    pp=effective_nodes(res,res.layers(p,kind='pPr'),'pPr')
    output=[{tag:node_value(tag,pp.get(tag)) for tag in set(pp)|set(k for k in DEFAULTS if k in ('jc','keepNext','keepLines','pageBreakBefore','contextualSpacing','widowControl'))}]
    for r in p.findall(q('r')):
        nodes=effective_nodes(res,res.layers(p,r),'rPr')
        output.append({tag:node_value(tag,nodes.get(tag)) for tag in set(nodes)|set(k for k in DEFAULTS if k in ('b','bCs','i','iCs','color'))})
    return output

def style_plan(pkg,p,level):
    """换样式前生成冻结原有效格式的显式补丁，不能安全表达的差异阻止修正。"""
    from .engine import _ensure
    res=Resolver(pkg)
    if numbering_info(pkg,res,p)['present']:raise Unresolved('自动编号标题不生成Heading样式修改方案，需人工核对编号依赖')
    if not authentic(res,level):raise Unresolved('缺少可验证的内置Heading样式；不新增或改动共享样式')
    candidate=deepcopy(p)
    pp=_ensure(candidate,'pPr');_ensure(pp,'pStyle').set(q('val'),f'Heading{level}')
    _ensure(pp,'outlineLvl').set(q('val'),str(level-1))
    old=formatting_snapshot(pkg,p);new=formatting_snapshot(pkg,candidate)
    plan=[]
    for run,(left,right) in enumerate(zip(old,new)):
        for tag in sorted(set(left)|set(right)):
            a,b=left.get(tag),right.get(tag)
            if a==b:continue
            if tag not in {'rFonts','sz','szCs','b','bCs','i','iCs','color','spacing','jc','keepNext','keepLines','pageBreakBefore','widowControl','contextualSpacing'}:
                raise Unresolved('标题样式可能改变未支持保留的属性 '+tag+'；需人工复核')
            if a is None:a=DEFAULTS.get(tag)
            if not isinstance(a,dict):raise Unresolved('无法可靠保留缺失或复杂属性 '+tag)
            a=deepcopy(a)
            if tag=='spacing':
                for k in set(b or {})-set(a):
                    defaults={'line':'240','lineRule':'auto','before':'0','after':'0','beforeLines':'0','afterLines':'0','beforeAutospacing':'0','afterAutospacing':'0'}
                    if k not in defaults:raise Unresolved('无法保留间距属性 '+k)
                    a[k]=defaults[k]
            if tag=='rFonts':
                # Materialize effective slots; symbolically identical theme references are preserved.
                # Merging layers can retain an inactive lower-layer theme next to a
                # higher-layer literal font. Do not promote that theme into a direct override.
                for slot in ('eastAsia','ascii','hAnsi'):
                    if slot in a:a.pop(slot+'Theme',None)
                for slot,theme in [('eastAsia','eastAsiaTheme'),('ascii','asciiTheme'),('hAnsi','hAnsiTheme')]:
                    if (slot in (b or {}) or theme in (b or {})) and slot not in a and theme not in a:
                        raise Unresolved('原字体槽位缺失，无法安全保持标题样式依赖')
                if set(b or {})-set(a)-{'ascii','hAnsi','eastAsia','asciiTheme','hAnsiTheme','eastAsiaTheme'}:
                    raise Unresolved('特殊字体槽位不能安全保留')
            plan.append({'run':run,'tag':tag,'attrs':a,'reason':'冻结换Heading样式前的有效格式，保留未选属性'})
            parent=_ensure(candidate,'pPr') if run==0 else _ensure(candidate.findall(q('r'))[run-1],'rPr')
            e=_ensure(parent,tag);e.attrib.clear()
            for k,v in a.items():e.set(q(k),v)
    # Compare semantics of common defaults after adding explicit XML values.
    if not snapshots_equal(old,formatting_snapshot(pkg,candidate)):
        raise Unresolved('不能证明添加Heading样式后未选格式保持一致；禁止自动修正')
    return plan

def snapshots_equal(a,b):
    # A missing spacing attr has the standard known default only in this limited comparison.
    def normalized(snapshot):
        out=deepcopy(snapshot)
        for layer in out:
            if 'spacing' in layer and isinstance(layer['spacing'],dict):
                d={'line':'240','lineRule':'auto','before':'0','after':'0','beforeLines':'0','afterLines':'0','beforeAutospacing':'0','afterAutospacing':'0'}
                d.update(layer['spacing']);layer['spacing']=d
            # Literal fonts override a lower theme. Remove the inactive theme attribute.
            if 'rFonts' in layer and isinstance(layer['rFonts'],dict):
                for slot in ('ascii','hAnsi','eastAsia'):
                    if slot in layer['rFonts']:layer['rFonts'].pop(slot+'Theme',None)
        return out
    return normalized(a)==normalized(b)

def append_checks(report,pkg,manifest,rules):
    res=Resolver(pkg);findings=report['findings'];notes=report['coverage_notes']
    def add(rid,loc,actual,expected,status,detail='',plan=None,fixable=True):
        cfg=rules['rules'][rid];src=deepcopy(cfg.get('source') or {'file':rules['source_file'],'physical_page':cfg['page'],'quote':cfg['quote'],'interpretation':cfg.get('demo_interpretation')})
        obj=manifest['paragraph_types'].get(str(loc.get('paragraph')))
        property_sources=cfg.get('caption_sources',{}).get(obj,{}) if rid=='R12' else cfg.get('property_sources',{})
        if loc.get('property') in property_sources:src=deepcopy(property_sources[loc['property']])
        elif property_sources and loc.get('property')=='numbering_symbol':
            src={'file':None,'physical_page':None,'label':'编号符号只读对照（来源分开）',
                 'quote':'西文/数字字体沿用固定Times New Roman；字号取确认的本级标题值：'+property_sources['size']['quote']}
        elif (property_sources or cfg.get('caption_sources')) and loc.get('property') not in ('font_ascii','font_hAnsi'):
            pieces=list(property_sources.values()) or [v for group in cfg.get('caption_sources',{}).values() for v in group.values()]
            src={'file':None,'physical_page':None,'label':'用户确认的标题题注配置','quote':'；'.join(v['quote'] for v in pieces)}
        if rid in ('R08','R09','R10') and loc.get('property') in ('font_ascii','font_hAnsi'):
            src['quote']='各章题序的阿拉伯数字用Times New Roman体；英文单词字体为Times New Roman'
        f={'key':rid+':'+':'.join(f'{k}={v}' for k,v in loc.items()),'rule_id':rid,'rule_name':cfg['name'],'locator':loc,
           'actual':actual,'expected':expected,'status':status,'fixable':status=='problem' and fixable and not pkg.signed and not pkg.ambiguous_sections,'source':src,'detail':detail}
        if rid=='R12' and obj in ('figure_caption','table_caption'):f['object_type']=obj
        if plan is not None:f['preserved_format_patch']=plan;f['dependency_note']='只改变Heading引用和大纲；显式保留原有效格式（字体、间距等属性），不修改共享样式。'
        findings.append(f)
    seen=set()
    for key,typ in manifest['paragraph_types'].items():
        n=int(key);p=pkg.paragraphs[n-1];loc={'paragraph':n}
        if typ=='pending':
            notes.append({'locator':loc,'status':'review','detail':'人工分类仍标为待确认，未应用正文/标题/题注规则'});continue
        if not (typ.startswith('heading') or typ.endswith('_caption')):continue
        level=int(typ[-1]) if typ.startswith('heading') else None
        rid=f'R{7+level:02}' if level else 'R12';seen.add(rid)
        if level:seen.add('R11')
        expected=rules['rules'][rid]['expected']
        if not level and 'figure_caption' in expected:expected=expected[typ]
        unsafe=paragraph_unsafe(p)
        try:
            pl=res.layers(p,kind='pPr')
            numbering=numbering_info(pkg,res,p) if level else {'present':False}
            numbered=numbering['present']
            runs=[(i,r,res.layers(p,r)) for i,r in enumerate(p.findall(q('r')),1)]
            if any(len(layer.findall(q(tag)))>1 for layer in pl+[layer for _,_,layers in runs for layer in layers]
                   for tag in ('jc','outlineLvl','pStyle','keepNext','keepLines','color','b','szCs')):
                raise Unresolved('重复标题格式属性，无法可靠确定有效值')
        except Unresolved as exc:unsafe=str(exc);runs=[]
        if unsafe:
            add(rid,loc,{'unresolved':unsafe},expected,'review',unsafe)
            if level:add('R11',loc,{'unresolved':unsafe},{'style_id':f'Heading{level}','outline_level':level-1},'review',unsafe)
            notes.append({'locator':loc,'status':'review','detail':unsafe});continue
        if numbered:
            proof=public_numbering(numbering)
            # Numbering pPr indentation/tabs are not title alignment/line/font properties.
            np=numbering.get('paragraph_properties')
            if np is not None and any(e.tag not in (q('ind'),q('tabs')) for e in np):
                numbering['paragraph_conflict']='编号层级含对齐/行距等段落属性，跨软件继承顺序待复核'
            if numbering['status']=='resolved':
                rp=numbering.get('symbol_properties')
                sl=[rp] if rp is not None else []
                si=res.font_info(sl,'ascii')
                if si['font'] is None and '槽位在' in si.get('reason',''):
                    si['reason']='编号层级rPr未明确指定ASCII字体；段落标记/符号继承尚未解析，不借用标题文字或docDefaults作编号字体证明'
                symbol_complex=(rp is not None and rp.find(q('rStyle')) is not None) or any(res.value(sl,tag,'0') not in ('0','false','off') for tag in ('rtl','cs','position')) or res.value(sl,'vertAlign','baseline')!='baseline'
                if symbol_complex:si={'font':None,'reason':'编号符号含字符样式依赖、复杂文字或基线格式，不能按ASCII判定'}
                symbol={'font':si['font'],'size_pt':res.size(sl)}
                why=si.get('reason','编号符号属性在独立lvl/rPr中读取；未指定字体/字号时不按标题文字格式补值')
                status='review' if symbol['font'] is None or symbol['size_pt'] is None else 'pass' if same_font(symbol['font'],'Times New Roman') and symbol['size_pt']==expected['size_pt'] else 'problem'
            else:
                symbol={'unresolved':numbering['reason']};si={};status='review';why=numbering['reason']+'；标题普通文字仍独立检查'
            add(rid,{'paragraph':n,'property':'numbering_symbol'},symbol,{'font':'Times New Roman','pt':expected['size_pt']},status,why,fixable=False)
            findings[-1]['numbering_evidence']=proof;findings[-1]['font_evidence']={'ascii':si} if si else {}
            notes.append({'locator':{'paragraph':n,'property':'numbering_symbol'},'status':'review','detail':'自动编号符号与序列未纳入自动修正；'+why,'numbering_evidence':proof,
                          'action':'在Word选中编号符号核对字体、字号及序列；不要用标题文字样式作为符号字体证明'})
        special=False;ordinary=0
        for i,r,layers in runs:
            text=''.join(r.xpath('.//w:t/text()',namespaces=NS));reason=res.special(r,layers)
            if reason:
                special=True;notes.append({'locator':{'paragraph':n,'run':i},'status':'review','detail':reason+'；特殊run未修改'});continue
            if not text.strip():continue
            ordinary+=1;cn,slots,unknown=scripts(text);wanted={slot:expected['font_latin'] for slot in slots}
            if cn:wanted['eastAsia']=expected['font_cn']
            for slot,value in wanted.items():
                proof=res.font_info(layers,slot,text)
                actual=proof['font'] if proof['font'] is not None else {'unresolved':proof['reason'],'slot':slot}
                add(rid,{'paragraph':n,'run':i,'property':'font_'+slot}, {'slot':slot,'font':actual},{'slot':slot,'font':value},
                    'review' if actual is None or isinstance(actual,dict) else 'pass' if same_font(actual,value) else 'problem',proof.get('reason',''),fixable=proof['safe_to_fix_slot'])
                findings[-1]['font_evidence']={slot:proof}
            actual=res.size(layers)
            add(rid,{'paragraph':n,'run':i,'property':'size'}, {'pt':actual},{'pt':expected['size_pt']},'review' if actual is None else 'pass' if actual==expected['size_pt'] else 'problem')
            if unknown:notes.append({'locator':{'paragraph':n,'run':i},'status':'review','detail':'标题/题注含未知字符槽位，字体未验证'})
        if not ordinary:add(rid,loc,{'unresolved':'没有普通文字'},expected,'review','没有可安全处理的普通文字')
        if not level:continue # Caption spacing/indent and position/number are deliberately untouched.
        numbered_paragraph_pending=numbered and (numbering['status']!='resolved' or bool(numbering.get('paragraph_conflict')))
        alignment=res.value(pl,'jc','left')
        add(rid,{'paragraph':n,'property':'alignment'},{'alignment':alignment},{'alignment':expected['alignment']},'review' if special or numbered_paragraph_pending else 'pass' if alignment==expected['alignment'] else 'problem',('编号段落对齐属性：'+numbering.get('paragraph_conflict',numbering.get('reason',''))+'；文字字体字号仍独立检查') if numbered_paragraph_pending else '混有特殊run，不自动修改段落格式' if special else '')
        findings[-1]['paragraph_evidence']={'inheritance_path':[res._layer_origin(x) for x in pl],'numbering':public_numbering(numbering) if numbered else None}
        attrs=res.attrs(pl,'spacing')
        try:line=float(attrs.get('line',240));mode=attrs.get('lineRule','auto');multiple=line/240 if mode=='auto' else None
        except (TypeError,ValueError):line=None;mode='invalid';multiple=None
        grid=any(s.find(q('docGrid')) is not None and s.find(q('docGrid')).get(q('type')) in ('lines','linesAndChars','snapToChars') for s in pkg.sections)
        if line is not None and not math.isfinite(line):line=None;multiple=None
        pending=special or (numbered and isinstance(expected['line_multiple'],dict)) or (numbered and (numbering['status']!='resolved' or numbering.get('paragraph_conflict'))) or mode not in ('auto','exact','atLeast') or line is None or line<=0 or (grid and res.value(pl,'snapToGrid','1') not in ('0','false','off'))
        add(rid,{'paragraph':n,'property':'line'}, {'line_rule':mode,'multiple':multiple,'pt':line/20 if line is not None and mode in ('exact','atLeast') else None}, {'multiple':expected['line_multiple']},
            'review' if pending else 'pass' if __import__('core.paragraph_values',fromlist=['line_equal']).line_equal({'line_rule':mode,'multiple':multiple,'pt':line/20 if mode!='auto' else None},expected['line_multiple']) else 'problem',('编号段落行距：'+numbering.get('paragraph_conflict',numbering.get('reason',''))+'；文字字体字号仍独立检查') if numbered_paragraph_pending else '特殊run/文档网格或异常行距，禁止自动修改' if pending else '')
        findings[-1]['paragraph_evidence']={'inheritance_path':[res._layer_origin(x) for x in pl],'numbering':public_numbering(numbering) if numbered else None}
        sid=p.find('w:pPr/w:pStyle',NS);sid=sid.get(q('val')) if sid is not None else None
        raw=res.value(pl,'outlineLvl')
        actual={'style_id':sid,'outline_level':int(raw) if raw is not None and raw.isdigit() else raw}
        exp={'style_id':f'Heading{level}','outline_level':level-1}
        if sid==exp['style_id'] and authentic(res,level) and actual['outline_level']==level-1:
            add('R11',loc,actual,exp,'pass')
        elif numbered:
            add('R11',loc,actual,exp,'problem','实际Heading样式/大纲与确认类型不符；numPr绑定编号，切换样式可能改变层级、起点或连续性，本阶段不可自动修正。请在Word人工核对样式与编号联动。',fixable=False)
            findings[-1]['numbering_evidence']=public_numbering(numbering)
        elif special:add('R11',loc,actual,exp,'review','混有特殊run，不切换标题样式')
        else:
            try:plan=style_plan(pkg,p,level);add('R11',loc,actual,exp,'problem',plan=plan)
            except Unresolved as exc:add('R11',loc,actual,exp,'review',str(exc))
    for rid in EXT_IDS:
        if rid not in seen:add(rid,{'document':1},None,rules['rules'][rid]['expected'],'not_applicable','本次确认分类中没有该类对象，不凭空报错')
    coverage=report['coverage'];coverage['paragraph_types']=deepcopy(manifest['paragraph_types']);coverage['classification_confirmation']=manifest['confirmation']
    coverage['confirmed_typed_paragraphs']=[int(n) for n,t in manifest['paragraph_types'].items() if t not in ('other','pending')]
    coverage['unconfirmed_paragraphs']=[int(n) for n,t in manifest['paragraph_types'].items() if t=='pending']
    if rules.get('mode')!='academic':
        from .academic_rules import NEW_TYPES
        for n,t in manifest['paragraph_types'].items():
            if t in NEW_TYPES:notes.append({'locator':{'paragraph':int(n)},'status':'review','detail':'该前后置类型未在当前模式检查；请使用单文档扩展模式并配置规则'})
    coverage['excluded']='其他/待确认段落、表格内格式、页眉页脚、脚注/文本框；特殊结构继续保护。不检查题注位置、编号及全文合格。'
    report['schema_version']=2;report['rules'].update(mode='extended',body_config_sha256=rules['body_config_sha256'],extension_sha256=rules['extension_sha256'])
    refresh_summary(report,len(rules['rules']))

def refresh_summary(report,count):
    s=report['summary'];fs=report['findings'];notes=report['coverage_notes']
    for name in ('problem','pass','not_applicable'):s[name+'_count']=sum(f['status']==name for f in fs)
    s['review_findings']=sum(f['status']=='review' for f in fs);s['review_notes']=len(notes);s['review_count']=s['review_findings']+len(notes)
    s['rule_count']=count;s['applicable_rule_count']=len({f['rule_id'] for f in fs if f['status']!='not_applicable'})
    s['conclusion']='已覆盖检查发现问题' if s['problem_count'] else '已覆盖检查未发现问题'

def apply_extended(pkg,f):
    from .engine import _ensure
    p=pkg.paragraphs[f['locator']['paragraph']-1];loc=f['locator'];expected=f['expected']
    if f['rule_id']=='R11':
        if numbering_info(pkg,Resolver(pkg),p)['present']:raise DemoError('自动编号标题不允许自动切换Heading样式')
        pp=_ensure(p,'pPr');_ensure(pp,'pStyle').set(q('val'),expected['style_id']);_ensure(pp,'outlineLvl').set(q('val'),str(expected['outline_level']))
        for patch in f.get('preserved_format_patch',[]):
            parent=pp if patch['run']==0 else _ensure(p.findall(q('r'))[patch['run']-1],'rPr')
            e=_ensure(parent,patch['tag']);e.attrib.clear()
            for k,v in patch['attrs'].items():e.set(q(k),v)
    elif loc['property'].startswith('font_'):
        rp=_ensure(p.findall(q('r'))[loc['run']-1],'rPr');rf=_ensure(rp,'rFonts');slot=expected['slot']
        rf.set(q(slot),expected['font']);rf.attrib.pop(q(slot+'Theme'),None)
    elif loc['property']=='size':_ensure(_ensure(p.findall(q('r'))[loc['run']-1],'rPr'),'sz').set(q('val'),str(round(expected['pt']*2)))
    elif loc['property']=='alignment':_ensure(_ensure(p,'pPr'),'jc').set(q('val'),expected['alignment'])
    elif loc['property']=='line':
        from .paragraph_values import apply
        apply(p,'line_spacing',expected['multiple'])

def mask_extended(p,f):
    loc=f['locator'];targets=[]
    if f['rule_id']=='R11':
        targets=[(p.find('w:pPr/w:pStyle',NS),['val']),(p.find('w:pPr/w:outlineLvl',NS),['val'])]
        for patch in f.get('preserved_format_patch',[]):
            parent=p.find(q('pPr')) if patch['run']==0 else p.findall(q('r'))[patch['run']-1].find(q('rPr'))
            e=parent.find(q(patch['tag'])) if parent is not None else None
            # All attributes of this known format node may be copied to freeze effective inheritance.
            if e is not None:targets.append((e,[ET.QName(k).localname for k in e.attrib]))
    else:
        prop=loc['property'];parent=p.find(q('pPr')) if 'run' not in loc else p.findall(q('r'))[loc['run']-1].find(q('rPr'))
        tag,attrs=('rFonts',[f['expected']['slot'],f['expected']['slot']+'Theme']) if prop.startswith('font_') else ('sz',['val']) if prop=='size' else ('jc',['val']) if prop=='alignment' else ('spacing',['line','lineRule'])
        targets=[(parent.find(q(tag)) if parent is not None else None,attrs)]
    for e,attrs in targets:
        if e is not None:
            for attr in attrs:e.attrib.pop(q(attr),None)
            if not len(e) and not e.attrib and not e.text:
                e.getparent().remove(e)

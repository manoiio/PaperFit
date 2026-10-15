"""W01/W02独立几何检查；不推断实际分页/像素，不计入格式规则统计。"""
from copy import deepcopy
import json
from pathlib import Path
from lxml import etree as E
from .package import Package, DemoError, q, NS, parse, sha256, new_path, write_new
from .formats import Resolver, Unresolved, paragraph_unsafe
from .engine import _rules, _confirmed_scope, _check, _ensure
from .dependencies import problem_delta

WP='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
PIC='http://schemas.openxmlformats.org/drawingml/2006/picture'
VERSION='width-1.0'
LIMIT='仅比较DOCX声明的几何尺寸，不证明渲染位置、分页或全文排版合格。缩小后可能增加换行和页数；图片高度及题注同页另行预览。'
MIN_COLUMN=10*1440/25.4  # 课程原型保护下限10mm，并非学校规则。

def _int(v,positive=False):
    try:
        if not isinstance(v,str) or not v.lstrip('-').isdigit():raise ValueError()
        n=int(v)
        if abs(n)>1000000000 or (positive and n<=0):raise ValueError()
        return n
    except (ValueError,TypeError):raise Unresolved('几何尺寸缺失、非法或超范围') from None

def _one(e,path,required=False):
    es=e.findall(path,NS)
    if len(es)>1 or (required and not es):raise Unresolved('几何属性重复或缺失：'+path)
    return es[0] if es else None

def _mm(twips):return twips*25.4/1440

def _sections(pkg):
    body=pkg.root.find(q('body'));mapping={};pending=[];number=0
    if pkg.ambiguous_sections:raise Unresolved('非顶层或修订分节，无法可靠确定对象所在节')
    if len(body.findall(q('sectPr')))!=1 or body[-1].tag!=q('sectPr'):raise Unresolved('末节属性不唯一或位置异常，待复核')
    for obj in body:
        if obj.tag==q('sectPr'):sp=obj
        else:
            pending.append(obj);sp=_one(obj,'w:pPr/w:sectPr') if obj.tag==q('p') else None
        if sp is not None:
            number+=1
            for item in pending:mapping[item]=(number,sp)
            pending=[]
    if pending or number==0:raise Unresolved('缺少末节属性，无法确定对象所在节')
    return mapping

def _page(pkg,num,sp):
    if sp.find(q('sectPrChange')) is not None:raise Unresolved('分节属性修订，待复核')
    settings=parse(pkg.parts.get('word/settings.xml',b'<w:settings xmlns:w="'+NS['w'].encode()+b'"/>'))
    if any(settings.find(q(k)) is not None for k in ('mirrorMargins','gutterAtTop','bookFoldPrinting','bookFoldRevPrinting')):raise Unresolved('镜像边距、顶部装订或书籍折页暂不支持')
    if sp.find(q('rtlGutter')) is not None:raise Unresolved('右侧/复杂装订设置暂不支持')
    cols=_one(sp,'w:cols')
    if cols is not None and (cols.get(q('num'),'1')!='1' or len(cols)):raise Unresolved('多栏或自定义分栏，待复核')
    size=_one(sp,'w:pgSz',True);mar=_one(sp,'w:pgMar',True)
    width=_int(size.get(q('w')),True);left=_int(mar.get(q('left')));right=_int(mar.get(q('right')));gutter=_int(mar.get(q('gutter'),'0'))
    if min(left,right,gutter)<0:raise Unresolved('负边距或装订线，待复核')
    usable=width-left-right-gutter
    if usable<=0:raise Unresolved('页面没有正的可用宽度')
    return {'section':num,'page_width_twips':width,'left_margin_twips':left,'right_margin_twips':right,'gutter_twips':gutter,'body_width_twips':usable,
            'page_width_mm':_mm(width),'left_margin_mm':_mm(left),'right_margin_mm':_mm(right),'gutter_mm':_mm(gutter),'body_width_mm':_mm(usable)}

def _table(pkg,t,page):
    if t.xpath('.//w:tbl|.//w:tblpPr|.//w:ins|.//w:del|.//w:sdt|.//w:customXml|.//w:tblPrChange|.//w:tcPrChange|.//w:trPrChange|.//w:tblPrEx',namespaces=NS):raise Unresolved('嵌套、浮动、修订或包裹表格不适配')
    direct=_one(t,'w:tblPr',True);pr=E.Element(q('tblPr'));grid=_one(t,'w:tblGrid',True)
    style=_one(direct,'w:tblStyle')
    resolver=Resolver(pkg)
    if style is None and 'table' in resolver.conflicting_defaults:raise Unresolved('默认表格样式冲突，待复核')
    style_id=style.get(q('val')) if style is not None else resolver.default_styles.get('table')
    if style_id:
        for st in resolver.chain(style_id,'table'):
            if st.xpath('.//w:tblStylePr//w:tblW|.//w:tblStylePr//w:tblInd|.//w:tblStylePr//w:tblLayout|.//w:tcW|.//w:tblpPr',namespaces=NS):raise Unresolved('表格样式含条件几何尺寸，待复核')
            layer=st.find(q('tblPr'))
            if layer is not None:
                for child in layer:
                    for old in pr.findall(child.tag):pr.remove(old)
                    pr.append(deepcopy(child))
    for child in direct:
        if len(direct.findall(child.tag))>1:raise Unresolved('重复表格属性，待复核')
        for old in pr.findall(child.tag):pr.remove(old)
        pr.append(deepcopy(child))
    if pr.find(q('bidiVisual')) is not None or pr.find(q('tblCellSpacing')) is not None:raise Unresolved('双向表格或单元格间距，待复核')
    ind=_one(pr,'w:tblInd');indent=0
    if ind is not None:
        if ind.get(q('type'))!='dxa':raise Unresolved('非绝对表格缩进，待复核')
        indent=_int(ind.get(q('w')))
        if indent<0:raise Unresolved('负表格缩进，待复核')
    jc=_one(pr,'w:jc');align=jc.get(q('val')) if jc is not None else 'left'
    if align not in ('left','center','right') or (indent and align!='left'):raise Unresolved('表格对齐与缩进影响无法可靠确定')
    available=page['body_width_twips']-indent
    if available<=0:raise Unresolved('缩进后无可用宽度')
    cols=[_int(e.get(q('w')),True) for e in grid]
    if not cols or any(e.tag!=q('gridCol') for e in grid):raise Unresolved('网格缺失或复杂网格')
    rows=t.findall(q('tr'))
    if not rows:raise Unresolved('空表格')
    for row in rows:
        if row.xpath('w:trPr/w:trHeight[@w:hRule="exact"]',namespaces=NS):raise Unresolved('已有固定行高，缩窄可能裁切文字；需人工处理')
        if row.find('w:trPr/w:gridBefore',NS) is not None or row.find('w:trPr/w:gridAfter',NS) is not None:raise Unresolved('行前后省略网格，不适配')
        cells=row.findall(q('tc'))
        if len(cells)!=len(cols):raise Unresolved('合并或不完整网格，待复核')
        for cell,cw in zip(cells,cols):
            if cell.xpath('w:tcPr/w:gridSpan|w:tcPr/w:vMerge|w:tcPr/w:hMerge',namespaces=NS):raise Unresolved('合并表格首版只人工复核，不重建')
            width=_one(cell,'w:tcPr/w:tcW',True)
            if width.get(q('type'))!='dxa' or abs(_int(width.get(q('w')),True)-cw)>1:raise Unresolved('单元格宽度与网格冲突或非绝对宽度，待复核')
            if cell.xpath('.//w:fldChar|.//w:fldSimple|.//w:drawing|.//w:pict|.//w:object|.//w:altChunk',namespaces=NS):raise Unresolved('表格含字段、图片或复杂对象，待复核')
    width=_one(pr,'w:tblW');typ=width.get(q('type')) if width is not None else 'auto';total=sum(cols)
    layout=_one(pr,'w:tblLayout');layout=layout.get(q('type')) if layout is not None else 'autofit'
    if layout not in ('fixed','autofit'):raise Unresolved('未知自动调整方式')
    adaptation=True;reason='表格、网格与单元格声明一致；仍是首选几何宽度，不代表实际可见宽度'
    if typ=='dxa':
        declared=_int(width.get(q('w')),True)
        if abs(declared-total)>len(cols):raise Unresolved('tblW与网格总宽度冲突，待复核')
    elif typ=='auto':
        if width is not None and width.get(q('w'),'0')!='0':raise Unresolved('自动宽度含非零值，待复核')
        declared=total;reason='自动宽度：一致的网格/单元格声明有宽度风险，最终宽度仍由排版器决定；适配须确认改为固定列宽'
    elif typ=='pct':
        pct=_int(width.get(q('w')),True)
        if pct>30000:raise Unresolved('百分比宽度超范围')
        declared=page['body_width_twips']*pct/5000
        if abs(declared-total)>len(cols):raise Unresolved('百分比首选宽度与网格/单元格冲突，待复核')
        adaptation=False;reason=f'百分比首选宽度{pct/50:g}%，相对正文区；本阶段只读，不自动转换百分比表格'
    else:raise Unresolved('未知或nil表格宽度，待复核')
    target=int(available);scaled=_scale(cols,target)
    if min(scaled)<MIN_COLUMN:adaptation=False;reason+='；缩小后列小于10mm原型保护下限，请人工调整内容/方向'
    return {'available_twips':available,'object_twips':declared,'grid_twips':cols,'width_type':typ,'layout':layout,'alignment':align,'indent_twips':indent,'rows':len(rows),'columns':len(cols),
            'fixable':adaptation,'reason':reason,'plan':{'target_twips':target,'columns_before_twips':cols,'columns_after_twips':scaled,'autofit_to_fixed':layout!='fixed','width_type_after':'dxa'}}

def _table_ensure(pr,tag):
    e=pr.find(q(tag))
    if e is not None:return e
    order=['tblStyle','tblpPr','tblOverlap','bidiVisual','tblStyleRowBandSize','tblStyleColBandSize','tblW','jc','tblCellSpacing','tblInd','tblBorders','shd','tblLayout','tblCellMar','tblLook','tblCaption','tblDescription','tblPrChange']
    e=E.Element(q(tag));at=order.index(tag)
    for i,child in enumerate(pr):
        if child.tag in [q(n) for n in order[at+1:]]:pr.insert(i,e);return e
    pr.append(e);return e

def _scale(cols,target):
    total=sum(cols);out=[c*target//total for c in cols];left=target-sum(out)
    order=sorted(range(len(cols)),key=lambda i:(cols[i]*target%total,-i),reverse=True)
    for i in order[:left]:out[i]+=1
    return out

def _image(pkg,p,inline,page):
    from .layout import _pair_reason
    # Reuse media/ordinary-picture relation protection without requiring an actual caption.
    c=E.Element(q('p'));E.SubElement(E.SubElement(c,q('r')),q('t')).text='校验占位'
    reason=_pair_reason(pkg,p,c)
    if reason and not reason.startswith('现有分页'):raise Unresolved(reason)
    if paragraph_unsafe(p):raise Unresolved('复杂图片段落，待复核')
    res=Resolver(pkg);layers=res.layers(p,kind='pPr');indent={}
    for layer in layers:
        e=_one(layer,'w:ind')
        if e is not None:indent.update(e.attrib)
        if layer.find(q('numPr')) is not None or layer.find(q('framePr')) is not None:raise Unresolved('图片段编号或浮动框架，待复核')
    if set(indent)-{q('left'),q('right'),q('firstLine'),q('hanging')}:raise Unresolved('字符或逻辑缩进对图片宽度影响待复核')
    left=_int(indent.get(q('left'),'0'));right=_int(indent.get(q('right'),'0'));first=_int(indent.get(q('firstLine'),'0'));hanging=_int(indent.get(q('hanging'),'0'))
    if min(left,right,first,hanging)<0 or (first and hanging):raise Unresolved('负或冲突图片段缩进')
    # Only one inline run; reserve positive first-line offset. Hanging may place it outside body => review.
    if hanging:raise Unresolved('图片段悬挂缩进，待复核')
    usable=page['body_width_twips']-left-right-first
    exts=inline.findall('{'+WP+'}extent');inner=inline.findall('.//{'+PIC+'}spPr/{'+A+'}xfrm/{'+A+'}ext')
    if len(exts)!=1 or len(inner)!=1:raise Unresolved('图片内外尺寸缺失或不唯一')
    xfrm=inner[0].getparent()
    if any(xfrm.get(k,'0') not in ('0','false') for k in ('rot','flipH','flipV')):raise Unresolved('旋转/翻转图片首版待复核')
    effect=inline.find('{'+WP+'}effectExtent')
    if effect is not None and any(_int(v)!=0 for v in effect.attrib.values()):raise Unresolved('图片效果扩展影响宽度，待复核')
    w=_int(exts[0].get('cx'),True);h=_int(exts[0].get('cy'),True)
    if (_int(inner[0].get('cx'),True),_int(inner[0].get('cy'),True))!=(w,h):raise Unresolved('图片内外尺寸冲突，待复核')
    if usable<=0:raise Unresolved('图片段缩进后无可用宽度')
    target=usable*635
    return {'available_twips':usable,'object_twips':w/635,'width_type':'inline_emu','fixable':True,'reason':'普通内嵌图片内外尺寸一致；仅等比例缩小，不放大；裁剪与媒体字节保留',
            'indent_twips':left+right+first,'plan':{'before_emu':[w,h],'after_emu':[target,round(h*target/w)],'autofit_to_fixed':False}}

def check_widths(input_path,*,rules_sha256=None):
    pkg=Package(input_path);rows=[];body=pkg.root.find(q('body'));tables=0;pn=0
    try:mapping=_sections(pkg);mapping_error=None
    except Unresolved as e:mapping={};mapping_error=str(e)
    for position,obj in enumerate(body,1):
        if obj.tag==q('p'):pn+=1
        is_table=obj.tag==q('tbl');drawings=obj.xpath('.//w:drawing|.//w:pict|.//w:object',namespaces=NS) if obj.tag==q('p') else []
        if not is_table and not drawings:continue
        if is_table:tables+=1
        row={'key':f'W01:table={tables}' if is_table else f'W02:paragraph={pn}','id':'W01' if is_table else 'W02','kind':'table' if is_table else 'image','body_object':position,
             'locator':{'table':tables} if is_table else {'paragraph':pn},'status':'review','fixable':False,'section':None,'basis':None,'reason':'','plan':None}
        try:
            if mapping_error:raise Unresolved(mapping_error)
            num,sp=mapping[obj];row['section']=num;page=_page(pkg,num,sp);row['basis']=page
            if is_table:data=_table(pkg,obj,page)
            else:
                ins=obj.findall('.//{'+WP+'}inline')
                if len(ins)!=1 or len(drawings)!=1 or obj.findall('.//{'+WP+'}anchor') or obj.findall('.//'+q('pict')):raise Unresolved('仅支持单一普通内嵌图片；浮动/VML/组合/多图待复核')
                data=_image(pkg,obj,ins[0],page)
            row.update(data);row['available_mm']=_mm(data['available_twips']);row['declared_width_mm']=_mm(data['object_twips']);row['excess_mm']=max(0,_mm(data['object_twips']-data['available_twips']))
            row['status']='risk' if data['object_twips']>data['available_twips']+1 else 'pass';row['fixable']=row['fixable'] and row['status']=='risk'
        except (Unresolved,KeyError) as e:row['reason']=str(e)
        if pkg.signed:row['fixable']=False;row['reason']+='；签名文档不修改'
        rows.append(row)
    report={'version':VERSION,'input_sha256':pkg.hash,'rules_sha256':rules_sha256,'objects':rows,'summary':{'risks':sum(r['status']=='risk' for r in rows),'reviews':sum(r['status']=='review' for r in rows),'passes':sum(r['status']=='pass' for r in rows)},'limitation':LIMIT}
    report['plan_sha256']=sha256(json.dumps(report,sort_keys=True,ensure_ascii=False).encode())
    return report

def _mask(pkg,rows):
    root=deepcopy(pkg.root);body=root.find(q('body'))
    for row in rows:
        obj=body[row['body_object']-1]
        if row['kind']=='table':
            pr=obj.find(q('tblPr'))
            for tag in ('tblW','tblLayout'):
                for e in pr.findall(q(tag)):pr.remove(e)
            for e in obj.findall('w:tblGrid/w:gridCol',NS):e.attrib.pop(q('w'),None)
            for e in obj.findall('w:tr/w:tc/w:tcPr/w:tcW',NS):
                e.attrib.pop(q('w'),None);e.attrib.pop(q('type'),None)
        else:
            inline=obj.find('.//{'+WP+'}inline')
            for e in [inline.find('{'+WP+'}extent'),inline.find('.//{'+PIC+'}spPr/{'+A+'}xfrm/{'+A+'}ext')]:
                e.attrib.pop('cx',None);e.attrib.pop('cy',None)
    return E.tostring(root,method='c14n')

def apply_width_adaptation(input_path,output_path,body=None,rules_path=None,*,custom_rules_path=None,mode='basic',classification_manifest=None,plan=None,selected_keys=(),confirmed_fixed_keys=()):
    destination=new_path(output_path,input_path)
    if destination.suffix.lower()!='.docx':raise DemoError('输出必须为新DOCX')
    pkg=Package(input_path);rules=_rules(rules_path,custom_rules_path,mode);scope,classification=_confirmed_scope(pkg,body,mode,classification_manifest)
    before_width=check_widths(input_path,rules_sha256=rules['sha256'])
    if plan!=before_width:raise DemoError('尺寸计划与文件或规则不匹配，请重新检查并确认')
    eligible={r['key']:r for r in before_width['objects'] if r['fixable']}
    keys=list(selected_keys);fixed=list(confirmed_fixed_keys)
    if not keys or any(type(k)!=str for k in keys+fixed) or len(set(keys))!=len(keys) or len(set(fixed))!=len(fixed) or set(keys)-set(eligible) or set(fixed)-set(keys):raise DemoError('须选择当前可安全适配的超宽对象，待复核及正常对象不执行')
    chosen=[eligible[k] for k in keys]
    if any(r['plan']['autofit_to_fixed'] and r['key'] not in fixed for r in chosen):raise DemoError('须明确确认所选表格由自动调整改为固定列宽')
    baseline=_mask(pkg,chosen);before=_check(pkg,scope,rules,classification);changes=[]
    for row in chosen:
        obj=pkg.root.find(q('body'))[row['body_object']-1];p=row['plan']
        if row['kind']=='table':
            pr=obj.find(q('tblPr'));w=_table_ensure(pr,'tblW');w.set(q('type'),'dxa');w.set(q('w'),str(p['target_twips']));_table_ensure(pr,'tblLayout').set(q('type'),'fixed')
            for e,c in zip(obj.findall('w:tblGrid/w:gridCol',NS),p['columns_after_twips']):e.set(q('w'),str(c))
            for tr in obj.findall(q('tr')):
                for tc,c in zip(tr.findall(q('tc')),p['columns_after_twips']):
                    w=tc.find('w:tcPr/w:tcW',NS);w.set(q('type'),'dxa');w.set(q('w'),str(c))
            old={'width_mm':row['declared_width_mm'],'columns_twips':p['columns_before_twips'],'layout':row['layout']};new={'width_mm':_mm(p['target_twips']),'columns_twips':p['columns_after_twips'],'layout':'fixed'}
        else:
            inline=obj.find('.//{'+WP+'}inline')
            for e in [inline.find('{'+WP+'}extent'),inline.find('.//{'+PIC+'}spPr/{'+A+'}xfrm/{'+A+'}ext')]:
                e.set('cx',str(p['after_emu'][0]));e.set('cy',str(p['after_emu'][1]))
            old={'size_emu':p['before_emu']};new={'size_emu':p['after_emu']}
        changes.append({'key':row['key'],'rule_id':row['id'],'locator':row['locator'],'before':old,'after':new,'verification':'pass','source':{'label':'用户确认的宽度辅助（非学校格式规则）','quote':'按所在节及对象缩进后可用宽度，等比例缩小所选对象；不改内容'}})
    if baseline!=_mask(pkg,chosen) or Path(input_path).read_bytes()!=pkg.raw:raise DemoError('修改超出已确认尺寸属性，未写输出')
    write_new(destination,pkg.bytes(True),input_path)
    try:
        saved=Package(destination);m=deepcopy(classification)
        if m is not None:m['input_sha256']=saved.hash;__import__('core.table_text',fromlist=['rebind']).rebind(m,saved.hash)
        after=_check(saved,scope,rules,m);after_width=check_widths(destination,rules_sha256=rules['sha256']);lookup={r['key']:r for r in after_width['objects']}
        preserved=baseline==_mask(saved,chosen);others=set(saved.parts)==set(pkg.parts) and all(saved.parts[n]==b for n,b in pkg.parts.items() if n!='word/document.xml');original=Path(input_path).read_bytes()==pkg.raw
        if not preserved or not others or not original or any(lookup[k]['status']!='pass' for k in keys):raise DemoError('尺寸落盘复查或完整性验证失败')
    except Exception:
        destination.unlink();raise
    return {'kind':'width_adaptation','output':str(destination),'before':before,'after':after,'changes':changes,'problem_delta':problem_delta(before,after),'skipped_review_keys':[],
            'widths':{'before':before_width,'after':after_width,'selected_keys':keys,'message':'已设置所选对象适配宽度并读回尺寸','limitation':LIMIT,'visual_status':'not_reviewed'},
            'output_body_manifest':{'input_sha256':saved.hash,'body_paragraphs':scope,'confirmation':'沿用确认范围，仅所选尺寸属性修改且结构保留验证通过'},
            **({'output_classification_manifest':m} if m else {}),
            'preservation':{'original_sha256_unchanged':original,'document_except_selected_format_attributes_equal':preserved,'other_zip_member_bytes_equal':others,
            'verified_objects':'完整主文档仅掩码所选tblW/tblLayout/gridCol宽度/tcW或图片内外extent尺寸；其他ZIP字节、媒体、裁剪、编号、分页属性、分节、表格文字及合并/边框保留。'}}

def width_markdown(report):
    lines=['# 页面可用宽度检查（独立布局）','',f"输入哈希：{report['input_sha256']}",f"规则哈希：{report['rules_sha256']}",f"几何算法：{report['version']}",'',report['limitation'],'','| 对象 | 节 | 可用mm | 声明mm | 超出mm | 状态/依据 |','| --- | --- | --- | --- | --- | --- |']
    for r in report['objects']:
        val=lambda k: f'{r[k]:.3f}' if k in r else '未确定'
        lines.append(f"| {r['key']} | {r['section']} | {val('available_mm')} | {val('declared_width_mm')} | {val('excess_mm')} | {r['status']} · {r['reason']} |")
        if r['basis']:lines+=['','计算依据：'+json.dumps(r['basis'],ensure_ascii=False)]
    return '\n'.join(lines)+'\n'

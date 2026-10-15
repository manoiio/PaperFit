"""L01产品辅助：只设置明确确认的紧邻内嵌图片/图题分页属性，不检测跨页。"""
from copy import deepcopy
from pathlib import Path
from lxml import etree as ET
from .package import Package, DemoError, q, NS, sha256, new_path, write_new
from .classification import validate_classification
from .formats import Resolver, Unresolved, paragraph_unsafe
from .engine import _rules, _confirmed_scope, _check, _ensure, _text
from .dependencies import problem_delta

WP='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
SOURCE={'label':'产品辅助L01（用户确认）','quote':'图片段keep-with-next；紧邻已确认图题keep-lines。表达相邻意图，不保证实际同页。'}
LIMIT='未检测实际分页；图片与题注整体过高、强制分页或不同渲染器仍可能跨页。请生成预览并人工查看。'

def _flag(pkg,p,tag):
    layers=Resolver(pkg).layers(p,kind='pPr')
    for layer in layers:
        es=layer.findall(q(tag))
        if len(es)>1:raise Unresolved('重复分页属性')
        if es and (set(es[0].attrib)-{q('val')} or len(es[0])):raise Unresolved('复杂分页属性')
    val=Resolver(pkg).value(layers,tag,'0')
    if val not in ('0','false','off','1','true','on'):raise Unresolved('无法解析分页属性')
    return val in ('1','true','on')

def _pair_reason(pkg,p,c):
    if pkg.signed or pkg.ambiguous_sections:return '签名或复杂分节，不支持辅助修改'
    if paragraph_unsafe(p):return '图片段含修订、框架或未支持结构，待复核'
    if _text(p).strip():return '图片段混有文字，待复核'
    if len(p.findall(q('r')))!=1 or any(x.tag not in (q('pPr'),q('r')) for x in p):return '不是普通单一图片段，待复核'
    if len(p.xpath('.//w:drawing',namespaces=NS))!=1 or len(p.findall('.//{'+WP+'}inline'))!=1 or p.findall('.//{'+WP+'}anchor'):return '仅支持单一普通内嵌图片；浮动、多图待复核'
    for run in p.findall(q('r')):
        if any(x.tag not in (q('rPr'),q('drawing')) for x in run):return '图片段含复杂结构，待复核'
    inline=p.find('.//{'+WP+'}inline')
    if len(inline.findall('.//{'+A+'}blip'))!=1 or inline.find('.//{'+A+'}blip').get('{'+R+'}link'):return '图片关系不明确或外链，待复核'
    if inline.xpath('.//*[local-name()="hlinkClick" or local-name()="hlinkHover"]') or len(inline.xpath('.//*[local-name()="pic"]'))!=1:return '图片含链接或非普通图片对象，待复核'
    rid=inline.find('.//{'+A+'}blip').get('{'+R+'}embed')
    from .package import parse
    rels=parse(pkg.parts.get('word/_rels/document.xml.rels',b'<Relationships/>'))
    rel=[e for e in rels if e.get('Id')==rid]
    if len(rel)!=1 or not rel[0].get('Type','').endswith('/image') or rel[0].get('TargetMode')=='External':return '非普通嵌入图片关系，待复核'
    from posixpath import normpath
    from urllib.parse import unquote
    target=unquote(rel[0].get('Target',''))
    member=normpath(target.lstrip('/') if target.startswith('/') else 'word/'+target)
    if not member.startswith('word/media/') or member not in pkg.parts:return '图片媒体成员缺失或关系不明确，待复核'
    if any(x.tag not in (q('rPr'),q('t')) for r in c.findall(q('r')) for x in r):return '图题含非普通文字片段，待复核'
    try:
        for r in c.findall(q('r')):
            if r.find('w:rPr/w:rPrChange',NS) is not None or Resolver(pkg).value(Resolver(pkg).layers(c,r),'vertAlign','baseline')!='baseline':return '图题含字符修订或上/下角标，待复核'
    except Unresolved:return '图题样式继承不明确，待复核'
    if paragraph_unsafe(c) or not _text(c).strip():return '图题含字段、链接、修订等复杂结构或为空，待复核'
    # Reject explicit/inherited page breaks and section changes rather than erase them.
    for para in (p,c):
        if para.find('w:pPr/w:sectPr',NS) is not None or para.xpath('.//w:br|.//w:lastRenderedPageBreak|.//w:pict|.//w:txbxContent',namespaces=NS):return '现有分页、分节或复杂对象冲突，待复核；不会删除原属性'
        try:
            if any(layer.find(q('framePr')) is not None or layer.find(q('pPrChange')) is not None for layer in Resolver(pkg).layers(para,kind='pPr')):return '继承的浮动框架或格式修订，待复核'
            if _flag(pkg,para,'pageBreakBefore'):return '现有段前分页冲突，待复核；不会删除原属性'
            for tag in ('keepNext','keepLines'):_flag(pkg,para,tag)
        except Unresolved as e:return str(e)+'，待复核'
    try:
        if _flag(pkg,c,'keepNext'):return '图题已有与后段相连属性，可能连续串联；待复核'
    except Unresolved as e:return str(e)+'，待复核'
    return None

def suggest_figure_pairs(input_path,classification_manifest):
    pkg=Package(input_path);m=validate_classification(pkg,classification_manifest)
    rows=[];children=list(pkg.root.find(q('body')));indices={id(p):i for i,p in enumerate(pkg.paragraphs,1)}
    for n,p in enumerate(pkg.paragraphs,1):
        if not p.xpath('.//w:drawing|.//w:pict',namespaces=NS):continue
        at=children.index(p);c=children[at+1] if at+1<len(children) else None
        cn=indices.get(id(c)) if c is not None else None
        reason='后一个主文档对象不是已确认图题，不关联远处题注'
        if cn and m['paragraph_types'][str(cn)]=='figure_caption':reason=_pair_reason(pkg,p,c)
        rows.append({'key':f'L01:{n}:{cn or 0}','image_paragraph':n,'caption_paragraph':cn,
                     'caption_text':_text(c) if cn else '', 'status':'review' if reason else 'available',
                     'reason':reason or '单一内嵌图片与紧接其后的已确认图题；建议尚未应用',
                     'limitation':LIMIT})
    return {'input_sha256':pkg.hash,'pairs':rows,'confirmation_required':True,'limitation':LIMIT}

AID_LIMIT='未检测实际分页；只表达相邻意图，长表仍可跨页，过长标题或后续内容可能无法同页。请在所用渲染环境人工查看。'

def _ordinary_reason(pkg,p):
    if pkg.signed or pkg.ambiguous_sections:return '签名或复杂分节，待复核'
    if paragraph_unsafe(p) or not _text(p).strip():return '空段或含字段、链接、修订等非普通结构，待复核'
    if any(x.tag not in (q('pPr'),q('r')) for x in p):return '非普通段落，待复核'
    if p.find('w:pPr/w:sectPr',NS) is not None or p.xpath('.//w:br[@w:type="page" or @w:type="column"]|.//w:lastRenderedPageBreak',namespaces=NS):return '现有分页、换行或分节冲突，待复核；不会删除原属性'
    try:
        res=Resolver(pkg)
        if any(layer.find(q('framePr')) is not None or layer.find(q('pPrChange')) is not None for layer in res.layers(p,kind='pPr')):return '继承框架或修订，待复核'
        if _flag(pkg,p,'pageBreakBefore'):return '现有段前分页，待复核；不会删除原属性'
        for tag in ('keepNext','keepLines'):_flag(pkg,p,tag)
        for r in p.findall(q('r')):
            if res.special(r,res.layers(p,r)):return '特殊文字片段，待复核'
    except Unresolved:return '样式或分页属性无法可靠解析，待复核'
    return None

def _table_reason(pkg,t):
    if t.tag!=q('tbl'):return '紧接对象不是普通顶层表格，不关联远处表格'
    if set(x.tag for x in t)-{q('tblPr'),q('tblGrid'),q('tr')}:return '表格含修订或包裹结构，待复核'
    if len(t.findall(q('tblPr')))>1 or len(t.findall(q('tblGrid')))!=1:return '表格结构不明确，待复核'
    if t.xpath('.//w:tbl|.//w:tblpPr|.//w:tblPrChange|.//w:trPrChange|.//w:tcPrChange|.//w:ins|.//w:del|.//w:sdt|.//w:customXml',namespaces=NS):return '嵌套、浮动或修订表格，待复核'
    style=t.find('w:tblPr/w:tblStyle',NS)
    if style is not None:
        try:
            for definition in Resolver(pkg).chain(style.get(q('val')),'table'):
                if definition.xpath('.//w:pPr/w:keepNext|.//w:pPr/w:pageBreakBefore|.//w:pPr/w:framePr|.//w:pPr/w:pPrChange',namespaces=NS):return '表格样式含分页/相连属性，条件继承暂待复核'
        except Unresolved:return '表格样式继承无法可靠解析，待复核'
    # Grid spans / vertical merges are retained byte-for-byte; no table reconstruction.
    rows=t.findall(q('tr'))
    if not rows:return '空表格，待复核'
    for row in rows:
        if set(x.tag for x in row)-{q('trPr'),q('tc')} or not row.findall(q('tc')):return '复杂或空表格行，待复核'
        for cell in row.findall(q('tc')):
            if set(x.tag for x in cell)-{q('tcPr'),q('p')} or not cell.findall(q('p')):return '复杂单元格，待复核'
            for p in cell.findall(q('p')):
                # Empty ordinary table paragraphs are allowed; only forbidden structures are checked.
                if not _text(p).strip() and not p.findall(q('r')):
                    probe=deepcopy(p);ET.SubElement(ET.SubElement(probe,q('r')),q('t')).text='占位'
                else:probe=p
                reason=_ordinary_reason(pkg,probe)
                if reason:return '表格内'+reason
    # A first-row keepNext chain may bind the whole table; we do not add to it.
    try:
        if any(_flag(pkg,p,'keepNext') for cell in rows[0].findall(q('tc')) for p in cell.findall(q('p'))):return '表格首行已有连续相连属性，待复核'
    except Unresolved:return '表格分页属性无法解析，待复核'
    return None

def suggest_pagination_aids(input_path,classification_manifest):
    pkg=Package(input_path);m=validate_classification(pkg,classification_manifest)
    result=suggest_figure_pairs(input_path,m);rows=result['pairs']
    for pair in rows:pair['id']='L01';pair['label']=f"图片段{pair['image_paragraph']} → 图题段{pair['caption_paragraph']} · {pair['caption_text']}"
    children=list(pkg.root.find(q('body')));indices={id(p):i for i,p in enumerate(pkg.paragraphs,1)}
    tables={id(t):i for i,t in enumerate(pkg.root.find(q('body')).findall(q('tbl')),1)}
    for n,p in enumerate(pkg.paragraphs,1):
        kind=m['paragraph_types'][str(n)]
        if kind not in ('table_caption','heading1','heading2','heading3','abstract_cn_title','abstract_en_title','reference_title','appendix_title','ack_title'):continue
        at=children.index(p);next_obj=children[at+1] if at+1<len(children) else None
        reason=_ordinary_reason(pkg,p);aid='L02' if kind=='table_caption' else 'L03'
        row={'id':aid,'paragraph':n,'text':_text(p),'body_object':at+1,'limitation':AID_LIMIT}
        if aid=='L02':
            table_id=tables.get(id(next_obj));row.update(table_position=table_id,table_body_object=at+2 if table_id else None)
            row['rows']=len(next_obj.findall(q('tr'))) if table_id else 0
            row['columns']=len(next_obj.findall('w:tblGrid/w:gridCol',NS)) if table_id else 0
            reason=reason or (_table_reason(pkg,next_obj) if next_obj is not None else '没有紧接表格，待复核')
            row['key']=f'L02:{n}:{table_id or 0}'
            row['label']=f"表题段{n} · {_text(p)[:100]} → 表格{table_id or '未关联'}（{row['rows']}行/{row['columns']}网格列）"
            row['properties']=[{'paragraph':n,'tag':'keepNext'}]
        else:
            nn=indices.get(id(next_obj));row['next_paragraph']=nn
            wanted={'abstract_cn_title':'abstract_cn_body','abstract_en_title':'abstract_en_body','reference_title':'reference_item','appendix_title':'appendix_text','ack_title':'ack_text'}.get(kind,'body')
            reason=reason or ('后续不是紧接且已确认的匹配内容；不跨空段、表格或复杂对象串联' if not nn or m['paragraph_types'][str(nn)]!=wanted else _ordinary_reason(pkg,next_obj))
            if not reason:
                try:
                    if _flag(pkg,next_obj,'keepNext'):reason='后续正文已有与后段相连，可能串联；待复核'
                except Unresolved:reason='后续正文属性无法解析，待复核'
            row['key']=f'L03:{n}:{nn or 0}';row['label']=f"标题段{n} · {_text(p)[:100]} → 匹配内容段{nn or '未关联'}"
            row['properties']=[{'paragraph':n,'tag':'keepNext'},{'paragraph':n,'tag':'keepLines'}]
        row['status']='review' if reason else 'available';row['reason']=reason or '实际XML顺序紧接，建议尚未应用；须确认所选对象'
        rows.append(row)
    if m.get('table_scope'):
        from .table_edges import header_suggestions
        rows.extend(header_suggestions(pkg,m['table_scope']))
    result['limitation']=AID_LIMIT+' 重复表头不补续表题注和（续）。';return result

def _properties(pair):
    if pair.get('id')=='L04':return [{'table':pair['table_position'],'row':i,'tag':'tblHeader'} for i in range(1,pair['header_count']+1)]
    return pair.get('properties') or [{'paragraph':pair['image_paragraph'],'tag':'keepNext'},{'paragraph':pair['caption_paragraph'],'tag':'keepLines'}]

def _mask(pkg,pairs):
    root=deepcopy(pkg.root);ps=root.find(q('body')).findall(q('p'))
    for pair in pairs:
        for prop in _properties(pair):
            if 'table' in prop:
                row=root.find(q('body')).findall(q('tbl'))[prop['table']-1].findall(q('tr'))[prop['row']-1]
                pp=row.find(q('trPr'))
            else:pp=ps[prop['paragraph']-1].find(q('pPr'))
            if pp is not None:
                for e in pp.findall(q(prop['tag'])):pp.remove(e)
    for pp in root.xpath('//w:pPr',namespaces=NS):
        if not len(pp) and not pp.attrib and not pp.text:pp.getparent().remove(pp)
    from .table_edges import prune
    prune(root)
    return ET.tostring(root,method='c14n')

def _apply_layout(input_path,output_path,body,rules_path,custom_rules_path,mode,classification_manifest,confirmed_keys,figure_only):
    destination=new_path(output_path,input_path)
    if destination.suffix.lower()!='.docx':raise DemoError('输出必须为新的.docx路径')
    pkg=Package(input_path);rules=_rules(rules_path,custom_rules_path,mode)
    scope,classification=_confirmed_scope(pkg,body,mode,classification_manifest)
    if classification is None:raise DemoError('排版辅助需要扩展模式的人工确认分类')
    suggestions=(suggest_figure_pairs if figure_only else suggest_pagination_aids)(input_path,classification)
    eligible={p['key']:p for p in suggestions['pairs'] if p['status']=='available'}
    keys=list(confirmed_keys)
    if not keys or any(type(k)!=str for k in keys) or len(keys)!=len(set(keys)) or set(keys)-set(eligible):raise DemoError('须显式确认可安全处理的相邻对象；待复核对象不执行')
    pairs=[eligible[k] for k in keys];baseline=_mask(pkg,pairs);before=_check(pkg,scope,rules,classification);changes=[]
    for pair in pairs:
        aid=pair.get('id','L01')
        for prop in _properties(pair):
            tag=prop['tag']
            if 'table' in prop:
                from .table_edges import tables,header_value
                p=tables(pkg)[prop['table']-1].findall(q('tr'))[prop['row']-1];old=header_value(p);loc={'table':prop['table'],'row':prop['row']};container='trPr'
            else:
                n=prop['paragraph'];p=pkg.paragraphs[n-1];old=_flag(pkg,p,tag);loc={'paragraph':n};container='pPr'
            if not old:
                _ensure(_ensure(p,container),tag).set(q('val'),'1')
                source={'label':'产品辅助L04（用户确认）','quote':'仅所选连续表头行tblHeader；不补续表题注、编号或（续），实际重复须另行查看。'} if aid=='L04' else SOURCE if aid=='L01' else {'label':'产品辅助'+aid+'（用户确认）','quote':'仅所选段落分页属性；表达相邻意图，不保证实际同页。'}
                changes.append({'key':pair['key']+':'+tag,'rule_id':aid,'locator':loc,'property':tag,'before':old,'after':True,'verification':'pass','source':source})
    if baseline!=_mask(pkg,pairs) or Path(input_path).read_bytes()!=pkg.raw:raise DemoError('修改超出所选分页属性或输入发生变化，未写输出')
    write_new(destination,pkg.bytes(bool(changes)),input_path)
    try:
        saved=Package(destination);m=deepcopy(classification);m['input_sha256']=saved.hash;__import__('core.table_text',fromlist=['rebind']).rebind(m,saved.hash);after=_check(saved,scope,rules,m)
        preserved=baseline==_mask(saved,pairs);others=all(saved.parts.get(n)==b for n,b in pkg.parts.items() if n!='word/document.xml');original=Path(input_path).read_bytes()==pkg.raw
        checks=[]
        for pair in pairs:
            flags=[]
            for p in _properties(pair):
                if 'table' in p:
                    from .table_edges import tables,header_value
                    value=header_value(tables(saved)[p['table']-1].findall(q('tr'))[p['row']-1]);where={'table':p['table'],'row':p['row']}
                else:value=_flag(saved,saved.paragraphs[p['paragraph']-1],p['tag']);where={'paragraph':p['paragraph']}
                flags.append({**where,'property':p['tag'],'value':value})
            c={'key':pair['key'],'properties':flags,'verification':'pass'}
            if pair.get('id','L01')=='L01':c.update(image_keep_with_next=flags[0]['value'],caption_keep_lines=flags[1]['value'])
            checks.append(c)
        if not preserved or not others or not original or any(not p['value'] for c in checks for p in c['properties']):raise DemoError('分页属性读回或内容完整性核对失败')
    except Exception:
        destination.unlink();raise
    ids=sorted({p.get('id','L01') for p in pairs});figure=ids==['L01']
    messages={'L01':'已设置图片与图题相邻属性','L02':'已设置表题相邻属性','L03':'已设置标题与匹配内容相邻属性','L04':'已设置重复表头属性（不补续表题注与（续））'}
    return {'kind':'figure_layout' if figure else 'pagination_layout','before':before,'after':after,'changes':changes,'output':str(destination),'problem_delta':problem_delta(before,after),'skipped_review_keys':[],
            'output_body_manifest':{'input_sha256':saved.hash,'body_paragraphs':scope,'confirmation':'沿用已确认分类；仅所选分页属性修改，结构核对通过'},
            'output_classification_manifest':m,'layout':{'id':','.join(ids),'pairs':pairs,'checks':checks,'message':'；'.join(messages[i] for i in ids),'limitation':LIMIT if figure else AID_LIMIT+(' 重复表头不保证实际重复，不补续表题注、编号或（续）。' if 'L04' in ids else ''),'visual_status':'not_reviewed','not_school_rule':True},
            'preservation':{'original_sha256_unchanged':original,'document_except_selected_format_attributes_equal':preserved,'other_zip_member_bytes_equal':others,
            'verified_objects':'完整主文档XML仅掩码所选段落keepNext/keepLines或所选表格行tblHeader；其他ZIP成员字节相同，含图片尺寸、媒体、字段、表格内容尺寸合并、编号和分节。'}}

def apply_figure_layout(input_path,output_path,body=None,rules_path=None,*,custom_rules_path=None,mode='extended',classification_manifest=None,confirmed_keys=()):
    return _apply_layout(input_path,output_path,body,rules_path,custom_rules_path,mode,classification_manifest,confirmed_keys,True)

def apply_pagination_layout(input_path,output_path,body=None,rules_path=None,*,custom_rules_path=None,mode='extended',classification_manifest=None,confirmed_keys=()):
    return _apply_layout(input_path,output_path,body,rules_path,custom_rules_path,mode,classification_manifest,confirmed_keys,False)

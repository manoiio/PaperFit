"""仅将引擎记录转换为自然语言和安全HTML，不做规则判断。"""
import html
import json
from core.report import basis

LABELS = {'pass': '符合', 'problem': '发现问题', 'review': '待复核', 'not_applicable': '不适用'}

def short(text, limit=36):
    text = ' '.join(text.split())
    return text if len(text) <= limit else text[:limit] + '…'

def position(loc):
    if 'note_kind' in loc:return ('脚注' if loc['note_kind']=='footnote' else '尾注')+' ID'+str(loc.get('note_id','关系'))+(' · 注释段'+str(loc['note_paragraph']) if 'note_paragraph' in loc else '')+(' · run'+str(loc['run']) if 'run' in loc else '')+(' · '+{'font_cn':'中文字体','font_size':'字号','line_multiple':'倍数行距','structure':'结构','relationship':'关系','protected_run':'保护片段','protected_marker':'自动标记混合片段'}.get(loc['property'],loc['property']) if loc.get('property') else '')
    if 'toc_object' in loc:return '目录对象 d:'+str(loc['toc_object'])+(' · 顶层段'+str(loc['paragraph']) if 'paragraph' in loc else '')+(' · run'+str(loc['run']) if 'run' in loc else '')+(' · '+str(loc['property']) if 'property' in loc else '')
    if loc.get('story'):return '节'+str(loc.get('section','?'))+' '+loc['story']+(' 段'+str(loc['story_paragraph']) if loc.get('story_paragraph') else '')+(' run'+str(loc['run']) if loc.get('run') else '')
    if 'body_object' in loc:return '文档对象 '+str(loc['body_object'])+(' · 未列入普通清单的表格'+str(loc['unlisted_table']) if 'unlisted_table' in loc else '')
    if 'table' in loc:
        return f"表 {loc['table']}" + (' · '+{'left':'左侧','right':'右侧'}.get(loc['side'],loc['side']) if 'side' in loc else '') + (f" · 行{loc['row']} · 单元格{loc['cell']} · 段{loc['cell_paragraph']} · run{loc.get('run','—')}" if 'cell_paragraph' in loc else ' · 行'+str(loc['row']) if 'row' in loc else '') + (' · '+{'font_cn':'中文字体','font_size':'普通字号'}.get(loc.get('property'),loc.get('property','')) if loc.get('property') else '')
    if 'section' in loc:
        return f"节 {loc['section']}"
    if 'paragraph' in loc:
        result = f"段 {loc['paragraph']}"
        prop=loc.get('property','')
        label={'size':'字号','alignment':'对齐','line':'行距','font_eastAsia':'中文字体','font_ascii':'西文/数字字体','font_hAnsi':'扩展西文字体','numbering_symbol':'自动编号符号','before':'段前','after':'段后','line_spacing':'行距','first_line_indent':'首行缩进','bold':'加粗'}.get(prop,prop)
        if 'start' in loc:result+=' · '+{'label':'标签','content':'内容'}.get(loc.get('part'),'文字')+f"字符{loc['start']+1}–{loc['end']}"
        return result + (f" · 片段 {loc['run']}" if 'run' in loc else '') + (' · '+label if label else '')
    return '主文档'

def original(finding, inventory):
    if finding.get('object_type') in ('footnote','endnote'):return finding.get('excerpt','注释关系或系统对象，详见清单')
    n = finding['locator'].get('paragraph')
    if n:
        return short(inventory['paragraphs'][n - 1]['text']) or '（空段或非文字对象）'
    return '该节页面设置'

def fmt(value, rule, expected=False):
    if rule=='R35' and isinstance(value,dict):
        if 'unresolved' in value:return '待复核：'+value['unresolved']
        return ('有外侧线' if value['visible'] else '无外侧线')+'；'+str(len(value.get('cells',[])))+'个外侧单元格（来源见详情）'
    if rule=='R33' and isinstance(value,str):return {'superscript':'上标','baseline':'基线（非上标）','subscript':'下标','mixed':'部分上标/混合','unresolved':'无法可靠判断'}.get(value,value)
    if rule=='R23':
        if isinstance(value,dict) and 'pt' in value and type(value['pt']) in (int,float):return f"{value['pt']:g}磅"
        if isinstance(value,dict) and isinstance(value.get('eastAsia'),str):return '中文 '+value['eastAsia']
        if expected and type(value) in (int,float):return f'{value:g}磅'
    if value is None:
        return '未确定' if not expected else '—'
    if expected:
        if rule == 'R05': return f'{value:g}磅'
        if rule == 'R06': return f'{value:g}倍'
        if rule == 'R07': return f'首行{value:g}字符（汉字）'
        if isinstance(value, str): return {'left':'居左','center':'居中','right':'居右','both':'两端对齐'}.get(value,value)
    if rule in tuple(f'R{i}' for i in range(13,23))+('R38','R39','R40','R41'):
        if type(value) in (int,float) and rule!='R22':return f'{value:g}磅'
        if isinstance(value,bool):return '加粗' if value else '不加粗'
        if isinstance(value,str):return {'left':'居左','center':'居中','right':'居右','both':'两端对齐'}.get(value,value)
        if isinstance(value,dict):
            if 'value' in value and 'unit' in value:return str(value['value'])+('行' if value['unit']=='lines' else '磅')
            if 'chars' in value:return '首行'+str(value['chars'])+'字符'
            if 'multiple' in value:return fmt(value,'R06') if 'line_rule' in value else str(value['multiple'])+'倍'
    if isinstance(value, dict):
        if rule in ('R08','R09','R10','R11','R12'):
            if rule=='R12' and 'figure_caption' in value and 'table_caption' in value:
                return '图题：'+fmt(value['figure_caption'],'R12',True)+'；表题：'+fmt(value['table_caption'],'R12',True)
            if 'font' in value and 'slot' not in value and ('pt' in value or 'size_pt' in value):
                font=value['font'] or '字体未确定';size=value.get('pt',value.get('size_pt'))
                return '编号符号：'+font+'；'+(f'{size:g}磅' if size is not None else '字号未确定')
            if 'slot' in value:
                font=value.get('font');return ('未确定（主题或字体槽位）' if font is None or isinstance(font,dict) else str(font))
            if 'pt' in value and 'line_rule' not in value:return f"{value['pt']:g}磅" if value['pt'] is not None else '字号未确定'
            if 'alignment' in value and len(value)==1:return {'left':'居左','center':'居中','right':'居右','both':'两端对齐'}.get(value['alignment'],value['alignment'])
            if set(value)=={'multiple'}:return f"{value['multiple']:g}倍"
            if 'style_id' in value:return str(value['style_id'] or '未指定Heading样式')+' · 大纲 '+('未指定' if value['outline_level'] is None else str(value['outline_level'])+'（从0起）')
            if 'heading_levels' in value:return 'Heading 1–3；对应大纲级别0–2（从0起）'
            if 'font_cn' in value:
                result=f"中文{value['font_cn']}；西文/数字{value['font_latin']}；{value['size_pt']:g}磅"
                if 'alignment' in value:result+='；'+{'left':'居左','center':'居中','right':'居右','both':'两端对齐'}.get(value['alignment'],str(value['alignment']))
                if 'line_multiple' in value:result+='；'+str(value['line_multiple'])+'倍行距'
                return result
            if 'line_rule' in value:return fmt(value,'R06')
        if 'unresolved' in value: return '未确定：' + str(value['unresolved'])
        if rule == 'R01':
            w = value.get('width_mm', value.get('w_mm'))
            h = value.get('height_mm', value.get('h_mm'))
            text=f'{w:g} × {h:g} mm' if w is not None and h is not None else '纸张尺寸未确定'
            if value.get('orientation'):text+=' · '+{'portrait':'竖向','landscape':'横向'}.get(value['orientation'],value['orientation'])
            return text
        if rule == 'R02':
            return '；'.join(label + (f'{value[k]:g} mm' if value.get(k) is not None else '未确定')
                            for k, label in [('top_mm','上'),('bottom_mm','下'),('left_mm','左'),('right_mm','右')])
        if rule in ('R03', 'R04'):
            labels = {'eastAsia': '中文', 'ascii': '西文/数字', 'hAnsi': '扩展西文'}
            chunks = []
            for k, v in value.items():
                text = '未确定' if v is None else ('主题字体（待复核）' if 'theme' in v else '未确定：'+str(v.get('unresolved','字体映射待复核'))) if isinstance(v, dict) else str(v)
                chunks.append(f'{labels.get(k,k)}：{text}')
            return '；'.join(chunks)
        if rule == 'R05':
            return f"{value['pt']:g}磅" if value.get('pt') is not None else '字号未确定'
        if rule == 'R06':
            if value.get('line_rule') == 'auto' and value.get('multiple') is not None:
                return f"{value['multiple']:g}倍"
            if value.get('pt') is not None:
                label = {'exact': '固定', 'atLeast': '最小值'}.get(value.get('line_rule'), value.get('line_rule'))
                return f"{label}{value['pt']:g}磅"
        if rule == 'R07':
            chunks = []
            if value.get('first_line_chars') is not None:
                chunks.append(f"首行{value['first_line_chars']:g}字符")
            if value.get('first_line_pt') is not None:
                chunks.append(f"点值{value['first_line_pt']:g}磅")
            for k, label in [('hanging','悬挂点值'),('hanging_chars','悬挂字符属性')]:
                if value.get(k) is not None:
                    chunks.append(f"{label}={value[k]}")
            return '；'.join(chunks) or '未设置首行缩进'
    # Exact fallback for an unfamiliar record; never turn an unknown value into a pass.
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))

def finding_table(findings, inventory):
    esc = lambda x: html.escape(str(x), quote=True)
    rows = []
    for f in findings:
        src = f['source']
        evidence = ((src['label']+'：' if src.get('label') else '')+f"手册物理页{src['physical_page']}：{src['quote']}") if src.get('file') else basis(src)
        cells = [f"{f['rule_id']} {f['rule_name']}", position(f['locator']), original(f, inventory),
                 fmt(f['actual'], f['rule_id']), fmt(f['expected'], f['rule_id'], True),
                 '可修正' if f['fixable'] else '不自动修正', evidence, resolution_text(f)]
        rows.append('<tr>' + ''.join(f'<td>{esc(v)}</td>' for v in cells) + '</tr>')
    headers = ['规则', '位置', '简短原文', '实际格式', '要求格式', '修正', '依据', '解析依据 / 处理建议']
    return '<div class="report-scroll"><table class="report-table"><thead><tr>' + ''.join(f'<th>{h}</th>' for h in headers) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'

def resolution_text(f):
    pieces=[]
    for slot,info in f.get('font_evidence',{}).items():
        if info.get('font'):
            pieces.append(slot+'文档指定 '+info['font']+'；'+str(info.get('declared_at','')))
            if info.get('theme_basis'):
                t=info['theme_basis'];pieces.append(t['theme']+' → '+t['selector']+'；主题语言 '+str(t.get('theme_font_lang') or '未指定，使用区域主题字体'))
        elif info.get('reason'):pieces.append(slot+'：'+info['reason'])
        if info.get('dependency'):pieces.append(info['dependency'])
        if info.get('fallback_basis'):pieces.append(info['fallback_basis'])
    if f.get('numbering_evidence'):pieces.append('只读编号：'+f['numbering_evidence']['reason'])
    if f.get('detail'):pieces.append(f['detail'])
    if f['status']=='review':pieces.append('请在Word核对该对象的槽位/样式/编号；本项不自动修正，其余可判定属性按各自记录检查。')
    elif f['status']=='problem' and not f['fixable']:pieces.append('本项为只读内容提示或存在修改依赖；请人工核对，不自动改写内容。')
    return '；'.join(dict.fromkeys(pieces)) or '本属性已检查；不代表电脑已安装字体或可见排版通过。'

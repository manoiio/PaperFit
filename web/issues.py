"""只投影已存在的结果：不判断字体、几何、分页，不改状态或选择。"""
from copy import deepcopy
from .presentation import fmt,position,short,resolution_text
from core.report import basis

CATEGORIES={'format':'确定的格式问题','width':'宽度风险','pagination':'可确认的分页辅助建议','review':'待复核及支持边界'}
STATUS={'problem':'发现问题','risk':'宽度风险','available':'建议待确认','review':'待复核','boundary':'支持边界','pass':'符合','not_applicable':'不适用'}

def locate(loc):
    if 'note_kind' in loc:return position(loc)
    return f"表格 {loc['table']}"+(' · 行'+str(loc['row'])+' · 单元格'+str(loc['cell'])+' · 段'+str(loc['cell_paragraph'])+' · run'+str(loc.get('run','—')) if 'row' in loc and 'cell_paragraph' in loc else '') if 'table' in loc else position(loc)

def object_key(loc):
    if 'note_kind' in loc:return loc['note_kind']+':'+str(loc.get('note_id','关系'))+':'+str(loc.get('note_index',''))
    for key in ('note_kind','citation','toc_object','paragraph','table','section'):
        if key in loc:return key+':'+str(loc[key])
    return 'document'

def value(v,rid='',expected=False):
    if rid=='R35' and isinstance(v,dict):
        if 'unresolved' in v:return '待复核：'+v['unresolved']
        return ('存在可见外侧线' if v['visible'] else '已解析来源中无外侧线')+'；影响'+str(len(v.get('cells',[])))+'个外侧单元格；来源：'+ '、'.join(dict.fromkeys(c['effective']['source'].split(' 行')[0] for c in v.get('cells',[])))
    if isinstance(v,dict) and rid in ('R01','R02'):
        rounded={k:round(n,2) if k.endswith('_mm') and type(n) in (float,int) else n for k,n in v.items()}
        return fmt(rounded,rid,expected)
    return fmt(v,rid,expected)

def field_value(v,rid,loc,expected=False):
    if rid=='R43':
        if isinstance(v,list):return ' → '.join({'figure':'图片','caption':'题注','table':'表格'}.get(x,str(x)) for x in v)
        if v=='unconfirmed':return '对象关联未确认'
        if v=='separated':return '隔有其他对象'
    if rid=='R42':
        if isinstance(v,list):return '编号序列：'+'、'.join(map(str,v[:20]))+('…（完整序列见高级报告）' if len(v)>20 else '')
        if isinstance(v,dict) and 'parsed' in v:
            n=v['parsed'];return (n['raw_number']+'；标题'+('已填写' if n['title'] else '未填写') if n else '编号无法可靠解析')+'；所属章 '+str(v.get('confirmed_chapter') or '待确认')+'；'+str(v.get('chapter_evidence',''))
    if rid in ('R36','R37'):
        if isinstance(v,dict) and 'pt' in v and loc.get('property')=='font_size':return str(v['pt'])+'磅'
        if isinstance(v,dict) and 'eastAsia' in v:return '中文：'+str(v['eastAsia'])
        if isinstance(v,dict) and 'multiple' in v:return (str(v['multiple'])+'倍') if v['multiple'] is not None else ('固定' if v['line_rule']=='exact' else '最小')+str(v['pt'])+'磅'
        if loc.get('property')=='line_multiple' and type(v) in (int,float):return str(v)+'倍'
        if loc.get('property')=='font_size' and type(v) in (int,float):return str(v)+'磅'
    prop=loc.get('property')
    if rid in ('R30','R31','R32'):
        if prop=='font_size' and type(v) in (int,float):return f'{v:g}磅'
        if prop=='line_multiple' and type(v) in (int,float):return f'{v:g}倍'
        if prop=='line_multiple' and isinstance(v,dict):return str(v.get('multiple'))+'倍' if 'multiple' in v else '固定/最小'+str(v.get('points'))+'磅'
    if rid in ('R24','R25','R26','R27','R28','R29'):
        if prop in ('font_size','page_font_size') and type(v) in (int,float):return f'{v:g}磅'
        if prop in ('header_distance_mm','footer_distance_mm') and type(v) in (int,float):return f'{v:.2f}mm'
        if prop=='bold' and type(v) is bool:return '加粗' if v else '不加粗'
    if rid in ('R08','R09','R10','R12',*[f'R{i}' for i in range(13,24)],'R38','R39','R40','R41') and type(v) in (int,float):
        if prop in ('size','font_size'):return f'{v:g}磅'
        if prop in ('line','line_spacing'):return f'{v:g}倍'
    if prop=='alignment' and isinstance(v,str):return {'left':'居左','center':'居中','right':'居右','both':'两端对齐'}.get(v,v)
    return value(v,rid,expected)

def project(format_report,width_report=None,proposals=None,*,inventory=None,context=None,boundaries=()):
    context=context or {};inventory=inventory or {'paragraphs':[]};rows=[]
    def add(category,key,loc,status,title,actual,expected,reason,action,source,raw):
        n=loc.get('paragraph');paras=inventory['paragraphs']
        excerpt=short(paras[n-1]['text'],48) if n and 0<n<=len(paras) else short(raw.get('excerpt',''),48)
        rows.append({'id':category+':'+key,'record_key':key,'category':category,'object':object_key(loc),'locator':deepcopy(loc),'position':locate(loc),'excerpt':excerpt,'status':status,
                     'title':title,'actual':actual,'expected':expected,'reason':reason,'action':action,'basis':source,'context':deepcopy(context),'raw':deepcopy(raw)})
    for f in format_report['findings']:
        cat='review' if f['status']=='review' else 'format'
        action='选择该格式项修正' if f['status']=='problem' and f['fixable'] else '人工核对，不自动执行' if f['status'] in ('problem','review') else '无需操作'
        if f['rule_id']=='R43' and f['status']=='problem':action='到题注位置操作，核对后单独选择L05；复杂对象仍禁止移动'
        add(cat,f['key'],f['locator'],f['status'],f['rule_id']+' '+f['rule_name'],field_value(f['actual'],f['rule_id'],f['locator']),field_value(f['expected'],f['rule_id'],f['locator'],True),resolution_text(f),action,basis(f['source']),f)
    for i,n in enumerate(format_report['coverage_notes']):
        add('review','coverage:'+str(i),n['locator'],'review','覆盖提示','该对象未完整检查','人工核对',n['detail'],'人工复核，不改变引擎状态','格式引擎覆盖记录',n)
    if format_report.get('toc'):
        toc=format_report['toc']
        for r in toc['rows']:
            add('review','toc-match:'+r['id'],r['locator'],'pass' if r['status']=='pass' else 'review','目录对应核对（只读）',r['entry']['title'],'与确认正文标题文字/层级一致；实际页码未核对',r['reason']+'；'+r['numbering_state'],'人工核对，不改域/文字/页码',r['evidence'],{**r,'object_type':'toc_correspondence'})
        boundaries=(*boundaries,*coverage_limits(format_report))
    if width_report:
        for r in width_report['objects']:
            cat='review' if r['status']=='review' else 'width'
            actual=f"声明{r['declared_width_mm']:.2f}mm；超出{r['excess_mm']:.2f}mm" if 'declared_width_mm' in r else '宽度未确定'
            expected=f"可用{r['available_mm']:.2f}mm" if 'available_mm' in r else '无法可靠计算'
            b=r.get('basis') or {};evidence=(f"节{b['section']}：页面{b['page_width_mm']:.2f} − 左{b['left_margin_mm']:.2f} − 右{b['right_margin_mm']:.2f} − 装订{b['gutter_mm']:.2f} = 正文{b['body_width_mm']:.2f}mm" if b else '未确定所在节/几何条件')
            add(cat,r['key'],r['locator'],'pass' if r['status']=='pass' else r['status'],r['id']+' '+('表格宽度' if r['kind']=='table' else '内嵌图片宽度'),actual,expected,r['reason'],'查看尺寸计划，单独确认适配' if r['fixable'] else '人工复核，不自动执行' if r['status']=='review' else '无需自动适配',evidence,r)
    else:boundaries=(*boundaries,'宽度检查：未检查')
    if proposals is not None:
        for p in proposals['pairs']:
            loc={'paragraph':p.get('paragraph',p.get('image_paragraph'))};loc={k:v for k,v in loc.items() if v is not None}
            if p.get('id')=='L04':loc={'table':p['table_position']}
            add('review' if p['status']=='review' else 'pagination',p['key'],loc,p['status'],p.get('id','L01')+(' 重复表头属性' if p.get('id')=='L04' else ' 相邻属性'),p.get('label',p.get('caption_text','')),'只表达相邻意图，不保证实际同页',p['reason'],'查看并确认具体关联' if p['status']=='available' else '人工复核，不自动执行','实际XML紧接对象与已确认分类；产品辅助，不是学校要求',p)
        if not proposals['pairs']:boundaries=(*boundaries,'分页辅助：没有适用关联建议（不适用），未检测实际孤行或跨页')
    else:boundaries=(*boundaries,'分页辅助：未检查（基础模式或分类尚未确认）')
    coverage=format_report['coverage']
    boundaries=(*boundaries,*coverage.get('academic_unchecked_requirements',[]),*coverage.get('note_limits',[]),*coverage.get('caption_limits',[]),*coverage.get('backmatter_limits',[]))
    boundaries=(*boundaries,'规则结论只针对已确认范围；未确认段落不自动套正文/标题/题注格式。','表格内部文字、页眉页脚及注释仅在明确启用且确认的范围内检查；文本框及实际分页仍需另行复核。宽度只覆盖受支持的顶层对象。','预览不是Microsoft Word最终排版，视觉结论必须由人工查看记录。')
    for i,n in enumerate(boundaries):
        add('review','boundary:'+str(i),{},'boundary','支持边界','未覆盖或限定范围','保留人工复核',n,'查看支持范围，不自动执行','本阶段支持范围',{'detail':n})
    return {'records':rows,'format_summary':deepcopy(format_report['summary']),'width_summary':deepcopy(width_report['summary']) if width_report else None,
            'pagination_summary':{'suggestions':sum(p['status']=='available' for p in proposals['pairs']),'reviews':sum(p['status']=='review' for p in proposals['pairs'])} if proposals else None,
            'coverage':deepcopy(coverage),'context':deepcopy(context)}

def filter_records(records,categories=(),objects=(),statuses=()):
    return [r for r in records if (not categories or r['category'] in categories) and (not objects or r['object'] in objects) and (not statuses or r['status'] in statuses)]

def group_records(records):
    grouped={}
    for r in records:grouped.setdefault((r['category'],r['object']),[]).append(r)
    return grouped

def next_steps(report,width_report=None,result=None,*,is_output=False):
    steps=[]
    def add(area,title,reason,keys=()):steps.append({'area':area,'title':title,'reason':reason,'keys':list(keys)})
    problems=[f for f in report['findings'] if f['status']=='problem' and f['fixable']]
    pages=[f['key'] for f in problems if f['rule_id'] in ('R01','R02')]
    if pages:add('format','先处理纸张与页边距','页面宽度改变后，应在新副本重新核对对象宽度；不自动选择修正。',pages)
    if result and any(c['rule_id'] in ('R01','R02') for c in result['changes']):add('width','页边距已改，核对本轮宽度','这份输出已有新的页面设置；查看当前输出的尺寸依据，再单独确认适配。')
    for dep in report.get('modification_dependencies',[]):add('format','字号与点值缩进需联动核对',dep['detail'],dep['trigger_keys'])
    if result:
        for dep in result['problem_delta']['new_problem_causes']:add('format','新出现的问题需下一轮处理',dep['detail'],[dep['key']])
    if problems and not pages:add('format','选择需要修正的格式项','只选择明确问题且可修正的记录；保留未选项。',[f['key'] for f in problems])
    if width_report and any(r['fixable'] for r in width_report['objects']):add('width','确认超宽对象的尺寸计划','适配是独立操作，不会因格式规则通过自动修改。',[r['key'] for r in width_report['objects'] if r['fixable']])
    if result and any(c['rule_id']=='R23' for c in result['changes']):add('preview','表格文字已修改，核对宽度与换行','字体字号可能改变换行及表格高度；原有列宽/行高未改，请重新核对宽度并主动预览。')
    if result and result.get('kind')=='width_adaptation':add('preview','宽度已适配，查看换行与高度','表格变窄可能增加换行/高度，图片只缩宽；请主动重新预览。')
    elif result:add('preview','属性已落盘，查看真实页面','属性复查不验证实际分页、裁切或题注同页；主动生成本轮预览。')
    if not steps:add('preview','查看页面或导出当前检查报告','覆盖内未发现可自动处理项，仍需保留边界和人工复核；不代表全文合格。')
    for step in steps:step['requires_next_round']=is_output and step['area']=='format' and bool(problems)
    return steps

def coverage_limits(report):return report['coverage'].get('toc_limits',[])


def type_records(records,coverage,chosen):
    if chosen=='全部':return list(records)
    if chosen in ('footnote','endnote','table_border','cover_title','cover_field','section_story','toc_title','toc_entry','toc_correspondence','citation','citation_relation'):
        return [r for r in records if r['raw'].get('object_type')==chosen]
    typed=coverage.get('paragraph_types',{})
    objects={'paragraph:'+str(n) for n,t in typed.items() if t==chosen}
    if chosen=='table_content':objects={'table:'+n for n,t in coverage.get('table_scope',{}).get('table_types',{}).items() if t=='content'}
    return [r for r in records if r['object'] in objects]

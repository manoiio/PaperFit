"""版本化、白名单模板：只编译为现有引擎的规则，不执行导入文件中的指令。"""
from copy import deepcopy
from datetime import datetime, timezone
import math
import re
from .package import DemoError
from .spec_validation import DANGEROUS, FONT_NAMES
from .norms import MAX_TEXT, marked_text

VERSION = 2  # Legacy body-only schema remains compatible.
LATEST_VERSION = 3
FIELDS = {
    'paper': ('R01', '纸张', 'paper'),
    'margin_top': ('R02', '上边距', 'mm'), 'margin_bottom': ('R02', '下边距', 'mm'),
    'margin_left': ('R02', '左边距', 'mm'), 'margin_right': ('R02', '右边距', 'mm'),
    'font_cn': ('R03', '正文中文字体', 'font'), 'font_western': ('R04', '正文西文字体', 'font'),
    'font_size': ('R05', '正文普通文字字号', 'pt'), 'line_spacing': ('R06', '正文倍数行距', 'multiple'),
    'first_line_indent': ('R07', '正文首行缩进', 'chars'),
}
EXT_FIELDS = {}
for level,label,rid in ((1,'一级标题','R08'),(2,'二级标题','R09'),(3,'三级标题','R10')):
    for prop,title,unit in (('font_cn','中文字体','font'),('font_size','字号','pt'),('alignment','对齐','alignment'),('line_spacing','倍数行距','multiple')):
        EXT_FIELDS[f'heading{level}_{prop}']=(rid,label+title,unit)
for obj,label in (('figure_caption','图题'),('table_caption','表题')):
    for prop,title,unit in (('font_cn','中文字体','font'),('font_size','字号','pt')):
        EXT_FIELDS[obj+'_'+prop]=('R12',label+title,unit)
ALL_FIELDS = {**FIELDS, **EXT_FIELDS}
ALIGNMENTS = {'left':'居左','center':'居中','right':'居右','both':'两端对齐'}


def field_map(data):
    if data.get('structure_version')==6 or any(n.startswith(('appendix_','ack_')) for n in data):
        from .back_templates import V6_FIELDS
        return V6_FIELDS
    if data.get('structure_version')==5 or 'table_content__font_cn' in data:
        from .table_templates import V5_FIELDS
        return V5_FIELDS
    if data.get('structure_version')==4 or any('__' in n for n in data):
        from .academic_templates import V4_FIELDS
        return V4_FIELDS
    # This helper only chooses a schema. Validation still requires exact keys.
    return ALL_FIELDS if data.get('structure_version') == LATEST_VERSION or set(data.get('final_values',data)) == set(ALL_FIELDS)|{'unsupported'} else FIELDS


CN = ('宋体', '黑体', '楷体', '仿宋')
WEST = ('Times New Roman', 'Arial', 'Calibri')
SOURCE_LABELS = {'ai_extracted': 'AI从原文提取后确认', 'user_confirmed': '用户确认值', 'default_inherited': '用户选择沿用默认值', 'legacy_fixed':'沿用旧版本固定标题题注要求'}
REASONS = {'unsupported','conflict','ambiguous','out_of_range','title','fixed_spacing','minimum_spacing','unknown_font','landscape','printing','semantic','indent_unit'}
LOCATOR = re.compile(r'(?:SRC:[0-9a-f]{64}:)?(?:TEXT:\d+|TXT:L\d+|DOCX:P\d+|DOCX:T\d+:R\d+:C\d+:P\d+|摘录:L\d+)\Z')


def safe_text(value, limit=200, allow_empty=False):
    if not isinstance(value, str) or len(value)>limit or (not allow_empty and not value.strip()) or DANGEROUS.search(value):
        raise DemoError('模板或依据文本无效；不接受代码、路径、密钥或工具指令')
    try:value.encode('utf-8',errors='strict')
    except UnicodeError:raise DemoError('文本含非法Unicode，不能可靠显示或保存') from None
    if any(ord(c)<32 and c not in '\n\r\t' for c in value):raise DemoError('文本含异常控制字符')
    return value


def validate_value(name, value):
    from .backmatter import FIELDS as back_fields
    if name in back_fields:
        from .back_templates import value as back_value
        return back_value(name,value)
    if name in ('table_content__font_cn','table_content__font_size'):
        from .table_templates import value as table_value
        return table_value(name,value)
    from .academic_rules import FIELDS as academic_fields
    if name in academic_fields:
        from .academic_templates import value as academic_value
        return academic_value(name,value)
    if name not in ALL_FIELDS: raise DemoError('未知可执行字段')
    if name in EXT_FIELDS:
        if name.endswith('_font_cn'):
            if type(value) is not str or value not in CN:raise DemoError('标题/题注中文字体不在支持范围')
        elif name.endswith('_alignment'):
            if type(value) is not str or value not in ALIGNMENTS:raise DemoError('标题对齐枚举无效')
        else:
            try:finite=type(value) in (int,float) and math.isfinite(value)
            except OverflowError:finite=False
            if not finite:raise DemoError('格式值必须是有限数字，不能是布尔或字符串')
            if name.endswith('_font_size'):
                upper=36 if name.startswith('heading') else 24
                if not (8<=value<=upper and value*2==round(value*2)):raise DemoError(f'字号仅支持8–{upper}pt，0.5pt步长')
            elif value not in (1,1.25,1.5,2):raise DemoError('标题倍数行距只支持1、1.25、1.5、2')
        return value
    if name == 'paper':
        if type(value) is not str or value != 'A4 portrait': raise DemoError('只支持A4竖向')
    elif name in ('font_cn', 'font_western'):
        if type(value) is not str or value not in (CN if name=='font_cn' else WEST): raise DemoError('字体不在课程原型支持范围')
    else:
        try: finite=type(value) in (int,float) and math.isfinite(value)
        except OverflowError: finite=False
        if not finite: raise DemoError('格式值必须是有限数字，不能是布尔、字符串或空值')
        if name.startswith('margin_') and not 10<=value<=50: raise DemoError('各边距仅支持10–50mm')
        if name=='font_size' and not (8<=value<=24 and value*2==round(value*2)): raise DemoError('字号仅支持8–24pt，0.5pt步长')
        if name=='line_spacing' and value not in (1,1.25,1.5,2): raise DemoError('倍数行距只支持1、1.25、1.5、2')
        if name=='first_line_indent' and value not in (0,1,2): raise DemoError('首行缩进只支持0、1、2字符')
    return value


def validate_segments(segments):
    if not isinstance(segments, list) or len(segments)>2000: raise DemoError('规范摘录结构无效')
    seen=set()
    for s in segments:
        if not isinstance(s, dict) or set(s)!={'location','text'} or not isinstance(s['location'],str) or not LOCATOR.fullmatch(s['location']) or s['location'] in seen:
            raise DemoError('规范来源位置无效或重复')
        safe_text(s['text'], MAX_TEXT)
        seen.add(s['location'])
    if len(marked_text(segments))>MAX_TEXT: raise DemoError('待发送规范（含来源标记）超过12000字符，请缩小范围')
    return segments


def font_candidates(segment,name):
    # 精确字体族；不把“方正黑体”“Arial Narrow”等未知族名截成白名单字体。
    choices=CN if name=='font_cn' else WEST
    normalized=re.sub(r'正文|普通文字|中文|西文|英文|英语|汉字|文字|字体|采用|使用|选用|设为|设置为|为|用|是',' ',segment)
    normalized=re.sub(r'\d+(?:\.\d+)?\s*(?:pt|磅)',' ',normalized,flags=re.I)
    tokens=[p.strip() for p in re.split(r'[，。；;\n\t、()（）“”‘’\"\']',normalized) if p.strip()]
    found={v for v in choices if any(t.lower()==v.lower() for t in tokens)}
    mentions=any(v.lower() in segment.lower() for v in choices)
    if mentions and not found:return {'unknown'}
    if name=='font_cn' and any(w in segment for w in ('微软雅黑','华文','思源','等线','隶书','方正','汉仪')):return found|{'unknown'}
    # A supported family alongside a named unknown variant is still a conflict.
    for t in tokens:
        if any(v.lower() in t.lower() for v in choices) and t.lower() not in {v.lower() for v in choices}:found.add('unknown')
    return found


def _values(segment, name):
    """只证明明确数值/范围与原文一致；无法证明时拒绝AI字段，仍可人工确认。"""
    if re.search(r'[-−]\s*\d',segment): return {'unsupported'}
    if any(w in segment for w in ('任选','或','大约','建议','可能','不超过','至少','至多')): return {'ambiguous'}
    if name=='paper': return {'A4 portrait'} if re.search(r'(?<![A-Za-z0-9])A4(?![A-Za-z0-9])',segment,re.I) and not any(w in segment for w in ('横向','横版','A3','A5')) else set()
    if name.startswith('margin_'):
        side={'margin_top':'上','margin_bottom':'下','margin_left':'左','margin_right':'右'}[name]
        result=set()
        for m in re.finditer(r'(上下左右|四周|四边|上下|左右|上|下|左|右)(?:页)?(?:边距)?\s*(?:均为|均|为|是|：|:|=)?\s*(\d+(?:\.\d+)?)\s*(mm|cm|毫米|厘米)',segment,re.I):
            if side in m.group(1) or m.group(1) in ('四周','四边'):
                result.add(round(float(m.group(2))*(10 if m.group(3).lower() in ('cm','厘米') else 1),8))
        return result
    if name in ('font_cn','font_western'): return font_candidates(segment,name)
    if name=='font_size':
        text=re.split(r'行距|缩进',segment)[0]
        values={FONT_NAMES[m.group(1)] for m in re.finditer(r'(小四|小五|小三|小二|四|五|三|二)号',text)}
        return values | {float(m.group(1)) for m in re.finditer(r'(\d+(?:\.\d+)?)\s*(?:pt|磅)',text,re.I)}
    if name=='line_spacing':
        if any(w in segment for w in ('固定','最小')): return {'unsupported'}
        return {float(m.group(1)) for m in re.finditer(r'(\d+(?:\.\d+)?)\s*倍',segment)} | ({1.0} if '单倍' in segment else set())
    if name=='first_line_indent':
        if re.search(r'首行[^。；;\n]*?(?:cm|厘米|mm|毫米|pt|磅)',segment,re.I): return {'unsupported'}
        values={float(m.group(1)) for m in re.finditer(r'首行(?:缩进)?\s*(?:为|：|:)?\s*([0123456789]+(?:\.\d+)?)\s*(?:个)?(?:字符|汉字|字)',segment)}
        if any(v in segment for v in ('无首行缩进','首行不缩进','首行缩进为零')): values.add(0)
        return values
    return set()


def _body_segments(text):
    for sentence in re.split(r'[。；;\n]',text):
        subjects=list(re.finditer(r'附\s*录\s*(?:[A-ZＡ-Ｚ]\s*)?(?:文献正文|普通(?:文献)?文字|正文|标题)|致\s*谢\s*(?:正文|普通文字|标题)|(?:中文|英文)?摘要(?:正文|内容|标题)?|Abstract(?:正文|内容|标题)?|参考文献(?:标题|条目|正文)?|(?:脚注|尾注)(?:普通文字|正文|文字)?|(?:中文|英文)?关键词(?:标签|内容|正文)?|正文|标题|图题|表题|题注|页眉|页脚|目录',sentence))
        for i,s in enumerate(subjects):
            if s.group()=='正文': yield sentence[s.start():subjects[i+1].start() if i+1<len(subjects) else len(sentence)]


def body_context(text,quote):
    positions=[m.start() for m in re.finditer(re.escape(quote),text)]
    for start in positions:
        sentence=re.split(r'[。；;\n]',text[:start+len(quote)].rstrip('。；;\n'))[-1]
        subjects=re.findall(r'附\s*录\s*(?:[A-ZＡ-Ｚ]\s*)?(?:文献正文|普通(?:文献)?文字|正文|标题)|致\s*谢\s*(?:正文|普通文字|标题)|(?:中文|英文)?摘要(?:正文|内容|标题)?|Abstract(?:正文|内容|标题)?|参考文献(?:标题|条目|正文)?|(?:脚注|尾注)(?:普通文字|正文|文字)?|(?:中文|英文)?关键词(?:标签|内容|正文)?|正文|标题|图题|表题|题注|页眉|页脚|目录',sentence)
        if not subjects or subjects[-1]!='正文':return False
    return bool(positions)


def page_context(text,quote):
    for m in re.finditer(re.escape(quote),text):
        sentence=re.split(r'[。；;\n]',text[:m.end()].rstrip('。；;\n'))[-1]
        subjects=re.findall(r'标题|摘要|图题|表题|题注|参考文献|页眉|页脚|目录|段落|缩进|页面|纸张|页边距',sentence)
        if subjects and subjects[-1] not in ('页面','纸张','页边距'):return False
    return True


def local_review_notes(segments, *, extended=False):
    """保守补充提示，明确由本地程序产生，不声称由AI返回。"""
    notes=[]
    patterns={
        'landscape':r'横向|横版', 'fixed_spacing':r'固定[^。\n]*(?:行距|磅|pt)',
        'minimum_spacing':r'最小[^。\n]*行距', 'printing':r'打印|装订',
        'indent_unit':r'首行[^。\n]*(?:cm|mm|pt|厘米|毫米|磅)',
        'unknown_font':r'微软雅黑|华文|思源|等线|隶书|Arial Narrow|Cambria',
        'title':r'(?:标题|摘要|题注|图题|表题)[^。\n]*(?:字体|号|行距|缩进)',
    }
    for s in segments:
        for reason,pattern in patterns.items():
            if extended and reason=='title':continue
            if re.search(pattern,s['text'],re.I):notes.append({'location':s['location'],'quote':s['text'][:200],'reason':reason})
    for name in FIELDS:
        candidates=set();origins=[]
        for s in segments:
            parts=[s['text']] if name=='paper' or name.startswith('margin_') else list(_body_segments(s['text']))
            for part in parts:
                values=_values(part,name)
                if values:candidates.update(values);origins.append(s)
        if len(candidates)>1 or 'ambiguous' in candidates:
            for s in origins:notes.append({'location':s['location'],'quote':s['text'][:200],'reason':'conflict' if len(candidates)>1 else 'ambiguous'})
    return notes


def _validate_body_draft(draft, segments):
    validate_segments(segments)
    if not isinstance(draft,dict) or set(draft)!=set(FIELDS)|{'unsupported'}: raise DemoError('AI草稿字段结构无效，拒绝未知可执行字段')
    if not isinstance(draft['unsupported'],list) or len(draft['unsupported'])>40: raise DemoError('不支持提示结构无效')
    byloc={s['location']:s['text'] for s in segments}
    def evidence(f):
        if f['location'] not in byloc or safe_text(f['quote']) not in byloc[f['location']]: raise DemoError('原文依据或来源位置不在所选规范中')
        return byloc[f['location']]
    for note in draft['unsupported']:
        if not isinstance(note,dict) or set(note)!={'quote','location','reason'} or type(note['reason']) is not str or note['reason'] not in REASONS: raise DemoError('不支持提示含未知字段')
        if not isinstance(note['location'],str): raise DemoError('来源位置类型错误')
        evidence(note)
    for name in FIELDS:
        f=draft[name]
        if f is None: continue
        if not isinstance(f,dict) or set(f)!={'value','unit','quote','location','support'} or f['unit']!=FIELDS[name][2] or f['support']!='supported' or not isinstance(f['location'],str): raise DemoError('AI字段结构、单位或支持标记无效')
        value=validate_value(name,f['value']);text=evidence(f)
        if name=='paper' or name.startswith('margin_'):
            if not page_context(text,f['quote']):raise DemoError('不是明确页面要求，不能把标题或摘要局部要求套到全部节')
        if name not in ('paper','margin_top','margin_bottom','margin_left','margin_right') and not body_context(text,f['quote']): raise DemoError('不是明确正文要求，不能将标题/摘要/题注套到正文')
        if name in ('font_cn','font_western'):
            for m in re.finditer(re.escape(f['quote']),text):
                prefix=re.split(r'[。；;\n]',text[:m.end()].rstrip('。；;\n'))[-1]
                slots=re.findall(r'中文|汉字|西文|英文|英语|数字|Latin',prefix,re.I)
                if slots and (slots[-1] in ('中文','汉字')) != (name=='font_cn'):raise DemoError('中文/西文字体范围不一致，不能套到另一字体槽位')
                if name=='font_western' and not slots:raise DemoError('西文字体缺少明确西文范围，请人工确认')
        if _values(f['quote'],name)!={value}: raise DemoError('提取值与原文依据不一致或无法证明，请手动确认')
        candidates=set()
        from .norms import evidence_segments
        for s in evidence_segments(segments,f['location']):
            parts=[s['text']] if name=='paper' or name.startswith('margin_') else list(_body_segments(s['text']))
            for part in parts: candidates.update(_values(part,name))
        if candidates!={value}: raise DemoError('规范要求冲突、含糊或不支持，不能自动应用，请人工确认')
    return deepcopy(draft)


def defaults(base, *, extended=False):
    out={'paper':'A4 portrait'}
    for side in ('top','bottom','left','right'): out['margin_'+side]=base['rules']['R02']['expected'][side+'_mm']
    for field,rid in [('font_cn','R03'),('font_western','R04'),('font_size','R05'),('line_spacing','R06'),('first_line_indent','R07')]: out[field]=base['rules'][rid]['expected']
    if extended:
        from .extended import EXPECTED
        for n in EXT_FIELDS:
            obj,prop=split_field(n)
            cfg=EXPECTED['R'+str(7+int(obj[-1])).zfill(2)] if obj.startswith('heading') else EXPECTED['R12']
            out[n]=cfg[{'font_size':'size_pt','line_spacing':'line_multiple'}.get(prop,prop)]
    return out


def make_template(name, values, sources, segments, base, *, norm_sha256=None, imported=False, extraction=None, compatibility=None):
    extended=set(values)==set(ALL_FIELDS)
    fields=ALL_FIELDS if extended else FIELDS
    data={'structure_version':LATEST_VERSION if extended else VERSION,'name':safe_text(name,80),'supported_fields':list(fields),
          'base_sha256':base['sha256'],'final_values':deepcopy(values),'field_sources':deepcopy(sources),
          'norm_excerpt':deepcopy(segments),'norm_file_sha256':norm_sha256,
          'extraction':deepcopy(extraction) if extraction else {'kind':'none','model':None,'timestamp_utc':None},
          'confirmation':{'method':'local_user','timestamp_utc':datetime.now(timezone.utc).isoformat(),'imported':imported}}
    if extended:
        data['extension_base_sha256']=extension_hash()
        data['compatibility']=deepcopy(compatibility)
    return validate_template(data,base)


def validate_template(data, base):
    if isinstance(data,dict) and data.get('structure_version')==6:
        from .back_templates import validate
        return validate(data,base)
    if isinstance(data,dict) and data.get('structure_version')==5:
        from .table_templates import validate
        return validate(data,base)
    if isinstance(data,dict) and data.get('structure_version')==4:
        from .academic_templates import validate
        return validate(data,base)
    keys={'structure_version','name','supported_fields','base_sha256','final_values','field_sources','norm_excerpt','norm_file_sha256','confirmation'}
    if not isinstance(data,dict) or type(data.get('structure_version')) is not int or data['structure_version'] not in (VERSION,LATEST_VERSION):raise DemoError('模板结构版本无效')
    extended=data['structure_version']==LATEST_VERSION
    fields=ALL_FIELDS if extended else FIELDS
    if extended:keys|={'extension_base_sha256','compatibility'}
    if set(data) not in (keys,keys|{'extraction'}) or data['supported_fields']!=list(fields):raise DemoError('模板结构或支持字段无效')
    if extended:
        if data['extension_base_sha256']!=extension_hash():raise DemoError('固定标题题注基础版本已变化，请重新核对')
        compatibility=data['compatibility']
        if compatibility is not None and (not isinstance(compatibility,dict) or set(compatibility)!={'from_version','method'} or type(compatibility['from_version']) is not int or compatibility['from_version']!=2 or compatibility['method']!='local_default_extension'):raise DemoError('模板兼容转换信息无效')
    data=deepcopy(data)
    extraction=data.setdefault('extraction',{'kind':'unverified_import','model':None,'timestamp_utc':None})
    if not isinstance(extraction,dict) or set(extraction)!={'kind','model','timestamp_utc'} or type(extraction['kind']) is not str or extraction['kind'] not in ('none','real_api','mock_api','unverified_import'):raise DemoError('模板解析来源结构无效')
    if extraction['kind'] in ('real_api','mock_api'):
        if extraction['model'] not in ('deepseek-flash','deepseek-v4-pro'):raise DemoError('模板模型记录无效')
        safe_text(extraction['timestamp_utc'],40)
        try:datetime.fromisoformat(extraction['timestamp_utc'])
        except ValueError:raise DemoError('模板解析时间无效') from None
    elif extraction['model'] is not None or extraction['timestamp_utc'] is not None:raise DemoError('未解析或未验真的来源不能自报模型/时间')
    safe_text(data['name'],80)
    if any(v in data['name'] for v in ('官方','华工','学校','华南理工')): raise DemoError('自定义模板名称不能冒充学校官方规范')
    if data['base_sha256']!=base['sha256']: raise DemoError('默认基础版本已变化，请重新创建模板')
    if data['norm_file_sha256'] is not None and (not isinstance(data['norm_file_sha256'],str) or not re.fullmatch('[a-f0-9]{64}',data['norm_file_sha256'])): raise DemoError('规范文件哈希无效')
    validate_segments(data['norm_excerpt'])
    conf=data['confirmation']
    if not isinstance(conf,dict) or set(conf)!={'method','timestamp_utc','imported'} or conf['method']!='local_user' or type(conf['imported']) is not bool: raise DemoError('模板确认结构无效')
    safe_text(conf['timestamp_utc'],40)
    try: datetime.fromisoformat(conf['timestamp_utc'])
    except ValueError: raise DemoError('模板确认时间无效') from None
    if not isinstance(data['final_values'],dict) or set(data['final_values'])!=set(fields) or not isinstance(data['field_sources'],dict) or set(data['field_sources'])!=set(fields): raise DemoError('模板必须逐项包含全部字段和值来源')
    basevalues=defaults(base,extended=extended);proof={k:None for k in fields};proof['unsupported']=[]
    for name in fields:
        value=validate_value(name,data['final_values'][name]);s=data['field_sources'][name]
        if not isinstance(s,dict) or set(s)!={'kind','quote','location'} or type(s['kind']) is not str or s['kind'] not in SOURCE_LABELS: raise DemoError('模板字段来源无效')
        safe_text(s['quote'],200,allow_empty=True)
        if s['location'] is not None and (not isinstance(s['location'],str) or not LOCATOR.fullmatch(s['location'])): raise DemoError('模板来源位置无效')
        if s['kind'] in ('default_inherited','legacy_fixed'):
            if s['kind']=='legacy_fixed' and (not extended or name not in EXT_FIELDS or data['compatibility'] is None):raise DemoError('旧版固定来源只允许经过本地兼容转换的扩展字段')
            if value!=basevalues[name] or s['quote'] or s['location'] is not None: raise DemoError('默认继承值或来源不一致')
        elif s['kind']=='ai_extracted':
            if extraction['kind']=='none':raise DemoError('没有解析记录，不能标记为AI提取')
            proof[name]={'value':value,'unit':fields[name][2],'quote':s['quote'],'location':s['location'],'support':'supported'}
        elif s['quote']:
            if not any(s['location']==p['location'] and s['quote'] in p['text'] for p in data['norm_excerpt']): raise DemoError('用户修改所保留的原文或位置不真实')
        elif s['location'] is not None: raise DemoError('空依据不能携带来源位置')
    validate_draft(proof,data['norm_excerpt'])
    return deepcopy(data)


def compile_template(data, base):
    if isinstance(data,dict) and data.get('structure_version')==6:
        from .back_templates import compile
        return compile(data,base)
    if isinstance(data,dict) and data.get('structure_version')==5:
        from .table_templates import compile
        return compile(data,base)
    if isinstance(data,dict) and data.get('structure_version')==4:
        from .academic_templates import compile
        return compile(data,base)
    data=validate_template(data,base);fields=field_map(data);out=deepcopy(base)
    out.update(kind='user_confirmed_template',name=data['name'],version='template-demo-'+str(data['structure_version'])+'.0.0',template_structure_version=data['structure_version'],base_sha256=base['sha256'],confirmed=True)
    grouped={r:[] for r in base['rules']}
    for name,(rid,label,unit) in fields.items():
        if name in EXT_FIELDS:continue
        value=data['final_values'][name];s=data['field_sources'][name]
        if name=='paper': out['rules'][rid]['expected']={'width_mm':210,'height_mm':297}
        elif name.startswith('margin_'): out['rules'][rid]['expected'][name[7:]+'_mm']=value
        else: out['rules'][rid]['expected']=value
        origin=SOURCE_LABELS[s['kind']]
        if s['kind']=='ai_extracted' and data['extraction']['kind']=='unverified_import':origin='导入文件的AI来源记录（调用未验真）'
        if s['kind']=='default_inherited':origin+=f'（默认PDF物理页{base["rules"][rid]["page"]}：{base["rules"][rid]["quote"]}）'
        grouped[rid].append(f'{label}={value}：{origin}'+(f'（{s["location"]}：{s["quote"]}；用户修改值不声称由原文精确支持）' if s['kind']=='user_confirmed' and s['quote'] else f'（{s["location"]}：{s["quote"]}）' if s['quote'] else ''))
    for rid,items in grouped.items():
        out['rules'][rid].pop('demo_interpretation',None)
        out['rules'][rid].pop('page',None);out['rules'][rid].pop('quote',None)
        out['rules'][rid]['source']={'file':None,'physical_page':None,'label':'导入模板，经本机重新确认' if data['confirmation']['imported'] else '用户确认的演示模板','quote':'；'.join(items),'parse_kind':data['extraction']['kind'],'fields':{n:deepcopy(data['field_sources'][n]) for n,v in FIELDS.items() if v[0]==rid}}
    if data['structure_version']==LATEST_VERSION:out['extension_config']=compile_extension(data)
    return out


# Explicit object boundaries. Numbers alone (e.g. 1.1) never select a level.
SUBJECT = re.compile(r'附\s*录\s*(?:[A-ZＡ-Ｚ]\s*)?(?:文献正文|普通(?:文献)?文字|正文|标题)|致\s*谢\s*(?:正文|普通文字|标题)|各级标题|[一二三]级标题|标题[123](?![\d.．])|Heading\s*[123](?![\d.])|图题|表题|正文|标题|摘要|题注|参考文献|页眉|页脚|目录', re.I)


def split_field(name):
    for obj in ('heading1','heading2','heading3','figure_caption','table_caption'):
        if name.startswith(obj+'_'):return obj,name[len(obj)+1:]
    return 'body',name


def subject_objects(subject):
    if subject=='各级标题':return {'heading1','heading2','heading3'}
    if subject in ('一级标题','二级标题','三级标题'):return {'heading'+str('一二三'.index(subject[0])+1)}
    if re.fullmatch(r'标题[123]|Heading\s*[123]',subject,re.I):return {'heading'+subject[-1]}
    return {'正文':'body','图题':'figure_caption','表题':'table_caption'}.get(subject,subject),


def object_parts(text, obj):
    for sentence in re.findall(r'[^。；;\n]+[。；;]?',text):
        matches=list(SUBJECT.finditer(sentence))
        for i,m in enumerate(matches):
            targets=subject_objects(m.group())
            if obj in targets:yield sentence[m.start():matches[i+1].start() if i+1<len(matches) else len(sentence)]


def object_values(text, name):
    obj,prop=split_field(name)
    text=SUBJECT.sub('',text).replace('：',' ').replace(':',' ').replace('均','')
    if any(w in text for w in ('任选','或','大约','建议','可能','不超过','至少','至多')):return {'ambiguous'}
    if re.search(r'[-−]\s*\d',text):return {'unsupported'}
    if prop=='alignment':
        return {v for v,label in ALIGNMENTS.items() if label in text} | ({'left'} if '左对齐' in text else set()) | ({'right'} if '右对齐' in text else set()) | ({'center'} if '居中对齐' in text else set())
    if prop=='font_size':
        # Only new title/caption schema adds larger Chinese sizes. Existing body validator unchanged.
        sizes={**FONT_NAMES,'初':42,'小初':36,'一':26,'小一':24}
        clean=re.split(r'行距|缩进',re.sub(r'(?:固定|最小)[^，。；;]*','',text))[0]
        values={sizes[m.group(1)] for m in re.finditer(r'(小初|初|小一|小二|小三|小四|小五|一|二|三|四|五)号',clean)}
        return values|{float(m.group(1)) for m in re.finditer(r'(\d+(?:\.\d+)?)\s*(?:pt|磅)',clean,re.I)}
    return _values(text,prop)


def validate_draft(draft, segments):
    if isinstance(draft,dict) and any(n.startswith(('appendix_','ack_')) for n in draft):
        from .back_templates import validate_draft as back_draft
        return back_draft(draft,segments)
    if isinstance(draft,dict) and any('__' in n for n in draft):
        from .academic_templates import validate_draft as academic_draft
        return academic_draft(draft,segments)
    if isinstance(draft,dict) and set(draft)==set(FIELDS)|{'unsupported'}:
        return _validate_body_draft(draft,segments)
    if not isinstance(draft,dict) or set(draft)!=set(ALL_FIELDS)|{'unsupported'}:raise DemoError('AI对象草稿结构无效，拒绝未知可执行字段')
    _validate_body_draft({n:draft[n] for n in (*FIELDS,'unsupported')},segments)
    byloc={s['location']:s['text'] for s in segments}
    for name in EXT_FIELDS:
        f=draft[name]
        if f is None:continue
        if not isinstance(f,dict) or set(f)!={'value','unit','quote','location','support'} or f['unit']!=ALL_FIELDS[name][2] or f['support']!='supported' or type(f['location']) is not str:raise DemoError('标题/题注字段结构、单位或支持标记无效')
        value=validate_value(name,f['value']);quote=safe_text(f['quote']);text=byloc.get(f['location'])
        if text is None or quote not in text:raise DemoError('原文依据或来源位置不在所选规范中')
        obj,prop=split_field(name)
        parts=list(object_parts(text,obj))
        # All occurrences need unambiguous object scope, not merely matching the end of a broad quote.
        if not any(quote in part for part in parts):raise DemoError('不是明确该级标题或该类题注的要求；不能根据数字或泛称标题猜测')
        if prop=='font_cn' and re.search(r'西文|英文|数字|Latin',quote,re.I):raise DemoError('中文字体字段不能接收西文/数字字体要求')
        if object_values(quote,name)!={value}:raise DemoError('提取值与标题/题注原文不一致、含糊或不支持')
        candidates=set()
        from .norms import evidence_segments
        for s in evidence_segments(segments,f['location']):
            for part in object_parts(s['text'],obj):candidates.update(object_values(part,name))
        if candidates!={value}:raise DemoError('同一对象要求冲突或含糊，不能自动选择；请用户明确取舍')
    return deepcopy(draft)


def object_review_notes(segments):
    notes=local_review_notes(segments,extended=True)
    for s in segments:
        # Generic title has no implicit level; unsupported scope stays visible.
        if any(m.group()=='标题' for m in SUBJECT.finditer(s['text'])):
            notes.append({'location':s['location'],'quote':s['text'][:200],'reason':'ambiguous'})
        if re.search(r'摘要|题注[^。\n]*行距|段前|段后|编号|章前|加粗',s['text']):
            notes.append({'location':s['location'],'quote':s['text'][:200],'reason':'unsupported'})
    for name in EXT_FIELDS:
        obj,_=split_field(name);values=set();origins=[]
        for s in segments:
            for part in object_parts(s['text'],obj):
                v=object_values(part,name)
                if v:values.update(v);origins.append(s)
        if len(values)>1 or 'ambiguous' in values:
            for s in origins:notes.append({'location':s['location'],'quote':s['text'][:200],'reason':'conflict' if len(values)>1 else 'ambiguous'})
    return notes


def extension_hash():
    from .extended import EXTENDED_RULES
    from .package import sha256
    return sha256(EXTENDED_RULES.read_bytes())


def upgrade_template(data, base):
    """Explicit local v2→v3 conversion; never silently change old body or fixed extension meaning."""
    data=validate_template(data,base)
    if data['structure_version']==LATEST_VERSION:return data
    values=defaults(base,extended=True);values.update(data['final_values'])
    sources=deepcopy(data['field_sources'])
    sources.update({n:{'kind':'legacy_fixed','quote':'','location':None} for n in EXT_FIELDS})
    return make_template(data['name'],values,sources,data['norm_excerpt'],base,
                         norm_sha256=data['norm_file_sha256'],imported=True,extraction=data['extraction'],
                         compatibility={'from_version':2,'method':'local_default_extension'})


def compile_extension(data):
    from .extended import EXPECTED
    expected=deepcopy(EXPECTED);by_rule={}
    captions={obj:deepcopy(EXPECTED['R12']) for obj in ('figure_caption','table_caption')}
    for name,(rid,label,unit) in EXT_FIELDS.items():
        obj,prop=split_field(name);key={'font_size':'size_pt','line_spacing':'line_multiple'}.get(prop,prop)
        target=expected[rid] if rid!='R12' else captions[obj]
        target[key]=data['final_values'][name]
        source=deepcopy(data['field_sources'][name]);kind=source['kind']
        origin=SOURCE_LABELS[kind]
        if kind=='ai_extracted' and data['extraction']['kind']=='unverified_import':origin='导入文件的AI来源记录（调用未验真）'
        desc=label+'='+str(data['final_values'][name])+'：'+origin
        if source['quote']:desc+='（'+source['location']+'：'+source['quote']+('；修改值不声称由原文精确支持' if kind=='user_confirmed' else '')+'）'
        src={'label':'导入模板，经本机重新确认' if data['confirmation']['imported'] else '用户确认的演示模板',
             'file':None,'physical_page':None,'quote':desc,'field':name,'origin':source,'parse_kind':data['extraction']['kind']}
        property_name={'font_cn':'font_eastAsia','font_size':'size','line_spacing':'line','alignment':'alignment'}[prop]
        by_rule.setdefault(obj if rid=='R12' else rid,{})[property_name]=src
    # Western slots are deliberately outside new custom scope; keep original default with its true source.
    expected['R12']=captions
    return {'expected':{rid:expected[rid] for rid in ('R08','R09','R10','R12')},'property_sources':by_rule,'compatibility':deepcopy(data['compatibility'])}

"""显式自定义入口的严格数据校验；不包含第二套文档检查器。"""
from copy import deepcopy
import json
import math
from pathlib import Path
from .package import DemoError, sha256

CUSTOM_NAME = '用户确认的演示规则'
CUSTOM_VERSION = 'custom-demo-1.0.0'
KINDS = {'ai_extracted':'AI提取后用户确认', 'user_confirmed':'用户确认值', 'default_inherited':'沿用默认值'}

def strict_json(text):
    def constant(_): raise DemoError('JSON包含非有限数值')
    def pairs(items):
        out={}
        for key,value in items:
            if key in out: raise DemoError('JSON包含重复字段')
            out[key]=value
        return out
    try:
        return json.loads(text, parse_constant=constant, object_pairs_hook=pairs)
    except (ValueError, TypeError) as exc:
        raise DemoError('返回或配置不是有效JSON') from exc

def validate_value(rule, value):
    try:
        finite = type(value) in (int,float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise DemoError('格式值必须为有限数字，不能是布尔值或字符串')
    if rule=='R05' and not (8<=value<=24 and value*2==round(value*2)):
        raise DemoError('正文普通文字字号仅支持8–24pt，0.5pt步长')
    if rule=='R06' and value not in (1.0,1.25,1.5,2.0):
        raise DemoError('正文倍数行距仅支持1、1.25、1.5、2倍')
    if rule not in ('R05','R06'):raise DemoError('只允许自定义R05、R06')
    return value

def validate_source(source, rule, value, base):
    keys={'kind','label','quote','input_text','file','physical_page','model','parse_kind'}
    if not isinstance(source,dict) or set(source)!=keys or source.get('kind') not in KINDS:
        raise DemoError('自定义字段来源结构无效')
    kind=source['kind']
    if source['label']!=KINDS[kind] or not isinstance(source['quote'],str) or not 1<=len(source['quote'])<=200:
        raise DemoError('自定义来源说明无效')
    if not isinstance(source['input_text'],str) or len(source['input_text'])>2000:
        raise DemoError('规范输入来源无效')
    from .spec_validation import validate_text, DANGEROUS
    if source['input_text']:
        validate_text(source['input_text'])
    if DANGEROUS.search(source['quote']):
        raise DemoError('来源不接受代码、文件路径、密钥或工具指令')
    if kind=='default_inherited':
        cfg=base['rules'][rule]
        if value!=cfg['expected'] or source['file']!=base['source_file'] or source['physical_page']!=cfg['page'] or source['quote']!=cfg['quote']:
            raise DemoError('默认继承来源或数值不一致')
        if source['model'] is not None or source['parse_kind'] is not None:
            raise DemoError('默认继承不能标为AI提取')
    else:
        if source['file'] is not None or source['physical_page'] is not None:
            raise DemoError('自定义值不能伪造学校PDF依据')
        if kind=='ai_extracted':
            if source['quote'] not in source['input_text'] or source['parse_kind'] not in ('real_api','mock_api') or source['model'] not in ('deepseek-flash','deepseek-v4-pro'):
                raise DemoError('AI原文、模型或调用来源无效')
            from .spec_validation import validate_draft
            name='font_size' if rule=='R05' else 'line_spacing'
            draft={'font_size':None,'line_spacing':None,'unsupported':[]}
            draft[name]={'value':value,'quote':source['quote']}
            validate_draft(draft,source['input_text'])
        elif source['model'] is not None or source['parse_kind'] is not None:
            raise DemoError('用户确认值不能标为AI精确提取')

def make_custom_config(base, values, sources):
    if set(values)!= {'R05','R06'} or set(sources)!= {'R05','R06'}:
        raise DemoError('必须明确决定两个自定义字段，包括默认继承')
    data={k:deepcopy(base[k]) for k in ('scope','source_file','rules')}
    data.update(kind='user_confirmed_demo', name=CUSTOM_NAME, version=CUSTOM_VERSION,
                base_sha256=base['sha256'], confirmed=True)
    for rule in ('R05','R06'):
        value=validate_value(rule,values[rule])
        validate_source(sources[rule],rule,value,base)
        data['rules'][rule]={'name':base['rules'][rule]['name'],'unit':base['rules'][rule]['unit'],
                             'expected':value,'source':deepcopy(sources[rule])}
    validate_custom_config(data,base)
    return data

def validate_custom_config(data,base):
    keys={'kind','name','version','scope','source_file','rules','base_sha256','confirmed'}
    if not isinstance(data,dict) or set(data)!=keys or data['kind']!='user_confirmed_demo' or data['name']!=CUSTOM_NAME or data['version']!=CUSTOM_VERSION or data['confirmed'] is not True:
        raise DemoError('需要明确确认的演示自定义配置')
    if data['base_sha256']!=base['sha256'] or data['scope']!=base['scope'] or data['source_file']!=base['source_file']:
        raise DemoError('基础演示规则已变化或来源不一致，请重新确认')
    if not isinstance(data['rules'],dict) or set(data['rules'])!=set(base['rules']):
        raise DemoError('自定义配置必须保留R01–R07')
    for rule,cfg in data['rules'].items():
        if rule not in ('R05','R06'):
            if cfg!=base['rules'][rule]:raise DemoError('其他规则不得自定义')
        else:
            if not isinstance(cfg,dict) or set(cfg)!= {'name','unit','expected','source'} or cfg['name']!=base['rules'][rule]['name'] or cfg['unit']!=base['rules'][rule]['unit']:
                raise DemoError('自定义规则字段无效')
            validate_value(rule,cfg['expected'])
            validate_source(cfg['source'],rule,cfg['expected'],base)
    return data

def read_custom_config(path,base):
    raw=Path(path).read_bytes()
    if len(raw)>160*1024:raise DemoError('自定义配置过大')
    try: data=strict_json(raw.decode('utf-8'))
    except UnicodeError: raise DemoError('配置须为UTF-8 JSON') from None
    if isinstance(data,dict) and data.get('format')=='paper-grid-rule-bundle':
        from .rule_bundle import compile_bundle
        data=compile_bundle(data,base)
    elif isinstance(data,dict) and 'structure_version' in data:
        from .templates import compile_template
        data=compile_template(data,base)
    else: data=validate_custom_config(data,base)
    data['sha256']=sha256(raw)
    return data

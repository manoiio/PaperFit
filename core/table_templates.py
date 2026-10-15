"""v5 adds two explicit table text fields; v2-v4 semantics remain unchanged."""
from copy import deepcopy
import json,re
from . import academic_templates as academic
from . import templates as old
from .table_text import PATH
from .package import DemoError,sha256

EXTRA={'table_content__font_cn':('R23','论文内容表格 中文字体','font'),'table_content__font_size':('R23','论文内容表格 普通字号','pt')}
V5_FIELDS={**academic.V4_FIELDS,**EXTRA}
def defaults(base):
 policy=json.loads(PATH.read_text());return {**academic.default_values(base),**{n:policy[n.split('__')[1]] for n in EXTRA}}
def value(n,v):
 if n not in EXTRA:return academic.value(n,v)
 if v is None:return None
 return academic.value('reference_item__'+n.split('__')[1],v)
def base_v4(data):
 d={k:deepcopy(v) for k,v in data.items() if k not in ('table_base_sha256','table_compatibility')}
 d['structure_version']=4;d['supported_fields']=list(academic.V4_FIELDS)
 d['final_values']={n:d['final_values'][n] for n in academic.V4_FIELDS};d['field_sources']={n:d['field_sources'][n] for n in academic.V4_FIELDS}
 return d
def make(base_template,values,sources,base):
 d=academic.validate(base_template,base);d.update(structure_version=5,supported_fields=list(V5_FIELDS),table_base_sha256=sha256(PATH.read_bytes()),table_compatibility={'from_version':4,'new_fields':'explicit_confirmed_or_disabled'})
 d['final_values'].update(deepcopy(values));d['field_sources'].update(deepcopy(sources));return validate(d,base)
def validate(data,base):
 if type(data) is not dict or set(data)!=set(academic.base_v3_keys())|{'academic_base_sha256','academic_compatibility','table_base_sha256','table_compatibility'} or type(data.get('structure_version')) is not int or data['structure_version']!=5:raise DemoError('v5模板版本或结构无效')
 if data.get('supported_fields')!=list(V5_FIELDS) or type(data.get('final_values')) is not dict or set(data['final_values'])!=set(V5_FIELDS) or type(data.get('field_sources')) is not dict or set(data['field_sources'])!=set(V5_FIELDS):raise DemoError('v5字段须完整且拒绝未知可执行字段')
 if data['table_base_sha256']!=sha256(PATH.read_bytes()) or type(data['table_compatibility']) is not dict or type(data['table_compatibility'].get('from_version')) is not int or data['table_compatibility']!={'from_version':4,'new_fields':'explicit_confirmed_or_disabled'}:raise DemoError('表格规则版本或兼容转换信息无效')
 academic.validate(base_v4(data),base)
 for n in EXTRA:
  v=value(n,data['final_values'][n]);s=data['field_sources'][n]
  if type(s) is not dict or set(s)!={'kind','quote','location'} or type(s['kind']) is not str or s['kind'] not in academic.KINDS:raise DemoError('表格字段来源无效')
  old.safe_text(s['quote'],200,allow_empty=True)
  if v is None:
   if s!={'kind':'not_enabled','quote':'','location':None}:raise DemoError('表格未配置值不能伪造默认或AI来源')
  elif s['kind']=='not_enabled':raise DemoError('未启用字段不得携带值')
  elif s['kind']=='default_inherited':
   if v!=defaults(base)[n] or s['quote'] or s['location'] is not None:raise DemoError('表格默认继承值不匹配')
  elif s['kind']=='ai_extracted':
   if data['extraction']['kind']=='none':raise DemoError('表格AI来源缺少解析记录')
   candidate(n,{'value':v,'unit':EXTRA[n][2],'quote':s['quote'],'location':s['location'],'support':'supported'},data['norm_excerpt'])
  elif s['quote'] and not any(x['location']==s['location'] and s['quote'] in x['text'] for x in data['norm_excerpt']):raise DemoError('表格人工值保留依据不真实')
  elif not s['quote'] and s['location'] is not None:raise DemoError('空依据不得携带位置')
 if len((json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())>64*1024:raise DemoError('v5模板超过64KB，请缩短摘录')
 return deepcopy(data)
def context(quote):return bool(re.search(r'表(?:内|格内|格中的|格中|格普通)(?:普通)?(?:文字|文本)|论文内容表格',quote)) and not re.search(r'表题|题注|正文|封面',quote)
def candidate(n,f,segments):
 from .norms import evidence_segments
 if type(f) is dict:segments=evidence_segments(segments,f.get('location'))
 if type(f) is not dict or set(f)!={'value','unit','quote','location','support'} or f['unit']!=EXTRA[n][2] or f['support']!='supported':raise DemoError('表格提取字段结构或单位无效')
 if type(f['quote']) is not str or not context(f['quote']) or not any(s['location']==f['location'] and f['quote'] in s['text'] for s in segments):raise DemoError('表格依据必须来自明确表内文字，不把表题/正文套入表格')
 old.safe_text(f['quote'],200)
 v=value(n,f['value'])
 if v is None:raise DemoError('表格AI提取不能携带空执行值')
 quotes=[c for s in segments for c in re.split('[。；;\n]',s['text']) if context(c)]
 def candidates(q):
  if n.endswith('font_cn'):
   clean=re.sub(r'论文内容表格|表(?:内|格内|格中的|格中|格普通)(?:普通)?(?:文字|文本)','',q)
   clean=re.sub(r'小(?:二|三|四|五)(?:号)?|(?:二|三|四|五)号','',clean)
   return old.font_candidates(clean,'font_cn')
  from .spec_validation import FONT_NAMES
  return {float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*(?:pt|磅)',q,re.I)}|{FONT_NAMES[m.group(0).rstrip('号')] for m in re.finditer(r'小(?:二|三|四|五)(?:号)?|(?:二|三|四|五)号',q)}
 if candidates(f['quote'])!={v} or len(set().union(*(candidates(q) for q in quotes)))!=1:raise DemoError('表格依据数值/字体不匹配或要求冲突，须人工确认')
 return deepcopy(f)
def validate_draft(data,segments):
 if type(data) is not dict or set(data)!=set(V5_FIELDS)|{'unsupported'}:raise DemoError('v5草稿字段不完整或含未知执行字段')
 academic.validate_draft({n:v for n,v in data.items() if n not in EXTRA},segments)
 for n in EXTRA:
  if data[n] is not None:candidate(n,data[n],segments)
 return deepcopy(data)
def compile(data,base):
 d=validate(data,base);out=academic.compile(base_v4(d),base)
 out.update(name=d['name'],version='template-demo-5.0.0',template_structure_version=5,table_config={'values':{n.split('__')[1]:d['final_values'][n] for n in EXTRA},'sources':{n.split('__')[1]:{**deepcopy(d['field_sources'][n]),'label':academic.KINDS[d['field_sources'][n]['kind']]+'（用户确认v5表格要求）','physical_page':None,'file':None} for n in EXTRA}})
 return out

"""v6 value/source fields extend v5 without changing historic schema meaning."""
from copy import deepcopy
import json,re
from . import table_templates as prior,academic_templates as academic,templates as old
from .backmatter import TYPES,PROPS,FIELDS as EXTRA,PATH,defaults as flat
from .package import DemoError,sha256
V6_FIELDS={**prior.V5_FIELDS,**{n:(rid,TYPES[obj]+' '+academic.LABELS.get(prop,prop),'spacing' if prop in ('before','after') else 'bool' if prop=='bold' else 'font' if prop in ('font_cn','font_western') else 'pt' if prop=='font_size' else 'multiple' if prop=='line_spacing' else 'chars' if prop=='first_line_indent' else 'alignment') for n,(rid,obj,prop) in EXTRA.items()}}
PATTERNS={'appendix_title':r'附\s*录\s*(?:[A-Z]\s*)?标题','appendix_text':r'附\s*录\s*(?:[A-Z]\s*)?(?:文献正文|普通(?:文献)?文字|正文)','ack_title':r'致谢标题','ack_text':r'致谢(?:正文|普通文字)'}
def value(n,v):
 if n not in EXTRA:return prior.value(n,v)
 _,obj,prop=EXTRA[n];return academic.value(('reference_title' if obj.endswith('title') else 'reference_item')+'__'+prop,v)
def defaults(base):return {**prior.defaults(base),**flat()}
def base_v5(d):
 out={k:deepcopy(v) for k,v in d.items() if k not in ('backmatter_base_sha256','backmatter_compatibility')};out.update(structure_version=5,supported_fields=list(prior.V5_FIELDS));out['final_values']={n:d['final_values'][n] for n in prior.V5_FIELDS};out['field_sources']={n:d['field_sources'][n] for n in prior.V5_FIELDS};return out

def upgrade(d,base):
 d=old.validate_template(d,base)
 if d['structure_version'] in (6,7):return d
 if d['structure_version']<4:d=academic.make(d,{n:None for n in academic.EXTRA},{n:{'kind':'not_enabled','quote':'','location':None} for n in academic.EXTRA},d['norm_excerpt'],base)
 if d['structure_version']==4:d=prior.make(d,{n:None for n in prior.EXTRA},{n:{'kind':'not_enabled','quote':'','location':None} for n in prior.EXTRA},base)
 d.update(structure_version=6,supported_fields=list(V6_FIELDS),backmatter_base_sha256=sha256(PATH.read_bytes()),backmatter_compatibility={'from_version':5,'new_fields':'explicit_confirmed_or_disabled'})
 d['final_values'].update({n:None for n in EXTRA});d['field_sources'].update({n:{'kind':'not_enabled','quote':'','location':None} for n in EXTRA});return validate(d,base)

def context(obj,quote):
 return bool(re.search(PATTERNS[obj],quote)) and not any(re.search(p,quote) for k,p in PATTERNS.items() if k!=obj)
def candidate(n,f,segments):
 from .norms import evidence_segments
 if type(f) is dict:segments=evidence_segments(segments,f.get('location'))
 # Reuse the proven attribute/unit/finite/source validator, with a precise object-local proof projection.
 if type(f) is not dict or type(f.get('quote')) is not str or not any(f.get('location')==s['location'] and f['quote'] in s['text'] for s in segments):raise DemoError('新增对象依据不存在')
 _,obj,prop=EXTRA[n]
 if not context(obj,f['quote']):raise DemoError('附录/致谢对象范围不明确，不能串用正文或其他标题')
 if obj=='appendix_text' and any(re.search(r'附录(?:正文)?\s*(?:均|全部|都|为|是)[^。；\n]*代码',s['text']) for s in segments):raise DemoError('附录被说明为代码；不能解析为普通文字统一修正授权')
 target='reference_title' if obj.endswith('title') else 'reference_item';label='参考文献标题' if obj.endswith('title') else '参考文献条目'
 projected=[]
 for s in segments:
  clauses=[re.sub(PATTERNS[obj],label,c) for c in re.findall(r'[^。；;\n]+[。；;]?',s['text']) if context(obj,c)]
  projected.append({'location':s['location'],'text':'；'.join(clauses)})
 cf=deepcopy(f);cf['quote']=re.sub(PATTERNS[obj],label,cf['quote']);academic.validate_candidate(target+'__'+prop,cf,projected);value(n,f['value']);return deepcopy(f)
def validate_draft(d,segments):
 if type(d) is not dict or set(d)!=set(V6_FIELDS)|{'unsupported'}:raise DemoError('v6草稿字段不完整或含未知执行字段')
 prior.validate_draft({n:v for n,v in d.items() if n not in EXTRA},segments)
 for n in EXTRA:
  if d[n] is not None:candidate(n,d[n],segments)
 return deepcopy(d)
def validate(d,base):
 if type(d) is not dict or set(d)!=set(academic.base_v3_keys())|{'academic_base_sha256','academic_compatibility','table_base_sha256','table_compatibility','backmatter_base_sha256','backmatter_compatibility'} or type(d.get('structure_version')) is not int or d['structure_version']!=6:raise DemoError('v6模板结构或版本无效')
 if d.get('supported_fields')!=list(V6_FIELDS) or type(d.get('final_values')) is not dict or set(d['final_values'])!=set(V6_FIELDS) or type(d.get('field_sources')) is not dict or set(d['field_sources'])!=set(V6_FIELDS):raise DemoError('v6完整值/来源字段无效')
 if d['backmatter_base_sha256']!=sha256(PATH.read_bytes()) or d['backmatter_compatibility']!={'from_version':5,'new_fields':'explicit_confirmed_or_disabled'} or type(d['backmatter_compatibility']['from_version']) is not int:raise DemoError('附录/致谢基础版本或兼容信息无效')
 prior.validate(base_v5(d),base)
 for n in EXTRA:
  v=value(n,d['final_values'][n]);s=d['field_sources'][n]
  if type(s) is not dict or set(s)!={'kind','quote','location'} or (type(s['kind']) is not str or s['kind'] not in academic.KINDS):raise DemoError('v6来源无效')
  old.safe_text(s['quote'],200,allow_empty=True)
  if v is None:
   if s!={'kind':'not_enabled','quote':'','location':None}:raise DemoError('未启用字段不能伪造来源')
  elif s['kind']=='not_enabled':raise DemoError('未启用不得携带执行值')
  elif s['kind']=='default_inherited':
   if v!=flat()[n] or s['quote'] or s['location'] is not None:raise DemoError('附录/致谢默认继承值不匹配')
  elif s['kind']=='ai_extracted':
   if d['extraction']['kind']=='none':raise DemoError('AI来源缺少本地解析记录')
   candidate(n,{'value':v,'unit':V6_FIELDS[n][2],'quote':s['quote'],'location':s['location'],'support':'supported'},d['norm_excerpt'])
  elif s['quote'] and not any(s['location']==p['location'] and s['quote'] in p['text'] for p in d['norm_excerpt']):raise DemoError('人工修改保留依据不真实')
  elif not s['quote'] and s['location'] is not None:raise DemoError('空依据不能携带位置')
 if len(json.dumps(d,ensure_ascii=False,allow_nan=False,indent=2).encode())>65536:raise DemoError('v6模板超过64KB，请缩短摘录')
 return deepcopy(d)
def compile(d,base):
 d=validate(d,base);out=prior.compile(base_v5(d),base);objects={obj:{} for obj in TYPES};sources={obj:{} for obj in TYPES}
 for n,(_,obj,p) in EXTRA.items():
  objects[obj][p]=deepcopy(d['final_values'][n]);s=deepcopy(d['field_sources'][n]);sources[obj][p]={**s,'file':None,'physical_page':None,'label':academic.KINDS[s['kind']]+'（用户确认v6附录/致谢模板，不冒充学校原文）'}
 out.update(name=d['name'],version='template-demo-6.0.0',template_structure_version=6,back_config={'objects':objects,'sources':sources});return out

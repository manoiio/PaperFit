"""v8 explicit character effects; old v2–v7 templates never enable them."""
from copy import deepcopy
from . import paragraph_templates as old,text_effects as effects
from .package import DemoError
FIELDS={**old.FIELDS,**effects.FIELDS}
EMPTY={'kind':'not_enabled','quote':'','location':None}
def base(d):
 c=deepcopy(d);c.update(structure_version=7,supported_fields=list(old.FIELDS))
 for k in ('final_values','field_sources'):c[k]={n:c[k][n] for n in old.FIELDS}
 return c
def validate(d,b):
 if type(d) is not dict or d.get('structure_version')!=8 or d.get('supported_fields')!=list(FIELDS) or set(d.get('final_values',{}))!=set(FIELDS) or set(d.get('field_sources',{}))!=set(FIELDS):raise DemoError('v8文字效果模板字段/版本无效')
 old.validate(base(d),b)
 effects.validate_requested(d['final_values'])
 from .rule_bundle import source
 for n in effects.FIELDS:
  v=effects.value(n,d['final_values'][n]);s=d['field_sources'][n];source(s,v,d['norm_excerpt'])
  if v is not None and s['kind'] not in ('user_confirmed','ai_extracted'):raise DemoError('文字效果必须来自明确要求，不继承学校默认')
  if s['kind']=='ai_extracted':
   if d['extraction']['kind']=='none':raise DemoError('AI效果来源缺少解析记录')
   effects.candidate(n,{'value':v,'unit':effects.FIELDS[n][2],'quote':s['quote'],'location':s['location'],'support':'supported'},d['norm_excerpt'])
 return deepcopy(d)
def wrap(d,values,sources,b):
 if not any(values.get(n) is not None for n in effects.FIELDS):return d
 # Promote even a v6 carrier through the existing v7 schema without new defaults.
 c=deepcopy(d);c.update(structure_version=8,supported_fields=list(FIELDS))
 for n in FIELDS:
  c['final_values'][n]=deepcopy(values.get(n,c['final_values'].get(n)))
  c['field_sources'][n]=deepcopy(sources.get(n,c['field_sources'].get(n,EMPTY)))
 return validate(c,b)
def compile(d,b):
 d=validate(d,b);out=old.compile(base(d),b);cfg={}
 for n in effects.FIELDS:
  v=d['final_values'][n]
  if v is None:continue
  obj,p=n.split('__');cfg.setdefault(obj,{})[p]={'value':v,'source':{**deepcopy(d['field_sources'][n]),'label':'明确普通文字要求（v8）','file':None,'physical_page':None}}
 out.update(text_normalization=cfg,template_structure_version=8,version='template-demo-8.0.0');return out

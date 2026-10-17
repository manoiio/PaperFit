"""v7 adds caption line declarations; older carriers stay byte/schema compatible."""
from copy import deepcopy
import json
from . import back_templates as old,academic_templates as a
from .package import DemoError
EXTRA={o+'__line_spacing':('R13',label+' 行距','multiple') for o,label in [('figure_caption','图题'),('table_caption','表题')]}
FIELDS={**old.V6_FIELDS,**EXTRA}
def base(d):
 c=deepcopy(d);c['structure_version']=6;c['supported_fields']=list(old.V6_FIELDS)
 for group in ('final_values','field_sources'):c[group]={n:c[group][n] for n in old.V6_FIELDS}
 return c
def candidate(n,f,segments):
 # Same native candidate/value/source machinery, with the real caption context.
 a.validate_candidate_for(n.split('__')[0],'line_spacing',f,segments)
def validate(d,b):
 if type(d) is not dict or d.get('structure_version')!=7 or d.get('supported_fields')!=list(FIELDS) or set(d.get('final_values',{}))!=set(FIELDS) or set(d.get('field_sources',{}))!=set(FIELDS):raise DemoError('v7段落模板字段/版本无效')
 old.validate(base(d),b)
 for n in EXTRA:
  v=d['final_values'][n];s=d['field_sources'][n]
  if v is not None:
   from .paragraph_values import line
   line(v)
  if type(s) is not dict or set(s)!={'kind','quote','location'} or s['kind'] not in a.KINDS:raise DemoError('v7来源无效')
  a.old.safe_text(s['quote'],200,allow_empty=True)
  if s['location'] is not None and (type(s['location']) is not str or not a.old.LOCATOR.fullmatch(s['location'])):raise DemoError('v7来源位置无效')
  if v is None:
   if s!={'kind':'not_enabled','quote':'','location':None}:raise DemoError('未配置字段不得携带来源')
  elif s['kind']=='ai_extracted':
   if d['extraction']['kind']=='none':raise DemoError('AI来源缺少真实/模拟解析记录')
   candidate(n,{'value':v,'unit':'multiple','quote':s['quote'],'location':s['location'],'support':'supported'},d['norm_excerpt'])
  elif s['kind']!='user_confirmed':raise DemoError('新增字段不自动继承学校默认')
  elif s['quote'] and not any(x['location']==s['location'] and s['quote'] in x['text'] for x in d['norm_excerpt']):raise DemoError('人工来源无效')
  elif not s['quote'] and s['location'] is not None:raise DemoError('空依据位置无效')
 if len(json.dumps(d,ensure_ascii=False,allow_nan=False,indent=2).encode())>65536:raise DemoError('v7模板超过64KB')
 return deepcopy(d)
def wrap(d,values,sources,b):
 if not any(values.get(n) is not None for n in EXTRA):return d
 c=deepcopy(d);c.update(structure_version=7,supported_fields=list(FIELDS));c['final_values'].update({n:deepcopy(values.get(n)) for n in EXTRA});c['field_sources'].update({n:deepcopy(sources.get(n,{'kind':'not_enabled','quote':'','location':None})) for n in EXTRA});return validate(c,b)
def compile(d,b):
 d=validate(d,b);r=old.compile(base(d),b)
 for n in EXTRA:
  o=n.split('__')[0];r['academic_config']['objects'][o]['line_spacing']=deepcopy(d['final_values'][n]);r['academic_config']['sources'][o]['line_spacing']={**deepcopy(d['field_sources'][n]),'file':None,'physical_page':None,'label':'用户明确配置的题注行距（v7；未冒充学校默认）'}
 r.update(template_structure_version=7,version='template-demo-7.0.0');return r

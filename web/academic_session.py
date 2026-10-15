"""v4 draft lifecycle reuses TemplateSession and its active-file/confirmation guards."""
from copy import deepcopy
from core.academic_templates import V4_FIELDS,EXTRA,flat_defaults,default_values,make,validate,value,base_v3
from core import load_rules
from core import templates as old
from core.package import DemoError
from core.backmatter import FIELDS as BACK_FIELDS

class AcademicSession:
 def start_academic_template(self):
  base=load_rules(self.rules_path)
  source=self.template_import or self.active_template
  if source:
   if source['structure_version'] in (4,5,6):return self.import_template(__import__('json').dumps(source,ensure_ascii=False).encode())
   data=deepcopy(source)
  else:
   data=old.make_template('单文档演示自定义要求',old.defaults(base,extended=True),{n:{'kind':'default_inherited','quote':'','location':None} for n in old.ALL_FIELDS},[],base)
  imported=make(data,{n:None for n in EXTRA},{n:{'kind':'not_enabled','quote':'','location':None} for n in EXTRA},data['norm_excerpt'],base,name='单文档演示自定义要求')
  self.import_template(__import__('json').dumps(imported,ensure_ascii=False).encode())

 def academic_defaults(self,only_missing=True):
  for n in self.template_fields:
   if only_missing and self.template_modes.get(n)!='choose':continue
   self.template_modes[n]='default';self.template_values[n]=self.academic_values()[n]

 def academic_disable_missing(self):
  for n in self.template_fields:
   if n not in EXTRA and n not in BACK_FIELDS and n not in ('table_content__font_cn','table_content__font_size'):continue
   if self.template_modes[n]=='choose':self.template_modes[n]='disabled';self.template_values[n]=None

 def proposed_academic_template(self):
  base=load_rules(self.rules_path);values={};sources={};defaults=self.academic_values()
  for n in self.template_fields:
   mode=self.template_modes[n];candidate=self.template_draft.get(n) if self.template_draft else None
   if mode=='ai' and candidate is None:raise DemoError('字段没有AI提取依据')
   if mode=='choose':raise DemoError('未提到的字段须明确选择默认/手动/未启用')
   if mode=='disabled':
    if n not in EXTRA and n not in BACK_FIELDS and n not in ('table_content__font_cn','table_content__font_size'):raise DemoError('原R01–R12字段不能禁用')
    v=None
   elif mode=='default':v=defaults[n]
   else:v=self.template_values[n]
   if mode=='manual' and v is None:raise DemoError('手动值尚未采用，请填写后点击采用，或明确选择未启用')
   if n in ('table_content__font_cn','table_content__font_size'):
    from core.table_templates import value as tv
    tv(n,v)
   else:old.validate_value(n,v)
   if v is None:
    if n not in EXTRA and n not in BACK_FIELDS and n not in ('table_content__font_cn','table_content__font_size'):raise DemoError('原字段不能为空')
    source={'kind':'not_enabled','quote':'','location':None}
   elif mode=='default':source={'kind':'default_inherited','quote':'','location':None}
   elif mode=='imported' and n not in self.template_touched and v==self.template_import['final_values'][n]:source=deepcopy(self.template_import['field_sources'][n])
   elif mode=='ai' and candidate and n not in self.template_touched and v==candidate['value']:source={'kind':'ai_extracted','quote':candidate['quote'],'location':candidate['location']}
   else:source={'kind':'user_confirmed','quote':candidate['quote'] if candidate else '', 'location':candidate['location'] if candidate else None}
   values[n]=v;sources[n]=source
  b=old.make_template(self.template_name,{n:values[n] for n in old.ALL_FIELDS},{n:sources[n] for n in old.ALL_FIELDS},self.norm_segments,base,imported=self.template_import is not None,extraction={k:self.template_receipt[k] for k in ('kind','model','timestamp_utc')} if self.template_receipt else self.template_import['extraction'] if self.template_import else None)
  v4=make(b,{n:values[n] for n in EXTRA},{n:sources[n] for n in EXTRA},self.norm_segments,base,name=self.template_name)
  if 'table_content__font_cn' in values:
   from core.table_templates import make as tm,EXTRA as te
   v5=tm(v4,{n:values[n] for n in te},{n:sources[n] for n in te},base)
   if any(n in BACK_FIELDS for n in values):
    from core.back_templates import upgrade,validate
    v6=upgrade(v5,base);v6['final_values'].update({n:values[n] for n in BACK_FIELDS});v6['field_sources'].update({n:sources[n] for n in BACK_FIELDS});return validate(v6,base)
   return v5
  return v4

 def upgrade_back_template(self):
  from core.back_templates import upgrade
  source=self.proposed_template() if self.template_import or self.template_draft else self.active_template
  if source is None:self.start_academic_template();source=self.template_import
  self.import_template(__import__('json').dumps(upgrade(source,load_rules(self.rules_path)),ensure_ascii=False).encode())

 def academic_values(self):
  if any(n in BACK_FIELDS for n in self.template_fields):
   from core.back_templates import defaults
   return defaults(load_rules(self.rules_path))
  if 'table_content__font_cn' in self.template_fields:
   from core.table_templates import defaults
   return defaults(load_rules(self.rules_path))
  return default_values(load_rules(self.rules_path))
 def upgrade_table_template(self):
  source=self.proposed_template() if self.template_import or self.template_draft else self.active_template
  if source is None:self.start_academic_template();source=self.template_import
  from core.table_templates import make as tm,EXTRA as te,base_v4
  if source['structure_version']==5:return
  if source['structure_version']!=4:raise DemoError('请先核对升级v4')
  d=tm(source,{n:None for n in te},{n:{'kind':'not_enabled','quote':'','location':None} for n in te},load_rules(self.rules_path))
  self.import_template(__import__('json').dumps(d,ensure_ascii=False).encode())

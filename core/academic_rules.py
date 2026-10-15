"""Opt-in single-document paragraph and front/back section requirements."""
from pathlib import Path
from copy import deepcopy
import json
from .package import sha256,DemoError
NEW_TYPES={'abstract_cn_title':'中文摘要标题','abstract_cn_body':'中文摘要正文','abstract_en_title':'英文摘要标题','abstract_en_body':'英文摘要正文','keywords_cn':'中文关键词行','keywords_en':'英文关键词行','reference_title':'参考文献标题','reference_item':'参考文献条目'}
RULE_FOR={name:f'R{n:02}' for n,name in enumerate(NEW_TYPES,14)}
PATH=Path(__file__).resolve().parents[1]/'rules/scut_2015_sections.json'
GENERIC_TYPES=('body','heading1','heading2','heading3','figure_caption','table_caption')
PROPS=('font_cn','font_western','font_size','line_spacing','first_line_indent','before','after','alignment','bold')
GENERIC={t:('before','after','bold') if t.startswith('heading') else ('before','after','alignment','bold') for t in GENERIC_TYPES}

def field_definitions():
 out={}
 for obj,props in GENERIC.items():
  for prop in props:out[obj+'__'+prop]=('R13',obj,prop)
 for obj in NEW_TYPES:
  props=('before','after','alignment','line_spacing','first_line_indent') if obj.startswith('keywords') else PROPS
  for prop in props:out[obj+'__'+prop]=(RULE_FOR[obj],obj,prop)
  if obj.startswith('keywords'):
   for part in ('label','content'):
    for prop in ('font_cn','font_western','font_size','bold'):out[obj+'__'+part+'_'+prop]=(RULE_FOR[obj],obj,part+'_'+prop)
 out['content_checks']=('R22','document','enabled')
 return out
FIELDS=field_definitions()
LABELS={'before':'段前间距','after':'段后间距','alignment':'对齐','bold':'加粗','font_cn':'中文字体','font_western':'西文字体','font_size':'字号','line_spacing':'倍数行距','first_line_indent':'首行字符缩进','enabled':'只读数量与存在提示'}

def school():return json.loads(PATH.read_text())
def flat_defaults():
 config=school()['objects'];out={}
 for field,(_,obj,prop) in FIELDS.items():out[field]=True if obj=='document' else deepcopy(config[obj].get(prop))
 return out

def extend(base):
 raw=PATH.read_bytes();data=school();out=deepcopy(base)
 custom=base.get('academic_config')
 enabled=not ('kind' in base) or custom is not None
 config=deepcopy(custom['objects'] if custom else data['objects'] if enabled else {t:{} for t in data['objects']})
 out['academic_objects']=config;out['academic_sources']=deepcopy(custom['sources']) if custom else None
 out['content_checks']=custom['content_checks'] if custom else True if enabled else False
 for rid,name in [('R13','通用段落属性')]+[(RULE_FOR[t],label+'格式') for t,label in NEW_TYPES.items()]+[('R22','前后置章节只读内容提示')]:
  out['rules'][rid]={'name':name,'expected':config if rid=='R13' else config[next(t for t in NEW_TYPES if RULE_FOR[t]==rid)] if rid!='R22' else {'cn_abstract_characters':[400,600],'keyword_count':[3,5],'confirmed_reference_count_min':10},'page':None,'quote':'属性由确认对象及明确来源决定；未配置不启用'}
 out['mode']='academic';out['version']+='+'+data['version'];out['name']+='（段落及摘要关键词参考文献）';out['academic_sha256']=sha256(raw)
 out['sha256']=sha256((base['sha256']+':'+sha256(raw)).encode());return out

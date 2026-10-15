"""Explicit supplement v1; independent of legacy v2-v5 object template semantics."""
from copy import deepcopy
from pathlib import Path
import json,math,re
from .package import DemoError,sha256
FIELDS={**{'cover_title__'+p:p for p in ('font_cn','font_size','bold','alignment')},**{o+'__'+p:p for o in ('header_text','footer_text') for p in ('font_cn','font_western','font_size','alignment')},'header_distance_mm':'mm','footer_distance_mm':'mm'}
CN=('宋体','黑体','楷体','仿宋');WEST=('Times New Roman','Arial','Calibri');ALIGN=('left','center','right','both')
def value(n,v):
 if n not in FIELDS:raise DemoError('补充模板含未知字段')
 if v is None:return None
 p=FIELDS[n]
 if p=='font_cn':ok=type(v) is str and v in CN
 elif p=='font_western':ok=type(v) is str and v in WEST
 elif p=='alignment':ok=type(v) is str and v in ALIGN
 elif p=='bold':ok=type(v) is bool
 else:ok=type(v) in (int,float) and math.isfinite(v) and (0<=v<=50 if p=='mm' else 8<=v<=(36 if n.startswith('cover') else 24) and v*2==int(v*2))
 if not ok:raise DemoError('补充模板字段类型或范围无效：'+n)
 return v

def school():
 vals={n:None for n in FIELDS};vals.update(cover_title__font_cn='黑体',cover_title__font_size=22,cover_title__bold=True,cover_title__alignment='center',header_distance_mm=15,footer_distance_mm=15,header_text__alignment='center')
 # 二号 is 22pt; physical page17 and cover example21, not 24pt.
 sources={n:{'kind':'school_demo' if v is not None else 'not_enabled','quote':'论文封面均使用中文撰写。二号，黑体，加粗，居中。' if n.startswith('cover') else '页眉的上边距为15mm；其上居中打印页眉；页脚的下边距为15mm。' if v is not None else '', 'location':'PDF:17,21' if n.startswith('cover') else 'PDF:19' if v is not None else None} for n,v in vals.items()}
 return {'format':'paper-grid-front-supplement','structure_version':1,'name':'华工本科工理类2015演示规则封面与页眉页脚补充','values':vals,'sources':sources,'confirmation':'固定原文配置；仅用户明确确认对象后执行'}

def validate(d):
 if type(d) is not dict or set(d)!={'format','structure_version','name','values','sources','confirmation'} or d['format']!='paper-grid-front-supplement' or type(d['structure_version']) is not int or d['structure_version']!=1:raise DemoError('封面补充模板结构版本无效')
 for k in ('name','confirmation'):
  if type(d[k]) is not str or not d[k].strip() or len(d[k])>160 or any(c in d[k] for c in '\\/<>{}'):raise DemoError('补充模板名称或确认信息无效')
 if type(d['values']) is not dict or set(d['values'])!=set(FIELDS) or type(d['sources']) is not dict or set(d['sources'])!=set(FIELDS):raise DemoError('补充模板缺失字段或含未知执行字段')
 for n,v in d['values'].items():
  value(n,v);s=d['sources'][n]
  if type(s) is not dict or set(s)!={'kind','quote','location'} or s['kind'] not in ('school_demo','user_confirmed','ai_extracted','not_enabled'):raise DemoError('补充字段来源无效')
  if type(s['quote']) is not str or len(s['quote'])>300 or any(c in s['quote'] for c in '<>{}\\'):raise DemoError('补充依据不安全')
  from .templates import LOCATOR
  if s['location'] is not None and (type(s['location']) is not str or not (re.fullmatch(r'PDF:\d+(?:,\d+)*',s['location']) or LOCATOR.fullmatch(s['location']))):raise DemoError('补充来源位置无效，不保存磁盘路径')
  if v is None and s!={'kind':'not_enabled','quote':'','location':None}:raise DemoError('缺失字段不得伪造来源')
  if v is not None and s['kind']=='not_enabled':raise DemoError('未启用字段不得携带值')
  if s['kind']=='school_demo' and (v!=school()['values'][n] or s!=school()['sources'][n]):raise DemoError('自定义值不得冒充学校原文')
  if s['kind']=='ai_extracted':
   f={'value':v,'unit':'pt' if FIELDS[n]=='font_size' else FIELDS[n],'quote':s['quote'],'location':s['location'],'support':'supported'}
   validate_draft({**{k:None for k in FIELDS},n:f,'unsupported':[]},s['quote'])
 if any(v['kind'] in ('user_confirmed','ai_extracted') for v in d['sources'].values()) and any(x in d['name'] for x in ('华工','学校','官方')):raise DemoError('自定义补充模板不得使用学校官方名称')
 if len(json.dumps(d,ensure_ascii=False,allow_nan=False).encode())>16000:raise DemoError('补充模板超过16KB')
 return deepcopy(d)

def digest(d):return sha256(json.dumps(validate(d),ensure_ascii=False,sort_keys=True).encode())
def loads(raw):
 if len(raw)>16000:raise DemoError('补充模板超过16KB')
 try:
  from .rule_config import strict_json
  return validate(strict_json(raw.decode('utf-8') if isinstance(raw,bytes) else raw))
 except (ValueError,TypeError,UnicodeError) as e:raise DemoError('补充模板JSON或字段无效') from e

def validate_draft(d,text,*,segments=None):
 if type(text) is not str or not 0<len(text)<=(12000 if segments is not None else 2000):raise DemoError('请核对1–2000字符公开规范摘录')
 if type(d) is not dict or set(d)!=set(FIELDS)|{'unsupported'} or type(d['unsupported']) is not list:raise DemoError('封面规范草稿字段不完整或含未知字段')
 for n,f in d.items():
  if n=='unsupported':
   for note in f:
    if type(note) is not str or not note or len(note)>200:raise DemoError('不支持提示无效')
   continue
  if f is None:continue
  if type(f) is not dict or set(f)!={'value','unit','quote','location','support'} or f['support']!='supported' or f['unit']!=('pt' if FIELDS[n]=='font_size' else 'mm' if FIELDS[n]=='mm' else FIELDS[n]):raise DemoError('封面字段单位或结构无效')
  value(n,f['value']);quote=f['quote']
  from .templates import LOCATOR
  if f['value'] is None or type(quote) is not str or not quote or len(quote)>200 or quote not in text or (not any(s['location']==f['location'] and quote in s['text'] for s in segments) if segments is not None else not LOCATOR.fullmatch(str(f['location']))) or any(c in quote for c in '<>{}\\'):raise DemoError('封面依据或位置无效')
  context='封面(?:论文)?标题' if n.startswith('cover') else '页眉' if n.startswith('header') else '页脚'
  clauses=[c for c in re.split('[。；;\n]',text) if re.search(context,c)]
  if not re.search(context,quote):raise DemoError('要求对象不匹配，不发送或解析个人信息')
  p=FIELDS[n];v=f['value']
  def candidates(q):
   if p=='font_cn':return {x for x in CN if x in q}
   if p=='font_western':return {x for x in WEST if x in q}
   if p=='font_size':
    from .spec_validation import FONT_NAMES
    return {float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*(?:pt|磅)',q,re.I)}|{FONT_NAMES[x.rstrip('号')] for x in re.findall(r'小[二三四五](?:号)?|[二三四五]号',q)}
   if p=='alignment':return {x for x,c in zip(ALIGN,('居左','居中','居右','两端对齐')) if c in q}
   if p=='bold':return {False} if '不加粗' in q else {True} if '加粗' in q else set()
   return {float(x)*(10 if u.lower() in ('cm','厘米') else 1) for x,u in re.findall(r'(\d+(?:\.\d+)?)\s*(mm|毫米|cm|厘米)',q,re.I)}
  if any(re.search('任选|不超过|至少|至多|大约|建议|可能|不规定|未规定|不作要求',c) for c in clauses):raise DemoError('封面/页眉页脚要求含糊，须用户明确确认')
  if p in ('font_cn','font_western'):
   from .templates import font_candidates
   clean=lambda c:re.sub(r'封面(?:论文)?标题|页眉|页脚|小[二三四五](?:号)?|[二三四五]号','',c)
   if set().union(*(font_candidates(clean(c),p) for c in clauses))!={v}:raise DemoError('封面/页眉页脚字体含未知字体或冲突')
  if candidates(quote)!={v} or set().union(*(candidates(c) for c in clauses))!={v}:raise DemoError('规范冲突、含糊或数值不匹配，须用户手动确认')
 return deepcopy(d)

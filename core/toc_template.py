"""Explicit v1 TOC supplement. Never silently enabled by legacy templates."""
from copy import deepcopy
import json, math, re
from .package import DemoError, sha256
from .rule_config import strict_json
OBJECTS=('title','level1','level2','level3')
PROPS=('font_cn','font_size','alignment','line_multiple')
FIELDS={o+'__'+p:p for o in OBJECTS for p in PROPS}
CN=('宋体','黑体','楷体','仿宋');ALIGN=('left','center','right','both');LINES=(1.,1.25,1.5,2.)
QUOTE='目录标题：小二号黑体，居中，单倍行距。目录中各章题序及标题：四号黑体，居左，1.5倍行距；各次级标题及题序：小四号，宋体，居左，1.5倍行距。'
def school():
 values={}
 for o in OBJECTS:
  for p,v in zip(PROPS,('黑体' if o in ('title','level1') else '宋体',18 if o=='title' else 14 if o=='level1' else 12,'center' if o=='title' else 'left',1. if o=='title' else 1.5)):values[o+'__'+p]=v
 return {'format':'paper-grid-toc-supplement','structure_version':1,'name':'2015目录演示补充要求','values':values,'sources':{n:{'kind':'school_demo','quote':QUOTE,'location':'学校PDF物理页18'} for n in FIELDS},'confirmation':'须人工确认目录对象与层级；非现行通用校规'}
def validate(d):
 from .templates import safe_text
 if type(d) is not dict or set(d)!={'format','structure_version','name','values','sources','confirmation'} or d['format']!='paper-grid-toc-supplement' or type(d['structure_version']) is not int or d['structure_version']!=1:raise DemoError('目录补充模板结构/版本不支持')
 if type(d['name']) is not str or not 0<len(d['name'])<=80 or type(d['confirmation']) is not str or not 0<len(d['confirmation'])<=200:raise DemoError('目录模板名称或确认信息无效')
 if type(d['values']) is not dict or set(d['values'])!=set(FIELDS) or type(d['sources']) is not dict or set(d['sources'])!=set(FIELDS):raise DemoError('目录模板字段缺失或未知')
 safe_text(d['name'],80);safe_text(d['confirmation'],200)
 for n,p in FIELDS.items():
  v=d['values'][n];s=d['sources'][n]
  if v is not None:
   if p in ('font_cn','alignment'):
    if type(v) is not str or v not in (CN if p=='font_cn' else ALIGN):raise DemoError('目录字体/对齐不支持')
   elif type(v) not in (int,float) or (p=='font_size' and not (8<=v<=36 and v*2==int(v*2))) or (p=='line_multiple' and v not in LINES):raise DemoError('目录字号或倍数行距无效')
  if type(s) is not dict or set(s)!={'kind','quote','location'} or s['kind'] not in ('school_demo','user_confirmed','ai_extracted','not_enabled') or type(s['quote']) is not str or len(s['quote'])>2000 or s['location'] is not None and (type(s['location']) is not str or len(s['location'])>100):raise DemoError('目录来源无效')
  if s['quote']:safe_text(s['quote'],2000)
  if s['location']:safe_text(s['location'],100)
  if (v is None)!=(s['kind']=='not_enabled'):raise DemoError('目录未启用状态与来源不一致')
  if s['kind']=='school_demo' and (v!=school()['values'][n] or s!=school()['sources'][n]):raise DemoError('不可伪造学校目录要求')
  if s['kind']=='ai_extracted' and (not s['quote'] or not s['location']):raise DemoError('AI目录字段缺少原文依据')
 if any(s['kind'] not in ('school_demo','not_enabled') for s in d['sources'].values()) and d['name']=='2015目录演示补充要求':raise DemoError('自定义目录要求不能冒充学校演示模板')
 return deepcopy(d)
def loads(raw):
 if len(raw)>32000:raise DemoError('目录模板过大')
 try:return validate(strict_json(raw.decode('utf-8') if isinstance(raw,bytes) else raw))
 except UnicodeDecodeError:raise DemoError('目录模板必须是UTF-8 JSON') from None
def digest(d):return sha256(json.dumps(validate(d),ensure_ascii=False,sort_keys=True).encode())
def validate_draft(d,text,*,segments=None):
 from .spec_validation import DANGEROUS
 if type(text) is not str or not text.strip() or len(text)>12000 or DANGEROUS.search(text):raise DemoError('目录规范只接受公开格式文字，不接受代码/文件路径/工具指令')
 if type(d) is not dict or set(d)!={'fields','unsupported'} or type(d['fields']) is not dict or set(d['fields'])!=set(FIELDS) or type(d['unsupported']) is not list:raise DemoError('目录AI草稿结构无效')
 for n,c in d['fields'].items():
  if c is None:continue
  if type(c) is not dict or set(c)!={'value','unit','quote','location','support'} or c['support']!='supported' or type(c['quote']) is not str or not c['quote'] or c['quote'] not in text or type(c['location']) is not str or (not re.fullmatch(r'TEXT:[1-9]\d*',c['location']) if segments is None else not any(s['location']==c['location'] and c['quote'] in s['text'] for s in segments)):raise DemoError('目录AI依据/结构无效')
  p=FIELDS[n];expected_unit={'font_cn':'font','font_size':'pt','alignment':'alignment','line_multiple':'multiple'}[p]
  if c['unit']!=expected_unit:raise DemoError('目录AI单位无效')
  draft=school();draft['name']='用户确认的目录演示要求';draft['values'][n]=c['value'];draft['sources'][n]={'kind':'user_confirmed','quote':'','location':None};validate(draft)
  # Require unambiguous TOC object context and literal/Chinese size/value support.
  q=c['quote'];o=n.split('__')[0]
  if '目录' not in q or (o=='title' and '标题' not in q) or (o!='title' and not any(x in q for x in ({'level1':('一级','各章'),'level2':('二级','次级'),'level3':('三级','次级')}[o]))):raise DemoError('目录对象依据不明确，须人工确认')
  if re.search(r'正文|摘要|图题|表题|参考文献',q):raise DemoError('目录依据混合其他对象，请选取更明确短句')
  v=c['value'];proof=[]
  if p=='font_cn':proof=[x for x in CN if x in q]
  elif p=='font_size':
   sizes={'小二':18,'二':22,'小三':15,'三':16,'小四':12,'四':14,'小五':9,'五':10.5}
   proof=[sizes[m] for m in re.findall(r'(小二|小三|小四|小五|二|三|四|五)号',q)]
   proof += [float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*(?:pt|磅)',q,re.I)]
  elif p=='alignment':proof=[x for x,label in {'left':'居左','center':'居中','right':'居右','both':'两端对齐'}.items() if label in q]
  else:
   proof=[float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*倍',q)]
   if '单倍' in q:proof.append(1.)
  if len(set(proof))!=1 or v not in proof:raise DemoError('目录值与原文不对应或存在冲突，不能自动采用')
 for u in d['unsupported']:
  if type(u) is not str or len(u)>500:raise DemoError('目录未支持提示类型无效')
 return deepcopy(d)

"""Optional reusable assembly strategy, never document locations or school defaults."""
from copy import deepcopy
import re
from .package import DemoError
DEFAULT={'version':1,'dynamic':False,'pages':'keep','roman':'lowerRoman','body_start':1,'front_start':1,'chapter_restart':False,'footer':'page','text':'','alignment':'center'}
def validate(p):
 if type(p) is not dict or set(p)!=set(DEFAULT):raise DemoError('完整整理策略字段不完整或未知')
 if type(p['version']) is not int or p['version']!=1 or type(p['dynamic']) is not bool or type(p['chapter_restart']) is not bool:raise DemoError('整理策略版本/开关无效')
 if p['pages'] not in ('keep','front-body','chapter-footers') or p['roman'] not in ('lowerRoman','upperRoman') or p['footer'] not in ('page','chapter','text') or p['alignment'] not in ('center','right'):raise DemoError('页码/页脚模式不支持')
 if any(type(p[k]) is not int or not 1<=p[k]<=9999 for k in ('body_start','front_start')):raise DemoError('正文页码起始值须1–9999')
 if type(p['text']) is not str or len(p['text'])>80 or any(ord(c)<32 for c in p['text']) or '<' in p['text'] or '>' in p['text']:raise DemoError('页脚普通文字无效')
 if p['footer']=='text' and not p['text']:raise DemoError('请填写页脚文字')
 return deepcopy(p)
def extract(text):
 """Bounded exact declarations only; all unconsumed clauses go to strict format parser.

 No approximate matching, inferred page positions, or silent removal of unknown demands.
 """
 p=deepcopy(DEFAULT);proof=[];rest=[];seen={}
 for m in re.finditer(r'[^；;。\n]+',text):
  t=m.group().strip();changes={}
  if not t:continue
  if re.fullmatch(r'封面不(?:显示|编)?页码[，,、 ]*(?:摘要和目录|前置部分)(?:使用|用)(小写|大写)罗马数字[，,、 ]*正文从([1-9][0-9]{0,3})开始(?:连续编号)?',t):
   x=re.search(r'(小写|大写)',t);changes={'pages':'front-body','roman':'lowerRoman' if x[1]=='小写' else 'upperRoman','body_start':int(re.search(r'正文从(\d+)',t)[1])}
  elif t=='各章页脚显示章节名称和页码':changes={'footer':'chapter'}
  elif t in ('整理图表编号并同步正文中的对应引用','整理图表编号并同步正文对应引用'):changes={'dynamic':True}
  else:rest.append(m.group());continue
  for k,v in changes.items():
   if k in seen and seen[k]!=v:raise DemoError('页码或动态要求存在冲突，请明确取舍')
   seen[k]=v;p[k]=v
  proof.append({'start':m.start(),'end':m.end(),'quote':m.group(),'values':changes})
 if proof and p['footer']=='chapter' and 'pages' not in seen:p['pages']='chapter-footers'
 return (validate(p) if proof else None),'；'.join(rest),proof

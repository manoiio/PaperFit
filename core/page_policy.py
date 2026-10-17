"""Optional reusable assembly strategy, never document locations or school defaults."""
from copy import deepcopy
import re
from .package import DemoError
DEFAULT={'version':1,'dynamic':False,'pages':'keep','roman':'lowerRoman','body_start':1,'front_start':1,'chapter_restart':False,'footer':'page','text':'','alignment':'center'}
def validate(p):
 if type(p) is not dict or set(p)!=(set(DEFAULT)|({'targets'} if p.get('version')==2 else set())):raise DemoError('完整整理策略字段不完整或未知')
 if type(p['version']) is not int or p['version'] not in (1,2) or type(p['dynamic']) is not bool or type(p['chapter_restart']) is not bool:raise DemoError('整理策略版本/开关无效')
 if p['pages'] not in ('keep','front-body','chapter-footers') or p['roman'] not in ('lowerRoman','upperRoman') or p['footer'] not in ('page','chapter','text') or p['alignment'] not in ('center','right'):raise DemoError('页码/页脚模式不支持')
 if any(type(p[k]) is not int or not 1<=p[k]<=9999 for k in ('body_start','front_start')):raise DemoError('正文页码起始值须1–9999')
 if type(p['text']) is not str or len(p['text'])>80 or any(ord(c)<32 for c in p['text']) or '<' in p['text'] or '>' in p['text']:raise DemoError('页脚普通文字无效')
 if p['footer']=='text' and not p['text']:raise DemoError('请填写页脚文字')
 if p['version']==2 and (type(p['targets']) is not list or any(type(x) is not str or x not in ('cover','front','body') for x in p['targets']) or len(set(p['targets']))!=len(p['targets'])):raise DemoError('页码适用区域无效')
 return deepcopy(p)
def _legacy_extract(text):
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


def extract(text):
 """Exact original spans, bounded equivalent expressions; unknown residue is never ignored."""
 old,remaining,proof=_legacy_extract(text)
 if old is not None and not remaining.strip():return old,remaining,proof
 p=deepcopy(DEFAULT);targets=set();seen={};proof=[];rest=[];new=False
 def accept(values,start,end,areas=()):
  for k,v in values.items():
   if k in seen and seen[k]!=v:raise DemoError('页码要求互相冲突，请明确取舍；不采用最后一句')
   seen[k]=v;p[k]=v
  targets.update(areas);proof.append({'start':start,'end':end,'quote':text[start:end],'values':values})
 for m in re.finditer(r'[^；;。\n]+',text):
  t=m.group().strip();one,left,ev=_legacy_extract(t)
  if one is not None and not left.strip():
   vals={k:v for e in ev for k,v in e['values'].items()};accept(vals,m.start(),m.end(),('cover','front','body') if 'pages' in vals else ('body',) if vals.get('footer') else ());continue
  unknown=[]
  for c in re.finditer(r'[^，,]+',m.group()):
   raw=c.group();v=raw.strip();vals={};areas=();boundary=None
   if re.fullmatch(r'前言(?:属于|作为|归入)(?:前置部分|正文)',v):
    boundary={'label':'前言','purpose':'front' if v.endswith('前置部分') else 'body'}
   elif re.fullmatch(r'封面(?:不要|不显示|不编|不用|不加)页码',v):vals={};areas=('cover',)
   elif re.fullmatch(r'(?:摘要和目录|摘要、目录|前置部分|前面)(?:使用|用)(?:小写罗马(?:数字)?|i、ii|i/ii)',v):vals={'pages':'front-body','roman':'lowerRoman'};areas=('front',)
   elif re.fullmatch(r'(?:摘要和目录|前置部分|前面)(?:使用|用)大写罗马(?:数字)?',v):vals={'pages':'front-body','roman':'upperRoman'};areas=('front',)
   elif re.fullmatch(r'正文(?:页码)?从[1-9][0-9]{0,3}开始(?:连续编号)?',v):vals={'pages':'front-body','body_start':int(re.search(r'从(\d+)',v)[1])};areas=('body',)
   elif v in ('正文用阿拉伯数字重新编号','正文使用阿拉伯数字重新编号'):vals={'pages':'front-body'};areas=('body',)
   elif v in ('正文页码接着排','后面每章连续','后续章节连续编号','正文页码连续'):vals={'chapter_restart':False};areas=('body',)
   elif v in ('每章页码重新从1开始','正文每章从1重新编号'):vals={'pages':'front-body','chapter_restart':True,'body_start':1};areas=('body',)
   elif v in ('各章换不同页脚','每章不同页脚','各章使用不同页脚','各章页脚显示章名和页码','显示章名','各章页脚显示章节名称和页码'):vals={'footer':'chapter'};areas=('body',)
   elif v in ('保留现在的页码','保持原有页码','页码保持原样'):vals={'pages':'keep'}
   elif v in ('只统一正文格式','只整理普通格式'):vals={'pages':'keep','dynamic':False}
   elif re.fullmatch(r'页脚(?:居中|居右)',v):vals={'alignment':'center' if v.endswith('居中') else 'right'};areas=('body',)
   else:unknown.append(raw);continue
   new=True;accept(vals,m.start()+c.start(),m.start()+c.end(),areas)
   if v=='只统一正文格式':proof[-1]['format_roles']=['body']
   if boundary:
    if any(e.get('boundary',{}).get('label')==boundary['label'] and e['boundary']['purpose']!=boundary['purpose'] for e in proof[:-1]):raise DemoError('同一区域的正文/前置用途要求冲突')
    proof[-1]['boundary']=boundary
  if unknown:rest.append('，'.join(unknown))
 if not proof:return None,text,[]
 if new:
  p['version']=2;p['targets']=[x for x in ('cover','front','body') if x in targets]
  if seen.get('pages')=='keep' and targets:raise DemoError('保持页码与修改页码要求冲突，需明确取舍')
  if 'pages' not in seen:p['pages']='chapter-footers' if p['footer'] in ('chapter','text') or targets=={'body'} and any(k in seen for k in ('alignment','chapter_restart')) else 'front-body' if targets else 'keep'
 return validate(p),'；'.join(rest),proof

def merge(base,parsed,proof):
 """Only named strategy values override a current plan; portable target intent stays explicit."""
 if base is None:return parsed
 out=deepcopy(base);values={k:v for e in proof for k,v in e['values'].items()};out.update(values)
 if parsed['version']==2:
  base_targets=set(base.get('targets',('cover','front','body') if base['pages']=='front-body' else ('body',) if base['pages']=='chapter-footers' else ()))
  out['version']=2;out['targets']=[x for x in ('cover','front','body') if x in base_targets|set(parsed['targets'])] if values.get('pages')!='keep' else []
 if parsed['version']==1 and out['version']==2 and values.get('pages')=='front-body':out['targets']=['cover','front','body']
 if 'pages' not in values and parsed['pages']=='chapter-footers' and base['pages']=='keep':out['pages']='chapter-footers'
 return validate(out)

"""Finite page-intent IDs; original spans prove every value before policy compilation."""
import re
from copy import deepcopy
from core.package import DemoError
from core.page_policy import DEFAULT,validate,extract
VERSION='page-intent-1'
FIELDS={
 'P01':{'name':'@cover','label':'封面页码显示','unit':'policy','allowed':['hide']},
 'P02':{'name':'@roman','label':'前置数字格式','unit':'policy','allowed':['lowerRoman','upperRoman']},
 'P03':{'name':'@body_start','label':'正文重启起始值','unit':'policy','allowed':'整数1至9999'},
 'P04':{'name':'@chapter_restart','label':'后续各章是否重启','unit':'policy','allowed':[True,False]},
 'P05':{'name':'@footer','label':'正文页脚内容','unit':'policy','allowed':['chapter']},
 'P06':{'name':'@alignment','label':'正文页脚对齐','unit':'policy','allowed':['center','right']},
 'P08':{'name':'@text','label':'正文页脚普通文字加页码','unit':'policy','allowed':'原文明确引号内普通文字，1至80字符'},
 'P07':{'name':'@preserve','label':'保留现有页码','unit':'policy','allowed':[True]},
}
def clauses(text):
 """These are supported vocabulary routes, not model permissions or fuzzy matches."""
 out=[]
 patterns=[
 ('P08',r'页脚(?:内容|文字)?(?:写|显示|采用|为)[“\"]([^”\"\n]{1,80})[”\"](?:并附|加|和|及|＋|\+)(?:页码|页号)',lambda m:m[1]),
 ('P01',r'封面(?:区域)?(?:隐藏|隐去|取消)(?:所有)?页(?:码|号)',lambda _: 'hide'),
 ('P02',r'(?:摘要(?:及|和)目录|前置部分|前面)(?:采用|使用)(?:罗马(?:数字)?小写|小写罗马(?:数字)?)',lambda _: 'lowerRoman'),
 ('P02',r'(?:摘要(?:及|和)目录|前置部分|前面)(?:采用|使用)(?:罗马(?:数字)?大写|大写罗马(?:数字)?)',lambda _: 'upperRoman'),
 ('P03',r'正文页码(?:起算值|起始数|起始值)(?:为|是|设为)([1-9][0-9]{0,3})',lambda m:int(m[1])),
 ('P04',r'(?:后续|后面|之后)(?:的)?(?:每章|各章|章节)页码(?:延续|接续|接着)(?:前章|上一章|编号)',lambda _:False),
 ('P04',r'(?:后续|后面|之后)(?:的)?(?:每章|各章|章节)页码(?:均|都)?重新编号',lambda _:True),
 ('P05',r'(?:各章|每章)页脚(?:采用|使用|包含|显示)(?:本章名称|章名|章节名称)(?:和|与|加|及|＋|\+)(?:页码|页号)',lambda _:'chapter'),
 ('P06',r'页脚(?:文字)?(?:靠右|右对齐|居右对齐)',lambda _:'right'),
 ('P06',r'页脚(?:文字)?(?:居中对齐|中间对齐)',lambda _:'center'),
 ('P07',r'(?:原有|现有)(?:的)?页码(?:全部)?(?:不变|保持不变|保留)',lambda _:True),
 ]
 for m in re.finditer(r'[^；;。\n，,]+',text):
  t=m.group().strip()
  for fid,pattern,value in patterns:
   match=re.fullmatch(pattern,t)
   if match:
    out.append({'id':fid,'value':value(match),'start':m.start(),'end':m.end(),'quote':m.group()});break
 return out

def strip(text):
 spans=clauses(text);chars=list(text)
 for e in spans:chars[e['start']:e['end']]=' '* (e['end']-e['start'])
 return ''.join(chars),spans

def compile(proofs,text):
 """All routed clauses must be accounted for; no conflict/source pruning."""
 wanted=clauses(text);received=[]
 for p in proofs:
  matches=[x for x in wanted if x['id']==p['id'] and x['quote'] in p['source_text'] and type(x['value']) is type(p['value']) and x['value']==p['value']]
  if not matches:raise DemoError('页码策略值无法由对应原文证明：'+p['id'])
  received.extend(matches)
 if any(e not in received for e in wanted):raise DemoError('页码策略有遗漏，整组尚未应用')
 policy,_,local=extract(text);policy=deepcopy(policy or DEFAULT);seen={k:v for p in local for k,v in p['values'].items()};targets=set(policy.get('targets',('cover','front','body') if local else ()));ev=[]
 for e in wanted:
  fid=e['id'];v=e['value'];changes={'P01':{},'P02':{'roman':v,'pages':'front-body'},'P03':{'body_start':v,'pages':'front-body'},'P04':{'chapter_restart':v},'P05':{'footer':v},'P06':{'alignment':v},'P07':{'pages':'keep'},'P08':{'footer':'text','text':v}}[fid]
  for k,x in changes.items():
   if k in seen and seen[k]!=x:raise DemoError('全文页码策略存在冲突：'+k)
   seen[k]=x;policy[k]=x
  targets.update(('cover',) if fid=='P01' else ('front',) if fid=='P02' else () if fid=='P07' else ('body',))
  ev.append({**e,'values':changes})
 if seen.get('pages')=='keep' and targets:raise DemoError('保留页码与修改策略冲突')
 if 'pages' not in seen:policy['pages']='chapter-footers' if policy['footer'] in ('chapter','text') or targets=={'body'} and any(k in seen for k in ('alignment','chapter_restart')) else 'front-body' if targets else 'keep'
 policy.update(version=2,targets=[x for x in ('cover','front','body') if x in targets])
 return {'policy':validate(policy),'proof':local+ev,'protocol':VERSION}

"""Explicit ordinary-character requirements. Shared reader, surgical patch and mask.

No defaults are enabled. Superscripts, complex containers and numbering symbols
are never targets. OOXML toggle semantics are evaluated through Resolver layers.
"""
from copy import deepcopy
import math,re
from .package import q,DemoError
from .formats import Resolver,Unresolved,paragraph_unsafe
from .classification import TYPES
PROPS={'shadow':('阴影','bool'),'outline':('轮廓','bool'),'emboss':('浮雕','bool'),'imprint':('印入','bool'),'scale':('字符缩放','percent'),'character_spacing':('字符间距','character_pt'),'baseline':('基线偏移','baseline_pt')}
OBJECTS=('body','heading1','heading2','heading3','figure_caption','table_caption','abstract_cn_title','abstract_cn_body','abstract_en_title','abstract_en_body','reference_title','reference_item','appendix_title','appendix_text','ack_title','ack_text')
FIELDS={o+'__'+p:('R13',TYPES.get(o,o)+' '+title,unit) for o in OBJECTS for p,(title,unit) in PROPS.items()}
TAGS={'scale':'w','character_spacing':'spacing','baseline':'position'}
# Shadow and outline can coexist. Relief effects cannot coexist with either
# of them or with each other (ISO 29500 17.3.2; Microsoft SDK remarks).
CONFLICTS=(('shadow','emboss'),('shadow','imprint'),('outline','emboss'),('outline','imprint'),('emboss','imprint'))
def conflicting(flags):return [(a,b) for a,b in CONFLICTS if flags.get(a) is True and flags.get(b) is True]
def validate_requested(values):
 for obj in OBJECTS:
  pairs=conflicting({p:values.get(obj+'__'+p) for p in ('shadow','outline','emboss','imprint')})
  if pairs:raise DemoError(TYPES.get(obj,obj)+' 的互斥文字效果不能同时启用：'+'、'.join(PROPS[a][0]+'/'+PROPS[b][0] for a,b in pairs))
def value(name,v):
 if v is None:return None
 p=name.split('__')[-1]
 if p not in PROPS:raise DemoError('未知文字效果')
 if p in ('shadow','outline','emboss','imprint'):
  if type(v) is not bool:raise DemoError('文字效果须明确启用或关闭')
 else:
  lo,hi,step={'scale':(50,200,1),'character_spacing':(-5,20,20),'baseline':(-20,20,2)}[p]
  if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi or abs(v*step-round(v*step))>1e-8:raise DemoError('字符值超出范围或OOXML精度：缩放50–200%整数；间距−5–20磅/0.05；偏移−20–20磅/0.5')
 return deepcopy(v)
def proof(name,quote):
 p=name.split('__')[-1]
 if re.search('建议|大约|可选|或者|任选|不超过|至少|全部|全文',quote):return set()
 if p in ('shadow','outline','emboss','imprint'):
  title=PROPS[p][0];out=set()
  for m in re.finditer(r'(不使用|不带|关闭|取消|无|使用|开启|启用|带有)\s*('+title+r')',quote):out.add(m[1] in ('使用','开启','启用','带有'))
  # "不使用阴影和轮廓" is one explicit negative list.
  if re.search(r'(?:不使用|不带|关闭|取消|无)\s*(?:阴影|轮廓|浮雕|印入)(?:[、和与及 ]+(?:阴影|轮廓|浮雕|印入))*',quote):
   for m in re.finditer(r'(?:不使用|不带|关闭|取消|无)\s*(?:阴影|轮廓|浮雕|印入)(?:[、和与及 ]+(?:阴影|轮廓|浮雕|印入))*',quote):
    if title in m[0]:out.add(False)
  return out
 if p=='scale':return {float(x) for x in re.findall(r'字符(?:水平)?缩放\s*(\d+(?:\.\d+)?)\s*[%％]',quote)}
 if p=='character_spacing':return ({0} if '标准字符间距' in quote else set())|{float(x) for x in re.findall(r'字符间距\s*(-?\d+(?:\.\d+)?)\s*(?:磅|pt)',quote,re.I)}
 return ({0} if re.search(r'基线(?:偏移)?\s*(?:为)?\s*0\s*(?:磅|pt)|基线不偏移',quote) else set())|{float(x) for x in re.findall(r'基线偏移\s*(-?\d+(?:\.\d+)?)\s*(?:磅|pt)',quote,re.I)}
def candidate(name,f,segments):
 from .academic_templates import context
 from .norms import evidence_segments
 segments=evidence_segments(segments,f.get('location'));obj=name.split('__')[0];quote=f.get('quote','');v=value(name,f.get('value'))
 if type(f) is not dict or set(f)!={'value','unit','quote','location','support'} or f['support']!='supported' or f['unit']!=FIELDS[name][2] or v is None:raise DemoError('文字效果字段、值或单位无效')
 if not any(s['location']==f['location'] and quote in s['text'] for s in segments) or not quote or len(quote)>200:raise DemoError('文字效果缺少真实连续原句')
 if not context(obj,'bold',quote) or proof(name,quote)!={v}:raise DemoError('文字效果对象或数值无法由原句证明')
 found=set()
 for s in segments:
  for clause in re.split('[。；;\n]',s['text']):
   if context(obj,'bold',clause):found.update(proof(name,clause))
 if found!={v}:raise DemoError('文字效果存在冲突或缺少完整依据')
 return deepcopy(f)
def read(res,layers,p):
 tag=TAGS.get(p,p);out=False if p not in TAGS else 100 if p=='scale' else 0;origins=[]
 for l in layers:
  es=l.findall(q(tag))
  if len(es)>1:raise Unresolved('重复文字效果元素')
  if not es:continue
  e=es[0]
  if set(e.attrib)-{q('val')} or len(e):raise Unresolved('文字效果含未知属性或子树')
  raw=e.get(q('val'),'1');origin=res._layer_origin(l);origins.append(origin)
  if p not in TAGS:
   if raw not in ('1','true','on','0','false','off'):raise Unresolved('文字效果布尔值未知')
   v=raw in ('1','true','on')
   if l.getparent().tag==q('style'):out=not out if v else out
   else:out=v
  else:
   if not re.fullmatch(r'-?\d+',raw):raise Unresolved('字符属性不是整数声明')
   out=int(raw)/(20 if p=='character_spacing' else 2 if p=='baseline' else 1)
 return {'value':out,'origins':origins or ['OOXML缺省（未声明）']}
def append_checks(report,pkg,manifest,rules):
 cfg=rules.get('text_normalization',{});res=Resolver(pkg)
 if not cfg:return
 from .academic_rules import RULE_FOR
 from .backmatter import RULE_FOR as BACK
 evidence=[]
 for sn,role in manifest['paragraph_types'].items():
  n=int(sn);p=pkg.paragraphs[n-1]
  for prop,setting in cfg.get(role,{}).items():
   wanted=setting['value'];rid={**RULE_FOR,**BACK}.get(role,'R13')
   for i,r in enumerate(p.findall(q('r')),1):
    if not ''.join(r.itertext()).strip():continue
    loc={'paragraph':n,'run':i,'property':'text_'+prop};status='review';detail='';actual=None;origins=[]
    try:
     why=paragraph_unsafe(p);layers=res.layers(p,r)
     reason=res.special(r,layers)
     if reason=='文字基线偏移':
      # Resolver returns its first reason. Neutralize ONLY the proven position
      # in disposable layers, then re-run every remaining original safeguard.
      read(res,layers,'baseline')
      neutral=deepcopy(layers)
      for layer in neutral:
       for e in layer.findall(q('position')):e.set(q('val'),'0')
      remaining=res.special(r,neutral)
      if remaining:raise Unresolved(remaining)
     if any(e.tag.startswith('{http://schemas.microsoft.com/office/word/') for layer in layers for e in layer):raise Unresolved('高级文字效果/艺术字仍受保护')
     if why or reason and not reason=='文字基线偏移':raise Unresolved(why or reason)
     if res.value(layers,'vertAlign','baseline')!='baseline':raise Unresolved('引文上标/下标保持，未套普通效果要求')
     flags={name:read(res,layers,name)['value'] for name in ('shadow','outline','emboss','imprint')}
     if conflicting(flags):raise Unresolved('原有效声明含互斥文字效果，不能猜测Word实际取舍；保持待复核')
     if prop in flags:
      projected={**flags,prop:wanted}
      if conflicting(projected):raise Unresolved('本项单独启用会与其他效果冲突；须先明确关闭冲突项并重新检查，不自动追加修正')
     info=read(res,layers,prop);actual=info['value'];origins=info['origins'];status='pass' if actual==wanted else 'problem'
    except (Unresolved,ValueError) as exc:actual={'unresolved':str(exc)};detail=str(exc)
    key=rid+':'+':'.join(f'{k}={v}' for k,v in loc.items())
    report['findings'].append({'key':key,'rule_id':rid,'rule_name':rules['rules'][rid]['name']+' · '+PROPS[prop][0],'locator':loc,'object_type':role,'property':'text_'+prop,'actual':actual,'expected':wanted,'status':status,'fixable':status=='problem' and not pkg.signed and not pkg.ambiguous_sections,'source':deepcopy(setting['source']),'detail':detail or '仅选中普通run的'+PROPS[prop][0]+'；不改编号符号、字体或其他效果','inheritance':origins})
    evidence.append({'locator':loc,'status':status})
 report['coverage']['text_normalization']=evidence
 report['coverage_notes'].append({'locator':{},'status':'boundary','detail':'普通文字效果按明确要求逐属性检查；编号符号、复杂容器与上/下标保持。声明属性符合不等于视觉合格。'})
def apply(pkg,f):
 from .engine import _ensure
 loc=f['locator'];r=pkg.paragraphs[loc['paragraph']-1].findall(q('r'))[loc['run']-1];p=loc['property'][5:];v=f['expected'];e=_ensure(_ensure(r,'rPr'),TAGS.get(p,p));e.set(q('val'),str(int(v)) if p=='scale' else str(round(v*(20 if p=='character_spacing' else 2))) if p in TAGS else '1' if v else '0')
def mask(p,f):
 loc=f['locator'];tag=TAGS.get(loc['property'][5:],loc['property'][5:]);r=p.findall(q('r'))[loc['run']-1];rp=r.find(q('rPr'));e=rp.find(q(tag)) if rp is not None else None
 if e is not None:
  e.attrib.pop(q('val'),None)
  if not e.attrib and not len(e):rp.remove(e)


def describe(prop,v):
 """Display only; never coerce execution values."""
 p=prop.removeprefix('text_')
 if p not in PROPS:return None
 if isinstance(v,dict):return '待复核：'+str(v.get('unresolved',v))
 if p in ('shadow','outline','emboss','imprint') and type(v) is bool:return '开启' if v else '关闭'
 if type(v) in (int,float):return f'{v:g}'+('%' if p=='scale' else '磅')+('（标准间距）' if p=='character_spacing' and v==0 else '')
 return str(v)

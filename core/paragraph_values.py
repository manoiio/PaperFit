"""Shared, bounded paragraph declarations. Legacy numbers keep their original units."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json,re
from .package import DemoError,q
from .formats import Unresolved

MODES={'multiple':'auto','exact':'exact','minimum':'atLeast'}
IND_ATTRS=('firstLine','firstLineChars','hanging','hangingChars')
def number(v,lo,hi,step):
 if type(v) not in (int,float):raise DemoError('数值必须为有限数字，不能是布尔或字符串')
 try:d=Decimal(str(v))
 except InvalidOperation:raise DemoError('数值无效') from None
 if not d.is_finite() or not Decimal(str(lo))<=d<=Decimal(str(hi)) or d%Decimal(str(step)):raise DemoError(f'数值须在{lo}–{hi}，步长{step}')
 return d

def line(v):
 if type(v) in (int,float):mode='multiple';x=v
 elif type(v) is dict and set(v)=={'mode','value'}:mode=v['mode'];x=v['value']
 else:raise DemoError('行距须为旧倍数数字或明确的mode/value')
 if type(mode) is not str or mode not in MODES:raise DemoError('行距模式仅倍数、固定、最小')
 number(x,.5 if mode=='multiple' else 1,5 if mode=='multiple' else 120,.05)
 return {'mode':mode,'value':x}

def indent(v,*,hanging=False):
 if type(v) in (int,float):
  if v not in (0,1,2):raise DemoError('旧字符缩进数字仅0/1/2；其他值须显式单位配置')
  d={'kind':'first','unit':'chars','value':v}
 elif type(v) is dict and set(v)=={'kind','unit','value'}:d=deepcopy(v)
 else:raise DemoError('缩进须明确kind/unit/value；旧数字仍为首行字符')
 if d['kind'] not in ('first','hanging') or d['kind']=='hanging' and not hanging:raise DemoError('此对象仅支持首行缩进；悬挂只用于普通参考文献条目')
 if d['unit'] not in ('chars','pt','mm','cm'):raise DemoError('缩进单位只支持字符、磅、毫米、厘米')
 number(d['value'],0,{'chars':10,'pt':144,'mm':50,'cm':5}[d['unit']],.01 if d['unit'] in ('chars','cm') else .05 if d['unit']=='pt' else .1)
 return d

def twips(d):
 x=Decimal(str(d['value']))*{'pt':Decimal(20),'mm':Decimal(1440)/Decimal('25.4'),'cm':Decimal(14400)/Decimal('25.4')}[d['unit']]
 return int(x.quantize(Decimal(1),rounding=ROUND_HALF_UP))
def line_xml(v):
 d=line(v);return {'line':str(int(Decimal(str(d['value']))*(240 if d['mode']=='multiple' else 20))),'lineRule':MODES[d['mode']]}
def read_line(res,layers,*,absent=False):
 if any(len(x.findall(q('spacing')))>1 for x in layers):raise Unresolved('重复行距属性')
 a=res.attrs(layers,'spacing');raw=a.get('line');mode=a.get('lineRule','auto')
 if raw is None:
  if absent:return {'multiple':1,'line_rule':'auto','pt':None}
  raise Unresolved('行距未设置，不补默认单倍')
 if not re.fullmatch(r'\d+',raw) or int(raw)<=0 or mode not in MODES.values():raise Unresolved('行距模式或数值无法解析')
 return {'multiple':int(raw)/240 if mode=='auto' else None,'line_rule':mode,'pt':int(raw)/20 if mode!='auto' else None}
def line_equal(actual,wanted):
 if type(wanted) is dict and 'multiple' in wanted:wanted=wanted['multiple']
 d=line(wanted);return actual['line_rule']==MODES[d['mode']] and abs((actual['multiple'] if d['mode']=='multiple' else actual['pt'])-d['value'])<1e-8

def read_indent(res,layers,wanted):
 d=indent(wanted,hanging=True);a=res.attrs(layers,'ind');inherited=res.attrs(layers[:-1] if layers and res._layer_origin(layers[-1])=='直接段落格式' else layers,'ind')
 if any(len(x.findall(q('ind')))>1 for x in layers):raise Unresolved('重复缩进属性')
 if any(k in inherited for k in IND_ATTRS):
  # Deleting a direct override cannot neutralize an inherited opposing/unit attribute.
  desired=('firstLineChars' if d['unit']=='chars' else 'firstLine') if d['kind']=='first' else ('hangingChars' if d['unit']=='chars' else 'hanging')
  if any(k!=desired for k in IND_ATTRS if k in inherited):raise Unresolved('继承缩进存在相反类型或不同单位，不能安全清理共享样式')
 for k in IND_ATTRS:
  if k in a and not re.fullmatch(r'\d+',a[k]):raise Unresolved('缩进属性值异常')
 key=('firstLine' if d['kind']=='first' else 'hanging')+('Chars' if d['unit']=='chars' else '')
 return {'raw':a,'attribute':key,'value':int(a.get(key,'0')),'unit':'hundredth_char' if d['unit']=='chars' else 'twips'}
def indent_equal(actual,wanted):
 d=indent(wanted,hanging=True);a=actual['raw'];key=actual['attribute'];expected=round(d['value']*100) if d['unit']=='chars' else twips(d)
 return actual['value']==expected and not any(k in a and int(a[k])!=0 for k in IND_ATTRS if k!=key)

def apply(p,prop,wanted):
 from .engine import _ensure
 pp=_ensure(p,'pPr')
 if prop in ('line','line_spacing','line_multiple'):
  if type(wanted) is dict and 'multiple' in wanted:wanted=wanted['multiple']
  e=_ensure(pp,'spacing')
  for k,v in line_xml(wanted).items():e.set(q(k),v)
 elif prop in ('first_line_indent','indent'):
  if type(wanted) is dict and set(wanted)=={'chars'}:wanted=wanted['chars']
  d=indent(wanted,hanging=True);e=_ensure(pp,'ind')
  for k in IND_ATTRS:e.attrib.pop(q(k),None)
  key=('firstLine' if d['kind']=='first' else 'hanging')+('Chars' if d['unit']=='chars' else '')
  e.set(q(key),str(round(d['value']*100) if d['unit']=='chars' else twips(d)))
 elif prop=='alignment':_ensure(pp,'jc').set(q('val'),wanted)
 elif prop in ('before','after'):
  e=_ensure(pp,'spacing')
  for k in (prop,prop+'Lines'):e.attrib.pop(q(k),None)
  e.set(q(prop+'Autospacing'),'0')
  if wanted['unit']=='lines':e.set(q(prop+'Lines'),str(round(wanted['value']*100)));e.set(q(prop),'0')
  else:e.set(q(prop),str(round(wanted['value']*20)))
 else:raise DemoError('未知段落属性')
def mask(p,prop):
 tag,attrs=('spacing',('line','lineRule')) if prop in ('line','line_spacing','line_multiple') else ('ind',IND_ATTRS) if prop in ('first_line_indent','indent') else ('jc',('val',)) if prop=='alignment' else ('spacing',(prop,prop+'Lines',prop+'Autospacing'))
 e=p.find('w:pPr/w:'+tag,__import__('core.package',fromlist=['NS']).NS)
 if e is not None:
  for a in attrs:e.attrib.pop(q(a),None)
  if not len(e) and not e.attrib:e.getparent().remove(e)
def label(v):
 if type(v) is dict and set(v)=={'multiple'} and type(v['multiple']) is dict:return label(v['multiple'])
 if type(v) is dict and v.get('line_rule') in ('auto','exact','atLeast'):
  mode={'auto':'multiple','exact':'exact','atLeast':'minimum'}[v['line_rule']];x=v.get('multiple' if mode=='multiple' else 'pt')
  if type(x) in (int,float):return label({'mode':mode,'value':x})
 if type(v) is dict and set(v)=={'mode','value'}:return {'multiple':f"{v['value']:g}倍",'exact':f"固定{v['value']:g}磅",'minimum':f"最小{v['value']:g}磅"}[v['mode']]
 if type(v) is dict and set(v)=={'kind','unit','value'}:return ('首行' if v['kind']=='first' else '悬挂')+f"{v['value']:g}"+{'chars':'字符','cm':'厘米','mm':'毫米','pt':'磅'}[v['unit']]
 return None

def proof(prop,text):
 """Exact declaration evidence only. Full-source conflict aggregation stays in callers."""
 out=[]
 if prop in ('line','line_spacing','line_multiple'):
  if re.search(r'(?:字号|字体|大小)\s*(?:为|：|:)?\s*(?:固定|最小|至少)',text):return []
  for m in re.finditer(r'(固定(?:值)?|最小(?:值)?|至少)\s*(\d+(?:\.\d+)?)\s*(?:pt|磅)(?:行距)?',text,re.I):out.append({'mode':'exact' if m[1].startswith('固定') else 'minimum','value':float(m[2])})
  out.extend(float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*倍',text))
  if '单倍' in text:out.append(1)
  if '双倍' in text:out.append(2)
 elif prop=='first_line_indent':
  for m in re.finditer(r'(首行|悬挂)(?:缩进|空)?\s*(\d+(?:\.\d+)?|[零一二两])\s*(?:个)?(字符|汉字|字|cm|厘米|mm|毫米|pt|磅)',text,re.I):
   x={'零':0,'一':1,'二':2,'两':2}.get(m[2]);x=float(m[2]) if x is None else x
   out.append({'kind':'first' if m[1]=='首行' else 'hanging','unit':{'字符':'chars','汉字':'chars','字':'chars','厘米':'cm','毫米':'mm','磅':'pt'}.get(m[3],m[3].lower()),'value':x})
 if prop=='first_line_indent' and re.search('无首行缩进|首行不缩进',text):out.append(0)
 return out
def token(v,prop):
 if prop in ('line','line_spacing','line_multiple'):v=line(v)
 elif prop=='first_line_indent':v=indent(v,hanging=True)
 if type(v) is dict and 'value' in v:v={**v,'value':float(v['value'])}
 return json.dumps(v,sort_keys=True,ensure_ascii=False)
def prove(prop,value,quote,clauses):
 expected=token(value,prop);found={token(v,prop) for c in clauses for v in proof(prop,c)}
 if expected not in {token(v,prop) for v in proof(prop,quote)} or found!={expected}:raise DemoError('段落模式、数值或单位与完整原文不符/冲突')

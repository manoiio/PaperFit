"""Selected paragraph attributes, independent units and conservative OOXML inheritance."""
import math
from .formats import Unresolved
from .package import q

TRUE=('1','true','on');FALSE=('0','false','off')
def onoff(value):
 if value in TRUE:return True
 if value in FALSE:return False
 raise Unresolved('无效OnOff属性')

def space(res,layers,side):
 if any(len(x.findall(q('spacing')))>1 for x in layers):raise Unresolved('重复spacing定义，不能可靠解析间距')
 if res.value(layers,'contextualSpacing','0') in TRUE:raise Unresolved('启用同样式上下文间距，需核对相邻段落和渲染效果；不按声明值直接通过')
 attrs=res.attrs(layers,'spacing');auto=attrs.get(side+'Autospacing','0')
 if onoff(auto):raise Unresolved(side+'自动间距由渲染器确定，不自动折算')
 point=attrs.get(side);line=attrs.get(side+'Lines')
 def number(raw):
  if raw is None:return None
  if not str(raw).isdigit():raise Unresolved('间距数值异常')
  return int(raw)
 p,l=number(point),number(line)
 if p is None and l is None:raise Unresolved('有效继承路径也未设置'+side+'间距；未按0处理')
 if p not in (None,0) and l is not None:raise Unresolved('磅值与行单位间距并存冲突，需人工核对')
 if l is not None:return {'value':l/100,'unit':'lines','origin':[res._layer_origin(x) for x in layers],'raw':attrs}
 return {'value':p/20,'unit':'pt','origin':[res._layer_origin(x) for x in layers],'raw':attrs}

def space_fixable(res,layers,side,wanted):
 # A lower inherited beforeLines cannot be disabled by deleting a direct attribute.
 if wanted['unit']=='pt' and any(x.find(q('spacing')) is not None and x.find(q('spacing')).get(q(side+'Lines')) is not None for x in layers if res._layer_origin(x)!='直接段落格式'):
  return False,'继承中的行单位不能安全改为磅值；本阶段不修改共享样式'
 return True,''

def alignment(res,layers):
 if any(len(x.findall(q('jc')))>1 for x in layers):raise Unresolved('重复对齐属性')
 value=res.value(layers,'jc')
 if value not in ('left','right','center','both'):raise Unresolved('对齐未设置/未支持或无法可靠继承')
 return value

def bold(res,layers):
 state=False;positive_styles=0;default_positive=False
 for x in layers:
  elements=x.findall(q('b'))
  if len(elements)>1:raise Unresolved('重复加粗属性')
  if not elements:continue
  value=onoff(elements[0].get(q('val'),'1'));origin=res._layer_origin(x)
  if origin=='直接run格式':return value
  if '样式:' in origin:
   positive_styles+=int(value)
   if value:state=not state
  else:state=value;default_positive=value
 if positive_styles>1 or (default_positive and positive_styles):raise Unresolved('多层样式切换型加粗存在跨软件边界，待复核')
 return state

def spacing_equal(actual,wanted):
 return (actual['unit']==wanted['unit'] and abs(actual['value']-wanted['value'])<.001) or (actual['value']==wanted['value']==0)

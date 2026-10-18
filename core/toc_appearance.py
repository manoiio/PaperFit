"""Project presentation defaults, not a school rule. Exact TOC cache pPr only."""
from copy import deepcopy
from lxml import etree as E
from .package import q,NS,DemoError
from .formats import Resolver,Unresolved

MODES=('preserve','standard')
def validate(mode):
 if type(mode) is not str or mode not in MODES:raise DemoError('目录外观须为保留原格式或项目默认格式')
 return mode

def prepare(pkg,field,templates,levels):
 from .word_fields import field_paragraphs
 from .widths import _sections,_page
 ps=field_paragraphs(pkg,field);p=ps[field['start']-1];owner=p
 while owner.getparent() is not pkg.root.find(q('body')):
  owner=owner.getparent()
  if owner is None:raise DemoError('目录所属主文档对象无法定位')
 record={'mode':'standard','source':'项目默认目录外观（非学校强制要求）','properties':['tabs:右对齐/dot','ind:缺失层级缩进','jc:居左'],'levels':[]}
 try:
  number,sp=_sections(pkg)[owner];width=_page(pkg,number,sp)['body_width_twips'];res=Resolver(pkg);out={}
  for level in sorted(set(levels)):
   original=templates.get(level)
   pr=deepcopy(original)
   if pr is None:
    # Carry safe common paragraph/text formatting without borrowing another level's indent.
    pr=deepcopy(next(iter(templates.values()))) if templates else E.Element(q('pPr'))
    for tag in ('pStyle','ind','tabs'):
     for e in pr.findall(q(tag)):pr.remove(e)
   mock=E.Element(q('p'));mock.append(pr)
   sid=pr.find(q('pStyle'));ident=sid.get(q('val')) if sid is not None else None
   implicit=ident in ('TOC1','TOC2','TOC3') and ident not in res.styles
   if implicit:
    # Word built-in TOC style may be referenced without a stored definition.
    # Do not infer its font/size; explicitly bound only this authorised cache's geometry.
    layers=[pr]
    record.setdefault('retained_implicit_styles',[]).append(ident)
   else:layers=res.layers(mock,kind='pPr')
   if res.value(layers,'bidi','0') not in ('0','false','off') or res.value(layers,'textDirection','lrTb')!='lrTb' or any(layer.find(q('numPr')) is not None for layer in layers):raise Unresolved('非普通从左到右目录或目录自身带自动编号，保留外观')
   # Conflicting, character-based and inherited unknown indent semantics stay protected.
   attrs=res.attrs(layers,'ind');ind=E.Element(q('ind')) if attrs else None
   if ind is not None:
    for k,v in attrs.items():ind.set(q(k),v)
   if ind is not None and any(k not in {q(x) for x in ('left','right','firstLine','hanging')} for k in ind.attrib):raise Unresolved('目录缩进含字符单位或未知属性，保留外观')
   if any(len(layer.findall(q('tabs')))>1 for layer in layers):raise Unresolved('重复目录制表位容器')
   nums={}
   if ind is not None:
    for k,v in ind.attrib.items():
     if not v.lstrip('-').isdigit():raise Unresolved('目录缩进值无法解释')
     nums[E.QName(k).localname]=int(v)
   left=nums.get('left',(level-1)*360);right=nums.get('right',0)
   if min(left,right)<0 or width-right-left<720:raise Unresolved('目录缩进后可用宽度不足')
   if 'firstLine' in nums and 'hanging' in nums and (nums['firstLine'] or nums['hanging']):raise Unresolved('目录首行和悬挂缩进冲突')
   direct=pr.find(q('ind'))
   if direct is None:direct=E.SubElement(pr,q('ind'))
   if 'left' not in nums:direct.set(q('left'),str(left))
   if implicit:
    direct.set(q('right'),str(right));direct.set(q('firstLine'),'0');direct.set(q('hanging'),'0')
   target=width-right
   effective_tabs={}
   for layer in layers:
    for stop in layer.findall('w:tabs/w:tab',NS):
     pos=stop.get(q('pos'))
     if stop.get(q('val'))=='clear':effective_tabs.pop(pos,None)
     else:effective_tabs[pos]=stop
   current=effective_tabs.get(str(target))
   if original is not None and current is not None and current.get(q('val'))=='right' and current.get(q('leader'))=='dot' and (level==1 or left>0) and res.value(layers,'jc','left')=='left':
    out[level]=deepcopy(original);record['levels'].append({'level':level,'left_twips':left,'right_tab_twips':target,'body_width_twips':width,'state':'already_satisfied'});continue
   jc=pr.find(q('jc'))
   if jc is None:jc=E.SubElement(pr,q('jc'))
   jc.set(q('val'),'left')
   # Clear inherited stops, retaining a deterministic numbering-to-title stop.
   stops=set()
   for layer in layers:
    tabs=layer.find(q('tabs')) if layer is not None else None
    if tabs is not None:
     for stop in tabs:
      raw=stop.get(q('pos'),'')
      if not raw.lstrip('-').isdigit():raise Unresolved('目录制表位无法解释')
      stops.add(int(raw))
   old=pr.find(q('tabs'))
   if old is not None:pr.remove(old)
   tabs=E.SubElement(pr,q('tabs'))
   title_stop=left+max(0,nums.get('firstLine',0))+360
   if title_stop>=target:raise Unresolved('目录首行缩进后没有可靠的制表空间')
   for pos in sorted(stops-{target,title_stop}):
    t=E.SubElement(tabs,q('tab'));t.set(q('val'),'clear');t.set(q('pos'),str(pos))
   t=E.SubElement(tabs,q('tab'));t.set(q('val'),'left');t.set(q('pos'),str(title_stop))
   t=E.SubElement(tabs,q('tab'));t.set(q('val'),'right');t.set(q('leader'),'dot');t.set(q('pos'),str(target))
   # Ordered pPr children are required for Word to honour these properties.
   order=('pStyle','keepNext','keepLines','pageBreakBefore','framePr','widowControl','numPr','suppressLineNumbers','pBdr','shd','tabs','suppressAutoHyphens','kinsoku','wordWrap','overflowPunct','topLinePunct','autoSpaceDE','autoSpaceDN','bidi','adjustRightInd','snapToGrid','spacing','ind','contextualSpacing','mirrorIndents','suppressOverlap','jc','textDirection','textAlignment','textboxTightWrap','outlineLvl','divId','cnfStyle','rPr','sectPr','pPrChange')
   for child in sorted(list(pr),key=lambda c:order.index(E.QName(c).localname) if E.QName(c).localname in order else len(order)):pr.append(child)
   out[level]=pr;record['levels'].append({'level':level,'left_twips':left,'right_tab_twips':target,'body_width_twips':width,'state':'applied'})
  record.update(state='already_satisfied' if all(x['state']=='already_satisfied' for x in record['levels']) else 'applied',section=number)
  return out,record
 except (Unresolved,KeyError,ValueError) as exc:
  record.update(state='kept',reason=str(exc));return templates,record

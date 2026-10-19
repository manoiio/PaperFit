"""Bounded TOC policy, confirmed roles only; no paragraph role/style changes."""
from copy import deepcopy
import re
from lxml import etree as E
from .package import q,NS,DemoError
DEFAULT={'version':1,'depth':3,'abstracts':True,'back':True,'self':True}
def validate(value):
 if value is None:return None
 if type(value) is not dict or set(value)!=set(DEFAULT) or type(value['version']) is not int or value['version']!=1 or type(value['depth']) is not int or value['depth'] not in (1,2,3) or any(type(value[k]) is not bool for k in ('abstracts','back','self')):raise DemoError('目录收录策略须明确层级1–3及摘要/后置标题/目录自身开关')
 return deepcopy(value)
def tc(text):
 if not text or len(text)>300 or re.search(r'["\\\r\n\t]',text):raise DemoError('目录附加标题包含不能可靠编码的字符，保持')
 out=[]
 for typ in ('begin','instruction','end'):
  r=E.Element(q('r'))
  if typ=='instruction':
   e=E.SubElement(r,q('instrText'));e.set('{http://www.w3.org/XML/1998/namespace}space','preserve');e.text=' TC "'+text+'" \\f C \\l "1" '
  else:E.SubElement(r,q('fldChar')).set(q('fldCharType'),typ)
  out.append(r)
 return out

def owned_tc(p,text):
 def signature(e):return (e.tag,tuple(sorted(e.attrib.items())),e.text or '',tuple(signature(c) for c in e))
 try:expected=[signature(e) for e in tc(text)]
 except DemoError:return []
 matches=[];children=list(p)
 for i in range(len(children)-2):
  if [signature(e) for e in children[i:i+3]]==expected:matches.extend(children[i:i+3])
 return matches

def select(pkg,manifest,policy,toc,level_of):
 """One ordered unique set drives generation, Word calculation and verification."""
 policy=validate(policy);out=[];kept=[]
 ps=pkg.paragraphs
 # Keep an already-linked, uniquely bookmarked back title when its ordinary
 # formatting role remains pending. This is continuity of TOC membership,
 # never permission to format that paragraph or classify its following text.
 existing=set()
 from .word_fields import field_block
 for paragraph in field_block(pkg,toc):
  for link in paragraph.findall(q('hyperlink')):
   name=link.get(q('anchor'));matches=pkg.root.xpath('.//w:bookmarkStart[@w:name=$n]',namespaces=NS,n=name) if name else []
   if len(matches)==1 and matches[0].getparent() in ps:existing.add(matches[0].getparent())
 from .classification import suggest_paragraph_types
 suggestions={r['index']:r['suggested_type'] for r in suggest_paragraph_types(pkg.path,include_sections=True)['paragraphs']}
 body=pkg.root.find(q('body'));toc_ps=set(ps[toc['start']-1:toc['end']]) if not toc.get('container') else set()
 owner=(body.findall(q('sdt'))[toc['container']-1] if toc.get('container') else ps[toc['start']-1]);at=body.index(owner)
 # Self inclusion is only the exact adjacent directory title, never keyword search.
 preceding=body[at-1] if at else None
 for n,p in enumerate(ps,1):
  if p in toc_ps or str(n) in manifest.get('material_exclusions',{}):continue
  role=manifest['paragraph_types'][str(n)];native=level_of(pkg,p,'\\u' in toc['instruction']);level=None;extra=False
  is_self=p is preceding and re.sub(r'\s','', ''.join(p.xpath('./w:r/w:t/text()',namespaces=NS)))=='目录'
  if is_self:
   if policy['self']:level=1;extra=native is None or native>policy['depth']
  elif role.startswith('heading') and role[-1:] in ('1','2','3'):
   if int(role[-1])<=policy['depth'] and native==int(role[-1]):level=int(role[-1])
   elif int(role[-1])<=policy['depth']:kept.append({'paragraph':n,'reason':'确认标题层级与Word有效层级不一致'})
  elif policy['abstracts'] and role in ('abstract_cn_title','abstract_en_title'):level=1;extra=native is None or native>policy['depth']
  elif policy['back'] and role in ('reference_title','ack_title','appendix_title'):level=1;extra=native is None or native>policy['depth']
  elif policy['back'] and role in ('pending','other') and p in existing and native==1 and suggestions.get(n) in ('reference_title','ack_title','appendix_title'):level=1
  if level is not None:out.append({'paragraph':n,'level':level,'extra':extra,'role':role})
  elif native is not None and native<=policy['depth']:kept.append({'paragraph':n,'reason':'域标题样式与本次确认收录集合不一致，不能静默改正文样式'})
 return out,kept

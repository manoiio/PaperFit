"""Optional R44. Read-only OPC story/target index; no evaluation or URL access.

Exact-name lookup only. A target's existence is not field freshness or a tested
jump. The index contains JSON values, never mutable XML or executable locators.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import PurePosixPath
from posixpath import normpath
from urllib.parse import unquote
import json,re
from lxml import etree as E
from .package import Package,DemoError,parse,q,NS,sha256
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
PREFIX='application/vnd.openxmlformats-officedocument.wordprocessingml.'
SOURCE={'label':'产品结构检查（非学校格式规定）','quote':'产品解释：验证已解析内部目标与书签边界，不更新域或推算实际页码。','interpretation':'按已验证Word故事部件、书签边界与精确目标核对；不更新域、不判断实际页码或跳转。'}
LIMITS=['R44为可选产品结构检查，不是学校格式规则；全部只读，不创建书签、不修改目标、域或缓存。','名称精确匹配；大小写近似、特殊名称、表格列书签及复杂边界不猜测。','目标存在不等于缓存新鲜、引用内容正确、实际页码或真实跳转已经验收。','只读索引可覆盖已验证主文档、页眉页脚和注释；文字修正仅明确启用后的已确认正文、参考文献、脚注/尾注普通链接。','自动目录、域、修订、SDT和链接段落属性仍保护；表格及页眉页脚链接文字未开放修正。']
MAX_OBJECTS=20000
NAME=re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,39}\Z')

def digest(d):return sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode())
def default_template():return {'structure_version':1,'kind':'paper-grid-internal-reference-supplement','name':'内部引用产品检查','integrity':True,'internal_text':False,'source':'product_structure'}
def template(d):
 if type(d) is not dict or set(d)!={'structure_version','kind','name','integrity','internal_text','source'} or type(d['structure_version']) is not int or d['structure_version']!=1 or d['kind']!='paper-grid-internal-reference-supplement':raise DemoError('内部引用补充配置结构或版本无效')
 if type(d['name']) is not str or not 1<=len(d['name'])<=80 or any(c in d['name'] for c in '/\\\x00\n') or d['source']!='product_structure' or any(type(d[k]) is not bool for k in ('integrity','internal_text')):raise DemoError('内部引用配置名称、开关或来源无效')
 if not d['integrity']:raise DemoError('内部引用补充配置须明确启用R44；停用请关闭模块，不以空配置冒充参与检查')
 return deepcopy(d)
def make_scope(pkg):return {'input_sha256':pkg.hash,'confirmed':False,'confirmation':'内部引用检查草稿','template':default_template()}
def validate_scope(pkg,s,*,confirmed=True):
 if type(s) is not dict or set(s)!={'input_sha256','confirmed','confirmation','template'} or s['input_sha256']!=pkg.hash:raise DemoError('内部引用范围文件绑定或结构无效')
 if type(s['confirmed']) is not bool or confirmed and not s['confirmed'] or type(s['confirmation']) is not str or not 1<=len(s['confirmation'])<=200:raise DemoError('内部引用检查配置尚未确认')
 template(s['template']);return deepcopy(s)
def configure(pkg,classification):
 s=(classification or {}).get('reference_scope')
 if s:validate_scope(pkg,s)
 pkg._reference_text_enabled=bool(s and s['template']['internal_text'])
 pkg._reference_integrity_enabled=bool(s and s['template']['integrity'])


def _stories(pkg):
 """Only verified reachable content parts; malformed/uncovered stories lower completeness."""
 stories=[('word/document.xml','document',pkg.root)];issues=[]
 def issue(reason,part=None,**kw):issues.append({'part':part,'reason':reason,**kw})
 try:
  ct=parse(pkg.parts['[Content_Types].xml']);rels=parse(pkg.parts.get('word/_rels/document.xml.rels',b''))
  if ct.tag!='{'+CT+'}Types' or any(e.tag not in ('{'+CT+'}Override','{'+CT+'}Default') for e in ct):raise DemoError('内容类型结构无效')
  types=defaultdict(list)
  for e in ct:
   if e.tag=='{'+CT+'}Override':types[e.get('PartName','').lstrip('/')].append(e.get('ContentType'))
  if any(len(v)!=1 for v in types.values()):raise DemoError('重复内容类型覆盖')
  if rels.tag!='{'+REL+'}Relationships' or any(e.tag!='{'+REL+'}Relationship' for e in rels) or any(not e.get('Id') for e in rels) or len({e.get('Id') for e in rels})!=len(rels):raise DemoError('主文档关系结构或ID异常')
 except (DemoError,E.XMLSyntaxError):return stories,[{'part':'word/document.xml','reason':'故事关系或内容类型损坏/缺失，目标清单不完整'}]
 seen={'word/document.xml'};bound={}
 for e in pkg.root.iter():
  if e.tag in (q('headerReference'),q('footerReference')):
   rid=e.get('{'+R+'}id');kind='header' if e.tag==q('headerReference') else 'footer'
   if not rid:issue('分节故事引用缺少关系ID')
   bound.setdefault(rid,set()).add(kind)
 for r in rels:
  kind=r.get('Type','').removeprefix(R+'/')
  if kind not in ('header','footer','footnotes','endnotes','comments','glossaryDocument','subDocument'):continue
  if kind not in ('header','footer','footnotes','endnotes'):issue('未覆盖的关联故事类型：'+kind);continue
  target=unquote(r.get('Target',''));member=normpath(target.lstrip('/') if target.startswith('/') else 'word/'+target)
  if not target or r.get('TargetMode') not in (None,'Internal') or '..' in target.split('/') or not member.startswith('word/') or member not in pkg.parts or '?' in target or '#' in target or '\\' in target:
   issue('故事关系目标缺失、外部或路径不支持');continue
  expected=PREFIX+kind+'+xml'
  if types.get(member)!=[expected]:issue('故事内容类型不匹配',member);continue
  if kind in ('header','footer') and bound.get(r.get('Id'))!={kind}:issue('故事关系未唯一匹配分节用途',member);continue
  if member in seen:issue('多条关系共享故事目标，保守待复核',member);continue
  try:
   root=parse(pkg.parts[member]);tag={'header':'hdr','footer':'ftr'}.get(kind,kind)
   if root.tag!=q(tag):raise DemoError('故事根节点不匹配')
   seen.add(member)
   if kind in ('footnotes','endnotes'):
    singular=kind[:-1];ids=Counter(e.get(q('id')) for e in root)
    if any(e.tag!=q(singular) for e in root) or any(v!=1 for v in ids.values()) or None in ids:issue('注释容器或ID异常',member)
    for i,n in enumerate(root,1):
     if n.tag==q(singular):stories.append((member,singular+':'+str(n.get(q('id')))+':'+str(i),n))
   else:stories.append((member,kind,root))
  except (DemoError,E.XMLSyntaxError):issue('故事XML损坏或结构不支持',member)
 for rid,kinds in bound.items():
  if len([r for r in rels if r.get('Id')==rid and r.get('Type') in {R+'/'+k for k in kinds}])!=1:issue('分节引用未唯一匹配故事关系')
 for part,ts in types.items():
  if any(t and t.startswith(PREFIX) and any(x in t for x in ('header+xml','footer+xml','footnotes+xml','endnotes+xml','comments+xml','glossary+xml')) for t in ts) and part not in seen:issue('存在未覆盖或未关联的故事内容类型',part)
 from .notes import inventory as note_inventory
 ni=note_inventory(pkg)
 for x in ni['issues']:issue('注释引用结构：'+x['reason'],x.get('part'))
 for x in ni['objects']:
  if not x['safe_relationship']:issue('注释引用关系不安全：'+x['reason'],x['part'],story=x['key'])
 return stories,issues


def field_target(f):
 """Bounded, non-evaluating REF/PAGEREF grammar. Unsupported switches stay review."""
 instruction=f['instruction']
 if len(instruction)>4096:return {'kind':'unknown','target':None,'reason':'域指令超过4096字符'}
 if not re.fullmatch(r'\s*(?:"[^"\r\n]*"|[^\s"]+)(?:\s+(?:"[^"\r\n]*"|[^\s"]+))*\s*',instruction):
  return {'kind':instruction.strip().split(' ',1)[0].upper(),'target':None,'reason':'域引号或词法边界不完整'}
 tokens=re.findall(r'"[^"\r\n]*"|[^\s"]+',instruction)
 if len(tokens)>128:return {'kind':tokens[0].upper(),'target':None,'reason':'域指令词元超过128项'}
 if not tokens:return {'kind':'unknown','target':None,'reason':'域指令为空'}
 kind=tokens[0].upper()
 if kind not in ('REF','PAGEREF'):return {'kind':kind,'target':None,'reason':'非书签引用指令，未作为REF/PAGEREF判断'}
 target=tokens[1].strip('"') if len(tokens)>1 else None
 reason=None
 if not f['balanced'] or not f.get('reliable',True):reason='断裂或嵌套指令结构不可靠'
 elif not target or not NAME.fullmatch(target):reason='目标名称不在首版明确ASCII名称范围，或缺少目标'
 else:
  i=2
  while i<len(tokens):
   token=tokens[i];i+=1
   if token=='\\*':
    if i>=len(tokens) or tokens[i] not in ('MERGEFORMAT','CHARFORMAT','Arabic','ROMAN','roman'):reason='格式开关不支持';break
    i+=1
   elif token not in (('\\h','\\p','\\n','\\r','\\w','\\t') if kind=='REF' else ('\\h','\\p')):reason='未支持或含糊的域开关/参数';break
 return {'kind':kind,'target':target,'reason':reason}


def _build(pkg):
 stories,issues=_stories(pkg);unsafe_stories={(x.get('part'),x.get('story')) for x in issues if x.get('story')};bookmarks=[];refs=[];fields=[];top={p:i for i,p in enumerate(pkg.paragraphs,1)}
 for part,owner,root in stories:
  ordered=list(root.iter())
  if len(ordered)>200000 or sum(e.tag in {q(t) for t in ('bookmarkStart','bookmarkEnd','hyperlink','fldChar','fldSimple')} for e in ordered)>MAX_OBJECTS:raise DemoError('故事节点或内部引用数量超过安全上限，未执行部分判定')
  order={e:i for i,e in enumerate(ordered)};ps=[p for p in root.iter(q('p')) if not any(a.tag==q('txbxContent') for a in p.iterancestors())];pmap={p:i for i,p in enumerate(ps,1)}
  def loc(e):
   p=next((a for a in e.iterancestors() if a.tag==q('p')),None)
   return {'part':part,'story':owner,'story_paragraph':pmap.get(p),'xml_ordinal':order[e],**({'paragraph':top[p]} if p in top else {})}
  # Unknown containers can conceal targets. Do not turn not-found into a proved absence.
  if root.xpath('.//w:txbxContent|.//w:altChunk|.//w:subDoc|.//w:ins|.//w:del|.//w:moveFrom|.//w:moveTo',namespaces=NS):issues.append({'part':part,'reason':'文本框、修订或外部内容未完整解释，缺失目标仅待复核'})
  if root.xpath('.//mc:AlternateContent',namespaces={'mc':'http://schemas.openxmlformats.org/markup-compatibility/2006'}):issues.append({'part':part,'reason':'兼容条件分支尚未选择，不能证明目标清单完整或授权内部链接文字修正'})
  canonical_id=re.compile(r'(?:0|[1-9][0-9]{0,9})\Z')
  if any(not canonical_id.fullmatch(e.get(q('id'),'')) for e in ordered if e.tag in (q('bookmarkStart'),q('bookmarkEnd'))):issues.append({'part':part,'reason':'书签ID含非规范ASCII整数形式；可能存在数字别名，首版不证明边界唯一'})
  starts=defaultdict(list);ends=defaultdict(list)
  for e in root.iter(q('bookmarkStart')):starts[e.get(q('id'))].append(e)
  for e in root.iter(q('bookmarkEnd')):ends[e.get(q('id'))].append(e)
  for ident,es in starts.items():
   for e in es:
    name=e.get(q('name'));reason=None;matches=ends[ident]
    if ident is None or not canonical_id.fullmatch(ident) or len(es)!=1 or len(matches)!=1:reason='书签ID或开始/结束边界缺失、重复'
    elif order[e]>=order[matches[0]]:reason='结束边界未位于开始之后'
    elif any(e.get(q(x)) is not None for x in ('colFirst','colLast')):reason='表格列/非连续书签首版待复核'
    elif root.tag in (q('footnote'),q('endnote')) and root.get(q('type'),'normal')!='normal':reason='系统注释分隔对象中的书签不作为普通跳转目标'
    elif (part,owner) in unsafe_stories:reason='注释故事引用关系异常，目标待复核'
    elif set(e.attrib)-{q('id'),q('name')} or set(matches[0].attrib)-{q('id')}:reason='书签边界含未解释属性，不推测位移或其他语义'
    elif not name or not NAME.fullmatch(name):reason='名称不在首版明确ASCII名称范围（不猜测匹配）'
    elif any(a.tag in {q(x) for x in ('txbxContent','ins','del','moveFrom','moveTo')} for el in (e,matches[0]) for a in el.iterancestors()):reason='书签边界位于未解释复杂结构'
    bookmarks.append({'name':name,'id':ident,'location':loc(e),'end_location':loc(matches[0]) if len(matches)==1 else None,'valid_boundary':reason is None,'reason':reason or '同一故事内按ID唯一配对，边界顺序有效'})
  for ident,es in ends.items():
   if ident not in starts:bookmarks.append({'name':None,'id':ident,'location':loc(es[0]),'end_location':None,'valid_boundary':False,'reason':'孤立结束边界，没有对应开始'})
  for e in root.iter(q('hyperlink')):
   anchor=e.get(q('anchor'))
   if anchor is not None:
    reason=None
    if e.get('{'+R+'}id') is not None or e.get(q('docLocation')) is not None:reason='anchor与关系/docLocation组合含糊，不推测目标'
    elif set(e.attrib)-{q(x) for x in ('anchor','tooltip','history','tgtFrame')}:reason='内部链接有未知属性'
    refs.append({'kind':'hyperlink','target':anchor,'location':loc(e),'instruction':None,'cached_result_present':bool(e.xpath('.//w:t',namespaces=NS)),'parse_reason':reason})
  from .toc import parse_fields
  fs,broken=parse_fields(pkg,paragraphs=ps,detailed=True)
  for i,f in enumerate(fs,1):
   target=field_target(f);positions=[{'part':part,'story':owner,'story_paragraph':int(o[2:]),**({'paragraph':top[ps[int(o[2:])-1]]} if ps[int(o[2:])-1] in top else {})} for o in f['objects']]
   public={'kind':target['kind'],'target':target['target'],'location':{**positions[0],'field':i},'positions':positions,'instruction':f['instruction'],'representation':f['representation'],'balanced':f['balanced'],'nested':f.get('nested',False),'cached_result_present':bool(f['result']),'parse_reason':target['reason']}
   fields.append(public)
   if target['kind'] in ('REF','PAGEREF'):refs.append(deepcopy(public))
  if broken:
   refs.append({'kind':'broken_field','target':None,'location':{'part':part,'story':owner,'objects':broken},'instruction':None,'cached_result_present':False,'parse_reason':'孤立或断裂域边界，不能推测目标'})
  if len(bookmarks)+len(refs)+len(fields)>MAX_OBJECTS:raise DemoError('内部引用索引超过20000对象上限，未执行部分判定')
 byname=defaultdict(list);fold=defaultdict(set)
 for b in bookmarks:
  if b['name'] is not None:byname[b['name']].append(b);fold[b['name'].casefold()].add(b['name'])
 complete=not issues
 resolutions={}
 for name,bs in byname.items():
  reason=None
  if len(bs)!=1 or len(fold[name.casefold()])!=1:reason='书签名称重复或大小写近似，Word/标准可能选择不同目标；不代选'
  elif not bs[0]['valid_boundary']:reason=bs[0]['reason']
  elif not complete:reason='已解析范围内目标存在，但故事清单不完整，不能证明目标全局唯一'
  resolutions[name]={'state':'review' if reason else 'pass','reason':reason or '唯一名称、有效边界的已解析目标','target_location':bs[0]['location'] if not reason else None}
 def resolve(name):
  if not isinstance(name,str) or not NAME.fullmatch(name):return {'state':'review','reason':'目标名称不在支持范围，未猜测','target_location':None}
  if name in resolutions:return deepcopy(resolutions[name])
  if name.casefold() in fold:return {'state':'review','reason':'仅存在大小写近似名称，不当作精确匹配或确定缺失','target_location':None}
  return {'state':'problem' if complete else 'review','reason':'已验证故事清单中目标未找到' if complete else '目标未找到，但故事覆盖不完整，不能判定断链','target_location':None}
 groups={}
 for i,r in enumerate(refs,1):
  r['id']='ref:'+str(i);result=resolve(r['target']) if not r['parse_reason'] else {'state':'review','reason':r['parse_reason'],'target_location':None};r.update(result)
  key='target:'+sha256(str(r['target']).encode())[:20] if r['target'] else r['id']
  if r['parse_reason']:key+=':parse:'+str(i)
  r['fault_key']=key
  group=groups.setdefault(key,{'key':key,'target':r['target'],'status':r['state'],'reason':r['reason'],'references':[]});group['references'].append(r['id'])
 for b in bookmarks:
  result=resolve(b['name']) if b['name'] else {'state':'review','reason':b['reason']};b['state']=result['state'];b['reason']=result['reason']
  if b['state']!='pass':
   key='target:'+sha256(str(b['name']).encode())[:20] if b['name'] else 'boundary:'+digest(b['location'])[:20]
   groups.setdefault(key,{'key':key,'target':b['name'],'status':'review','reason':b['reason'],'references':[]})
 return {'input_sha256':pkg.hash,'bookmarks':bookmarks,'references':refs,'fields':fields,'groups':list(groups.values()),'issues':issues,'complete':complete,'stories':[{'part':p,'story':o} for p,o,_ in stories],'limits':LIMITS,'resolutions':resolutions,'fold_names':list(fold)}

def _index(pkg):
 if not hasattr(pkg,'_internal_reference_index'):
  # Immutable serialized index. No mutable XML or cross-session/global document cache.
  pkg._internal_reference_index=json.dumps(_build(pkg),ensure_ascii=False,sort_keys=True).encode()
  data=json.loads(pkg._internal_reference_index)
  from types import MappingProxyType
  pkg._internal_reference_lookup=MappingProxyType({k:json.dumps(v,ensure_ascii=False) for k,v in data['resolutions'].items()})
  pkg._internal_reference_folds=frozenset(data['fold_names']);pkg._internal_reference_complete=data['complete']
 return pkg._internal_reference_index

def inventory(path):
 pkg=path if isinstance(path,Package) else Package(path);d=json.loads(_index(pkg));d.pop('resolutions');d.pop('fold_names');return d

def resolve_target(pkg,name):
 _index(pkg)
 if not isinstance(name,str) or not NAME.fullmatch(name):return {'state':'review','reason':'目标名称不在支持范围','target_location':None}
 if name in pkg._internal_reference_lookup:return json.loads(pkg._internal_reference_lookup[name])
 if name.casefold() in pkg._internal_reference_folds:return {'state':'review','reason':'仅存在大小写近似名称，未猜测匹配','target_location':None}
 return {'state':'problem' if pkg._internal_reference_complete else 'review','reason':'目标未找到' if pkg._internal_reference_complete else '目标未找到且故事覆盖不完整','target_location':None}

def append_checks(report,pkg,classification):
 s=(classification or {}).get('reference_scope')
 if not s or not s['template']['integrity']:return
 validate_scope(pkg,s);inv=inventory(pkg);cfg=s['template'];fs=report['findings']
 def add(key,status,actual,detail):
  fs.append({'key':'R44:'+key,'rule_id':'R44','rule_name':'内部引用结构完整性（产品检查）','object_type':'internal_reference','locator':{'reference_target':key},'actual':actual,'expected':'唯一且边界有效的可解析内部目标','status':status,'fixable':False,'source':deepcopy(SOURCE),'detail':detail})
 for g in inv['groups']:add(g['key'],g['status'],g,g['reason']+'；一个目标/解析故障组，影响'+str(len(g['references']))+'处引用；缓存及实际跳转未验收。')
 for i,issue in enumerate(inv['issues'],1):add('coverage:'+str(i),'review',issue,issue['reason'])
 if not inv['groups']:add('none','not_applicable',None,'未发现受支持的内部引用或异常书签；无引用不判缺项，未引用有效书签不判错误。')
 report['internal_references']=inv;report['coverage']['reference_scope']=deepcopy(s);report['coverage']['reference_limits']=LIMITS
 report['rules']['reference_supplement']={'name':cfg['name'],'version':1,'sha256':digest(cfg),'integrity':cfg['integrity'],'internal_text':cfg['internal_text'],'source':SOURCE}
 report['summary']['rule_count']+=1
 for status,key in [('problem','problem_count'),('review','review_findings'),('pass','pass_count'),('not_applicable','not_applicable_count')]:report['summary'][key]=sum(f['status']==status for f in fs)
 report['summary']['review_count']=report['summary']['review_findings']+len(report['coverage_notes']);report['summary']['applicable_rule_count']=len({f['rule_id'] for f in fs if f['status']!='not_applicable'});report['summary']['conclusion']='已覆盖检查发现问题' if report['summary']['problem_count'] else '已覆盖检查未发现问题'

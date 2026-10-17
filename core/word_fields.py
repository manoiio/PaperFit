"""Explicit, bounded Word calculator transaction. No ordinary preservation exemption.
Only rebuilt authorised TOC caches, selected field caches, and exact destination
bookmark pairs enter output. The saved Word package is NEVER published.
"""
from copy import deepcopy
from pathlib import Path
import re,json
from lxml import etree as E
from .package import Package,DemoError,NS,q,sha256,write_new
from .toc import ordered_text,nodes
VERSION='word-fields-1'
MAX_PASSES=4
SOURCE={'label':'本机Word显式目录/引用更新（非学校新规则）','quote':'仅更新已授权的安全目录和目标唯一的REF/PAGEREF保存结果'}
def canon(e):return E.tostring(e,method='c14n')
def text(e):return ''.join(e.xpath('.//w:t/text()',namespaces=NS))
def clean_instruction(s):return ' '.join(s.split())
def fields(pkg):
 """Main-body direct runs only; nested TOC result fields are not independent grants."""
 ps=pkg.paragraphs;out=[];stack=[];broken=False
 for n,p in enumerate(ps,1):
  for j,e in enumerate(p):
   if e.tag==q('fldSimple'):
    out.append({'instruction':e.get(q('instr'),''),'start':n,'end':n,'first':j,'last':j,'simple':True,'node':e,'locked':e.get(q('fldLock')) in ('1','true'),'nested':bool(stack)})
   elif e.tag==q('r'):
    for x in e:
     if x.tag==q('fldChar'):
      typ=x.get(q('fldCharType'))
      if typ=='begin':stack.append({'instruction':'','start':n,'first':j,'simple':False,'locked':x.get(q('fldLock')) in ('1','true'),'nested':bool(stack),'separate':None})
      elif typ=='separate':
       if not stack:broken=True
       else:stack[-1]['separate']=(n,j)
      elif typ=='end':
       if not stack:broken=True
       else:
        f=stack.pop();f.update(end=n,last=j);out.append(f)
     elif x.tag==q('instrText'):
      if stack and stack[-1].get('separate') is None:stack[-1]['instruction']+=x.text or ''
      else:broken=True
 return sorted(out,key=lambda f:(f['start'],f['first'])),bool(stack) or broken

def toc_levels(code):
 m=re.fullmatch(r'\s*TOC\s+\\o\s+"([1-3])-([1-3])"((?:\s+\\[hzu])*)\s*',code,re.I)
 if not m or int(m[1])>int(m[2]):return None
 return list(range(int(m[1]),int(m[2])+1))
def paragraph_level(pkg,p,outline=False):
 from .formats import Resolver
 sid=p.find('w:pPr/w:pStyle',NS);sid=sid.get(q('val')) if sid is not None else None
 style=next((s for s in pkg.styles if s.get(q('styleId'))==sid),None) if pkg.styles is not None else None
 name=style.find('w:name',NS) if style is not None else None
 m=re.fullmatch(r'(?:heading|标题)\s*([1-3])',name.get(q('val'),'') if name is not None else '',re.I)
 if m:return int(m[1])
 if outline:
  try:
   res=Resolver(pkg);value=res.value(res.layers(p,kind='pPr'),'outlineLvl')
   if value is not None and int(value) in (0,1,2):return int(value)+1
  except Exception:pass
 return None

def reference_view(pkg,issues):
 """R44 remains conservative. Prove page-isolation leftovers contain no targets.
 Only unreachable validated header/footer parts without ANY bookmark or hidden
 container can be excluded from the calculator's uniqueness view. Bytes persist.
 """
 from .package import parse
 allowed={'故事关系未唯一匹配分节用途','存在未覆盖或未关联的故事内容类型'}
 if not issues or any(i['reason'] not in allowed or not i.get('part') for i in issues):return pkg,[]
 parts=sorted({i['part'] for i in issues});rels=parse(pkg.parts['word/_rels/document.xml.rels']);ct=parse(pkg.parts['[Content_Types].xml']);R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
 active={e.get(R) for e in pkg.root.iter() if e.tag in (q('headerReference'),q('footerReference'))};remove=[]
 for part in parts:
  root=parse(pkg.parts[part])
  if root.tag not in (q('hdr'),q('ftr')) or root.xpath('.//w:bookmarkStart|.//w:bookmarkEnd|.//w:txbxContent|.//w:altChunk|.//w:sdt|.//w:ins|.//w:del',namespaces=NS):return pkg,[]
  matches=[r for r in rels if __import__('posixpath').normpath('word/'+r.get('Target',''))==part]
  if len(matches)!=1 or matches[0].get('Id') in active or matches[0].get('TargetMode')=='External':return pkg,[]
  remove.extend(matches)
 view=__import__('copy').copy(pkg);view.parts=dict(pkg.parts)
 for key in list(view.__dict__):
  if key.startswith('_internal_reference'):delattr(view,key)
 for r in remove:rels.remove(r)
 for e in list(ct):
  if e.get('PartName','').lstrip('/') in parts:ct.remove(e)
 view.parts['word/_rels/document.xml.rels']=E.tostring(rels);view.parts['[Content_Types].xml']=E.tostring(ct)
 return view,parts

def inventory(path):
 from .internal_refs import inventory as refs,resolve_target
 pkg=path if isinstance(path,Package) else Package(path);fs,broken=fields(pkg);ri=refs(pkg);refpkg,extra=reference_view(pkg,ri['issues']);rows=[]
 complex_tags={q(t) for t in ('ins','del','moveFrom','moveTo','drawing','pict','object','sdt','txbxContent','hyperlink')}
 for i,f in enumerate(fs):
  code=f['instruction'];kind=code.strip().split(' ',1)[0].upper();reason=None;target=None;levels=None
  if f['nested']:continue
  if kind not in ('TOC','REF','PAGEREF'):continue
  block=pkg.paragraphs[f['start']-1:f['end']]
  if broken:reason='主文档域边界断裂，不能安全计算'
  elif f['locked'] or kind=='TOC' and any(e.get(q('fldLock')) in ('1','true') for p in block for e in p.iter()):reason='域已锁定'
  elif any(e.tag in complex_tags-{q('hyperlink')} for p in block for e in p.iter()):reason='域所在段落含复杂结构'
  elif any(p.getparent()!=pkg.root.find(q('body')) or p.find('w:pPr/w:sectPr',NS) is not None for p in block):reason='非独立顶层或包含分节'
  if kind=='TOC':
   levels=toc_levels(code)
   if any(not re.match(r'^\s*(TOC|PAGEREF)\b',v,re.I) for p in block for v in p.xpath('.//w:instrText/text() | .//w:fldSimple/@w:instr',namespaces=NS)):reason=reason or '目录含未支持的嵌套域'
   if not levels:reason=reason or '仅支持明确\\o 1–3范围及h/z/u开关的目录'
   # TOC owns entire paragraphs; no unrelated visible text/objects outside field.
   if f['simple']:
    outside=[e for e in block[0] if e is not f['node'] and e.tag!=q('pPr')]
   else:outside=list(block[0])[1 if block[0].find(q('pPr')) is not None else 0:f['first']]+list(block[-1])[f['last']+1:]
   if any(text(e) or e.xpath('.//w:br|.//w:tab|.//w:bookmarkStart|.//w:bookmarkEnd',namespaces=NS) for e in outside):reason=reason or '目录边界外有其他内容'
  else:
   m=re.fullmatch(r'\s*(REF|PAGEREF)\s+([A-Za-z_][A-Za-z0-9_]{0,39})((?:\s+\\h|\s+\\\*\s+MERGEFORMAT)*)\s*',code,re.I)
   if not m:reason=reason or '不支持该引用指令/开关'
   else:
    target=m[2];r=resolve_target(refpkg,target)
    if r['state']!='pass':reason=reason or r['reason']
    else:
     try:target_plain(pkg,target)
     except DemoError as exc:reason=reason or str(exc)
   if f['start']!=f['end'] or (not f['simple'] and f['separate'] is None):reason=reason or '跨段/缺少分隔的引用'
   if any(e.tag==q('hyperlink') for p in block for e in p.iter()):reason=reason or '链接中的域仍受保护'
   if f['start']==f['end']:
    cache=list(f['node']) if f['simple'] else list(block[0])[f['separate'][1]+1:f['last']] if f.get('separate') else []
    if any(e.tag!=q('r') or any(x.tag not in (q('rPr'),q('t')) for x in e) for e in cache):reason=reason or '缓存含嵌套/非普通文字结构'
    styles={E.tostring(e.find(q('rPr'))) if e.find(q('rPr')) is not None else b'' for e in cache}
    if len(styles)>1:reason=reason or '缓存混合字符格式，不能安全重建文字结果'
  rows.append({'id':'field:'+str(i+1),'kind':kind,'instruction':code,'start':f['start'],'end':f['end'],'safe':reason is None,'reason':reason,'target':target,'levels':levels})
 # Surface excluded containers explicitly; they do not silently disappear.
 from .toc import parse_fields
 nested=[p for p in pkg.root.iter(q('p')) if p not in pkg.paragraphs]
 for j,f in enumerate(parse_fields(pkg,paragraphs=nested,detailed=True)[0],1):
  kind=f['instruction'].strip().split(' ',1)[0].upper()
  if kind in ('TOC','REF','PAGEREF'):rows.append({'id':'container:'+str(j),'kind':kind,'instruction':f['instruction'],'start':None,'end':None,'safe':False,'reason':'内容控件/表格/文本框中的域首版保持；需在Word中核对','target':None,'levels':None})
 return {'input_sha256':pkg.hash,'objects':rows,'limits':['只更新主文档顶层安全TOC与REF/PAGEREF；其他故事、嵌套或复杂域保持','目标存在不证明引用语义或目录正确；最终另行Word分页核对'],'story_issues':ri['issues'],'additional_target_free_orphan_proof':extra}

def plan(path,classification,selected=None,creation=None):
 from .classification import validate_classification
 pkg=Package(path);m=validate_classification(pkg,classification);inv=inventory(pkg);rows=inv['objects'];ids={r['id'] for r in rows if r['safe']};chosen=ids if selected is None else set(selected)
 if chosen-ids:raise DemoError('包含未通过安全校验或旧定位的域')
 selected_rows=[r for r in rows if r['id'] in chosen];kept=[r for r in rows if r['id'] not in chosen]
 for r in selected_rows:
  if r['kind']!='TOC' and (r['start'] in m.get('citation_scope',{}).get('scan',[]) or str(r['start']) in m.get('caption_scope',{}).get('captions',{})):raise DemoError('引用结果文字改变涉及活动引文/题注定位；须先重新核对该范围')
 # Equal code occurrences are all-or-none: Word is addressed by exact code, never text search.
 codes={clean_instruction(r['instruction']) for r in selected_rows}
 if any(clean_instruction(r['instruction']) in codes for r in kept):raise DemoError('同指令重复域须整组选择，避免Word索引歧义')
 if len(selected_rows)>200:raise DemoError('本次最多200个域')
 if creation:
  if set(creation)!={'start','end','levels','confirmed'} or creation['confirmed'] is not True or any(type(creation[k]) is not int for k in ('start','end')) or not 1<=creation['start']<=creation['end']<=len(pkg.paragraphs) or creation['levels'] not in ([1],[1,2],[1,2,3]):raise DemoError('目录创建位置/层级须明确确认')
  s=m.get('toc_scope',{});objects=s.get('objects',{});ps=nodes(pkg)
  for n in range(creation['start'],creation['end']+1):
   p=pkg.paragraphs[n-1];oid='d:'+str(ps.index(p)+1)
   if not s.get('confirmed') or objects.get(oid) not in ('level1','level2','level3','unknown') or any(e.tag not in {q(t) for t in ('p','pPr','pStyle','jc','spacing','ind','tabs','tab','r','rPr','rFonts','sz','szCs','b','i','t','color','u')} for e in p.iter()) or p.find('w:pPr/w:sectPr',NS) is not None:raise DemoError('只可替换已确认目录区域内的普通手工条目/空条目，标题保持')
  if any(r['start'] is not None and r['start']<=creation['end'] and r['end']>=creation['start'] for r in rows):raise DemoError('创建范围与已有域冲突')
 return {'version':VERSION,'input_sha256':pkg.hash,'classification_sha256':sha256(json.dumps(m,sort_keys=True).encode()),'selected':selected_rows,'kept':kept,'creation':deepcopy(creation)}

def run_text(value,rpr=None):
 r=E.Element(q('r'))
 if rpr is not None:r.append(deepcopy(rpr))
 t=E.SubElement(r,q('t'));t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=value;return r

def set_cache(pkg,f,value):
 p=pkg.paragraphs[f['start']-1]
 if f['simple']:
  e=f['node'];old=e.find('w:r/w:rPr',NS)
  for c in list(e):e.remove(c)
  e.append(run_text(value,old))
 else:
  n,j=f['separate'];cache=list(p)[j+1:f['last']];old=next((e.find(q('rPr')) for e in cache if e.tag==q('r')),None)
  for c in list(p)[j+1:f['last']]:p.remove(c)
  p.insert(j+1,run_text(value,old))

def page_format(pkg,n,number):
 from .front import section_inventory
 sections=section_inventory(pkg);s=next(x for x in sections if n in x['paragraphs']);fmt=s['page_numbering'].get('fmt','decimal')
 if fmt not in ('decimal','lowerRoman','upperRoman'):raise DemoError('目标页码格式超出可核对范围')
 if fmt=='decimal':return str(number)
 if not 1<=number<=3999:raise DemoError('罗马页码超出支持范围')
 out='';v=number
 for a,b in ((1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')):
  while v>=a:out+=b;v-=a
 return out.lower() if fmt=='lowerRoman' else out

def cache_text(pkg,f):
 if f['simple']:return text(f['node'])
 if not f.get('separate'):raise DemoError('计算结果缺少域分隔')
 a,j=f['separate'];ps=pkg.paragraphs;parts=[]
 for n in range(a,f['end']+1):
  p=ps[n-1];start=j+1 if n==a else 0;end=f['last'] if n==f['end'] else len(p)
  parts.extend(text(e) for e in list(p)[start:end])
 return ''.join(parts)

def target_plain(pkg,name):
 starts=pkg.root.xpath('.//w:bookmarkStart[@w:name=$n]',namespaces=NS,n=name)
 if len(starts)!=1:raise DemoError('目标书签不唯一')
 start=starts[0];p=start.getparent();end=p.find('w:bookmarkEnd[@w:id="'+start.get(q('id'))+'"]',NS)
 if p.tag!=q('p') or p not in pkg.paragraphs or end is None:raise DemoError('首版更新只支持同一顶层段落内的普通目标')
 inside=list(p)[p.index(start)+1:p.index(end)]
 if any(e.tag!=q('r') or any(c.tag not in (q('rPr'),q('t'),q('tab'),q('br')) for c in e) for e in inside):raise DemoError('目标包含复杂对象或其他域')
 from .formats import Resolver,Unresolved
 res=Resolver(pkg)
 try:
  if any(res.special(e,res.layers(p,e)) for e in inside):raise DemoError('引用目标含特殊/隐藏文字，不重建其普通可见缓存')
 except Unresolved:raise DemoError('引用目标字符继承无法确定') from None
 return ''.join(text(e) for e in inside),pkg.paragraphs.index(p)+1

def make_toc(instruction,heads,pages,templates):
 """Rebuild only cache rows. Stable anchors; original field instruction retained."""
 out=[]
 def control(typ):r=E.Element(q('r'));E.SubElement(r,q('fldChar')).set(q('fldCharType'),typ);return r
 for i,h in enumerate(heads):
  p=E.Element(q('p'));pr=templates.get(h['level'])
  if pr is not None:p.append(deepcopy(pr))
  if i==0:
   p.append(control('begin'));r=E.SubElement(p,q('r'));it=E.SubElement(r,q('instrText'));it.set('{http://www.w3.org/XML/1998/namespace}space','preserve');it.text=instruction;p.append(control('separate'))
  link=E.SubElement(p,q('hyperlink'));link.set(q('anchor'),h['anchor']);link.set(q('history'),'1');link.append(run_text(h['text']))
  r=E.SubElement(link,q('r'));E.SubElement(r,q('tab'))
  f=E.SubElement(link,q('fldSimple'));f.set(q('instr'),' PAGEREF '+h['anchor']+' \\h ');f.append(run_text(pages[h['anchor']]['display']))
  if i==len(heads)-1:p.append(control('end'))
  out.append(p)
 if not out:raise DemoError('目录指令未覆盖可验证标题；不发布空TOC')
 return out

def update(source,output,classification,transaction,*,calculator=None,artifact_dir=None):
 """Finite fixed point includes read-only Word measurement of the final backfill."""
 from .word_native import calculate
 calculator=calculator or calculate
 a=Package(source)
 if transaction!=plan(source,classification,[r['id'] for r in transaction['selected']],transaction['creation']):raise DemoError('目录/引用方案与当前输入不匹配')
 if a.signed or a.ambiguous_sections:raise DemoError('签名或分节归属异常，禁止更新')
 # Do not send potentially active external instructions to Word at all.
 for name,raw in a.parts.items():
  if name.startswith('word/') and name.endswith('.xml'):
   root=__import__('core.package',fromlist=['parse']).parse(raw)
   instructions=root.xpath('.//w:fldSimple/@w:instr',namespaces=NS)
   parsed=__import__('core.toc',fromlist=['parse_fields']).parse_fields(a,paragraphs=list(root.iter(q('p'))),detailed=True)[0]
   instructions += [f['instruction'] for f in parsed]
   if any(re.match(r'^\s*(?:DDEAUTO|DDE|INCLUDETEXT|INCLUDEPICTURE|LINK|DATABASE)\b',c,re.I) for c in instructions):raise DemoError('存在外部主动域，保持普通排版结果；本机计算器不打开此类文档')
 for name,raw in a.parts.items():
  if name.endswith('.rels'):
   rels=__import__('core.package',fromlist=['parse']).parse(raw)
   if any(r.get('TargetMode')=='External' and not r.get('Type','').endswith('/hyperlink') for r in rels):raise DemoError('存在外部模板/媒体依赖，未送入Word计算器')
 if not transaction['selected'] and not transaction['creation']:return None
 work=Path(artifact_dir or Path(output).parent);work.mkdir(parents=True,exist_ok=True)
 # Build immutable authorised blueprint on original XML objects.
 original=list(a.paragraphs);body=a.root.find(q('body'));fs,_=fields(a);byid={'field:'+str(i+1):f for i,f in enumerate(fs)}
 tocs=[];refs=[];targets={};anchor_specs=[];usedids=[int(e.get(q('id'))) for e in a.root.iter(q('bookmarkStart')) if e.get(q('id'),'').isdigit()];nextid=max(usedids,default=0)+1
 selected=transaction['selected'];allrows=inventory(a)['objects']
 for row in selected:
  f=byid[row['id']]
  if row['kind']=='TOC':tocs.append({'start':row['start'],'end':row['end'],'instruction':row['instruction'],'levels':row['levels'],'creation':False})
  else:
   value,n=target_plain(a,row['target']);targets[row['target']]=n;refs.append({**row,'original_target_text':value})
 if transaction['creation']:
  c=transaction['creation'];tocs.append({**c,'instruction':' TOC \\o "1-'+str(max(c['levels']))+'" \\h ','creation':True})
 if len(tocs)>4:raise DemoError('本次最多4份独立安全目录')
 for t in tocs:
  heads=[];templates={}
  for n,p in enumerate(original,1):
   level=paragraph_level(a,p,'\\u' in t['instruction'])
   if level not in t['levels']:continue
   if t['creation'] and classification['paragraph_types'].get(str(n))!='heading'+str(level):raise DemoError('新建目录覆盖的标题必须已有准确确认层级')
   if any(x['start']<=n<=x['end'] for x in tocs) or p.find('w:pPr/w:sectPr',NS) is not None or p.xpath('.//w:fldChar|.//w:fldSimple|.//w:drawing|.//w:ins|.//w:del|.//w:hyperlink|.//w:numPr',namespaces=NS):raise DemoError('目录覆盖标题含未解释编号/复杂结构')
   existing=[e for e in p.findall(q('bookmarkStart')) if e.get(q('name'),'').startswith('PFToc_') and p.find('w:bookmarkEnd[@w:id="'+e.get(q('id'),'')+'"]',NS) is not None]
   anchor=existing[0].get(q('name')) if len(existing)==1 else 'PFToc_'+a.hash[:12]+'_'+str(n)
   if not existing and any(e.get(q('name'))==anchor for e in a.root.iter(q('bookmarkStart'))):raise DemoError('新目标名称冲突')
   from .numbering import numbering_info
   if numbering_info(a,__import__('core.formats',fromlist=['Resolver']).Resolver(a),p).get('present'):raise DemoError('标题自动编号显示值未受支持，不猜测目录标题序号')
   heads.append({'paragraph':n,'level':level,'text':text(p),'anchor':anchor});targets[anchor]=n
  if not heads or len(heads)>200:raise DemoError('目录标题集合为空或超过200项')
  # Keep the original cache paragraph formatting where available; no new school defaults.
  for n in range(t['start'],t['end']+1):
   p=original[n-1];pr=p.find(q('pPr'));sid=pr.find(q('pStyle')) if pr is not None else None
   mm=re.fullmatch(r'(?:TOC|目录)\s*([1-3])',sid.get(q('val'),''),re.I) if sid is not None else None
   if pr is not None and pr.find(q('sectPr')) is None:templates.setdefault(int(mm[1]) if mm else 1,deepcopy(pr))
  for h in heads:
   if not any(e.get(q('name'))==h['anchor'] for e in a.root.iter(q('bookmarkStart'))) and h['anchor'] not in {s['name'] for s in anchor_specs}:anchor_specs.append({'name':h['anchor'],'id':str(nextid),'paragraph':h['paragraph']});nextid+=1
  t.update(heads=heads,templates=templates)
 # Original immutable skeleton is used on EVERY pass. Word package changes cannot leak in.
 from copy import deepcopy as cp
 root_bytes=E.tostring(a.root);root_original=cp(a.root)
 def build(pages,values):
  pkg=Package(source);ps=list(pkg.paragraphs);parent=pkg.root.find(q('body'));mapping={str(n):p for n,p in enumerate(ps,1)}
  for s in anchor_specs:
   p=ps[s['paragraph']-1];b=E.Element(q('bookmarkStart'));b.set(q('id'),s['id']);b.set(q('name'),s['name']);p.insert(1 if p.find(q('pPr')) is not None else 0,b);e=E.SubElement(p,q('bookmarkEnd'));e.set(q('id'),s['id'])
  # Descending cache edits retain child offsets for independent fields in the same paragraph.
  currentfields,_=fields(pkg);cm={'field:'+str(i+1):f for i,f in enumerate(currentfields)}
  for r in reversed(refs):set_cache(pkg,cm[r['id']],values.get(r['id'],cache_text(pkg,cm[r['id']])))
  created=[];retired=set()
  for t in reversed(tocs):
   old=ps[t['start']-1:t['end']];at=parent.index(old[0]);rows=make_toc(t['instruction'],t['heads'],pages,t['templates'])
   for p in old:parent.remove(p);retired.add(str(ps.index(p)+1))
   for p in reversed(rows):parent.insert(at,p)
   created.extend(rows)
  return pkg,mapping,retired,created
 pages={n:{'display':'0','adjusted':1,'physical':1} for n in targets};values={};previous=None;passes=[];final=None
 codes=[r['instruction'] for r in selected]+[t['instruction'] for t in tocs if t['creation']]
 for iteration in range(1,MAX_PASSES+1):
  candidate,_,_,_=build(pages,values);raw=candidate.bytes(True)
  # Locks are calculator-only. They NEVER enter the published package.
  calc=Package(source);calc.root=deepcopy(candidate.root)
  for e in calc.root.iter():
   if e.tag==q('fldSimple') or e.tag==q('fldChar') and e.get(q('fldCharType'))=='begin':e.set(q('fldLock'),'1')
  # fields() needs the current root's paragraphs, never the original ordinal cache.
  calc.paragraphs=calc.root.find(q('body')).findall(q('p'))
  for f in fields(calc)[0]:
   if f['instruction'] in codes:
    if f['simple']:f['node'].attrib.pop(q('fldLock'),None)
    else:
     for el in calc.paragraphs[f['start']-1][f['first']].iter(q('fldChar')):el.attrib.pop(q('fldLock'),None)
  for f in fields(calc)[0]:
   if f['instruction'] in codes and toc_levels(f['instruction']):
    for p in calc.paragraphs[f['start']-1:f['end']]:
     for e in p.iter():
      if e.tag in (q('fldSimple'),q('fldChar')):e.attrib.pop(q('fldLock'),None)
  receipt=calculator(calc.bytes(True),list(dict.fromkeys(codes)),list(targets),update=True)
  saved=write_new(work/('calculator-'+str(iteration)+'.docx'),receipt['raw']);computed=Package(saved);cfs,_=fields(computed)
  pages={n:{**r,'display':page_format(a,targets[n],r['adjusted'])} for n,r in receipt['pages'].items()}
  for r in refs:
   original_matches=[x for x in allrows if clean_instruction(x['instruction'])==clean_instruction(r['instruction'])];index=original_matches.index(r) if r in original_matches else [x['id'] for x in original_matches].index(r['id'])
   matches=[f for f in cfs if not f['nested'] and clean_instruction(f['instruction'])==clean_instruction(r['instruction'])]
   if len(matches)!=len(original_matches):raise DemoError('Word引用数量/身份无法可靠对应')
   value=cache_text(computed,matches[index]);expected=r['original_target_text'] if r['kind']=='REF' else pages[r['target']]['display']
   if value!=expected or re.search(r'Error!|错误[！!]|未定义书签',value,re.I):raise DemoError('Word域结果与目标/显示页码不符，拒绝更新：'+r['id'])
   values[r['id']]=value
  # Word's own generated TOC must cover exactly this instruction's actual heading set.
  for t in tocs:
   matches=[f for f in cfs if f['instruction'].strip()==t['instruction'].strip() and not f['nested']]
   if len(matches)!=1:raise DemoError('Word目录指令身份不唯一')
   f=matches[0];entries=[]
   for p in computed.paragraphs[f['start']-1:f['end']]:
    for link in p.findall(q('hyperlink')):
     anchor=link.get(q('anchor'));bm=computed.root.xpath('.//w:bookmarkStart[@w:name=$n]',namespaces=NS,n=anchor)
     if len(bm)!=1:raise DemoError('Word目录目标不唯一')
     targetp=bm[0].getparent();own=[h for h in t['heads'] if any(b.get(q('name'))==h['anchor'] for b in targetp.iter(q('bookmarkStart')))]
     if len(own)!=1:raise DemoError('Word目录目标不属于对应标题身份')
     tx=ordered_text(link);page=pages[own[0]['anchor']]['display']
     if tx!=own[0]['text']+'\t'+page:raise DemoError('Word目录文字或页码与目标不一致')
     entries.append(own[0]['anchor'])
   if entries!=[h['anchor'] for h in t['heads']]:raise DemoError('目录条目与指令覆盖集合不一致')
  built,mapping,retired,created=build(pages,values);newraw=built.bytes(True)
  observation=calculator(newraw,[],list(targets),update=False)
  stable=all(observation['pages'][n]==receipt['pages'][n] for n in targets)
  signature=json.dumps({'pages':pages,'values':values},sort_keys=True)
  passes.append({'pass':iteration,'seconds':receipt.get('seconds'),'readback_seconds':observation.get('seconds'),'final_target_pages_equal':stable})
  if stable and signature==previous:final=(built,mapping,retired,created,newraw);break
  previous=signature
 if final is None:raise DemoError('目录/页码在4遍内未稳定，未发布更新；普通排版结果保留')
 pkg,mapping,retired,created,raw=final
 # Exact object identity mapping for survivors; all new cache paragraphs stay "other".
 out=deepcopy(classification);newps=pkg.root.find(q('body')).findall(q('p'));pmap={k:str(newps.index(p)+1) for k,p in mapping.items() if k not in retired}
 protected=set(out.get('material_exclusions',{}))|{k[2:] for k in out.get('front_scope',{}).get('objects',{}) if k.startswith('p:')}|{str(n) for n in out.get('citation_scope',{}).get('scan',[])}|set(out.get('caption_scope',{}).get('captions',{}))|set(out.get('caption_scope',{}).get('chapter_map',{}))
 if retired&protected:raise DemoError('目录替换涉及活动保护/引文/封面/题注范围，不能可靠重绑')
 out['paragraph_types']={pmap[k]:v for k,v in out['paragraph_types'].items() if k not in retired};out['paragraph_types'].update({str(newps.index(p)+1):'other' for p in created})
 if out.get('material_exclusions'):out['material_exclusions']={pmap[k]:v for k,v in out['material_exclusions'].items()}
 for scope in ('citation_scope','caption_scope','front_scope','toc_scope'):
  if scope not in out:continue
  s=out[scope]
  if scope=='citation_scope':
   s['scan']=[int(pmap[str(n)]) for n in s['scan']];s['objects']={':'.join([k.split(':')[0],pmap[k.split(':')[1]],*k.split(':')[2:]]):v for k,v in s['objects'].items()}
  if scope=='front_scope':s['objects']={('p:'+pmap[k[2:]] if k.startswith('p:') else k):v for k,v in s['objects'].items()}
  if scope=='caption_scope':
   for key in ('captions','chapter_map'):s[key]={pmap[k]:v for k,v in s[key].items()}
   s['associations']={pmap[k]:('image:p:'+pmap[v[8:]] if v.startswith('image:p:') else v) for k,v in s['associations'].items()}
  if scope=='toc_scope':
   oldnodes=nodes(a);newnodes=nodes(pkg);survivor={p:i for i,p in mapping.items() if i not in retired};dm={'d:'+str(i):'d:'+str(newnodes.index(mapping[str(a.paragraphs.index(p)+1)])+1) for i,p in enumerate(oldnodes,1) if p in a.paragraphs and str(a.paragraphs.index(p)+1) in pmap}
   if any(k not in dm and oldnodes[int(k[2:])-1] not in a.paragraphs for k in s['objects']):raise DemoError('目录SDT活动定位无法重绑')
   s['objects']={dm[k]:v for k,v in s['objects'].items() if k in dm};s['complete']=False;s['headings_complete']=False
 from .table_text import rebind
 h=sha256(raw);out['input_sha256']=h;rebind(out,h)
 write_new(output,raw,source)
 from .classification import validate_classification
 validate_classification(Package(output),out)
 proof={'input_sha256':a.hash,'output_sha256':h,'unselected_parts_byte_equal':True,'original_object_relative_order':True,'paragraph_map':pmap,'retired_TOC_paragraphs':sorted(retired),'new_TOC_paragraphs':[newps.index(p)+1 for p in created],'added_bookmarks':anchor_specs,'selected_fields':[r['id'] for r in selected],'passes':passes,'target_pages':pages,'cache_values':values,'kept':transaction['kept'],'calculator_package_published':False}
 # Independent reverse-mask: remove only exact new bookmark pairs and restore precisely authorised cache blocks/results.
 check=deepcopy(pkg.root);cps=check.find(q('body')).findall(q('p'));cb=check.find(q('body'))
 for s in anchor_specs:
  for e in check.xpath('.//w:bookmarkStart[@w:name=$n]',namespaces=NS,n=s['name']):
   ident=e.get(q('id'));e.getparent().remove(e)
   ends=check.xpath('.//w:bookmarkEnd[@w:id=$i]',namespaces=NS,i=ident)
   if len(ends)!=1:raise DemoError('新增书签反向校验失败')
   ends[0].getparent().remove(ends[0])
 # Survivor subtrees (after authorised reference caches) are compared to this explicit blueprint.
 expected=deepcopy(root_original);ep=expected.find(q('body')).findall(q('p'))
 for r in reversed(refs):
  fake=Package(source);fake.root=expected;fake.paragraphs=ep;ff={ 'field:'+str(i+1):f for i,f in enumerate(fields(fake)[0])};set_cache(fake,ff[r['id']],values[r['id']])
 surviving=[e for e in expected.find(q('body')) if e not in [p for i,p in enumerate(ep,1) if str(i) in retired]]
 actual=[e for e in cb if e not in [p for i,p in enumerate(cps,1) if i in proof['new_TOC_paragraphs']]]
 if dict(check.attrib)!=dict(root_original.attrib):raise DemoError('主文档根属性发生非授权变化')
 if len(actual)!=len(surviving) or any(canon(x)!=canon(y) for x,y in zip(actual,surviving)):raise DemoError('回填改变未授权段落/格式')
 if any(a.parts[n]!=Package(output).parts[n] for n in a.parts if n!='word/document.xml'):raise DemoError('回填改变其他ZIP部件')
 return {'output':str(output),'classification':out,'proof':proof,'changes':[{'rule_id':'R44' if r['kind']!='TOC' else 'R30','locator':{'paragraph':r['start']},'property':'field_cache','before':'旧保存结果','after':r['kind']+'已更新','verification':'pass','source':SOURCE} for r in selected]+([{'rule_id':'R30','locator':{'paragraph':transaction['creation']['start']},'property':'toc_creation','before':'已确认普通手工条目','after':'自动目录','verification':'pass','source':SOURCE}] if transaction['creation'] else [])}

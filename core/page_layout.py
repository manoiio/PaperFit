"""Exact structural transaction: safe sectPr boundaries and isolated PAGE footers.
No field evaluation, physical page guessing, shared-story writes or new paragraphs.
"""
from copy import deepcopy
from pathlib import Path
import re,posixpath,json
from lxml import etree as E
from .package import Package,DemoError,q,NS,parse,sha256,write_new
from .front import section_inventory,fields,R,REL
from .classification import validate_classification
from .table_text import rebind
from .page_policy import validate as policy_validate
VERSION='section-pages-2'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
SOURCE={'label':'用户明确选择的页码/章节页脚方案','quote':'可选产品结构处理，不是学校默认要求；PAGE域存在不代表目录或引用页码已刷新。'}
def digest(d):return sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode())
def canon(e):return E.tostring(e,method='c14n')
def text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=NS))
def safe_boundary(pkg,start):
 if type(start) is not int or not 1<=start<=len(pkg.paragraphs):raise DemoError('分区起点不是有效主文档段落')
 if start==1:return
 prev=pkg.paragraphs[start-2];p=pkg.paragraphs[start-1];body=list(pkg.root.find(q('body')))
 if body.index(p)!=body.index(prev)+1:raise DemoError('分节边界跨表格或未知容器，不能自动拆分')
 for node in (prev,p):
  from .formats import paragraph_unsafe
  if paragraph_unsafe(node):raise DemoError('分节边界含格式修订、浮动框架、字段或未支持结构')
  bookmarks=node.xpath('.//w:bookmarkStart|.//w:bookmarkEnd',namespaces=NS)
  if bookmarks:
   from .word_fields import paragraph_level
   from .numbering import heading_numbering
   ni=heading_numbering(pkg,node)
   if not paragraph_level(pkg,node,True) or ni.get('present') and ni.get('status')!='resolved':raise DemoError('分节边界书签不属于可证明标题')
   for bm in bookmarks:
    ident=bm.get(q('id'));starts=pkg.root.xpath('.//w:bookmarkStart[@w:id=$i]',namespaces=NS,i=ident);ends=pkg.root.xpath('.//w:bookmarkEnd[@w:id=$i]',namespaces=NS,i=ident)
    if len(starts)!=1 or len(ends)!=1 or starts[0].getparent() is not node or ends[0].getparent() is not node or node.index(starts[0])>=node.index(ends[0]) or not re.fullmatch(r'_Toc[0-9]{1,20}|PFToc_[a-f0-9]{12}_[0-9]{1,6}',starts[0].get(q('name'),'')):raise DemoError('分节边界书签不唯一、跨段或不是普通目录目标')
  if node.xpath('.//w:sectPrChange|.//w:rPrChange|.//w:ins|.//w:del|.//w:sdt|.//w:fldChar|.//w:fldSimple|.//w:hyperlink|.//w:drawing|.//w:pict|.//w:object',namespaces=NS):raise DemoError('分节边界包含复杂对象、书签或字段')
  if any(c.tag not in (q('pPr'),q('r'),q('bookmarkStart'),q('bookmarkEnd')) for c in node):raise DemoError('分节边界结构不明确')
  if len(node.findall(q('pPr')))>1:raise DemoError('重复段落属性')
 # A page break isolated in an otherwise empty preceding paragraph can leave an extra page.
 if not text(prev).strip() and prev.xpath('.//w:br[@w:type="page"]',namespaces=NS):raise DemoError('边界前有独立分页空段，请先核对，不能悄悄删段')
def regions_validate(pkg,regions):
 if type(regions) is not list or not 1<=len(regions)<=60:raise DemoError('分区数须1–60')
 starts=[]
 for r in regions:
  if type(r) is not dict or set(r)!= {'start','role','format','restart','footer','text','alignment'}:raise DemoError('分区字段不完整或未知')
  safe_boundary(pkg,r['start']);starts.append(r['start'])
  if r['role'] not in ('cover','front','body','keep') or r['format'] not in ('decimal','lowerRoman','upperRoman','keep') or r['footer'] not in ('page','chapter','text') or r['alignment'] not in ('center','right'):raise DemoError('分区模式不支持')
  if r['restart'] is not None and (type(r['restart']) is not int or not 1<=r['restart']<=9999):raise DemoError('页码起始值无效')
  if type(r['text']) is not str or len(r['text'])>100 or any(ord(c)<32 for c in r['text']):raise DemoError('页脚文字无效')
 if starts!=sorted(set(starts)) or starts[0]!=1:raise DemoError('分区须从首段开始且起点严格递增')
 return deepcopy(regions)
def automatic(pkg,m,policy,*,front_start=None,body_start=None,cover=True):
 policy=policy_validate(policy);types=m['paragraph_types'];heads=[int(n) for n,t in types.items() if t=='heading1']
 if body_start is None:body_start=min(heads) if heads else None
 if body_start is None:raise DemoError('无法确定正文起点，请在本页核对')
 if front_start is None:
  xs=[int(n) for n,t in types.items() if t in ('abstract_cn_title','abstract_en_title','abstract_cn_body','abstract_en_body') and int(n)<body_start];front_start=min(xs) if xs else body_start
 if type(front_start) is not int or type(body_start) is not int or not 1<=front_start<=body_start<=len(pkg.paragraphs):raise DemoError('前置起点须不晚于正文起点，请核对两处位置')
 if policy['pages']=='chapter-footers':front_start=1
 starts={1:'cover' if cover and front_start>1 else 'keep' if front_start>1 else 'front' if body_start>1 else 'body',front_start:'front' if front_start<body_start else 'body',body_start:'body'}
 if policy['pages']=='chapter-footers' and body_start>1:starts[1]='keep'
 if policy['footer']=='chapter' or policy['chapter_restart']:
  for n in heads:
   if n>=body_start:starts[n]='body'
 out=[];first_body=True
 for n,role in sorted(starts.items()):
  title=text(pkg.paragraphs[max((h for h in heads if h<=n),default=n)-1]).strip() if role=='body' else ''
  if policy['footer']=='chapter' and role=='body' and types.get(str(n))!='heading1':raise DemoError('章节页脚须定位到已确认一级标题')
  out.append({'start':n,'role':role,'format':'keep' if policy['pages']=='chapter-footers' else policy['roman'] if role=='front' else 'decimal','restart':None if policy['pages']=='chapter-footers' else policy['front_start'] if role=='front' else policy['body_start'] if role=='body' and (first_body or policy['chapter_restart']) else None,'footer':policy['footer'] if role=='body' else 'page','text':title if policy['footer']=='chapter' and role=='body' else policy['text'],'alignment':policy['alignment']})
  if role=='body':first_body=False
 return regions_validate(pkg,out)
def _ensure(p,tag):
 e=p.find(q(tag))
 if e is None:e=E.Element(q(tag));p.insert(0,e) if tag=='pPr' else p.append(e)
 return e
ORDER=['headerReference','footerReference','footnotePr','endnotePr','type','pgSz','pgMar','paperSrc','pgBorders','lnNumType','pgNumType','cols','formProt','vAlign','noEndnote','titlePg','textDirection','bidi','rtlGutter','docGrid','printerSettings','sectPrChange']
def put(s,e):
 tag=E.QName(e).localname;idx=ORDER.index(tag)
 for i,c in enumerate(s):
  if E.QName(c).localname in ORDER and ORDER.index(E.QName(c).localname)>idx:s.insert(i,e);return
 s.append(e)
def _footer(pkg,part,region):
 root=parse(pkg.parts[part]) if part else E.Element(q('ftr'),nsmap={'w':NS['w']});hits=fields(root)
 if any(not f['balanced'] for f in hits) or any(f['is_page'] and (f['representation']!='simple' or not re.fullmatch(r'\s*PAGE\s*(?:\\\*\s*MERGEFORMAT\s*)?',f['instruction'],re.I)) for f in hits):raise DemoError('复杂/嵌套PAGE或断裂字段，不能安全替换')
 pages=[e for e in root.iter(q('fldSimple')) if re.match(r'^\s*PAGE(?:\s|$)',e.get(q('instr'),''),re.I)]
 if len(pages)>1:raise DemoError('同一页脚存在多个PAGE，不能叠加/猜测')
 if root.xpath('.//w:ins|.//w:del|.//w:sdt|.//w:altChunk|.//w:pPrChange|.//w:rPrChange|.//w:framePr',namespaces=NS):raise DemoError('页脚有修订/内容控件，禁止自动修改')
 if root.xpath('.//w:bookmarkStart|.//w:bookmarkEnd|.//w:drawing|.//w:pict|.//w:object|.//w:tbl',namespaces=NS):raise DemoError('页脚含图形、书签或表格，尚不能证明克隆安全；原内容保持，不自动处理')
 if pages:
  f=pages[0];p=f.getparent()
  if p.tag!=q('p') or any(c is not f and c.tag!=q('pPr') for c in p):raise DemoError('既有PAGE与其他文字/对象混在同段，须人工核对')
  # Reuse an existing dedicated page line; other paragraphs stay byte-equivalent.
  p.remove(f)
 else:
  # Do not hijack an unrelated empty paragraph's formatting.
  p=E.SubElement(root,q('p'))
 if region['role']=='cover':
  if pages and len(p)==0:root.remove(p)
  elif not pages:root.remove(p)
  if not len(root):E.SubElement(root,q('p'))
  return root
 pp=_ensure(p,'pPr');jc=_ensure(pp,'jc');jc.set(q('val'),region['alignment'])
 if region['footer']!='page' and region['text']:
  r=E.SubElement(p,q('r'));t=E.SubElement(r,q('t'));t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=region['text']+'  '
 f=E.SubElement(p,q('fldSimple'));f.set(q('instr'),' PAGE ')
 # No fabricated cached page number or updateFields flag.
 E.SubElement(f,q('r'))
 return root

def build(pkg,regions):
 if pkg.signed or pkg.ambiguous_sections:raise DemoError('签名或不明确分节不可修改')
 regions=regions_validate(pkg,regions);root=deepcopy(pkg.root);ps=root.find(q('body')).findall(q('p'));body=root.find(q('body'))
 if len(body.findall(q('sectPr')))!=1 or body[-1].tag!=q('sectPr'):raise DemoError('末节属性缺失或不在主文档末尾')
 inventory=section_inventory(pkg)
 if any(s['errors'] or s['odd_even_different'] is None or s['body_objects'] is None or s['body_objects']['start']>s['body_objects']['end'] for s in inventory):raise DemoError('已有页眉页脚关系或节属性异常')
 for s in pkg.sections:
  if any(len(s.findall(q(tag)))>1 for tag in ('type','pgSz','cols','footnotePr','endnotePr')):raise DemoError('重复节属性，不能安全解释')
 rels=parse(pkg.parts.get('word/_rels/document.xml.rels',b'<Relationships xmlns="'+REL.encode()+b'"/>'));ct=parse(pkg.parts['[Content_Types].xml']);added={};records=[];section_map={}
 # Materialize inherited header/footer references at original section boundaries:
 # later keep-regions must not accidentally inherit our newly introduced footer.
 originals=[]
 for s,inv in zip(pkg.sections,inventory):
  owner=s.getparent().getparent() if s.getparent().tag!=q('body') else None
  originals.append((pkg.paragraphs.index(owner)+1 if owner is not None else len(ps),deepcopy(s),inv))
 old_starts={1,*[end+1 for end,_,_ in originals[:-1]]}  # Paragraph identity, never body-object counts (tables differ).
 for r in regions[1:]:
  n=r['start'];prev=ps[n-2];pp=_ensure(prev,'pPr')
  if pp.find(q('sectPr')) is not None:continue
  original=next((s for end,s,inv in originals if end>=n-1),None)
  if original is not None and original.xpath('./w:footnotePr/w:numRestart[@w:val="eachSect"]|./w:endnotePr/w:numRestart[@w:val="eachSect"]|./w:footnotePr/w:numStart|./w:endnotePr/w:numStart',namespaces=NS):raise DemoError('新增节可能改变注释编号重启设置，禁止自动分节')
  settings=parse(pkg.parts['word/settings.xml']) if 'word/settings.xml' in pkg.parts else E.Element(q('settings'))
  if settings.xpath('./w:footnotePr/w:numRestart[@w:val="eachSect"]|./w:endnotePr/w:numRestart[@w:val="eachSect"]',namespaces=NS) or original.find(q('lnNumType')) is not None:raise DemoError('新增分节可能影响已有注释/行编号，禁止自动处理')
  if original is None:raise DemoError('分节归属无法确定')
  s=deepcopy(original);put(s,E.Element(q('type'),{q('val'):'nextPage'})) if s.find(q('type')) is None else s.find(q('type')).set(q('val'),'nextPage');pp.append(s)
  # New next-page section replaces only an explicit pageBreakBefore at the same start.
  pbf=ps[n-1].find('w:pPr/w:pageBreakBefore',NS)
  if pbf is not None: pbf.getparent().remove(pbf)
  # Explicit run page breaks at this boundary are ambiguous, not silently removed.
  if prev.xpath('.//w:br[@w:type="page"]',namespaces=NS) or ps[n-1].xpath('./w:r/w:br[@w:type="page"]',namespaces=NS):raise DemoError('边界有显式分页run，需核对以免多出空白页')
  records.append({'kind':'new_section','start':n})
 ends=[]
 for p in ps:
  s=p.find('w:pPr/w:sectPr',NS)
  if s is not None:ends.append((ps.index(p)+1,s))
 ends.append((len(ps),body.find(q('sectPr'))));start=1
 for si,(end,s) in enumerate(ends,1):
  r=next(r for r in reversed(regions) if r['start']<=start);orig=next(inv for e,os,inv in originals if e>=end)
  old_section=canon(s)
  if start>1 and any(x['start']==start for x in regions) and start not in old_starts:
   typ=s.find(q('type'))
   if typ is None:put(s,E.Element(q('type'),{q('val'):'nextPage'}))
   else:typ.set(q('val'),'nextPage')
  # Resolve originally active stories before changing ANY reference.
  for key,info in orig['references'].items():
   kind,variant=key.split(':')
   if kind=='footer' and info.get('part') and not any(x.get(q('type'))==variant for x in s.findall(q(kind+'Reference'))):
    source_section=originals[info['defined_section']-1][1];ref=next(x for x in source_section.findall(q(kind+'Reference')) if x.get(q('type'))==variant);put(s,deepcopy(ref))
  if r['role']=='keep':
   if canon(s)!=old_section:records.append({'kind':'preserve_inheritance','section':si})
   start=end+1;continue
  # A header PAGE would duplicate visible numbering. Preserve and refuse, never delete header graphics.
  for variant in ('default','first','even'):
   if any(f['is_page'] for f in orig['references']['header:'+variant].get('fields',[])):raise DemoError('页眉含PAGE，需先决定保留位置，不能额外叠加页脚页码')
  pg=s.findall(q('pgNumType'))
  if len(pg)>1:raise DemoError('重复页码设置')
  if r['role']!='cover' and r['format']!='keep':
   if pg and any(pg[0].get(q(x)) is not None for x in ('chapStyle','chapSep')):raise DemoError('已有页码包含章节前缀，不能默默覆盖其语义')
   e=pg[0] if pg else E.Element(q('pgNumType'))
   if not pg:put(s,e)
   e.set(q('fmt'),r['format']);e.attrib.pop(q('start'),None)
   # Restart only at explicitly selected region start; subsequent original sections continue.
   if start==r['start'] and r['restart'] is not None:e.set(q('start'),str(r['restart']))
  if r['format']=='keep' and pg and start not in old_starts:pg[0].attrib.pop(q('start'),None)
  variants=['default']+(['first'] if orig['first_page_different'] else [])+(['even'] if orig['odd_even_different'] else [])
  for variant in variants:
   part=orig['references']['footer:'+variant].get('part')
   if part and [e.get('ContentType') for e in ct if e.get('PartName')=='/'+part]!=['application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml']:raise DemoError('页脚内容类型缺失或重复，不能克隆')
   if part and _footer_idempotent(pkg,part,r):continue
   fr=_footer(pkg,part,r)
   if part and canon(fr)==canon(parse(pkg.parts[part])):continue
   existing=s.findall(q('footerReference'));ref=next((e for e in existing if e.get(q('type'))==variant),None)
   # Idempotence: a previously generated isolated footer already matches the desired line.
   if part:
    desired=_footer_idempotent(pkg,part,r)
    if desired:continue
   idx=1
   while f'word/footerPF{idx}.xml' in pkg.parts or f'word/footerPF{idx}.xml' in added:idx+=1
   target=f'word/footerPF{idx}.xml'
   while any(e.get('PartName')=='/'+target for e in ct):
    idx+=1;target=f'word/footerPF{idx}.xml'
    while target in pkg.parts or target in added:idx+=1;target=f'word/footerPF{idx}.xml'
   rid='rIdPF'+str(idx)
   while any(e.get('Id')==rid for e in rels):idx+=1;rid='rIdPF'+str(idx)
   if ref is not None:s.remove(ref)
   put(s,E.Element(q('footerReference'),{q('type'):variant,'{'+R+'}id':rid}))
   E.SubElement(rels,'{'+REL+'}Relationship',Id=rid,Type=R+'/footer',Target=target.removeprefix('word/'))
   E.SubElement(ct,'{'+CT+'}Override',PartName='/'+target,ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml')
   added[target]=E.tostring(fr,xml_declaration=True,encoding='UTF-8',standalone=True)
   # Footer-local relationships must be cloned for retained images/hyperlinks.
   oldrel='word/_rels/'+posixpath.basename(part)+'.rels' if part else None
   if oldrel and oldrel in pkg.parts:added['word/_rels/'+posixpath.basename(target)+'.rels']=pkg.parts[oldrel]
   if sum(len(v) for v in added.values())>10*1024*1024:raise DemoError('克隆页脚超过10MB附加部件预算，请缩小处理范围')
   records.append({'kind':'footer','section':si,'variant':variant,'old_part':part,'new_part':target,'role':r['role'],'format':r['format'],'restart':r['restart'] if start==r['start'] else None,'text':r['text'],'alignment':r['alignment']})
  if canon(s)!=old_section and not any(x.get('section')==si for x in records):records.append({'kind':'section_numbering','section':si,'format':r['format'],'restart':r['restart'] if start==r['start'] else None})
  section_map[str(si)]={'start':start,'end':end,'role':r['role']};start=end+1
 replacements={'word/document.xml':E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True),'word/_rels/document.xml.rels':E.tostring(rels,xml_declaration=True,encoding='UTF-8',standalone=True),'[Content_Types].xml':E.tostring(ct,xml_declaration=True,encoding='UTF-8',standalone=True)}
 # Keep original bytes when semantically unchanged; no gratuitous serialization.
 replacements={k:v for k,v in replacements.items() if k not in pkg.parts or canon(parse(v))!=canon(parse(pkg.parts[k]))}
 return replacements,added,records,section_map

def _footer_idempotent(pkg,part,r):
 root=parse(pkg.parts[part]);pages=[e for e in root.iter(q('fldSimple')) if re.match(r'^\s*PAGE(?:\s|$)',e.get(q('instr'),''),re.I)]
 if r['role']=='cover':return not any(f['is_page'] for f in fields(root))
 if len(pages)!=1 or pages[0].get(q('instr'),'').strip()!='PAGE':return False
 p=pages[0].getparent()
 if p.tag!=q('p') or p.find('w:pPr/w:jc',NS) is None or p.find('w:pPr/w:jc',NS).get(q('val'))!=r['alignment']:return False
 return text(p)==(r['text']+'  ' if r['footer']!='page' and r['text'] else '') and all(c.tag in (q('pPr'),q('r'),q('fldSimple')) for c in p)

def propose(path,m,policy,regions):
 pkg=Package(path);validate_classification(pkg,m);policy_validate(policy);regions=regions_validate(pkg,regions)
 heads=[int(n) for n,t in m['paragraph_types'].items() if t=='heading1']
 for r in regions:
  if r['role']=='body' and r['footer']=='chapter':
   candidates=[n for n in heads if n<=r['start']]
   if not candidates or r['text']!=text(pkg.paragraphs[max(candidates)-1]).strip():raise DemoError('章节页脚文字须来自当前已确认标题，不接受编造名称')
 replacement,added,records,mapping=build(pkg,regions)
 p={'version':VERSION,'input_sha256':pkg.hash,'classification_sha256':digest(m),'policy':policy,'regions':regions,'replacements':{k:sha256(v) for k,v in replacement.items()},'added':{k:sha256(v) for k,v in added.items()},'records':records,'section_map':mapping};p['seal']=digest(p);return p

def validate_output(source,output,m,plan):
 a=Package(source);b=Package(output)
 if plan!=propose(source,m,plan['policy'],plan['regions']):raise DemoError('分节页码计划绑定已失效')
 replacement,added,_,_=build(a,plan['regions']);expected={**a.parts,**replacement,**added}
 if expected!=b.parts:raise DemoError('结构事务出现计划外部件或字节变化')
 return {'input_sha256':a.hash,'output_sha256':b.hash,'new_parts':sorted(added),'changed_parts':sorted(replacement),'only_authorized_structure':True,'main_object_order_preserved':True,'physical_pages_not_computed':True}

def rehearse(source,output,m,plan,**rules_args):
 from . import check_document
 a=Package(source)
 if plan!=propose(source,m,plan['policy'],plan['regions']):raise DemoError('页码计划变化')
 before=check_document(source,mode='academic',classification_manifest=m,**rules_args);replacement,added,_,_=build(a,plan['regions']);raw=a.structure_bytes(replacement,added);write_new(output,raw,source)
 try:
  proof=validate_output(source,output,m,plan);b=Package(output);out=deepcopy(m);out['input_sha256']=b.hash;rebind(out,b.hash)
  if out.get('front_scope'):
   old=section_inventory(a);new=section_inventory(b);roles=out['front_scope']['section_roles'];out['front_scope']['section_roles']={str(s['index']):(plan['section_map'].get(str(s['index']),{}).get('role') if plan['section_map'].get(str(s['index']),{}).get('role') in ('cover','front','body') else roles[str(next(x['index'] for x in old if x['body_objects']['start']<=s['body_objects']['start']<=x['body_objects']['end']))]) for s in new}
  validate_classification(b,out);after=check_document(output,mode='academic',classification_manifest=out,**rules_args)
  if before['rules']['sha256']!=after['rules']['sha256'] or sha256(Path(source).read_bytes())!=a.hash:raise DemoError('页码事务期间输入或规则变化')
  changes=[{'rule_id':'R29','key':'pages:'+str(i),'locator':{'section':r.get('section',1)},'property':'section_pages','before':r.get('old_part'),'after':r,'verification':'pass','source':SOURCE} for i,r in enumerate(plan['records'],1)]
  return {'kind':'section_pages','output':str(output),'before':before,'after':after,'changes':changes,'skipped_review_keys':[],'input_classification_manifest':m,'output_classification_manifest':out,'output_body_manifest':{'input_sha256':b.hash,'body_paragraphs':after['coverage']['body_paragraphs'],'confirmation':'同一对象身份，结构事务后重新校验'},'preservation':proof,'page_layout':{'plan':plan,'validation':proof},'problem_delta':__import__('core.dependencies',fromlist=['problem_delta']).problem_delta(before,after)}
 except Exception:Path(output).unlink(missing_ok=True);raise

"""Opt-in R30-R32 manual TOC format + read-only cached correspondence.
New d:N IDs enumerate body/SDT paragraph objects only, never change legacy p:N.
"""
from copy import deepcopy
import re
from lxml import etree as E
from .package import Package,DemoError,q,NS
from .formats import Resolver,Unresolved,paragraph_unsafe,scripts,same_font
from .paragraph_properties import alignment
from .toc_template import school,validate as validate_template,digest,QUOTE
IDS={'R30','R31','R32'}
ROLES={'title':'目录标题','level1':'一级条目','level2':'二级条目','level3':'三级条目','unknown':'条目级别待确认'}
LIMITS=['只覆盖人工确认的目录对象；旧顶层段落编号保持不变，表格/文本框中的目录不自动修正。','自动目录缓存只读：不改域、链接、书签、PAGEREF、dirty/locked或全局更新设置。','保存页码不是实际页码；修改可能改变分页，目录页码尚未核对，需在Word人工更新后作为新输入检查。','物理页18明确条文作为属性依据；页24范例的点线、缩进、制表位、字间空格、西文字体与段距未增加为校规。']
def text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=NS))
def nodes(pkg):
 # Include ordinary and SDT paragraphs, but never table cells or textboxes.
 return [p for p in pkg.root.find(q('body')).iter(q('p')) if not any(a.tag in (q('tc'),q('txbxContent')) for a in p.iterancestors())]
def ordered_text(p):
 return ''.join((e.text or '') if e.tag==q('t') else '\t' if e.tag==q('tab') else '' for e in p.iter())
def parse_fields(pkg, *, paragraphs=None, detailed=False):
 """Field stack across paragraphs; nested saved result contributes to enclosing TOC."""
 ps=nodes(pkg) if paragraphs is None else paragraphs;pids={id(p):'d:'+str(i) for i,p in enumerate(ps,1)};stack=[];out=[];broken=[]
 for p in ps:
  pid=pids[id(p)]
  for f in stack:
   if pid not in f['objects']:f['objects'].append(pid)
  for e in p.iter():
   if e.tag==q('fldSimple'):
    instr=e.get(q('instr'),'');out.append({'instruction':instr,'result':ordered_text(e),'objects':[pid],'balanced':True,'representation':'simple',**({'nested':bool(e.xpath('.//w:fldChar|.//w:fldSimple',namespaces=NS)), 'reliable':not bool(e.xpath('.//w:fldChar|.//w:fldSimple',namespaces=NS))} if detailed else {})})
   elif e.tag==q('fldChar'):
    typ=e.get(q('fldCharType'))
    if typ=='begin':
     if detailed and stack and stack[-1]['phase']=='instruction':stack[-1]['reliable']=False
     stack.append({'instruction':'','result':'','objects':[pid],'balanced':True,'representation':'complex','phase':'instruction',**({'nested':bool(stack),'reliable':not any(a.tag==q('fldSimple') for a in e.iterancestors()),'separated':False} if detailed else {})})
    elif typ=='separate':
     if not stack or stack[-1]['phase']!='instruction':broken.append(pid)
     else:
      stack[-1]['phase']='result'
      if detailed:stack[-1]['separated']=True
    elif typ=='end':
     if not stack:broken.append(pid)
     else:
      f=stack.pop();f.pop('phase');out.append(f)
    else:broken.append(pid)
   elif e.tag==q('instrText'):
    if stack and stack[-1]['phase']=='instruction':stack[-1]['instruction']+=e.text or ''
    else:broken.append(pid)
   elif e.tag in (q('t'),q('tab')):
    for f in stack:
     if f['phase']=='result':f['result']+=(e.text or '') if e.tag==q('t') else '\t'
   for f in stack:
    if pid not in f['objects']:f['objects'].append(pid)
 for f in stack:
  f.pop('phase');f['balanced']=False;out.append(f);broken.extend(f['objects'])
 if detailed:
  for f in out:
   if set(f['objects']) & set(broken):f['reliable']=False
 return out,sorted(set(broken))
def inventory(path):
 pkg=path if isinstance(path,Package) else Package(path);res=Resolver(pkg);fields,broken=parse_fields(pkg)
 toc=[f for f in fields if re.match(r'^\s*TOC(?:\s|$)',f['instruction'],re.I)];auto={o for f in toc for o in f['objects']};top={id(p):i for i,p in enumerate(pkg.paragraphs,1)};rows=[]
 for i,p in enumerate(nodes(pkg),1):
  pid='d:'+str(i);tx=ordered_text(p);style=p.find('w:pPr/w:pStyle',NS);sid=style.get(q('val')) if style is not None else '';sdt=any(a.tag==q('sdt') for a in p.iterancestors());hint=None;reasons=[]
  if re.fullmatch(r'\s*目\s*录\s*',tx):hint='title';reasons.append('文字为目录标题候选，仍需确认')
  m=re.fullmatch(r'(?:TOC|目录)\s*([1-3])',sid,re.I)
  if m:hint='level'+m[1];reasons.append('TOC类样式线索，未证明层级')
  if pid in auto:reasons.append('位于TOC域保存结果/边界，首版只读')
  if '\t' in tx and re.search(r'\t(?:\d+|[IVXLCDMivxlcdm]+)\s*$',tx):
   reasons.append('制表符及末尾页码候选，不自动确认');hint=hint or 'unknown'
  if pid in broken:reasons.append('孤立/断裂域边界，待复核')
  special=paragraph_unsafe(p)
  if any(a.tag not in (q('body'),q('document'),q('sdtContent'),q('sdt')) for a in p.iterancestors()):special='修订或未知包装结构，不能安全修改'
  if any(a.tag==q('sdt') and a.find('w:sdtPr/w:dataBinding',NS) is not None or a.tag==q('sdt') and a.find('w:sdtPr/w:lock',NS) is not None for a in p.iterancestors()):special='绑定或锁定内容控件，不改缓存或普通文字'
  rows.append({'id':pid,'locator':{'toc_object':i,**({'paragraph':top[id(p)]} if id(p) in top else {})},'text':tx[:180],'style':sid,'structure':'内容控件' if sdt else '主文档顶层','automatic':pid in auto,'candidate':hint,'reason':'；'.join(reasons) or '未发现目录线索；可人工指定但须结构校验','ambiguous':True,'complex':bool(p.xpath('.//w:ins|.//w:del|.//w:moveFrom|.//w:moveTo|.//w:drawing|.//w:pict|.//w:object|.//w:txbxContent',namespaces=NS)),'special':special,'broken':pid in broken or any(not f['balanced'] and pid in f['objects'] for f in toc)})
 unlisted=[]
 supported=set(ps for ps in nodes(pkg))
 for j,p in enumerate(pkg.root.find(q('body')).iter(q('p')),1):
  if p in supported:continue
  instructions=' '.join(p.xpath('.//w:instrText/text() | .//w:fldSimple/@w:instr',namespaces=NS));style=p.find('w:pPr/w:pStyle',NS)
  if re.search(r'\bTOC\b',instructions,re.I) or style is not None and re.fullmatch(r'(?:TOC|目录)\s*[1-9]',style.get(q('val'),''),re.I) or re.fullmatch(r'\s*目\s*录\s*',text(p)):
   unlisted.append({'id':'unsupported:'+str(j),'reason':'表格/文本框中的目录线索未纳入可确认对象；需在Word人工核对，不能宣称已覆盖'})
 return {'input_sha256':pkg.hash,'objects':rows,'fields':fields,'unlisted_structures':unlisted,'broken_objects':broken,'limits':LIMITS,'indexing':'d:N为主文档及内容控件段落对象编号；旧顶层段落编号不变，不是物理页码'}
def make_scope(path):
 inv=inventory(path)
 return {'input_sha256':inv['input_sha256'],'confirmed':False,'confirmation':'建议尚未确认','objects':{},'covered_levels':[1,2,3],'complete':False,'headings_complete':False,'template':school()}
def validate_scope(pkg,s,*,confirmed=True):
 if type(s) is not dict or set(s)!={'input_sha256','confirmed','confirmation','objects','covered_levels','complete','headings_complete','template'} or s['input_sha256']!=pkg.hash:raise DemoError('目录范围结构或文件哈希不匹配')
 if type(s['confirmed']) is not bool or confirmed and not s['confirmed'] or type(s['confirmation']) is not str or not 0<len(s['confirmation'])<=200:raise DemoError('目录范围/层级须人工确认')
 if type(s['complete']) is not bool or type(s['headings_complete']) is not bool or type(s['covered_levels']) is not list or not s['covered_levels'] or any(type(n) is not int or n not in (1,2,3) for n in s['covered_levels']) or len(set(s['covered_levels']))!=len(s['covered_levels']):raise DemoError('目录覆盖层级或完整范围声明无效')
 ids={'d:'+str(i) for i,_ in enumerate(nodes(pkg),1)}
 if type(s['objects']) is not dict or any(type(k) is not str or k not in ids or type(v) is not str or v not in ROLES for k,v in s['objects'].items()):raise DemoError('目录对象定位或层级无效')
 validate_template(s['template']);return deepcopy(s)
def norm(s):return re.sub(r'\s+',' ',s).strip() # do not erase numbering or punctuation

def entry(p):
 tx=ordered_text(p);m=re.match(r'^(.*?)(?:\t+|\.{3,}|…{2,})\s*(\d+|[IVXLCDMivxlcdm]+)\s*$',tx)
 return {'original':tx,'title':m[1].rstrip() if m else tx,'saved_page':m[2] if m else None,'page_state':'保存文本，实际页码未核对'}
def correspond(pkg,s,classification,inv):
 from .numbering import numbering_info,public_numbering
 res=Resolver(pkg);heads=[];last=0;jumps=[]
 for n,t in sorted(classification['paragraph_types'].items(),key=lambda item:int(item[0])):
  if t not in ('heading1','heading2','heading3','appendix_title','ack_title'):continue
  p=pkg.paragraphs[int(n)-1];level=int(t[-1]) if t.startswith('heading') else 1;info=public_numbering(numbering_info(pkg,res,p))
  heads.append({'paragraph':int(n),'level':level,'type':t,'text':text(p),'numbering':info})
  if level>last+1:jumps.append({'paragraph':int(n),'reason':'已确认标题层级跳跃；不自动改级别/编号'})
  last=level
 bookmarks={};duplicates=set();invalid_bookmarks=set();ordered=list(pkg.root.iter());positions={e:i for i,e in enumerate(ordered)}
 starts=list(pkg.root.iter(q('bookmarkStart')));ends=list(pkg.root.iter(q('bookmarkEnd')))
 for e in pkg.root.iter(q('bookmarkStart')):
  name=e.get(q('name'));p=next((a for a in e.iterancestors() if a.tag==q('p')),None)
  n=next((i for i,x in enumerate(pkg.paragraphs,1) if x is p),None)
  if name in bookmarks:duplicates.add(name)
  ident=e.get(q('id'));matching=[x for x in ends if x.get(q('id'))==ident]
  if ident is None or len([x for x in starts if x.get(q('id'))==ident])!=1 or len(matching)!=1 or positions[e]>=positions[matching[0]]:invalid_bookmarks.add(name)
  bookmarks[name]=n
 rows=[];matched=set();ps=nodes(pkg);byid={x['id']:x for x in inv['objects']}
 for oid,role in sorted(s['objects'].items(),key=lambda item:int(item[0][2:])):
  if role=='title':continue
  p=ps[int(oid[2:])-1];info=entry(p);anchors=list(dict.fromkeys(p.xpath('.//w:hyperlink/@w:anchor',namespaces=NS)))
  # Common PAGEREF instructions only; never evaluate.
  instr=list(p.xpath('.//w:instrText/text() | .//w:fldSimple/@w:instr',namespaces=NS))
  for t in instr:
   m=re.match(r'^\s*PAGEREF\s+(?:"([^"]+)"|([^\s\\]+))',t,re.I)
   if m:anchors.append(m[1] or m[2])
  for f in inv['fields']:
   if oid in f['objects']:
    m=re.match(r'^\s*PAGEREF\s+(?:"([^"]+)"|([^\s\\]+))',f['instruction'],re.I)
    if m:anchors.append(m[1] or m[2])
  anchors=list(dict.fromkeys(anchors));reason='';evidence='确认范围内文字精确匹配（仅空白归一）';status='review';candidates=[]
  if anchors:
   evidence='内部目标 '+', '.join(anchors)
   if getattr(pkg,'_reference_integrity_enabled',False) and len(anchors)==1:
    from .internal_refs import resolve_target
    proof=resolve_target(pkg,anchors[0]);evidence+='；共用R44目标证据（重复展示不另计目标故障）'
    if proof['state']!='pass':reason=proof['reason']
    else:
     target=proof['target_location']
     candidates=[h for h in heads if target['part']=='word/document.xml' and h['paragraph']==target.get('paragraph')]
     if not candidates:reason='有效内部目标不在已确认主文档标题范围，无法判断'
   elif len(anchors)!=1 or anchors[0] in duplicates:reason='多个/重复书签目标，无法唯一对应'
   elif anchors[0] not in bookmarks:reason='链接/PAGEREF目标缺失'
   elif anchors[0] in invalid_bookmarks:reason='书签边界缺失/重复/次序异常，不能证明内部目标有效'
   else:
    candidates=[h for h in heads if h['paragraph']==bookmarks[anchors[0]]]
    if not candidates:reason='目标不在已确认正文标题范围，无法判断'
  else:candidates=[h for h in heads if norm(h['text'])==norm(info['title'])]
  if not reason:
   if not candidates:reason='确认范围不足，未找到候选不证明缺项' if not s['headings_complete'] else '已声明完整标题范围内未找到明确对应'
   elif len(candidates)>1:reason='同名标题，多候选，须人工确认'
   elif role=='unknown':reason='目录级别未确认'
   elif norm(candidates[0]['text'])!=norm(info['title']):
    if info['saved_page'] is None:status='review';reason='未可靠拆分保存页码，缓存文字与目标比较须人工核对'
    elif candidates[0]['numbering'].get('present'):status='review';reason='缓存文字与标题文字不同；自动编号显示序号未计算，编号对应与文字差异须分别人工核对'
    else:status='risk';reason='缓存文字与链接目标标题不同，可能需要人工更新目录'
   elif candidates[0]['level']!=int(role[-1]):status='risk';reason='确认的目录层级与正文标题层级冲突'
   else:status='pass';reason='文字与确认层级一致；页码仍未核对';matched.add(candidates[0]['paragraph'])
  if any(h.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id') is not None for h in p.iter(q('hyperlink'))):status='review';reason='目录含关系ID链接，未证明为本主文档内部书签；文字匹配不替代链接目标核对'
  if byid[oid]['complex']:status='review';reason='含修订、图形或文本框等复杂内容；文字及目标对应不能可靠解释'
  if byid[oid]['broken']:status='review';reason='域断裂/未闭合，保存结果范围不能可靠解释'
  rows.append({'id':oid,'locator':byid[oid]['locator'],'level':role,'entry':info,'targets':anchors,'candidates':candidates,'evidence':evidence,'status':status,'reason':reason,'numbering_state':'自动编号显示序号未计算，文字与编号分开核对' if any(h['numbering'].get('present') for h in candidates) else '文字比较保留原题序；无序号重写'})
 missing=[]
 if s['complete'] and s['headings_complete']:
  missing=[{'paragraph':h['paragraph'],'level':h['level'],'reason':'完整确认范围内，所覆盖层级未找到已证明一致的目录条目；可能缺项或存在对应风险'} for h in heads if h['level'] in s['covered_levels'] and h['paragraph'] not in matched]
 return {'rows':rows,'hierarchy_notes':jumps,'missing_candidates':missing,'scope_state':'已确认完整对应范围' if s['complete'] and s['headings_complete'] else '部分确认，不判整篇缺项','page_status':'未核对实际页码','normalization':'仅连续空白归一及去除已明确识别的末尾页码分隔；保留数字、标点与原文','risk_count':sum(r['status']=='risk' for r in rows),'review_count':sum(r['status']=='review' for r in rows)}

def append_checks(report,pkg,s,classification):
 s=validate_scope(pkg,s);inv=inventory(pkg);res=Resolver(pkg);byid={r['id']:r for r in inv['objects']};ps=nodes(pkg);fs=report['findings'];values=s['template']['values']
 def add(rid,loc,prop,actual,target,status,reason='',safe=False,n=None):
  loc={**loc,'property':prop};src=s['template']['sources'][n] if n else {'kind':'not_enabled','quote':'','location':None}
  source={'label':'2015学校目录演示原文；非现行标准','file':'00-全员必看/本科毕业设计论文.pdf','physical_page':18,'quote':QUOTE} if src['kind']=='school_demo' else {'label':{'user_confirmed':'用户确认值','ai_extracted':'模板保存的历史AI依据（本次非实时解析）','not_enabled':'产品支持边界'}[src['kind']],'quote':src['quote'],'location':src['location']}
  f={'key':rid+':'+':'.join(f'{k}={v}' for k,v in loc.items()),'rule_id':rid,'rule_name':{'R30':'目录标题格式','R31':'一级目录条目格式','R32':'次级目录条目格式'}[rid]+' · '+prop,'locator':loc,'property':prop,'object_type':'toc_title' if rid=='R30' else 'toc_entry','actual':actual,'expected':target,'status':status,'fixable':status=='problem' and safe and not pkg.signed and not pkg.ambiguous_sections,'source':source,'detail':reason,'excerpt':byid['d:'+str(loc['toc_object'])]['text'][:64] if 'toc_object' in loc else ''};fs.append(f);return f
 for oid,role in sorted(s['objects'].items(),key=lambda item:int(item[0][2:])):
  row=byid[oid];loc=row['locator'];p=ps[int(oid[2:])-1];rid='R30' if role=='title' else 'R31' if role=='level1' else 'R32'
  if role=='unknown':add(rid,loc,'structure','目录级别未确认',None,'review','请核对条目级别；未执行格式修正');continue
  if row['automatic'] or row['special'] or row['broken']:
   add(rid,loc,'structure','自动目录缓存只读' if row['automatic'] else row['special'] or '断裂域',None,'review','保留域/超链接/书签/PAGEREF；本阶段不修正缓存，普通手工目录才可修正');continue
  if len(p.findall(q('pPr')))>1:add(rid,loc,'structure','重复段落格式容器',None,'review');continue
  for prop in ('alignment','line_multiple'):
   n=role+'__'+prop;target=values[n]
   if target is None:continue
   try:
    layers=res.layers(p,kind='pPr')
    if any(len(layer.findall(q('jc' if prop=='alignment' else 'spacing')))>1 for layer in layers):raise Unresolved('重复段落属性，继承值有冲突')
    if prop=='alignment':a=alignment(res,layers)
    else:
     attrs=res.attrs(layers,'spacing');line=attrs.get('line');kind=attrs.get('lineRule','auto')
     if line is None or not re.fullmatch(r'\d+',line) or int(line)<=0 or kind not in ('auto','exact','atLeast'):raise Unresolved('行距缺失或无法判断')
     a={'multiple':int(line)/240} if kind=='auto' else {'points':int(line)/20,'lineRule':kind}
    eq=a==target if prop=='alignment' else a.get('multiple')==target
    special=any(res.special(r,res.layers(p,r)) for r in p.findall(q('r')))
    add(rid,loc,prop,a,target,'pass' if eq else 'problem',safe=not special,n=n)
   except (Unresolved,ValueError) as e:add(rid,loc,prop,{'unresolved':str(e)},target,'review',str(e),n=n)
  for i,r in enumerate(p.findall(q('r')),1):
   tx=text(r)
   if not tx.strip():continue
   rl={**loc,'run':i}
   try:
    layers=res.layers(p,r);special=res.special(r,layers)
    if any(len(layer.findall(q(name)))>1 for layer in layers for name in ('rFonts','sz')):raise Unresolved('重复字体/字号属性，继承值冲突')
    if special or len(r.findall(q('rPr')))>1:raise Unresolved(special or '重复文字格式容器')
   except Unresolved as e:add(rid,rl,'structure',str(e),None,'review','特殊文字未修正：'+str(e));continue
   cn,west,unknown=scripts(tx)
   for prop in ('font_cn','font_size'):
    n=role+'__'+prop;target=values[n]
    if target is None or prop=='font_cn' and not cn:continue
    try:
     if prop=='font_cn':
      proof=res.font_info(layers,'eastAsia',tx)
      if proof['font'] is None:raise Unresolved(proof.get('reason','字体无法确定'))
      a=proof['font'];f=add(rid,rl,prop,a,target,'pass' if same_font(a,target) else 'problem',safe=proof['safe_to_fix_slot'],n=n);f['font_evidence']={'eastAsia':proof}
     else:
      a=res.size(layers)
      if a is None:raise Unresolved('字号未设置且无有效继承')
      add(rid,rl,prop,a,target,'pass' if a==target else 'problem',safe=True,n=n)
    except Unresolved as e:add(rid,rl,prop,{'unresolved':str(e)},target,'review',str(e),n=n)
   if unknown:add(rid,rl,'character_boundary','不支持文字槽位',None,'review','不证明任意Unicode字体已覆盖')
 for rid in IDS:
  if not any(f['rule_id']==rid for f in fs):add(rid,{'document':1},'scope','当前确认范围无适用对象',None,'not_applicable','不据此断言整篇缺少目录')
 for obj in inv['unlisted_structures']:report['coverage_notes'].append({'locator':{'toc_unlisted':obj['id']},'status':'review','detail':obj['reason']})
 report['summary']['review_notes']=len(report['coverage_notes'])
 report['coverage']['toc_scope']=deepcopy(s);report['coverage']['toc_limits']=LIMITS
 report['rules']['toc_supplement']={'name':s['template']['name'],'structure_version':1,'sha256':digest(s['template']),'sources':deepcopy(s['template']['sources'])}
 report['toc']=correspond(pkg,s,classification,inv);report['toc']['inventory']=inv
 for state,name in [('problem','problem_count'),('pass','pass_count'),('not_applicable','not_applicable_count'),('review','review_findings')]:report['summary'][name]=sum(f['status']==state for f in fs)
 report['summary']['rule_count']+=3;report['summary']['review_count']=report['summary']['review_findings']+len(report['coverage_notes']);report['summary']['applicable_rule_count']=len({f['rule_id'] for f in fs if f['status']!='not_applicable'});report['summary']['conclusion']='已覆盖检查发现问题' if report['summary']['problem_count'] else '已覆盖检查未发现问题'

def apply(pkg,f):
 from .engine import _ensure
 p=nodes(pkg)[f['locator']['toc_object']-1];prop=f['property'];v=f['expected']
 if prop in ('font_cn','font_size'):
  r=p.findall(q('r'))[f['locator']['run']-1];rp=_ensure(r,'rPr');e=_ensure(rp,'rFonts' if prop=='font_cn' else 'sz')
  e.set(q('eastAsia' if prop=='font_cn' else 'val'),v if prop=='font_cn' else str(round(v*2)))
  if prop=='font_cn':e.attrib.pop(q('eastAsiaTheme'),None)
 else:
  pp=_ensure(p,'pPr');e=_ensure(pp,'jc' if prop=='alignment' else 'spacing')
  if prop=='alignment':e.set(q('val'),v)
  else:e.set(q('line'),str(round(v*240)));e.set(q('lineRule'),'auto')
def mask(root,f):
 class Proxy:pass
 pkg=Proxy();pkg.root=root
 p=nodes(pkg)[f['locator']['toc_object']-1];prop=f['property']
 if prop in ('font_cn','font_size'):
  r=p.findall(q('r'))[f['locator']['run']-1];e=r.find('w:rPr/w:'+('rFonts' if prop=='font_cn' else 'sz'),NS);attrs=('eastAsia','eastAsiaTheme') if prop=='font_cn' else ('val',)
 else:e=p.find('w:pPr/w:'+('jc' if prop=='alignment' else 'spacing'),NS);attrs=('val',) if prop=='alignment' else ('line','lineRule')
 if e is not None:
  for a in attrs:e.attrib.pop(q(a),None)
 # Empty jc can be introduced; removal is confined to selected object.
 for e in reversed(list(p.iter())):
  if e.tag in {q(x) for x in ('jc','spacing','rFonts','sz','rPr','pPr')} and not len(e) and not e.attrib and not e.text:e.getparent().remove(e)

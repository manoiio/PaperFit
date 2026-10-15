"""Opt-in R33/R34. Local candidates are not confirmed citations.
Only ASCII [positive integer] is executable; other bracket forms stay read-only.
"""
from copy import deepcopy
import json,re
from lxml import etree as E
from .package import Package,DemoError,q,NS,sha256
from .formats import Resolver,Unresolved,paragraph_unsafe
QUOTE='正文中应按顺序在引用参考文献处的文字右上角用[]标明，[]中序号应与参考文献中序号一致。'
SOURCE={'file':'00-全员必看/本科毕业设计论文.pdf','physical_page':18,'quote':QUOTE,'label':'2015学校演示材料，非现行通用规范'}
LIMITS=['仅人工确认正文扫描范围；候选不是引用，确认不授权修正。','仅ASCII [1]单个正整数（1–99999）可执行；组合、区间、全角及异常数字只读，不转换文字。','对应与首次顺序均只读；不核验文献真实性或论据，不改编号、不补删条目。','复杂段落（含域、链接、书签、修订、公式等）整体不拆run；其他安全段落仍可修正。','上标后通用正文规则继续保护特殊run；新增覆盖提示不是全文通过或格式回退。']
CONFIG={'structure_version':1,'kind':'paper-grid-citation-supplement','name':'用户确认的引文演示检查','superscript':True,'correspondence':True,'source':SOURCE}

def template(value):
 if type(value) is not dict or set(value)!=set(CONFIG) or type(value['structure_version']) is not int or value['structure_version']!=1 or value['kind']!=CONFIG['kind'] or type(value['name']) is not str or not 0<len(value['name'])<=80 or any(type(value[k]) is not bool for k in ('superscript','correspondence')) or value['source']!=SOURCE:raise DemoError('引文补充配置版本、字段或来源无效')
 return deepcopy(value)
def text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=NS))
def field_paragraphs(pkg):
 # Reuse the existing cross-paragraph field stack; a cache paragraph need not contain fldChar.
 from .toc import parse_fields,nodes
 fields,broken=parse_fields(pkg);known={oid for f in fields for oid in f['objects']};ids=known|set(broken)
 # An orphan end/separator can hide an earlier cache; preceding paragraphs are uncertain.
 orphan=[int(oid[2:]) for oid in broken if oid not in known]
 if orphan:ids|={'d:'+str(i) for i in range(1,max(orphan)+1)}
 protected={p for i,p in enumerate(nodes(pkg),1) if 'd:'+str(i) in ids}
 return {n for n,p in enumerate(pkg.paragraphs,1) if p in protected}

def reference_evidence(pkg,nums):
 """Shared by R22 and R34: never infer reference number from row order."""
 rows=[];res=Resolver(pkg);field_ps=field_paragraphs(pkg)
 for n in sorted(nums):
  p=pkg.paragraphs[n-1];m=re.match(r'^\s*[\[［](\d+)[\]］]',text(p));reason='手工方括号编号（复用R22证据）';number=None
  try:
   if n in field_ps or paragraph_unsafe(p):reason='条目含域/跨段域缓存或复杂结构，R22未确认其编号'
   elif any(x.find(q('numPr')) is not None for x in res.layers(p,kind='pPr')):reason='自动编号，未计算显示编号'
   elif m and len(m[1])<=5:number=int(m[1])
   elif m:reason='编号过长，超出本地核对范围'
   else:reason='未识别明确的手工方括号编号'
  except Unresolved as e:reason=str(e)
  rows.append({'paragraph':n,'number':number,'preview':text(p)[:60],'reason':reason})
 return rows

def safe(p,res):
 if p.xpath('.//w:fldSimple|.//w:fldChar|.//w:instrText',namespaces=NS):return '域/REF或交叉引用生成文字：只读，不改域指令与缓存'
 if p.xpath('.//w:hyperlink',namespaces=NS):return '超链接文字：只读，不拆链接或改关系'
 if p.xpath('.//w:bookmarkStart|.//w:bookmarkEnd',namespaces=NS):return '书签边界：只读，不跨边界拆run'
 reason=paragraph_unsafe(p)
 if reason:return reason
 if any(c.tag not in (q('pPr'),q('r')) for c in p):return '书签、校对边界或未知对象；不跨边界拆run'
 for r in p.findall(q('r')):
  if set(c.tag for c in r)-{q('rPr'),q('t')} or len(r.findall(q('t')))!=1 or len(r.findall(q('rPr')))>1 or not text(r):return '非单一普通w:t结构，禁止拆分'
  try:
   layers=res.layers(p,r)
   # Superscript is the intended change; all other special protections still apply.
   for tag in ('position','rtl','cs','vanish','webHidden'):
    if res.value(layers,tag,'0') not in ('0','false','off'):return '基线位移、复杂文字或隐藏文字'
   if any(layer.find(q(tag)) is not None for layer in layers for tag in ('rPrChange','fitText','eastAsianLayout','oMath')):return '修订或特殊文字格式'
   if res.value(layers,'vertAlign','baseline') not in ('baseline','superscript','subscript'):return '未知vertAlign'
  except Unresolved as e:return str(e)
 return None

def states(p,start,end,res):
 offset=0;values=[]
 for i,r in enumerate(p.findall(q('r')),1):
  stop=offset+len(text(r))
  if offset<end and stop>start:
   layers=res.layers(p,r);value=res.value(layers,'vertAlign','baseline')
   if value not in ('baseline','superscript','subscript'):raise Unresolved('未知vertAlign值')
   source=next((('直接格式' if layer is r.find(q('rPr')) else '样式/默认继承') for layer in reversed(layers) if layer.find(q('vertAlign')) is not None),'OOXML缺省baseline')
   values.append({'run':i,'start':max(offset,start),'end':min(stop,end),'value':value,'source':source})
  offset=stop
 if not values:raise Unresolved('没有可靠的普通文字范围')
 return values

def inventory(path,scan):
 pkg=path if isinstance(path,Package) else Package(path);res=Resolver(pkg);rows=[];field_ps=field_paragraphs(pkg)
 for n in sorted(scan):
  p=pkg.paragraphs[n-1];tx=text(p);why='域/跨段域缓存：只读，不改指令、缓存或边界' if n in field_ps else safe(p,res)
  for m in re.finditer(r'[\[［][^\[\]［］\r\n]*[\]］]',tx):
   raw=m[0]
   if not re.search(r'\d',raw):continue
   normal=re.fullmatch(r'\[([1-9][0-9]{0,4})\]',raw)
   numbers=[int(normal[1])] if normal else [];reason=why or (None if normal else '不支持的组合/区间/全角或异常编号语法；只读待复核')
   try:
    if why:raise Unresolved(why)
    vs=states(p,m.start(),m.end(),res);current='superscript' if all(v['value']=='superscript' for v in vs) else 'mixed' if len(set(v['value'] for v in vs))>1 else vs[0]['value']
   except Unresolved as e:vs=[];current='unresolved';reason=reason or str(e)
   rows.append({'id':f'c:{n}:{m.start()}:{m.end()}','paragraph':n,'start':m.start(),'end':m.end(),'text':raw[:100],'context':tx[max(0,m.start()-15):min(len(tx),m.end()+15)][:100],'numbers':numbers,'vertical':current,'evidence':vs,'structure':'普通文字' if not why else '域或跨段域缓存' if n in field_ps else '超链接' if '超链接' in why else '书签边界' if '书签' in why else '受保护结构','safe_structure':not reason,'fixable':not reason and not pkg.signed and not pkg.ambiguous_sections,'reason':reason or '仅候选，可能是数组或其他标记，须人工确认用途'})
 return {'input_sha256':pkg.hash,'objects':rows,'limits':LIMITS}

def make_scope(pkg,scan):
 return {'input_sha256':pkg.hash,'scan':sorted(scan),'objects':{},'complete':False,'references_complete':False,'confirmed':False,'confirmation':'候选尚未人工核对','template':deepcopy(CONFIG)}
def validate_scope(pkg,s,classification=None,*,confirmed=True):
 keys={'input_sha256','scan','objects','complete','references_complete','confirmed','confirmation','template'}
 if type(s) is not dict or set(s)!=keys or s['input_sha256']!=pkg.hash:raise DemoError('引文范围结构或哈希不匹配')
 if type(s['scan']) is not list or any(type(n) is not int or not 1<=n<=len(pkg.paragraphs) for n in s['scan']) or len(set(s['scan']))!=len(s['scan']):raise DemoError('引文扫描段落无效')
 if any(type(s[k]) is not bool for k in ('complete','references_complete','confirmed')) or confirmed and not s['confirmed'] or type(s['confirmation']) is not str or not 0<len(s['confirmation'])<=200:raise DemoError('引文范围和用途须人工确认')
 if classification and any(classification['paragraph_types'].get(str(n))!='body' for n in s['scan']):raise DemoError('引文只能扫描已确认正文，不能覆盖目录/参考文献/封面')
 inv=inventory(pkg,s['scan']);ids={r['id'] for r in inv['objects']}
 if type(s['objects']) is not dict or any(type(k) is not str or k not in ids or type(v) is not str or v not in ('citation','excluded','pending') for k,v in s['objects'].items()):raise DemoError('引文准确字符范围或用途失效，请重新核对')
 template(s['template']);return deepcopy(s)

def append_checks(report,pkg,s,classification):
 s=validate_scope(pkg,s,classification);inv=inventory(pkg,s['scan']);res=Resolver(pkg);fs=report['findings'];selected=[r for r in inv['objects'] if s['objects'].get(r['id'])=='citation'];refs=reference_evidence(pkg,sorted(int(n) for n,t in classification['paragraph_types'].items() if t=='reference_item'));by={}
 for r in refs:
  if r['number'] is not None:by.setdefault(r['number'],[]).append(r)
 undecided=[r['id'] for r in inv['objects'] if s['objects'].get(r['id'],'pending')=='pending'];unknown=any(r['number'] is None for r in refs) or any(not r['numbers'] or not r['safe_structure'] for r in selected)
 full=bool(selected) and bool(refs) and s['complete'] and s['references_complete'] and not undecided and not unknown and set(s['scan'])=={int(n) for n,t in classification['paragraph_types'].items() if t=='body'}
 def add(rid,loc,actual,expected,status,reason,fixable=False,excerpt=''):
  key=rid+':'+':'.join(f'{k}={v}' for k,v in loc.items());f={'key':key,'rule_id':rid,'rule_name':'正文引文上标' if rid=='R33' else '引文对应及顺序（只读）','locator':loc,'actual':actual,'expected':expected,'status':status,'fixable':status=='problem' and fixable,'source':deepcopy(SOURCE),'detail':reason,'excerpt':excerpt,'object_type':'citation' if rid=='R33' else 'citation_relation'};fs.append(f);return f
 rows=[];seen=set();order=[];used=set()
 for r in selected:
  loc={'citation':r['id'],'paragraph':r['paragraph'],'start':r['start'],'end':r['end']}
  if s['template']['superscript']:
   status='review' if not r['safe_structure'] else 'pass' if r['vertical']=='superscript' else 'problem'
   f=add('R33',loc,r['vertical'],'superscript',status,r['reason'] if status=='review' else '仅改变此引文vertAlign；不缩小字号。跨run按原始字符快照拆分，前后文字保留。',r['fixable'],r['text']);f['vertical_evidence']=r['evidence']
  if s['template']['correspondence']:
   if not r['numbers']:
    add('R34',{**loc,'property':'correspondence'},None,'唯一手工编号条目','review','组合/区间或异常编号语法未解释；不展开或猜测');rows.append({**r,'references':[],'status':'review','relation':'编号无法确定'});continue
   number=r['numbers'][0];matches=by.get(number,[]);used.add(number)
   status='review' if not r['safe_structure'] else 'pass' if len(matches)==1 else 'review' if len(matches)>1 or not full else 'problem'
   why='对应唯一确认条目（不证明真实性或引用准确）' if len(matches)==1 else '重复参考文献编号，关联R22手工编号证据，不重复新增缺号结论' if matches else '完整且可解析的确认范围内未找到对应条目' if full else '当前确认范围内未找到，范围/编号不完整，不能判全文缺失'
   if not r['safe_structure']:why='受保护/不支持引文结构，缓存数字不足以证明对应；'+r['reason']
   add('R34',{**loc,'property':'correspondence'},[m['paragraph'] for m in matches],f'文献[{number}]唯一条目',status,why)
   rows.append({**r,'references':matches,'status':status,'relation':why})
   if r['safe_structure'] and number not in seen:order.append(number);seen.add(number)
 if s['template']['correspondence']:
  ok=order==sorted(order) and (not order or order[0]==1) and order==list(range(1,len(order)+1))
  add('R34',{'document':1,'property':'first_occurrence'},order,'首次引用从1顺序出现；重复引用不重复计入','pass' if full and ok else 'problem' if full and not ok else 'review','完整确认范围内的首次顺序只读核对' if full else '仅局部首次顺序；范围或编号不足，未完成全文顺序验收')
  if not selected:add('R34',{'document':1,'property':'scope'},0,None,'review','未确认引文；不能声称全文无引用或对应通过')
 if s['template']['superscript'] and not selected:add('R33',{'document':1,'property':'scope'},0,None,'not_applicable','当前未确认引文，不代表全文无引文或全文上标通过')
 unreferenced=[r for r in refs if r['number'] is not None and r['number'] not in used] if s['template']['correspondence'] else []
 report['citations']={'enabled':{k:s['template'][k] for k in ('superscript','correspondence')},'rows':rows,'references':refs,'unreferenced':unreferenced,'undecided':undecided,'scope_state':'未启用R34，对应与顺序未检查' if not s['template']['correspondence'] else '已声明完整且解析覆盖足够' if full else '部分/不确定范围，不能判全文缺失或顺序通过','order':order,'limits':LIMITS,'unreferenced_state':'确认范围内未找到已解析引文，仅核对提示；复杂/未确认引文可能遗漏，无自动删除或违规结论','r22_link':'文献手工编号证据复用R22，重复编号仅造成关系待复核，不另计同一编号错误'}
 report['citations']['summary']={'superscript_problems':sum(f['rule_id']=='R33' and f['status']=='problem' for f in fs),'correspondence_problems':sum(f['rule_id']=='R34' and f['locator'].get('property')=='correspondence' and f['status']=='problem' for f in fs),'order_problems':sum(f['rule_id']=='R34' and f['locator'].get('property')=='first_occurrence' and f['status']=='problem' for f in fs),'review_records':sum(f['rule_id'] in ('R33','R34') and f['status']=='review' for f in fs)}
 report['coverage']['citation_scope']=deepcopy(s)
 raw=json.dumps(template(s['template']),ensure_ascii=False,sort_keys=True).encode();report['rules']['citation_supplement']={'name':s['template']['name'],'version':1,'sha256':sha256(raw),'values':deepcopy(s['template']),'source':SOURCE}
 for status,name in [('problem','problem_count'),('pass','pass_count'),('not_applicable','not_applicable_count'),('review','review_findings')]:report['summary'][name]=sum(f['status']==status for f in fs)
 report['summary']['rule_count']+=int(s['template']['superscript'])+int(s['template']['correspondence']);report['summary']['review_count']=report['summary']['review_findings']+len(report['coverage_notes']);report['summary']['applicable_rule_count']=len({f['rule_id'] for f in fs if f['status']!='not_applicable'});report['summary']['conclusion']='已覆盖检查发现问题' if report['summary']['problem_count'] else '已覆盖检查未发现问题' 

def apply(pkg,f):
 from .academic import isolate
 from .engine import _ensure
 loc=f['locator'];p=pkg.paragraphs[loc['paragraph']-1]
 if safe(p,Resolver(pkg)):raise DemoError('引文结构不能安全拆分')
 for r in isolate(p,loc['start'],loc['end']):_ensure(_ensure(r,'rPr'),'vertAlign').set(q('val'),'superscript')
def mask(p,f):
 offset=0;loc=f['locator']
 for r in p.findall(q('r')):
  end=offset+len(text(r))
  if offset>=loc['start'] and end<=loc['end']:
   rp=r.find(q('rPr'))
   if rp is not None:
    for e in list(rp.findall(q('vertAlign'))):rp.remove(e)
  offset=end

def boundaries(p):
 offset=0;out=[]
 for r in p.findall(q('r')):offset+=len(text(r));out.append(offset)
 return out

def partition_guard(before,after,selected):
 """Only necessary boundaries may be added; never merge or resplit other runs."""
 for n in {f['locator']['paragraph'] for f in selected if f['rule_id']=='R33'}:
  wanted=set(boundaries(before.paragraphs[n-1]))
  for f in selected:
   if f['rule_id']=='R33' and f['locator']['paragraph']==n:wanted.update((f['locator']['start'],f['locator']['end']))
  wanted.discard(0)
  if boundaries(after.paragraphs[n-1])!=sorted(wanted):raise DemoError('引文拆分超出所选字符的必要run边界')

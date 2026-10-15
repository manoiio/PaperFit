"""Opt-in R42/R43 and L05. Numbering is read-only; movement is an exact XML permutation."""
from copy import deepcopy
from collections import Counter
import json,re
from lxml import etree as E
from .package import Package,DemoError,q,NS,sha256
from .formats import Resolver,Unresolved
from .numbering import numbering_info,public_numbering
from .table_text import tables
from .layout import _ordinary_reason,_pair_reason,_table_reason

SOURCE={'label':'2015学校材料；章内连续序列为产品核对解释','file':'00-全员必看/本科毕业设计论文.pdf','physical_page':18,'quote':'插图（表）应有图（表）题（由序号和标题组成），图（表）号按章编序，如第一章第一图的号为“图1-1”。图题置于图下方，表题置于表上方。'}
LIMITS=['编号只读，不改SEQ/STYLEREF缓存、numbering.xml、题注文字或编号。','XML前后顺序不等于页面坐标；位置正确不证明实际同页。图与图题不得拆页须另行视觉核对。','完整范围声明且普通手工编号解析充分时才检查起始/缺号；续表、分图和附录编号只读待复核。','L05仅交换紧邻普通题注与单一内嵌图片段/普通顶层表格；不跨空段、分节、强制分页、域、书签或链接。','位置修正独立一轮；不自动附加L01/L02，不保证移动后同页。']
ROLES={'normal':'普通手工题注','continuation':'续表（只读）','special':'分图/附录等（待复核）','pending':'待确认','excluded':'排除'}
def digest(v):return sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode())
def text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=NS))
def school():return {'kind':'paper-grid-caption-supplement','structure_version':1,'name':'用户确认的题注编号位置核对','numbering':True,'position':True}
def template(t):
 if type(t) is not dict or set(t)!={'kind','structure_version','name','numbering','position'} or t['kind']!='paper-grid-caption-supplement' or type(t['structure_version']) is not int or t['structure_version']!=1 or type(t['name']) is not str or not 1<=len(t['name'])<=80 or any(c in t['name'] for c in '/\\\n\x00') or any(type(t[k]) is not bool for k in ('numbering','position')):raise DemoError('题注补充配置版本或字段无效')
 return deepcopy(t)
def make_scope(pkg):return {'input_sha256':pkg.hash,'confirmed':False,'confirmation':'题注范围尚未核对','captions':{},'chapter_map':{},'associations':{},'complete':False,'chapters_complete':False,'template':school()}
def objects(pkg):
 # Same top-level image paragraphs and tables as L01/L02; no nested inventory.
 body=pkg.root.find(q('body'));pnums={p:n for n,p in enumerate(pkg.paragraphs,1)};ts={t:n for n,t in enumerate(tables(pkg),1)};out={}
 for i,e in enumerate(body,1):
  if e in ts:out['table:'+str(ts[e])]={'kind':'table','table':ts[e],'body_object':i,'summary':f'{len(e.findall(q("tr")))}行 / {len(e.findall("w:tblGrid/w:gridCol",NS))}列','element':e}
  elif e in pnums and e.xpath('.//w:drawing|.//w:pict|.//w:object',namespaces=NS):out['image:p:'+str(pnums[e])]={'kind':'figure','paragraph':pnums[e],'body_object':i,'summary':'图片段（普通内嵌/复杂结构须另行核对）','element':e}
 return out
def validate_scope(pkg,s,classification=None,*,confirmed=True):
 keys={'input_sha256','confirmed','confirmation','captions','chapter_map','associations','complete','chapters_complete','template'}
 if type(s) is not dict or set(s)!=keys or s['input_sha256']!=pkg.hash:raise DemoError('题注范围结构或文件哈希失效')
 if any(type(s[k]) is not bool for k in ('confirmed','complete','chapters_complete')) or confirmed and not s['confirmed'] or type(s['confirmation']) is not str or not 1<=len(s['confirmation'])<=200:raise DemoError('题注、关联及章节须人工核对确认')
 ids={str(i) for i in range(1,len(pkg.paragraphs)+1)}
 if type(s['captions']) is not dict or any(type(n) is not str or n not in ids or type(v) is not str or v not in ROLES for n,v in s['captions'].items()):raise DemoError('题注用途或段落编号无效')
 if type(s['chapter_map']) is not dict or any(type(n) is not str or n not in ids or type(v) is not int or not 1<=v<=999 for n,v in s['chapter_map'].items()):raise DemoError('章节对应须为已确认一级标题与1–999章号')
 if classification:
  types=classification['paragraph_types']
  if any(types[n] not in ('figure_caption','table_caption') for n in s['captions'] if s['captions'][n]!='excluded') or any(types[n]!='heading1' for n in s['chapter_map']):raise DemoError('题注/章节与当前分类冲突，请先核对分类，不能静默修改')
 obs=objects(pkg)
 if type(s['associations']) is not dict or any(type(n) is not str or n not in s['captions'] or type(o) is not str or o not in obs for n,o in s['associations'].items()):raise DemoError('题注关联对象定位无效')
 if classification and any(obs[o]['kind']!=('figure' if classification['paragraph_types'][n]=='figure_caption' else 'table') for n,o in s['associations'].items()):raise DemoError('图题/表题与关联对象类型冲突')
 template(s['template']);return deepcopy(s)
def chapter_number(pkg,n):
 p=pkg.paragraphs[n-1];info=public_numbering(numbering_info(pkg,Resolver(pkg),p));tx=text(p).strip()
 if info['present']:return None,'自动编号标题的实际显示章号未计算，请明确核对章号',info
 m=re.match(r'^(?:第([一二三四五六七八九十百零〇0-9]+)章|([1-9][0-9]{0,2})\s+\S)',tx)
 if not m:return None,'一级标题未含可解析章号；不得用排列位置代替章号',info
 raw=m[1] or m[2]
 if raw.isascii() and raw.isdigit():return int(raw),'标题中的明确阿拉伯章号',info
 cn={'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
 value=cn.get(raw)
 if value is None and re.fullmatch(r'[一二三四五六七八九]?十[一二三四五六七八九]?',raw):
  a,b=raw.split('十');value=cn.get(a,1)*10+cn.get(b,0)
 return value,'标题中的明确中文章号（支持1–99）' if value else '不支持的中文章号，请人工指定',info

def parse_caption(tx):
 m=re.fullmatch(r'\s*([图表])\s*([1-9][0-9]{0,2})-([1-9][0-9]{0,3})(?:\s+(.*))?',tx, re.S)
 if not m:return None
 return {'type':'figure' if m[1]=='图' else 'table','raw_number':tx[:m.end(3)].strip(),'chapter':int(m[2]),'sequence':int(m[3]),'title':(m[4] or '').strip()}

def inventory(path,classification):
 pkg=path if isinstance(path,Package) else Package(path);types=classification['paragraph_types'];obs=objects(pkg);body=list(pkg.root.find(q('body')));rows=[];chapters=[]
 for n,t in sorted(types.items(),key=lambda kv:int(kv[0])):
  if t=='heading1':
   value,reason,number=chapter_number(pkg,int(n));chapters.append({'paragraph':int(n),'text':text(pkg.paragraphs[int(n)-1])[:70],'number':value,'reason':reason,'numbering':number})
  if t not in ('figure_caption','table_caption'):continue
  p=pkg.paragraphs[int(n)-1];at=body.index(p);kind='figure' if t=='figure_caption' else 'table';near=[oid for oid,o in obs.items() if o['kind']==kind and abs(o['body_object']-1-at)==1]
  fields=p.xpath('.//w:instrText/text() | .//w:fldSimple/@w:instr',namespaces=NS)
  rows.append({'paragraph':int(n),'type':kind,'text':text(p)[:180],'body_object':at+1,'parsed':parse_caption(text(p)),'nearby':near,'fields':fields,'reason':'存在域；指令与保存结果分开，只读' if fields else '已确认题注类型仍须核对用途、章节和对象关联'})
 return {'input_sha256':pkg.hash,'captions':rows,'chapters':chapters,'objects':[{k:v for k,v in o.items() if k!='element'}|{'id':oid} for oid,o in obs.items()],'limits':LIMITS}

def boundary_reason(pkg,c,o):
 """Catch enclosing bookmarks/fields, including boundaries outside the moved nodes."""
 from .toc import nodes,parse_fields
 ps=nodes(pkg);fields,broken=parse_fields(pkg);pair={c,o};ids={'d:'+str(i) for i,p in enumerate(ps,1) if p in pair}
 if set(broken)&ids or any(ids&set(f['objects']) for f in fields):return '域/断裂域或缓存范围覆盖移动对象，禁止跨复杂边界'
 allnodes=list(pkg.root.iter());positions={e:i for i,e in enumerate(allnodes)};starts=list(pkg.root.iter(q('bookmarkStart')));ends=list(pkg.root.iter(q('bookmarkEnd')))
 low=min(positions[c],positions[o]);high=max(positions[x] for root in pair for x in root.iter())
 for b in starts:
  es=[e for e in ends if e.get(q('id'))==b.get(q('id'))]
  if len(es)!=1:
   return '存在无法可靠解释的书签范围，禁止位置纠正'
  if positions[b]<=high and positions[es[0]]>=low:return '书签范围覆盖移动对象，禁止跨书签边界'
 if len(starts)!=len(ends):return '书签边界异常，禁止位置纠正'
 return None

def position_evidence(pkg,n,oid,classification):
 p=pkg.paragraphs[n-1];obs=objects(pkg);o=obs[oid];e=o['element'];body=list(pkg.root.find(q('body')));ci=body.index(p);oi=body.index(e);kind='figure' if classification['paragraph_types'][str(n)]=='figure_caption' else 'table'
 adjacent=abs(ci-oi)==1;correct=(oi<ci if kind=='figure' else ci<oi)
 status='pass' if adjacent and correct else 'problem' if adjacent else 'review'
 reason='已确认关联且结构位置正确；实际同页尚未核对' if status=='pass' else '反向紧邻，可核对独立L05位置纠正' if adjacent else '中间有其他对象，不能自动移动或证明位置'
 why=None
 if adjacent and not correct:
  why=('重复题注段落/字符格式容器，不能证明安全' if len(p.findall(q('pPr')))>1 or any(len(r.findall(q('rPr')))>1 for r in p.findall(q('r'))) else None) or _ordinary_reason(pkg,p) or (None if all(x.tag in (q('rPr'),q('t')) for r in p.findall(q('r')) for x in r) else '题注含非普通文字结构')
  if any(x.tag not in (q('p'),q('tbl'),q('sdt'),q('sectPr')) for x in pkg.root.find(q('body'))):why=why or '主文档包含未支持的顶层边界对象，禁止位置纠正'
  if kind=='figure' and len(e.findall(q('pPr')))>1:why=why or '图片段格式容器重复，待复核'
  if numbering_info(pkg,Resolver(pkg),p)['present']:why=why or '自动编号题注的位置移动可能影响序列，首版只读'
  why=why or (_pair_reason(pkg,e,p) if kind=='figure' else ('合并表格首版不自动移动题注' if e.xpath('.//w:gridSpan|.//w:vMerge|.//w:hMerge',namespaces=NS) else _table_reason(pkg,e))) or boundary_reason(pkg,p,e)
  # Reject table/paragraph hard breaks, including inherited table-cell breaks above.
  if pkg.signed or pkg.ambiguous_sections:why=why or '签名或分节结构不明确'
 if kind=='figure' and (len(e.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}inline'))!=1 or e.xpath('.//w:pict|.//w:object|.//*[local-name()="anchor"]',namespaces=NS) or len(e.xpath('.//w:drawing',namespaces=NS))!=1 or text(e).strip()):status='review';why=why or '图片段不是单一普通内嵌对象，关联及可见位置需人工核对'
 return {'key':'L05:'+str(n)+':'+oid,'paragraph':n,'object':oid,'kind':kind,'caption_body_object':ci+1,'object_body_object':oi+1,'status':status,'order':'correct_adjacent' if adjacent and correct else 'reverse_adjacent' if adjacent else 'separated','movable':status=='problem' and not why,'reason':why or reason,'current_order':['caption',kind] if ci<oi else [kind,'caption'],'target_order':[kind,'caption'] if kind=='figure' else ['caption',kind],'actual_pages':'未核对'}

def analyze(pkg,s,classification):
 s=validate_scope(pkg,s,classification);inv=inventory(pkg,classification);rows=[];positions=[];seen=Counter()
 candidates={r['paragraph']:r for r in inv['captions']};assoc_counts=Counter(s['associations'].values())
 for ns,role in sorted(s['captions'].items(),key=lambda kv:int(kv[0])):
  n=int(ns);r=deepcopy(candidates.get(n,{'paragraph':n,'type':'unknown','text':text(pkg.paragraphs[n-1])[:180],'parsed':None,'fields':[]}));p=r['parsed'];issues=[];state='pass'
  heads=[h for h in inv['chapters'] if h['paragraph']<n];h=heads[-1] if heads else None;chapter=s['chapter_map'].get(str(h['paragraph']),h['number']) if h else None
  evidence='用户明确确认的章号' if h and str(h['paragraph']) in s['chapter_map'] else h['reason'] if h else '确认范围内无前置一级标题'
  if role=='excluded':continue
  if re.search(r'（续）|\(续\)|分图|[图表]\s*[A-Za-z]-|[0-9]-[0-9]+(?:[a-zA-Z]|\s*[（(][a-zA-Z])',r['text']):role='special';r['role']=role
  if role!='normal':state='review';issues.append('续表/特殊材料/用途未确定，不参与完整序列判定')
  if r['fields']:state='review';issues.append('域题注只读；保存结果不证明实际SEQ/STYLEREF求值')
  if not p:state='review';issues.append('编号缺失或不在可解析普通语法内；请核对，不能将未解析形式当作通过或自动改号')
  else:
   if p['type']!=r['type']:issues.append('题注类型与已确认类型冲突');state='problem' if state!='review' else state
   if not p['title']:issues.append('编号后缺少标题文字');state='problem' if state!='review' else state
   if chapter is None:issues.append('所属章号无法确定，须人工核对');state='review'
   elif chapter!=p['chapter']:issues.append('题注章号与最近确认标题章号不一致'+('；所属章节范围尚不完整，须核对' if not s['chapters_complete'] else ''));state='problem' if state!='review' and s['chapters_complete'] else 'review'
   if role=='normal' and not r['fields'] and p['type']==r['type']:seen[(r['type'],p['chapter'],p['sequence'])]+=1
  r.update(role=role,chapter_heading=h['paragraph'] if h else None,confirmed_chapter=chapter,chapter_evidence=evidence,status=state,reasons=issues);rows.append(r)
 for r in rows:
  p=r['parsed']
  if p and p['type']==r['type'] and r['role']=='normal' and not r['fields'] and seen[(r['type'],p['chapter'],p['sequence'])]>1:r['status']='problem';r['reasons'].append('同章同类编号重复；不改编号')
  if not r['reasons']:r['reasons']=['普通编号、标题文字及所属章号在确认范围内一致']
  n=r['paragraph'];oid=s['associations'].get(str(n))
  if oid:
   pos=position_evidence(pkg,n,oid,classification)
   if assoc_counts[oid]>1:pos.update(status='review',movable=False,reason='同一对象关联多个题注，存在歧义，禁止移动')
   if r['role']!='normal':pos.update(status='review',movable=False,reason='续表/特殊或未确认用途不自动移动')
   if not s['template']['position']:pos.update(movable=False,reason='位置检查未启用；不可授权L05移动')
   positions.append(pos)
  else:positions.append({'key':'L05:'+str(n)+':unconfirmed','paragraph':n,'status':'review','movable':False,'order':'unconfirmed','reason':'未确认具体对象关联；不能断言缺少图表或自动关联远处对象','actual_pages':'未核对'})
 unconfirmed=[r['paragraph'] for r in inv['captions'] if str(r['paragraph']) not in s['captions']]
 sequences=[];sufficient=not unconfirmed and s['complete'] and s['chapters_complete'] and all(r['parsed'] and r['status']=='pass' and r['role']=='normal' and not r['fields'] for r in rows)
 groups={}
 for r in rows:
  if r['parsed'] and r['parsed']['type']==r['type'] and r['role']=='normal' and not r['fields']:
   p=r['parsed'];groups.setdefault((r['type'],p['chapter']),[]).append(p['sequence'])
 for (kind,chapter),seq in groups.items():
  ordered=list(dict.fromkeys(seq));order_ok=ordered==sorted(ordered);continuous=sorted(set(seq))==list(range(1,len(set(seq))+1))
  sequences.append({'type':kind,'chapter':chapter,'observed':seq,'status':'problem' if sufficient and (not order_ok or not continuous) else 'review' if not sufficient else 'pass','reason':'完整确认范围内章内起始/顺序/缺号需核对' if sufficient and (not order_ok or not continuous) else '部分范围、编号冲突或特殊形式，不能判定完整序列' if not sufficient else '完整普通编号范围内顺序连续'})
 return {'inventory':inv,'unconfirmed_captions':unconfirmed,'numbers':rows,'positions':positions,'sequences':sequences,'scope_complete':bool(sufficient),'actual_pagination':'未检查实际同页；属性、结构与渲染结果分别核对','limits':LIMITS}

def append_checks(report,pkg,s,classification):
 a=analyze(pkg,s,classification);fs=report['findings']
 def add(rid,loc,prop,actual,wanted,status,reason):
  loc={**loc,'property':prop};fs.append({'key':rid+':'+':'.join(f'{k}={v}' for k,v in loc.items()),'rule_id':rid,'rule_name':'题注编号与章内序列' if rid=='R42' else '题注对象关联与结构位置','locator':loc,'property':prop,'object_type':'caption_number' if rid=='R42' else 'caption_position','actual':actual,'expected':wanted,'status':status,'fixable':False,'source':SOURCE,'detail':reason,'excerpt':''})
 for n in (a['unconfirmed_captions'] if any(s['template'][k] for k in ('numbering','position')) else []):
  report['coverage_notes'].append({'locator':{'paragraph':n},'status':'review','detail':'题注类型已分类，但本次编号/关联用途未确认；未执行R42/R43，不能据范围完整声明推断整篇序列已覆盖。'})
 if s['template']['numbering']:
  for r in a['numbers']:add('R42',{'paragraph':r['paragraph']},'caption_number',{k:r[k] for k in ('parsed','confirmed_chapter','chapter_heading','chapter_evidence')},'图/表按章编号并有标题文字',r['status'],'；'.join(r['reasons']))
  for i,r in enumerate(a['sequences'],1):add('R42',{'caption_sequence':i},'sequence',r['observed'],'完整范围内同章同类连续编号',r['status'],r['reason'])
 if s['template']['position']:
  for r in a['positions']:add('R43',{'paragraph':r['paragraph']},'caption_position',r.get('current_order',r['order']),r.get('target_order','明确图表关联'),'problem' if r['status']=='problem' else r['status'],r['reason']+'；L05须单独明确选择' if r['movable'] else r['reason'])
 for rid,opt in [('R42','numbering'),('R43','position')]:
  if s['template'][opt] and not any(f['rule_id']==rid for f in fs):add(rid,{'document':1},'scope',None,None,'not_applicable','没有确认题注；不推断缺少图表或题注')
 a['enabled']={k:s['template'][k] for k in ('numbering','position')}
 a['summary']={'numbering_problems':sum(r['status']=='problem' for r in a['numbers'])+sum(r['status']=='problem' for r in a['sequences']),'position_problems':sum(r['status']=='problem' for r in a['positions']),'complex_or_scope_reviews':len(a['unconfirmed_captions'])+sum(r['status']=='review' for r in a['numbers'])+sum(r['status']=='review' for r in a['positions'])+sum(r['status']=='review' for r in a['sequences']),'actual_pagination':'未核对'}
 if not s['template']['numbering']:a['summary']['numbering_problems']=None
 if not s['template']['position']:a['summary']['position_problems']=None
 report['captions']=a;report['coverage']['caption_scope']=deepcopy(s);report['coverage']['caption_limits']=LIMITS
 report['rules']['caption_supplement']={'name':s['template']['name'],'structure_version':1,'sha256':digest(s['template']),'source':SOURCE}
 report['summary']['rule_count']+=sum(s['template'][x] for x in ('numbering','position'))
 for state,name in [('problem','problem_count'),('pass','pass_count'),('not_applicable','not_applicable_count'),('review','review_findings')]:report['summary'][name]=sum(f['status']==state for f in fs)
 report['summary']['review_notes']=len(report['coverage_notes'])
 report['summary']['review_count']=report['summary']['review_findings']+len(report['coverage_notes']);report['summary']['applicable_rule_count']=len({f['rule_id'] for f in fs if f['status']!='not_applicable'})
 report['summary']['conclusion']='已覆盖检查发现问题' if report['summary']['problem_count'] else '已覆盖检查未发现问题'

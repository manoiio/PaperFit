"""R36/R37 opt-in note text. OPC validated; markers and system notes are immutable."""
from copy import deepcopy
from pathlib import Path
from posixpath import normpath
from urllib.parse import unquote
import json,math,re
from collections import Counter,defaultdict
from lxml import etree as E
from .package import Package,DemoError,parse,q,NS,sha256
from .formats import Resolver,Unresolved,scripts,same_font
KINDS={'footnote':'脚注','endnote':'尾注'}
FIELDS=('font_cn','font_size','line_multiple')
DEFAULT={'font_cn':'宋体','font_size':12,'line_multiple':1.5}
QUOTE='参考文献和注释正文为小四号，宋体，1.5倍行距。'
SOURCE={'label':'2015学校演示材料（Word普通注释对象解释）','file':'00-全员必看/本科毕业设计论文.pdf','physical_page':18,'quote':QUOTE}
LIMITS=['只覆盖确认的Word脚注/尾注普通文字；手工篇末注、正文括号说明和是否需要注释未检查。','正文引用与注释内部自动编号标记、系统分隔/延续分隔对象只读。','对象顺序及引用段落不是物理页码；格式通过不证明内容、引用语义或全文排版合格。','复杂结构按可证明粒度待复核，不解域、不改链接、编号、关系或共享样式。']
def digest(v):return sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode())
def text(e):return ''.join(e.xpath('.//w:t/text()',namespaces=NS))
def school():return {'structure_version':1,'kind':'paper-grid-note-supplement','name':'用户确认的注释演示规则','values':{k:deepcopy(DEFAULT) for k in KINDS},'sources':{k:{p:'school_default' for p in FIELDS} for k in KINDS}}
def template(d):
 if type(d) is not dict or set(d)!={'structure_version','kind','name','values','sources'} or type(d['structure_version']) is not int or d['structure_version']!=1 or d['kind']!='paper-grid-note-supplement' or type(d['name']) is not str or not 1<=len(d['name'])<=80 or any(c in d['name'] for c in '/\\\x00\n'):raise DemoError('注释补充配置版本或结构无效')
 for group in ('values','sources'):
  if type(d[group]) is not dict or set(d[group])!=set(KINDS):raise DemoError('注释配置对象字段无效')
  for kind in KINDS:
   if type(d[group][kind]) is not dict or set(d[group][kind])!=set(FIELDS):raise DemoError('注释配置含未知或缺失字段')
 for k in KINDS:
  for prop,v in d['values'][k].items():
   valid=v is None or (type(v) is str and v in ('宋体','黑体','楷体','仿宋') if prop=='font_cn' else type(v) in (int,float) and math.isfinite(v) and (8<=v<=24 and v*2==int(v*2) if prop=='font_size' else v in (1,1.25,1.5,2)))
   origin=d['sources'][k][prop]
   if not valid or origin not in ('school_default','user_confirmed','not_enabled') or (v is None)!=(origin=='not_enabled') or origin=='school_default' and v!=DEFAULT[prop]:raise DemoError('注释字段取值或来源无效；编辑后应记为用户确认值')
 return deepcopy(d)

def inventory(path):
 pkg=path if isinstance(path,Package) else Package(path);rows=[];systems=[];issues=[];partmap={};refs=[]
 try:relroot=parse(pkg.parts.get('word/_rels/document.xml.rels',b'<Relationships/>'))
 except (DemoError,E.XMLSyntaxError):relroot=E.Element('InvalidRelationships')
 ct=parse(pkg.parts['[Content_Types].xml']);top={p:i for i,p in enumerate(pkg.paragraphs,1)}
 relns='http://schemas.openxmlformats.org/package/2006/relationships';ctns='http://schemas.openxmlformats.org/package/2006/content-types'
 relvalid=relroot.tag=='{'+relns+'}Relationships' and all(e.tag=='{'+relns+'}Relationship' for e in relroot) and len({e.get('Id') for e in relroot})==len(relroot) and all(e.get('Id') for e in relroot)
 ctvalid=ct.tag=='{'+ctns+'}Types' and all(e.tag in ('{'+ctns+'}Override','{'+ctns+'}Default') for e in ct)
 def issue(kind,reason,**kw):issues.append({'kind':kind,'reason':reason,**kw})
 for k in KINDS:
  for e in pkg.root.iter(q(k+'Reference')):
   ps=next((a for a in e.iterancestors() if a.tag==q('p')),None)
   refs.append({'kind':k,'note_id':e.get(q('id')),'paragraph':top.get(ps),'location':'顶层段落' if ps in top else '嵌套/表格/未知位置（不改原段落编号）','custom_mark':e.get(q('customMarkFollows'))})
  rels=[r for r in relroot if r.get('Type')=='http://schemas.openxmlformats.org/officeDocument/2006/relationships/'+k+'s']
  if len(rels)>1:issue(k,'重复脚注/尾注关系，不能唯一确定部件');continue
  if not rels:
   if any(x['kind']==k for x in refs):issue(k,'有正文引用但缺少对应包关系（或关系XML损坏）')
   continue
  if not relvalid or not ctvalid:issue(k,'包关系/内容类型命名空间、结构或关系ID重复异常');continue
  rel=rels[0];target=unquote(rel.get('Target',''));member=normpath(target.lstrip('/') if target.startswith('/') else 'word/'+target)
  if rel.get('TargetMode')=='External' or not target or not member.startswith('word/') or '..' in target.split('/') or member not in pkg.parts:issue(k,'注释关系为外部、缺失或不支持路径');continue
  shared=[r for r in relroot if r.get('Type') in ['http://schemas.openxmlformats.org/officeDocument/2006/relationships/'+kind+'s' for kind in KINDS] and normpath(unquote(r.get('Target','')).lstrip('/') if unquote(r.get('Target','')).startswith('/') else 'word/'+unquote(r.get('Target','')))==member]
  if len(shared)!=1:issue(k,'多个注释关系共享同一部件，首版只读');continue
  types=[e.get('ContentType') for e in ct if e.get('PartName')=='/'+member]
  if types!=['application/vnd.openxmlformats-officedocument.wordprocessingml.'+k+'s+xml']:issue(k,'关系目标内容类型不匹配或重复',part=member);continue
  try:root=parse(pkg.parts[member])
  except (DemoError,E.XMLSyntaxError):issue(k,'注释部件XML损坏',part=member);continue
  if root.tag!=q(k+'s') or any(c.tag!=q(k) for c in root):issue(k,'注释根节点或包裹结构不支持',part=member);continue
  partmap[k]=member;objects=list(root);ids=Counter(e.get(q('id')) for e in objects)
  if len(objects)>5000 or len(refs)>10000:issue(k,'注释或引用数量超过本阶段安全上限，部件只读');continue
  links_by_id=defaultdict(list)
  for ref in refs:
   if ref['kind']==k:links_by_id[ref['note_id']].append(ref)
  for idx,note in enumerate(objects,1):
   ident=note.get(q('id'));typ=note.get(q('type'),'normal');key=f'{k}:{ident}:{idx}';links=links_by_id[ident];why=[]
   if ident is None or not re.fullmatch(r'(?:0|-[1-9]\d{0,9}|[1-9]\d{0,9})',ident):why.append('注释ID缺失或不支持')
   if ids[ident]>1:why.append('重复注释ID')
   if typ in ('separator','continuationSeparator','continuationNotice'):
    systems.append({'key':key,'kind':k,'note_id':ident,'type':typ,'part':member})
    if why:issue(k,'系统注释对象ID异常：'+'；'.join(why),note_id=ident)
    if links:issue(k,'系统注释对象被正文引用',note_id=ident)
    continue
   if typ!='normal':why.append('未知注释类型；不按ID正负猜用途')
   if len(links)!=1:why.append('正文引用缺失或重复，不能安全定位对应关系')
   if any(r['custom_mark'] not in (None,'0','false','off') for r in links):why.append('自定义引用标记，首版只读')
   marks=list(note.iter(q(k+'Ref')))
   if len(marks)!=1 or len(marks[0]) or marks[0].attrib:why.append('内部自动标记缺失、重复或异常')
   elif any(a.tag in {q(t) for t in ('ins','del','sdt','hyperlink','fldSimple')} for a in marks[0].iterancestors()):why.append('内部标记处于复杂包裹或修订中')
   complex_=note.xpath('.//w:tbl|.//w:sdt|.//w:fldChar|.//w:fldSimple|.//w:hyperlink|.//w:ins|.//w:del|.//*[local-name()="oMath"]',namespaces=NS)
   structures=[name for name,tag in [('链接','hyperlink'),('复杂域','fldChar'),('简单域','fldSimple'),('公式','oMath'),('表格','tbl'),('内容控件','sdt'),('插入修订','ins'),('删除修订','del')] if any(isinstance(e.tag,str) and E.QName(e).localname==tag for e in note.iter())]
   rows.append({'structures':structures,'key':key,'kind':k,'part':member,'note_id':ident,'note_index':idx,'type':typ,'preview':text(note)[:90],'references':links,'paragraphs':len(note.findall(q('p'))),'complex':bool(complex_),'reason':'；'.join(why) or '关系和类型明确；'+('含'+ '、'.join(structures)+'，复杂片段只读；普通run另查' if structures else '普通run可检查，自动编号标记只读'),'safe_relationship':not why})
  for ref in [x for x in refs if x['kind']==k]:
   if ids[ref['note_id']]!=1:issue(k,'正文引用未唯一对应注释对象',note_id=ref['note_id'],paragraph=ref['paragraph'])
 # A part merely present is not a valid relationship. Never treat it as a safe story.
 for e in ct:
  if e.get('ContentType') in ['application/vnd.openxmlformats-officedocument.wordprocessingml.'+k+'s+xml' for k in KINDS] and e.get('PartName','').lstrip('/') not in partmap.values():
   kind='footnote' if 'footnotes' in e.get('ContentType','') else 'endnote';issue(kind,'存在未关联或未通过校验的注释内容类型部件',part=e.get('PartName'))
 return {'input_sha256':pkg.hash,'objects':rows,'systems':systems,'issues':issues,'references':refs,'parts':partmap,'limits':LIMITS}

def make_scope(pkg):return {'input_sha256':pkg.hash,'objects':[],'confirmed':False,'confirmation':'注释范围草稿','template':school()}
def validate_scope(pkg,s,*,confirmed=True):
 if type(s) is not dict or set(s)!={'input_sha256','objects','confirmed','confirmation','template'} or s['input_sha256']!=pkg.hash:raise DemoError('注释范围结构或文件哈希不匹配')
 if type(s['confirmed']) is not bool or confirmed and not s['confirmed'] or type(s['confirmation']) is not str or not s['confirmation'].strip():raise DemoError('注释范围尚未明确确认')
 if type(s['objects']) is not list or any(type(x) is not str for x in s['objects']) or len(set(s['objects']))!=len(s['objects']) or set(s['objects'])-{r['key'] for r in inventory(pkg)['objects']}:raise DemoError('注释范围含未知对象、系统对象或重复选择')
 template(s['template']);return deepcopy(s)

def locate(pkg,f):
 part=f['story_part'];root=pkg.story_roots.setdefault(part,parse(pkg.parts[part]));return locate_root(root,f)
def locate_root(root,f):
 loc=f['locator'];note=list(root)[loc['note_index']-1];p=note.findall(q('p'))[loc['note_paragraph']-1];return p.findall(q('r'))[loc['run']-1] if 'run' in loc else p

def line_value(res,layers):
 for layer in layers:
  if len(layer.findall(q('spacing')))>1:raise Unresolved('重复spacing属性')
 a=res.attrs(layers,'spacing');raw=a.get('line');mode=a.get('lineRule','auto')
 if raw is None:raise Unresolved('行距未设置，不补默认单倍')
 try:v=int(raw)
 except (TypeError,ValueError):raise Unresolved('行距数值无效') from None
 if v<=0 or mode not in ('auto','exact','atLeast'):raise Unresolved('行距单位或数值不支持')
 return {'multiple':v/240 if mode=='auto' else None,'line_rule':mode,'pt':v/20 if mode!='auto' else None}

def append_checks(report,pkg,scope):
 s=validate_scope(pkg,scope);inv=inventory(pkg);fs=report['findings'];res=Resolver(pkg);cfg=s['template'];selected=set(s['objects']);marker_count=0;previews={(r['kind'],r['note_index']):r['preview'] for r in inv['objects']}
 def add(k,loc,prop,actual,status,reason='',safe=True,part=None):
  wanted=cfg['values'][k].get(prop);origin=cfg['sources'][k].get(prop);source=deepcopy(SOURCE) if origin=='school_default' else {'label':'用户确认的注释值' if origin=='user_confirmed' else '注释结构只读边界','quote':'用户确认值，不伪造学校原文' if origin=='user_confirmed' else reason}
  f={'key':('R36' if k=='footnote' else 'R37')+':'+':'.join(f'{a}={b}' for a,b in {**loc,'property':prop}.items()),'rule_id':'R36' if k=='footnote' else 'R37','rule_name':KINDS[k]+'普通文字 · '+{'font_cn':'中文字体','font_size':'字号','line_multiple':'倍数行距'}.get(prop,'结构与覆盖'),'object_type':k,'locator':{**loc,'property':prop},'actual':actual,'expected':wanted,'status':status,'fixable':status=='problem' and safe and not pkg.signed and not pkg.ambiguous_sections,'source':source,'detail':reason,'property':prop}
  if part:f['story_part']=part
  excerpt=previews.get((k,loc.get('note_index')))
  if excerpt:f['excerpt']=excerpt[:48]
  fs.append(f);return f
 for row in inv['objects']:
  if row['key'] not in selected:continue
  k=row['kind'];base={a:row[a] for a in ('note_id','note_index')};base['note_kind']=k;part=row['part'];root=parse(pkg.parts[part]);note=list(root)[row['note_index']-1];marker_count+=len(list(note.iter(q(k+'Ref'))))
  if not row['safe_relationship']:add(k,base,'structure',row['reason'],'review',row['reason'],False);continue
  # Fields may span paragraphs. Protect all text in a note with any field, but other notes stay actionable.
  field=bool(note.xpath('.//w:fldChar|.//w:fldSimple|.//w:instrText',namespaces=NS))
  if any(c.tag!=q('p') for c in note):add(k,base,'structure',None,'review','含表格、内容控件或其他非普通子对象；其内容只读，顶层普通段落另查',False)
  for pn,p in enumerate(note.findall(q('p')),1):
   loc={**base,'note_paragraph':pn};complex_p=field or any(c.tag not in (q('pPr'),q('r')) for c in p) or len(p.findall(q('pPr')))>1
   pl=[];paragraph_reason='段落含'+('、'.join(row['structures']) or '包裹、修订、编号依赖或未知结构')+'；行距不修，域缓存及复杂对象不检查'
   try:
    pl=res.layers(p,kind='pPr')
    if any(x.find(q('pPrChange')) is not None or x.find(q('sectPr')) is not None or x.find(q('framePr')) is not None or x.find(q('numPr')) is not None for x in pl):complex_p=True
   except Unresolved as exc:complex_p=True;paragraph_reason=str(exc)+'；继承不可靠，行距不修'
   if complex_p:add(k,loc,'structure',None,'review',paragraph_reason,False)
   if cfg['values'][k]['line_multiple'] is not None:
    try:
     if complex_p:raise Unresolved(paragraph_reason)
     for run in p.findall(q('r')):
      if len(run.findall(q('rPr')))>1:raise Unresolved('重复run格式')
      for c in run:
       if c.tag not in {q(x) for x in ('rPr','t','tab','br','cr',k+'Ref')}:raise Unresolved('段落含未支持的文字/编号结构')
       if c.tag==q('br') and c.get(q('type'),'textWrapping')!='textWrapping':raise Unresolved('强制分页/分栏保留，行距待复核')
      rl=res.layers(p,run)
      if run.find(q(k+'Ref')) is None and res.special(run,rl):raise Unresolved('段落含特殊文字；行距待复核')
     if any(sec.find(q('docGrid')) is not None and sec.find(q('docGrid')).get(q('type')) not in (None,'default') for sec in pkg.sections) and res.value(pl,'snapToGrid','1') not in ('0','false','off'):raise Unresolved('文档网格可能影响注释行距，待复核')
     actual=line_value(res,pl);add(k,loc,'line_multiple',actual,'pass' if actual['multiple']==cfg['values'][k]['line_multiple'] else 'problem',part=part)
    except (Unresolved,ValueError) as exc:add(k,loc,'line_multiple',{'unresolved':str(exc)},'review',str(exc),False)
   for ri,r in enumerate(p.findall(q('r')),1):
    rl={**loc,'run':ri}
    if r.find(q(k+'Ref')) is not None:
     if text(r).strip():add(k,rl,'protected_marker',None,'review','编号标记与正文混在同一run；仅此片段不修字体字号，不拆标记',False)
     continue
    if not text(r).strip():continue
    try:
     layers=res.layers(p,r)
     why='域缓存及边界只读' if field else '修订/未知格式容器' if len(r.findall(q('rPr')))>1 else res.special(r,layers)
     if p.find('w:pPr/w:pPrChange',NS) is not None:why='段落格式修订只读'
     if scripts(text(r))[2]:why='超出普通中文/Latin文字支持的字符，保持原状'
     if why:raise Unresolved(why)
    except Unresolved as exc:add(k,rl,'protected_run',None,'review',str(exc),False);continue
    for prop in ('font_cn','font_size'):
     wanted=cfg['values'][k][prop]
     if wanted is None or prop=='font_cn' and not scripts(text(r))[0]:continue
     try:
      if prop=='font_cn':
       ev=res.font_info(layers,'eastAsia',text(r));actual=ev['font']
       if actual is None:raise Unresolved(ev['reason'])
       f=add(k,rl,prop,{'eastAsia':actual},'pass' if same_font(actual,wanted) else 'problem',safe=ev['safe_to_fix_slot'],part=part);f['font_evidence']={'eastAsia':ev}
      else:
       actual=res.size(layers)
       if actual is None:raise Unresolved('字号缺失或无效')
       add(k,rl,prop,{'pt':actual},'pass' if actual==wanted else 'problem',part=part)
     except Unresolved as exc:add(k,rl,prop,{'unresolved':str(exc)},'review',str(exc),False)
 for i,x in enumerate(inv['issues'],1):add(x['kind'],{'note_kind':x['kind'],'relation_issue':i},'relationship',x,'review',x['reason'],False)
 for k,rid in [('footnote','R36'),('endnote','R37')]:
  if not any(f['rule_id']==rid for f in fs):add(k,{'note_kind':k},'structure',None,'not_applicable','没有所选可适用Word注释；不判缺少注释',False)
 report['coverage']['note_scope']=s;report['coverage']['note_limits']=LIMITS
 report['notes']={'inventory':inv,'selected':s['objects'],'automatic_markers_preserved':marker_count,'system_objects_readonly':len(inv['systems']),'limits':LIMITS}
 report['rules']['note_supplement']={'name':cfg['name'],'version':1,'sha256':digest(cfg),'values':deepcopy(cfg['values']),'sources':deepcopy(cfg['sources'])}
 report['summary']['rule_count']+=2
 for status,n in [('problem','problem_count'),('review','review_findings'),('pass','pass_count'),('not_applicable','not_applicable_count')]:report['summary'][n]=sum(f['status']==status for f in fs)
 report['summary']['review_count']=report['summary']['review_findings']+len(report['coverage_notes']);report['summary']['applicable_rule_count']=len({f['rule_id'] for f in fs if f['status']!='not_applicable'});report['summary']['conclusion']='已覆盖检查发现问题' if report['summary']['problem_count'] else '已覆盖检查未发现问题'

def apply(pkg,f):
 from .engine import _ensure
 e=locate(pkg,f);prop=f['property'];rpr=prop!='line_multiple';container=_ensure(e,'rPr' if rpr else 'pPr')
 if prop=='font_cn':rf=_ensure(container,'rFonts');rf.set(q('eastAsia'),f['expected']);rf.attrib.pop(q('eastAsiaTheme'),None)
 elif prop=='font_size':_ensure(container,'sz').set(q('val'),str(round(f['expected']*2)))
 else:sp=_ensure(container,'spacing');sp.set(q('line'),str(round(f['expected']*240)));sp.set(q('lineRule'),'auto')
def mask_story(root,f):
 el=locate_root(root,f);prop=f['property'];tag='rFonts' if prop=='font_cn' else 'sz' if prop=='font_size' else 'spacing';e=el.find('w:'+('pPr' if prop=='line_multiple' else 'rPr')+'/w:'+tag,NS)
 if e is not None:
  for a in ('eastAsia','eastAsiaTheme') if prop=='font_cn' else ('val',) if prop=='font_size' else ('line','lineRule'):e.attrib.pop(q(a),None)
 for e in reversed(list(el.iter())):
  if e.tag in {q(x) for x in ('rFonts','sz','spacing','rPr','pPr')} and not len(e) and not e.attrib and not e.text:e.getparent().remove(e)

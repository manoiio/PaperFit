"""R24-R29 opt-in cover/section/story checks. PAGE is always read-only."""
from copy import deepcopy
from pathlib import Path
from posixpath import normpath
from urllib.parse import unquote
import re,json
from lxml import etree as E
from .package import Package,DemoError,q,NS,parse,sha256
from .formats import Resolver,Unresolved,paragraph_unsafe,scripts,same_font
from .paragraph_properties import alignment,bold
from .front_template import validate as template_validate,digest,school
from .table_text import tables,text,_layers
IDS={'R24','R25','R26','R27','R28','R29'}
ROLES={'pending':'待确认','cover':'封面','front':'前置部分','body':'正文及后置部分','other':'其他','mixed':'混合用途'}
FIELDS={'title':'论文标题','name':'姓名','student_id':'学号','college':'学院','major':'专业','supervisor':'指导教师','date':'日期','other':'其他字段'}
LABELS={'font_cn':'中文字体','font_western':'西文字体','font_size':'字号','bold':'加粗','alignment':'对齐','header_distance_mm':'页眉距离','footer_distance_mm':'页脚距离'}
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
def nodes(pkg):
 rows=[]
 for i,p in enumerate(pkg.paragraphs,1):rows.append((f'p:{i}',{'paragraph':i},p,None))
 for ti,t in enumerate(tables(pkg),1):
  if t.find('.//'+q('tbl')) is not None:continue
  for ri,row in enumerate(t.findall(q('tr')),1):
   for ci,c in enumerate(row.findall(q('tc')),1):
    for pi,p in enumerate(c.findall(q('p')),1):rows.append((f't:{ti}:{ri}:{ci}:{pi}',{'table':ti,'row':ri,'cell':ci,'cell_paragraph':pi},p,t))
 return rows

def fields(root):
 """Ordered simple and balanced complex fields, with saved results; never evaluate."""
 result=[];stack=[]
 for e in root.iter():
  if e.tag==q('fldSimple'):
   result.append({'instruction':e.get(q('instr'),''),'saved_result':text(e),'representation':'simple','balanced':not bool(e.findall('.//'+q('fldChar')))})
  elif e.tag==q('fldChar'):
   typ=e.get(q('fldCharType'))
   if typ=='begin':stack.append({'instruction':'','saved_result':'','representation':'complex','balanced':True,'phase':'instruction','nested':bool(stack)})
   elif typ=='separate':
    if stack:stack[-1]['phase']='result'
    else:result.append({'instruction':'','saved_result':'','representation':'complex','balanced':False})
   elif typ=='end':
    if stack:
     f=stack.pop();f.pop('phase',None)
     if f.pop('nested',False) or stack:f['balanced']=False
     result.append(f)
    else:result.append({'instruction':'','saved_result':'','representation':'complex','balanced':False})
  elif e.tag==q('instrText') and stack:stack[-1]['instruction']+=e.text or ''
  elif e.tag==q('t') and stack and stack[-1]['phase']=='result':stack[-1]['saved_result']+=e.text or ''
 for f in stack:f.pop('phase',None);f.pop('nested',None);f['balanced']=False;result.append(f)
 for f in result:f['is_page']=bool(re.match(r'^\s*PAGE(?:\s|$)',f['instruction'],re.I))
 return result

def section_inventory(pkg):
 body=list(pkg.root.find(q('body')));out=[];previous={};last=0;rels={};errors=[]
 try:
  root=parse(pkg.parts.get('word/_rels/document.xml.rels',b'<Relationships/>'))
  for e in root:
   ident=e.get('Id')
   if ident in rels:raise Unresolved('重复包关系ID')
   rels[ident]=e
 except (DemoError,Unresolved,E.XMLSyntaxError) as exc:errors.append(str(exc))
 settings=parse(pkg.parts['word/settings.xml']) if 'word/settings.xml' in pkg.parts else E.Element(q('settings'))
 es=settings.findall(q('evenAndOddHeaders'));odd=None if len(es)>1 else bool(es and es[0].get(q('val'),'1') not in ('0','false','off'))
 for n,s in enumerate(pkg.sections,1):
  obj=s if s.getparent().tag==q('body') else s.getparent().getparent();end=body.index(obj)+1 if obj in body else None
  refs={};ref_errors=list(errors)
  for kind in ('header','footer'):
   for variant in ('default','first','even'):
    key=kind+':'+variant;hits=[e for e in s.findall(q(kind+'Reference')) if e.get(q('type'))==variant]
    if len(hits)>1:ref_errors.append('重复'+key+'引用');refs[key]={'error':'重复引用'};continue
    if not hits:
     refs[key]={**deepcopy(previous.get(key,{'part':None,'defined_section':None})),'linked_previous':n>1}
     continue
    rid=hits[0].get('{'+R+'}id');rel=rels.get(rid)
    target=unquote(rel.get('Target','')) if rel is not None else ''
    path=normpath('word/'+target) if target and not target.startswith('/') else target.lstrip('/')
    if rel is None or rel.get('Type')!=R+'/'+kind or rel.get('TargetMode')=='External' or path not in pkg.parts or not re.fullmatch(r'word/(?:header|footer)[\w-]*\.xml',path):
     refs[key]={'error':'故事关系缺失、外部或非标准路径'};ref_errors.append(key+'关系不支持');continue
    try:
     story=parse(pkg.parts[path]);expected=q('hdr' if kind=='header' else 'ftr')
     if story.tag!=expected:raise DemoError('故事根节点类型错误')
     complex_=bool(story.xpath('.//w:pict|.//w:drawing|.//w:sdt|.//w:ins|.//w:del|.//w:object|.//w:tbl',namespaces=NS))
     refs[key]={'part':path,'defined_section':n,'linked_previous':False,'ordinary_text':bool(text(story).strip()),'complex_objects':complex_,'fields':fields(story),'paragraphs':len(story.findall(q('p')))}
    except (DemoError,E.XMLSyntaxError):refs[key]={'error':'故事XML损坏'};ref_errors.append(key+'XML损坏')
  for e in s:
   if e.tag in (q('headerReference'),q('footerReference')) and e.get(q('type')) not in ('default','first','even'):ref_errors.append('不支持的故事变体')
  pp=s.findall(q('pgMar'));sz=s.find(q('pgSz'));title=s.findall(q('titlePg'));num=s.findall(q('pgNumType'))
  def attrs(e):return {E.QName(k).localname:v for k,v in e.attrib.items()} if e is not None else {}
  valid_range=end is not None and not pkg.ambiguous_sections
  out.append({'index':n,'body_objects':{'start':last+1,'end':end} if valid_range else None,'paragraphs':[i for i,p in enumerate(pkg.paragraphs,1) if valid_range and last< body.index(p)+1<=end], 'page':attrs(sz),'margins':attrs(pp[0]) if len(pp)==1 else {},'first_page_different':bool(title and title[0].get(q('val'),'1') not in ('0','false','off')),'odd_even_different':odd,'references':refs,'errors':ref_errors+(['重复节页边距、页码或首页属性'] if len(pp)>1 or len(num)>1 or len(title)>1 else []),'page_numbering':attrs(num[0]) if len(num)==1 else {},'page_numbering_count':len(num)})
  previous=refs;last=end or last
 return out

def inventory(path):
 pkg=Package(path);objects=[]
 for key,loc,p,t in nodes(pkg):
  tx=text(p);compact=re.sub(r'\s','',tx);candidates=[f for f,pat in [('name','(?:学生)?姓名'),('student_id','(?:学生)?学号'),('college','学院'),('major','专业'),('supervisor','指导教师'),('date','(?:提交)?日期')] if re.match('^'+pat,compact)]
  objects.append({'id':key,'locator':loc,'text':tx[:100],'candidates':candidates,'special':paragraph_unsafe(p),'in_table':t is not None})
 return {'input_sha256':pkg.hash,'cover_objects':objects,'sections':section_inventory(pkg),'indexing':'段落为顶层编号；封面表格使用实际XML表/行/格/段落编号；节范围为XML对象，不是物理页码'}

def make_scope(path):
 inv=inventory(path)
 return {'input_sha256':inv['input_sha256'],'confirmed':False,'confirmation':'尚未核对','objects':{},'section_roles':{str(s['index']):'pending' for s in inv['sections']},'template':school()}

def validate_scope(pkg,s,*,confirmed=True):
 if type(s) is not dict or set(s)!={'input_sha256','confirmed','confirmation','objects','section_roles','template'} or s['input_sha256']!=pkg.hash:raise DemoError('封面/节清单结构或文件哈希不匹配')
 if type(s['confirmed']) is not bool or confirmed and not s['confirmed'] or type(s['confirmation']) is not str or not 0<len(s['confirmation'])<=160:raise DemoError('封面与节范围须人工核对确认')
 template_validate(s['template']);allnodes={k for k,_,_,_ in nodes(pkg)}
 if type(s['objects']) is not dict or any(type(k) is not str or k not in allnodes or type(v) is not str or v not in FIELDS for k,v in s['objects'].items()):raise DemoError('封面定位或字段类型无效；嵌套表格/文本框不支持')
 if type(s['section_roles']) is not dict or set(s['section_roles'])!={str(i) for i in range(1,len(pkg.sections)+1)} or any(type(v) is not str or v not in ROLES for v in s['section_roles'].values()):raise DemoError('节用途须完整且合法')
 return deepcopy(s)

def source(scope,n=None,page=19,quote=''):
 s=scope['template']['sources'].get(n) if n else None
 if s and s['kind']!='school_demo':return {'label':{'user_confirmed':'用户确认值','ai_extracted':'历史AI提取后用户确认','not_enabled':'未启用'}[s['kind']],'quote':s['quote'],'location':s['location'],'physical_page':None,'file':None}
 return {'label':'2015学校演示原文；非现行标准','file':'00-全员必看/本科毕业设计论文.pdf','physical_page':17 if n and n.startswith('cover') else page,'quote':s['quote'] if s else quote}

def append_checks(report,pkg,scope):
 scope=validate_scope(pkg,scope);res=Resolver(pkg);cfg=scope['template']['values'];fs=report['findings'];before=len(fs);secs=section_inventory(pkg);selected={int(n) for n,v in scope['section_roles'].items() if v!='pending'}
 def add(rid,loc,prop,actual,expected,status,reason='',safe=False,n=None,obj=None):
  loc={**loc,'property':prop};f={'key':rid+':'+':'.join(f'{k}={v}' for k,v in loc.items()),'rule_id':rid,'rule_name':{'R24':'封面论文标题格式','R25':'封面字段核对（只读）','R26':'页眉页脚距离','R27':'普通页眉页脚文字','R28':'页眉结构与内容模式（只读）','R29':'页码基础检查（只读）'}[rid]+' · '+LABELS.get(prop,prop),'locator':loc,'object_type':obj or ('cover_title' if rid=='R24' else 'section_story'),'property':prop,'actual':actual,'expected':expected,'status':status,'fixable':status=='problem' and safe and not pkg.signed and not pkg.ambiguous_sections,'source':source(scope,n,page=17 if rid in ('R24','R25') else 19,quote='封面范例字段仅供人工核对，不补造个人资料。' if rid=='R25' else '页眉分奇偶页；页码从主体开始连续编写，前置罗马数字，封面不编页码。'),'detail':reason};fs.append(f);return f
 def read(rid,loc,prop,fn,target,*,n=None,safe=False,eq=lambda a,b:a==b):
  try:
   a=fn()
   if a is None:raise Unresolved('有效值缺失，不补默认')
   return add(rid,loc,prop,a,target,'pass' if eq(a,target) else 'problem',safe=safe,n=n)
  except (Unresolved,ValueError,TypeError) as e:return add(rid,loc,prop,{'unresolved':str(e)},target,'review',str(e)+'；请在Word核对继承/复杂对象',n=n)
 def ordinary(p,loc,obj,rid,t=None,allow=True,allow_school=True):
  why=paragraph_unsafe(p)
  if len(p.findall(q('pPr')))>1:why='重复段落格式容器'
  if t is not None and (t.xpath('.//w:tbl|.//w:ins|.//w:del|.//w:sdt|.//w:tblpPr|.//w:tcPrChange|.//w:trPrChange',namespaces=NS)):why='复杂、嵌套或修订表格'
  if t is not None:
   cell=p.getparent();vm=cell.find('w:tcPr/w:vMerge',NS) if cell.tag==q('tc') else None
   if vm is not None and vm.get(q('val'),'continue')!='restart':why='纵向合并续格，无法保证该内容是独立可见对象'
  if why:add(rid,loc,'structure',why,None,'review','整个段落未修正；确认不能绕过结构保护');return
  target=cfg[obj+'__alignment']
  if not allow_school and scope['template']['sources'][obj+'__alignment']['kind']=='school_demo':target=None
  if target is not None:
   try:
    if any(res.special(r,res.layers(p,r)) for r in p.findall(q('r'))):raise Unresolved('含特殊片段，不改整段对齐')
    if t is not None and any(st.find(q('pPr')) is not None or c.find(q('pPr')) is not None for st in res.chain((t.find('w:tblPr/w:tblStyle',NS).get(q('val')) if t.find('w:tblPr/w:tblStyle',NS) is not None else res.default_styles.get('table')),'table') for c in [st,*st.findall(q('tblStylePr'))]):raise Unresolved('表格条件段落格式不能唯一确定')
    read(rid,loc,'alignment',lambda:alignment(res,res.layers(p,kind='pPr')),target,n=obj+'__alignment',safe=allow)
   except Unresolved as e:add(rid,loc,'alignment',str(e),target,'review',str(e))
  for i,r in enumerate(p.findall(q('r')),1):
   tx=text(r)
   if not tx.strip():continue
   rl={**loc,'run':i}
   try:
    layers=res.layers(p,r)
    if len(r.findall(q('rPr')))>1:raise Unresolved('重复文字格式容器')
    why=res.special(r,layers)
    if why:raise Unresolved(why)
   except Unresolved as e:add(rid,rl,'structure',str(e),None,'review','特殊文字未检查、未修正：'+str(e));continue
   cn,west,unknown=scripts(tx)
   props=('font_cn','font_size','bold') if obj=='cover_title' else ('font_cn','font_western','font_size')
   for prop in props:
    n=obj+'__'+prop;target=cfg[n]
    if not allow_school and scope['template']['sources'][n]['kind']=='school_demo':target=None
    if target is None or prop=='font_cn' and not cn or prop=='font_western' and not west:continue
    try:
     effective=_layers(res,t,p,r,'font_cn' if prop=='font_cn' else 'font_size') if t is not None else layers
     if t is not None and prop=='bold' and any(st.findall('w:tblStylePr/w:rPr/w:b',NS) for st in res.styles.values()):raise Unresolved('表格条件加粗无法唯一确定')
     why=res.special(r,effective)
     if why:raise Unresolved(why)
     if prop.startswith('font_') and prop!='font_size':
      slots=['eastAsia'] if prop=='font_cn' else [x for x in ('ascii','hAnsi') if x in west]
      if not slots:continue
      proof={slot:res.font_info(effective,slot,tx) for slot in slots}
      if any(p['font'] is None for p in proof.values()):raise Unresolved(';'.join(p.get('reason','') for p in proof.values() if p['font'] is None))
      actual={slot:p['font'] for slot,p in proof.items()};f=add(rid,rl,prop,actual,target,'pass' if all(same_font(v,target) for v in actual.values()) else 'problem',safe=allow and all(p['safe_to_fix_slot'] for p in proof.values()),n=n);f['font_evidence']=proof
     else:read(rid,rl,prop,lambda:res.size(effective) if prop=='font_size' else bold(res,effective),target,n=n,safe=allow)
     fs[-1]['excerpt']=tx[:48]
    except Unresolved as e:add(rid,rl,prop,str(e),target,'review',str(e),n=n)
   if unknown:add(rid,rl,'character_boundary','未支持文字槽位',None,'review','字号或加粗检查不证明字体全部可判定')
 for key,loc,p,t in nodes(pkg):
  typ=scope['objects'].get(key)
  if typ=='title':
   title_text=text(p).strip()
   if not title_text or re.fullmatch(r'[\s_＿—－:：]*(?:待填(?:写)?|请输入(?:论文)?标题|论文标题|论文题目|XXX)?[\s_＿—－:：]*',title_text,re.I):
    add('R25',loc,'title_content','空白或标题占位','人工填写/核对真实标题','review','只读提示；不补造标题，不用空段对齐代表标题合格',obj='cover_field')
    add('R24',loc,'structure','标题文字未确认',None,'review','先人工核对实际标题，当前不自动套格式')
   else:ordinary(p,loc,'cover_title','R24',t)
  elif typ:
   tx=text(p).strip();blank=not tx or bool(re.fullmatch(r'[\s_＿—－:：年月日]*(?:待填|待填写|请输入|XXX|×××)?[\s_＿—－:：年月日]*',tx,re.I)) or bool(re.fullmatch(r'(?:学生)?(?:姓名|学号|学院|专业|指导教师|提交日期|日期)[\s_＿—－:：年月日]*(?:待填|XXX)?',re.sub(r'\s','',tx),re.I))
   blank=blank or bool(re.search(r'待填|请输入|XXX|×××',tx,re.I))
   add('R25',loc,typ,'空白/标签/占位，未证明已填写' if blank else '已确认字段有文字，真实性未核验','人工核对'+FIELDS[typ],'review','只读提示，不补造内容；相邻单元格标签/值需分别确认。',obj='cover_field')
 for typ in FIELDS:
  count=list(scope['objects'].values()).count(typ)
  if typ!='other' and count!=1:add('R25',{'document':1},'candidates_'+typ,count,'一个经人工核对的'+FIELDS[typ],'review',('未确认候选不等于实际缺少字段；只覆盖明确普通段落/普通表格' if not count else '多个候选，请核对，不擅自选最后一项'),obj='cover_field')
 for sec in secs:
  sn=sec['index'];role=scope['section_roles'][str(sn)]
  if role=='pending':continue
  loc={'section':sn}
  for n,a in [('header_distance_mm','header'),('footer_distance_mm','footer')]:
   target=cfg[n]
   if target is None:continue
   def dist():
    if sec['errors'] or sec['body_objects'] is None:raise Unresolved('节属性/对象范围有冲突')
    raw=sec['margins'].get(a)
    if raw is None or not re.fullmatch(r'\d+',raw):raise Unresolved('节距离缺失或非有效非负twip')
    return int(raw)*25.4/1440
   read('R26',loc,n,dist,target,n=n,safe=True,eq=lambda a,b:abs(a-b)<.03)
  active=['default']+(['first'] if sec['first_page_different'] else [])+(['even'] if sec['odd_even_different'] else [])
  if sec['errors']:add('R28',loc,'relationships',sec['errors'],None,'review','关系异常，不修正故事；普通距离也保守阻止')
  if role=='mixed':add('R29',loc,'mixed_use','一节混合用途',None,'review','不能按段落推算物理页码，不拆节、不重建编号');continue
  if role in ('cover','front') and any(sec['references']['header:'+v].get('ordinary_text') or sec['references']['header:'+v].get('complex_objects') for v in active):add('R28',loc,'header_outside_body','此用途节配置页眉内容','学校原文从主体部分开始标注页眉','review','只读核对；不删除页眉，不猜测实际页数、首页或奇偶显示')
  if role=='body':
   add('R28',loc,'odd_even',sec['odd_even_different'],True,'pass' if sec['odd_even_different'] is True else 'review' if sec['odd_even_different'] is None else 'problem','只读，不重建奇偶页结构')
   even=sec['references']['header:even'];part=even.get('part');even_text=text(parse(pkg.parts[part])) if part else ''
   add('R28',loc,'even_header_content',even_text[:80] or '无可读内容','华南理工大学学士学位论文','pass' if not even.get('complex_objects') and not even.get('fields') and even_text.strip()=='华南理工大学学士学位论文' and sec['odd_even_different'] else 'review','不替换文字；章序章标题及1磅横线另需人工核对')
  page_records=[]
  for kind in ('header','footer'):
   for variant in active:
    ref=sec['references'][kind+':'+variant];part=ref.get('part')
    if ref.get('error'):add('R29',{**loc,'story':kind+':'+variant},'page_field',ref['error'],None,'review','不能证明字段缺失');continue
    if not part:
     if kind=='footer' and role in ('front','body'):add('R29',{**loc,'story':kind+':'+variant},'page_variant_presence','此活动变体没有可读故事关系','人工核对是否实际使用及PAGE位置','review','未发现不等于已确定缺失；不猜测此节实际页数、奇偶或首页覆盖')
     continue
    root=parse(pkg.parts[part]);ps=root.findall(q('p'));affected=[s['index'] for s in secs if any(r.get('part')==part for r in s['references'].values())]
    safe=set(affected)<=selected and all(scope['section_roles'][str(n)] not in ('mixed','pending') for n in affected) and not ref.get('complex_objects') and not sec['errors']
    if ref.get('complex_objects'):add('R27',{**loc,'story':kind+':'+variant},'structure','图片、VML、表格、文本框或修订对象',None,'review','复杂故事不整体重写；其中普通文字可能只读检查，复杂对象和关系保持')
    for pn,p in enumerate(ps,1):
     locp={'section':sn,'story':kind+':'+variant,'story_paragraph':pn}
     if text(p).strip():
      start=len(fs);ordinary(p,locp,kind+'_text','R27',allow=safe,allow_school=role=='body')
      for f in fs[start:]:
       f['story_part']=part;f['affected_sections']=affected
       if len(affected)>1:f['detail']+='；该故事共享于已列出的节'+','.join(map(str,affected))+'，所选属性会同时影响这些节；本阶段不自动断链。'
       if not safe:f['detail']+='；共享部件影响未选/混合节，或故事含复杂对象；不自动断链、复制或整体重写'
    for f in ref.get('fields',[]):
     if f['is_page'] or not f['balanced']:
      rec={**f,'story':kind+':'+variant,'part':part};page_records.append(rec)
      add('R29',{**loc,'story':kind+':'+variant,'field':len(page_records)},'page_field',{k:v for k,v in rec.items() if k!='part'},'只读PAGE字段；显示结果可能陈旧','review','字段存在不代表页码准确；不计算域，不根据保存数字判断实际页号')
  # Inspect only cached PAGE result runs, never instructions or arbitrary 'PAGE' text.
  for kind in ('header','footer'):
   for variant in active:
    part=sec['references'][kind+':'+variant].get('part')
    if not part:continue
    root=parse(pkg.parts[part])
    for pn,p in enumerate(root.findall(q('p')),1):
     if not any(f['is_page'] for f in fields(p)):continue
     result_runs=[];complex_stack=[];ambiguous=False
     for child in p:
      if child.tag==q('fldSimple'):
       if re.match(r'^\s*PAGE(?:\s|$)',child.get(q('instr'),''),re.I):result_runs.extend(child.findall(q('r')))
       continue
      if child.tag!=q('r'):continue
      fc=child.find(q('fldChar'))
      if fc is not None:
       typ=fc.get(q('fldCharType'))
       if typ=='begin':complex_stack.append({'instruction':'','result':False});ambiguous|=len(complex_stack)>1
       elif typ=='separate' and complex_stack:complex_stack[-1]['result']=True
       elif typ=='end' and complex_stack:complex_stack.pop()
       else:ambiguous=True
      elif complex_stack:
       f=complex_stack[-1]
       if not f['result']:f['instruction']+=''.join(child.xpath('./w:instrText/text()',namespaces=NS))
       elif re.match(r'^\s*PAGE(?:\s|$)',f['instruction'],re.I) and text(child):result_runs.append(child)
     if ambiguous or complex_stack:
      add('R29',{**loc,'story':kind+':'+variant,'story_paragraph':pn},'page_result_format','复杂/不平衡域',None,'review','编号符号格式无法可靠确定');continue
     for ri,r in enumerate(result_runs,1):
      try:
       layers=res.layers(p,r);actual=res.size(layers)
       if res.special(r,layers) or actual is None:raise Unresolved('页码保存结果特殊或字号未确定')
       add('R29',{**loc,'story':kind+':'+variant,'story_paragraph':pn,'field_result_run':ri},'page_font_size',actual,10.5,'pass' if actual==10.5 else 'problem','只读保存结果字号；不重建域、不证明实际分页')
      except Unresolved as e:add('R29',{**loc,'story':kind+':'+variant,'story_paragraph':pn,'field_result_run':ri},'page_font_size',str(e),10.5,'review','不能自动改域结果')
  setting=sec['page_numbering'];fmt=setting.get('fmt','decimal');num_known=sec['page_numbering_count']<=1 and not sec['errors'];wanted='Roman/roman' if role=='front' else 'decimal' if role=='body' else '封面不编页码' if role=='cover' else None
  if role in ('front','body'):
   ok=fmt in ('upperRoman','lowerRoman') if role=='front' else fmt=='decimal'
   add('R29',loc,'number_format',{'format':fmt,'explicit':bool(setting.get('fmt'))},wanted,'pass' if num_known and ok else 'problem' if num_known else 'review','仅编号设置；未显式fmt按OOXML decimal默认，不证明连续性')
   add('R29',loc,'number_start',{'start':setting.get('start'),'mode':'明确重启' if 'start' in setting else '未声明重启，沿用连续编号意图'},'按用途人工核对重启与跨节连续性','review','没有物理布局不证明连续或准确；start异常/多个节重启也须核对')
   if not page_records:add('R29',loc,'page_presence','所列活动故事未发现可识别PAGE','人工核对','review','不等于已确定缺失；可能在不支持结构或复杂域中')
   add('R29',loc,'page_position','学校页19居中、页20主体外侧下脚存在冲突','用户确认位置要求','review','本阶段不制造唯一官方标准，不自动重建页码位置')
  elif role=='cover':add('R29',loc,'cover_page_field',len(page_records),'活动故事无PAGE','problem' if page_records else 'pass','只检查可读活动故事；不证明封面物理页一定无页码，不删除字段')
 for i,f in enumerate(fields(pkg.root),1):
  if f['is_page'] or not f['balanced']:add('R29',{'document':1,'main_field':i},'main_page_field',f,'人工核对所在页与用途','review','主文档域含文本框等位置，本阶段不推算物理页码，不改域')
 for rid in sorted(IDS):
  if not any(f['rule_id']==rid for f in fs[before:]):add(rid,{'document':1},'scope',None,None,'not_applicable','未确认此对象、无支持的普通文字或模板属性未启用')
 report['coverage']['front_scope']=deepcopy(scope);report['coverage']['section_inventory']=secs
 report['coverage']['front_limits']=['封面字段仅普通段落/非嵌套表格定位；不校验个人资料真实性，不发送外部API。','节对象范围不是物理页码；PAGE字段与保存结果不证明页码准确；不重建字段/分节。','复杂故事、共享到未选节的故事不自动修改；VML和OLE保留，原真实课程论文裁切仍是渲染限制。','打印人工清单：封面学校标题蓝色、210g/m²橙色封面纸、单/双面与装订；电子属性不能证明满足。','页眉章标题、横线粗细及位置未完整自动校验；学校页19/20页码位置冲突须人工决定。']
 report['rules']['front_supplement']={'name':scope['template']['name'],'version':1,'sha256':digest(scope['template']),'values':deepcopy(cfg),'sources':deepcopy(scope['template']['sources'])}
 report['summary']['rule_count']+=len(IDS)
 for status,n in [('problem','problem_count'),('review','review_findings'),('pass','pass_count'),('not_applicable','not_applicable_count')]:report['summary'][n]=sum(f['status']==status for f in fs)
 report['summary']['review_count']=report['summary']['review_findings']+len(report['coverage_notes']);report['summary']['review_notes']=len(report['coverage_notes']);report['summary']['applicable_rule_count']=len({f['rule_id'] for f in fs if f['status']!='not_applicable'});report['summary']['conclusion']='已覆盖检查发现问题' if report['summary']['problem_count'] else '已覆盖检查未发现问题'

def locate(pkg,loc,part=None):
 if part:
  root=pkg.story_roots.setdefault(part,parse(pkg.parts[part]));p=root.findall(q('p'))[loc['story_paragraph']-1]
 elif 'table' in loc:
  p=tables(pkg)[loc['table']-1].findall(q('tr'))[loc['row']-1].findall(q('tc'))[loc['cell']-1].findall(q('p'))[loc['cell_paragraph']-1]
 else:p=pkg.paragraphs[loc['paragraph']-1]
 return p.findall(q('r'))[loc['run']-1] if 'run' in loc else p

def attribute(f):
 prop=f['property']
 return ('pgMar',[('header' if prop.startswith('header') else 'footer')]) if f['rule_id']=='R26' else ('jc',['val']) if prop=='alignment' else ('b',['val']) if prop=='bold' else ('sz',['val']) if prop=='font_size' else ('rFonts',['eastAsia','eastAsiaTheme']) if prop=='font_cn' else ('rFonts',[a for x in f['actual'] for a in (x,x+'Theme')])

def apply(pkg,f):
 from .engine import _ensure
 tag,attrs=attribute(f)
 if f['rule_id']=='R26':_ensure(pkg.sections[f['locator']['section']-1],tag).set(q(attrs[0]),str(round(f['expected']*1440/25.4)));return
 el=locate(pkg,f['locator'],f.get('story_part'));container=_ensure(el,'rPr' if 'run' in f['locator'] else 'pPr');target=_ensure(container,tag)
 for a in attrs:
  if a.endswith('Theme'):target.attrib.pop(q(a),None)
  else:target.set(q(a),str(round(f['expected']*2)) if tag=='sz' else '1' if tag=='b' and f['expected'] else '0' if tag=='b' else f['expected'])

def mask_main(root,f):
 # Reuse exact locators with a lightweight view, never a cached mutable Package.
 class View:pass
 v=View();v.root=root;v.paragraphs=root.find(q('body')).findall(q('p'));v.sections=root.findall('w:body/w:p/w:pPr/w:sectPr',NS)+root.findall('w:body/w:sectPr',NS)
 tag,attrs=attribute(f)
 if f['rule_id']=='R26':e=v.sections[f['locator']['section']-1].find(q(tag))
 else:
  el=locate(v,f['locator']);e=el.find('w:'+('rPr' if 'run' in f['locator'] else 'pPr')+'/w:'+tag,NS)
 if e is not None:
  for a in attrs:e.attrib.pop(q(a),None)

def story_fingerprint(pkg,changes):
 out={}
 for part in {f['story_part'] for f in changes if f.get('story_part')}:
  root=deepcopy(pkg.story_roots[part]) if part in pkg.story_roots else parse(pkg.parts[part])
  for f in changes:
   if f.get('story_part')!=part:continue
   if f['rule_id'] in ('R36','R37'):
    from .notes import mask_story
    mask_story(root,f);continue
   p=root.findall(q('p'))[f['locator']['story_paragraph']-1];el=p.findall(q('r'))[f['locator']['run']-1] if 'run' in f['locator'] else p;tag,attrs=attribute(f);e=el.find('w:'+('rPr' if 'run' in f['locator'] else 'pPr')+'/w:'+tag,NS)
   if e is not None:
    for a in attrs:e.attrib.pop(q(a),None)
  if any(f.get('story_part')==part and f['rule_id'] not in ('R36','R37') for f in changes):prune(root)
  out[part]=E.tostring(root,method='c14n').decode()
 return json.dumps(out,sort_keys=True).encode()

def prune(root):
 for e in reversed(list(root.iter())):
  if e.tag in {q(x) for x in ('rFonts','sz','b','jc','pPr','rPr')} and not len(e) and not e.attrib and not e.text:e.getparent().remove(e)

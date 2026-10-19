"""Opt-in attribute findings and surgical edits; delegates to the existing engine transaction."""
from copy import deepcopy
import re,math
from lxml import etree as ET
from .package import q,NS,DemoError
from .formats import Resolver,Unresolved,scripts,same_font,paragraph_unsafe
from .paragraph_properties import space,space_fixable,spacing_equal,alignment,bold
from .academic_rules import school,NEW_TYPES,RULE_FOR,FIELDS,LABELS

from .backmatter import TYPES as BACK_TYPES,RULE_FOR as BACK_RULES,FIELDS as BACK_FIELDS,school as back_school
XML_SPACE='{http://www.w3.org/XML/1998/namespace}space'
def text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=NS))
def source(rules,obj,prop):
 if obj in BACK_TYPES:
  if rules.get('back_sources') is not None:return deepcopy(rules['back_sources'][obj].get({'中文字体':'font_cn','西文字体':'font_western','字号':'font_size','加粗':'bold'}.get(prop,prop),{'label':'新增对象复杂文字槽位覆盖边界','quote':''}))
  src=rules['back_policy']['source'];return {'file':rules['back_policy']['source_file'],'physical_page':src['physical_page'],'quote':src['quote'],'label':'2015明确附录条文；仅确认普通文献文字'}
 if obj=='document':
  return {'file':school()['source_file'],'physical_page':16,'quote':'摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。','label':'2015范例只读口径'+('（用户明确启用，不由AI提取）' if rules['academic_sources'] else '')}
 if rules['academic_sources'] is not None:
  out=deepcopy(rules['academic_sources'].get(obj,{}).get(prop,{'label':'未配置属性','quote':''}))
  if out.get('quote','').startswith('PaperFit项目默认'):out['label']='PaperFit项目默认（本次开始授权；非学校要求）'
  return out
 s=school()['sources'].get(obj,{'page':None,'quote':'学校原文未明确，不默认启用'})
 return {'file':school()['source_file'],'physical_page':s['page'],'quote':s['quote'],'label':'2015演示规则原文/范例；不宣称现行标准'}

def append_checks(report,pkg,manifest,rules,*,generic_only=False):
 proofs={p['paragraph']:p for p in report['coverage'].get('citation_paragraph_evidence',[])}
 res=Resolver(pkg);seen=set();fs=report['findings'];notes=report['coverage_notes'];cfg=rules['academic_objects']
 report['coverage']['disabled_academic_properties']={t:[p for _,o,p in {**FIELDS,**BACK_FIELDS}.values() if o==t and c.get(p) is None] for t,c in cfg.items()}
 report['coverage']['academic_unchecked_requirements']=['外文参考文献2篇以上及主要文献身份、指导教师例外未自动判断（学校PDF物理页16）；需人工核对。','中英文摘要/关键词的语义一致性、关键词层次及著录真实性未检查；不生成或改写内容。']
 report['coverage']['academic_property_scope']='本清单列已启用的通用/章节属性（含确认附录致谢时R38–R41）；正文/标题/题注原R01–R12要求仍按其规则独立执行。'
 def add(rid,loc,obj,prop,actual,wanted,status,reason='',fixable=True):
  key=rid+':'+':'.join(f'{k}={v}' for k,v in loc.items())
  fs.append({'key':key,'rule_id':rid,'rule_name':rules['rules'][rid]['name']+' · '+LABELS.get(prop,prop),'locator':loc,'object_type':obj,'actual':actual,'expected':wanted,'status':status,'fixable':status=='problem' and fixable,'source':source(rules,obj,prop),'detail':reason,'property':prop});seen.add(rid)
  return fs[-1]
 def read(rid,loc,obj,prop,fn,wanted,eq=lambda a,b:a==b,allow=True):
  try:
   actual=fn();return add(rid,loc,obj,prop,actual,wanted,'pass' if eq(actual,wanted) else 'problem',fixable=allow)
  except (Unresolved,ValueError,TypeError,OverflowError) as exc:return add(rid,loc,obj,prop,{'unresolved':str(exc)},wanted,'review',str(exc),False)
 for name,typ in manifest['paragraph_types'].items():
  n=int(name);c=cfg.get(typ,{})
  if typ in ('other','pending'):continue
  rid={**RULE_FOR,**BACK_RULES}.get(typ,'R13')
  if generic_only and rid!='R13':continue
  p=pkg.paragraphs[n-1];loc={'paragraph':n};why=paragraph_unsafe(p)
  if typ in ('figure_caption','table_caption') and c.get('alignment')=='center':
   try:
    offsets=res.attrs(res.layers(p,kind='pPr'),'ind')
    if any(str(v) not in ('0','0.0') for v in offsets.values()):notes.append({'locator':loc,'status':'review','detail':'题注已要求居中，但存在首行/悬挂/左右缩进；本次未授权清除缩进，视觉中心需核对。','declared_indentation':offsets})
   except (Unresolved,ValueError):pass
  enabled={k:v for k,v in c.items() if v is not None}
  if not enabled:continue
  try:pl=res.layers(p,kind='pPr')
  except Unresolved as exc:why=str(exc);pl=[]
  from .text_runs import walk,select_run,executable_run
  linked=walk(pkg,p) if typ=='reference_item' and p.find(q('hyperlink')) is not None else None
  partial=bool(linked and linked['supported_links'] and not linked['context_reason'])
  if partial:why=None
  if why:
   add(rid,loc,typ,'特殊结构',{'unresolved':why},enabled,'review',why+'；分类确认不能绕过保护',False);continue
  runs=[];special=partial
  if partial:
   notes.append({'locator':loc,'status':'review','detail':'参考文献普通链接文字独立检查；段落属性、编号及引用语义不放宽。'})
   for issue in linked['issues']:notes.append({'locator':{**loc,**issue['locator']},'status':'review','detail':issue['detail']})
  segments=linked['rows'] if partial else [{'locator':{'run':i},'node':r,'reason':None,'evidence':None} for i,r in enumerate(p.findall(q('r')),1)]
  for segment in segments:
   run_loc=segment['locator'];r=segment['node'];i=run_loc.get('run',run_loc.get('link_run'))
   try:
    layers=res.layers(p,r);reason=segment['reason'] or res.special(r,layers)
   except Unresolved as exc:layers=[];reason=str(exc)
   if reason:
    special=True;notes.append({'locator':{'paragraph':n,**run_loc},'status':'review','detail':reason+'；前后置章节特殊片段未修改'})
   elif text(r).strip():runs.append((run_loc,r,layers))
  numbered=any(x.find(q('numPr')) is not None for x in pl)
  for prop in ('before','after','alignment','line_spacing','first_line_indent'):
   wanted=c.get(prop)
   if wanted is None:continue
   location={**loc,'property':prop}
   limited=typ=='body' and rid=='R13' and prop in ('before','after','alignment') and proofs.get(n,{}).get('structurally_safe',False)
   if (special and not limited) or numbered:
    add(rid,location,typ,prop,{'unresolved':'特殊片段/自动编号段落属性依赖'},wanted,'review','普通文字仍独立检查；不改段落或编号定义',False);continue
   if prop in ('before','after'):
    ok,reason=space_fixable(res,pl,prop,wanted)
    def read_space():
     value=space(res,pl,prop)
     if limited and proofs[n].get('grid_active') and ('lines' in (value['unit'],wanted['unit'])):raise Unresolved('文档网格/吸附影响行单位段距，未将声明值当作可见间距通过')
     return value
    f=read(rid,location,typ,prop,read_space,wanted,spacing_equal,ok)
    if reason:f['detail']=reason
    if f['fixable']:f['dependency_note']='只更改'+prop+'间距属性，清理/中和相同行单位、磅值、自动间距冲突；保留行距/另一侧间距/缩进/分页'
   elif prop=='alignment':read(rid,location,typ,prop,lambda:alignment(res,pl),wanted)
   elif prop=='line_spacing':
    from .paragraph_values import read_line,line_equal
    f=read(rid,location,typ,prop,lambda:read_line(res,pl),{'multiple':wanted} if not isinstance(wanted,dict) else wanted,line_equal)
    if any(s.find(q('docGrid')) is not None and s.find(q('docGrid')).get(q('type')) in ('lines','linesAndChars','snapToChars') for s in pkg.sections) and res.value(pl,'snapToGrid','1') not in ('0','false','off'):
     f.update(status='review',fixable=False,detail='存在文档网格且未关闭吸附，不能保证倍数行距')
   else:
    if isinstance(wanted,dict):
     from .paragraph_values import read_indent,indent_equal
     def explicit_indent():
      if any(s.find(q('docGrid')) is not None and s.find(q('docGrid')).get(q('type')) in ('lines','linesAndChars','snapToChars') for s in pkg.sections) and res.value(pl,'snapToGrid','1') not in ('0','false','off'):raise Unresolved('文档网格影响，明确缩进仍待复核')
      return read_indent(res,pl,wanted)
     read(rid,location,typ,prop,explicit_indent,wanted,indent_equal);continue
    def indent():
     a=res.attrs(pl,'ind')
     if any(k in a for k in ('hanging','hangingChars')):raise Unresolved('首行/悬挂缩进冲突')
     if 'firstLineChars' in a:
      value=int(a['firstLineChars'])/100
      if 'firstLine' in a:
       sizes={res.size(l) for _,_,l in runs}
       if len(sizes)!=1 or None in sizes or abs(int(a['firstLine'])/20-next(iter(sizes))*value)>.1:raise Unresolved('字符和点值缩进冲突')
      return {'chars':value,'origin':'字符属性'}
     if 'firstLine' not in a:raise Unresolved('首行缩进未明确设置')
     sizes={res.size(l) for _,_,l in runs}
     if len(sizes)!=1 or None in sizes:raise Unresolved('字号不一致，点值缩进不能换算字符')
     return {'chars':int(a['firstLine'])/20/next(iter(sizes)),'pt':int(a['firstLine'])/20,'origin':'当前有效字号等效点值'}
    read(rid,location,typ,prop,indent,{'chars':wanted},lambda a,b:abs(a['chars']-b['chars'])<.01)
  if typ.startswith('keywords'):
   if special or not simple_keyword(p):
    add(rid,loc,typ,'标签边界',{'unresolved':'标签不明确或包含复杂结构'},None,'review','只支持普通w:t片段；字段、链接、公式、tab等不拆分',False);continue
   full=text(p);m=keyword_label(full,typ)
   if not m:
    add(rid,loc,typ,'标签边界',full[:32],None,'review','无法唯一识别段首关键词标签和冒号，不重写文字',False);continue
   offset=0
   for r in p.findall(q('r')):
    value=text(r);end=offset+len(value);layers=res.layers(p,r)
    for part,start,stop in [('label',offset,min(end,m.end())),('content',max(offset,m.end()),end)]:
     if stop<=start or not full[start:stop].strip():continue
     props={k:c.get(part+'_'+k) for k in ('font_cn','font_western','font_size','bold')}
     _text_checks(read,add,res,layers,full[start:stop],rid,{'paragraph':n,'start':start,'end':stop,'part':part},typ,props)
    offset=end
  else:
   for run_loc,r,layers in runs:_text_checks(read,add,res,layers,text(r),rid,{'paragraph':n,**run_loc},typ,c)
   if partial:
    for f in fs:
     if f['locator'].get('paragraph')==n and 'link' in f['locator']:
      segment=next(x for x in segments if x['locator']=={k:f['locator'][k] for k in ('link','link_run')})
      f['link_evidence']=deepcopy(segment['evidence'])
 for rid in ('R13',) if generic_only else tuple(f'R{i:02}' for i in range(13,22))+tuple(r for r in BACK_RULES.values() if r in rules['rules']):
  if rid not in seen:
   f=add(rid,{'document':1},'document','未启用/不适用',None,None,'not_applicable','当前模板未配置或确认范围无该对象，不套正文规则',False)
   if rid in BACK_RULES.values():
    f['object_type']=next(o for o,r in BACK_RULES.items() if r==rid);f['source']={'label':'新对象未配置或当前范围无对象；不推定学校要求/已通过','quote':''}
 if any(r in rules['rules'] for r in BACK_RULES.values()):
  report['coverage']['backmatter_limits']=rules['back_policy']['limits'];report['coverage']['material_exclusions']=deepcopy(manifest.get('material_exclusions',{}))
  report['coverage']['backmatter_confirmed_objects']=[{'paragraph':int(n),'type':t,'enabled_properties':[k for k,v in cfg.get(t,{}).items() if v is not None]} for n,t in manifest['paragraph_types'].items() if t in BACK_TYPES]
  report['rules']['backmatter_sha256']=rules['backmatter_sha256'];report['rules']['backmatter_version']=rules['back_policy']['version']
 if not generic_only:content_checks(report,pkg,manifest,rules,add)
 from .extended import refresh_summary
 report['rules'].update(mode='academic',academic_sha256=rules['academic_sha256']);refresh_summary(report,len(rules['rules']))

def _text_checks(read,add,res,layers,value,rid,loc,typ,c):
 cn,slots,unknown=scripts(value)
 for slot,wanted in [('eastAsia',c.get('font_cn'))]+[(s,c.get('font_western')) for s in slots]:
  if wanted is None or (slot=='eastAsia' and not cn):continue
  info=res.font_info(layers,slot,value)
  f=read(rid,{**loc,'property':'font_'+slot},typ,'中文字体' if slot=='eastAsia' else '西文字体',lambda:info['font'] if info['font'] is not None else (_ for _ in ()).throw(Unresolved(info['reason'])),wanted,lambda a,b:isinstance(a,str) and same_font(a,b),info['safe_to_fix_slot'])
  if info['font'] is None:f.update(status='review',fixable=False,detail=info['reason'])
  f['font_evidence']={slot:info}
 if c.get('font_size') is not None:
  def size():
   v=res.size(layers)
   if v is None:raise Unresolved('字号未明确指定')
   return v
  read(rid,{**loc,'property':'size'},typ,'字号',size,c['font_size'])
 if c.get('bold') is not None:read(rid,{**loc,'property':'bold'},typ,'加粗',lambda:bold(res,layers),c['bold'])
 if unknown and (c.get('font_cn') is not None or c.get('font_western') is not None):add(rid,{**loc,'property':'文字槽位'},typ,'文字槽位',value[:20],None,'review','未知Unicode槽位未宣称全部字体覆盖',False)

def keyword_label(value,typ):return re.match(r'^\s*关键词\s*[:：]\s*' if typ=='keywords_cn' else r'^\s*Key\s*words\s*[:：]\s*',value,re.I)
def simple_keyword(p):
 return all(all(e.tag in (q('rPr'),q('t')) for e in r) and len(r.findall(q('t')))==1 for r in p.findall(q('r')))

def content_checks(report,pkg,manifest,rules,add):
 if not rules['content_checks']:
  add('R22',{'document':1},'document','只读内容提示',None,None,'not_applicable','旧模板或用户选择未启用，不静默新增学校要求',False);return
 types=manifest['paragraph_types'];counts={t:[] for t in NEW_TYPES}
 for n,t in types.items():
  if t in counts:counts[t].append(int(n))
 for t,nums in counts.items():
  add('R22',{'document':1,'property':'存在_'+t},'document','确认范围内存在',len(nums),'>=1','pass' if nums else 'review','只统计确认类型；未发现时须核对分类，不能直接断言文档物理缺少或补写内容',False)
 total=sum(len(re.sub(r'\s','',text(pkg.paragraphs[n-1]))) for n in counts['abstract_cn_body'])
 if counts['abstract_cn_body']:add('R22',{'document':1,'property':'中文摘要字数'},'document','中文摘要字数',total,'400–600','review' if any(paragraph_unsafe(pkg.paragraphs[n-1]) for n in counts['abstract_cn_body']) else 'pass' if 400<=total<=600 else 'problem','复杂结构不能宣称计数完整；正文非空白Unicode字符数，标点/数字计入，不含标题或关键词；不生成/扩写摘要',False)
 for typ in ('keywords_cn','keywords_en'):
  for n in counts[typ]:
   value=text(pkg.paragraphs[n-1]);m=keyword_label(value,typ)
   if not m or paragraph_unsafe(pkg.paragraphs[n-1]) or not simple_keyword(pkg.paragraphs[n-1]):
    add('R22',{'paragraph':n,'property':'关键词数量'},'document','关键词数量',None,'3–5','review','标签无法定位，不猜测数量',False);continue
   content=value[m.end():].strip();parts=re.split('[;；]',content);valid=len([v for v in parts if v.strip()])
   add('R22',{'paragraph':n,'property':'关键词数量'},'document','关键词数量',valid,'3–5','pass' if 3<=valid<=5 else 'problem','按中英文分号分隔非空项；不添加关键词',False)
   ok=valid>=1 and not any(not v.strip() for v in parts) and not re.search('[,，、。.!！;；]$',content) and not re.search('[,，、]',content)
   add('R22',{'paragraph':n,'property':'关键词分隔符'},'document','关键词分隔符',content[:100],'分号分隔，末项无标点','pass' if ok else 'problem','只读，不调整词序或改写标点',False)
 from .citations import reference_evidence
 evidence=reference_evidence(pkg,counts['reference_item'])
 numbers=[r['number'] for r in evidence if r['number'] is not None];unresolved=[r['paragraph'] for r in evidence if r['number'] is None]
 add('R22',{'document':1,'property':'参考文献条目数'},'document','参考文献条目数',len(counts['reference_item']),'确认条目≥10（主要文献/外文身份另核对）','pass' if len(counts['reference_item'])>=10 else 'problem','按人工确认条目计数；不足时核对范围或资料，不生成文献；不判断主要文献身份、语种或所有著录格式',False)
 if numbers:
  duplicate=len(set(numbers))!=len(numbers);bad=duplicate or numbers!=list(range(1,len(numbers)+1))
  status='problem' if duplicate else 'review' if unresolved else 'problem' if bad else 'pass'
  add('R22',{'document':1,'property':'参考文献手工编号'},'document','参考文献手工编号',numbers,'从1顺序、无重复/跳号',status,'含其他/自动编号，已解析部分只确定重复；全文连续性待复核，不从手工子序列断言跳号' if unresolved else '仅明确[整数]的只读检查；不重排或改编号',False)
 if unresolved:add('R22',{'document':1,'property':'参考文献其他编号'},'document','其他/自动编号',unresolved,None,'review','自动编号、作者年份或其他著录形式的编号序列未判断；不借人工分类宣称通过',False)

def isolate(p,start,end):
 offset=0;out=[]
 for r in list(p.findall(q('r'))):
  value=text(r);stop=offset+len(value)
  if stop<=start or offset>=end:offset=stop;continue
  cuts=sorted({0,len(value),max(0,start-offset),min(len(value),end-offset)})
  pieces=[]
  for a,b in zip(cuts,cuts[1:]):
   if b<=a:continue
   piece=deepcopy(r);t=piece.find(q('t'));t.text=value[a:b];t.set(XML_SPACE,'preserve');pieces.append(piece)
   if offset+a>=start and offset+b<=end:out.append(piece)
  pos=p.index(r);p.remove(r)
  for i,piece in enumerate(pieces):p.insert(pos+i,piece)
  offset=stop
 return out

def apply(pkg,f):
 from .engine import _ensure
 p=pkg.paragraphs[f['locator']['paragraph']-1];loc=f['locator'];prop=loc['property'];wanted=f['expected']
 if 'start' in loc:
  if not simple_keyword(p) or paragraph_unsafe(p):raise DemoError('关键词片段不能安全拆分')
  targets=isolate(p,loc['start'],loc['end'])
 else:
  from .text_runs import select_run,executable_run
  targets=[executable_run(pkg,p,loc) if 'link' in loc else select_run(p,loc)] if 'run' in loc or 'link_run' in loc else []
 if targets:
  for r in targets:
   rp=_ensure(r,'rPr')
   if prop.startswith('font_'):
    slot=prop[5:];e=_ensure(rp,'rFonts');e.set(q(slot),wanted);e.attrib.pop(q(slot+'Theme'),None)
   elif prop=='size':_ensure(rp,'sz').set(q('val'),str(round(wanted*2)))
   elif prop=='bold':_ensure(rp,'b').set(q('val'),'1' if wanted else '0')
 elif prop in ('before','after','alignment','line_spacing','first_line_indent'):
  from .paragraph_values import apply as patch
  patch(p,prop,wanted)
 else:raise DemoError('未知章节修正属性')

def canonical_keyword(p):
 # Integrity-only normalization: each safe character retains its original run attributes/rPr.
 for r in list(p.findall(q('r'))):
  value=text(r);pos=p.index(r);p.remove(r)
  for i,char in enumerate(value):
   piece=deepcopy(r);t=piece.find(q('t'));t.text=char;t.set(XML_SPACE,'preserve');p.insert(pos+i,piece)

def mask(p,f):
 loc=f['locator'];prop=loc['property']
 if 'start' in loc:
  offset=0;targets=[]
  for r in p.findall(q('r')):
   stop=offset+len(text(r))
   if offset>=loc['start'] and stop<=loc['end']:targets.append(r)
   offset=stop
 else:
  from .text_runs import select_run
  targets=[select_run(p,loc)] if 'run' in loc or 'link_run' in loc else [p]
 tag,attrs=('rFonts',[prop[5:],prop[5:]+'Theme']) if prop.startswith('font_') else ('sz',['val']) if prop=='size' else ('b',['val']) if prop=='bold' else ('jc',['val']) if prop=='alignment' else ('spacing',[prop,prop+'Lines',prop+'Autospacing']) if prop in ('before','after') else ('spacing',['line','lineRule']) if prop=='line_spacing' else ('ind',['firstLine','firstLineChars','hanging','hangingChars'])
 for obj in targets:
  parent=obj.find(q('rPr' if obj.tag==q('r') else 'pPr'));e=parent.find(q(tag)) if parent is not None else None
  if e is not None:
   for a in attrs:e.attrib.pop(q(a),None)
   if not e.attrib and not len(e):parent.remove(e)

"""Rule-only orchestration. Native module validators remain execution authorities."""
from copy import deepcopy
import json,re
from .package import DemoError,sha256
from .rule_config import strict_json
from . import templates as main,back_templates as back,front_template as front,toc_template as toc,notes
from .norms import marked_text
from . import paragraph_templates as paragraphs
MODULES=('main','front','toc','notes')
LABELS={'main':'正文与章节 v6','front':'封面与页眉页脚','toc':'目录','notes':'脚注与尾注'}
FIELDS={'main':paragraphs.FIELDS,'front':{n:('',n,'pt' if p=='font_size' else 'mm' if p=='mm' else p) for n,p in front.FIELDS.items()},'toc':{n:('',n,{'font_cn':'font','font_size':'pt','alignment':'alignment','line_multiple':'multiple'}[p]) for n,p in toc.FIELDS.items()},'notes':{k+'__'+p:('',notes.KINDS[k]+' '+p,{'font_cn':'font','font_size':'pt','line_multiple':'multiple','before':'spacing','after':'spacing','alignment':'alignment'}[p]) for k in notes.KINDS for p in notes.ALL_FIELDS}}
for _m in ('front','toc'):
 for _n,(_rid,_label,_unit) in list(FIELDS[_m].items()):
  if _n.endswith('_distance_mm'):_label='页眉距离' if _n.startswith('header') else '页脚距离'
  else:
   _obj,_prop=_n.split('__');_label={'cover_title':'封面论文标题','header_text':'普通页眉文字','footer_text':'普通页脚文字','title':'目录标题','level1':'目录一级条目','level2':'目录二级条目','level3':'目录三级条目'}[_obj]+' '+{'font_cn':'中文字体','font_western':'西文字体','font_size':'字号','alignment':'对齐','bold':'加粗','line_multiple':'倍数行距'}[_prop]
  FIELDS[_m][_n]=(_rid,_label,_unit)
MAX_BYTES=160*1024
EMPTY={'kind':'not_enabled','quote':'','location':None}
def raw(d):return (json.dumps(d,ensure_ascii=False,sort_keys=True,allow_nan=False,indent=2)+'\n').encode()
def digest(d):return sha256(raw(d))
def require(ok,msg):
 if not ok:raise DemoError(msg)
def exact(d,keys,msg):require(type(d) is dict and set(d)==set(keys),msg)
def flat(module,cfg):
 if module=='main':return {n:None for n in FIELDS[module]}|deepcopy(cfg['template']['final_values'])|{n:None for n in cfg['disabled_fields']}
 if module=='notes':return {n:None for n in FIELDS[module]}|{k+'__'+p:v for k,ps in cfg['values'].items() for p,v in ps.items()}
 return deepcopy(cfg['values'])
def origins(module,cfg):
 if module=='main':return {n:deepcopy(EMPTY) for n in FIELDS[module]}|deepcopy(cfg['template']['field_sources'])|{n:deepcopy(EMPTY) for n in cfg['disabled_fields']}
 if module=='notes':return {n:deepcopy(EMPTY) for n in FIELDS[module]}|{k+'__'+p:{'kind':s,'quote':'','location':None} for k,ps in cfg['sources'].items() for p,s in ps.items()}
 return deepcopy(cfg['sources'])
def validate_value(module,n,v):
 require(module in MODULES and n in FIELDS[module],'规则包含未知执行字段')
 if module=='main':
  if v is not None:main.validate_value(n,v)
 elif module=='front':front.value(n,v)
 else:
  d=toc.school() if module=='toc' else notes.school()
  if module=='toc':d['name']='用户确认的目录演示要求';d['values'][n]=v;d['sources'][n]=deepcopy(EMPTY) if v is None else {'kind':'user_confirmed','quote':'','location':None};toc.validate(d)
  else:
   k,p=n.split('__');d=notes.promote(d) if p in notes.EXTRA_FIELDS else d;d['values'][k][p]=v;d['sources'][k][p]='not_enabled' if v is None else 'user_confirmed';notes.template(d)
 return v

def source(s,v,segments):
 exact(s,('kind','quote','location'),'规则包来源结构无效')
 require(s['kind'] in ('school_demo','school_default','default_inherited','legacy_fixed','ai_extracted','user_confirmed','not_enabled'),'规则包来源类型无效')
 main.safe_text(s['quote'],200,allow_empty=True)
 require((v is None)==(s['kind']=='not_enabled'),'规则包未启用值与来源不一致')
 if s['kind'] in ('ai_extracted','user_confirmed'):
  require(not s['quote'] and s['location'] is None or bool(s['quote']) and any(x['location']==s['location'] and s['quote'] in x['text'] for x in segments),'规则包原句或来源位置伪造')
  if s['kind']=='ai_extracted':require(bool(s['quote']),'AI字段缺少原文依据')

def validate(d,base):
 require(type(d) is dict,'规则包必须是JSON对象')
 d=deepcopy(d)
 exact({k:v for k,v in d.items() if k not in ('notices','assembly')},('format','version','name','excerpt','excerpt_sha256','extraction','modules','provenance','confirmation'),'规则包结构不支持')
 if 'assembly' in d:__import__('core.page_policy',fromlist=['validate']).validate(d['assembly'])
 require(d['format']=='paper-grid-rule-bundle' and type(d['version']) is int and d['version']==1,'未知规则包版本')
 main.safe_text(d['name'],80);require(not any(x in d['name'] for x in ('官方','华工','学校')),'自定义规则包不能冒充学校官方规范')
 main.validate_segments(d['excerpt']);__import__('core.norms',fromlist=['verify_namespaces']).verify_namespaces(d['excerpt']);require(d['excerpt_sha256']==sha256(marked_text(d['excerpt']).encode()),'规则包摘录哈希不符')
 exact(d['extraction'],('kind','model','timestamp_utc'),'规则包解析来源无效')
 require(d['extraction']['kind'] in ('none','real_api','mock_api','unverified_import'),'规则包解析来源无效')
 require(d['extraction']['model'] in (None,'deepseek-flash','deepseek-v4-pro'),'规则包模型无效');require(d['extraction']['timestamp_utc'] is None or type(d['extraction']['timestamp_utc']) is str and len(d['extraction']['timestamp_utc'])<=80,'规则包时间摘要无效')
 if d['extraction']['kind'] in ('real_api','mock_api'):
  require(d['extraction']['model'] in ('deepseek-flash','deepseek-v4-pro'),'解析模型缺失')
  main.safe_text(d['extraction']['timestamp_utc'],40)
  from datetime import datetime
  try:datetime.fromisoformat(d['extraction']['timestamp_utc'])
  except ValueError:raise DemoError('解析时间无效') from None
 else:require(d['extraction']['model'] is None and d['extraction']['timestamp_utc'] is None,'未解析或未验真来源不能自报模型/时间')
 require(d['confirmation']=='用户核对后应用；规则不确认论文对象','规则包确认信息无效')
 exact(d['modules'],MODULES,'规则包模块缺失或未知，不能推断应用含义');require(d['modules']['main'] is not None,'规则包主模块必须明确，可逐字段选择不检查');exact(d['provenance'],MODULES,'规则包来源模块无效')
 for m,c in d['modules'].items():
  if c is None:require(d['provenance'][m] is None,'未配置模块不能携带来源');continue
  if m=='main':
   exact(c,('template','disabled_fields'),'正文模块结构无效');main.validate_template(c['template'],base)
   require(type(c['disabled_fields']) is list and len(c['disabled_fields'])==len(set(c['disabled_fields'])) and all(n in main.ALL_FIELDS for n in c['disabled_fields']),'禁用字段无效')
  elif m=='front':front.validate(c)
  elif m=='toc':toc.validate(c)
  else:notes.template(c)
  require(len(raw(c['template'] if m=='main' else c))<=({'main':65536,'front':16000,'toc':32000,'notes':65536}[m]),'模块配置超过已有容量上限')
  vals=flat(m,c);ss=d['provenance'][m]
  if type(ss) is dict:
   for n in set(FIELDS[m])-set(ss):
    if vals[n] is None:ss[n]=deepcopy(EMPTY)
  exact(ss,FIELDS[m],'规则包逐字段来源缺失或未知')
  for n,v in vals.items():
   validate_value(m,n,v);source(ss[n],v,d['excerpt'])
   native=origins(m,c)[n]
   if ss[n]['kind'] in ('school_demo','school_default','default_inherited','legacy_fixed'):require(ss[n]==native,'不得伪造学校/默认来源')
   elif m!='notes':require(ss[n]==native,'模块来源与规则包来源不一致')
   if ss[n]['kind']=='ai_extracted':
    require(d['extraction']['kind']!='none','AI来源缺少解析记录')
    field={'value':v,'unit':FIELDS[m][n][2],'quote':ss[n]['quote'],'location':ss[n]['location'],'support':'supported'}
    validate_candidate(m,n,field,d['excerpt'])
 validate_notices(d.get('notices',{m:[] for m in MODULES}),d['excerpt'])
 require(len(raw(d))<=MAX_BYTES,'规则包超过160KB，请缩小规范摘录')
 return deepcopy(d)

def loads(content,base):
 require(type(content) is bytes and 0<len(content)<=MAX_BYTES,'规则包须为不超过160KB的UTF-8 JSON')
 try:d=strict_json(content.decode('utf-8'))
 except UnicodeError:raise DemoError('规则包须为UTF-8 JSON') from None
 return validate(d,base)

def defaults(base):
 b=main.make_template('用户确认的演示规则',main.defaults(base,extended=True),{n:{'kind':'default_inherited','quote':'','location':None} for n in main.ALL_FIELDS},[],base)
 b=back.upgrade(b,base)
 # Legacy upgrades never add new checks. Explicit school initial values are shown before adoption.
 from .academic_templates import default_values
 from .table_templates import defaults as td
 for n,v in {**default_values(base),**td(base),**back.flat()}.items():
  if n not in main.ALL_FIELDS:b['final_values'][n]=v;b['field_sources'][n]={'kind':'default_inherited' if v is not None else 'not_enabled','quote':'','location':None}
 back.validate(b,base)
 return {'main':{'template':b,'disabled_fields':[]},'front':front.school(),'toc':toc.school(),'notes':notes.school()}

def build(name,modules,segments,extraction,base,provenance=None,notices=None,assembly=None):
 d={'format':'paper-grid-rule-bundle','version':1,'name':name,'excerpt':deepcopy(segments),'excerpt_sha256':sha256(marked_text(segments).encode()),'extraction':extraction or {'kind':'none','model':None,'timestamp_utc':None},'modules':deepcopy(modules),'provenance':provenance or {m:origins(m,c) if c else None for m,c in modules.items()},'confirmation':'用户核对后应用；规则不确认论文对象','notices':deepcopy(notices or {m:[] for m in MODULES})}
 if assembly is not None:d['assembly']=deepcopy(assembly)
 return validate(d,base)

def validate_candidate(m,n,f,segments):
 from .norms import evidence_segments
 if type(f) is dict:segments=evidence_segments(segments,f.get('location'))
 exact(f,('value','unit','quote','location','support'),'统一草稿字段结构无效')
 require(f['support']=='supported' and f['value'] is not None and f['unit']==FIELDS[m][n][2],'统一草稿单位或支持状态无效')
 main.safe_text(f['quote'],200);require(any(s['location']==f['location'] and f['quote'] in s['text'] for s in segments),'依据必须是来源位置内的连续原句')
 validate_value(m,n,f['value'])
 if m=='main':
  d={x:None for x in back.V6_FIELDS};d['unsupported']=[]
  if n in paragraphs.EXTRA:paragraphs.candidate(n,f,segments)
  else:d[n]=f;back.validate_draft(d,segments)
 elif m=='front':
  d={x:None for x in FIELDS[m]};d.update({n:f,'unsupported':[]});front.validate_draft(d,'\n'.join(s['text'] for s in segments),segments=segments)
 elif m=='toc':
  d={'fields':{x:None for x in FIELDS[m]},'unsupported':[]};d['fields'][n]=f;toc.validate_draft(d,marked_text(segments),segments=segments)
  # Independently validate every clause for this object/property; never cut away conflicts.
  found=set();o=n.split('__')[0]
  for s in segments:
   for q in re.split('[。；;\n]',s['text']):
    if '目录' not in q or (o=='title' and '标题' not in q) or (o!='title' and not any(t in q for t in {'level1':('一级','各章'),'level2':('二级','次级'),'level3':('三级','次级')}[o])):continue
    for v in proof(n.split('__')[1],q):found.add(v)
  require(found=={f['value']},'目录原文存在冲突或不支持要求，须明确取舍')
 else:
  k,p=n.split('__');q=f['quote'];ctx=notes.KINDS[k]+r'(?:普通文字|正文|文字)?'
  require(bool(re.search(ctx,q)) and not re.search(('尾注' if k=='footnote' else '脚注')+'|正文标题|目录|论文正文',q),'注释对象依据不明确或混用')
  if p in ('line_multiple','before','after','alignment'):
   require(bool(re.search(ctx,q)),'注释对象不明确')
   clauses=[c for s in segments for c in re.split('[。；;\n]',s['text']) if re.search(ctx,c)]
   if p=='line_multiple':
    from .paragraph_values import prove
    prove(p,f['value'],q,clauses)
   else:
    from .academic_templates import validate_candidate_for
    # Spacing/alignment proof is shared with ordinary paragraph units.
    wanted=f['value'];found=[]
    for c in clauses:
     if p=='alignment':found.extend(v for v,t in main.ALIGNMENTS.items() if t in c)
     else:found.extend({'value':float(x),'unit':'lines' if u=='行' else 'pt'} for x,u in re.findall(('段前' if p=='before' else '段后')+r'\s*(\d+(?:\.\d+)?)\s*(pt|磅|行)',c,re.I))
    require(bool(found) and all(x==wanted for x in found),'注释段落要求不匹配或冲突')
   return deepcopy(f)
  found=set()
  for s in segments:
   for clause in re.split('[。；;\n]',s['text']):
    if re.search(ctx,clause):found.update(proof(p,clause))
  require(proof(p,q)=={f['value']} and found=={f['value']},'注释原句数值不符、冲突或未支持')
 return deepcopy(f)

def proof(p,q):
 if re.search('任选|不超过|至少|至多|大约|建议|可能|不规定|未规定|不作要求|不要求',q):return {'unsupported'}
 if p=='font_cn':
  # Strip the object label, sizes and ordinary requirement words; retain unknown family qualifiers.
  from .spec_validation import FONT_NAMES
  q=re.sub(r'脚注|尾注|目录(?:一级|二级|三级)?(?:条目|标题)?|各章题序及标题|普通文字|正文|文字|字体|小[二三四五]号|[二三四五]号','',q)
  return main.font_candidates(q,'font_cn')
 if p=='font_size':
  from .spec_validation import FONT_NAMES
  return {FONT_NAMES[x.rstrip('号')] for x in re.findall('小[二三四五]号|[二三四五]号',q)}|{float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*(?:pt|磅)',re.split('行距',q)[0],re.I)}
 if p=='alignment':return {v for v,t in main.ALIGNMENTS.items() if t in q}
 if re.search('固定|最小',q):return {'unsupported'}
 return {float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*倍',q)}|({1.} if '单倍' in q else set())

def validate_draft(d,segments):
 main.validate_segments(segments)
 from .norms import source_group,verify_namespaces
 verify_namespaces(segments);require(len({source_group(s['location']) for s in segments})<=1,'一次AI摘录必须有一致来源；历史规范留在已生效配置中，不混作本次冲突判断')
 exact(d,MODULES,'统一响应模块缺失或未知')
 for m,part in d.items():
  exact(part,('fields','issues'),'统一模块草稿字段无效')
  require(type(part['fields']) is dict and set(part['fields'])<=set(FIELDS[m]),'统一草稿含未知执行字段')
  require(type(part['issues']) is list and len(part['issues'])<=100,'冲突/未支持记录无效')
  blocked=set()
  for i in part['issues']:
   exact(i,('fields','quote','location','reason'),'冲突/未支持结构无效')
   require(type(i['fields']) is list and all(type(n) is str and n in FIELDS[m] for n in i['fields']) and type(i['reason']) is str and i['reason'] in main.REASONS,'冲突字段或原因无效')
   main.safe_text(i['quote'],200);require(any(s['location']==i['location'] and i['quote'] in s['text'] for s in segments),'未支持记录原文或位置伪造')
   blocked.update(i['fields'])
  for n,f in part['fields'].items():
   if f is not None:
    require(n not in blocked,'冲突/未支持字段必须为空，不自动采用');validate_candidate(m,n,f,segments)
 return deepcopy(d)

def make_main(name,values,sources,segments,extraction,base):
 from . import academic_templates as a,table_templates as t
 carrier=main.defaults(base,extended=True);disabled=[n for n in main.ALL_FIELDS if values[n] is None]
 vals={n:carrier[n] if n in disabled else values[n] for n in main.ALL_FIELDS}
 ss={n:{'kind':'default_inherited','quote':'','location':None} if n in disabled else sources[n] for n in main.ALL_FIELDS}
 b=main.make_template(name,vals,ss,segments,base,extraction=extraction if extraction and extraction['kind']!='none' else None)
 b=a.make(b,{n:values[n] for n in a.EXTRA},{n:sources[n] for n in a.EXTRA},segments,base,name=name)
 b=t.make(b,{n:values[n] for n in t.EXTRA},{n:sources[n] for n in t.EXTRA},base)
 b=back.upgrade(b,base);b['final_values'].update({n:values[n] for n in back.EXTRA});b['field_sources'].update({n:sources[n] for n in back.EXTRA})
 return {'template':paragraphs.wrap(back.validate(b,base),values,sources,base),'disabled_fields':disabled}

def compile_bundle(d,base):
 d=validate(d,base);cfg=d['modules']['main'];require(cfg is not None,'执行规则包必须有明确的正文模块；补充模块请与当前正文规则核对后应用')
 out=main.compile_template(cfg['template'],base)
 out['workbench']={'version':1,'name':d['name'],'sha256':digest(d),'excerpt_sha256':d['excerpt_sha256'],'disabled_fields':cfg['disabled_fields'],'note_sources':deepcopy(d['provenance']['notes']),'notices':deepcopy(d.get('notices',{m:[] for m in MODULES})),'modules':{m:{'configured':c is not None,'version':c['template']['structure_version'] if c and m=='main' else c['structure_version'] if c else None,'sha256':digest(c) if c else None} for m,c in d['modules'].items()}}
 if d.get('assembly'):out['workbench']['assembly']=deepcopy(d['assembly'])
 out['name']=d['name'];out['version']='rule-bundle-1+'+out['version']
 return out

def project_checks(report,rules,classification):
 """Explicit no-check mask only. All executed checks/patches are existing engine code."""
 wb=rules.get('workbench')
 if not wb:return
 disabled=set(wb['disabled_fields']);removed=[];kept=[]
 simple={v[0]:n for n,v in main.FIELDS.items() if v[0]!='R02'}
 props={'font_eastAsia':'font_cn','size':'font_size','line':'line_spacing','alignment':'alignment'}
 for f in report['findings']:
  rid=f['rule_id'];name=simple.get(rid)
  if rid in ('R08','R09','R10','R12'):
   typ=(classification or {}).get('paragraph_types',{}).get(str(f['locator'].get('paragraph')))
   prop=props.get(f['locator'].get('property'));name=(typ+'_'+prop) if typ and prop else None
  if name in disabled:removed.append(f);continue
  if rid=='R02':
   names={side:('margin_'+side) for side in ('top','bottom','left','right')};expected={k:v for k,v in f['expected'].items() if names[k.removesuffix('_mm')] not in disabled}
   if not expected:removed.append(f);continue
   f['expected']=expected
   if f['status']!='review':f['status']='pass' if all(abs(f['actual'][k]-v)<=.03 for k,v in expected.items()) else 'problem';f['fixable']=f['status']=='problem' and f['fixable']
  kept.append(f)
 report['findings']=kept;report['rules']['workbench']=deepcopy(wb)
 report['coverage']['explicitly_not_checked_fields']=sorted(disabled)
 if report['rules'].get('note_supplement') and wb['note_sources']:report['rules']['note_supplement']['field_sources']=deepcopy(wb['note_sources'])
 # Do not remove coverage notes or hide complex objects. They retain their separate meaning.
 s=report['summary']
 for state,key in [('problem','problem_count'),('review','review_findings'),('pass','pass_count'),('not_applicable','not_applicable_count')]:s[key]=sum(f['status']==state for f in kept)
 s['review_count']=s['review_findings']+len(report['coverage_notes']);s['applicable_rule_count']=len({f['rule_id'] for f in kept if f['status']!='not_applicable'})
 inactive={rid for rid,n in simple.items() if n in disabled}
 if all('margin_'+a in disabled for a in ('top','bottom','left','right')):inactive.add('R02')
 s['rule_count']-=len(inactive)
 s['conclusion']='已覆盖检查发现问题' if s['problem_count'] else '已覆盖检查未发现问题'

def validate_state(w,base):
 exact({k:v for k,v in w.items() if k not in ('historical','diagnostics')},('active','draft','text','segments','confirmed_excerpt','receipt','parse_attempted','generation','origin'),'规范工作台状态无效')
 if 'diagnostics' in w:
  from .spec_diagnostics import validate_store
  store=validate_store(w['diagnostics'])
  if store['adopted_sha256']:
   require(store['current']['segments']==w['segments'] and store['current']['input_sha256']==w['confirmed_excerpt'],'已采用诊断与当前规范不符')
   from .spec_diagnostics import diagnose
   require(w['draft'] is not None,'已采用诊断缺少草稿')
   for short in diagnose(store['current'])['user_confirmed']:
    m,n=short.split('.')
    require(w['draft']['fields'][m][n]['mode']!='ai','修复来源不可冒充原始AI')
 require(type(w.get('historical',False)) is bool,'历史解析标记无效')
 if w['active'] is not None:validate(w['active'],base)
 require(type(w['text']) is str and len(w['text'])<=12000,'规范草稿文本超限')
 main.validate_segments(w['segments'])
 require(not w['segments'] or '\n'.join(s['text'] for s in w['segments'])=='\n'.join(t for t in w['text'].splitlines() if t.strip()),'规范草稿来源不一致')
 require(w['confirmed_excerpt'] is None or w['confirmed_excerpt']==sha256(marked_text(w['segments']).encode()),'规范草稿确认哈希不一致')
 require(type(w['parse_attempted']) is bool and type(w['generation']) is int and 0<=w['generation']<=100000 and w['origin'] in ('local','applied','historical_import','restored'),'工作台状态标记无效')
 if w['receipt'] is not None:
  from .project_editor import receipt
  receipt(w['receipt'])
 d=w['draft']
 if d is None:return deepcopy(w)
 exact(d,('name','baseline','fields','issues','strategies','imported'),'统一草稿状态结构无效');main.safe_text(d['name'],80);validate(d['baseline'],base);require(type(d['imported']) is bool,'导入标记无效');exact(d['fields'],MODULES,'草稿模块无效');exact(d['issues'],MODULES,'草稿提示模块无效')
 parsed={m:{'fields':{},'issues':d['issues'][m]} for m in MODULES}
 for m,fields in d['fields'].items():
  exact(fields,FIELDS[m],'草稿字段缺失或未知')
  for n,f in fields.items():
   exact(f,('mode','value','candidate'),'字段决策结构无效');require(f['mode'] in ('choose','keep','disabled','manual','ai','imported'),'字段决策无效')
   validate_value(m,n,f['value'])
   if f['candidate'] is not None:parsed[m]['fields'][n]=f['candidate']
   if f['mode']=='ai':require(f['candidate'] is not None and f['value']==f['candidate']['value'],'AI采用值不符')
 if any(f['candidate'] is not None for fs in d['fields'].values() for f in fs.values()):validate_draft(parsed,w['segments'])
 else:validate_notices(d['issues'],d['baseline']['excerpt'])
 require(type(d['strategies']) is list and len(d['strategies'])<=100,'批量策略无效')
 for s in d['strategies']:
  exact(s,('policy','fields'),'批量策略结构无效');require(s['policy'] in ('keep','disabled') and type(s['fields']) is list and len(s['fields'])==len(set(s['fields'])) and all(n in {m+'.'+f for m in MODULES for f in FIELDS[m]} for n in s['fields']),'批量策略字段无效')
 return deepcopy(w)

def blank_module(m,base):
 c=defaults(base)[m]
 if m=='notes':
  for k in c['values']:
   for p in c['values'][k]:c['values'][k][p]=None;c['sources'][k][p]='not_enabled'
 else:
  for n in c['values']:c['values'][n]=None;c['sources'][n]=deepcopy(EMPTY)
 return c

def validate_scope_templates(rules,classification):
 wb=rules.get('workbench')
 if not wb or not classification:return
 for m,scope in [('front','front_scope'),('toc','toc_scope'),('notes','note_scope')]:
  if not classification.get(scope):continue
  cfg=classification[scope]['template'];expected=wb['modules'][m]
  if expected['configured']:require(digest(cfg)==expected['sha256'],'确认范围中的'+LABELS[m]+'规则与当前规则包不一致，请重新核对')
  else:require(all(v is None for v in flat(m,cfg).values()),'规则包未配置该模块，不得静默使用旧范围中的要求')

def validate_notices(data,segments):
 exact(data,MODULES,'规范历史提示模块缺失或未知')
 for m,items in data.items():
  require(type(items) is list and len(items)<=100,'规范历史提示过多')
  for x in items:
   exact(x,('fields','quote','location','reason'),'规范历史提示结构无效')
   require(type(x['fields']) is list and all(type(n) is str and n in FIELDS[m] for n in x['fields']) and type(x['reason']) is str and x['reason'] in main.REASONS,'历史提示字段或原因无效')
   main.safe_text(x['quote'],200);require(any(s['location']==x['location'] and x['quote'] in s['text'] for s in segments),'历史提示原句或位置伪造')
 return deepcopy(data)

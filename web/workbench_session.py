"""Private draft/active orchestration. No object confirmation or document mutation here."""
from copy import deepcopy
from uuid import uuid4
from core import load_rules,effective_rules
from core.package import DemoError,write_new,sha256
from core import rule_bundle as rb
from core.norms import selected_segments,marked_text
from core.templates import validate_template

from .diagnostic_session import DiagnosticSession

class WorkbenchSession(DiagnosticSession):
 def init_workbench(self):
  self.workbench={'active':None,'draft':None,'text':'','segments':[],'confirmed_excerpt':None,'receipt':None,'parse_attempted':False,'generation':0,'origin':'local','historical':False}
 def current_rule_bundle(self):
  base=load_rules(self.rules_path);active=self.workbench['active'];mods=rb.defaults(base)
  if self.active_template:
   from core.back_templates import upgrade
   t=upgrade(self.active_template,base);disabled=(active or {}).get('modules',{}).get('main',{}).get('disabled_fields',[])
   if active and active['modules']['main']['template']!=self.active_template:disabled=[]
   mods['main']={'template':t,'disabled_fields':disabled}
  elif self.active_custom_data and self.active_custom_data.get('kind')=='user_confirmed_demo':
   values=rb.flat('main',mods['main']);ss=rb.origins('main',mods['main'])
   for n,rid in [('font_size','R05'),('line_spacing','R06')]:values[n]=self.active_custom_data['rules'][rid]['expected'];ss[n]={'kind':'user_confirmed','quote':'','location':None}
   mods['main']=rb.make_main('用户确认的兼容短规范要求',values,ss,[],None,base)
  elif active:mods['main']=deepcopy(active['modules']['main'])
  for m in ('front','toc','notes'):
   d=getattr(self,{'front':'front_draft','toc':'toc_draft','notes':'note_draft'}[m])
   mods[m]=deepcopy(d['template'] if d else active['modules'][m] if active else None)
  segments=deepcopy(active['excerpt'] if active else [])
  for x in mods['main']['template']['norm_excerpt']:
   if x not in segments:
    if any(y['location']==x['location'] for y in segments):raise DemoError('规范来源位置冲突，请先统一核对摘录')
    segments.append(x)
  if self.front_spec and not any(x['location']=='TEXT:1' for x in segments):
   if any(s['kind']=='ai_extracted' and s['location']=='TEXT:1' for s in (mods['front'] or {}).get('sources',{}).values()):
    segments.append({'location':'TEXT:1','text':self.front_spec})  # Original legacy front input marker, never a fabricated line mapping.
  provenance={m:rb.origins(m,c) if c else None for m,c in mods.items()}
  if active:
   for m,c in mods.items():
    if not c or not active['modules'][m]:continue
    oldvals=rb.flat(m,active['modules'][m]);newvals=rb.flat(m,c)
    for n,v in newvals.items():
     if v==oldvals[n] and rb.origins(m,c)[n]==rb.origins(m,active['modules'][m])[n]:provenance[m][n]=deepcopy(active['provenance'][m][n])
  extraction=active['extraction'] if active else mods['main']['template']['extraction']
  if extraction['kind']=='none' and any(s['kind']=='ai_extracted' for ss in provenance.values() if ss for s in ss.values()):
   extraction={k:self.front_ai_receipt[k] for k in ('kind','model','timestamp_utc')} if self.front_ai_receipt else {'kind':'unverified_import','model':None,'timestamp_utc':None}
  notices=deepcopy((active or {}).get('notices',{m:[] for m in rb.MODULES}))
  if active and 'notices' not in active and self.workbench['draft'] and self.workbench['receipt'] and self.workbench['receipt']['timestamp_utc']==active['extraction']['timestamp_utc']:
   notices=deepcopy(self.workbench['draft']['issues'])
  return rb.build(active['name'] if active else '用户确认的组合演示要求',mods,segments,extraction,base,provenance,notices)
 def seed_workbench_module(self,module,scope):
  active=self.workbench['active']
  if active and active['modules'][module] is not None:scope['template']=deepcopy(active['modules'][module])
  elif active:
   c=rb.defaults(load_rules(self.rules_path))[module]
   if module=='notes':
    for k in c['values']:
     for p in c['values'][k]:c['values'][k][p]=None;c['sources'][k][p]='not_enabled'
   else:
    for n in c['values']:c['values'][n]=None;c['sources'][n]=deepcopy(rb.EMPTY)
   scope['template']=c
  return scope
 def workbench_text(self,text,segments=None):
  if type(text) is not str or len(text)>12000:raise DemoError('公开摘录最多12000字符，不自动截断')
  w=self.workbench
  if segments:
   from core.norms import qualify_segments,source_group
   existing=(w['active'] or {}).get('excerpt',(self.active_template or {}).get('norm_excerpt',[]));byloc={s['location']:s['text'] for s in existing}
   if not any(source_group(s['location']) for s in segments) and any(s['location'] in byloc and byloc[s['location']]!=s['text'] for s in segments):segments=qualify_segments(segments)
  if text!=w['text'] or segments is not None and segments!=w['segments']:
   self.archive_diagnostic()
   w.update(text=text,segments=deepcopy(segments or []),confirmed_excerpt=None,draft=None,receipt=None,parse_attempted=False,generation=w['generation']+1,origin='local',historical=False)
 def confirm_workbench_excerpt(self):
  w=self.workbench
  if not w['segments']:
   existing=(w['active'] or {}).get('excerpt',[]);offset=max([int(x['location'].split('L')[-1]) for x in existing if x['location'].startswith('摘录:L')]+[0])
   w['segments']=[{'location':f'摘录:L{offset+i}','text':s['text']} for i,s in enumerate(selected_segments(w['text']),1)]
  rb.main.validate_segments(w['segments'])
  if not w['segments'] or '\n'.join(s['text'] for s in w['segments'])!='\n'.join(t for t in w['text'].splitlines() if t.strip()):raise DemoError('待发送摘录和来源不一致')
  w['confirmed_excerpt']=sha256(marked_text(w['segments']).encode())
 def parse_workbench(self,parser=None):
  w=self.workbench
  if w['parse_attempted']:raise DemoError('该摘录已请求一次；失败不自动重试。请明确重置请求状态后再次请求')
  if w['confirmed_excerpt']!=sha256(marked_text(w['segments']).encode()) or not w['segments']:raise DemoError('请先核对并确认待发送公开摘录')
  if self.norm_inventory and self.norm_path and any('TXT:' in s['location'] or 'DOCX:' in s['location'] for s in w['segments']):
   if sha256(self.norm_path.read_bytes())!=self.norm_inventory['file_sha256']:raise DemoError('规范文件已被外部修改，请重新导入；未发起API请求')
  ds=self.diagnostic_store()
  if ds['current'] and len(ds['history'])>=3:raise DemoError('诊断历史已满，请明确导出/清理后再请求；未发起API')
  w['parse_attempted']=True;w['historical']=False
  from ai.workbench_spec import parse_diagnosed
  if parser is not None:response=parser(deepcopy(w['segments']))
  else:
   record=parse_diagnosed(deepcopy(w['segments']))
   write_new(self._norm_directory()/('workbench-diagnosis-'+uuid4().hex+'.json'),rb.raw(record))
   return self.receive_diagnostic(record)
  d=rb.validate_draft(response['draft'],w['segments']);w['receipt']={k:response['receipt'][k] for k in ('kind','model','timestamp_utc')}
  self.start_workbench_draft(d)
  write_new(self._norm_directory()/('workbench-parse-'+uuid4().hex+'.json'),rb.raw(response))
  return response
 def start_workbench_draft(self,parsed=None):
  self.diagnostic_store()['adopted_sha256']=None
  w=self.workbench;current=self.current_rule_bundle()
  fields={m:{n:{'mode':'ai' if f else 'choose','value':deepcopy(f['value']) if f else None,'candidate':deepcopy(f)} for n in rb.FIELDS[m] for f in [(parsed or {}).get(m,{}).get('fields',{}).get(n)]} for m in rb.MODULES}
  w['draft']={'name':'课程论文组合演示要求','baseline':current,'fields':fields,'issues':{m:deepcopy((parsed or {}).get(m,{}).get('issues',[])) for m in rb.MODULES},'strategies':[],'imported':False};w['generation']+=1
 def workbench_edit(self,m,n,mode,value=None):
  d=self.workbench['draft']
  if not d or m not in rb.MODULES or n not in rb.FIELDS[m] or mode not in ('keep','disabled','manual','ai','imported'):raise DemoError('规则草稿字段或决策无效')
  f=d['fields'][m][n]
  if mode=='ai':
   if f['candidate'] is None:raise DemoError('没有AI字段可采用')
   value=f['candidate']['value']
  if mode=='manual':
   if value is None:raise DemoError('手动指定必须填写值')
   rb.validate_value(m,n,value)
  f.update(mode=mode,value=deepcopy(value));self.workbench['origin']='local'
 def workbench_policy(self,policy,*,acknowledged=False):
  if acknowledged is not True or policy not in ('keep','disabled'):raise DemoError('须明确核对批量策略及受影响字段')
  d=self.workbench['draft']
  if not d:raise DemoError('尚无规则草稿')
  affected=[]
  for m,fields in d['fields'].items():
   for n,f in fields.items():
    if f['mode']=='choose':self.workbench_edit(m,n,policy);affected.append(m+'.'+n)
  d['strategies'].append({'policy':policy,'fields':affected})
 def proposed_rule_bundle(self):
  w=self.workbench;d=w['draft']
  if not d:raise DemoError('尚无待确认草稿')
  self.validate_diagnostic_adoption()
  live=self.current_rule_bundle()
  base=load_rules(self.rules_path);segments=deepcopy(d['baseline']['excerpt'])
  if any(f['mode']=='keep' for fs in d['fields'].values() for f in fs.values()):
   for x in live['excerpt']:
    if x not in segments:segments.append(x)
  for s in w['segments']:
   if s not in segments:
    if any(x['location']==s['location'] for x in segments):raise DemoError('不同规范来源位置冲突，不能覆盖旧原文')
    segments.append(s)
  extraction=w['receipt'] or d['baseline']['extraction'];mods={};provenance={}
  for m,fields in d['fields'].items():
   prior=d['baseline']['modules'][m];oldvals=rb.flat(m,prior) if prior else {n:None for n in fields};vals={};ss={}
   for n,f in fields.items():
    mode=f['mode'];candidate=f['candidate']
    if mode=='choose':raise DemoError('未提及或冲突字段尚未决定：'+rb.LABELS[m]+' '+n)
    if mode in ('keep','imported'):
     record=live if mode=='keep' else d['baseline'];cfg=record['modules'][m]
     vals[n]=rb.flat(m,cfg)[n] if cfg else None;ss[n]=deepcopy(record['provenance'][m][n]) if cfg else deepcopy(rb.EMPTY)
     if mode=='keep' and ss[n]['kind']=='ai_extracted':ss[n]['kind']='user_confirmed'
    elif mode=='disabled':vals[n]=None;ss[n]=deepcopy(rb.EMPTY)
    else:
     vals[n]=deepcopy(f['value']);ss[n]={'kind':'ai_extracted' if mode=='ai' else 'user_confirmed','quote':candidate['quote'] if candidate else '', 'location':candidate['location'] if candidate else None}
    rb.validate_value(m,n,vals[n])
   provenance[m]=ss
   if all(v is None for v in vals.values()) and prior is None and live['modules'][m] is None and all(f['mode'] in ('keep','imported') for f in fields.values()):mods[m]=None;provenance[m]=None;continue
   if m=='main' and prior and vals==rb.flat(m,prior) and ss==d['baseline']['provenance'][m]:mods[m]=deepcopy(prior);continue
   if m=='main':mods[m]=rb.make_main(d['name'],vals,ss,segments,extraction,base)
   elif m=='notes':
    c=rb.notes.school();c['name']=d['name'];c['values']={k:{p:vals[k+'__'+p] for p in rb.notes.FIELDS} for k in rb.notes.KINDS};c['sources']={k:{p:('not_enabled' if vals[k+'__'+p] is None else 'school_default' if ss[k+'__'+p]['kind']=='school_default' else 'user_confirmed') for p in rb.notes.FIELDS} for k in rb.notes.KINDS};mods[m]=rb.notes.template(c)
   else:
    c=rb.front.school() if m=='front' else rb.toc.school();c.update(name=d['name'],values=vals,sources=ss);mods[m]=c
  notices=deepcopy(d['baseline'].get('notices',{m:[] for m in rb.MODULES}))
  for m,issues in d['issues'].items():
   for issue in issues:
    if issue not in notices[m]:notices[m].append(deepcopy(issue))
  return rb.build(d['name'],mods,segments,extraction,base,provenance,notices)
 def apply_workbench(self,*,acknowledged=False):
  if acknowledged is not True:raise DemoError('须核对全部差异及完整配置后确认应用')
  if self.mode!='academic':raise DemoError('统一工作台只在单文档模式应用')
  if self.inventory:self._current()
  d=self.proposed_rule_bundle();base=load_rules(self.rules_path);rb.compile_bundle(d,base)
  # Validate every existing object draft against new module values before writing or publishing anything.
  staged={}
  for m,attr,validator in [('front','front_draft',__import__('core.front',fromlist=['validate_scope']).validate_scope),('toc','toc_draft',__import__('core.toc',fromlist=['validate_scope']).validate_scope),('notes','note_draft',__import__('core.notes',fromlist=['validate_scope']).validate_scope)]:
   old=getattr(self,attr)
   if old:
    c=deepcopy(old);c['confirmed']=False
    c['template']=deepcopy(d['modules'][m]) if d['modules'][m] is not None else rb.blank_module(m,base)
    if self.inventory:
     from core.package import Package
     validator(Package(self.input_path),c,confirmed=False)
    staged[attr]=c
  directory=self.task_dir or self._norm_directory();path=directory/('user-rules-'+uuid4().hex+'.json')
  try:
   write_new(path,rb.raw(d));compiled=effective_rules(custom_rules_path=path,mode=self.mode)
  except Exception:
   path.unlink(missing_ok=True);raise
  # All potentially failing validation/storage has finished. Publish one canonical configuration.
  file_hash=sha256(path.read_bytes())
  self.custom_rules_path=path;self.active_template=deepcopy(d['modules']['main']['template']);self.active_template_sha256=file_hash;self.active_custom_data=deepcopy(compiled)
  self.workbench['active']=deepcopy(d)
  for attr,c in staged.items():setattr(self,attr,c)
  self.invalidate();self.rules_hash=compiled['sha256'];self.template_error=None
  self.workbench['origin']='applied';self.workbench['generation']+=1
  self.template_draft=self.template_receipt=None;self.template_import=deepcopy(self.active_template)
  self.template_values=deepcopy(self.active_template['final_values']);self.template_modes={n:'imported' for n in self.template_values};self.template_touched=set();self.template_name=d['name']
  self.norm_segments=deepcopy(self.active_template['norm_excerpt']);self.norm_text='\n'.join(x['text'] for x in self.norm_segments);self.template_generation+=1
  return d
 def import_rule_bundle(self,content):
  imported_module=None
  base=load_rules(self.rules_path)
  try:obj=rb.loads(content,base)
  except DemoError:
   from core.rule_config import strict_json
   if type(content) is not bytes or len(content)>rb.MAX_BYTES:raise
   obj=strict_json(content.decode('utf-8'));current=self.current_rule_bundle();mods=deepcopy(current['modules'])
   if obj.get('format')=='paper-grid-front-supplement':m='front';obj=rb.front.loads(content)
   elif obj.get('format')=='paper-grid-toc-supplement':m='toc';obj=rb.toc.loads(content)
   elif obj.get('kind')=='paper-grid-note-supplement':m='notes';obj=rb.notes.template(obj)
   elif obj.get('structure_version') in (2,3,4,5,6):
    m='main';obj={'template':rb.back.upgrade(validate_template(obj,base),base),'disabled_fields':[]}
   else:raise DemoError('不是受支持的规则包、旧模板或独立补充JSON')
   if m=='main':
    oldloc={s['location']:s['text'] for s in current['excerpt']}
    incoming=obj['template']['norm_excerpt']
    if any(s['location'] in oldloc and oldloc[s['location']]!=s['text'] for s in incoming):
     from core.norms import qualify_segments
     qualified=qualify_segments(incoming);mapping={a['location']:b['location'] for a,b in zip(incoming,qualified)}
     obj['template']['norm_excerpt']=qualified
     for source in obj['template']['field_sources'].values():
      if source['location'] in mapping:source['location']=mapping[source['location']]
     validate_template(obj['template'],base)
   imported_module=m
   mods[m]=obj;segs=deepcopy(current['excerpt'])
   if m=='front' and self.front_spec and any(x['kind']=='ai_extracted' and x['location']=='TEXT:1' for x in obj['sources'].values()):
    if {'location':'TEXT:1','text':self.front_spec} not in segs:segs.append({'location':'TEXT:1','text':self.front_spec})
   if m=='main':
    for s in obj['template']['norm_excerpt']:
     if s not in segs:segs.append(s)
   sources=deepcopy(current['provenance']);sources[m]=rb.origins(m,obj)
   obj=rb.build('导入的组合演示要求',mods,segs,obj['template']['extraction'] if m=='main' else current['extraction'],base,sources,current.get('notices'))
  self.archive_diagnostic()
  w=self.workbench;w.update(text='',segments=[],confirmed_excerpt=None,receipt=None,parse_attempted=False,origin='historical_import',historical=True)
  self.start_workbench_draft();w['draft']['issues']=deepcopy(obj.get('notices',{m:[] for m in rb.MODULES}));w['draft']['baseline']=obj;w['draft']['name']=obj['name'];w['draft']['imported']=True
  w['segments']=deepcopy(obj['excerpt']);w['text']='\n'.join(s['text'] for s in w['segments'])
  for module,fields in w['draft']['fields'].items():
   for f in fields.values():f.update(mode='choose' if imported_module is not None and module!=imported_module else 'imported',value=None,candidate=None)
 def rule_bundle_download(self):
  if self.custom_rules_path:self._current() if self.inventory else self.sync_rules()
  if self.rules_hash is None:raise DemoError('当前规则文件未通过校验，拒绝导出旧规则包')
  return rb.raw(self.current_rule_bundle())
 def workbench_native_change(self,module,cfg):
  active=self.workbench['active']
  if not active or active['modules'][module]==cfg:return
  d=self.current_rule_bundle();d['modules'][module]=deepcopy(cfg);d['provenance'][module]=rb.origins(module,cfg)
  d=rb.validate(d,load_rules(self.rules_path));path=(self.task_dir or self._norm_directory())/('user-rules-'+uuid4().hex+'.json')
  write_new(path,rb.raw(d));compiled=effective_rules(custom_rules_path=path,mode=self.mode)
  self.workbench['active']=d;self.custom_rules_path=path;self.active_template_sha256=sha256(path.read_bytes());self.active_template=deepcopy(d['modules']['main']['template']);self.rules_hash=compiled['sha256'];self.active_custom_data=compiled

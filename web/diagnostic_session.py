"""Session-only diagnosis/repair; no network outside the explicit parse action."""
from copy import deepcopy
from core import spec_diagnostics as sd,rule_bundle as rb
from core.package import DemoError,sha256,write_new
from core.norms import marked_text

class DiagnosticSession:
 def diagnostic_store(self):return self.workbench.setdefault('diagnostics',{'current':None,'history':[],'adopted_sha256':None})
 def archive_diagnostic(self):
  s=self.diagnostic_store()
  if s['current']:
   if len(s['history'])>=sd.MAX_HISTORY:raise DemoError('已有3份历史诊断，请先导出并明确清理历史；没有丢弃记录')
   s['history'].append(deepcopy(s['current']));s['current']=None;s['adopted_sha256']=None
 def receive_diagnostic(self,record,*,historical=False):
  r=sd.validate_record(record);w=self.workbench
  if not w['confirmed_excerpt'] or w['segments']!=r['segments'] or w['confirmed_excerpt']!=r['input_sha256']:raise DemoError('诊断与当前已确认规范快照不符；不能用当前规范冒充历史输入')
  staged=deepcopy(self.diagnostic_store())
  if staged['current']:
   if len(staged['history'])>=sd.MAX_HISTORY:raise DemoError('历史已满，请明确导出/清理后继续')
   staged['history'].append(staged['current'])
  staged.update(current=r,adopted_sha256=None);sd.validate_store(staged);self.workbench['diagnostics']=staged;w['draft']=None;w['receipt']=None;w['historical']=historical;w['generation']+=1;w['origin']='local'
  return sd.diagnose(r)
 def diagnostic_analysis(self):
  s=self.diagnostic_store()
  return sd.diagnose(s['current']) if s['current'] else None
 def _diagnostic_current(self):
  s=self.diagnostic_store();r=s['current'];w=self.workbench
  if r is None or r['segments']!=w['segments'] or r['input_sha256']!=w['confirmed_excerpt']:raise DemoError('规范已改变，旧诊断只保留历史，不能继续采用')
  return r
 def repair_diagnostic(self,path,action,data,reason):
  r=sd.revise(self._diagnostic_current(),path,action,data,reason);s=self.diagnostic_store();staged=deepcopy(s);staged.update(current=r,adopted_sha256=None);sd.validate_store(staged);s['current']=r
  if s['adopted_sha256']:self.workbench['draft']=None
  s['adopted_sha256']=None;self.workbench['generation']+=1
  return sd.diagnose(r)
 def repair_unique_sources(self,paths,*,acknowledged=False):
  if acknowledged is not True or type(paths) is not list or not paths:raise DemoError('须明确核对并选择唯一来源修复对象')
  r=deepcopy(self._diagnostic_current());a=sd.diagnose(r)
  for path in paths:
   short=path.split('.')[0]+'.'+path.split('.')[-1];f=a['fields'].get(short)
   if not f or not f['suggestion']:raise DemoError('含糊/无唯一映射字段不能批量修复')
   c=deepcopy(f['raw']);c['location']=f['suggestion']['to']
   r=sd.revise(r,path,'candidate',c,'用户核对原行号、唯一连续原句后明确采用来源映射')
  s=self.diagnostic_store();staged=deepcopy(s);staged.update(current=r,adopted_sha256=None);sd.validate_store(staged);s['current']=r
  if s['adopted_sha256']:self.workbench['draft']=None
  s['adopted_sha256']=None;self.workbench['generation']+=1;return sd.diagnose(r)
 def use_diagnostic_draft(self,*,acknowledged=False):
  if acknowledged is not True:raise DemoError('须核对诊断、全部本地决定和候选后明确转入规则草稿')
  r=self._diagnostic_current();a=sd.diagnose(r)
  if a['status']!='validated':raise DemoError('仍有隔离字段或整体拒绝，不能转入规则草稿')
  # Same strict full-input validator as the original public parser. No relaxed execution path.
  rb.validate_draft(a['strict_draft'],r['segments'])
  self.start_workbench_draft(a['strict_draft'])
  for short in a['user_confirmed']:
   m,n=short.split('.');decision=a['decisions'].get(short);f=self.workbench['draft']['fields'][m][n]
   if decision:
    self.workbench_edit(m,n,'manual' if decision['action']=='manual' else 'disabled',decision['data'])
   else:self.workbench_edit(m,n,'manual',a['fields'][short]['candidate']['value'])
  receipt=r['receipt'];self.workbench['receipt']={k:receipt[k] for k in ('kind','model','timestamp_utc')} if receipt else None
  # Synthetic diagnostics cannot claim an API call. User-confirm all candidates in that case.
  if receipt is None:
   for m,fields in self.workbench['draft']['fields'].items():
    for n,f in fields.items():
     if f['mode']=='ai':self.workbench_edit(m,n,'manual',f['value'])
  self.diagnostic_store()['adopted_sha256']=rb.digest(r)
  self.workbench['generation']+=1
 def diagnostic_download(self):
  s=sd.validate_store(self.diagnostic_store());return rb.raw({'format':'paper-grid-spec-diagnostic-export','version':1,'store':s,'notice':'不可信原始模型文本及规范快照；导入/恢复为历史，不证明本次API调用'})
 def import_diagnostic(self,raw):
  if type(raw) is not bytes or len(raw)>1024*1024:raise DemoError('诊断JSON最多1MB')
  from core.rule_config import strict_json
  d=strict_json(raw.decode('utf-8'));rb.exact(d,('format','version','store','notice'),'诊断导出结构无效')
  if d['format']!='paper-grid-spec-diagnostic-export' or type(d['version']) is not int or d['version']!=1:raise DemoError('诊断版本不支持')
  s=sd.validate_store(d['store']);r=s['current']
  if r is None:raise DemoError('导出中没有当前诊断，请查看其中历史记录')
  self.receive_diagnostic(r,historical=True)  # Never adopts imported "passed" claims.
 def load_synthetic_diagnostic(self):
  from pathlib import Path
  root=Path(__file__).resolve().parents[1];r=sd.validate_record(__import__('json').loads((root/'samples/phase25/synthetic-response.json').read_text()))
  self.workbench_text('\n'.join(s['text'] for s in r['segments']),r['segments']);self.confirm_workbench_excerpt();return self.receive_diagnostic(r,historical=True)

 def validate_diagnostic_adoption(self):
  s=sd.validate_store(self.diagnostic_store())
  if s['adopted_sha256']:
   r=self._diagnostic_current();a=sd.diagnose(r)
   if a['status']!='validated':raise DemoError('诊断尚未通过全量重新校验')
   for short in a['user_confirmed']:
    m,n=short.split('.')
    if self.workbench['draft']['fields'][m][n]['mode']=='ai':raise DemoError('本地修复字段不得冒充原始AI提取值')

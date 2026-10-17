"""Explicit table draft/confirmation; no mutable parsed XML retained in sessions."""
from copy import deepcopy
from core.table_text import inventory,validate_scope,TYPES,PATH
from core.package import Package,DemoError,sha256,q

class TableSession:
 def init_tables(self):
  self.table_explicit_choice=None;self.table_enabled=False;self.table_types={};self.table_confirmed=None;self.table_layout_options=None
 def table_inventory(self):
  self._current();return self.cached_data(('table-inventory',self.inventory['input_sha256']),lambda:inventory(self.input_path))
 def set_table_enabled(self,enabled):
  if type(enabled) is not bool or self.mode!='academic':raise DemoError('表格普通文字仅用于单文档模式')
  self.table_explicit_choice=enabled
  if self.table_enabled!=enabled:self.table_enabled=enabled;self.invalidate()
 def set_table_types(self,types):
  self._current();scope={'input_sha256':self.inventory['input_sha256'],'table_types':types,'confirmed':False,'confirmation':'网页表格类型草稿'}
  validate_scope(Package(self.input_path),scope,confirmed=False)
  if self.table_types!=types:
   self.table_types=deepcopy(types)
   if self.table_layout_options:self.table_layout_options['headers']={n:c for n,c in self.table_layout_options['headers'].items() if types[n]=='content'}
   self.invalidate()
 def confirm_tables(self):
  self._current()
  if not self.table_enabled:raise DemoError('请先明确启用表内文字检查')
  scope={'input_sha256':self.inventory['input_sha256'],'table_types':deepcopy(self.table_types),'confirmed':True,'confirmation':'网页人工核对论文内容/封面/其他表格',**({'layout_options':deepcopy(self.table_layout_options)} if self.table_layout_options else {})}
  validate_scope(Package(self.input_path),scope);self.table_confirmed={'scope':scope,'rules_hash':self.rules_hash,'policy_hash':sha256(PATH.read_bytes())}
 def table_manifest(self):
  if not self.table_enabled or self.mode!='academic':return None
  c=self.table_confirmed
  if c is None or c['rules_hash']!=self.rules_hash or c['policy_hash']!=sha256(PATH.read_bytes()) or c['scope']['input_sha256']!=self.inventory['input_sha256'] or c['scope']['table_types']!=self.table_types or c['scope'].get('layout_options')!=self.table_layout_options:raise DemoError('表格范围或规则已变化，请重新核对并确认表格')
  return deepcopy(c['scope'])


 def table_requirements(self):
  self._current()
  from core import effective_rules
  from .session import digest
  def read():
   cfg=effective_rules(**self._base_rules_arguments(),mode=self.mode)
   from core.table_text import requirements
   return requirements(cfg)['values']
  return self.cached_data(('table-requirements',self.rules_hash,self.mode,digest(PATH.read_bytes())),read)

 def set_table_layout_options(self,options):
  self._current()
  from core.table_edges import validate_options
  if options is not None:validate_options(Package(self.input_path),options,self.table_types)
  if options!=self.table_layout_options:self.table_layout_options=deepcopy(options);self.invalidate()
 def table_edge_inventory(self):
  self._current()
  from core.table_edges import evidence,header_value
  from core.table_text import tables
  from core.formats import Unresolved
  pkg=Package(self.input_path);out=[]
  for n,t in enumerate(tables(pkg),1):
   row={'table':n,'cells':sum(len(r.findall(q('tc'))) for r in t.findall(q('tr')))}
   for side in ('left','right'):
    try:row[side]=evidence(pkg,t,side)
    except Unresolved as exc:row[side]={'unresolved':str(exc)}
   try:row['current_headers']=[i for i,r in enumerate(t.findall(q('tr')),1) if header_value(r)]
   except Unresolved as exc:row['current_headers']=str(exc)
   out.append(row)
  return out

 def export_table_options(self):
  self._current()
  import json
  if not self.table_layout_options:raise DemoError('尚未启用表格补充配置')
  return json.dumps({'input_sha256':self.inventory['input_sha256'],'layout_options':self.table_layout_options},ensure_ascii=False,indent=2).encode()
 def import_table_options(self,raw):
  from core.rule_config import strict_json
  self._current()
  if len(raw)>65536:raise DemoError('表格补充配置超过64KB')
  try:data=strict_json(raw.decode('utf-8'))
  except (UnicodeError,AttributeError):raise DemoError('请导入UTF-8表格补充配置') from None
  if type(data) is not dict or set(data)!={'input_sha256','layout_options'} or data['input_sha256']!=self.inventory['input_sha256']:raise DemoError('补充配置与当前输入哈希不匹配，请核对文件')
  self.set_table_layout_options(data['layout_options'])

 def table_header_preview(self,ident,count):
  self._current()
  from core.table_text import tables,text
  from core.table_edges import header_value
  from core.formats import Unresolved
  pkg=Package(self.input_path)
  if type(ident) is not int or not 1<=ident<=len(tables(pkg)) or type(count) is not int or count<0:raise DemoError('表头预览编号无效')
  out=[]
  for i,r in enumerate(tables(pkg)[ident-1].findall(q('tr'))[:count],1):
   try:flag='已开启' if header_value(r) else '未开启'
   except Unresolved as exc:flag='待复核：'+str(exc)
   out.append({'行':i,'简短文字':text(r)[:80],'当前tblHeader':flag})
  return out

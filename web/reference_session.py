"""Explicit private reference scope/configuration. Never invokes AI."""
from copy import deepcopy
import json
from core.package import Package,DemoError
from core.internal_refs import make_scope,validate_scope,inventory,template,digest
from core.rule_config import strict_json
class ReferenceSession:
 def init_references(self):self.reference_enabled=False;self.reference_draft=None;self.reference_confirmed=None
 def enable_references(self,value):
  self._current()
  if self.mode!='academic' or type(value) is not bool:raise DemoError('内部引用检查须在单文档模式明确启用')
  if value!=self.reference_enabled:
   self.reference_enabled=value
   if not self.reference_draft or self.reference_draft['input_sha256']!=self.inventory['input_sha256']:self.reference_draft=make_scope(Package(self.input_path))
   self.invalidate()
 def reference_inventory(self):
  self._current();return self.cached_data(('references',self.inventory['input_sha256']),lambda:inventory(self.input_path))
 def edit_references(self,s):
  self._current();validate_scope(Package(self.input_path),s,confirmed=False)
  if s!=self.reference_draft:self.reference_draft=deepcopy(s);self.invalidate()
 def confirm_references(self):
  self._current()
  if not self.reference_enabled or not self.reference_draft:raise DemoError('请先启用并核对内部引用范围')
  s=deepcopy(self.reference_draft);s.update(confirmed=True,confirmation='网页人工核对内部引用只读检查和可选普通内部链接文字支持')
  validate_scope(Package(self.input_path),s);self.reference_draft=s;self.reference_confirmed={'scope':deepcopy(s),'rules_hash':self.rules_hash}
 def reference_manifest(self):
  if not self.reference_enabled or self.mode!='academic':return None
  c=self.reference_confirmed
  if not c or c['rules_hash']!=self.rules_hash or c['scope']!=self.reference_draft:raise DemoError('内部引用范围或配置变化，请重新确认')
  validate_scope(Package(self.input_path),c['scope']);return deepcopy(c['scope'])
 def adopt_reference_scope(self,s,confirmed=False):
  self.reference_enabled=True;self.reference_draft=deepcopy(s);self.reference_draft['input_sha256']=self.inventory['input_sha256'];self.reference_confirmed=None
  if confirmed:self.confirm_references()
 def reference_binding(self):return (digest(self.reference_draft['template']),) if self.mode=='academic' and self.reference_enabled else ()
 def reference_template_bytes(self):return json.dumps(template(self.reference_draft['template']),ensure_ascii=False,indent=2).encode()
 def import_reference_template(self,raw):
  if not self.reference_enabled or not self.reference_draft:raise DemoError('请先启用内部引用范围')
  if len(raw)>65536:raise DemoError('内部引用配置超过64KB')
  try:d=template(strict_json(raw.decode('utf-8')))
  except UnicodeError:raise DemoError('配置须为UTF-8 JSON') from None
  s=deepcopy(self.reference_draft);s['template']=d;self.edit_references(s)

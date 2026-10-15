"""Session owned TOC draft, explicit scope/level and supplement confirmation."""
from copy import deepcopy
import json
from core.package import Package,DemoError,sha256
from core.toc import inventory,make_scope,validate_scope
from core.toc_template import validate,digest
class TocSession:
 def init_toc(self):self.toc_enabled=False;self.toc_draft=None;self.toc_confirmed=None
 def toc_inventory(self):
  self._current();return self.cached_data(('toc-inventory',self.inventory['input_sha256']),lambda:inventory(self.input_path))
 def enable_toc(self,value):
  self._current()
  if self.mode!='academic' or type(value) is not bool:raise DemoError('目录检查须在单文档模式明确启用')
  stale=self.toc_draft is None or self.toc_draft['input_sha256']!=self.inventory['input_sha256']
  if value!=self.toc_enabled or value and stale:
   self.toc_enabled=value
   if stale:
    previous=deepcopy(self.toc_draft['template']) if self.toc_draft else None
    self.toc_draft=self.seed_workbench_module("toc",make_scope(self.input_path))
    if previous is not None:self.toc_draft['template']=previous
   self.invalidate()
 def edit_toc(self,scope):
  self._current();validate_scope(Package(self.input_path),scope,confirmed=False)
  self.workbench_native_change("toc",scope["template"])
  if scope!=self.toc_draft:self.toc_draft=deepcopy(scope);self.invalidate()
 def confirm_toc(self):
  self._current()
  if not self.toc_enabled or self.toc_draft is None:raise DemoError('先启用并核对目录对象和级别')
  d=deepcopy(self.toc_draft);d.update(confirmed=True,confirmation='网页人工核对目录对象、级别及覆盖声明；实际页码未核对')
  validate_scope(Package(self.input_path),d);self.toc_draft=deepcopy(d);self.toc_confirmed={'scope':d,'rules_hash':self.rules_hash}
 def toc_manifest(self):
  if not self.toc_enabled or self.mode!='academic':return None
  c=self.toc_confirmed
  if not c or c['rules_hash']!=self.rules_hash or c['scope']!=self.toc_draft:raise DemoError('目录范围、层级或模板变化，请重新核对确认')
  validate_scope(Package(self.input_path),c['scope']);return deepcopy(c['scope'])
 def adopt_toc_scope(self,s,confirmed=False):
  self.toc_enabled=True;self.toc_draft=deepcopy(s);self.toc_draft['input_sha256']=self.inventory['input_sha256'];self.toc_confirmed=None
  if confirmed:self.confirm_toc()
 def toc_template_bytes(self):return (json.dumps(validate(self.toc_draft['template']),ensure_ascii=False,indent=2)+'\n').encode()

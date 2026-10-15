"""Explicit private note scope/configuration. Never invokes AI."""
from copy import deepcopy
import json
from core.package import Package,DemoError
from core.notes import make_scope,validate_scope,inventory,template,digest
from core.rule_config import strict_json
class NoteSession:
 def init_notes(self):self.note_enabled=False;self.note_draft=None;self.note_confirmed=None
 def enable_notes(self,value):
  self._current()
  if self.mode!='academic' or type(value) is not bool:raise DemoError('注释检查须在单文档模式明确启用')
  if value!=self.note_enabled:
   self.note_enabled=value
   if not self.note_draft or self.note_draft['input_sha256']!=self.inventory['input_sha256']:self.note_draft=self.seed_workbench_module("notes",make_scope(Package(self.input_path)))
   self.invalidate()
 def note_inventory(self):
  self._current();return self.cached_data(('notes',self.inventory['input_sha256']),lambda:inventory(self.input_path))
 def edit_notes(self,s):
  self._current();validate_scope(Package(self.input_path),s,confirmed=False)
  self.workbench_native_change("notes",s["template"])
  if s!=self.note_draft:self.note_draft=deepcopy(s);self.invalidate()
 def confirm_notes(self):
  self._current()
  if not self.note_enabled or not self.note_draft:raise DemoError('请先启用并核对注释范围')
  s=deepcopy(self.note_draft);s.update(confirmed=True,confirmation='网页人工核对Word注释范围与配置')
  validate_scope(Package(self.input_path),s);self.note_draft=s;self.note_confirmed={'scope':deepcopy(s),'rules_hash':self.rules_hash}
 def note_manifest(self):
  if not self.note_enabled or self.mode!='academic':return None
  c=self.note_confirmed
  if not c or c['rules_hash']!=self.rules_hash or c['scope']!=self.note_draft:raise DemoError('注释范围或配置变化，请重新确认')
  validate_scope(Package(self.input_path),c['scope']);return deepcopy(c['scope'])
 def adopt_note_scope(self,s,confirmed=False):
  self.note_enabled=True;self.note_draft=deepcopy(s);self.note_draft['input_sha256']=self.inventory['input_sha256'];self.note_confirmed=None
  if confirmed:self.confirm_notes()
 def note_binding(self):return (digest({k:self.note_draft[k] for k in ('objects','template')}),) if self.mode=='academic' and self.note_enabled else ()
 def note_template_bytes(self):return json.dumps(template(self.note_draft['template']),ensure_ascii=False,indent=2).encode()
 def import_note_template(self,raw):
  if not self.note_enabled or not self.note_draft:raise DemoError('请先启用注释范围')
  if len(raw)>65536:raise DemoError('注释配置超过64KB')
  try:d=template(strict_json(raw.decode('utf-8')))
  except UnicodeError:raise DemoError('配置须为UTF-8 JSON') from None
  s=deepcopy(self.note_draft);s['template']=d;self.edit_notes(s)

"""Session-only citation draft and user confirmation. No network or rendering."""
from copy import deepcopy
import json
from core.package import Package,DemoError
from core.citations import make_scope,validate_scope,inventory,template
class CitationSession:
 def init_citations(self):self.citation_enabled=False;self.citation_draft=None;self.citation_confirmed=None
 def enable_citations(self,value):
  self._current()
  if self.mode!='academic' or type(value) is not bool:raise DemoError('引文检查须在单文档模式明确启用')
  if value!=self.citation_enabled or value and (not self.citation_draft or self.citation_draft['input_sha256']!=self.inventory['input_sha256']):
   self.citation_enabled=value
   if not self.citation_draft or self.citation_draft['input_sha256']!=self.inventory['input_sha256']:self.citation_draft=make_scope(Package(self.input_path),[int(n) for n,t in self.paragraph_types.items() if t=='body'])
   self.invalidate()
 def citation_inventory(self):
  self._current();return self.cached_data(('citations',self.inventory['input_sha256'],tuple(self.citation_draft['scan']),json.dumps(self.citation_draft['template'],sort_keys=True)),lambda:inventory(self.input_path,self.citation_draft['scan'],self.citation_draft['template']))
 def edit_citations(self,s):
  self._current();validate_scope(Package(self.input_path),s,{'paragraph_types':self.paragraph_types},confirmed=False)
  if self.citation_draft!=s:self.citation_draft=deepcopy(s);self.invalidate()
 def confirm_citations(self):
  self._current()
  if not self.citation_enabled or not self.citation_draft:raise DemoError('请先启用并核对引文用途')
  s=deepcopy(self.citation_draft);s.update(confirmed=True,confirmation='网页人工核对引文准确范围、用途及完整性声明')
  validate_scope(Package(self.input_path),s,{'paragraph_types':self.paragraph_types});self.citation_draft=s;self.citation_confirmed={'scope':deepcopy(s),'rules_hash':self.rules_hash}
 def citation_manifest(self):
  if not self.citation_enabled or self.mode!='academic':return None
  c=self.citation_confirmed
  if not c or c['rules_hash']!=self.rules_hash or c['scope']!=self.citation_draft:raise DemoError('引文范围、用途或配置变化，请重新确认')
  validate_scope(Package(self.input_path),c['scope'],{'paragraph_types':self.paragraph_types});return deepcopy(c['scope'])
 def adopt_citation_scope(self,s,confirmed=False):
  self.citation_enabled=True;self.citation_draft=deepcopy(s);self.citation_draft['input_sha256']=self.inventory['input_sha256'];self.citation_confirmed=None
  if confirmed:self.confirm_citations()
 def citation_template_bytes(self):return (json.dumps(template(self.citation_draft['template']),ensure_ascii=False,indent=2)+'\n').encode()
 def citation_binding(self):
  from core.package import sha256
  return (sha256(json.dumps({k:self.citation_draft[k] for k in ('scan','objects','complete','references_complete','template')},sort_keys=True,ensure_ascii=False).encode()),) if self.mode=='academic' and self.citation_enabled else ()

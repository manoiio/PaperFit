"""Private front-scope draft; explicit confirmation, legacy modes unchanged."""
from copy import deepcopy
import json
from core.package import Package,DemoError,sha256
from core.front import make_scope,inventory,validate_scope
from core.front_template import validate as validate_template,digest
class FrontSession:
 def init_front(self):self.front_enabled=False;self.front_draft=None;self.front_confirmed=None;self.front_ai_draft=None;self.front_ai_receipt=None;self.front_spec=''
 def front_inventory(self):
  self._current();return self.cached_data(('front-inventory',self.inventory['input_sha256']),lambda:inventory(self.input_path))
 def enable_front(self,enabled):
  self._current()
  if self.mode!='academic' or type(enabled) is not bool:raise DemoError('封面/页眉页脚只在单文档模式明确启用')
  if enabled!=self.front_enabled:
   self.front_enabled=enabled
   if self.front_draft is None:self.front_draft=self.seed_workbench_module("front",make_scope(self.input_path))
   self.invalidate()
 def edit_front(self,scope):
  self._current();validate_scope(Package(self.input_path),scope,confirmed=False)
  self.workbench_native_change("front",scope["template"])
  if scope!=self.front_draft:self.front_draft=deepcopy(scope);self.invalidate()
 def confirm_front(self):
  self._current()
  if not self.front_enabled or self.front_draft is None:raise DemoError('请明确启用并核对封面和节范围')
  d=deepcopy(self.front_draft);d.update(confirmed=True,confirmation='网页人工核对封面对象与节用途；不补造信息')
  validate_scope(Package(self.input_path),d);self.front_draft=deepcopy(d);self.front_confirmed={'scope':d,'rules_hash':self.rules_hash}
 def front_manifest(self):
  if not self.front_enabled or self.mode!='academic':return None
  c=self.front_confirmed
  if not c or c['rules_hash']!=self.rules_hash or c['scope']!=self.front_draft:raise DemoError('封面/节范围或配置变化，请重新核对确认')
  validate_scope(Package(self.input_path),c['scope']);return deepcopy(c['scope'])
 def adopt_front_scope(self,scope,confirmed=False):
  self.front_enabled=True;self.front_draft=deepcopy(scope);self.front_draft['input_sha256']=self.inventory['input_sha256'];self.front_confirmed=None
  if confirmed:self.confirm_front()
 def front_template_bytes(self):
  self._current();return (json.dumps(validate_template(self.front_draft['template']),ensure_ascii=False,indent=2)+'\n').encode()
 def set_front_spec(self,text):
  if not isinstance(text,str) or len(text)>2000:raise DemoError('规范摘录最多2000字符')
  if text!=self.front_spec:self.front_spec=text;self.front_ai_draft=self.front_ai_receipt=None
 def parse_front(self,*,parser=None):
  if self.front_ai_draft is not None:raise DemoError('已有对应草稿；再次解析须先修改规范')
  from ai.front_spec import parse_requirements
  result=(parser or parse_requirements)(self.front_spec);draft=result['draft'];receipt=result['receipt']
  from core.front_template import validate_draft
  self.front_ai_draft=validate_draft(draft,self.front_spec);self.front_ai_receipt=receipt
 def use_front_ai_draft(self):
  if self.front_ai_draft is None:raise DemoError('没有解析草稿')
  from core.front_template import FIELDS,validate_draft
  draft=validate_draft(self.front_ai_draft,self.front_spec);s=deepcopy(self.front_draft)
  s['template'].update(name='用户确认的封面页眉页脚演示要求',confirmation='规范草稿经用户确认后执行')
  for n in FIELDS:
   f=draft[n];s['template']['values'][n]=f['value'] if f else None;s['template']['sources'][n]={'kind':'ai_extracted','quote':f['quote'],'location':f['location']} if f else {'kind':'not_enabled','quote':'','location':None}
  self.edit_front(s)

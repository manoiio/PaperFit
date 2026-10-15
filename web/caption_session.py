"""Session-owned opt-in captions, no AI. L05 is a separate round."""
from copy import deepcopy
from uuid import uuid4
import json
from core.package import Package,DemoError,sha256
from core.captions import make_scope,validate_scope,inventory,analyze,template,digest
from core.caption_move import apply_caption_positions
class CaptionSession:
 def init_captions(self):self.caption_enabled=False;self.caption_draft=None;self.caption_confirmed=None;self.caption_move_signature=None
 def enable_captions(self,value):
  self._current()
  if self.mode!='academic' or type(value) is not bool:raise DemoError('题注编号位置须在单文档模式明确启用')
  if self.caption_enabled!=value:
   self.caption_enabled=value
   if not self.caption_draft or self.caption_draft['input_sha256']!=self.inventory['input_sha256']:self.caption_draft=make_scope(Package(self.input_path))
   self.invalidate()
 def caption_inventory(self):
  self._current();key=('caption-inventory',self.inventory['input_sha256'],tuple(sorted(self.paragraph_types.items())))
  return self.cached_data(key,lambda:inventory(self.input_path,{'paragraph_types':self.paragraph_types}))
 def edit_captions(self,s):
  self._current();validate_scope(Package(self.input_path),s,{'paragraph_types':self.paragraph_types},confirmed=False)
  if s!=self.caption_draft:self.caption_draft=deepcopy(s);self.invalidate()
 def confirm_captions(self):
  self._current()
  if not self.caption_enabled or not self.caption_draft:raise DemoError('请先启用并核对题注与关联')
  s=deepcopy(self.caption_draft);s.update(confirmed=True,confirmation='网页人工核对题注、章节、关联及范围声明')
  validate_scope(Package(self.input_path),s,{'paragraph_types':self.paragraph_types});self.caption_draft=s;self.caption_confirmed={'scope':deepcopy(s),'rules_hash':self.rules_hash}
 def caption_manifest(self):
  if not self.caption_enabled or self.mode!='academic':return None
  c=self.caption_confirmed
  if not c or c['scope']!=self.caption_draft or c['rules_hash']!=self.rules_hash:raise DemoError('题注范围、关联或配置变化，请重新确认')
  validate_scope(Package(self.input_path),c['scope'],{'paragraph_types':self.paragraph_types});return deepcopy(c['scope'])
 def adopt_caption_scope(self,s,confirmed=False):
  self.caption_enabled=True;self.caption_draft=deepcopy(s);self.caption_draft['input_sha256']=self.inventory['input_sha256'];self.caption_confirmed=None
  if confirmed:self.confirm_captions()
 def caption_binding(self):return (digest({k:self.caption_draft[k] for k in ('captions','chapter_map','associations','complete','chapters_complete','template')}),) if self.mode=='academic' and self.caption_enabled else ()
 def caption_template_bytes(self):return json.dumps(template(self.caption_draft['template']),ensure_ascii=False,indent=2).encode()
 def import_caption_template(self,raw):
  from core.rule_config import strict_json
  if not self.caption_enabled or not self.caption_draft:raise DemoError('请先启用题注范围')
  if len(raw)>65536:raise DemoError('题注补充配置超过64KB')
  try:t=template(strict_json(raw.decode('utf-8')))
  except UnicodeError:raise DemoError('配置须为UTF-8 JSON') from None
  s=deepcopy(self.caption_draft);s['template']=t;self.edit_captions(s)
 def generate_caption_move(self,keys):
  try:
   self._current()
   if not self.report or not self.classification_confirmed:raise DemoError('请确认完整分类与题注范围并检查')
   sig=(self.inventory['input_sha256'],self._history_binding(),tuple(sorted(keys)))
   if self.caption_move_signature==sig and self.result and self.result.get('kind')=='caption_position':self.downloads();return True
   r=apply_caption_positions(self.input_path,self.task_dir/('caption-position-'+uuid4().hex+'.docx'),self.confirmed,mode=self.mode,classification_manifest=self.classification_confirmed,confirmed_keys=keys,**self._base_rules_arguments())
   if r['after']['rules']['sha256']!=self.rules_hash:raise DemoError('规则变化，请重新确认')
   self.generation_count+=1;r['round']={'number':self.generation_count,'input_round':self.current_round,'input_sha256':self.inventory['input_sha256'],'original_sha256':sha256(self.original_bytes),'rules_version':r['after']['rules']['version'],'rules_sha256':self.rules_hash};r['round_input_path']=str(self.input_path)
   self._archive_round(r);self.result=r;self.result_signature=self._signature();self.caption_move_signature=sig;self.error=None;return True
  except Exception as exc:
   from .session import public_error
   self.error=public_error(exc);self.result=self.result_signature=None;return False

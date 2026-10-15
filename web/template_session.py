"""规范文件/待编辑模板与当前生效规则分别保存，文件仅属于本会话。"""
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import json
import shutil
from core.package import DemoError, write_new, sha256
from core.norms import extract_norm, selected_segments, marked_text
from core.templates import FIELDS, ALL_FIELDS, EXT_FIELDS, field_map, defaults, validate_segments, validate_draft, validate_template, make_template, upgrade_template
from core.rule_config import strict_json


class TemplateSession:
    @property
    def template_fields(self):
        return field_map(self.template_import or self.template_draft or {})

    def init_templates(self):
        self.norm_dir=None
        self.norm_inventory=None
        self.norm_bytes=None
        self.norm_path=None
        self.norm_text=''
        self.norm_segments=[]
        self.norm_confirmed_hash=None
        self.historical_norm_sha256=None
        self.template_draft=None
        self.template_receipt=None
        self.template_modes={n:'choose' for n in FIELDS}
        self.template_values={}
        self.template_touched=set()
        self.template_import=None
        self.active_template=None
        self.active_template_sha256=None
        self.template_error=None
        self.template_busy=False
        self.template_generation=0
        self.template_name='课程论文演示要求'

    def _norm_directory(self):
        if self.norm_dir is None:
            self.work_root.mkdir(parents=True,exist_ok=True)
            self.norm_dir=self.work_root/uuid4().hex
            self.norm_dir.mkdir()
        return self.norm_dir

    def reset_templates(self):
        if self.norm_dir is not None:
            if self.norm_dir.parent.resolve()!=self.work_root or self.norm_dir.is_symlink(): raise DemoError('规范任务目录不安全')
            if self.norm_dir.exists(): shutil.rmtree(self.norm_dir)
        generation=self.template_generation+1
        self.init_templates()
        self.template_generation=generation

    def _clear_template_draft(self):
        self.template_draft=self.template_receipt=self.template_import=None
        self.norm_confirmed_hash=None
        self.template_error=None
        self.template_values={}
        self.template_modes={n:'choose' for n in FIELDS}
        self.template_touched=set()
        self.template_generation+=1

    def load_norm(self, data, filename, encoding='auto'):
        from web.session import public_error
        self.norm_inventory=self.norm_bytes=None
        self.historical_norm_sha256=None
        self.norm_text='';self.norm_segments=[]
        self._clear_template_draft();self.invalidate()
        try:
            suffix=Path(filename.replace('\\','/')).suffix.lower()
            if suffix not in ('.txt','.docx'): raise DemoError('格式要求只支持TXT/DOCX；不是待检查论文上传入口')
            path=self._norm_directory()/('norm-'+uuid4().hex+suffix)
            if not isinstance(data,bytes) or not data or len(data)>2*1024*1024: raise DemoError('格式要求文件最大2MB且不能为空')
            write_new(path,data)
            self.norm_path=path
            self.norm_inventory=extract_norm(data,suffix[1:],encoding=encoding,path=path)
            self.norm_bytes=data
            return True
        except Exception as exc:
            self.template_error=public_error(exc)
            return False

    def set_norm_text(self, text, *, segments=None):
        if text!=self.norm_text or (segments is not None and segments!=self.norm_segments):
            self.norm_text=text
            self.norm_segments=deepcopy(segments) if segments is not None else []
            self._clear_template_draft()
            self.invalidate()

    def select_norm_segments(self, locations):
        if self.norm_inventory is None: raise DemoError('请先导入可读取的格式要求文件')
        if self.norm_path is None or sha256(self.norm_path.read_bytes())!=self.norm_inventory['file_sha256'] or sha256(self.norm_bytes)!=self.norm_inventory['file_sha256']: raise DemoError('规范文件哈希发生变化')
        allowed={s['location'] for s in self.norm_inventory['segments']}
        if not isinstance(locations,list) or any(x not in allowed for x in locations): raise DemoError('选段位置无效')
        segments=[s for s in self.norm_inventory['segments'] if s['location'] in locations]
        validate_segments(segments)
        self.set_norm_text('\n'.join(s['text'] for s in segments),segments=segments)

    def confirm_norm_text(self):
        if not self.norm_segments:
            self.norm_segments=selected_segments(self.norm_text)
        validate_segments(self.norm_segments)
        if not self.norm_segments: raise DemoError('请核对非空规范摘录')
        # Empty lines carry no executable requirement; preserve every nonempty line verbatim.
        if '\n'.join(line for line in self.norm_text.splitlines() if line.strip())!='\n'.join(s['text'] for s in self.norm_segments): raise DemoError('摘录文字与来源不一致，请重新核对')
        self.norm_confirmed_hash=sha256(marked_text(self.norm_segments).encode())

    def parse_template(self, parser=None):
        from ai.template_spec import parse_template_requirements
        from web.session import public_error
        if self.template_busy or self.template_draft is not None:return False
        self.template_busy=True;self.template_error=None
        try:
            if self.norm_inventory and (self.norm_path is None or sha256(self.norm_path.read_bytes())!=self.norm_inventory['file_sha256']): raise DemoError('规范文件哈希变化，请重新导入')
            if self.norm_confirmed_hash!=sha256(marked_text(self.norm_segments).encode()) or not self.norm_segments: raise DemoError('请先核对并确认要交给AI的规范摘录')
            if parser is not None:response=parser(deepcopy(self.norm_segments))
            elif self.mode=='academic':
                from ai.academic_spec import parse_requirements
                response=parse_requirements(deepcopy(self.norm_segments),include_tables=True,include_backmatter=True)
            elif self.mode=='extended':response=parse_template_requirements(deepcopy(self.norm_segments),extended=True)
            else:response=parse_template_requirements(deepcopy(self.norm_segments))
            self.template_draft=validate_draft(response['draft'],self.norm_segments)
            self.template_receipt=deepcopy(response['receipt'])
            self.template_import=None;self.template_touched=set()
            from core import load_rules
            fields=self.template_fields
            if len(fields)>26:
                from core.academic_templates import default_values
                values=self.academic_values()
            else:values=defaults(load_rules(self.rules_path),extended=fields is ALL_FIELDS)
            self.template_modes={n:'choose' for n in fields}
            for n in fields:
                f=self.template_draft[n]
                self.template_modes[n]='ai' if f else 'choose'
                self.template_values[n]=f['value'] if f else values[n]
            self.template_generation+=1
            write_new(self._norm_directory()/('parse-'+uuid4().hex+'.json'),(json.dumps(response,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
            return True
        except Exception as exc:
            self.template_draft=self.template_receipt=None
            self.template_error=public_error(exc)
            return False
        finally:self.template_busy=False

    def import_template(self, raw):
        from core import load_rules
        from web.session import public_error
        self._clear_template_draft();self.invalidate()
        try:
            if not isinstance(raw,bytes) or len(raw)>64*1024: raise DemoError('模板须为不超过64KB的UTF-8 JSON')
            data=validate_template(strict_json(raw.decode('utf-8')),load_rules(self.rules_path))
            self.template_import=data
            self.norm_text='\n'.join(s['text'] for s in data['norm_excerpt'])
            self.norm_segments=deepcopy(data['norm_excerpt'])
            self.norm_inventory=self.norm_bytes=None
            self.template_values=deepcopy(data['final_values'])
            self.template_modes={n:'imported' for n in field_map(data)}
            self.template_name=data['name']
            write_new(self._norm_directory()/('import-'+uuid4().hex+'.json'),raw)
            return True
        except Exception as exc:
            self.template_error=public_error(exc)
            return False

    def edit_template(self, name, mode, value=None, touched=False):
        if name not in self.template_fields or mode not in ('choose','ai','manual','default','imported','disabled'): raise DemoError('模板编辑字段或模式无效')
        if mode=='disabled' and '__' not in name and name!='content_checks':raise DemoError('旧模板字段不能禁用')
        self.template_modes[name]=mode
        if mode=='disabled':self.template_values[name]=None
        if mode=='default':
            from core import load_rules
            if self.template_fields.get(name) and ('__' in name or len(self.template_fields)>26):
                from core.academic_templates import default_values
                self.template_values[name]=self.academic_values()[name]
            else:self.template_values[name]=defaults(load_rules(self.rules_path),extended=self.template_fields is ALL_FIELDS)[name]
        elif mode=='ai' and self.template_draft and self.template_draft[name]:
            self.template_values[name]=self.template_draft[name]['value']
        elif mode=='imported' and self.template_import:
            self.template_values[name]=self.template_import['final_values'][name]
        if value is not None:self.template_values[name]=value
        if touched:self.template_touched.add(name)
        # 草稿修改不会改变已生效配置；只能通过显式确认应用改变规则。

    def proposed_template(self):
        if len(self.template_fields)>26:return self.proposed_academic_template()
        from core import load_rules
        fields=self.template_fields
        base=load_rules(self.rules_path);d=defaults(base,extended=fields is ALL_FIELDS);values={};sources={}
        for n in fields:
            mode=self.template_modes[n]
            if mode=='choose': raise DemoError('每个未提到的字段须明确选择沿用默认值或手动指定')
            candidate=self.template_draft[n] if self.template_draft else None
            if mode=='ai' and candidate is None: raise DemoError('字段没有AI提取依据')
            value=d[n] if mode=='default' else self.template_values[n]
            if mode=='default':source={'kind':'default_inherited','quote':'','location':None}
            elif mode=='imported':
                if self.template_import is None:raise DemoError('没有待确认的导入模板')
                source=deepcopy(self.template_import['field_sources'][n])
                if n in self.template_touched or value!=self.template_import['final_values'][n]:source['kind']='user_confirmed'
            elif mode=='ai' and n not in self.template_touched and value==candidate['value']:
                source={'kind':'ai_extracted','quote':candidate['quote'],'location':candidate['location']}
            else:source={'kind':'user_confirmed','quote':candidate['quote'] if candidate else '', 'location':candidate['location'] if candidate else None}
            values[n]=value;sources[n]=source
        return make_template(self.template_name,values,sources,self.norm_segments,base,
                             norm_sha256=self.norm_inventory['file_sha256'] if self.norm_inventory else self.template_import['norm_file_sha256'] if self.template_import else self.historical_norm_sha256,
                             imported=self.template_import is not None,
                             compatibility=self.template_import.get('compatibility') if self.template_import else None,
                             extraction=self.template_import['extraction'] if self.template_import else {k:self.template_receipt[k] for k in ('kind','model','timestamp_utc')} if self.template_receipt else None)

    def upgrade_template_draft(self):
        from core import load_rules
        if self.template_import is None:raise DemoError('请先导入旧模板，再明确升级')
        data=upgrade_template(self.template_import,load_rules(self.rules_path))
        self.template_import=data
        self.template_draft=self.template_receipt=None
        self.template_values=deepcopy(data['final_values'])
        self.template_modes={n:'imported' for n in ALL_FIELDS}
        self.template_touched=set();self.template_generation+=1

    def choose_missing_defaults(self):
        # Only an explicit UI action; never turn an AI null into an extracted value.
        for n in self.template_fields:
            if self.template_modes[n]=='choose':self.edit_template(n,'default')

    def apply_template(self):
        from web.session import public_error
        try:
            data=self.proposed_template()
            self._save_custom(data)
            self.invalidate();self.sync_rules()
            if self.rules_hash is None:raise DemoError('模板未能生效，请恢复默认规则')
            self.template_error=None
            return True
        except Exception as exc:
            self.template_error=public_error(exc)
            return False

    def template_download(self):
        if self.active_template is None:return None
        from core import load_custom_rules
        if self.custom_rules_path is None or not self.custom_rules_path.exists():return None
        if sha256(self.custom_rules_path.read_bytes())!=self.active_template_sha256:
            self.invalidate();self.template_error='模板文件发生变化，请重新载入并确认'
            return None
        loaded=load_custom_rules(self.custom_rules_path)
        from core import effective_rules
        if effective_rules(**self._base_rules_arguments(),mode=self.mode)['sha256']!=self.rules_hash: return None
        raw=self.custom_rules_path.read_bytes()
        if self.workbench['active'] and __import__('json').loads(raw).get('format')=='paper-grid-rule-bundle':
            if self.workbench['active']['modules']['main']['disabled_fields']:return None
            from core.rule_bundle import raw as encode
            return encode(self.active_template)
        return raw

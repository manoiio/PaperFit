"""每个Streamlit会话独立的状态；无共享缓存、CLI子进程或规则副本逻辑。"""
from pathlib import Path
from uuid import uuid4
import hashlib
import json
import shutil
from copy import deepcopy
from core import inspect_document, check_document, fix_document, load_rules, load_custom_rules, effective_rules, suggest_paragraph_types
from core.rule_config import make_custom_config, KINDS
from core.engine import DEFAULT_RULES
from core.package import DemoError, write_new
from core.report import markdown, modification_markdown

MAX_BYTES = 10 * 1024 * 1024

def digest(data):
    return hashlib.sha256(data).hexdigest()

def public_error(exc):
    if isinstance(exc, DemoError):
        # Engine errors may include paths. Keep default UI free from private disk paths.
        message = str(exc).split('：/')[0]
        return message
    return '本次处理未完成，请检查文件是否可读取，并重新开始。'

from .template_session import TemplateSession

from .preview_session import PreviewSession

from .width_session import WidthSession

from .center_session import CenterSession
from .efficiency import EfficiencySession
from .async_preview import AsyncPreviewSession
from .project_session import ProjectSession
from .academic_session import AcademicSession
from .table_session import TableSession
from .front_session import FrontSession
from .toc_session import TocSession
from .citation_session import CitationSession
from .note_session import NoteSession
from .reference_session import ReferenceSession
from .caption_session import CaptionSession
from .material_session import MaterialSession
from .workbench_session import WorkbenchSession
from .scope_session import ScopeSession
from .rehearsal_session import RehearsalSession
from .plan_session import PlanSession

class WebSession(TemplateSession, PreviewSession, WidthSession, CenterSession, EfficiencySession, AsyncPreviewSession, ProjectSession, AcademicSession, TableSession, FrontSession, TocSession, CitationSession, NoteSession, ReferenceSession, CaptionSession, MaterialSession, WorkbenchSession, ScopeSession, RehearsalSession, PlanSession):
    def __init__(self, work_root, rules_path=DEFAULT_RULES):
        self.work_root = Path(work_root).resolve()
        self.rules_path = Path(rules_path).resolve()
        self.task_dir = None
        self.input_path = None
        self.input_bytes = None
        self.display_name = ''
        self.inventory = None
        self.body = []
        self.confirmed = None
        self.classification_confirmed = None
        self.report = None
        self.selected = []
        self.result = None
        self.result_signature = None
        self.error = None
        self.page_layout_draft = None
        self.rules_hash = None
        self.revision = 0
        self.report_revision = 0
        self.custom_rules_path = None
        self.active_custom_data = None
        self.spec_text = ''
        self.ai_draft = None
        self.ai_receipt = None
        self.ai_error = None
        self.ai_busy = False
        self.draft_modes = {'R05': 'choose', 'R06': 'choose'}
        self.draft_values = {'R05': 12.0, 'R06': 1.5}
        self.draft_edited = set()
        self.draft_generation = 0
        self.mode = 'basic'
        self.suggestions = None
        self.paragraph_types = {}
        self.classification_confirmed = None
        self.original_path = None
        self.original_bytes = None
        self.current_round = 0
        self.generation_count = 0
        self.history = []
        self.init_center()
        self.init_templates()
        self.init_workbench()
        self.init_preview()
        self.init_rehearsal()
        self.init_efficiency()
        self.init_async_preview()
        self.init_project()
        self.init_tables()
        self.init_front()
        self.init_toc()
        self.init_citations()
        self.init_notes()
        self.init_references()
        self.init_captions()
        self.material_exclusions={}

    def invalidate(self, preserve_tables=False):
        self.cancel_rehearsal()
        if not preserve_tables:
            self.table_confirmed = None
            self.front_confirmed = None
            self.toc_confirmed = None
            self.citation_confirmed = None
            self.note_confirmed = None
            self.reference_confirmed = None
            self.caption_confirmed = None
        self.invalidate_preview_jobs()
        self.init_efficiency()
        self.invalidate_center()
        self.layout_signature = None
        self.width_signature = None
        self.width_error = None
        self.preview_error = self.layout_error = None
        self.confirmed = None
        self.classification_confirmed = None
        self.report = None
        self.selected = []
        self.result = None
        self.result_signature = None
        self.error = None
        self.revision += 1

    def sync_rules(self):
        try:
            if self.active_template is not None and self.custom_rules_path and digest(self.custom_rules_path.read_bytes()) != self.active_template_sha256:
                raise DemoError('已应用模板文件发生变化，请重新载入并确认或恢复默认规则')
            base = load_custom_rules(self.custom_rules_path) if self.custom_rules_path else load_rules(self.rules_path)
            rules = effective_rules(**self._base_rules_arguments(), mode=self.mode)
            if self.custom_rules_path:
                self.active_custom_data = {k:deepcopy(v) for k,v in base.items() if k!='sha256'}
            if rules['sha256'] != self.rules_hash:
                self.invalidate()
                self.rules_hash = rules['sha256']
                if self.custom_rules_path:
                    self.active_custom_data = {k:deepcopy(v) for k,v in base.items() if k!='sha256'}
                return True
            return False
        except Exception as exc:
            self.invalidate()
            self.rules_hash = None
            self.error = public_error(exc)
            return True

    def reset(self, preserve_settings=False):
        self.cancel_rehearsal()
        self.cancel_project_import()
        self.project_export=None
        self.project_checkpoint=None
        self.clear_async_artifacts()
        self.retire_center_history(preserve_settings)
        self.init_preview()
        # Delete only the directory issued to this session, never enumerate work/.
        if self.task_dir is not None:
            owned = self.task_dir
            if owned.parent.resolve() != self.work_root or owned.is_symlink():
                raise DemoError('当前任务目录不安全，拒绝清理')
            if owned.exists():
                shutil.rmtree(owned)
        self.task_dir = self.input_path = self.input_bytes = self.inventory = None
        self.display_name = ''
        self.init_tables()
        self.init_front()
        self.init_toc()
        self.init_citations()
        self.init_notes()
        self.init_references()
        self.init_captions()
        self.material_exclusions={}
        self.body = []
        self.paragraph_types = {}
        self.suggestions = self.classification_confirmed = None
        self.original_path = self.original_bytes = None
        self.current_round = self.generation_count = 0
        self.history = []
        if not preserve_settings:
            self.mode = 'basic'
            self.reset_templates()
            self.init_workbench()
        self.custom_rules_path = None
        if not preserve_settings:
            self.active_custom_data = None
            self.spec_text = ''
            self.ai_draft = self.ai_receipt = None
            self.ai_error = None
            self.draft_modes = {'R05':'choose','R06':'choose'}
            self.draft_values = {'R05':12.0,'R06':1.5}
            self.draft_edited = set()
            self.draft_generation += 1
        self.invalidate()

    def load(self, data, display_name, prefill=None):
        self.reset(preserve_settings=True)
        self.display_name = Path(display_name.replace('\\', '/')).name
        try:
            if not self.display_name.lower().endswith('.docx'):
                raise DemoError('请选择DOCX文件')
            if len(data) > MAX_BYTES:
                raise DemoError('文件超过10MB，请使用更小的DOCX')
            if not self.sync_rules() and self.rules_hash is None:
                raise DemoError('固定规则配置不可用')
            if self.rules_hash is None:
                raise DemoError('固定规则配置不可用')
            self.work_root.mkdir(parents=True, exist_ok=True)
            self.task_dir = self.work_root / uuid4().hex
            self.task_dir.mkdir()
            if self.active_template or self.active_custom_data:
                self._save_custom(self.workbench["active"] if self.workbench["active"] and self.custom_rules_path is None and self.active_template==self.workbench["active"]["modules"]["main"]["template"] else self.active_template or self.active_custom_data)
                self.sync_rules()
            self.input_path = self.task_dir / 'input.docx'
            write_new(self.input_path, data)
            # Publish inventory only after both reads succeed: a rerun must not
            # see a readable file with a half-built classification draft.
            inventory = inspect_document(self.input_path)
            suggestions = suggest_paragraph_types(self.input_path,include_sections=True) if self.mode=='academic' else suggest_paragraph_types(self.input_path)
            self.suggestions = suggestions
            self.inventory = inventory
            from core.table_text import inventory as table_inventory
            self.table_types={str(t['index']):'pending' for t in table_inventory(self.input_path)['tables']}
            self.input_bytes = data
            self.original_path = self.input_path
            self.original_bytes = data
            self.paragraph_types = {str(p['index']):p['suggested_type'] for p in self.suggestions['paragraphs']}
            if prefill is not None:
                if prefill.get('input_sha256') != self.inventory['input_sha256']:
                    raise DemoError('内置样本清单与文件不匹配，不能预填正文')
                self.set_body(prefill['body_paragraphs'])
            # Uploaded documents never receive a filename-based or hash-based preset.
            self.error = None
            return True
        except Exception as exc:
            self.inventory = None
            self.input_bytes = None
            self.invalidate()
            self.error = public_error(exc)
            return False

    def set_body(self, body):
        if self.inventory is None:
            raise DemoError('请先选择可读取的DOCX')
        count = len(self.inventory['paragraphs'])
        if any(type(n) is not int or n < 1 or n > count for n in body) or len(set(body)) != len(body):
            raise DemoError('正文段落编号无效')
        current = sorted(body)
        if current != self.body:
            self.body = current
            self.invalidate(preserve_tables=True)
            return True
        return False

    def _current(self):
        if self.input_path is None or self.inventory is None or self.input_bytes is None:
            raise DemoError('请先选择可读取的DOCX')
        if digest(self.input_path.read_bytes()) != self.inventory['input_sha256']:
            self.invalidate()
            self.inventory = None
            self.input_bytes = None
            raise DemoError('当前输入文件发生变化，请重新选择文件')
        if self.table_enabled and self.table_confirmed is not None:
            from core.table_text import PATH
            if self.table_confirmed['policy_hash']!=digest(PATH.read_bytes()):
                self.invalidate();raise DemoError('表格规则来源文件发生变化，请重新核对并确认')
        if self.report and self.report['rules'].get('backmatter_sha256'):
            from core.backmatter import PATH
            if digest(PATH.read_bytes())!=self.report['rules']['backmatter_sha256']:self.invalidate();raise DemoError('附录/致谢默认依据已变化，请重新核对')
        old = self.rules_hash
        self.sync_rules()
        if self.rules_hash is None or old != self.rules_hash:
            raise DemoError('规则配置已变化，请重新确认正文')

    def confirm(self):
        self._current()
        if self.mode != 'basic':
            self.confirm_classification()
            return
        if not self.body:
            self.invalidate()
            raise DemoError('请至少选择一个明确的正文段落；未选择时不会执行正文检查')
        self.confirmed = {'input_sha256': self.inventory['input_sha256'], 'body_paragraphs': self.body.copy(),
                          'confirmation': '网页人工确认'}
        self.error = None

    def check(self, force=False):
        self.cancel_rehearsal()
        self.report = self.result = self.result_signature = None
        self.selected = []
        self.report_revision += 1
        try:
            self._current()
            if self.confirmed is None or self.confirmed['body_paragraphs'] != self.body or (self.mode != 'basic' and self.classification_confirmed is None):
                raise DemoError('正文范围尚未确认，请先确认')
            key=('check',self.inventory['input_sha256'],self._history_binding())
            if force:self.readonly_cache.pop(key,None)
            self.report = self.cached_data(key,lambda:check_document(self.input_path, self.confirmed, **self._rules_arguments()))
            self._current()
            self.error = None
            return True
        except Exception as exc:
            self.error = public_error(exc)
            return False

    def eligible(self):
        if self.report is None:
            return []
        return [f for f in self.report['findings'] if f['status'] == 'problem' and f['fixable']]

    def set_selection(self, keys):
        allowed = {f['key'] for f in self.eligible()}
        selected = sorted(set(keys) & allowed)
        if selected != self.selected:
            self.cancel_rehearsal()
            self.selected = selected
            self.result = self.result_signature = None
            self.error = None

    def _signature(self):
        return (self.inventory['input_sha256'], tuple(self.body), self.mode, tuple(sorted(self.paragraph_types.items())) if self.mode!='basic' else (), self.rules_hash,
                self.report_revision, tuple(self.selected))

    def generate(self):
        self.cancel_rehearsal()
        try:
            self._current()
            if self.report is None or self.confirmed is None:
                raise DemoError('检查结果已失效，请重新确认并检查')
            # Re-filter, so stale/forged UI selections cannot reach the engine.
            self.set_selection(self.selected)
            if not self.selected:
                raise DemoError('请至少选择一个可修正的问题')
            signature = self._signature()
            if self.result is not None and self.result_signature == signature:
                return True  # Duplicate click/rerun never calls fix_document twice.
            self.result = self.result_signature = None
            out = self.task_dir / ('fixed-' + uuid4().hex + '.docx')
            result = fix_document(self.input_path, out, self.confirmed,
                                  selected_keys=self.selected, **self._rules_arguments())
            # Protect against a rule file changing during execution.
            if result['after']['rules']['sha256'] != self.rules_hash:
                out.unlink()
                self.invalidate()
                raise DemoError('规则配置在处理时变化，请重新确认并检查')
            self.generation_count += 1
            result['round'] = {'number':self.generation_count,'input_round':self.current_round,
                               'input_sha256':self.inventory['input_sha256'],'original_sha256':digest(self.original_bytes),
                               'rules_version':result['after']['rules']['version'],'rules_sha256':self.rules_hash,**({'toc_supplement_sha256':result['after']['rules']['toc_supplement']['sha256']} if result['after']['rules'].get('toc_supplement') else {}),**({'front_supplement_sha256':result['after']['rules']['front_supplement']['sha256']} if result['after']['rules'].get('front_supplement') else {})}
            self._archive_round(result)
            self.result = result
            self.result_signature = signature
            self.error = None
            return True
        except Exception as exc:
            self.result = self.result_signature = None
            self.error = public_error(exc)
            return False

    def downloads(self):
        """Only current bindings may serve data; this function never performs a correction."""
        self._current()
        if self.result is None or self.result_signature != self._signature():
            return {}
        output = Path(self.result['output'])
        data = output.read_bytes()
        if digest(data) != self.result['output_body_manifest']['input_sha256']:
            self.result = self.result_signature = None
            raise DemoError('修正版文件发生变化，请重新生成')
        if self.result.get('plan'):self.plan_step_downloads()
        if (self.result.get('plan') or self.result.get('kind') in ('figure_layout','pagination_layout','width_adaptation','caption_position','dynamic_text','section_pages','field_update')) and digest(Path(self.result['round_input_path']).read_bytes()) != self.result['round']['input_sha256']:
            self.result = self.result_signature = None
            raise DemoError('本轮辅助输入文件发生变化，结果已失效')
        j = lambda x: (json.dumps(x, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        def build():
            return {'changes.md': modification_markdown(self.result).encode('utf-8'),
                    'recheck.md': markdown(self.result['after']).encode('utf-8'),
                    'result.json': j(self.result), 'fixed.body.json': j(self.result['output_body_manifest'])}
        reports=self.cached_bytes('legacy',self.result,build)
        files = {'fixed.docx': data, 'original.docx': self.original_bytes,
                'round-input.docx': (Path(self.result['round_input_path']).read_bytes() if self.result.get('plan') or self.result.get('kind') in ('figure_layout','pagination_layout','width_adaptation','caption_position','dynamic_text','section_pages','field_update') else self.input_bytes),
                **reports}
        if 'widths' in self.result:
            from core.widths import width_markdown
            files['width-recheck.md']=width_markdown(self.result['widths']['after']).encode()
            files['width-recheck.json']=j(self.result['widths']['after'])
        if 'output_classification_manifest' in self.result:
            files['fixed.types.json'] = j(self.result['output_classification_manifest'])
        if self.custom_rules_path:
            files['rules.json'] = self.custom_rules_path.read_bytes()
        return files

    def _base_rules_arguments(self):
        return {'custom_rules_path':self.custom_rules_path} if self.custom_rules_path else {'rules_path':self.rules_path}

    def _rules_arguments(self):
        args=self._base_rules_arguments()
        if self.mode != 'basic':
            args.update(mode=self.mode,classification_manifest=self.classification_confirmed)
        return args

    def set_mode(self, mode):
        if mode not in ('basic','extended','academic'):raise DemoError('检查模式无效')
        if mode != self.mode:
            self.mode=mode
            self.invalidate()
            self.sync_rules()
            if self.input_path is not None and self.inventory is not None:
                self.suggestions=suggest_paragraph_types(self.input_path,include_sections=mode=='academic')
            return True
        return False

    def set_types(self, items):
        from core.classification import TYPES
        if self.inventory is None or not isinstance(items,dict) or set(items)!=set(self.paragraph_types) or any(v not in TYPES for v in items.values()):
            raise DemoError('段落分类无效')
        items=deepcopy(items)
        for n in self.material_exclusions:items[n]='other'
        if items != self.paragraph_types:
            self.citation_confirmed=None
            self.paragraph_types=deepcopy(items)
            self.body=sorted(int(n) for n,t in items.items() if t=='body')
            self.invalidate(preserve_tables=True)
            return True
        return False

    def confirm_classification(self):
        self._current()
        if self.mode == 'basic':raise DemoError('请切换到正文及标题题注检查')
        from core.classification import validate_classification
        from core.package import Package
        manifest=self._classification_manifest()
        validate_classification(Package(self.input_path),manifest)
        if self.classification_confirmed==manifest:return
        self.classification_confirmed=manifest
        self.body=sorted(int(n) for n,t in self.paragraph_types.items() if t=='body')
        self.confirmed={'input_sha256':self.inventory['input_sha256'],'body_paragraphs':self.body.copy(),'confirmation':'网页分类人工确认'}
        write_new(self.task_dir/('confirmed-types-'+uuid4().hex+'.json'),(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
        self.error=None

    def _classification_manifest(self):
        """Build the same manifest for separate and unified confirmation."""
        manifest={'input_sha256':self.inventory['input_sha256'],'paragraph_types':deepcopy(self.paragraph_types),
                  'confirmed':True,'confirmation':'网页用户逐项核对或确认整份分类；待确认项不检查、不修正'}
        if self.material_exclusions:manifest['material_exclusions']=deepcopy(self.material_exclusions)
        table_scope=self.table_manifest()
        if table_scope is not None:manifest['table_scope']=table_scope
        caption_scope=self.caption_manifest()
        if caption_scope is not None:manifest['caption_scope']=caption_scope
        reference_scope=self.reference_manifest()
        if reference_scope is not None:manifest['reference_scope']=reference_scope
        note_scope=self.note_manifest()
        if note_scope is not None:manifest['note_scope']=note_scope
        citation_scope=self.citation_manifest()
        if citation_scope is not None:manifest['citation_scope']=citation_scope
        toc_scope=self.toc_manifest()
        if toc_scope is not None:manifest['toc_scope']=toc_scope
        front_scope=self.front_manifest()
        if front_scope is not None:manifest['front_scope']=front_scope
        return manifest

    def backmatter_binding(self):
        from core.backmatter import binding
        return binding(self.mode,self.paragraph_types,(self.active_template or {}).get('structure_version'))

    def _history_binding(self):
        return (self.mode,self.rules_hash,tuple(sorted(self.paragraph_types.items())) if self.mode!='basic' else tuple(self.body))+((tuple(sorted(self.table_types.items())),) if self.mode=='academic' and self.table_enabled else ())+((digest(json.dumps({k:self.front_draft[k] for k in ('objects','section_roles','template')},ensure_ascii=False,sort_keys=True).encode()),) if self.mode=='academic' and self.front_enabled else ())+((digest(json.dumps({k:self.toc_draft[k] for k in ('objects','covered_levels','complete','headings_complete','template')},ensure_ascii=False,sort_keys=True).encode()),) if self.mode=='academic' and self.toc_enabled else ())+self.citation_binding()+self.note_binding()+self.reference_binding()+self.caption_binding()+((digest(json.dumps(self.table_layout_options,ensure_ascii=False,sort_keys=True).encode()),) if self.mode=='academic' and self.table_enabled and self.table_layout_options else ())+((digest(json.dumps(self.material_exclusions,ensure_ascii=False,sort_keys=True).encode()),) if self.material_exclusions else ())+self.backmatter_binding()

    def _archive_round(self,result):
        if result['after']['rules'].get('reference_supplement'):
            result['round']['reference_supplement_sha256']=result['after']['rules']['reference_supplement']['sha256']
        if result['after']['rules'].get('note_supplement'):
            result['round']['note_supplement_sha256']=result['after']['rules']['note_supplement']['sha256']
        if result['after']['rules'].get('backmatter_sha256'):result['round']['backmatter_sha256']=result['after']['rules']['backmatter_sha256']
        stem='round-'+str(result['round']['number'])+'-'+uuid4().hex
        write_new(self.task_dir/(stem+'.json'),(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
        write_new(self.task_dir/(stem+'-changes.md'),modification_markdown(result).encode())
        write_new(self.task_dir/(stem+'-recheck.md'),markdown(result['after']).encode())
        write_new(self.task_dir/(stem+'.body.json'),(json.dumps(result['output_body_manifest'],ensure_ascii=False,indent=2)+'\n').encode())
        if 'output_classification_manifest' in result:
            write_new(self.task_dir/(stem+'.types.json'),(json.dumps(result['output_classification_manifest'],ensure_ascii=False,indent=2)+'\n').encode())
        bundle=self.capture_center_round(result)
        write_new(self.task_dir/(stem+'-reading.json'),(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n').encode())
        rulepath=self.custom_rules_path or self.rules_path
        copy_rules=self.task_dir/(stem+'-rules.json')
        write_new(copy_rules,rulepath.read_bytes())
        self.history.append({'result':deepcopy(result),'stem':stem,'binding':self._history_binding(),'reading_bundle':bundle,
                             'project_rules_path':str(copy_rules),'project_rules_kind':'custom' if self.custom_rules_path else 'default'})

    def next_round(self):
        try:
            files=self.downloads()
            if not files:raise DemoError('没有可作为下一轮输入的当前修正版')
            result=self.result
            self.input_path=Path(result['output'])
            self.input_bytes=files['fixed.docx']
            self.inventory=inspect_document(self.input_path)
            self.suggestions=suggest_paragraph_types(self.input_path,include_sections=self.mode=='academic')
            self.current_round=result['round']['number']
            self.invalidate()
            self.confirmed=deepcopy(result['output_body_manifest'])
            self.classification_confirmed=deepcopy(result.get('output_classification_manifest'))
            self.body=list(self.confirmed['body_paragraphs'])
            if self.classification_confirmed:self.paragraph_types=deepcopy(self.classification_confirmed['paragraph_types'])
            self.material_exclusions=deepcopy((self.classification_confirmed or {}).get('material_exclusions',{}))
            if self.classification_confirmed and self.classification_confirmed.get('caption_scope'):
                self.adopt_caption_scope(self.classification_confirmed['caption_scope'],confirmed=True)
            if self.classification_confirmed and self.classification_confirmed.get('table_scope'):
                sc=self.classification_confirmed['table_scope'];self.table_types=deepcopy(sc['table_types']);self.table_enabled=True;self.table_layout_options=deepcopy(sc.get('layout_options'))
                from core.table_text import PATH
                self.table_confirmed={'scope':deepcopy(sc),'rules_hash':self.rules_hash,'policy_hash':digest(PATH.read_bytes())}
            if self.classification_confirmed and self.classification_confirmed.get('reference_scope'):
                self.adopt_reference_scope(self.classification_confirmed['reference_scope'],confirmed=True)
            if self.classification_confirmed and self.classification_confirmed.get('note_scope'):
                self.adopt_note_scope(self.classification_confirmed['note_scope'],confirmed=True)
            if self.classification_confirmed and self.classification_confirmed.get('citation_scope'):
                self.adopt_citation_scope(self.classification_confirmed['citation_scope'],confirmed=True)
            if self.classification_confirmed and self.classification_confirmed.get('toc_scope'):
                self.adopt_toc_scope(self.classification_confirmed['toc_scope'],confirmed=True)
            if self.classification_confirmed and self.classification_confirmed.get('front_scope'):
                self.adopt_front_scope(self.classification_confirmed['front_scope'],confirmed=True)
            # Explicit click confirms carrying verified unchanged structure into this new hash.
            return self.check()
        except Exception as exc:
            self.error=public_error(exc)
            return False

    def history_downloads(self):
        self._current()
        if self.confirmed is None:return []
        out=[]
        for h in self.history:
            if h['binding']!=self._history_binding():continue
            r=h['result'];p=Path(r['output'])
            if not p.exists() or digest(p.read_bytes())!=r['output_body_manifest']['input_sha256']:continue
            stem=h['stem']
            out.append({'round':r['round'],'fixed.docx':p.read_bytes(),
                        'changes.md':(self.task_dir/(stem+'-changes.md')).read_bytes(),
                        'recheck.md':(self.task_dir/(stem+'-recheck.md')).read_bytes(),
                        'result.json':(self.task_dir/(stem+'.json')).read_bytes()})
        return out

    def set_spec_text(self, text):
        if text != self.spec_text:
            self.spec_text = text
            self.ai_draft = self.ai_receipt = None
            self.ai_error = None
            self.draft_modes = {'R05':'choose','R06':'choose'}
            self.draft_values = {'R05':12.0,'R06':1.5}
            self.draft_edited = set()
            self.draft_generation += 1

    def parse_spec(self, parser=None):
        from ai.short_spec import parse_requirements
        if self.ai_busy or self.ai_draft is not None:
            return False  # Explicitly disabled after success; never label a reuse as a new API request.
        self.ai_busy = True
        self.ai_error = None
        try:
            response = (parse_requirements if parser is None else parser)(self.spec_text)
            from core.spec_validation import validate_draft
            self.ai_draft = validate_draft(response['draft'], self.spec_text)
            self.ai_receipt = response['receipt']
            self.draft_edited = set()
            for rid,name in [('R05','font_size'),('R06','line_spacing')]:
                field = self.ai_draft[name]
                self.draft_modes[rid] = 'ai' if field else 'choose'
                self.draft_values[rid] = field['value'] if field else (12.0 if rid=='R05' else 1.5)
            self.draft_generation += 1
            if self.task_dir:
                write_new(self.task_dir / ('ai-receipt-'+uuid4().hex+'.json'),
                          (json.dumps(response,ensure_ascii=False,indent=2)+'\n').encode())
            return True
        except Exception as exc:
            self.ai_draft = self.ai_receipt = None
            self.ai_error = public_error(exc)
            return False
        finally:
            self.ai_busy = False

    def edit_draft(self, rule, mode, value=None, touched=False):
        if rule not in ('R05','R06') or mode not in ('choose','ai','manual','default'):
            raise DemoError('草稿字段或模式无效')
        self.draft_modes[rule] = mode
        if mode == 'default':
            self.draft_values[rule] = 12.0 if rule == 'R05' else 1.5
        elif value is not None:
            self.draft_values[rule] = value
        if touched:
            self.draft_edited.add(rule)
        # No active rules, confirmation or existing document result changes here.

    def load_historical_spec(self, path):
        """显式沿用已记录的真实解析结果；本次操作不调用API。"""
        from core.rule_config import strict_json
        from core.spec_validation import validate_draft
        try:
            data = strict_json(Path(path).read_text(encoding='utf-8'))
            receipt = data['receipt']
            if receipt['kind'] != 'real_api' or receipt['model'] not in ('deepseek-flash','deepseek-v4-pro') or receipt['request_count'] != 1:
                raise DemoError('该记录不是可沿用的真实解析验收记录')
            text = receipt['input_text']
            validate_draft(data['draft'], text)
            self.set_spec_text(text)
            self.ai_draft = None
            receipt = {k:receipt[k] for k in ('kind','model','timestamp_utc','elapsed_seconds','input_text','input_sha256','json_output','request_count')}
            if receipt['input_sha256'] != digest(text.encode()):raise DemoError('历史规范记录的哈希不匹配')
            receipt.update(historical_reuse=True,requests_this_action=0)
            return self.parse_spec(parser=lambda _: {'draft':data['draft'],'receipt':receipt})
        except Exception as exc:
            self.ai_draft = self.ai_receipt = None
            self.ai_error = public_error(exc)
            return False

    def proposed_rules(self):
        base = load_rules(self.rules_path)
        values,sources = {},{}
        for rid,name in [('R05','font_size'),('R06','line_spacing')]:
            mode = self.draft_modes[rid]
            if mode == 'choose':raise DemoError('缺失字段须明确选择“沿用默认值”或“手动指定”')
            candidate = self.ai_draft[name] if self.ai_draft else None
            if mode=='ai' and candidate is None:raise DemoError('此字段未由AI提取')
            kind = 'default_inherited' if mode=='default' else 'ai_extracted' if mode=='ai' and rid not in self.draft_edited and self.draft_values[rid]==candidate['value'] else 'user_confirmed'
            values[rid] = base['rules'][rid]['expected'] if mode=='default' else self.draft_values[rid]
            source={'kind':kind,'label':KINDS[kind],'quote':'','input_text':self.spec_text,'file':None,'physical_page':None,'model':None,'parse_kind':None}
            if kind=='ai_extracted':
                source.update(quote=candidate['quote'],model=self.ai_receipt['model'],parse_kind=self.ai_receipt['kind'])
            elif kind=='default_inherited':
                source.update(quote=base['rules'][rid]['quote'],file=base['source_file'],physical_page=base['rules'][rid]['page'],input_text='')
            else:
                source['quote']='用户在网页手动确认值，不宣称原文精确支持'
            sources[rid]=source
        return make_custom_config(base, values, sources)

    def _save_custom(self, data):
        if 'structure_version' in data and self.workbench['active'] is not None:
            from core import rule_bundle as rb
            d=self.current_rule_bundle();t=rb.back.upgrade(data,load_rules(self.rules_path));d['modules']['main']={'template':t,'disabled_fields':[]};d['provenance']['main']=rb.origins('main',d['modules']['main'])
            for x in t['norm_excerpt']:
                if x not in d['excerpt']:d['excerpt'].append(x)
            d['excerpt_sha256']=digest(rb.marked_text(d['excerpt']).encode());d['extraction']=t['extraction'];data=rb.validate(d,load_rules(self.rules_path))
        directory=self.task_dir or self._norm_directory()
        path=directory / ('user-rules-'+uuid4().hex+'.json')
        write_new(path,(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
        self.custom_rules_path=path
        if data.get('format')=='paper-grid-rule-bundle':
            self.workbench['active']=deepcopy(data)
            self.active_template=deepcopy(data['modules']['main']['template'])
            self.active_template_sha256=digest(path.read_bytes())
        elif 'structure_version' in data:
            self.active_template=deepcopy(data)
            self.active_template_sha256=digest(path.read_bytes())
        else:
            self.active_template=None
            self.workbench['active']=None
        self.active_custom_data=deepcopy(data)

    def apply_draft(self):
        try:
            if self.task_dir is None or self.inventory is None:
                raise DemoError('请先选择文档；确认的配置将保存到本会话任务目录')
            self._current()
            data=self.proposed_rules()
            self._save_custom(data)
            self.invalidate()
            self.sync_rules()
            return True
        except Exception as exc:
            self.ai_error=public_error(exc)
            return False

    def use_default_rules(self):
        self.diagnostic_store()["adopted_sha256"]=None
        self.workbench.update(active=None,draft=None,origin="local",historical=True,generation=self.workbench["generation"]+1)
        for attr,module in (("front_draft","front"),("toc_draft","toc"),("note_draft","notes")):
            if getattr(self,attr):
                from core.rule_bundle import defaults
                getattr(self,attr)["template"]=defaults(load_rules(self.rules_path))[module]
        self.custom_rules_path=None
        self.active_custom_data=None
        self.active_template=None
        self.active_template_sha256=None
        self.invalidate()
        self.sync_rules()

"""当前会话的显式预览与L01新轮次；缓存从不跨用户共享。"""
from pathlib import Path
from copy import deepcopy
from uuid import uuid4
import json
from core.package import DemoError,sha256,write_new
from core.preview import render_preview,configuration,valid_artifacts
from core.layout import suggest_figure_pairs,suggest_pagination_aids,apply_pagination_layout

class PreviewSession:
    def init_preview(self):
        self.preview_engine="libreoffice";self.preview_environments={}
        self.width_signature=None;self.width_error=None;self.preview_cache={};self.preview_environment=None;self.preview_error=None;self.layout_error=None;self.layout_signature=None;self.visual_reviews={}

    def preview_targets(self):
        self._current()
        if self.confirmed is None:return {}
        if self.original_path.read_bytes()!=self.original_bytes:raise DemoError('原稿副本发生变化，预览目标已拒绝')
        ctx={'rules_sha256':self.rules_hash,'rules_version':self.report['rules']['version'] if self.report else '',
             'rules_name':self.report['rules']['name'] if self.report else ''}
        def target(path,number,manifest,body):
            return {'path':str(path),'sha256':sha256(Path(path).read_bytes()),'round':number,
                    'classification':deepcopy(manifest),'body':deepcopy(body),'context':{**ctx,'round':number,'file_name':self.display_name}}
        out={'original':target(self.original_path,0,None,None),
             'input':target(self.input_path,self.current_round,self.classification_confirmed,self.confirmed)}
        for h in self.history:
            if h['binding']!=self._history_binding():continue
            r=h['result'];p=Path(r['output'])
            if p.is_file() and sha256(p.read_bytes())==r['output_body_manifest']['input_sha256']:
                out['round-'+str(r['round']['number'])]=target(p,r['round']['number'],r.get('output_classification_manifest'),r['output_body_manifest'])
        # Only locally proved index-preserving history may reuse original positions.
        # Imported/checkpoint histories are untrusted even if their saved kind says format.
        original_indices_match=(out['input']['sha256']==out['original']['sha256'] or (self.project_checkpoint is None and not any(h['result'].get('kind')=='caption_position' for h in self.history)))
        if self.classification_confirmed and original_indices_match:
            out['original']['classification']=deepcopy(self.classification_confirmed)
            out['original']['classification']['input_sha256']=out['original']['sha256']
            from core.table_text import rebind
            rebind(out['original']['classification'],out['original']['sha256'])
        if original_indices_match:
            out['original']['body']=deepcopy(self.confirmed);out['original']['body']['input_sha256']=out['original']['sha256']
        # After a permutation original is render-only; never rebind current p:N to original.
        return out

    def preview_configuration(self):
        if self.preview_engine=="word":
            from core.word_preview import configuration as word_configuration
            return word_configuration()
        return configuration()

    def set_preview_engine(self,engine):
        if engine not in ("word","libreoffice"):raise DemoError("未知预览引擎")
        self.preview_engine=engine;self.preview_environment=self.preview_environments.get(engine)

    def preview_page_batch(self,key,page):
        target=self.preview_targets().get(key);binding=self._preview_binding(target,probe=False) if target else None
        meta=self.preview_cache.get(binding)
        if not meta or meta.get("engine")!="word":raise DemoError("先生成此文件的Word PDF")
        from core.word_preview import batch
        updated=batch(meta,page)
        if self.preview_targets().get(key)!=target:raise DemoError("目标发生变化，未接入页图")
        self.preview_cache[binding]=updated
        from core.word_preview import retire_pages
        retire_pages(updated)
        return updated

    def refresh_preview_environment(self):
        self.preview_environment=self.preview_configuration()
        self.preview_environments[self.preview_engine]=self.preview_environment
        return deepcopy(self.preview_environment[0])

    def _preview_binding(self,t,probe=True):
        if probe:self.refresh_preview_environment()
        if self.preview_environment is None:return None
        _,cfg=self.preview_environment
        return (t['sha256'],cfg,t['round'],self._history_binding())

    def get_preview(self,key,verify_environment=True):
        if not self.preview_cache:return None
        targets=self.preview_targets()
        if key not in targets:return None
        meta=self.preview_cache.get(self._preview_binding(targets[key],probe=verify_environment))
        return meta if meta and valid_artifacts(meta) else None

    def generate_preview(self,key,renderer=None):
        self.preview_error=None
        try:
            targets=self.preview_targets()
            if key not in targets:raise DemoError('预览目标已失效，请重新选择')
            t=targets[key];binding=self._preview_binding(t)
            old=self.preview_cache.get(binding)
            if old and valid_artifacts(old):return True
            self.preview_cache.pop(binding,None)
            result=(renderer or (__import__('core.word_preview',fromlist=['render_preview']).render_preview if self.preview_engine=='word' else render_preview))(t['path'],self.task_dir/'previews',context=t['context'])
            if result['document_sha256']!=t['sha256'] or result['render_config_sha256']!=binding[1] or not valid_artifacts(result):raise DemoError('渲染结果绑定不匹配，预览已拒绝')
            if self.preview_targets().get(key)!=t:raise DemoError('输入或规则变化，预览已失效')
            self.preview_cache[binding]=result
            return True
        except Exception as exc:
            from .session import public_error
            self.preview_error=public_error(exc);return False

    def figure_pairs(self,key):
        t=self.preview_targets().get(key)
        if not t or not t['classification'] or self.mode=='basic':raise DemoError('请在扩展模式确认分类后使用图题辅助')
        return suggest_figure_pairs(t['path'],t['classification'])

    def layout_proposals(self,key):
        t=self.preview_targets().get(key)
        if not t or not t["classification"] or self.mode=="basic":raise DemoError("请先在扩展模式确认分类")
        return self.analysis('pagination',t["path"],t["classification"])

    def generate_layout(self,key,confirmed_keys):
        self.layout_error=None
        try:
            t=self.preview_targets().get(key)
            if not t:raise DemoError('辅助输入已失效，请重新确认')
            sig=(t['sha256'],t['round'],self._history_binding(),tuple(sorted(confirmed_keys)))
            if self.layout_signature==sig and self.result and self.result.get('kind') in ('figure_layout','pagination_layout'):
                self.downloads();return True
            args=self._base_rules_arguments()
            r=apply_pagination_layout(t['path'],self.task_dir/('layout-'+uuid4().hex+'.docx'),t['body'],
                                  mode=self.mode,classification_manifest=t['classification'],confirmed_keys=confirmed_keys,**args)
            if r['after']['rules']['sha256']!=self.rules_hash:
                Path(r['output']).unlink();raise DemoError('规则配置变化，请重新确认')
            self.generation_count+=1
            r['round']={'number':self.generation_count,'input_round':t['round'],'input_sha256':t['sha256'],
                        'original_sha256':sha256(self.original_bytes),'rules_version':r['after']['rules']['version'],'rules_sha256':self.rules_hash}
            r['round_input_path']=t['path']
            self._archive_round(r);self.result=r;self.result_signature=self._signature();self.layout_signature=sig
            self.error=None;return True
        except Exception as exc:
            from .session import public_error
            self.layout_error=public_error(exc);self.result=self.result_signature=None;self.layout_signature=None;return False

    def record_visual_review(self,key,status,notes):
        meta=self.get_preview(key)
        if not meta or status not in ('looked','issues') or not isinstance(notes,str) or len(notes)>1000:raise DemoError('请先生成匹配预览，再记录人工查看结果')
        t=self.preview_targets()[key];review={'method':'human','status':status,'notes':notes,
            'document_sha256':t['sha256'],'round':t['round'],'render_config_sha256':meta['render_config_sha256'],
            'preview_range':meta['preview_range'],'not_automatic_validation':True}
        self.visual_reviews[self._preview_binding(t)]=review
        write_new(self.task_dir/('visual-review-'+uuid4().hex+'.json'),json.dumps(review,ensure_ascii=False,indent=2).encode())

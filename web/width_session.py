"""会话内尺寸计划/独立轮次；不复用其他用户文件。"""
from pathlib import Path
from uuid import uuid4
from core.widths import check_widths,apply_width_adaptation
from core.package import DemoError,sha256

class WidthSession:
    def width_report(self,key):
        t=self.preview_targets().get(key)
        if not t:raise DemoError('宽度检查目标已失效，请重新确认范围')
        return self.analysis('width',t['path'])

    def generate_width(self,key,plan,selected_keys,confirmed_fixed_keys=()):
        self.width_error=None
        try:
            t=self.preview_targets().get(key)
            if not t:raise DemoError('尺寸输入已失效，请重新确认')
            if plan!=self.width_report(key):raise DemoError('尺寸计划与当前文件或规则不匹配，请重新确认')
            sig=(t['sha256'],t['round'],self._history_binding(),plan.get('plan_sha256'),tuple(sorted(selected_keys)),tuple(sorted(confirmed_fixed_keys)))
            if self.width_signature==sig and self.result and self.result.get('kind')=='width_adaptation':
                self.downloads();return True
            r=apply_width_adaptation(t['path'],self.task_dir/('width-'+uuid4().hex+'.docx'),t['body'],mode=self.mode,
                    classification_manifest=t['classification'],plan=plan,selected_keys=selected_keys,confirmed_fixed_keys=confirmed_fixed_keys,**self._base_rules_arguments())
            if r['after']['rules']['sha256']!=self.rules_hash or self.preview_targets().get(key)!=t:
                Path(r['output']).unlink();raise DemoError('文件或规则变化，尺寸结果失效')
            self.generation_count+=1
            r['round']={'number':self.generation_count,'input_round':t['round'],'input_sha256':t['sha256'],'original_sha256':sha256(self.original_bytes),
                        'rules_version':r['after']['rules']['version'],'rules_sha256':self.rules_hash}
            r['round_input_path']=t['path'];self._archive_round(r)
            self.result=r;self.result_signature=self._signature();self.width_signature=sig;self.error=None
            return True
        except Exception as e:
            from .session import public_error
            self.width_error=public_error(e);self.result=self.result_signature=None;self.width_signature=None
            return False

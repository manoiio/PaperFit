"""主线程拥有绑定/会话；后台只接收独立快照及渲染函数。"""
from pathlib import Path
from copy import deepcopy
from uuid import uuid4
import shutil
from core.package import DemoError,sha256
from core.preview import configuration,render_preview,valid_artifacts
from core.preview_jobs import SCHEDULER

class AsyncPreviewSession:
    def init_async_preview(self):
        self.preview_owner=uuid4().hex;self.preview_epoch=0;self.preview_jobs={};self.async_artifact_roots=set();self.preview_view_request=None

    def invalidate_preview_jobs(self):
        if not hasattr(self,'preview_jobs'):return
        for identity,record in self.preview_jobs.items():
            if not record.get('accepted'):
                record['scheduler'].cancel(self.preview_owner,identity)
                record['scheduler'].release(self.preview_owner,identity)
        self.preview_jobs={};self.preview_epoch+=1;self.preview_view_request=None

    def clear_async_artifacts(self):
        self.invalidate_preview_jobs()
        root=(self.work_root/'_preview-jobs').resolve()
        for folder in getattr(self,'async_artifact_roots',set()):
            p=Path(folder)
            if p.parent.resolve()==root and not p.is_symlink():shutil.rmtree(p,ignore_errors=True)
        self.async_artifact_roots=set()

    def submit_preview(self,key,*,scheduler=None,renderer=None):
        scheduler=scheduler or SCHEDULER;self.preview_error=None
        try:
            target=self.preview_targets().get(key)
            if not target:raise DemoError('预览目标已失效，请重新确认')
            binding=self._preview_binding(target)
            cached=self.preview_cache.get(binding)
            if cached and valid_artifacts(cached):return {'state':'cached','id':None}
            raw=Path(target['path']).read_bytes()
            if sha256(raw)!=target['sha256']:raise DemoError('预览输入发生变化，请重新选择')
            identity=scheduler.submit(self.preview_owner,self.work_root/'_preview-jobs',raw,binding,target['context'],renderer or render_preview)
            self.preview_jobs[identity]={'target':deepcopy(target),'key':key,'binding':binding,'epoch':self.preview_epoch,
                                         'scheduler':scheduler,'accepted':False,'state':'queued'}
            return {'state':scheduler.status(self.preview_owner,identity)['state'],'id':identity}
        except Exception as exc:
            from .session import public_error
            self.preview_error=public_error(exc);return {'state':'failed','id':None,'error':self.preview_error}

    def preview_job_status(self,identity):
        """Running/queued polling touches no DOCX/configuration; completion validates once."""
        record=self.preview_jobs.get(identity)
        if not record:return {'state':'missing','error':'任务不属于当前状态，或应用已重启，请重新生成'}
        if record['state']=='invalidated':return {'state':'invalidated','error':record['error']}
        if record['accepted']:return {'id':identity,'state':'succeeded','accepted':True,'elapsed':record['elapsed']}
        scheduler=record['scheduler'];status=scheduler.status(self.preview_owner,identity)
        if status['state']!='succeeded':return status
        try:
            target=self.preview_targets().get(record['key'])
            if record['epoch']!=self.preview_epoch or target!=record['target']:raise DemoError('文件、规则、范围或轮次变化，后台结果已失效')
            config=configuration();self.preview_environment=config
            if config[1]!=record['binding'][1]:raise DemoError('渲染或字体环境已变化，请重新生成')
            result=scheduler.result(self.preview_owner,identity)
            if not result or result['document_sha256']!=target['sha256'] or result['render_config_sha256']!=config[1] or not valid_artifacts(result):raise DemoError('后台页图或哈希核对失败，拒绝接入')
            self.preview_cache[record['binding']]=deepcopy(result)
            # Snapshot root belongs only to this task and survives main input reset until worker exits.
            artifact=Path(result['pages'][0]).resolve()
            root=(self.work_root/'_preview-jobs').resolve()
            for parent in artifact.parents:
                if parent.parent==root:self.async_artifact_roots.add(str(parent));break
            record.update(accepted=True,state='succeeded',elapsed=status['elapsed'])
            scheduler.release(self.preview_owner,identity,retain_files=True)
            return {'id':identity,'state':'succeeded','accepted':True,'elapsed':status['elapsed']}
        except Exception as exc:
            from .session import public_error
            scheduler.cancel(self.preview_owner,identity);scheduler.release(self.preview_owner,identity)
            record['state']='invalidated';record['error']=public_error(exc)
            return {'state':'invalidated','error':record['error'],'elapsed':status['elapsed']}

    def cancel_preview(self,identity):
        record=self.preview_jobs.get(identity)
        if not record:raise DemoError('此任务不属于当前会话')
        record['scheduler'].cancel(self.preview_owner,identity)
        return record['scheduler'].status(self.preview_owner,identity)

    def active_preview_job(self,key):
        for identity,record in reversed(list(self.preview_jobs.items())):
            if record['key']==key and record['epoch']==self.preview_epoch:
                state=self.preview_job_status(identity)
                if state['state'] in ('queued','running'):return identity
        return None

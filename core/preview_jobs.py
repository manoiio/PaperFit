"""只调度渲染的进程内单工作线程；不导入Streamlit，不读取会话。"""
from collections import deque
from copy import deepcopy
from pathlib import Path
from threading import Condition,Thread,Lock
from uuid import uuid4
import time,shutil
from .package import DemoError,sha256,write_new

class PreviewJobs:
    def __init__(self,max_queued=2):
        self.max_queued=max_queued;self.lock=Condition();self.queue=deque();self.jobs={};self.active=None;self.thread=None

    def submit(self,owner,root,raw,binding,context,renderer,discard_cleanup=None):
        with self.lock:
            for job in self.jobs.values():
                if job['owner']==owner and job['binding']==binding and job['state'] in ('queued','running'):return job['id']
            # First task gets one running slot; only two other tasks may wait.
            pending=len(self.queue)+(1 if self.active else 0)
            if pending>=self.max_queued+1 or (self.active is None and self.queue and len(self.queue)>=self.max_queued):raise DemoError('预览队列已满，请稍后明确重试；检查与下载仍可使用')
            identity=uuid4().hex;folder=Path(root).resolve()/identity;folder.mkdir(parents=True,exist_ok=False)
            write_new(folder/'input.docx',raw)
            self.jobs[identity]={'id':identity,'owner':owner,'root':str(folder),'binding':deepcopy(binding),'context':deepcopy(context),
                                 'input_sha256':sha256(raw),'state':'queued','created':time.monotonic(),'started':None,'finished':None,
                                 'discard':False,'result':None,'error':None,'renderer':renderer,'discard_cleanup':discard_cleanup}
            self.queue.append(identity)
            if self.thread is None or not self.thread.is_alive():
                self.thread=Thread(target=self._work,name='paper-preview',daemon=True);self.thread.start()
            self.lock.notify_all();return identity

    def _owned(self,owner,identity):
        job=self.jobs.get(identity)
        if job is None:return None
        if job['owner']!=owner:raise DemoError('此预览任务不属于当前会话')
        return job

    def status(self,owner,identity):
        with self.lock:
            job=self._owned(owner,identity)
            if job is None:return {'state':'missing','error':'预览任务已丢失或应用重启，请重新生成'}
            return {k:deepcopy(v) for k,v in job.items() if k not in ('owner','root','renderer','discard_cleanup','context','result','binding')}|{'elapsed':(job['finished'] or time.monotonic())-job['created']}

    def result(self,owner,identity):
        with self.lock:
            job=self._owned(owner,identity)
            return deepcopy(job['result']) if job and job['state']=='succeeded' and not job['discard'] else None

    def cancel(self,owner,identity):
        with self.lock:
            job=self._owned(owner,identity)
            if not job:return
            job['discard']=True
            if job['state']=='queued':
                self.queue.remove(identity);job['state']='cancelled';job['error']='已取消排队，本任务不会启动';job['finished']=time.monotonic();shutil.rmtree(job['root'],ignore_errors=True)
            elif job['state']=='running':job['state']='cancelled';job['error']='停止接收结果；不表示子进程已停止，等待本任务退出；本地渲染器按各自超时边界处理'
            elif job['state']=='succeeded':
                if job.get('discard_cleanup') and job.get('result'):
                    try:job['discard_cleanup'](job['result'])
                    except Exception:job['cleanup_deferred']=True
                job['state']='invalidated';job['result']=None;shutil.rmtree(job['root'],ignore_errors=True)

    def release(self,owner,identity,retain_files=False):
        with self.lock:
            job=self._owned(owner,identity)
            if not job or identity==self.active or job['state'] in ('queued','running'):return
            if not retain_files:shutil.rmtree(job['root'],ignore_errors=True)
            self.jobs.pop(identity,None)

    def _work(self):
        while True:
            with self.lock:
                if not self.queue:self.thread=None;return
                identity=self.queue.popleft();job=self.jobs[identity];self.active=identity;job['state']='running';job['started']=time.monotonic()
            result=None
            try:
                result=job['renderer'](Path(job['root'])/'input.docx',Path(job['root'])/'pages',context=deepcopy(job['context']))
                if result.get('document_sha256')!=job['input_sha256'] or result.get('render_config_sha256')!=job['binding'][1]:raise DemoError('后台预览的文件或环境绑定不匹配')
                if sha256((Path(job['root'])/'input.docx').read_bytes())!=job['input_sha256']:raise DemoError('后台输入快照发生变化')
                with self.lock:
                    if not job['discard']:job['result']=result;job['state']='succeeded'
            except Exception as exc:
                with self.lock:
                    if not job['discard']:
                        job['state']='failed';job['error']=str(exc) if isinstance(exc,DemoError) else '本地后台渲染失败，请重新明确请求'
            finally:
                with self.lock:
                    job['finished']=time.monotonic();self.active=None
                    if job['discard']:
                        if result and job.get('discard_cleanup'):
                            try:job['discard_cleanup'](result)
                            except Exception:job['cleanup_deferred']=True
                        shutil.rmtree(job['root'],ignore_errors=True)
                    # Keep only a bounded terminal registry; accepted page files have separate owners.
                    old=[j for j in self.jobs.values() if j['state'] not in ('queued','running') and j['id']!=identity]
                    for j in old[:-32]:
                        shutil.rmtree(j['root'],ignore_errors=True);self.jobs.pop(j['id'],None)

SCHEDULER=PreviewJobs()
RENDER_LOCK=Lock()

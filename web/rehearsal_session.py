"""Session-owned actual rehearsals; adoption reuses bytes, never re-runs fixing."""
from copy import copy,deepcopy
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timezone
import json,shutil,os,time
from core.package import DemoError,Package,sha256,write_new
from core.rehearsal import reconcile,validate_existing_result
from .scope_session import fingerprint

ROOT=Path(__file__).resolve().parents[1]
VERSION='format-rehearsal-v1'

def execution_hash():
    paths=sorted((ROOT/'core').glob('*.py'))+[ROOT/'web/session.py',Path(__file__),ROOT/'web/scope_session.py']
    return fingerprint({str(p.relative_to(ROOT)):sha256(p.read_bytes()) for p in paths})

class RehearsalSession:
    def init_rehearsal(self):
        self.rehearsal=None;self.rehearsal_error=None

    def cancel_rehearsal(self):
        r=getattr(self,'rehearsal',None);cleanup_failed=False
        if r:
            p=Path(r['directory'])
            # Never enumerate/delete other tasks or formally adopted files.
            if self.task_dir and p.parent==self.task_dir and p.name.startswith('rehearsal-') and not p.is_symlink():
                if p.exists():
                    try:shutil.rmtree(p)
                    except OSError:cleanup_failed=True
        self.init_rehearsal()
        if cleanup_failed:self.rehearsal_error='预演已取消且不可采用；临时文件暂未清理，重新开始时将清理本任务。'

    def rehearsal_binding(self, *, generation_count=None, history=None):
        self._current()
        if self.report is None or self.confirmed is None:raise DemoError('检查已失效，请重新确认范围并检查')
        if not self.selected or set(self.selected)-{f['key'] for f in self.eligible()}:raise DemoError('请明确选择当前可修正项')
        scope=self._scope_snapshot()
        if scope['actual_input_sha256']!=self.inventory['input_sha256']:raise DemoError('输入已变化')
        # Drafts, ALL actual confirmations, report, file bytes, dependency bytes,
        # current round and executable source are bound independently of filenames.
        return fingerprint({'scope':scope,'confirmed':self.confirmed,'classification':self.classification_confirmed,
                            'native_confirmations':{a:deepcopy(getattr(self,a+'_confirmed')) for a in ('table','front','toc','citation','note','caption')},
                            'selected':self.selected,'report':self.report,'revision':self.report_revision,'generation_count':self.generation_count if generation_count is None else generation_count,
                            'history_outputs':[h['result']['output_body_manifest']['input_sha256'] for h in (self.history if history is None else history)],
                            'rule_dependencies':{p.name:sha256(p.read_bytes()) for p in sorted((ROOT/'rules').glob('*.json'))},
                            'version':VERSION,'execution_sha256':execution_hash()})

    def rehearsal_view(self):
        r=self.rehearsal
        if not r:return None
        try:
            if self.rehearsal_binding()!=r.get('adopted_binding',r['binding']):raise DemoError('输入、规则、范围或选择已变化，请重新预演')
            if r.get('adopted_round'):
                if not self.result or self.result.get('rehearsal',{}).get('id')!=r['id'] or not self.downloads():raise DemoError('已采用副本不再对应当前结果')
                return deepcopy(r['view'])
            p=Path(r['result']['output']);report=Path(r['directory'])/'transaction.json'
            if p.is_symlink() or not p.is_file() or sha256(p.read_bytes())!=r['output_sha256']:raise DemoError('预演副本缺失或被修改，请重新预演')
            if not report.is_file() or sha256(report.read_bytes())!=r['report_sha256'] or fingerprint(r['result'])!=r['result_sha256'] or fingerprint(r['view'])!=r['view_sha256']:
                raise DemoError('预演报告或影响记录不匹配，请重新预演')
            return deepcopy(r['view'])
        except Exception as exc:
            from .session import public_error
            message=public_error(exc);self.cancel_rehearsal();self.rehearsal_error=message
            return None

    def rehearse(self):
        start=time.perf_counter()
        try:
            binding=self.rehearsal_binding()
            if self.rehearsal_view() is not None and self.rehearsal['binding']==binding:return True
            self.cancel_rehearsal()
            directory=self.task_dir/('rehearsal-'+uuid4().hex);directory.mkdir()
            self.rehearsal={'directory':str(directory)}  # ownership even if engine/storage fails
            from . import session as api
            result=api.fix_document(self.input_path,directory/'fixed.docx',self.confirmed,selected_keys=self.selected,**self._rules_arguments())
            if self.rehearsal_binding()!=binding:raise DemoError('处理时绑定发生变化，请重新预演')
            if result['after']['rules']['sha256']!=self.rules_hash:raise DemoError('规则在预演时变化')
            impact=reconcile(result,Package(self.input_path),Package(result['output']))
            selected=[{'key':f['key'],'locator':deepcopy(f['locator']),'rule_id':f['rule_id'],'actual':deepcopy(f['actual']),'expected':deepcopy(f['expected']),'source':deepcopy(f['source'])} for f in self.report['findings'] if f['key'] in self.selected]
            view={'id':directory.name,'binding':binding,'input_round':self.current_round,'output_is_formal':False,
                  'rules':{k:result['before']['rules'][k] for k in ('name','version','sha256')},
                  'input_sha256':result['before']['input_sha256'],'output_sha256':result['after']['input_sha256'],
                  'scope':deepcopy(self.classification_confirmed or self.confirmed),'selected':selected,
                  'changes':deepcopy(result['changes']),'impact':impact,
                  'created_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-start,
                  'execution_version':VERSION,'execution_sha256':execution_hash()}
            report=write_new(directory/'transaction.json',(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode())
            self.rehearsal={'id':directory.name,'directory':str(directory),'binding':binding,'result':result,'view':view,
                            'output_sha256':result['after']['input_sha256'],'report_sha256':sha256(report.read_bytes()),
                            'result_sha256':fingerprint(result),'view_sha256':fingerprint(view),'adopted_round':None}
            self.rehearsal_error=None;return True
        except Exception as exc:
            from .session import public_error
            self.cancel_rehearsal();self.rehearsal_error='预演未生成：'+public_error(exc)
            return False

    def rehearsal_download(self):
        view=self.rehearsal_view()
        if view is None:raise DemoError('没有可用预演记录')
        from .reading_report import clean
        return (json.dumps(clean(view),ensure_ascii=False,indent=2)+'\n').encode()

    def adopt_rehearsal(self, identifier, *, acknowledged=False):
        start=time.perf_counter();archive=None;destination=None
        try:
            if acknowledged is not True:raise DemoError('请先核对实际修改、关联影响及剩余事项')
            view=self.rehearsal_view();r=self.rehearsal
            if not view or identifier!=r['id']:raise DemoError('预演已失效，请重新预演并核对')
            if r['adopted_round'] is not None:return True
            binding=self.rehearsal_binding()
            proof=validate_existing_result(self.input_path,r['result'],self.confirmed,selected_keys=self.selected,**self._rules_arguments())
            if self.rehearsal_binding()!=binding:raise DemoError('确认采用时文件、规则或范围变化')
            # Exclusive hard link: same verified DOCX bytes; never reserialize or overwrite.
            destination=self.task_dir/('fixed-'+uuid4().hex+'.docx')
            os.link(r['result']['output'],destination)
            result=deepcopy(r['result']);result['output']=str(destination);result['after']['input']=str(destination.resolve())
            number=self.generation_count+1
            result['round']={'number':number,'input_round':self.current_round,'input_sha256':self.inventory['input_sha256'],
                             'original_sha256':sha256(self.original_bytes),'rules_version':result['after']['rules']['version'],'rules_sha256':self.rules_hash}
            for key in ('front_supplement','toc_supplement'):
                if result['after']['rules'].get(key):result['round'][key+'_sha256']=result['after']['rules'][key]['sha256']
            result['rehearsal']={'id':r['id'],'binding':binding,'execution_version':VERSION,'execution_sha256':view['execution_sha256'],
                                  'created_at':view['created_at'],'adopted_at':datetime.now(timezone.utc).isoformat(),
                                  'rehearsal_transaction_sha256':r['report_sha256'],'validation':proof,
                                  'fix_calls_at_adoption':0,'validation_elapsed_seconds':time.perf_counter()-start,
                                  'input_still_current_at_adoption':True,'output_auto_switched_at_adoption':False}
            result['impact']=deepcopy(view['impact'])
            # Original archive writer on an isolated state and owned storage.
            # Nothing is published to live history/count/result until ALL writes
            # and the final byte/snapshot verification succeed.
            archive=self.task_dir/('round-records-'+uuid4().hex);archive.mkdir()
            staged=copy(self);staged.task_dir=archive;staged.history=deepcopy(self.history)
            staged.center_cache=deepcopy(self.center_cache)
            staged._archive_round(result)
            if self.rehearsal_binding()!=binding or sha256(destination.read_bytes())!=r['output_sha256'] or self.rehearsal_view() is None:
                raise DemoError('归档期间预演绑定变化，未登记正式轮次')
            entry=staged.history[-1];entry['stem']=archive.name+'/'+entry['stem']
            adopted_binding=self.rehearsal_binding(generation_count=number,history=[*self.history,entry])
            if self.rehearsal_binding()!=binding:raise DemoError('登记前绑定发生变化，未发布轮次')
            signature=self._signature()
            # From here only in-memory publication; no fallible validation/storage.
            self.history.append(entry);self.generation_count=number;self.result=result;self.result_signature=signature
            r['adopted_round']=number
            r['adopted_binding']=adopted_binding
            owned=Path(r['directory'])
            try:shutil.rmtree(owned)
            except Exception:r['cleanup_pending']=True  # never roll back a published valid round
            self.rehearsal_error='正式副本已登记；本会话预演目录暂未清理，取消预演或重新开始可重试。' if r.get('cleanup_pending') else None
            self.error=None
            return True
        except Exception as exc:
            if destination and destination.exists():destination.unlink()
            if archive and archive.exists():shutil.rmtree(archive)
            from .session import public_error
            self.rehearsal_error='未采用副本：'+public_error(exc)
            return False

"""At most two existing transactions; all archives published together, zero refixing."""
from copy import copy,deepcopy
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timezone
import json,os,shutil,time
from core.package import Package,DemoError,sha256,write_new
from core import check_document
from core.correction_plan import draft,handoff,resolve_targets,VERSION
from core.rehearsal import reconcile,validate_existing_result
from .scope_session import fingerprint

def encoded(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()

class PlanSession:
    def correction_plan(self):
        self._current()
        if self.report is None or self.confirmed is None:raise DemoError('请先确认范围并检查')
        p=draft(self.report,self.selected,Package(self.input_path),self.classification_confirmed)
        p['binding']=self.rehearsal_binding() if self.selected and not p['blocked'] else None
        p['input_sha256']=self.inventory['input_sha256'];p['input_round']=self.current_round
        p['rules']={k:self.report['rules'][k] for k in ('name','version','sha256')}
        p['scope']=deepcopy(self.classification_confirmed or self.confirmed)
        return p

    def plan_rehearsal_view(self):
        r=self.rehearsal
        try:
            if self.rehearsal_binding()!=r.get('adopted_binding',r['binding']):raise DemoError('文件、规则、范围、选择或轮次已变化，请重新预演计划')
            if r.get('adopted_rounds'):
                if not self.result or self.result.get('plan',{}).get('summary',{}).get('id')!=r['id']:raise DemoError('计划不再对应当前结果')
                self.plan_step_downloads();return deepcopy(r['view'])
            if fingerprint({'draft':r['draft'],'transactions':r['transactions'],'view':r['view'],'resolved':r['resolved']})!=r['seal']:raise DemoError('计划、范围或报告不匹配')
            for tx in r['transactions']:
                p=Path(tx['result']['output']);src=Path(tx['input'])
                if p.is_symlink() or not p.is_file() or sha256(p.read_bytes())!=tx['result']['after']['input_sha256']:raise DemoError('计划中间或最终副本缺失/被修改')
                if sha256(src.read_bytes())!=tx['result']['before']['input_sha256']:raise DemoError('计划步骤输入父子关系失效')
                report=Path(tx['record'])
                if not report.is_file() or sha256(report.read_bytes())!=tx['record_sha256']:raise DemoError('步骤落盘报告不匹配')
            return deepcopy(r['view'])
        except Exception as exc:
            from .session import public_error
            msg=public_error(exc);self.cancel_rehearsal();self.rehearsal_error=msg;return None

    def rehearse_plan(self):
        try:
            p=self.correction_plan()
            if p['blocked']:raise DemoError('计划含不能进入的项目：'+'；'.join(x['reason'] for x in p['blocked']))
            if not p['two_steps']:return self.rehearse()  # original one-step path, no extra artifact
            if self.rehearsal and self.rehearsal.get('kind')=='format_plan' and self.plan_rehearsal_view():return True
            self.cancel_rehearsal();binding=p['binding'];start=time.perf_counter()
            directory=self.task_dir/('rehearsal-plan-'+uuid4().hex);directory.mkdir();self.rehearsal={'directory':str(directory)}
            from . import session as api
            args=self._rules_arguments();body=deepcopy(self.confirmed)
            one=api.fix_document(self.input_path,directory/'step-1.docx',body,selected_keys=p['steps'][0]['keys'],**args)
            mid=Package(one['output']);sc=handoff(Package(self.input_path),mid,one['output_classification_manifest'])
            args2={**self._base_rules_arguments(),'mode':self.mode,'classification_manifest':sc}
            fresh=check_document(one['output'],one['output_body_manifest'],**args2)
            resolved=resolve_targets(mid,sc,p['targets'],fresh);keys=[x['new_key'] for x in resolved if x['status']=='待修正']
            transactions=[]
            def add(result,source,body_,classification,keys_):
                record=write_new(directory/f'transaction-{len(transactions)+1}.json',encoded(result))
                transactions.append({'result':result,'input':str(source),'body':deepcopy(body_),'classification':deepcopy(classification),'keys':list(keys_),
                                     'record':str(record),'record_sha256':sha256(record.read_bytes())})
            add(one,self.input_path,body,self.classification_confirmed,p['steps'][0]['keys'])
            if keys:
                two=api.fix_document(one['output'],directory/'step-2.docx',one['output_body_manifest'],selected_keys=keys,**args2)
                if two['before']!=fresh:raise DemoError('第二步没有使用实际第一步副本的新检查')
                add(two,one['output'],one['output_body_manifest'],sc,keys)
            final=transactions[-1]['result'];steps=[]
            for i,tx in enumerate(transactions,1):
                rr=tx['result'];steps.append({'number':i,'engine_calls':1,'input_sha256':rr['before']['input_sha256'],'output_sha256':rr['after']['input_sha256'],
                      'selected_keys':tx['keys'],'changes':deepcopy(rr['changes']),'scope_sha256':fingerprint(tx['classification']),
                      'output_scope_sha256':fingerprint(rr.get('output_classification_manifest') or rr['output_body_manifest']),
                      'impact':reconcile(rr,Package(tx['input']),Package(rr['output'])),'status':'实际修正及落盘复查通过'})
            if not keys:steps.append({'number':2,'engine_calls':0,'status':'所选引文已经符合，无需修改','changes':[],'impact':None,
                                      'input_sha256':mid.hash,'output_sha256':mid.hash,'selected_keys':[]})
            aggregate={'before':one['before'],'after':final['after'],'changes':[c for tx in transactions for c in tx['result']['changes']]}
            overall=reconcile(aggregate,Package(self.input_path),Package(final['output']))
            view={'id':directory.name,'version':VERSION,'binding':binding,'draft':p,'steps':steps,'resolved_targets':resolved,'overall_impact':overall,
                  'engine_calls':len(transactions),'formal_rounds':0,'expected_adopted_rounds':len(transactions),'actual_change_records':len(aggregate['changes']),
                  'created_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-start,
                  'selected_outcomes':[{'origin_key':k,'status':'逐步读回复查通过，后续只允许所选上标变化'} for k in p['selected_keys']]}
            if self.rehearsal_binding()!=binding:raise DemoError('计划预演期间绑定变化')
            r={'kind':'format_plan','id':directory.name,'directory':str(directory),'binding':binding,'draft':p,'transactions':transactions,'view':view,'resolved':resolved,'adopted_rounds':None}
            r['seal']=fingerprint({k:r[k] for k in ('draft','transactions','view','resolved')});self.rehearsal=r;self.rehearsal_error=None;return True
        except Exception as exc:
            from .session import public_error
            self.cancel_rehearsal();self.rehearsal_error='整计划未完成，未登记正式轮次：'+public_error(exc);return False

    def adopt_plan(self,identifier,*,acknowledged=False):
        archive=None;destinations=[];start=time.perf_counter()
        try:
            if acknowledged is not True:raise DemoError('请核对完整计划、各步及最终影响')
            view=self.plan_rehearsal_view();r=self.rehearsal
            if not view or r['id']!=identifier:raise DemoError('计划已失效，请重新预演')
            if r['adopted_rounds']:return True
            binding=self.rehearsal_binding();txs=r['transactions'];proofs=[]
            from core.project import MAX_ROUNDS
            if len(self.history)+len(txs)>MAX_ROUNDS:raise DemoError('计划会超过现有历史上限，请明确减少历史后再处理')
            for i,tx in enumerate(txs):
                args={**self._base_rules_arguments(),'mode':self.mode,'classification_manifest':tx['classification']}
                if i and (tx['input']!=txs[i-1]['result']['output'] or tx['body']!=txs[i-1]['result']['output_body_manifest'] or tx['classification']!=txs[i-1]['result']['output_classification_manifest']):raise DemoError('计划真实父子范围不对应')
                proofs.append(validate_existing_result(tx['input'],tx['result'],tx['body'],selected_keys=tx['keys'],**args))
            one=txs[0]['result'];mid=Package(one['output']);sc=handoff(Package(self.input_path),mid,one['output_classification_manifest'])
            fresh=check_document(one['output'],one['output_body_manifest'],**{**self._base_rules_arguments(),'mode':self.mode,'classification_manifest':sc})
            if resolve_targets(mid,sc,r['draft']['targets'],fresh)!=r['resolved']:raise DemoError('引文重新定位证据变化')
            if not self.plan_rehearsal_view() or self.rehearsal_binding()!=binding:raise DemoError('采用前计划绑定变化')
            archive=self.task_dir/('plan-records-'+uuid4().hex);archive.mkdir()
            staged=copy(self);staged.task_dir=archive;staged.history=deepcopy(self.history);staged.center_cache=deepcopy(self.center_cache)
            summary=deepcopy(view);summary.pop('draft');summary.update(adopted_at=datetime.now(timezone.utc).isoformat(),formal_rounds=len(txs),fix_calls_at_adoption=0,
                 validation=proofs,input_auto_switched=False,intermediate_docx_in_result_package=False,
                 rounds=[{'number':self.generation_count+i+1,'parent':self.current_round if i==0 else self.generation_count+i,'input_sha256':tx['result']['before']['input_sha256'],'output_sha256':tx['result']['after']['input_sha256']} for i,tx in enumerate(txs)])
            results=[];entries=[]
            for i,tx in enumerate(txs):
                dest=self.task_dir/('fixed-plan-'+uuid4().hex+f'-step-{i+1}.docx');os.link(tx['result']['output'],dest);destinations.append(dest)
                rr=deepcopy(tx['result']);rr['output']=str(dest);rr['after']['input']=str(dest.resolve())
                source=self.input_path if i==0 else destinations[i-1];rr['before']['input']=str(source.resolve());rr['round_input_path']=str(source)
                row=summary['rounds'][i];rr['round']={'number':row['number'],'input_round':row['parent'],'input_sha256':row['input_sha256'],
                  'original_sha256':sha256(self.original_bytes),'rules_version':rr['after']['rules']['version'],'rules_sha256':self.rules_hash}
                rr['plan']={'summary':summary,'step':i+1};rr['impact']=deepcopy(view['steps'][i]['impact'])
                for k in ('front_supplement','toc_supplement'):
                    if rr['after']['rules'].get(k):rr['round'][k+'_sha256']=rr['after']['rules'][k]['sha256']
                staged._archive_round(rr);h=staged.history[-1]
                self._verify_plan_archive(archive,h,rr)
                entry=deepcopy(h);entry['stem']=archive.name+'/'+entry['stem'];entries.append(entry);results.append(rr)
            record=write_new(archive/'plan-summary.json',encoded(summary))
            if record.read_bytes()!=encoded(summary):raise DemoError('计划摘要存储不匹配')
            for entry,rr in zip(entries,results):
                self._verify_plan_archive(archive,{**entry,'stem':entry['stem'].split('/',1)[1]},rr)
            if record.read_bytes()!=encoded(summary):raise DemoError('发布前计划摘要变化')
            for dest,tx in zip(destinations,txs):
                if sha256(dest.read_bytes())!=tx['result']['after']['input_sha256']:raise DemoError('正式副本字节变化')
            if not self.plan_rehearsal_view() or self.rehearsal_binding()!=binding:raise DemoError('归档期间绑定变化，整计划未发布')
            future=self.rehearsal_binding(generation_count=self.generation_count+len(txs),history=[*self.history,*entries]);signature=self._signature()
            if self.rehearsal_binding()!=binding:raise DemoError('发布前绑定变化')
            self.history=[*self.history,*entries];self.generation_count+=len(txs);self.result=results[-1];self.result_signature=signature
            r['adopted_rounds']=[x['number'] for x in summary['rounds']];r['adopted_binding']=future
            try:shutil.rmtree(r['directory'])
            except Exception:r['cleanup_pending']=True
            self.rehearsal_error='计划已采用；临时目录尚未清理，可重新开始时清理。' if r.get('cleanup_pending') else None
            self.error=None;return True
        except Exception as exc:
            for p in destinations:
                if p.exists():p.unlink()
            if archive and archive.exists():shutil.rmtree(archive)
            from .session import public_error
            self.rehearsal_error='整计划未采用，未发布任何新轮次：'+public_error(exc);return False

    def _verify_plan_archive(self,directory,entry,result):
        from core.report import markdown,modification_markdown
        stem=entry['stem'];j=lambda x:(json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode()
        expected={'.json':j(result),'-changes.md':modification_markdown(result).encode(),'-recheck.md':markdown(result['after']).encode(),
                  '.body.json':j(result['output_body_manifest']),'-reading.json':j(entry['reading_bundle']),'-rules.json':Path(self.custom_rules_path or self.rules_path).read_bytes()}
        if result.get('output_classification_manifest'):expected['.types.json']=j(result['output_classification_manifest'])
        if any((directory/(stem+suffix)).read_bytes()!=data for suffix,data in expected.items()):raise DemoError('步骤归档文件与实际记录不一致')

    def plan_step_downloads(self):
        if not self.result or not self.result.get('plan'):raise DemoError('没有当前正式计划')
        self._current()
        if self.result_signature!=self._signature():raise DemoError('计划结果已失效')
        summary=self.result['plan']['summary'];out=[]
        for row in summary['rounds']:
            h=next((h for h in self.history if h['result']['round']['number']==row['number'] and h['result']['after']['input_sha256']==row['output_sha256']),None)
            if not h:raise DemoError('计划步骤历史缺失')
            rr=h['result'];p=Path(rr['output']);source=Path(rr['round_input_path'])
            if not p.is_file() or p.is_symlink() or sha256(p.read_bytes())!=row['output_sha256'] or not source.is_file() or sha256(source.read_bytes())!=row['input_sha256']:raise DemoError('计划副本或父步骤字节变化，不能下载')
            from core.report import markdown,modification_markdown
            out.append({'round':row['number'],'fixed.docx':p.read_bytes(),'changes.md':modification_markdown(rr).encode(),'recheck.md':markdown(rr['after']).encode()})
        return out

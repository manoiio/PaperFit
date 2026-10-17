"""Reuses the bounded owned background queue and original archive/adoption contract."""
from copy import deepcopy,copy
from pathlib import Path
from uuid import uuid4
import os,json,shutil
from core.package import Package,DemoError,sha256,write_new
from core.preview_jobs import PreviewJobs
from core import check_document,word_fields
from .dynamic_session import context,valid
from .scope_session import fingerprint
JOBS=PreviewJobs()

def render_worker(source,out,*,context):
 out.mkdir();c=context
 r=word_fields.update(source,out/'fields.docx',c['classification'],c['plan'],artifact_dir=out)
 if r is None:return {'document_sha256':sha256(source.read_bytes()),'render_config_sha256':c['seal'],'result':None}
 before=check_document(source,mode='academic',classification_manifest=c['classification'],**c['rules'])
 after=check_document(r['output'],mode='academic',classification_manifest=r['classification'],**c['rules'])
 from core.caption_move import mapped_delta
 from core.toc import nodes
 oldpkg=Package(source);newpkg=Package(r['output']);oldnodes=nodes(oldpkg);newnodes=nodes(newpkg);pm=r['proof']['paragraph_map'];dm={}
 for i,p in enumerate(oldnodes,1):
  if p in oldpkg.paragraphs:
   n=str(oldpkg.paragraphs.index(p)+1)
   if n in pm:dm['d:'+str(i)]='d:'+str(newnodes.index(newpkg.paragraphs[int(pm[n])-1])+1)
 comparable=deepcopy(before);unmapped=[];kept=[]
 for f in comparable['findings']:
  loc=f['locator']
  if loc.get('paragraph') is not None and str(loc['paragraph']) not in pm or loc.get('toc_object') is not None and 'd:'+str(loc['toc_object']) not in dm:unmapped.append(f['key'])
  else:kept.append(f)
 comparable['findings']=[{**f,'locator':deepcopy(f['locator'])} for f in kept];delta=mapped_delta(comparable,deepcopy(after),{'paragraphs':pm,'toc_objects':dm});delta['unaligned_cache_records']=unmapped
 result={'kind':'field_update','output':r['output'],'before':before,'after':after,'changes':r['changes'],'skipped_review_keys':[],'input_classification_manifest':c['classification'],'output_classification_manifest':r['classification'],'output_body_manifest':{'input_sha256':r['proof']['output_sha256'],'body_paragraphs':after['coverage']['body_paragraphs'],'confirmation':'目录替换按存活XML对象身份重绑；新缓存不冒充正文'},'preservation':r['proof'],'field_update':{'plan':c['plan'],'validation':r['proof']},'problem_delta':delta}
 result['preservation'].update(original_sha256_unchanged=sha256(source.read_bytes())==c['plan']['input_sha256'],only_authorized_field_caches=True,unselected_zip_member_bytes_equal=True)
 return {'document_sha256':sha256(source.read_bytes()),'render_config_sha256':c['seal'],'result':result}

def submit(model,state,*,selected=None,creation=None,scheduler=None,worker=None):
 ctx,b=context(model);p=word_fields.plan(ctx['input'],ctx['classification'],selected,creation)
 if not p['selected'] and not p['creation']:state.update(empty=True,kept=p['kept']);return False
 seal=fingerprint(p);owner=state.setdefault('owner',uuid4().hex);scheduler=scheduler or JOBS
 identity=scheduler.submit(owner,model.work_root/'_word-jobs',Path(ctx['input']).read_bytes(),(b,seal),{'plan':p,'classification':ctx['classification'],'rules':model._base_rules_arguments(),'seal':seal},worker or render_worker)
 state.update(identity=identity,binding=b,context=ctx,scheduler=scheduler,plan=p,empty=False);return True

def receive(model,state):
 status=state['scheduler'].status(state['owner'],state['identity'])
 if status['state']!='succeeded':return status
 if context(model)[1]!=state['binding']:
  state['scheduler'].cancel(state['owner'],state['identity']);return {'state':'invalidated','error':'输入、规则、范围或轮次变化，Word结果不采用'}
 if not state.get('result'):
  payload=state['scheduler'].result(state['owner'],state['identity']);r=payload['result']
  if not r:raise DemoError('没有可发布的域更新结果')
  folder=Path(r['output']).parent;rec=write_new(folder/'transaction.json',(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n').encode());state.update(result=r,directory=str(folder),result_sha256=fingerprint(r),record_sha256=sha256(rec.read_bytes()))
 return status

def adopt(model,state):
 if state.get('adopted'):
  if context(model)[1]!=state['adopted_binding']:raise DemoError('采用记录失效')
  model.downloads();return True
 r=valid(model,state);ctx=state['context'];dest=None;folder=None
 try:
  if len(model.history)>=30:raise DemoError('历史已达30轮')
  if sha256(Path(ctx['input']).read_bytes())!=r['preservation']['input_sha256']:raise DemoError('Word父文件变化')
  if check_document(r['output'],mode='academic',classification_manifest=r['output_classification_manifest'],**model._base_rules_arguments())!=r['after']:raise DemoError('最终回填文件复查不符')
  dest=model.task_dir/('fields-fixed-'+uuid4().hex+'.docx');os.link(r['output'],dest);rr=deepcopy(r);rr['output']=str(dest);rr['after']['input']=str(dest.resolve());rr['round_input_path']=ctx['input'];number=model.generation_count+1
  rr['round']={'number':number,'input_round':ctx['parent'],'input_sha256':ctx['sha256'],'original_sha256':sha256(model.original_bytes),'rules_version':rr['after']['rules']['version'],'rules_sha256':model.rules_hash}
  rr['field_update']['adoption']={'fix_calls':0,'Word_calls':0,'current_input_auto_switched':False}
  folder=model.task_dir/('round-records-fields-'+uuid4().hex);folder.mkdir();staged=copy(model);staged.task_dir=folder;staged.history=deepcopy(model.history);staged.center_cache=deepcopy(model.center_cache);staged._archive_round(rr);staged._verify_plan_archive(folder,staged.history[-1],rr)
  if context(model)[1]!=state['binding'] or valid(model,state) is None:raise DemoError('Word归档期间绑定变化')
  entry=deepcopy(staged.history[-1]);entry['stem']=folder.name+'/'+entry['stem'];future={**ctx,'input':str(dest),'sha256':rr['after']['input_sha256'],'classification':rr['output_classification_manifest'],'parent':number,'history':number}
  model.history.append(entry);model.generation_count=number;model.result=rr;model.result_signature=model._signature();state.update(adopted=number,adopted_binding=fingerprint(future));return True
 except Exception:
  if dest:dest.unlink(missing_ok=True)
  if folder:shutil.rmtree(folder,ignore_errors=True)
  raise

def cancel(state):
 if state.get('identity'):state['scheduler'].cancel(state['owner'],state['identity'])

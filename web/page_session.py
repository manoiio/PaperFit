"""The existing archive/adoption contract around a separate structural transaction."""
from copy import deepcopy,copy
from pathlib import Path
from uuid import uuid4
import os,shutil,json
from core.package import DemoError,Package,sha256,write_new
from core import page_layout,check_document
from .dynamic_session import context,cancel
from .scope_session import fingerprint

def preview(model,state,policy,regions):
 ctx,b=context(model);cancel(model,state)
 plan=page_layout.propose(ctx['input'],ctx['classification'],policy,regions)
 folder=model.task_dir/('dynamic-preview-pages-'+uuid4().hex);folder.mkdir()
 try:
  result=page_layout.rehearse(ctx['input'],folder/'pages.docx',ctx['classification'],plan,**model._base_rules_arguments())
  if context(model)[1]!=b:raise DemoError('页码预演期间绑定变化')
  record=write_new(folder/'transaction.json',(json.dumps(result,ensure_ascii=False,sort_keys=True)+'\n').encode())
  state.update(context=ctx,binding=b,result=result,directory=str(folder),record_sha256=sha256(record.read_bytes()),result_sha256=fingerprint(result),adopted=None)
  return result
 except Exception:shutil.rmtree(folder,ignore_errors=True);raise

def adopt(model,state):
 if state.get('adopted'):
  if state['adopted_binding']!=context(model)[1]:raise DemoError('采用记录变化')
  model.downloads();return True
 from .dynamic_session import valid
 r=valid(model,state);ctx=state['context'];dest=None;folder=None
 try:
  proof=page_layout.validate_output(ctx['input'],r['output'],ctx['classification'],r['page_layout']['plan'])
  if check_document(r['output'],mode='academic',classification_manifest=r['output_classification_manifest'],**model._base_rules_arguments())!=r['after']:raise DemoError('页码复查不匹配')
  if len(model.history)>=30:raise DemoError('历史轮次达到上限')
  dest=model.task_dir/('pages-fixed-'+uuid4().hex+'.docx');os.link(r['output'],dest);rr=deepcopy(r);rr['output']=str(dest);rr['after']['input']=str(dest.resolve());rr['round_input_path']=ctx['input'];number=model.generation_count+1
  rr['round']={'number':number,'input_round':ctx['parent'],'input_sha256':ctx['sha256'],'original_sha256':sha256(model.original_bytes),'rules_version':rr['after']['rules']['version'],'rules_sha256':model.rules_hash}
  rr['page_layout']['adoption']={'fix_calls':0,'validation':proof,'current_input_auto_switched':False}
  folder=model.task_dir/('round-records-pages-'+uuid4().hex);folder.mkdir();staged=copy(model);staged.task_dir=folder;staged.history=deepcopy(model.history);staged.center_cache=deepcopy(model.center_cache);staged._archive_round(rr)
  staged._verify_plan_archive(folder,staged.history[-1],rr)
  if context(model)[1]!=state['binding'] or valid(model,state) is None or sha256(dest.read_bytes())!=proof['output_sha256']:raise DemoError('归档期间页码绑定变化')
  entry=deepcopy(staged.history[-1]);entry['stem']=folder.name+'/'+entry['stem'];future={**ctx,'input':str(dest),'sha256':proof['output_sha256'],'classification':rr['output_classification_manifest'],'parent':number,'history':number}
  model.history.append(entry);model.generation_count=number;model.result=rr;model.result_signature=model._signature();state['adopted']=number;state['adopted_binding']=fingerprint(future);return True
 except Exception:
  if dest:dest.unlink(missing_ok=True)
  if folder:shutil.rmtree(folder,ignore_errors=True)
  raise

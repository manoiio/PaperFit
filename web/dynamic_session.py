"""Owned optional dynamic previews. Only explicit adoption publishes one round."""
from copy import deepcopy,copy
from pathlib import Path
from uuid import uuid4
import os,shutil,json
from core.package import Package,DemoError,sha256,write_new
from core import check_document
from core import dynamic
from .scope_session import fingerprint
from .rehearsal_session import execution_hash

def context(model):
    model._current()
    if model.mode!='academic' or not model.classification_confirmed:raise DemoError('动态文本处理须先在单文档扩展模式确认章节与题注分类；不从排列位置猜章号')
    if model.result:
        if not model.downloads():raise DemoError('本轮输出已失效')
        path=Path(model.result['output']);sc=model.result['output_classification_manifest'];parent=model.result['round']['number']
    else:path=model.input_path;sc=model.classification_confirmed;parent=model.current_round
    value={'input':str(path),'sha256':sha256(path.read_bytes()),'classification':deepcopy(sc),'parent':parent,
           'current_scope':model._scope_snapshot(),'selected':model.selected,'rules':model.rules_hash,'history':model.generation_count,'execution':execution_hash()}
    return value,fingerprint(value)

def preview(model,state,*,complete=False):
    ctx,b=context(model)
    cancel(model,state)
    plan=dynamic.propose(ctx['input'],ctx['classification'],complete=complete)
    folder=model.task_dir/('dynamic-preview-'+uuid4().hex);folder.mkdir()
    try:
        result=dynamic.rehearse(ctx['input'],folder/'dynamic.docx',ctx['classification'],plan,**model._base_rules_arguments())
        if context(model)[1]!=b:raise DemoError('动态预演期间绑定变化')
        record=write_new(folder/'transaction.json',(json.dumps(result,ensure_ascii=False,sort_keys=True)+'\n').encode())
        state.update(context=ctx,binding=b,result=result,directory=str(folder),record_sha256=sha256(record.read_bytes()),result_sha256=fingerprint(result),adopted=None)
        return result
    except Exception:shutil.rmtree(folder,ignore_errors=True);raise

def cancel(model,state):
    folder=Path(state['directory']) if state.get('directory') else None
    if folder and model.task_dir and folder.parent==model.task_dir and folder.name.startswith('dynamic-preview-') and not folder.is_symlink():shutil.rmtree(folder,ignore_errors=True)
    state.clear()

def valid(model,state):
    if not state.get('result'):raise DemoError('尚未生成动态预演')
    if context(model)[1]!=state['binding']:raise DemoError('动态目标、输入、范围或规则已变化，请重新预演')
    result=state['result'];path=Path(result['output'])
    if path.is_symlink() or not path.is_file() or sha256(path.read_bytes())!=result['after']['input_sha256']:raise DemoError('动态预演副本缺失或字节变化')
    if fingerprint(result)!=state['result_sha256'] or sha256((Path(state['directory'])/'transaction.json').read_bytes())!=state['record_sha256']:raise DemoError('动态预演记录被修改')
    return result

def adopt(model,state):
    if state.get('adopted'):
        if state['adopted_binding']!=context(model)[1]:raise DemoError('采用记录不再适用')
        model.downloads();return True
    result=valid(model,state);ctx=state['context'];before_binding=state['binding'];folder=None;dest=None
    if len(model.history)>=30:raise DemoError('历史轮次已达上限')
    try:
        proof=dynamic.validate_output(ctx['input'],result['output'],result['dynamic']['plan'],ctx['classification'])
        if check_document(ctx['input'],mode='academic',classification_manifest=ctx['classification'],**model._base_rules_arguments())!=result['before']:raise DemoError('动态处理前报告不匹配')
        if check_document(result['output'],mode='academic',classification_manifest=result['output_classification_manifest'],**model._base_rules_arguments())!=result['after']:raise DemoError('动态处理后报告不匹配')
        dest=model.task_dir/('dynamic-fixed-'+uuid4().hex+'.docx');os.link(result['output'],dest)
        rr=deepcopy(result);rr['output']=str(dest);rr['after']['input']=str(dest.resolve());rr['round_input_path']=ctx['input']
        number=model.generation_count+1
        rr['round']={'number':number,'input_round':ctx['parent'],'input_sha256':ctx['sha256'],'original_sha256':sha256(model.original_bytes),'rules_version':rr['after']['rules']['version'],'rules_sha256':model.rules_hash}
        rr['dynamic']['adoption']={'fix_calls':0,'validation':proof,'current_input_auto_switched':False}
        folder=model.task_dir/('dynamic-records-'+uuid4().hex);folder.mkdir()
        staged=copy(model);staged.task_dir=folder;staged.history=deepcopy(model.history);staged.center_cache=deepcopy(model.center_cache)
        staged._archive_round(rr)
        staged._verify_plan_archive(folder,staged.history[-1],rr)
        if context(model)[1]!=before_binding or valid(model,state) is None:raise DemoError('动态归档期间绑定变化')
        if sha256(dest.read_bytes())!=proof['output_sha256']:raise DemoError('正式动态副本变化')
        entry=deepcopy(staged.history[-1]);entry['stem']=folder.name+'/'+entry['stem']
        future={**ctx,'input':str(dest),'sha256':rr['after']['input_sha256'],'classification':rr['output_classification_manifest'],'parent':number,'history':number}
        future_binding=fingerprint(future)
        # All fallible IO/guards precede publication.
        model.history.append(entry);model.generation_count=number;model.result=rr;model.result_signature=model._signature()
        state['adopted']=number;state['adopted_binding']=future_binding
        return True
    except Exception:
        if dest:dest.unlink(missing_ok=True)
        if folder:shutil.rmtree(folder,ignore_errors=True)
        raise

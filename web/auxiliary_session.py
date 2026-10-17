"""Finite safe-layout-v1 command adapter over the original independent transactions.
No AI, rendering, new engine, relaxed mask or text-based identity mapping.
"""
from copy import deepcopy,copy
from collections import Counter
from pathlib import Path
from uuid import uuid4
import json,os,shutil,time
from core.package import Package,DemoError,sha256,write_new,q
from .dynamic_session import context,valid,cancel
from .scope_session import fingerprint


def enabled(policy):return bool(policy and policy.get('version')==3 and policy.get('auxiliaries')=='safe-layout-v1')


def protected_paragraphs(pkg,m):
 out=set(m.get('material_exclusions',{}))
 out.update(k[2:] for k in m.get('front_scope',{}).get('objects',{}) if k.startswith('p:'))
 if m.get('toc_scope'):
  from core.toc import nodes
  ns=nodes(pkg)
  for k in m['toc_scope']['objects']:
   obj=ns[int(k[2:])-1]
   if obj in pkg.paragraphs:out.add(str(pkg.paragraphs.index(obj)+1))
 return out


def classification(ctx):
 """Fresh ordinary adjacent evidence only; explicit prior scope/exclusions win."""
 from core import captions
 from core.classification import validate_classification
 pkg=Package(ctx['input']);m=deepcopy(ctx['classification']);protected=protected_paragraphs(pkg,m)
 if m.get('caption_scope'):return m
 s=captions.make_scope(pkg)
 # Existing inactive/unconfirmed manual drafts are not a fresh automatic grant.
 # They still belong to the original input, so never copy stale paragraph IDs.
 if ctx.get('current_scope',{}).get('caption_draft') is not None:
  s.update(confirmed=True,confirmation='已有题注草稿/关闭决定保持；本次不补造自动关联')
  m['caption_scope']=s;return validate_classification(pkg,m)
 inv=captions.inventory(pkg,m)
 for r in inv['captions']:
  n=str(r['paragraph'])
  if n in protected or not r['parsed'] or not r['parsed']['title'] or r['fields']:continue
  if len(r['nearby'])==1:
   oid=r['nearby'][0]
   if oid.startswith('image:p:') and oid[8:] in protected:continue
   if oid.startswith('table:') and m.get('table_scope',{}).get('table_types',{}).get(oid[6:])!='content':continue
   s['captions'][n]='normal';s['associations'][n]=oid
 s.update(confirmed=True,confirmation='本次新版完整方案授权：仅严格解析题注及XML唯一紧邻对象；未声明范围完整')
 m['caption_scope']=s
 return validate_classification(pkg,m)


def inventory(ctx,kind):
 m=classification(ctx);path=ctx['input'];pkg=Package(path);kept=[];selected=[];protected=protected_paragraphs(pkg,m)
 if kind=='position':
  from core.captions import analyze
  rows=analyze(pkg,m['caption_scope'],m)['positions']
  for r in rows:
   blocked=str(r['paragraph']) in protected or r.get('object','').startswith('image:p:') and r['object'][8:] in protected
   status='selected' if r.get('movable') and not blocked else 'satisfied' if r['status']=='pass' else 'protected'
   if status=='selected':selected.append(r['key'])
   kept.append({'key':r['key'],'status':status,'reason':'人工排除或封面/目录保护保持' if blocked else r['reason']})
  plan={'selected':selected}
 elif kind=='width':
  from core.widths import check_widths
  plan=check_widths(path,rules_sha256=ctx['rules']);scope=m.get('table_scope',{}).get('table_types',{});associated=set(m['caption_scope']['associations'].values())
  from core.captions import position_evidence
  counts=Counter(m['caption_scope']['associations'].values())
  safe_images={oid for n,oid in m['caption_scope']['associations'].items() if counts[oid]==1 and oid.startswith('image:') and oid[8:] not in protected and n not in protected and m['caption_scope']['captions'][n]=='normal' and position_evidence(pkg,int(n),oid,m)['status']=='pass'}
  for r in plan['objects']:
   loc=r['locator'];authorised=scope.get(str(loc.get('table')))=='content' if r['kind']=='table' else 'image:p:'+str(loc.get('paragraph')) in safe_images
   reason=r['reason'];status='protected'
   if not authorised:reason='不属于已确认内容表格或安全关联图片；封面、未知用途、材料保护保持'
   elif r['fixable'] and not r['plan']['autofit_to_fixed']:status='selected';selected.append(r['key'])
   elif r['fixable']:reason='需另行明确授权自动列宽转固定；本版自动方案保持'
   elif r['status']=='pass':status='satisfied'
   kept.append({'key':r['key'],'status':status,'reason':reason,'section':r['section']})
 elif kind=='pagination':
  from core.layout import suggest_pagination_aids,_properties,_flag
  from core.table_edges import tables,header_value,header_plan
  ts=m.get('table_scope');scope=ts.get('table_types',{}) if ts else {}
  # An existing, uniquely interpretable prefix is evidence, never a guessed header.
  if ts:
   opts=ts.setdefault('layout_options',{'version':1,'outer_edges':False,'headers':{}})
   for i,t in enumerate(tables(pkg),1):
    if scope.get(str(i))!='content' or str(i) in opts['headers']:continue
    try:
     flags=[header_value(row) for row in t.findall(q('tr'))];count=next((n for n,v in enumerate(flags) if not v),len(flags))
     if count and count<len(flags) and not any(flags[count:]):header_plan(pkg,t,count);opts['headers'][str(i)]=count
    except Exception as exc:
     from core.formats import Unresolved
     if not isinstance(exc,(Unresolved,DemoError)):raise
     kept.append({'key':'L04:'+str(i),'status':'protected','reason':str(exc)})
   m=__import__('core.classification',fromlist=['validate_classification']).validate_classification(pkg,m)
  plan=suggest_pagination_aids(path,m);assoc=m['caption_scope']['associations'];counts=Counter(assoc.values())
  for r in plan['pairs']:
   ident=r.get('id','L01');reason=r['reason'];authorised=True
   if ident=='L01':authorised=m['caption_scope']['captions'].get(str(r.get('caption_paragraph')))=='normal' and counts[assoc.get(str(r.get('caption_paragraph'))) ]==1 and str(r['image_paragraph']) not in protected and str(r.get('caption_paragraph')) not in protected and assoc.get(str(r.get('caption_paragraph')))=='image:p:'+str(r['image_paragraph'])
   if ident=='L02':authorised=m['caption_scope']['captions'].get(str(r['paragraph']))=='normal' and counts[assoc.get(str(r['paragraph']))]==1 and scope.get(str(r.get('table_position')))=='content' and assoc.get(str(r['paragraph']))=='table:'+str(r.get('table_position'))
   status='protected'
   if not authorised:reason='关联或内容表格用途未确认；不借相似文字扩大范围'
   elif r['status']=='available':
    props=_properties(r);done=all(header_value(tables(pkg)[p['table']-1].findall(q('tr'))[p['row']-1]) if 'table' in p else _flag(pkg,pkg.paragraphs[p['paragraph']-1],p['tag']) for p in props)
    status='satisfied' if done else 'selected'
    if not done:selected.append(r['key'])
   kept.append({'key':r['key'],'status':status,'reason':reason})
  # Make absent header evidence visible without inventing a first row.
  for i,role in scope.items():
   if role=='content' and i not in ts.get('layout_options',{}).get('headers',{}):kept.append({'key':'L04:'+i,'status':'protected','reason':'没有已确认或现存明确连续表头依据；未猜测表头行数'})
 else:raise DemoError('未知辅助阶段')
 return m,plan,selected,kept


def rehearse(model,state,kind):
 ctx,b=context(model);cancel(model,state);start=time.monotonic();m,plan,keys,rows=inventory(ctx,kind)
 state['summary']={'stage':kind,'input_sha256':ctx['sha256'],'objects':rows,'selected_count':len(keys),'status':'not_applicable' if not rows else 'ready' if keys else 'unchanged','seconds':round(time.monotonic()-start,4)}
 if not keys:return None
 folder=model.task_dir/('dynamic-preview-aux-'+uuid4().hex);folder.mkdir()
 try:
  args=dict(mode='academic',classification_manifest=m,**model._base_rules_arguments())
  if kind=='position':
   from core.caption_move import apply_caption_positions
   r=apply_caption_positions(ctx['input'],folder/'aux.docx',confirmed_keys=keys,**args)
  elif kind=='width':
   from core.widths import apply_width_adaptation
   r=apply_width_adaptation(ctx['input'],folder/'aux.docx',plan=plan,selected_keys=keys,confirmed_fixed_keys=(),**args)
  else:
   from core.layout import apply_pagination_layout
   r=apply_pagination_layout(ctx['input'],folder/'aux.docx',confirmed_keys=keys,**args)
  if context(model)[1]!=b:raise DemoError('辅助预演期间绑定变化')
  rec=write_new(folder/'transaction.json',(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n').encode())
  state.update(context=ctx,binding=b,result=r,directory=str(folder),record_sha256=sha256(rec.read_bytes()),result_sha256=fingerprint(r),adopted=None,classification=m)
  state['summary'].update(status='verified',changes=len(r['changes']),output_sha256=r['after']['input_sha256'],seconds=round(time.monotonic()-start,4))
  return r
 except Exception:shutil.rmtree(folder,ignore_errors=True);raise


def adopt(model,state):
 """Adopt exactly the verified bytes via the established staged archive contract."""
 if state.get('adopted'):
  if context(model)[1]!=state['adopted_binding']:raise DemoError('辅助采用绑定变化')
  model.downloads();return True
 from core import check_document
 r=valid(model,state);ctx=state['context'];dest=folder=None
 try:
  if len(model.history)>=30:raise DemoError('历史轮次已达上限')
  if check_document(ctx['input'],mode='academic',classification_manifest=state['classification'],**model._base_rules_arguments())!=r['before']:raise DemoError('辅助父文件复查不匹配')
  if check_document(r['output'],mode='academic',classification_manifest=r['output_classification_manifest'],**model._base_rules_arguments())!=r['after']:raise DemoError('辅助输出复查不匹配')
  if not all(v is True for k,v in r['preservation'].items() if k.endswith('_equal') or k in ('original_sha256_unchanged','only_authorized_caption_permutation','all_object_subtrees_equal')):raise DemoError('辅助完整性证明未通过')
  dest=model.task_dir/('aux-fixed-'+uuid4().hex+'.docx');os.link(r['output'],dest);rr=deepcopy(r);rr['input_classification_manifest']=deepcopy(state['classification']);rr['output']=str(dest);rr['after']['input']=str(dest.resolve());rr['round_input_path']=ctx['input'];number=model.generation_count+1
  rr['round']={'number':number,'input_round':ctx['parent'],'input_sha256':ctx['sha256'],'original_sha256':sha256(model.original_bytes),'rules_version':rr['after']['rules']['version'],'rules_sha256':model.rules_hash}
  rr['auxiliary']={'summary':deepcopy(state['summary']),'adoption':{'fix_calls':0,'input_auto_switched':False},'authorisation':'safe-layout-v1本次明确命令；非旧逐项勾选'}
  folder=model.task_dir/('round-records-aux-'+uuid4().hex);folder.mkdir();staged=copy(model);staged.task_dir=folder;staged.history=deepcopy(model.history);staged.center_cache=deepcopy(model.center_cache);staged._archive_round(rr);staged._verify_plan_archive(folder,staged.history[-1],rr)
  if context(model)[1]!=state['binding'] or valid(model,state) is None or sha256(dest.read_bytes())!=r['after']['input_sha256']:raise DemoError('辅助归档期间绑定变化')
  entry=deepcopy(staged.history[-1]);entry['stem']=folder.name+'/'+entry['stem'];future={**ctx,'input':str(dest),'sha256':rr['after']['input_sha256'],'classification':rr['output_classification_manifest'],'parent':number,'history':number}
  model.history.append(entry);model.generation_count=number;model.result=rr;model.result_signature=model._signature();state.update(adopted=number,adopted_binding=fingerprint(future));return True
 except Exception:
  if dest:dest.unlink(missing_ok=True)
  if folder:shutil.rmtree(folder,ignore_errors=True)
  raise


def execute(model,state,kind,emit):
 emit({'position':'纠正安全题注位置','width':'适配最终节内宽度','pagination':'设置相邻属性与可靠表头'}[kind]);st={}
 try:
  r=rehearse(model,st,kind);summary=deepcopy(st['summary'])
  if r:
   adopt(model,st)
   if kind=='position' and state.get('page_regions'):
    mapping=r['range_mapping']['paragraphs']
    for region in state['page_regions']:region['start']=int(mapping[str(region['start'])])
    from core.page_layout import regions_validate
    regions_validate(Package(model.result['output']),state['page_regions'])
  state['audit'].setdefault('auxiliaries',[]).append(summary)
  return r
 finally:cancel(model,st)

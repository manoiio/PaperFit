"""Finite ordinary -> numeric -> section-page sequence; all steps use real transactions."""
from copy import deepcopy
from pathlib import Path
from core.package import Package,DemoError,sha256
from core.page_policy import validate as validate_policy
from core.page_layout import automatic

def policy_for(model):
 draft=getattr(model,'page_layout_draft',None)
 if draft and draft.get('enabled'):return validate_policy(draft['policy'])
 if draft and draft.get('explicit') and not draft.get('enabled'):return None
 return deepcopy(model.current_rule_bundle().get('assembly'))

def regions_from(stage,types,policy,**kwargs):
 pkg=Package(stage.input_path);rows=automatic(pkg,{'paragraph_types':types},policy,**kwargs)
 if policy.get('version')==2:
  allowed=set(policy['targets'])
  for row in rows:
   if row['role'] not in allowed:row['role']='keep'
  # Do not introduce a redundant split between consecutive unmodified prefixes.
  rows=[r for i,r in enumerate(rows) if not (i and r['role']=='keep' and rows[i-1]['role']=='keep')]
 return rows

def prepare(stage,state,proposal):
 p=state.get('assembly')
 if not p or p['pages']=='keep':return []
 types=proposal['draft']['paragraph_types'];pkg=Package(stage.input_path);draft=getattr(stage,'page_layout_draft',None) or {}
 if draft.get('regions'):
  from core.page_layout import regions_validate
  if draft.get('input_sha256')!=pkg.hash:raise DemoError('本地分区起点绑定旧文件，请重新核对')
  state['page_regions']=regions_validate(pkg,draft['regions']);return page_probe(pkg,state)
 front=[int(n) for n,t in types.items() if t in ('abstract_cn_title','abstract_cn_body','abstract_en_title','abstract_en_body')]+[m['paragraph'] for m in proposal.get('structure',{}).get('markers',[]) if m['role']=='toc'];heads=([proposal['structure']['body_start']] if proposal['structure'].get('body_start') else []) if 'structure' in proposal else [int(n) for n,t in types.items() if t=='heading1'];options={str(i):''.join(x.xpath('.//w:t/text()',namespaces=__import__('core.package',fromlist=['NS']).NS))[:65] for i,x in enumerate(pkg.paragraphs,1)}
 questions=[]
 if not heads:
  protected=set(stage.material_exclusions)
  for scope in (stage.front_draft if stage.front_enabled else None,stage.toc_draft if stage.toc_enabled else None):protected.update(k[2:] for k in (scope or {}).get('objects',{}) if k.startswith('p:'))
  safe={str(r['index']):options[str(r['index'])] for r in stage.suggestions['paragraphs'] if not r['special'] and r['text'].strip() and str(r['index']) not in protected}
  questions.append({'id':'page_body','text':'尚无足够证据确定正文开始位置。','question':'正文从哪个一级章标题开始？选中文字将确认为一级章标题，同时用于分类、页码与章节页脚。' if p['footer']=='chapter' else '正文从哪一段开始？此决定同时更新正文分类和页码分区。','options':{**safe,'skip':'本次保持原有页码'},'title_choices':list(safe) if p['footer']=='chapter' else []})
 body=min(heads) if heads else None
 if p['pages']=='front-body':
  targets=set(p.get('targets',('cover','front','body')))
  relevant_front=[n for n in front if body is None or n<body]
  if 'front' in targets and ((body is None and not relevant_front) or (body and body>1 and not relevant_front)):
   choices={k:v for k,v in options.items() if body is None or int(k)<=body}
   questions.append({'id':'page_front','text':'未能确定摘要/目录等前置部分的起点；可选正文起点表示没有单独前置区。','question':'前置部分从哪一段开始？','options':choices|{'skip':'本次保持原有页码'}})
  earliest=min(relevant_front,default=body)
  if 'cover' in targets and not cover_known(stage,pkg) and (earliest is None or earliest>1):questions.append({'id':'page_cover','text':'前置部分之前的内容尚未确定用途，不能凭顺序当作封面。','question':'前置部分之前是否全部属于不显示页码的封面？','options':{'cover':'是，整个封面区域不显示页码','keep':'不确定，保持这部分原有页码'}})
 if not questions:state['page_regions']=regions_from(stage,types,p,body_start=body,front_start=min((n for n in front if body and n<body),default=body),cover=cover_known(stage,pkg))
 for question in questions:
  if question['id'] in ('page_body','page_front'):
   plausible=[n for n,t in types.items() if t.startswith('heading') or t.endswith('_title') or (len(options.get(n,''))<=45 and options.get(n,'').strip())]
   question['visible_options']=[n for n in question['options'] if n in plausible][:12]+(['skip'] if 'skip' in question['options'] else [])
 if not questions:questions+=page_probe(pkg,state)
 if state['audit'].get('body_start_unspecified'):
  questions.append({'id':'page_number_start','text':'要求明确重新编号，但没有写正文起始值；不会替您填写1。','question':'正文页码从哪里开始？','options':{'1':'正文从1开始；后续按本次连续/重启要求','keep':'保持正文页码及页脚；仅处理其他明确区段','edit':'修改要求，填写其他起始值'}})
 if state['audit'].get('continuity_restart_conflict'):
  questions.append({'id':'page_continuity','text':'原文后续节存在重启值；仅换章名页脚不能保证页码接续。','question':'如何处理后续章节的现有重启？','options':{'1':'正文从1开始，后续连续；其他区段保持','keep':'本次保持页码，仅处理已授权章节页脚','edit':'修改要求，明确正文起始值'}})
 return questions

def cover_known(stage,pkg):
 return (stage.front_draft or {}).get('section_roles',{}).get('1')=='cover' or bool(__import__('re').match(r'^封面(?:\s|[—－:：-]|$)',page_layout_text(pkg.paragraphs[0]).strip()))

def page_probe(pkg,state):
 from core.page_layout import build
 try:
  if state['audit'].get('page_alignment_only'):
   from core.front import section_inventory
   from core.package import parse,NS,q
   for section in section_inventory(pkg):
    if not section['paragraphs']:raise DemoError('页脚所属段落范围不明确，不能仅调整对齐')
    start=min(section['paragraphs']);active=max((r for r in state['page_regions'] if r['start']<=start),key=lambda r:r['start'])
    if active['role']!='body':continue
    variants=['default']+(['first'] if section['first_page_different'] else [])+(['even'] if section['odd_even_different'] else [])
    for variant in variants:
     part=section['references']['footer:'+variant].get('part');root=parse(pkg.parts[part]) if part else None
     fields=[] if root is None else root.xpath('.//w:fldSimple',namespaces=NS)
     if len(fields)!=1 or fields[0].get(q('instr'),'').strip()!='PAGE' or fields[0].xpath('.//w:t',namespaces=NS):raise DemoError('仅要求页脚对齐，不能补造PAGE或清除已有缓存；请明确页码方案，或保持该辅助')
  build(pkg,state['page_regions'])
 except DemoError as exc:
  state['audit']['page_structure_blocker']=str(exc)
  return [{'id':'page_conflict','text':str(exc),'question':'页码结构不能安全自动处理，是否保留原有页码并继续其他安全整理？','options':{'keep':'保持原有页码，继续其他安全处理','edit':'返回调整文件或方案'}}]
 return []

def page_layout_text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=__import__('core.package',fromlist=['NS']).NS))

def continue_regions(stage,state,decisions):
 if not state.get('assembly') or state['assembly']['pages']=='keep':return
 if decisions.get('page_number_start')=='keep':
  state['assembly'].update(version=2,targets=[x for x in state['assembly'].get('targets',('cover','front','body')) if x!='body'])
 if decisions.get('page_number_start')=='1':state['assembly']['body_start']=1
 if decisions.get('page_continuity')=='1':state['assembly'].update(version=2,targets=['body'],pages='front-body',body_start=1,chapter_restart=False)
 if any(k in decisions for k in ('page_number_start','page_continuity')):state.pop('page_regions',None)
 if decisions.get('page_conflict')=='keep':
  state['assembly']['pages']='keep';state['audit']['page_skipped']=state['audit'].get('page_structure_blocker','用户明确保持原页码');return
 if any(decisions.get(k)=='skip' for k in ('page_front','page_body')):
  state['assembly']['pages']='keep';state['audit']['page_skipped']='用户明确保持原有页码';return
 if 'page_body' in decisions:
  from .structure_session import coordinate
  coordinate(stage,state['proposal'],body_start=int(decisions['page_body']),confirmed=bool(state['audit'].get('prior_classification_preserved')))
  state['audit']['explicit_body_boundary_reanalysis']=int(decisions['page_body'])
 if 'page_front' in decisions or 'page_body' in decisions or not state.get('page_regions'):
  state['page_regions']=regions_from(stage,state['proposal']['draft']['paragraph_types'],state['assembly'],front_start=int(decisions['page_front']) if 'page_front' in decisions else None,body_start=int(decisions['page_body']) if 'page_body' in decisions else state['proposal'].get('structure',{}).get('body_start'),cover=decisions.get('page_cover')=='cover' or cover_known(stage,Package(stage.input_path)))
 if decisions.get('page_cover')=='keep':state['page_regions'][0]['role']='keep'


def execute(stage,state,emit):
 p=state.get('assembly')
 if not p:return
 history=state['history_length'];steps=[]
 for h in stage.history[history:]:
  r=h['result'];steps.append({'kind':'format','round':r['round']['number'],'input_sha256':r['round']['input_sha256'],'output_sha256':r['after']['input_sha256'],'changes':len(r['changes'])})
 if p['dynamic']:
  emit('同步安全题注编号与文本引用')
  from core import dynamic
  from .dynamic_session import context,preview,adopt
  ctx,_=context(stage);plan=dynamic.propose(ctx['input'],ctx['classification'],automatic=True)
  state['audit']['dynamic_scope_proof']=deepcopy(plan.get('automatic_scope'))
  state['audit']['dynamic_blocked_groups']=deepcopy(plan['blocked_groups'])
  if plan['edits']:
   st={};preview(stage,st,automatic=True);adopt(stage,st)
   from .dynamic_session import cancel
   cancel(stage,st);r=stage.result;steps.append({'kind':'dynamic_text','round':r['round']['number'],'input_sha256':r['round']['input_sha256'],'output_sha256':r['after']['input_sha256'],'changes':len(r['changes'])})
 if p['pages']!='keep':
  emit('安排分节与页码')
  from .dynamic_session import context
  from .page_session import preview,adopt
  ctx,_=context(stage);regions=state.get('page_regions')
  if not regions:raise DemoError('分区起点尚未核对')
  st={};r=preview(stage,st,p,regions)
  if r['changes'] or r['before']['input_sha256']!=r['after']['input_sha256']:
   adopt(stage,st)
   from .dynamic_session import cancel
   cancel(stage,st);r=stage.result;steps.append({'kind':'section_pages','round':r['round']['number'],'input_sha256':r['round']['input_sha256'],'output_sha256':r['after']['input_sha256'],'changes':len(r['changes'])})
  else:
   from .dynamic_session import cancel
   cancel(stage,st)
 if steps:
  for a,b in zip(steps,steps[1:]):
   if a['output_sha256']!=b['input_sha256']:raise DemoError('完整整理阶段父子关系错误')
  state['audit']['assembly_steps']=steps
  stage.result['assembly']={'policy':deepcopy(p),'steps':steps,'total_changes':sum(s['changes'] for s in steps),'input_auto_switched':False,'fields_evaluated':False,'structure_evidence':deepcopy(state['audit'].get('structure'))}
  # Additive metadata is archived separately for readable export/history; DOCX never rewritten.
  state['outcome_changes']=sum(s['changes'] for s in steps)
  stage.history[-1]['saved_record']={'format':stage.result['after']['summary'],'preservation':stage.result.get('preservation'),'assembly':deepcopy(stage.result['assembly']),'page_layout':deepcopy(stage.result.get('page_layout'))}

def execute_local(model,state,*,acknowledged=False,emit=None):
 """Local orchestration only: no AI runner, settings lookup or onepass network branch."""
 from .smart_session import isolated,binding,suggest,accept_scope,execute as formats
 from .scope_session import fingerprint
 emit=emit or (lambda _:None)
 if acknowledged is not True:raise DemoError('请明确授权当前方案与范围')
 if state.get('post')==binding(model) and state.get('done'):
  if model.result:model.downloads()
  return state
 if not model.classification_confirmed:raise DemoError('请先在范围页确认当前分类')
 initial=binding(model);stage=isolated(model);p=policy_for(stage)
 if not p:raise DemoError('未选择完整整理方案')
 from core import rule_bundle as rb,load_rules
 prior=deepcopy(stage.paragraph_types);bundle=stage.current_rule_bundle();bundle['assembly']=deepcopy(p);stage._save_custom(rb.validate(bundle,load_rules(stage.rules_path)));stage.sync_rules();proposal=suggest(stage);proposal['draft']['paragraph_types']=prior
 from .onepass_session import seal_proposal
 from .structure_session import coordinate
 coordinate(stage,proposal,confirmed=True)
 seal_proposal(stage,proposal)
 own={'assembly':p,'history_length':len(stage.history),'audit':{}}
 questions=prepare(stage,own,proposal)
 if questions:raise DemoError('分区起点不明确，请在本页保存明确分区草稿')
 try:
  plan=accept_scope(stage,proposal,confirmation_text='本地完整方案按钮授权；仅当前明确范围')
  formats(stage,plan,{})
  execute(stage,own,emit)
  if binding(model)!=initial:raise DemoError('本地完整整理期间输入或方案变化')
  if stage.result:stage.downloads()
  jobs=model.preview_jobs;model.__dict__.update({k:v for k,v in stage.__dict__.items() if k!='preview_jobs'});model.preview_jobs=jobs
  state.update(done=True,post=binding(model),audit=own['audit']);return state
 except Exception:
  from .onepass_session import clean_stage
  clean_stage(model,{'stage':stage,'history_length':len(model.history),'original_rule_path':model.custom_rules_path});raise

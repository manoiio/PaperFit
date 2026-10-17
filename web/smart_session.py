"""Explicit shortcut commands over the original scope, rehearsal and adoption APIs.

Suggestions are never confirmations. No API, renderer or autonomous follow-up.
"""
from copy import copy,deepcopy
from pathlib import Path
from core.package import Package,DemoError,sha256
from core.backmatter import material_hint
from .scope_session import ATTRS,fingerprint
from .rehearsal_session import execution_hash

VERSION='smart-format-v1'

def isolated(model):
    stage=copy(model)
    for k,v in model.__dict__.items():
        if k not in ('preview_jobs',):setattr(stage,k,deepcopy(v))
    stage.preview_jobs={};stage.rehearsal=None
    return stage

def binding(model,*,rounds=None):
    model._current()
    return fingerprint({'scope':model._scope_snapshot(),'confirmations':{k:getattr(model,k) for k in ATTRS},
                        'assembly_draft':getattr(model,'page_layout_draft',None),'report':model.report,'selection':model.selected,'history':model._history_binding(),
                        'module_decisions':__import__('web.auto_ranges',fromlist=['decisions']).decisions(model),'rounds':model.generation_count if rounds is None else rounds,'execution':execution_hash(),'version':VERSION})

def suggest(model):
    """Prepare an immutable, conservative projection; never publish any range."""
    start=binding(model);types=deepcopy(model.paragraph_types);excluded=[]
    confirmed=bool(model.classification_confirmed)
    for row in model.suggestions['paragraphs']:
        n=str(row['index']);original=row['suggested_type']
        if n in model.material_exclusions:types[n]='other'
        elif not confirmed and types[n]==original and (row['ambiguous'] or material_hint(row['text'])):
            types[n]='pending'
        if types[n] in ('pending','other'):
            excluded.append({'paragraph':int(n),'type':types[n],'reason':model.material_exclusions.get(n) or ('原材料线索提示疑似代码/数据，暂不自动纳入；可在详细范围核对' if material_hint(row['text']) else row['reason'])})
    body=deepcopy(model.body) if model.mode=='basic' and model.body else sorted(int(n) for n,t in types.items() if t=='body')
    draft={'body':body,'paragraph_types':types}
    stage=isolated(model)
    for k,v in draft.items():setattr(stage,k,deepcopy(v))
    # Existing optional drafts and all exclusions remain untouched. No optional
    # declaration is upgraded to complete, no table is guessed to be content.
    pre=stage.scope_preflight()
    out={'version':VERSION,'source_binding':start,'draft':draft,'preflight':pre,'excluded':excluded,
         'rules':{'name':pre.get('summary',{}).get('rules_name'),'sha256':model.rules_hash},
         'limits':['范围建议由本地结构证据产生；接受摘要才经原接口确认。',
                   '表格、封面、目录、引文、注释等沿用已准备范围；未准备的可选模块不自动开启。',
                   '歧义、代码/数据保护及未配置属性不自动处理；页面检查仍覆盖实际分节。',
                   '本次本地范围建议未调用AI；可选结构识别需明确发送有限摘录，规范解析另行操作。']}
    out['seal']=fingerprint(out)
    if binding(model)!=start:raise DemoError('分析期间输入、规则或范围变化，请重新准备摘要')
    return out

def accept_scope(model,proposal,*,confirmation_text=None):
    frozen={k:v for k,v in proposal.items() if k!='seal'}
    if fingerprint(frozen)!=proposal['seal'] or binding(model)!=proposal['source_binding']:raise DemoError('范围摘要已变化或失效，请重新分析')
    stage=isolated(model)
    for k,v in proposal['draft'].items():setattr(stage,k,deepcopy(v))
    pre=stage.scope_preflight()
    if not pre['ready']:raise DemoError('范围仍有阻止项：'+'；'.join(r['reason'] for r in pre['blockers']))
    if not stage.confirm_scopes_and_check(pre['signature'],acknowledged=True,confirmation_text=confirmation_text):raise DemoError(stage.error)
    if binding(model)!=proposal['source_binding']:raise DemoError('确认检查期间绑定变化，未发布检查')
    model.cancel_rehearsal()
    for k in set(ATTRS+['paragraph_types','report','report_revision','selected','result','result_signature','readonly_cache','error']+list(proposal['draft'])):setattr(model,k,getattr(stage,k))
    return shortcut_plan(model)

def shortcut_plan(model):
    model._current()
    if not model.report:raise DemoError('请先接受范围摘要并检查')
    included=[f for f in model.eligible() if f['rule_id'].startswith('R') and f['rule_id'] not in ('R35',)]
    stage=isolated(model);stage.selected=sorted(f['key'] for f in included)
    plan=stage.correction_plan() if included else None
    data={'version':VERSION,'binding':binding(model),'keys':stage.selected,'items':deepcopy(included),'plan':plan,
          'excluded':[{'key':f['key'],'rule_id':f['rule_id'],'reason':f['detail']} for f in model.report['findings'] if f['status'] in ('problem','review') and f not in included],
          'excluded_operations':['对象移动','宽度适配','分页/重复表头辅助','边框辅助','动态编号及域更新']}
    data['seal']=fingerprint(data);return data

def execute(model,plan,state):
    """One explicit button authorizes only the displayed bound set. Adoption refixes 0 times."""
    if state.get('completed') and state.get('binding')==binding(model):
        if model.result:model.downloads()
        return state['completed']
    if plan['seal']!=fingerprint({k:v for k,v in plan.items() if k!='seal'}) or plan['binding']!=binding(model):raise DemoError('快捷方案已失效，请重新检查摘要')
    if not plan['keys']:
        state.update(binding=binding(model),completed={'status':'no_changes','rounds':0,'message':'本次确认范围没有可安全修正项；未生成无意义副本。'})
        return state['completed']
    if plan['plan']['blocked']:raise DemoError('方案存在不兼容项，请进入详细操作核对')
    model.set_selection(plan['keys'])
    if not model.rehearse_plan():raise DemoError(model.rehearsal_error)
    view=model.rehearsal_view()
    if not view:raise DemoError('预演验证失败，未发布正式结果')
    # The original rehearsal binding revalidates every byte, rule, range and key.
    future=binding(model,rounds=model.generation_count+view.get('expected_adopted_rounds',1))
    if not model.adopt_rehearsal(view['id'],acknowledged=True):raise DemoError(model.rehearsal_error)
    outcome={'status':'adopted','rounds':view.get('expected_adopted_rounds',1),'selected':len(plan['keys']),
             'changes':sum(len(s['changes']) for s in view['steps']) if 'steps' in view else len(view['changes']),'output_sha256':model.result['after']['input_sha256'],
             'fix_calls_at_adoption':0,'summary':deepcopy(model.result['after']['summary'])}
    state.update(binding=future,completed=outcome)
    return outcome

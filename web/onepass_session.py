"""One bounded user command, isolated original transactions, no new DOCX engine.
Only the start/continue handlers execute; rendering never advances this state.
"""
from copy import deepcopy
from pathlib import Path
import re,shutil,time
from uuid import uuid4
from core.package import DemoError,sha256
from core.classification import TYPES,title_number
from core.spec_validation import validate_text,validate_draft
from .scope_session import fingerprint
from .smart_session import binding,isolated,suggest,accept_scope,execute
from . import structure_session as structure

VERSION='onepass-3'


def command_binding(model,extra):
    return fingerprint({'source':binding(model),'extra':extra,'version':VERSION})


def current(model,state,extra):
    try:return state.get('post' if state.get('status')=='done' else 'start')==command_binding(model,extra)
    except Exception:return False


def clean_stage(model,state):
    stage=state.get('stage')
    if not stage:return
    stage.cancel_rehearsal()
    # Only paths issued by this isolated command, never enumerate task directories.
    for h in stage.history[state.get('history_length',len(stage.history)):]:
        parent=Path(h['stem']).parts[0]
        if parent.startswith('round-records-'):
            folder=stage.task_dir/parent
            if folder.parent==stage.task_dir and not folder.is_symlink():shutil.rmtree(folder,ignore_errors=True)
        output=Path(h['result']['output'])
        if output.parent==stage.task_dir and output.name.startswith('fixed-'):output.unlink(missing_ok=True)
    path=stage.custom_rules_path
    if path and path!=state.get('original_rule_path') and path.parent==stage.task_dir and path.name.startswith('user-rules-'):path.unlink(missing_ok=True)


def cancel(model,state):
    if state.get('status')!='done':clean_stage(model,state)
    state.clear();state['status']='cancelled'


def supplement_supported(text):
    from ai.smart_spec import coverage
    return coverage(text)


def overlay(stage,text,result):
    """Native workbench validation/compilation, only explicitly touched fields."""
    from core import rule_bundle as rb,load_rules
    from core.norms import qualify_segments,selected_segments
    from ai.smart_spec import VERSION as SPEC_VERSION,validate
    draft=result['draft'];plain=selected_segments(text)
    if set(draft)=={'font_size','line_spacing','unsupported'}:
        # Compatibility for the old two-field injected caller; no broadening.
        old=validate_draft(draft,text);fields={}
        if old['unsupported']:raise DemoError('补充要求含不支持内容，尚未采用')
        for n in ('font_size','line_spacing'):
            if old[n] is not None:
                location=next((s['location'] for s in plain if old[n]['quote'] in s['text']),None)
                fields[n]={'value':old[n]['value'],'unit':rb.FIELDS['main'][n][2],'quote':old[n]['quote'],'location':location,'support':'supported'}
        draft={'version':SPEC_VERSION,'fields':fields,'issues':[]}
    draft=validate(draft,text);touched=[n for n,f in draft['fields'].items() if f is not None]
    if stage.mode!='academic' and any(n.startswith(('body__','table_content__')) for n in touched) or stage.mode=='basic' and any(n.startswith(('heading','figure_caption','table_caption')) for n in touched):raise DemoError('当前检查方式不支持本次对象要求；未改变已有模式，请在本地工作台核对。')
    base=load_rules(stage.rules_path);prior=stage.current_rule_bundle();mods=deepcopy(prior['modules']);ss=deepcopy(prior['provenance'])
    values=rb.flat('main',mods['main']);segments=deepcopy(prior['excerpt']);new=qualify_segments(plain);locations={s['location']:n['location'] for s,n in zip(plain,new)}
    for x in new:
        if x not in segments:segments.append(x)
    applied=[]
    for n in touched:
        f=draft['fields'][n];values[n]=deepcopy(f['value']);ss['main'][n]={'kind':'ai_extracted','quote':f['quote'],'location':locations[f['location']]}
        applied.append({'field':n,'object_property':rb.FIELDS['main'][n][1],'value':deepcopy(f['value']),'unit':f['unit'],'quote':f['quote'],'location':locations[f['location']]})
    receipt={k:result['receipt'][k] for k in ('kind','model','timestamp_utc')}
    mods['main']=rb.make_main('本次补充排版要求',values,ss['main'],segments,receipt,base)
    bundle=rb.build('本次补充排版要求',mods,segments,receipt,base,ss,prior.get('notices'));rb.compile_bundle(bundle,base)
    stage._save_custom(bundle);stage.sync_rules()
    if stage.rules_hash is None:raise DemoError('补充规则未通过原配置验证')
    return {'fields':touched,'overrides':applied,'receipt':{k:v for k,v in result['receipt'].items() if k!='input_text'},'source_sha256':sha256(text.encode())}


def structure_questions(stage,proposal,result=None):
    """No guessing unnumbered heading levels; numbering/outline/style evidence first."""
    types=proposal['draft']['paragraph_types'];byid={str(r['index']):r for r in stage.suggestions['paragraphs']};asks=[]
    protected=set(stage.material_exclusions)
    ai_ids={r['id'].split(':')[1] for r in proposal.get('structure_ai',{}).get('rows',[]) if r['accepted'] and r['id'].startswith('p:')}
    if stage.classification_confirmed or stage.mode=='basic':return asks
    for n,t in list(types.items()):
        row=byid[n]
        # A plain assignment with code operators is not silently treated as prose.
        # Human-confirmed scopes remain authoritative; no new formatting rule.
        if stage.paragraph_types[n]==row['suggested_type'] and re.match(r'^\s*[A-Za-z_]\w*\s*=\s*',row['text']) and re.search(r'[\[\]();#]',row['text']):
            types[n]='pending';continue
        weak_short=(t=='body' and n in ai_ids and len(row['text'])<=32 and not re.search(r'[。！？；;!?]',row['text']) and not re.match(r'^\s*\d',row['text']) and int(n)<len(byid) and len(byid[str(int(n)+1)]['text'])>20)
        if (not t.startswith('heading') and not weak_short) or n in protected:continue
        row=byid[n]
        if stage.paragraph_types[n]!=row['suggested_type']:continue  # human draft remains authoritative
        level=title_number(row['text'])
        reliable=row.get('outline_level')
        styled=row.get('style_id') in ('Heading1','Heading2','Heading3') and reliable==int(row['style_id'][-1])-1
        levels=set(([level] if level else [])+([reliable+1] if type(reliable) is int and 0<=reliable<=2 else []))
        if len(levels)==1:
            types[n]='heading'+str(next(iter(levels)));continue
        # This is an actual proposed title, not every unclassified paragraph.
        before=[(m,k) for m,k in types.items() if int(m)<int(n) and k.startswith('heading')]
        prior=max(before,key=lambda x:int(x[0])) if before else None
        options={'body':'这是普通正文','pending':'暂不处理这段文字'}
        if prior:
            l=int(prior[1][-1]);options['heading'+str(l)]='与前一标题同级（'+TYPES['heading'+str(l)]+'）'
            if l<3:options['heading'+str(l+1)]='前一标题下面的小标题（'+TYPES['heading'+str(l+1)]+'）'
        for i in range(1,4):options.setdefault('heading'+str(i),TYPES['heading'+str(i)])
        asks.append({'id':'paragraph:'+n,'paragraph':n,'text':row['text'][:140],
                     'context':byid[prior[0]]['text'][:100] if prior else '',
                     'question':'这段文字与前一标题同级，还是它下面的小标题？' if prior else '这段文字是几级标题，还是普通正文？',
                     'options':options,'AI_suggestion':t})
        types[n]='pending'  # never apply an unproved AI guess while waiting
    return asks


def seal_proposal(stage,proposal):
    proposal['draft']['body']=deepcopy(stage.body) if stage.mode=='basic' and stage.body else sorted(int(n) for n,t in proposal['draft']['paragraph_types'].items() if t=='body')
    trial=isolated(stage)
    for k,v in proposal['draft'].items():setattr(trial,k,deepcopy(v))
    proposal['preflight']=trial.scope_preflight();proposal['seal']=fingerprint({k:v for k,v in proposal.items() if k!='seal'})


def pending_seal(state):
    return fingerprint({'start':state['start'],'proposal':state.get('proposal'),'questions':state['questions'],
                        'stage':binding(state['stage']),'version':VERSION})


def start(model,state,extra='',*,structure_runner=None,spec_parser=None,emit=None):
    emit=emit or (lambda name:None)
    if state.get('status')=='done' and current(model,state,extra):
        if model.result:model.downloads()
        return state
    if state.get('status') in ('waiting','failed','running') and current(model,state,extra):return state
    if len(extra)>2000:raise DemoError('补充要求最多2000字')
    cancel(model,state)
    source=command_binding(model,extra);stage=isolated(model);token=uuid4().hex
    prior_types=deepcopy(stage.paragraph_types) if stage.classification_confirmed else None
    state.update(id=token,start=source,extra=extra,stage=stage,status='running',questions=[],history_length=len(model.history),original_rule_path=model.custom_rules_path,
                 audit={'kind':'onepass_command','version':VERSION,'authorization':'点击开始智能排版：按显示规则与明确补充要求，处理可安全识别对象、另存复查；不含动态/移动/宽度/分页辅助',
                        'command_id':token,'source_sha256':model.inventory['input_sha256'],'start_binding':source,'API':{},'phases':[]})
    own={'stage':stage,'history_length':len(model.history),'original_rule_path':model.custom_rules_path}
    def phase(name):
        if state.get('id')!=token:raise DemoError('本次处理已取消')
        state['audit']['phases'].append(name);emit(name)
    try:
        if extra.strip():
            phase('理解排版要求')
            try:
                supplement_supported(extra)
                # Preserve the same effective local note requirements that a
                # no-supplement command would prepare. A rule-only main overlay
                # must not turn implicit current note values into an empty module.
                from .auto_ranges import prepare as prepare_ranges
                initial_ranges=prepare_ranges(stage)
                if initial_ranges.get('notes') is not None:
                    stage.note_enabled=True;stage.note_draft=deepcopy(initial_ranges['notes'])
                    state['audit']['notes_prepared_before_supplement']=deepcopy(initial_ranges['note_counts'])
                from ai.smart_spec import parse_requirements
                # One supplement POST, native field validators, no retry.
                result=(spec_parser or parse_requirements)(extra)
                if state.get('id')!=token:raise DemoError('本次处理已取消')
                state['audit']['API']['requirements']=overlay(stage,extra,result)
            except Exception as exc:
                from .session import public_error
                if state.get('id')!=token:raise DemoError('本次处理已取消')
                clean_stage(model,own);stage=isolated(model);state['stage']=stage;own['stage']=stage
                state['audit']['API']['requirements']={'status':'not_applied','error':public_error(exc),'requests':'未知或未发送；不自动重试'}
                message=public_error(exc)
                if any(w in message for w in ('API','密钥','.env','模型','JSON','连接','超时')):message='这次暂时无法理解补充要求。可以沿用当前排版要求，或修改文字后再试。'
                state['questions'].append({'id':'requirements','text':message,'question':'补充要求尚不能安全执行，您希望怎样继续？',
                                           'options':{'template':'本次沿用页面显示的原有要求','edit':'返回修改补充要求'}})
        phase('识别论文内容');proposal=suggest(stage)
        prepared=structure.prepare(stage,include_tables=True,preserve_paragraphs=prior_types is not None);state['audit']['candidate_count']=len(prepared['request']['candidates'])
        state['audit']['candidate_kinds']={'paragraphs':sum(c.get('kind')!='table' for c in prepared['request']['candidates']),'tables':sum(c.get('kind')=='table' for c in prepared['request']['candidates']),'remaining':prepared['remaining']}
        if prepared['request']['candidates']:
            store={};state['structure_store']=store
            try:
                result=(structure_runner or structure.run)(stage,prepared,store)
                if state.get('id')!=token:raise DemoError('本次处理已取消')
                proposal=structure.merge(stage,prepared,result)
                state['audit']['API']['structure']={'receipt':deepcopy(result['receipt']),'cache_hit':store.get('cache_hit',False),'suggestions':[{k:r[k] for k in ('id','role','accepted','decision_reason')} for r in result['suggestions']]}
            except Exception as exc:
                from .session import public_error
                if state.get('id')!=token:raise DemoError('本次处理已取消')
                state['audit']['structure_fallback']=public_error(exc)
                state['audit']['API']['structure']={'status':'failed','request_attempts':store.get('attempts',0),'elapsed_seconds':store.get('elapsed_seconds')}
        else:state['audit']['structure_local_only']=True
        from .auto_ranges import apply as apply_auto_ranges
        state['questions']+=apply_auto_ranges(stage,proposal,prepared)
        if prior_types is not None:
            proposal['draft']['paragraph_types']=deepcopy(prior_types)
            state['audit']['prior_classification_preserved']=True
        state['audit']['auto_ranges']=deepcopy(proposal.get('auto_ranges'))
        if prior_types is None:state['questions']+=structure_questions(stage,proposal)
        seal_proposal(stage,proposal);state['proposal']=proposal
        if state.get('id')!=token or command_binding(model,extra)!=source:raise DemoError('识别期间文档或要求已变化，本次结果未接入。')
        if state['questions']:
            state['status']='waiting';state['pending_seal']=pending_seal(state);return state
        return finish(model,state,emit=emit,command_id=token)
    except Exception as exc:
        from .session import public_error
        clean_stage(model,own)
        if state.get('id')==token:state.update(status='failed',error=public_error(exc))
        return state


def continue_command(model,state,extra,decisions,*,emit=None):
    if state.get('status')!='waiting' or not current(model,state,extra) or state.get('pending_seal')!=pending_seal(state):raise DemoError('文档、要求或待确认事项已变化，请重新开始。')
    if set(decisions)!={q['id'] for q in state['questions']} or any(decisions[q['id']] not in q['options'] for q in state['questions']):raise DemoError('请决定全部事项，或明确选择暂不处理。')
    if decisions.get('requirements')=='edit':cancel(model,state);return state
    for q in state['questions']:
        if 'paragraph' in q:state['proposal']['draft']['paragraph_types'][q['paragraph']]=decisions[q['id']]
        if 'table' in q:state['proposal']['draft']['table_types'][q['table']]=decisions[q['id']]
    state['audit']['user_decisions']=deepcopy(decisions)
    seal_proposal(state['stage'],state['proposal']);state['status']='running'
    token=state['id'];own={'stage':state['stage'],'history_length':state['history_length'],'original_rule_path':state['original_rule_path']}
    try:return finish(model,state,emit=emit,command_id=token)
    except Exception as exc:
        from .session import public_error
        clean_stage(model,own)
        if state.get('id')==token:state.update(status='failed',error=public_error(exc))
        return state


def finish(model,state,*,emit=None,command_id=None):
    emit=emit or (lambda name:None)
    if state.get('id')!=command_id or not current(model,state,state['extra']):raise DemoError('本次命令绑定已变化，未发布副本。')
    stage=state['stage'];proposal=state['proposal']
    if not proposal['preflight']['ready']:raise DemoError('现有设置仍有冲突：'+'；'.join(r['reason'] for r in proposal['preflight']['blockers']))
    authorization='一站式开始命令授权（可安全识别对象，非旧勾选）：'+command_id+':'+state['start']
    plan=accept_scope(stage,proposal,confirmation_text=authorization)
    state['audit']['plan_sha256']=fingerprint(plan);state['audit']['selected_count']=len(plan['keys'])
    state['audit']['confirmed_scope_sha256']=fingerprint(stage.classification_confirmed or stage.confirmed)
    emit('调整格式');state['audit']['phases'].append('调整格式')
    outcome=execute(stage,plan,{})
    emit('检查修改后的文件');state['audit']['phases'].append('检查修改后的文件')
    if stage.result:stage.downloads()
    state['audit']['processed_scope']={'tables':deepcopy(stage.table_types) if stage.table_enabled else {},'notes':deepcopy(stage.note_draft['objects']) if stage.note_enabled else []}
    post=command_binding(stage,state['extra'])
    if state.get('id')!=command_id or command_binding(model,state['extra'])!=state['start']:raise DemoError('整理期间文档或要求发生变化，未发布本次副本。')
    # All storage, original transactions and final bindings passed. In-memory publish only.
    jobs=model.preview_jobs
    model.__dict__.update({k:v for k,v in stage.__dict__.items() if k!='preview_jobs'})
    model.preview_jobs=jobs
    state.update(status='done',outcome=deepcopy(outcome),post=post)
    state['audit']['outcome']=deepcopy(outcome);state['audit']['automatic_input_switch']=False
    state.pop('stage',None);state.pop('proposal',None);state.pop('structure_store',None)
    return state

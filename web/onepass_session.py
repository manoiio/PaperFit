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

VERSION='onepass-8'


def command_binding(model,extra,requirements=None):
    return fingerprint({'source':binding(model),'extra':extra,'requirements':requirements,'version':VERSION,'field_updates':bool(getattr(model,'field_updates_enabled',False))})


def current(model,state,extra,requirements=None):
    try:return state.get('post' if state.get('status')=='done' else 'start')==command_binding(model,extra,requirements)
    except Exception:return False


def clean_stage(model,state):
    stage=state.get('stage')
    if not stage:return
    stage.cancel_rehearsal()
    # Only paths issued by this isolated command, never enumerate task directories.
    for h in stage.history[state.get('history_length',len(stage.history)):]:
        parent=Path(h['stem']).parts[0]
        if parent.startswith(('round-records-','dynamic-records-')):
            folder=stage.task_dir/parent
            if folder.parent==stage.task_dir and not folder.is_symlink():shutil.rmtree(folder,ignore_errors=True)
        output=Path(h['result']['output'])
        if output.parent==stage.task_dir and output.name.startswith(('fixed-','pages-fixed-','dynamic-fixed-')):output.unlink(missing_ok=True)
    path=stage.custom_rules_path
    if path and path!=state.get('original_rule_path') and path.parent==stage.task_dir and path.name.startswith('user-rules-'):path.unlink(missing_ok=True)


def cancel(model,state):
    if state.get('field_job'):
        from .field_session import cancel as cancel_fields
        cancel_fields(state['field_job'])
    if state.get('status')!='done':clean_stage(model,state)
    state.clear();state['status']='cancelled'


def supplement_supported(text):
    from ai.smart_spec import coverage
    return coverage(text)


def overlay(stage,text,result,*,segments=None,name="本次补充排版要求"):
    """Native workbench validation/compilation, only explicitly touched fields."""
    from core import rule_bundle as rb,load_rules
    from core.norms import qualify_segments,selected_segments
    from ai.smart_spec import VERSION as SPEC_VERSION,validate
    source_segments=segments;draft=result['draft'];plain=deepcopy(segments) if segments is not None else selected_segments(text)
    if set(draft)=={'font_size','line_spacing','unsupported'}:
        # Compatibility for the old two-field injected caller; no broadening.
        old=validate_draft(draft,text);fields={}
        if old['unsupported']:raise DemoError('补充要求含不支持内容，尚未采用')
        for n in ('font_size','line_spacing'):
            if old[n] is not None:
                location=next((s['location'] for s in plain if old[n]['quote'] in s['text']),None)
                fields[n]={'value':old[n]['value'],'unit':rb.FIELDS['main'][n][2],'quote':old[n]['quote'],'location':location,'support':'supported'}
        draft={'version':SPEC_VERSION,'fields':fields,'issues':[]}
    if segments is None:draft=validate(draft,text)
    else:
        if set(draft)!={'version','fields','issues'} or draft['version']!=SPEC_VERSION or draft['issues'] or not set(draft['fields'])<=set(__import__('ai.smart_spec',fromlist=['ALLOWED']).ALLOWED):raise DemoError('文件适配字段结构无效')
        native={m:{'fields':{},'issues':[]} for m in rb.MODULES};
        for n,f in draft['fields'].items():native[__import__('ai.smart_spec',fromlist=['module']).module(n)]['fields'][n]=f
        rb.validate_draft(native,plain)
    touched=[n for n,f in draft['fields'].items() if f is not None]
    if stage.mode!='academic' and any(n.startswith(('body__','table_content__')) for n in touched) or stage.mode=='basic' and any(n.startswith(('heading','figure_caption','table_caption')) for n in touched):raise DemoError('当前检查方式不支持本次对象要求；未改变已有模式，请在本地工作台核对。')
    base=load_rules(stage.rules_path);prior=stage.current_rule_bundle();mods=deepcopy(prior['modules']);ss=deepcopy(prior['provenance'])
    values=rb.flat('main',mods['main']);segments=deepcopy(prior['excerpt']);new=qualify_segments(plain);locations={s['location']:n['location'] for s,n in zip(plain,new)}
    for x in new:
        if x not in segments:segments.append(x)
    applied=[]
    for n in touched:
        f=draft['fields'][n];m=__import__('ai.smart_spec',fromlist=['module']).module(n)
        if m=='main':values[n]=deepcopy(f['value'])
        else:
            from core import notes
            if mods[m] is None:
                mods[m]=notes.promote(notes.school())
                for kind in notes.KINDS:
                    for prop in notes.ALL_FIELDS:mods[m]['values'][kind][prop]=None;mods[m]['sources'][kind][prop]='not_enabled'
            else:mods[m]=notes.promote(mods[m])
            k,p=n.split('__');mods[m]['values'][k][p]=deepcopy(f['value']);mods[m]['sources'][k][p]='user_confirmed'
            if ss[m] is None:ss[m]=rb.origins(m,mods[m])
        ss[m][n]={'kind':'ai_extracted','quote':f['quote'],'location':locations[f['location']]}
        applied.append({'field':n,'object_property':rb.FIELDS[m][n][1],'value':deepcopy(f['value']),'unit':f['unit'],'quote':f['quote'],'location':locations[f['location']]})
    receipt={k:result['receipt'][k] for k in ('kind','model','timestamp_utc')}
    mods['main']=rb.make_main(name,values,ss['main'],segments,receipt,base)
    notices=deepcopy(prior.get('notices',{m:[] for m in rb.MODULES}))
    for note in result.get('notices',[]):
        if note.get('location') in locations and note.get('text'):
            item={'fields':[],'quote':note['text'],'location':locations[note['location']],'reason':'unsupported'}
            if item not in notices['main']:notices['main'].append(item)
    bundle=rb.build(name,mods,segments,receipt,base,ss,notices,assembly=prior.get('assembly'));rb.compile_bundle(bundle,base)
    stage._save_custom(bundle);stage.sync_rules()
    if stage.note_enabled and stage.note_draft and any(__import__('ai.smart_spec',fromlist=['module']).module(n)=='notes' for n in touched):
        note_scope=deepcopy(stage.note_draft);note_scope['template']=deepcopy(mods['notes']);note_scope['confirmed']=False
        __import__('core.notes',fromlist=['validate_scope']).validate_scope(__import__('core.package',fromlist=['Package']).Package(stage.input_path),note_scope,confirmed=False)
        stage.note_draft=note_scope;stage.note_confirmed=None
    if stage.rules_hash is None:raise DemoError('补充规则未通过原配置验证')
    return {'fields':touched,'overrides':applied,'receipt':{k:v for k,v in result['receipt'].items() if k!='input_text'},'source_sha256':sha256(text.encode()) if source_segments is None else result['receipt'].get('file_sha256',sha256(__import__('core.norms',fromlist=['marked_text']).marked_text(plain).encode()))}


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


def start(model,state,extra='',*,requirements=None,requirements_cache=None,file_parser=None,structure_runner=None,spec_parser=None,emit=None):
    emit=emit or (lambda name:None)
    if state.get('status')=='done' and current(model,state,extra,requirements):
        if model.result:model.downloads()
        return state
    if state.get('status') in ('waiting','failed','running') and current(model,state,extra,requirements):return state
    from .requirements_input import verify
    verify(requirements,model)
    if requirements is not None and extra.strip():raise DemoError('文件/已保存要求与文字补充本阶段为二选一')
    if len(extra)>2000:raise DemoError('补充要求最多2000字')
    cancel(model,state)
    source=command_binding(model,extra,requirements);stage=isolated(model);token=uuid4().hex
    prior_types=deepcopy(stage.paragraph_types) if stage.classification_confirmed else None
    state.update(id=token,start=source,extra=extra,requirements=deepcopy(requirements),stage=stage,status='running',questions=[],history_length=len(model.history),original_rule_path=model.custom_rules_path,
                 audit={'kind':'onepass_command','version':VERSION,'authorization':'点击开始智能排版：按显示规则与明确补充要求，处理可安全识别对象、另存复查；不含动态/移动/宽度/分页辅助',
                        'command_id':token,'source_sha256':model.inventory['input_sha256'],'start_binding':source,'API':{},'phases':[]})
    own={'stage':stage,'history_length':len(model.history),'original_rule_path':model.custom_rules_path}
    def phase(name):
        if state.get('id')!=token:raise DemoError('本次处理已取消')
        state['audit']['phases'].append(name);emit(name)
    try:
        if requirements is not None and requirements['kind']=='saved':
            phase('载入已保存的排版要求')
            stage.import_rule_bundle(__import__('core.rule_bundle',fromlist=['raw']).raw(requirements['bundle']))
            stage.apply_workbench(acknowledged=True)  # This start command, not a restored checkbox, authorizes use.
            state['audit']['requirements_source']={'kind':'saved','name':requirements['bundle']['name'],'file_sha256':requirements['file_sha256'],'requests':0}
        file_policy_only=False
        if requirements is not None and requirements['kind']=='file':
            from core.page_policy import extract
            try:
                pp,remaining,_=extract('\n'.join(s['text'] for s in requirements['extraction']['segments']))
                file_policy_only=pp is not None and not remaining.strip()
            except DemoError:pass
        if file_policy_only:
            state['audit']['API']['requirements']={'requests':0,'source':'local_exact_file_strategy','file_sha256':requirements['extraction']['file_sha256']}
            state['audit']['requirements_source']={'kind':'file','name':requirements['name'],'file_sha256':requirements['extraction']['file_sha256']}
            unextracted=requirements['extraction'].get('unextracted',[])
            if unextracted:
                state['audit']['requirements_not_applied']=[{'location':'文件','text':x,'reason':'未提取，不能宣称全部执行'} for x in unextracted]
                state['questions'].append({'id':'requirements_partial','text':'已证明页码/动态策略；文件另有未提取内容。','question':'是否仅处理已证明策略？','options':{'partial':'仅执行已证明策略','template':'仍用当前要求，不采用文件','edit':'返回更换要求文件'}})
        if extra.strip() or requirements is not None and requirements['kind']=='file' and not file_policy_only:
            phase('理解排版要求')
            try:
                if requirements is None:supplement_supported(extra)
                # Preserve the same effective local note requirements that a
                # no-supplement command would prepare. A rule-only main overlay
                # must not turn implicit current note values into an empty module.
                from .auto_ranges import prepare as prepare_ranges
                initial_ranges=prepare_ranges(stage)
                if initial_ranges.get('notes') is not None:
                    stage.note_enabled=True;stage.note_draft=deepcopy(initial_ranges['notes'])
                    state['audit']['notes_prepared_before_supplement']=deepcopy(initial_ranges['note_counts'])
                from ai.semantic_spec import parse_requirements
                # One supplement POST, native field validators, no retry.
                if requirements is None:
                    from core.page_policy import extract
                    _,format_extra,_=extract(extra)
                    result=(spec_parser or parse_requirements)(extra) if format_extra.strip() else None
                    format_extra=extra
                    if result and result.get('page_strategy'):state['semantic_page_strategy']=deepcopy(result['page_strategy'])
                else:
                    from ai.file_spec import parse_requirements as parse_file
                    from ai.short_spec import settings
                    cfg=settings() if file_parser is None else None
                    cache_key=fingerprint({'task':stage.task_dir.name,'mode':stage.mode,'requirements':requirements,'paper':stage.inventory['input_sha256'],'rules':stage.rules_hash,'model':cfg.model if cfg else 'injected','base':cfg.base_url if cfg else 'injected','execution':__import__('web.rehearsal_session',fromlist=['execution_hash']).execution_hash()})
                    if requirements_cache is not None and requirements_cache.get('key')==cache_key:
                        result=deepcopy(requirements_cache['result']);result['receipt'].update(cache_hit=True,request_count=0,source='current_valid_parse_cache')
                    else:
                        result=file_parser(requirements['extraction']) if file_parser else parse_file(requirements['extraction'],config=cfg)
                        if requirements_cache is not None:requirements_cache.update(key=cache_key,result=deepcopy(result))
                if state.get('id')!=token:raise DemoError('本次处理已取消')
                if result and result.get('page_strategy'):state['semantic_page_strategy']=deepcopy(result['page_strategy'])
                if requirements is None:
                    if result is not None:state['audit']['API']['requirements']=overlay(stage,format_extra,result)
                    else:state['audit']['API']['requirements']={'requests':0,'source':'local_exact_strategy'}
                else:
                    state['audit']['API']['requirements']=overlay(stage,'',result,segments=requirements['extraction']['segments'],name=('部分文件要求 · ' if result['notices'] else '文件要求覆盖 · ')+requirements['extraction']['file_sha256'])
                    state['audit']['requirements_source']={'kind':'file','name':requirements['name'],'file_sha256':requirements['extraction']['file_sha256'],'notes':deepcopy(requirements['extraction']['notes'])}
                    state['audit']['requirements_not_applied']=deepcopy(result['notices'])
                    if result['notices']:
                        options={'template':'本次仍用当前要求，不采用文件','edit':'返回更换要求文件'}
                        if result['draft']['fields']:options={'partial':'仅处理列出的已验证要求，其余明确不执行',**options}
                        state['questions'].append({'id':'requirements_partial','text':'可执行 '+str(len(result['draft']['fields']))+' 项要求；另有 '+str(len(result['notices']))+' 项未执行/未提取。','question':'是否仅按已验证的部分处理？请展开下方说明核对。','options':options})

            except Exception as exc:
                from .session import public_error
                if state.get('id')!=token:raise DemoError('本次处理已取消')
                clean_stage(model,own);stage=isolated(model);state['stage']=stage;own['stage']=stage
                state['audit']['API']['requirements']={'status':'not_applied','error':public_error(exc),'requests':'未知或未发送；不自动重试','diagnostics':deepcopy(getattr(exc,'diagnostics',[]))}
                message=public_error(exc)
                if any(w in message for w in ('API','密钥','.env','模型','JSON','连接','超时')):message='这次暂时无法理解补充要求。可以沿用当前排版要求，或修改文字后再试。'
                state['questions'].append({'id':'requirements','text':message,'question':'补充要求尚不能安全执行，您希望怎样继续？',
                                           'options':{'template':'本次沿用页面显示的原有要求','edit':'返回更换要求文件' if requirements is not None else '返回修改补充要求'}})
        from .assembly_session import policy_for
        from core.page_policy import extract as extract_pages
        page_text=extra if requirements is None else '\n'.join(s['text'] for s in requirements['extraction']['segments']) if requirements['kind']=='file' else ''
        try:parsed_policy,_,page_evidence=extract_pages(page_text) if page_text.strip() else (None,'',[])
        except DemoError as exc:
            parsed_policy=None;page_evidence=[]
            state['audit']['page_policy_not_applied']=str(exc)
            if not any(q['id']=='requirements' for q in state['questions']):state['questions'].append({'id':'requirements','text':str(exc),'question':'这些要求尚不能执行，您希望怎样继续？','options':{'template':'本次沿用原有要求','edit':'返回修改要求'}})
        if state.get('semantic_page_strategy'):
            parsed_policy=state['semantic_page_strategy']['policy'];page_evidence=state['semantic_page_strategy']['proof']
        from core.page_policy import merge as merge_policy
        base_policy=policy_for(stage)
        state['assembly']=merge_policy(base_policy,parsed_policy,page_evidence) if parsed_policy else base_policy
        if parsed_policy and not (base_policy and base_policy['pages']=='front-body'):
            stated={k:v for e in page_evidence for k,v in e['values'].items()}
            state['audit']['page_alignment_only']=set(stated)=={'alignment'} and not (base_policy and base_policy['pages']!='keep')
            if stated.get('pages')=='front-body' and 'body' in parsed_policy.get('targets',('cover','front','body')) and 'body_start' not in stated:state['audit']['body_start_unspecified']=True
            if stated.get('chapter_restart') is False and parsed_policy['pages']=='chapter-footers':
                from core.front import section_inventory
                from core.package import Package
                state['audit']['continuity_restart_conflict']=any(s['page_numbering'].get('start') is not None for s in section_inventory(Package(stage.input_path))[1:])
        if state['assembly'] is None and (getattr(stage,'page_layout_draft',None) or {}).get('explicit') and stage.current_rule_bundle().get('assembly'):
            from core import rule_bundle as rb,load_rules
            bundle=stage.current_rule_bundle();bundle.pop('assembly',None);stage._save_custom(rb.validate(bundle,load_rules(stage.rules_path)));stage.sync_rules()
        if state['assembly']:
            old_draft=getattr(stage,'page_layout_draft',None) or {}
            if not old_draft.get('explicit'):stage.page_layout_draft={'explicit':False,'enabled':True,'policy':deepcopy(state['assembly']),'input_sha256':stage.inventory['input_sha256'],'regions':deepcopy(old_draft.get('regions',[]))}
            state['audit']['authorization']='本次开始命令：所列格式、数字、页码及Word安全缓存更新；'+('safe-layout-v1另授权安全题注位置、固定内容表/关联图片缩小、L01–L04；不含自动列宽转固定' if state['assembly'].get('version')==3 else '旧方案不含题注移动、宽度或相邻辅助')
            from core import rule_bundle as rb
            bundle=stage.current_rule_bundle();bundle['assembly']=deepcopy(state['assembly']);stage._save_custom(rb.validate(bundle,__import__('core',fromlist=['load_rules']).load_rules(stage.rules_path)));stage.sync_rules()
            state['audit']['assembly_authorization']={'policy':deepcopy(state['assembly']),'evidence':page_evidence,'source_locations':[{'quote':e['quote'],'locations':[s['location'] for s in requirements['extraction']['segments'] if e['quote'] in s['text']]} for e in page_evidence] if requirements is not None and requirements['kind']=='file' else [],'grant':'本次开始命令授权所列安全事务，不冒充旧勾选'}
        boundaries=[e['boundary'] for e in page_evidence if e.get('boundary')]
        body_intent=None
        for decision in boundaries:
            matches=[r for r in stage.suggestions['paragraphs'] if re.sub(r'\s','',r['text'])==decision['label']]
            if prior_types is not None:
                state['audit'].setdefault('boundary_limits',[]).append('已有人工范围优先，未覆盖前言用途');continue
            if len(matches)!=1 or matches[0]['special'] or str(matches[0]['index']) in stage.material_exclusions:
                state['audit'].setdefault('boundary_limits',[]).append('前言起点不唯一或受保护，未推测位置')
                state['questions'].append({'id':'region_requirement','text':'无法唯一定位要求中的前言，原保护不变。','question':'是否暂不处理这项分区要求，继续其他安全整理？','options':{'skip':'暂不处理该分区要求','edit':'返回调整要求'}});continue
            row=matches[0];n=str(row['index'])
            stage.paragraph_types[n]='heading1' if decision['purpose']=='body' and row.get('style_id')=='Heading1' and row.get('outline_level')==0 else 'body' if decision['purpose']=='body' else 'other'
            if decision['purpose']=='body':body_intent=int(n)
            state['audit'].setdefault('explicit_region_purposes',[]).append({**decision,'paragraph':int(n)})
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
                state['audit']['API']['structure']={'status':'failed','request_attempts':store.get('attempts',0),'elapsed_seconds':store.get('elapsed_seconds'),'diagnostics':deepcopy(store.get('diagnostics',getattr(exc,'diagnostics',[])))}
        else:state['audit']['structure_local_only']=True
        from .auto_ranges import apply as apply_auto_ranges
        state['questions']+=apply_auto_ranges(stage,proposal,prepared)
        if prior_types is not None:
            proposal['draft']['paragraph_types']=deepcopy(prior_types)
            state['audit']['prior_classification_preserved']=True
        state['audit']['auto_ranges']=deepcopy(proposal.get('auto_ranges'))
        if prior_types is None:state['questions']+=structure_questions(stage,proposal)
        from .structure_session import coordinate
        coordinate(stage,proposal,body_start=body_intent,confirmed=prior_types is not None)
        state['audit']['structure']=deepcopy(proposal['structure'])
        from .assembly_session import prepare as prepare_assembly
        state['questions']+=prepare_assembly(stage,state,proposal)
        body_question=next((q for q in state['questions'] if q['id']=='page_body'),None)
        if body_question:
            titles=[q for q in state['questions'] if q.get('paragraph') and 'heading1' in q['options']][:1]
            body_question['title_choices']=list(dict.fromkeys(body_question.get('title_choices',[])+[q['paragraph'] for q in titles]))
            if titles:
                body_question['question']='正文从哪个一级章标题开始？此决定同时用于分类、页码和章节页脚。'
                state['questions']=[q for q in state['questions'] if q not in titles]
        seal_proposal(stage,proposal);state['proposal']=proposal
        if state.get('id')!=token or command_binding(model,extra,requirements)!=source:raise DemoError('识别期间文档或要求已变化，本次结果未接入。')
        if state['questions']:
            state['status']='waiting';state['pending_seal']=pending_seal(state);return state
        return finish(model,state,emit=emit,command_id=token)
    except Exception as exc:
        from .session import public_error
        clean_stage(model,own)
        if state.get('id')==token:state.update(status='failed',error=public_error(exc))
        return state


def continue_command(model,state,extra,decisions,*,requirements=None,emit=None):
    if state.get('status')!='waiting' or not current(model,state,extra,requirements) or state.get('pending_seal')!=pending_seal(state):raise DemoError('文档、要求或待确认事项已变化，请重新开始。')
    if set(decisions)!={q['id'] for q in state['questions']} or any(decisions[q['id']] not in q['options'] for q in state['questions']):raise DemoError('请决定全部事项，或明确选择暂不处理。')
    body=decisions.get('page_body')
    for question in state['questions']:
        if question.get('paragraph')==body and body in next((q.get('title_choices',[]) for q in state['questions'] if q['id']=='page_body'),[]) and decisions[question['id']]!='heading1':raise DemoError('同一文字的正文起点与标题级别选择不一致，请统一后继续')
    front=decisions.get('page_front');known_body=body or state['proposal'].get('structure',{}).get('body_start')
    if front not in (None,'skip') and known_body not in (None,'skip') and int(front)>int(known_body):raise DemoError('前置起点不能晚于正文起点；尚未改变您的方案，请重新选择')
    if decisions.get('requirements')=='edit' or decisions.get('requirements_partial')=='edit' or decisions.get('page_conflict')=='edit' or decisions.get('region_requirement')=='edit' or decisions.get('page_number_start')=='edit' or decisions.get('page_continuity')=='edit':cancel(model,state);return state
    if decisions.get('requirements_partial')=='template':
        old=state['stage'];clean_stage(model,state);stage=isolated(model)
        # Same unmodified DOCX and exact accepted structural draft; only the
        # explicit rule decision changes. Revalidate/reseal with original APIs.
        if old.inventory['input_sha256']!=stage.inventory['input_sha256']:raise DemoError('输入变化，不能继承范围建议')
        state['stage']=stage;state['proposal']['source_binding']=binding(stage)
        if state['audit'].get('explicit_region_purposes'):
            fresh=suggest(stage)
            from .auto_ranges import apply as apply_ranges
            apply_ranges(stage,fresh,structure.prepare(stage,include_tables=True))
            state['proposal']=fresh
            state['audit']['discarded_region_purposes']=state['audit'].pop('explicit_region_purposes')
            state['audit']['file_boundary_decisions_discarded']=True
        state['audit']['file_requirements_declined']=True
    if decisions.get('requirements')=='template' or decisions.get('requirements_partial')=='template':
        from .assembly_session import policy_for
        state['assembly']=policy_for(model);state.pop('page_regions',None)
    for q in state['questions']:
        if 'paragraph' in q:state['proposal']['draft']['paragraph_types'][q['paragraph']]=decisions[q['id']]
        if 'table' in q:state['proposal']['draft']['table_types'][q['table']]=decisions[q['id']]
    bq=next((q for q in state['questions'] if q['id']=='page_body'),{})
    if decisions.get('page_body') in bq.get('title_choices',[]):state['proposal']['draft']['paragraph_types'][decisions['page_body']]='heading1'
    from .structure_session import coordinate
    coordinate(state['stage'],state['proposal'],body_start=int(decisions['page_body']) if decisions.get('page_body','skip')!='skip' else None,decided=[q['paragraph'] for q in state['questions'] if q.get('paragraph')],confirmed=bool(state['audit'].get('prior_classification_preserved')))
    state['audit']['structure']=deepcopy(state['proposal']['structure'])
    from .assembly_session import continue_regions
    continue_regions(state['stage'],state,decisions)
    if any(k in decisions for k in ('page_number_start','page_continuity')):
        from core import rule_bundle as rb,load_rules
        stage=state['stage'];bundle=stage.current_rule_bundle();bundle['assembly']=deepcopy(state['assembly']);stage._save_custom(rb.validate(bundle,load_rules(stage.rules_path)));stage.sync_rules()
        state['proposal']['source_binding']=binding(stage)
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
    if state.get('id')!=command_id or not current(model,state,state['extra'],state.get('requirements')):raise DemoError('本次命令绑定已变化，未发布副本。')
    stage=state['stage'];proposal=state['proposal']
    if not proposal['preflight']['ready']:raise DemoError('现有设置仍有冲突：'+'；'.join(r['reason'] for r in proposal['preflight']['blockers']))
    authorization='一站式开始命令授权（可安全识别对象，非旧勾选）：'+command_id+':'+state['start']
    plan=accept_scope(stage,proposal,confirmation_text=authorization)
    if any(e.get('format_roles')==['body'] for e in state['audit'].get('assembly_authorization',{}).get('evidence',[])):
        from .smart_session import shortcut_plan
        keys=[f['key'] for f in plan['items'] if f['rule_id'] in ('R03','R04','R05','R06','R07','R13') and proposal['draft']['paragraph_types'].get(str(f['locator'].get('paragraph')))=='body']
        plan=shortcut_plan(stage,allowed_keys=keys);state['audit']['format_roles']=['body']
    state['audit']['plan_sha256']=fingerprint(plan);state['audit']['selected_count']=len(plan['keys'])
    state['audit']['confirmed_scope_sha256']=fingerprint(stage.classification_confirmed or stage.confirmed)
    emit('调整格式');state['audit']['phases'].append('调整格式')
    outcome=execute(stage,plan,{})
    from .assembly_session import execute as execute_assembly
    execute_assembly(stage,state,emit)
    if state.get('outcome_changes') is not None:outcome={**outcome,'changes':state['outcome_changes'],'rounds':len(state['audit'].get('assembly_steps',[]))}
    if state.get('assembly') and getattr(stage,'field_updates_enabled',False) and not any(e.get('format_roles') for e in state['audit'].get('assembly_authorization',{}).get('evidence',[])):
        from .field_session import submit
        job={};state['field_job']=job;state['pending_outcome']=deepcopy(outcome)
        try:
            if submit(stage,job):state['status']='updating';state['audit']['phases'].append('本机Word更新目录和引用');return state
            state['audit']['field_update']={'status':'nothing_supported','kept':job.get('kept',[])}
        except Exception as exc:state['audit']['field_update']={'status':'failed','reason':str(exc),'fallback':'已经验证的普通排版/页码副本'}
    return publish(model,state,outcome,emit,command_id)


def publish(model,state,outcome,emit,command_id):
    stage=state['stage'];emit('检查修改后的文件');state['audit']['phases'].append('检查修改后的文件')
    if stage.result:stage.downloads()
    state['audit']['processed_scope']={'tables':deepcopy(stage.table_types) if stage.table_enabled else {},'notes':deepcopy(stage.note_draft['objects']) if stage.note_enabled else []}
    post=command_binding(stage,state['extra'],state.get('requirements'))
    if state.get('id')!=command_id or command_binding(model,state['extra'],state.get('requirements'))!=state['start']:raise DemoError('整理期间文档或要求发生变化，未发布本次副本。')
    # All storage, original transactions and final bindings passed. In-memory publish only.
    jobs=model.preview_jobs
    model.__dict__.update({k:v for k,v in stage.__dict__.items() if k!='preview_jobs'})
    model.preview_jobs=jobs
    state.update(status='done',outcome=deepcopy(outcome),post=post)
    state['audit']['outcome']=deepcopy(outcome);state['audit']['automatic_input_switch']=False
    state.pop('stage',None);state.pop('proposal',None);state.pop('structure_store',None)
    return state


def poll_fields(model,state):
    """Only completes a job authorised by Start; never invokes AI or fixing again."""
    if state.get('status')!='updating':return state
    from .field_session import receive,adopt,cancel as cancel_fields
    if not current(model,state,state['extra'],state.get('requirements')):
        cancel_fields(state['field_job']);state.update(status='cancelled',error='输入或要求变化，Word任务结果不发布');return state
    stage=state['stage'];job=state['field_job']
    try:
        status=receive(stage,job)
        if status['state'] in ('queued','running'):return state
        if status['state']!='succeeded':raise DemoError(status.get('error','Word任务未完成'))
        previous=(deepcopy(stage.result.get('assembly')) if stage.result else None) or {'policy':deepcopy(state['assembly']),'steps':[],'total_changes':0,'input_auto_switched':False,'fields_evaluated':False}
        adopt(stage,job);proof=stage.result['field_update']['validation'];state['audit']['field_update']={'status':'updated','validation':proof,'counts':{k:sum(r['kind']==k for r in job['plan']['selected']) for k in ('TOC','REF','PAGEREF')},'kept_count':len(job['plan']['kept'])}
        if previous:
            r=stage.result;previous['steps'].append({'kind':'field_update','round':r['round']['number'],'input_sha256':r['round']['input_sha256'],'output_sha256':r['after']['input_sha256'],'changes':len(r['changes'])});previous['fields_evaluated']=True;previous['total_changes']+=len(r['changes']);r['assembly']=previous;stage.history[-1]['saved_record']={'assembly':deepcopy(previous),'field_update':deepcopy(r['field_update'])}
            state['audit']['assembly_steps']=deepcopy(previous['steps']);state['pending_outcome'].update(changes=previous['total_changes'],rounds=len(previous['steps']))
    except Exception as exc:
        state['audit']['field_update']={'status':'failed','reason':str(exc),'fallback':'已经验证的普通排版/页码副本'}
    return publish(model,state,state['pending_outcome'],lambda _:None,state['id'])


def register_dynamic_followup(model,state,expected_post,parent_sha256):
    """Register only a separately authorized, already verified dynamic adoption.

    This does not execute anything or restore the original ordinary-format grant.
    Input/requirements stay bound; a different history/output cannot be attached.
    """
    result=model.result
    if state.get('status')!='done' or state.get('post')!=expected_post or not result or result.get('kind')!='dynamic_text' or result['round']['input_sha256']!=parent_sha256:
        raise DemoError('动态副本与本次智能结果的父子关系不匹配')
    model.downloads()  # Existing adopted-byte/transaction/history validation.
    if result.get('dynamic',{}).get('adoption',{}).get('fix_calls')!=0:raise DemoError('动态结果没有原采用验证记录')
    state['audit']['dynamic_followup']={'round':result['round']['number'],'parent_round':result['round']['input_round'],'parent_sha256':parent_sha256,'output_sha256':result['after']['input_sha256'],'numeric_changes':len(result['changes']),'separately_authorized':True,'fields_refreshed':False,'fix_calls_at_adoption':0}
    state['post']=command_binding(model,state['extra'],state.get('requirements'))

"""Session-local object editing buffers; native field validation and draft semantics only."""
from copy import copy,deepcopy
import streamlit as st
from core import rule_bundle as rb
from core.package import DemoError
from .rule_fields_ui import group,label,spec,value_control,accepts,DECISIONS,friendly_error


def editor_signature(model):
    return rb.digest({'task':model.task_dir.name if model.task_dir else None,'mode':model.mode,'generation':model.workbench['generation'],'rules':model.rules_hash,'draft':model.workbench['draft']})


def save_object_changes(model,module,obj,changes,expected):
    """Stage original per-field operations on an isolated draft, then publish together.

    workbench_edit only changes draft fields and origin (no IO). Never stage apply,
    scope, checks or DOCX work. Other saved fields retain their exact dictionaries.
    """
    if editor_signature(model)!=expected:raise DemoError('草稿已变化，请核对最新对象要求后重新保存')
    stage=copy(model);stage.workbench=deepcopy(model.workbench);errors=[]
    for name,edit in changes.items():
        try:
            if name not in rb.FIELDS.get(module,{}) or group(module,name)!=obj:raise DemoError('不属于当前格式对象')
            stage.workbench_edit(module,name,edit['mode'],deepcopy(edit['value']))
        except Exception as exc:errors.append((label(module,name) if name in rb.FIELDS.get(module,{}) else str(name))+'：'+friendly_error(str(exc)))
    if errors:raise DemoError('本对象未保存，全部改动保持待编辑：'+'；'.join(errors))
    if editor_signature(model)!=expected:raise DemoError('保存期间草稿已变化，未发布任何字段')
    model.workbench['draft']=stage.workbench['draft'];model.workbench['origin']=stage.workbench['origin']


def field_value(field,active,baseline):
    mode=field['mode']
    return active if mode=='keep' else baseline if mode=='imported' else None if mode in ('disabled','choose') else field['candidate']['value'] if mode=='ai' and field['candidate'] else field['value']


def render_object_editor(model,module,obj,visible,g,active,baseline,current,display,origins):
    fs=model.workbench['draft']['fields'][module]
    owned=[n for n in fs if group(module,n)==obj]
    buffer_key='wb-buffer-'+g;dirty_key='wb-unsaved-'+model.task_dir.name+'-'+g if model.task_dir else 'wb-unsaved-no-document-'+g
    buffers=st.session_state.setdefault(buffer_key,{})
    epoch_key='wb-edit-epoch-'+g
    message_key='wb-object-message-'+g+'-'+module+'-'+obj
    def changed():
        st.session_state[dirty_key]=list(buffers)
        st.session_state[epoch_key]=st.session_state.get(epoch_key,0)+1
        st.session_state.pop(message_key,None)
    def keys(n):return 'wb-control-'+g+'-'+module+'-'+n,'wb-edit-mode-'+g+'-'+module+'-'+n
    def capture(n,mode,value=None):
        path=module+'.'+n;f=fs[n]
        if mode==f['mode'] and (mode!='manual' or value==f['value']):buffers.pop(path,None)
        else:buffers[path]={'mode':mode,'value':deepcopy(value)}
        changed()
    def value_changed(n):
        key,mk=keys(n);s=spec(module,n);value=st.session_state.get(key)
        if s['kind']=='spacing':
            unit=st.session_state.get(key+'-unit');value={'value':value,'unit':unit} if value is not None and unit is not None else None
        if s['kind']=='line':
            mode=st.session_state.get(key+'-mode');value={'mode':mode,'value':value} if mode is not None and value is not None else None
        if s['kind']=='indent':
            kind=st.session_state.get(key+'-kind');unit=st.session_state.get(key+'-unit');value={'kind':kind,'unit':unit,'value':value} if kind is not None and unit is not None and value is not None else None
        st.session_state[mk]='manual';capture(n,'manual',value)
    def reset_widgets(mod,n,value,mode):
        key='wb-control-'+g+'-'+mod+'-'+n
        st.session_state['wb-edit-mode-'+g+'-'+mod+'-'+n]=mode
        # Widget cleanup alone can reconnect the previous browser value. Set an
        # explicit (possibly empty) UI value; this does not write a draft field.
        if spec(mod,n)['kind']=='spacing':
            st.session_state[key]=float(value['value']) if value is not None else None
            st.session_state[key+'-unit']=value['unit'] if value is not None else None
        elif spec(mod,n)['kind']=='line':
            from core.paragraph_values import line
            d=line(value) if value is not None else None;st.session_state[key]=float(d['value']) if d else None;st.session_state[key+'-mode']=d['mode'] if d else None
        elif spec(mod,n)['kind']=='indent':
            from core.paragraph_values import indent
            d=indent(value,hanging=True) if value is not None else None;st.session_state[key]=float(d['value']) if d else None;st.session_state[key+'-kind']=d['kind'] if d else None;st.session_state[key+'-unit']=d['unit'] if d else None
        else:st.session_state[key]=float(value) if value is not None and spec(mod,n)['kind']=='number' else value
    def mode_changed(n):
        _,mk=keys(n);mode=st.session_state[mk]
        value=effective(n) if mode=='manual' else None
        capture(n,mode,value)
        reset_widgets(module,n,effective(n),mode)
    def formatted(n,value):
        unit=spec(module,n)['unit']
        return display(value)+("" if isinstance(value,dict) else {'pt':'磅','mm':'毫米','multiple':'倍','chars':'字符'}.get(unit,'') if value is not None else '')
    def editing(n):return buffers.get(module+'.'+n,fs[n])
    def effective(n):
        edit=editing(n)
        return field_value({**fs[n],**edit},active[n],baseline[n])
    def clear(paths):
        d=model.workbench['draft']
        for path in paths:
            mod,n=path.split('.',1);f=d['fields'][mod][n]
            cfg=current['modules'][mod];base=d['baseline']['modules'][mod]
            value=field_value(f,rb.flat(mod,cfg)[n] if cfg else None,rb.flat(mod,base)[n] if base else None)
            reset_widgets(mod,n,value,f['mode']);buffers.pop(path,None)
            st.session_state.pop('wb-object-message-'+g+'-'+mod+'-'+group(mod,n),None)
        changed()
    def save(names):
        changes={n:deepcopy(buffers[module+'.'+n]) for n in names if module+'.'+n in buffers}
        try:
            save_object_changes(model,module,obj,changes,signature)
        except Exception as exc:
            st.session_state[message_key]={'error':friendly_error(str(exc))};return
        for n in changes:buffers.pop(module+'.'+n,None)
        changed()
        st.session_state[message_key]={'saved':obj+'：已将'+str(len(changes))+'项改动保存到草稿，尚未应用整份规则。'}
    signature=editor_signature(model)
    st.session_state[dirty_key]=list(buffers)
    view=st.radio('编辑方式',['集中编辑本对象','高级：单字段编辑'],horizontal=True,key='wb-layout-'+g)
    pending=[n for n in owned if module+'.'+n in buffers]
    with st.container(border=True,key='wb-object-form'):
        st.markdown('**'+obj+' · 要求与本次编辑**')
        st.caption('修改控件值表示手动指定；未触碰字段的采用方式与来源保持。保存对象只进入草稿；整体核对应用后才生效。未保存控件仅留在本会话，项目包只保存已保存草稿。')
        table=[]
        for n in dict.fromkeys(visible+pending):
            f=fs[n];v=field_value(f,active[n],baseline[n])
            table.append({'属性':label(module,n),'当前生效':formatted(n,active[n]),'已保存草稿':'尚未决定' if f['mode']=='choose' else formatted(n,v),'本次未保存':DECISIONS[editing(n)['mode']]+' · '+formatted(n,effective(n)) if n in pending else '—'})
        if table:st.dataframe(table,hide_index=True,width='stretch',height=min(240,36+35*len(table)))
        def control(n):
            key,mk=keys(n)
            if mk not in st.session_state:st.session_state[mk]=editing(n)['mode']
            seed=effective(n)
            # A bad pending unit/value stays editable in the existing widgets.
            # Only corrupt saved values use value_control's read-only error path.
            if module+'.'+n in buffers and seed is not None and not accepts(module,n,seed):seed=None
            value_control(module,n,seed,key,lambda n=n:value_changed(n))
        def decision(n,single=False):
            f=fs[n];_,mk=keys(n)
            modes=list(dict.fromkeys([f['mode'],'manual','keep','disabled']+(['ai'] if f['candidate'] else [])))
            mode=editing(n)['mode']
            if mode not in modes:modes.append(mode)
            st.selectbox('此字段采用方式' if single else label(module,n)+'采用方式',modes,index=modes.index(mode),format_func=DECISIONS.get,key=mk,on_change=lambda n=n:mode_changed(n))
            provenance=current['provenance'][module][n] if current['provenance'][module] else rb.EMPTY
            saved_source=(model.workbench['draft']['baseline']['provenance'][module] or {}).get(n,rb.EMPTY) if f['mode']=='imported' else provenance if f['mode']=='keep' else {'kind':'user_confirmed' if f['mode']=='manual' else 'ai_extracted' if f['mode']=='ai' else 'not_enabled'}
            st.caption('生效：'+origins[provenance['kind']]+' · 草稿：'+('尚未决定' if f['mode']=='choose' else origins[saved_source['kind']])+' · '+DECISIONS[f['mode']])
            if f['candidate']:st.text('候选依据：'+f['candidate']['quote']+' · '+f['candidate']['location'])
        if visible:
            if view=='高级：单字段编辑':
                n=st.selectbox('编辑字段',visible,format_func=lambda n:label(module,n),key='wb-field-'+g+'-'+module+'-'+obj)
                control(n);decision(n,True)
                st.button('保存本字段到草稿',disabled=module+'.'+n not in buffers,on_click=save,args=([n],),key='wb-save-one-'+g+'-'+module+'-'+n)
            else:
                sections=[('字体与文字要求',[n for n in visible if spec(module,n)['unit'] in ('font','pt','bool','bold')]),('段落与间距',[n for n in visible if spec(module,n)['unit'] in ('alignment','multiple','chars','spacing')])]
                used={n for _,ns in sections for n in ns};sections.append(('其他已支持属性',[n for n in visible if n not in used]))
                for title,names in sections:
                    if not names:continue
                    st.markdown('**'+title+'**')
                    for start in range(0,len(names),3):
                        for column,n in zip(st.columns(3),names[start:start+3]):
                            with column:control(n)
                with st.expander('采用方式、来源与候选（逐属性核对）'):
                    for n in visible:decision(n)
            if pending:
                st.write('本次尚未保存 '+str(len(pending))+' 项：'+'；'.join(label(module,n)+' → '+formatted(n,effective(n))+'（'+DECISIONS[editing(n)['mode']]+'）' for n in pending))
            else:st.caption('本对象没有未保存改动；已保存草稿与当前生效要求见上表。')
        else:st.info('此对象没有显示的已配置属性。可勾选上方“编辑未提及或保留字段”，不自动补值。')
        a,b=st.columns(2)
        a.button('保存本对象的'+str(len(pending))+'项改动到草稿',disabled=not pending,on_click=save,args=(owned,),type='primary',key='wb-save-object-'+g+'-'+module+'-'+obj,width='stretch')
        b.button('放弃本对象未保存改动',disabled=not pending,on_click=clear,args=([module+'.'+n for n in pending],),key='wb-discard-object-'+g+'-'+module+'-'+obj,width='stretch')
        message=st.session_state.get(message_key)
        if message:
            if 'error' in message:st.error(message['error'])
            else:st.success(message['saved'])
        with st.expander('本对象完整字段ID与保存记录'):
            st.json({n:fs[n] for n in owned})
    if buffers:
        st.warning('还有未保存的控件编辑：'+'、'.join(friendly_error(x) for x in buffers)+'。请保存或明确放弃后再整体应用。')
        st.button('放弃未保存控件编辑（保留已保存草稿）',on_click=clear,args=(list(buffers),),key='wb-discard-all-'+g)
    return dirty_key,st.session_state.get(epoch_key,0)

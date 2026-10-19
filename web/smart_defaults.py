"""Versioned smart-entry defaults. No engine, implicit confirmations or network.

A blank field in an imported/edited bundle is a decision, never a missing default.
Only pristine built-in rules are supplemented. Existing bundle sources carry the
product decisions on subsequent exports; scope proposals still use ScopeSession.
"""
from copy import deepcopy
from core.package import Package,DemoError,q
from core import load_rules,rule_bundle as rb
VERSION=1
QUOTE='PaperFit项目默认v1：普通图题居中；普通表题居中。不是学校明文要求；其他属性沿用原要求。'
FIELDS={'figure_caption__alignment':'center','table_caption__alignment':'center'}


def requested(model):
    return (getattr(model,'page_layout_draft',None) or {}).get('smart_defaults')==VERSION


def pristine(model):
    return not (model.custom_rules_path or model.active_template or model.workbench.get('active') or model.project_notice or model.history or model.workbench.get('draft'))


def prepare_rules(stage):
    """Called on the command's isolated stage before user supplements, never render."""
    if not requested(stage):return {'version':0,'applied':[],'reason':'沿用旧任务或明确保留的要求'}
    if not pristine(stage):return {'version':VERSION,'applied':[],'reason':'已保存/导入/编辑要求优先；空值及不检查不补写'}
    bundle=stage.current_rule_bundle();base=load_rules(stage.rules_path)
    # Capturing a main-only carrier must not turn the original implicit note/TOC
    # requirements into explicit disabled modules (seed_workbench_module semantics).
    builtin=rb.defaults(base)
    for module in ('front','toc','notes'):
        if bundle['modules'][module] is None:
            bundle['modules'][module]=deepcopy(builtin[module]);bundle['provenance'][module]=rb.origins(module,builtin[module])
    vals=rb.flat('main',bundle['modules']['main']);ss=deepcopy(bundle['provenance']['main'])
    # The source lives in the existing rule package, not a hidden per-file override.
    from core.norms import qualify_segments
    segment=qualify_segments([{'location':'摘录:L1','text':QUOTE}])[0]
    segments=deepcopy(bundle['excerpt'])+[segment];changed=[]
    for field,value in FIELDS.items():
        if vals[field] is not None:continue
        vals[field]=value;ss[field]={'kind':'user_confirmed','quote':QUOTE,'location':segment['location']};changed.append(field)
    if not changed:return {'version':VERSION,'applied':[],'reason':'当前要求已配置'}
    bundle['modules']['main']=rb.make_main('当前要求＋PaperFit项目默认',vals,ss,segments,bundle['extraction'],base)
    bundle['name']='当前要求＋PaperFit项目默认';bundle['excerpt']=segments;bundle['provenance']['main']=ss
    from core.norms import marked_text
    from core.package import sha256
    bundle['excerpt_sha256']=sha256(marked_text(segments).encode())
    # Original import/apply validates every native field and atomically publishes to this stage.
    stage.import_rule_bundle(rb.raw(rb.validate(bundle,base)));stage.apply_workbench(acknowledged=True)
    return {'version':VERSION,'applied':changed,'source':QUOTE}


def prepare_scopes(stage,proposal,*,defaults_applied=False):
    """Read-only structure + existing safe caption association; never full-range claims."""
    if not requested(stage) or stage.project_notice:return
    if stage.mode!='academic':return
    from .smart_session import isolated
    view=isolated(stage)
    for k,v in proposal['draft'].items():setattr(view,k,deepcopy(v))
    pkg=Package(stage.input_path)
    # R35 already has material evidence; only the new complete command, not
    # format-only, old saved rules or explicit table layout decisions, opts in.
    draft=getattr(stage,'page_layout_draft',None) or {}
    sources=stage.current_rule_bundle()['provenance']['main']
    # A later explicit supplement may replace BOTH caption sources. That must
    # not accidentally disable the independently authorized table-edge check.
    # This command-local fact comes only from prepare_rules, not a restored flag.
    new_rules=bool(defaults_applied) or any(s.get('quote')==QUOTE for s in sources.values())
    if new_rules and draft.get('enabled') and draft['policy'].get('version')==3 and stage.table_layout_options is None and view.table_enabled:
        proposal['draft']['table_layout_options']={'version':1,'outer_edges':True,'headers':{}}
        view.table_layout_options=deepcopy(proposal['draft']['table_layout_options'])
    if not stage.reference_enabled and stage.reference_draft is None:
        from core.internal_refs import make_scope
        draft=make_scope(pkg)
        # Only integrity is automatic: enabling link text beyond prior intent is separate.
        proposal['draft'].update(reference_enabled=True,reference_draft=draft)
    if not stage.toc_enabled and stage.toc_draft is None:
        from core import toc
        inv=toc.inventory(pkg);automatic={r['id']:r for r in inv['objects'] if r['automatic']}
        if automatic:
            draft=stage.seed_workbench_module('toc',toc.make_scope(pkg))
            draft['objects']={oid:r['candidate'] if r['candidate'] in ('level1','level2','level3') else 'unknown' for oid,r in automatic.items() if view.paragraph_types.get(str(r['locator'].get('paragraph')),'other') in ('other','pending')}
            if draft['objects']:proposal['draft'].update(toc_enabled=True,toc_draft=draft)
    if not stage.caption_enabled and stage.caption_draft is None:
        from .auxiliary_session import classification
        manifest={'input_sha256':pkg.hash,'paragraph_types':deepcopy(view.paragraph_types),'confirmed':True,'confirmation':'本次开始命令的范围预检投影；尚未发布确认'}
        for area in ('front','toc','citation','note','reference'):
            if getattr(view,area+'_enabled') and getattr(view,area+'_draft'):
                # Use the original isolated preflight's validated confirmation, not a flag assignment.
                getattr(view,'confirm_'+{'front':'front','toc':'toc','citation':'citations','note':'notes','reference':'references'}[area])()
                manifest[area+'_scope']=deepcopy(getattr(view,area+'_confirmed')['scope'])
        if stage.material_exclusions:manifest['material_exclusions']=deepcopy(stage.material_exclusions)
        if proposal['draft'].get('table_enabled',stage.table_enabled):
            view.confirm_tables()
            manifest['table_scope']=deepcopy(view.table_manifest())
        # Association discovery uses original exact adjacency/safety; the final real
        # confirmation is performed only by confirm_scopes_and_check in accept_scope.
        m=classification({'input':stage.input_path,'classification':manifest,'current_scope':stage._scope_snapshot()})
        draft=m['caption_scope'];draft.update(confirmed=False,confirmation='本次智能范围建议；未声明整章完整')
        proposal['draft'].update(caption_enabled=True,caption_draft=draft)


def coverage(report,manifest):
    from .scope_session import report_scope_summary
    rules=report['rules'];rows=report_scope_summary(report,manifest)
    rows['executed_rules']=sorted({f['rule_id'] for f in report['findings'] if f['status']!='not_applicable'})
    rows['unconfigured_properties']=deepcopy(report['coverage'].get('disabled_academic_properties',{}))
    rows['explicitly_not_checked_fields']=deepcopy(report['coverage'].get('explicitly_not_checked_fields',[]))
    rows['meaning']='已启用检查项在确认范围内的结果；不是全文合格。未配置与未覆盖不作为通过。'
    return rows

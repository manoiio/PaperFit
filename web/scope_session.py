"""Read-only scope orchestration. Original validators and confirmation methods remain authoritative.

No cached mutable XML, no document checks or UI calls in preflight. Confirmation
is staged on an isolated view, persisted once, then published as one transaction.
"""
from copy import copy, deepcopy
from itertools import combinations
from pathlib import Path
import json
from uuid import uuid4
from core.package import Package, DemoError, sha256, write_new, q, NS
from core import effective_rules
from core.classification import validate_classification

AREAS = {'paragraph':'段落分类与材料保护','table':'表格用途与辅助配置','front':'封面对象与分节用途',
         'toc':'目录范围与层级','citation':'正文引文','note':'脚注与尾注','caption':'题注、章号与关联'}
METHODS = {'table':'confirm_tables','front':'confirm_front','toc':'confirm_toc',
           'citation':'confirm_citations','note':'confirm_notes','caption':'confirm_captions'}
ATTRS = ['confirmed','classification_confirmed','body','error','table_confirmed'] + [a+'_'+b for a in ('front','toc','citation','note','caption') for b in ('draft','confirmed')]
LIMITS = ['数量按各区域的定位单位分别统计；同一段落可被多个模块引用，不能相加为全文覆盖率。',
          '未发现候选不证明物理上没有对象；文本框、浮动对象、复杂容器和未知结构仍需复核。',
          '实际页码、实际同页与Word显示未由范围确认验证；预览与人工视觉核对另行进行。']

def fingerprint(value):
    return sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())


def _has_values(value):
    """Nested note values and flat supplements share only the configured dimension."""
    return any(_has_values(v) for v in value.values()) if isinstance(value,dict) else value is not None


def report_scope_summary(report, classification=None):
    """Projection only: derive participation from the actual report, never a current UI draft."""
    coverage=report['coverage'];types=coverage.get('paragraph_types',{})
    scopes=classification or coverage
    rows=[{'area':'paragraph','name':AREAS['paragraph'],'unit':'顶层段落',
           'selected':sum(v not in ('pending','other') for v in types.values()) if types else len(coverage['body_paragraphs']),
           'excluded':len(scopes.get('material_exclusions',{})),
           'participates':True,'scope':'已确认范围，待确认和其他不套普通段落规则'}]
    for a in METHODS:
        s=scopes.get(a+'_scope');items=(s or {}).get('objects',{})
        if a=='table':items={n:t for n,t in (s or {}).get('table_types',{}).items() if t=='content'}
        if a=='caption':items={n:t for n,t in (s or {}).get('captions',{}).items() if t not in ('pending','excluded')}
        if a=='citation':items={n:t for n,t in items.items() if t=='citation'}
        rows.append({'area':a,'name':AREAS[a],'unit':{'table':'顶层表格','front':'封面对象（节另计）','toc':'目录段落对象','citation':'字符范围','note':'独立注释对象','caption':'题注段落'}[a],
                     'selected':len(items),'participates':s is not None,
                     'scope':'已确认；未配置属性不检查' if s is not None else '未启用或不在本轮确认范围',
                     'declarations':{k:deepcopy(s[k]) for k in ('complete','headings_complete','references_complete','chapters_complete','covered_levels') if k in s} if s else {}})
    return {'file_sha256':report['input_sha256'],'rules_sha256':report['rules']['sha256'],
            'scope_sha256':fingerprint(classification or coverage),'areas':rows,'limits':deepcopy(LIMITS),
            'coverage_note_count':len(report.get('coverage_notes',[])),
            'unconfirmed_top_level_paragraphs':deepcopy(coverage.get('unconfirmed_paragraphs',[])),
            'review_record_keys':[f['key'] for f in report['findings'] if f['status']=='review'],
            'review_counts':{'rule_records':report['summary']['review_findings'],'coverage_notes':report['summary']['review_notes']},
            'review_explanation':'原始待复核记录全部保留；范围未确认、复杂结构及解析限制仍按原报告分别说明。'}


class ScopeSession:
    def _scope_snapshot(self):
        # Actual bytes, not mtime/TTL. Does not call mutating _current/sync_rules.
        state={k:deepcopy(getattr(self,k)) for k in ('mode','current_round','body','paragraph_types','material_exclusions','table_enabled','table_types','table_layout_options')}
        for a in ('front','toc','citation','note','caption'):
            state[a+'_enabled']=getattr(self,a+'_enabled');state[a+'_draft']=deepcopy(getattr(self,a+'_draft'))
        state['task_id']=self.task_dir.name if self.task_dir else None
        state['display_name']=self.display_name  # hashed locally; never exported in the preflight summary
        state['expected_input_sha256']=(self.inventory or {}).get('input_sha256')
        state['expected_rules_sha256']=self.rules_hash
        state['actual_input_sha256']=sha256(self.input_path.read_bytes()) if self.input_path else None
        state['rule_files']={}
        paths=[self.custom_rules_path or self.rules_path]
        from core.extended import EXTENDED_RULES
        from core.academic_rules import PATH as ACADEMIC
        from core.backmatter import PATH as BACK
        from core.table_text import PATH as TABLE
        if self.mode!='basic':paths.append(EXTENDED_RULES)
        if self.mode=='academic':paths.extend([ACADEMIC,BACK,TABLE])
        for i,p in enumerate(paths):state['rule_files'][str(i)]=sha256(Path(p).read_bytes())
        state['template_sha256']=getattr(self,'active_template_sha256',None) if self.active_template else None
        return state

    def scope_preflight(self):
        """Validate proposed confirmations independently, then all cross-range constraints.

        This method does not prepare/accept suggestions, populate caches, write
        files, check formats, or touch confirmation/report/preview state.
        """
        rows=[];problems=[];warnings=[];staged=None
        def record(area,code,text,level='block'):
            target=problems if level=='block' else warnings
            if not any(x['area']==area and x['code']==code and x['reason']==text for x in target):
                target.append({'area':area,'code':code,'reason':text,'entry':AREAS.get(area,'当前文件与规则')})
        try:
            snapshot=self._scope_snapshot();binding=fingerprint(snapshot)
            pkg=Package(self.input_path)
            if pkg.hash!=snapshot['expected_input_sha256']:record('input','file_changed','输入字节已变化，请重新上传或恢复核对；不能沿用旧定位。')
            cfg=effective_rules(**self._base_rules_arguments(),mode=self.mode)
            if cfg['sha256']!=self.rules_hash:record('rules','rules_changed','规则文件已变化，请重新应用规则并核对范围。')
            if self.active_template and self.custom_rules_path and sha256(self.custom_rules_path.read_bytes())!=self.active_template_sha256:record('rules','template_changed','已确认模板文件字节已变化。')
        except Exception as exc:
            return {'signature':None,'areas':[],'blockers':[{'area':'input','code':'binding_unavailable','reason':str(exc) if isinstance(exc,DemoError) else '输入或规则不可读取，请重新选择。','entry':'当前文件与规则'}], 'warnings':[],'limits':deepcopy(LIMITS),'ready':False,'summary':{}}
        base={'input_sha256':pkg.hash,'paragraph_types':deepcopy(self.paragraph_types),'confirmed':True,'confirmation':'统一范围草稿预检（尚未发布确认）'}
        if self.material_exclusions:base['material_exclusions']=deepcopy(self.material_exclusions)
        paragraph_selected=len(self.body) if self.mode=='basic' else sum(t not in ('other','pending') for t in self.paragraph_types.values())
        paragraph_valid=self.confirmed is not None and self.confirmed.get('input_sha256')==pkg.hash and self.confirmed.get('body_paragraphs')==self.body
        if self.mode!='basic':paragraph_valid=paragraph_valid and bool(self.classification_confirmed) and self.classification_confirmed.get('paragraph_types')==self.paragraph_types and self.classification_confirmed.get('material_exclusions',{})==self.material_exclusions
        rows.append({'area':'paragraph','name':AREAS['paragraph'],'enabled':True,'configured':True,'detected':len(pkg.paragraphs),'unit':'顶层段落',
                     'selected':paragraph_selected,'excluded':len(self.material_exclusions),'pending':sum(t=='pending' for t in self.paragraph_types.values()) if self.mode!='basic' else len(pkg.paragraphs)-len(self.body),
                     'confirmed':paragraph_valid,'declarations':{},'details':{'suggested_ambiguities':sum(bool(r.get('ambiguous')) for r in (self.suggestions or {}).get('paragraphs',[])),'other':sum(t=='other' for t in self.paragraph_types.values()),'protected_paragraphs':sorted(self.material_exclusions,key=int)}})
        if self.mode=='basic':
            if not self.body or any(type(n) is not int or not 1<=n<=len(pkg.paragraphs) for n in self.body) or len(set(self.body))!=len(self.body):record('paragraph','body_invalid','先准备至少一个合法且明确选择的正文段落。')
        else:
            try:validate_classification(pkg,base)
            except DemoError as exc:record('paragraph','classification_invalid',str(exc))
        # Isolated confirmation fields. Original methods can only mutate this view;
        # _current is intentionally disabled here after binding checks above.
        staged=copy(self)
        for key in ATTRS:setattr(staged,key,deepcopy(getattr(self,key)))
        staged._current=lambda:None
        scopes={}
        from core import toc,notes,citations,captions,front,table_text
        inventories={}
        for area in METHODS:
            enabled=self.mode=='academic' and getattr(self,area+'_enabled')
            draft=getattr(self,area+'_draft',None)
            c=getattr(self,area+'_confirmed')
            try:
                if area=='table':
                    ts=table_text.tables(pkg);detected=len(ts);selected=sum(t=='content' for t in self.table_types.values());excluded=sum(t in ('cover','other') for t in self.table_types.values());pending=sum(t=='pending' for t in self.table_types.values());configured=any(v is not None for v in table_text.requirements(cfg)['values'].values()) if self.mode=='academic' else False
                    details={'nested':sum(bool(t.findall('.//'+q('tbl'))) for t in ts),'merged':sum(bool(t.xpath('.//w:gridSpan|.//w:vMerge|.//w:hMerge',namespaces=NS)) for t in ts),'unlisted':len(table_text.unlisted_tables(pkg)),'layout_options':deepcopy(self.table_layout_options)}
                    valid=bool(c) and c['rules_hash']==self.rules_hash and c['policy_hash']==snapshot['rule_files'].get('4') and c['scope'].get('table_types')==self.table_types and c['scope'].get('layout_options')==self.table_layout_options and c['scope']['input_sha256']==pkg.hash
                else:
                    if area=='front':
                        # All supported objects can be manually identified, not all are cover candidates.
                        inv={'objects':list(front.nodes(pkg)),'sections':front.section_inventory(pkg)};detected=len(inv['objects']);details={'sections':len(inv['sections']),'pending_sections':sum(t=='pending' for t in (draft or {}).get('section_roles',{}).values()),'mixed_sections':sum(t=='mixed' for t in (draft or {}).get('section_roles',{}).values())}
                    elif area=='toc':
                        inv=toc.inventory(pkg);detected=sum(bool(r['candidate'] or r['automatic'] or r['broken']) for r in inv['objects']);details={'supported_objects':len(inv['objects']),'unlisted':len(inv['unlisted_structures']),'automatic':sum(r['automatic'] for r in inv['objects'])}
                    elif area=='note':
                        inv=notes.inventory(pkg);detected=len(inv['objects']);details={'system_readonly':len(inv['systems']),'complex':sum(r['complex'] or not r['safe_relationship'] for r in inv['objects']),'relationship_issues':len(inv['issues'])}
                    elif area=='citation':
                        scan=(draft or {}).get('scan',[int(n) for n,t in self.paragraph_types.items() if t=='body'])
                        if any(type(n) is not int or not 1<=n<=len(pkg.paragraphs) for n in scan):raise DemoError('引文扫描段落定位失效')
                        inv=citations.inventory(pkg,scan,draft['template'] if draft else None);detected=len(inv['objects']);details={'scan_paragraphs':deepcopy(scan),'complex':sum(not r['safe_structure'] for r in inv['objects'])}
                    else:
                        inv=captions.inventory(pkg,base);detected=len(inv['captions']);details={'objects':len(inv['objects']),'chapter_map':deepcopy((draft or {}).get('chapter_map',{})),'associations':deepcopy((draft or {}).get('associations',{}))}
                    inventories[area]=inv
                    items=(draft or {}).get('captions' if area=='caption' else 'objects',{})
                    selected=sum(t=='citation' for t in items.values()) if area=='citation' else sum(t not in ('pending','excluded') for t in items.values()) if area=='caption' else len(items)
                    excluded=sum(t=='excluded' for t in items.values()) if area in ('citation','caption') else 0
                    pending=sum(t=='pending' for t in items.values())+max(0,detected-len(items)) if area in ('citation','caption') else sum(t=='unknown' for t in items.values()) + max(0,detected-sum(bool(r['candidate'] or r['automatic'] or r['broken']) for r in inv['objects'] if r['id'] in items)) if area=='toc' else max(0,detected-selected) if area=='note' else details['pending_sections']
                    if draft and area in ('front','toc'):
                        values=draft['template']['values'];configured=any(v is not None for v in values.values())
                    elif draft and area=='note':configured=any(v is not None for obj in draft['template']['values'].values() for v in obj.values())
                    elif draft:configured=any(draft['template'].get(k) is True for k in (('numbering','position') if area=='caption' else ('superscript','correspondence')))
                    else:
                        active=(self.workbench.get('active') or {}).get('modules',{}).get({'note':'notes'}.get(area,area))
                        configured=bool(active and _has_values(active.get('values',{})))
                    valid=bool(c) and c['rules_hash']==self.rules_hash and c['scope']==draft and draft['input_sha256']==pkg.hash
                row={'area':area,'name':AREAS[area],'enabled':enabled,'configured':configured,'detected':detected,'selected':selected,'excluded':excluded,'pending':pending,'confirmed':valid,'unit':{'table':'顶层表格','front':'可定位段落/表格内段落；节另计','toc':'目录线索对象（含内容控件）','citation':'扫描范围内字符区间','note':'普通脚注/尾注（系统对象另计）','caption':'分类中的题注段落'}[area], 'declarations':{k:deepcopy(draft[k]) for k in ('complete','references_complete','headings_complete','chapters_complete','covered_levels') if draft and k in draft},'details':details}
                rows.append(row)
                if enabled:
                    try:
                        getattr(staged,METHODS[area])()
                        scopes[area+'_scope']=deepcopy(getattr(staged,area+'_confirmed')['scope'])
                    except (DemoError,KeyError,TypeError) as exc:record(area,'scope_invalid',str(exc) if isinstance(exc,DemoError) else '范围草稿结构无效，请回到对应区域核对。')
                    if not selected:record(area,'empty_selection','当前没有纳入对象；允许部分检查，不代表已验证不存在。','warning')
                    if not configured:record(area,'not_configured','格式未配置；确认对象不会补默认值或宣称格式通过。','warning')
                    if any(v is False for k,v in row['declarations'].items() if k.endswith('complete')):record(area,'partial_scope','保留当前部分范围声明；不推断整篇缺项或完整序列。','warning')
                else:record(area,'disabled','本轮未启用该区域；仅展示可发现线索，不参与格式判断。','warning')
                if pending:record(area,'pending_objects',f'{pending}个待核对/未纳入线索，不能算通过；各区域口径见清单。','warning')
                if any(details.get(k) for k in ('complex','unlisted','automatic','relationship_issues','nested','merged','mixed_sections')):
                    clues='；'.join(label+str(details[k]) for k,label in [('complex','复杂线索'),('unlisted','清单外对象'),('automatic','自动目录对象'),('relationship_issues','关系提示'),('nested','含嵌套表格'),('merged','含合并表格'),('mixed_sections','混合用途节')] if details.get(k))
                    record(area,'structural_limits',clues+'。这些线索不自动判错；保留原结构保护，具体安全属性及未检查项以实际报告为准。','warning')
            except (DemoError,ValueError,TypeError,KeyError,IndexError,AttributeError) as exc:
                rows[:]=[r for r in rows if r['area']!=area]
                rows.append({'area':area,'name':AREAS[area],'enabled':enabled,'configured':False,'detected':None,'selected':0,'excluded':0,'pending':None,'confirmed':False,'unit':'清单无法可靠读取','declarations':{},'details':{}})
                record(area,'inventory_unavailable',str(exc) if isinstance(exc,DemoError) else '清单或草稿结构不可解释', 'block' if enabled else 'warning')
        if self.mode!='basic':
            if rows[0]['pending']:record('paragraph','pending_classification','待确认段落不套格式；材料排除及其他类型仍保留。','warning')
            if rows[0]['details']['suggested_ambiguities']:record('paragraph','ambiguous_suggestions',str(rows[0]['details']['suggested_ambiguities'])+'个原建议含歧义线索；请核对完整分类，统一确认不会将歧义自动算通过。','warning')
            # Validate independent scopes and interactions separately so one error
            # does not hide unrelated areas. Then validate the complete manifest.
            for size in (1,2):
                for keys in combinations(scopes,size):
                    try:validate_classification(pkg,{**base,**{k:scopes[k] for k in keys}})
                    except DemoError as exc:
                        area=next((a for word,a in [('目录','toc'),('封面','front'),('引文','citation'),('题注','caption')] if word in str(exc)),keys[-1].removesuffix('_scope'));record(area,'cross_scope_conflict',str(exc))
            try:validate_classification(pkg,{**base,**scopes})
            except DemoError as exc:
                if not any(p['reason']==str(exc) for p in problems):record('paragraph','combined_scope_invalid',str(exc))
        for row in rows:
            row['blocked']=any(p['area'] in (row['area'],'input','rules') for p in problems)
            row['status']='未启用' if not row['enabled'] else '阻止检查' if row['blocked'] else '未发现适用对象（仍有边界）' if row['detected']==0 and row['selected']==0 else '格式未配置' if not row['configured'] else '已确认（当前有效）' if row['confirmed'] else '草稿待统一核对'
        summary={'file_sha256':pkg.hash,'round':self.current_round,'mode':self.mode,'rules_name':cfg['name'],'rules_version':cfg['version'],'rules_sha256':cfg['sha256'],'selected_areas':[r['area'] for r in rows if r['enabled']], 'material_exclusions':sorted(self.material_exclusions,key=int),'page_scope':'全部实际分节，沿用原页面检查范围，无新增确认'}
        return {'signature':binding,'areas':rows,'blockers':problems,'warnings':warnings,'limits':deepcopy(LIMITS),'ready':not problems,'summary':summary}

    def scope_draft_rows(self):
        """Exact local locators and roles only, never excerpt or private identity text."""
        rows=[]
        if self.mode=='basic':
            rows.extend({'区域':AREAS['paragraph'],'对象':str(n),'草稿用途':'正文','附加说明':''} for n in self.body)
        else:
            rows.extend({'区域':AREAS['paragraph'],'对象':n,'草稿用途':t,'附加说明':'主动保护材料' if n in self.material_exclusions else ''} for n,t in self.paragraph_types.items())
        for a in METHODS:
            if self.mode!='academic' or not getattr(self,a+'_enabled'):continue
            d=getattr(self,a+'_draft',None) or {}
            items=self.table_types if a=='table' else d.get('captions' if a=='caption' else 'objects',{})
            if isinstance(items,list):items={n:'纳入检查' for n in items}
            rows.extend({'区域':AREAS[a],'对象':str(n),'草稿用途':t,'附加说明':''} for n,t in items.items())
            if a=='citation':rows.append({'区域':AREAS[a],'对象':', '.join(map(str,d.get('scan',[]))),'草稿用途':'引文扫描段落','附加说明':'扫描不等于确认候选用途'})
            if a=='table' and self.table_layout_options:rows.append({'区域':AREAS[a],'对象':'本轮表格辅助配置','草稿用途':json.dumps(self.table_layout_options,ensure_ascii=False),'附加说明':'L04等辅助仍须另行选择和执行'})
            for name in ('section_roles','chapter_map','associations'):
                rows.extend({'区域':AREAS[a],'对象':str(n),'草稿用途':str(t),'附加说明':name} for n,t in d.get(name,{}).items())
        return rows

    def confirm_scopes_and_check(self, signature, *, acknowledged=False):
        """Atomic original confirmations; execute only on this explicitly acknowledged snapshot."""
        if acknowledged is not True:raise DemoError('请先核对完整范围摘要并明确确认。')
        pre=self.scope_preflight()
        if not pre['signature'] or signature!=pre['signature']:raise DemoError('文件、规则或范围草稿已变化，请核对新的摘要；旧勾选不再有效。')
        if not pre['ready']:raise DemoError('预检存在阻止项，请先核对各区域。')
        staged=copy(self)
        for key in ATTRS:setattr(staged,key,deepcopy(getattr(self,key)))
        staged._current=lambda:None
        if self.mode=='academic':
            for area,method in METHODS.items():
                if getattr(self,area+'_enabled'):getattr(staged,method)()
        manifest=None
        if self.mode!='basic':
            manifest=staged._classification_manifest();validate_classification(Package(self.input_path),manifest)
            staged.classification_confirmed=manifest
            staged.body=sorted(int(n) for n,t in self.paragraph_types.items() if t=='body')
            staged.confirmed={'input_sha256':self.inventory['input_sha256'],'body_paragraphs':staged.body.copy(),'confirmation':'网页分类人工确认'}
        else:
            staged.confirmed={'input_sha256':self.inventory['input_sha256'],'body_paragraphs':self.body.copy(),'confirmation':'网页人工确认'}
        saved=None
        # Storage succeeds before any live confirmation field is published.
        if manifest is not None:
            saved=write_new(self.task_dir/('confirmed-types-'+uuid4().hex+'.json'),(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
        try:
            if fingerprint(self._scope_snapshot())!=signature:raise DemoError('确认期间文件、规则或范围变化，请重新核对。')
        except Exception:
            if saved:saved.unlink(missing_ok=True)
            raise
        for key in ATTRS:setattr(self,key,deepcopy(getattr(staged,key)))
        return self.check()

"""Explicit snapshot preparation/staging/adoption; no AI, renderer or mutation calls."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
import json, shutil
from core.package import DemoError, sha256, write_new, Package
from core import inspect_document, check_document, effective_rules, load_custom_rules, suggest_paragraph_types
from core.project import VERSION, MAX_ROUNDS, pack, stage, require, json_bytes, scope
from core.project_editor import KEYS, validate_editor
from .reading_report import clean

def editor(model):
    data={k:deepcopy(getattr(model,k)) for k in KEYS}
    if model.norm_inventory:data['historical_norm_sha256']=model.norm_inventory['file_sha256']
    for name in ('template_touched','draft_edited'):data[name]=sorted(data[name])
    for name in ('template_receipt','ai_receipt'):
        if data[name]:data[name]={k:data[name][k] for k in ('kind','model','timestamp_utc')}
    return validate_editor(data,model.rules_path)

def manifest_scope(model, report=None, file_hash=None):
    cov=report['coverage'] if report else None
    return {'file_sha256':file_hash or model.inventory['input_sha256'],
            'body':deepcopy(cov['body_paragraphs'] if cov else sorted(int(n) for n,t in model.paragraph_types.items() if t=='body') if model.mode!='basic' else model.body),
            'types':deepcopy(cov.get('paragraph_types',model.paragraph_types) if cov else model.paragraph_types),
            'saved_confirmed':True if cov else model.confirmed is not None,
            **({'backmatter_policy_sha256':report['rules']['backmatter_sha256']} if report and report['rules'].get('backmatter_sha256') else {'backmatter_policy_sha256':model.backmatter_binding()[0]} if cov is None and model.backmatter_binding() else {}),
            **({'material_exclusions':deepcopy(cov.get('material_exclusions',{}))} if cov and cov.get('material_exclusions') else {'material_exclusions':deepcopy(model.material_exclusions)} if cov is None and model.material_exclusions else {}),
            **({'caption_scope':deepcopy(cov['caption_scope'])} if cov and cov.get('caption_scope') else {'caption_scope':deepcopy(model.caption_draft)} if cov is None and model.caption_enabled else {}),
            **({'reference_scope':deepcopy(cov['reference_scope'])} if cov and cov.get('reference_scope') else {'reference_scope':deepcopy(model.reference_draft)} if cov is None and model.reference_enabled else {}),
            **({'note_scope':deepcopy(cov['note_scope'])} if cov and cov.get('note_scope') else {'note_scope':deepcopy(model.note_draft)} if cov is None and model.note_enabled else {}),
            **({'citation_scope':deepcopy(cov['citation_scope'])} if cov and cov.get('citation_scope') else {'citation_scope':deepcopy(model.citation_draft)} if cov is None and model.citation_enabled else {}),
            **({'toc_scope':deepcopy(cov['toc_scope'])} if cov and cov.get('toc_scope') else {'toc_scope':deepcopy(model.toc_draft)} if cov is None and model.toc_enabled else {}),
            **({'front_scope':deepcopy(cov['front_scope'])} if cov and cov.get('front_scope') else {'front_scope':deepcopy(model.front_draft)} if cov is None and model.front_enabled else {}),
            **({'table_scope':deepcopy(cov['table_scope'])} if cov and cov.get('table_scope') else {'table_scope':{'input_sha256':file_hash or model.inventory['input_sha256'],'table_types':deepcopy(model.table_types),'confirmed':model.table_confirmed is not None,'confirmation':'保存时表格草稿/确认；恢复须本次核对',**({'layout_options':deepcopy(model.table_layout_options)} if model.table_layout_options else {})}} if cov is None and model.table_enabled else {})}

def rule_args(path,kind,mode,sc):
    return {('custom_rules_path' if kind=='custom' else 'rules_path'):path,'mode':mode,
            **({'classification_manifest':{'input_sha256':sc['file_sha256'],'paragraph_types':sc['types'],'confirmed':True,'confirmation':'本次恢复用户核对',**({'material_exclusions':deepcopy(sc['material_exclusions'])} if sc.get('material_exclusions') else {}),**({'caption_scope':{**deepcopy(sc['caption_scope']),'input_sha256':sc['file_sha256']}} if sc.get('caption_scope') and sc['caption_scope']['confirmed'] else {}),**({'reference_scope':{**deepcopy(sc['reference_scope']),'input_sha256':sc['file_sha256']}} if sc.get('reference_scope') and sc['reference_scope']['confirmed'] else {}),**({'note_scope':{**deepcopy(sc['note_scope']),'input_sha256':sc['file_sha256']}} if sc.get('note_scope') and sc['note_scope']['confirmed'] else {}),**({'citation_scope':{**deepcopy(sc['citation_scope']),'input_sha256':sc['file_sha256']}} if sc.get('citation_scope') and sc['citation_scope']['confirmed'] else {}),**({'toc_scope':{**deepcopy(sc['toc_scope']),'input_sha256':sc['file_sha256']}} if sc.get('toc_scope') and sc['toc_scope']['confirmed'] else {}),**({'front_scope':{**deepcopy(sc['front_scope']),'input_sha256':sc['file_sha256']}} if sc.get('front_scope') and sc['front_scope']['confirmed'] else {}),**({'table_scope':{**sc['table_scope'],'input_sha256':sc['file_sha256']}} if sc.get('table_scope') and sc['table_scope']['confirmed'] else {})}} if mode!='basic' else {})}

class ProjectSession:
    def init_project(self):
        self.project_export=None;self.project_notice=None;self.project_pending=None;self.project_checkpoint=None

    def project_snapshot(self, history_policy='all'):
        self._current()
        require(history_policy in ('all','current'),'保存历史选项无效')
        members={};docs={};rules={}
        def document(path,expected):
            content=Path(path).read_bytes();h=sha256(content)
            require(h==expected,'文件已被外部修改，拒绝旧项目包')
            if h not in docs:
                name=f'documents/{len(docs):04}.docx';members[name]=content;docs[h]={'sha256':h,'member':name}
            return h
        candidates=[(self.rules_path,'default')]
        if self.custom_rules_path:candidates.append((self.custom_rules_path,'custom'))
        for folder in (self.task_dir,self.norm_dir):
            if folder and folder.exists():candidates.extend((p,'custom') for p in folder.glob('user-rules-*.json'))
        def rule(wanted,mode):
            for path,kind in candidates:
                try:
                    if effective_rules(**{('custom_rules_path' if kind=='custom' else 'rules_path'):path},mode=mode)['sha256']!=wanted:continue
                    content=path.read_bytes();h=sha256(content)
                    if h not in rules:
                        name=f'rules/{len(rules):04}.json';members[name]=content;rules[h]={'sha256':h,'member':name,'kind':kind}
                    return h
                except DemoError:continue
            raise DemoError('历史规则文件缺失，不能完整保存；可明确选择只保留原稿和当前输入')
        original=document(self.original_path,sha256(self.original_bytes))
        current=document(self.input_path,self.inventory['input_sha256'])
        checkpoint=self.project_checkpoint or {'round':0,'file':original}
        if history_policy=='current':checkpoint={'round':self.current_round,'file':current}
        elif checkpoint['file']!=original:
            source=next((h['result']['output'] for h in self.history if h['result']['after']['input_sha256']==checkpoint['file']),None)
            if source is None:source=getattr(self,'project_checkpoint_path',None)
            require(source is not None,'历史检查点文件缺失');document(source,checkpoint['file'])
        active=rule(self.rules_hash,self.mode);history=[]
        if history_policy=='all':
            require(len(self.history)<=MAX_ROUNDS,'历史超过30轮，请明确减少历史')
            sources={sha256(self.original_bytes):self.original_path,current:self.input_path}
            if self.project_checkpoint:sources[self.project_checkpoint['file']]=self.project_checkpoint_path
            for h in self.history:sources[h['result']['output_body_manifest']['input_sha256']]=Path(h['result']['output'])
            for h in self.history:
                r=h['result'];before=r['before'];after=r['after'];ih=before['input_sha256'];oh=after['input_sha256']
                require(ih in sources,'历史输入缺失')
                document(sources[ih],ih);document(r['output'],oh)
                # Each archive retains the exact raw rule file, including legacy and imported rules.
                if h.get('project_rules_path'):candidates.insert(0,(Path(h['project_rules_path']),h['project_rules_kind']))
                history.append({'number':r['round']['number'],'parent':r['round']['input_round'],'input':ih,'output':oh,
                                'rule':rule(after['rules']['sha256'],h['binding'][0]),'mode':h['binding'][0],
                                **({'input_scope':manifest_scope(self,before,ih)} if r.get('kind') in ('caption_position','dynamic_text','section_pages','field_update') else {}),
                                'scope':manifest_scope(self,after,oh),'changes':clean(h.get('saved_changes',r['changes'])),
                                'kind':r.get('kind','format'),'saved_summary':clean(h.get('saved_record',{'format':after['summary'],'preservation':r.get('preservation'),
                                        'pagination':r.get('layout'),'width':r.get('widths'),'delta':r.get('problem_delta'),'plan':r.get('plan'),'assembly':r.get('assembly'),'page_layout':r.get('page_layout')}))})
        data={'format':'paper-grid-project','version':VERSION,'saved_at':datetime.now(timezone.utc).isoformat(),
              'display_name':clean(Path(self.display_name.replace('\\','/')).name[:100]) or '文档.docx',
              'documents':list(docs.values()),'rules':list(rules.values()),
              'state':{'original':original,'current':current,'current_round':self.current_round,'generation_count':self.generation_count,
                       'mode':self.mode,'rule':active,'scope':manifest_scope(self),'selected':list(self.selected),'editor':editor(self),
                       'history':history,'history_policy':history_policy,'preview_history':bool(self.preview_cache),'checkpoint':checkpoint}}
        return data,members

    def prepare_project(self,history_policy='all'):
        data,members=self.project_snapshot(history_policy)
        # Save timestamp is not part of cache identity; every explicit/download validation still hashes all files.
        identity=sha256(json_bytes({k:v for k,v in data.items() if k!='saved_at'}))
        if self.project_export and self.project_export['signature']==identity:return self.project_export['bytes']
        raw=pack(data,members)
        self.project_export={'signature':identity,'bytes':raw,'policy':history_policy}
        return raw

    def project_download(self):
        if not self.project_export:return None
        old=self.project_export
        data,_=self.project_snapshot(old['policy'])
        signature=sha256(json_bytes({k:v for k,v in data.items() if k!='saved_at'}))
        if signature!=old['signature']:
            self.project_export=None;return None
        return old['bytes']

    def stage_project(self,raw):
        self.cancel_project_import()
        self.project_pending=stage(raw,self.work_root)
        return self.project_summary()

    def cancel_project_import(self):
        if self.project_pending:
            shutil.rmtree(self.project_pending['directory'],ignore_errors=True)
            self.project_pending=None

    def project_summary(self):
        require(self.project_pending is not None,'尚未校验项目包')
        d=self.project_pending['manifest'];s=d['state']
        require(sha256(self.project_pending['rulepaths'][s['rule']].read_bytes())==s['rule'],'暂存规则文件已变化，请重新导入')
        kind=next(r for r in d['rules'] if r['sha256']==s['rule'])['kind']
        cfg=effective_rules(**{('custom_rules_path' if kind=='custom' else 'rules_path'):self.project_pending['rulepaths'][s['rule']]},mode=s['mode'])
        return {'文件':d['display_name'],'当前输入':'原稿' if not s['current_round'] else f"第{s['current_round']}轮副本",
                '检查模式':{'basic':'基础 R01–R07','extended':'扩展 R01–R12','academic':'单文档 R01–R22（确认表格时增加R23）'}[s['mode']],
                '表格用途草稿':len(s['scope'].get('table_scope',{}).get('table_types',{})),
                '分类段落':len(s['scope']['types']),'正文段落':len(s['scope']['body']),'历史轮数':len(s['history']),
                '范围状态':'保存时已确认，须本次核对' if s['scope']['saved_confirmed'] else '尚未确认的范围草稿',
                '历史保存':'检查点之前历史已明确省略；保留此后所选记录' if s['checkpoint']['round'] else '完整历史' if s['history_policy']=='all' else '已明确省略历史，仅原稿和当前输入',
                '规则':cfg['name'],'规则版本':cfg['version']}

    def project_review(self):
        p=self.project_pending;s=p['manifest']['state'];kind=next(r for r in p['manifest']['rules'] if r['sha256']==s['rule'])['kind']
        require(sha256(p['rulepaths'][s['rule']].read_bytes())==s['rule'] and sha256(p['paths'][s['current']].read_bytes())==s['current'],'暂存文件已变化，请重新导入')
        cfg=effective_rules(**{('custom_rules_path' if kind=='custom' else 'rules_path'):p['rulepaths'][s['rule']]},mode=s['mode'])
        from .issues import value
        rules=[{'规则':rid+' '+r['name'],'要求':value(r['expected'],rid,True)} for rid,r in cfg['rules'].items()]
        inv=inspect_document(p['paths'][s['current']])
        from core.classification import TYPES
        rows=[{'编号':r['index'],'简短文本':r['text'][:48],'类型':TYPES[s['scope']['types'][str(r['index'])]],'正文已选':r['index'] in s['scope']['body']} for r in inv['paragraphs']]
        if s['scope'].get('table_scope'):
            from core.table_text import requirements as table_requirements
            values=table_requirements(cfg)['values']
            rules.append({'规则':'R23 论文内容表格普通文字','要求':'中文字体 '+(values['font_cn'] or '未配置')+'；普通字号 '+(str(values['font_size'])+'pt' if values['font_size'] is not None else '未配置')+'；只执行明确确认的表格，未配置不代表符合'})
            from core.table_text import inventory as table_inventory,TYPES as TABLE_TYPES
            table_scope=s['scope']['table_scope']
            if table_scope.get('layout_options'):rules.append({'规则':'R35/L04表格补充（结构v1）','要求':str(table_scope['layout_options'])+'；恢复后重新检查'})
            for row in rows:row['编号']=str(row['编号'])
            for row in table_inventory(p['paths'][s['current']])['tables']:
                typ=table_scope['table_types'][str(row['index'])]
                rows.append({'编号':'表格'+str(row['index']),'简短文本':row['text'][:48],'类型':TABLE_TYPES[typ],'正文已选':False,'表内检查范围':('保存时已确认' if table_scope['confirmed'] else '未确认草稿')+'；'+('论文内容' if typ=='content' else '不纳入文字检查')})
        if s['scope'].get('caption_scope'):
            cs=s['scope']['caption_scope'];rules.append({'规则':'R42/R43题注补充配置','要求':cs['template']['name']+'；编号只读，L05必须另行授权，恢复实际重新检查'})
            rows += [{'编号':'题注段落'+key,'类型':kind,'简短文本':'按文件哈希和XML对象重绑；当前页码未核对','正文已选':False} for key,kind in cs['captions'].items()]
        if s['scope'].get('reference_scope'):
            rules.append({'规则':'R44产品结构检查','要求':str(s['scope']['reference_scope']['template'])+'；导入后重新核对目标，不恢复跳转或缓存结论'})
        if s['scope'].get('note_scope'):
            ns=s['scope']['note_scope']
            from core.notes import KINDS,FIELDS
            for kind in KINDS:
                for prop in FIELDS:rules.append({'规则':KINDS[kind]+' '+{'font_cn':'中文字体','font_size':'字号pt','line_multiple':'倍数行距'}[prop],'要求':str(ns['template']['values'][kind][prop])+'；来源 '+ns['template']['sources'][kind][prop]+'；恢复后重新检查'})
            for key in ns['objects']:rows.append({'编号':key,'简短文本':'Word注释（导入后本机清单查看）','类型':'脚注/尾注','正文已选':False})
        if s['scope'].get('citation_scope'):
            cs=s['scope']['citation_scope'];rules.append({'规则':'R33/R34引文补充','要求':cs['template']['name']+'；恢复后实际重新检查，历史候选不是本次API'})
            rows += [{'编号':key,'类型':kind,'简短文本':'准确字符范围绑定文档哈希；恢复后重新读取','正文已选':False} for key,kind in cs['objects'].items()]
        if s['scope'].get('toc_scope'):
            toc=s['scope']['toc_scope'];rules.append({'规则':'R30–R32目录补充模板','要求':toc['template']['name']+'；'+json.dumps(toc['template']['values'],ensure_ascii=False)})
            rows += [{'编号':key,'类型':kind,'简短文本':'目录对象恢复后重新读取；保存时实际页码未核对','正文已选':False} for key,kind in toc['objects'].items()]
        if s['scope'].get('front_scope'):
            front=s['scope']['front_scope'];rules.append({'规则':'R24–R29补充模板','要求':front['template']['name']+'；'+json.dumps(front['template']['values'],ensure_ascii=False)})
            rows += [{'编号':key,'类型':kind,'简短文本':'封面定位，恢复后实际重新读取','正文已选':False} for key,kind in front['objects'].items()]
            rows += [{'编号':'节'+n,'类型':role,'简短文本':'节用途（不是物理页码）','正文已选':False} for n,role in front['section_roles'].items()]
        return rules,rows

    def restore_project(self, *, acknowledged=False):
        require(acknowledged is True,'须明确核对恢复摘要；现有工作尚未替换')
        require(self.project_pending is not None,'没有待恢复项目')
        try:return self._restore_project(acknowledged=True)
        except Exception:
            self.cancel_project_import()
            raise

    def _restore_project(self, *, acknowledged=False):
        require(acknowledged is True,'须明确核对恢复摘要；现有工作尚未替换')
        require(self.project_pending is not None,'没有待恢复项目')
        from .session import WebSession
        pending=self.project_pending;data=pending['manifest'];state=data['state'];directory=pending['directory']
        # Revalidate staged bytes immediately before adoption; private paths are issued locally.
        for h,p in {**pending['paths'],**pending['rulepaths']}.items():require(sha256(p.read_bytes())==h,'暂存文件发生变化，恢复被拒绝')
        new=WebSession(self.work_root,self.rules_path);new.task_dir=directory
        new.input_path=pending['paths'][state['current']];new.original_path=pending['paths'][state['original']]
        new.input_bytes=new.input_path.read_bytes();new.original_bytes=new.original_path.read_bytes()
        new.display_name=data['display_name'];new.mode=state['mode']
        kinds={r['sha256']:r['kind'] for r in data['rules']}
        rp=pending['rulepaths'][state['rule']]
        if kinds[state['rule']]=='custom':
            raw=rp.read_bytes();cfg=json.loads(raw);new.custom_rules_path=rp
            new.active_custom_data=deepcopy(cfg)
            if cfg.get('format')=='paper-grid-rule-bundle':new.active_template=deepcopy(cfg['modules']['main']['template']);new.active_template_sha256=sha256(raw)
            elif 'structure_version' in cfg:new.active_template=deepcopy(cfg);new.active_template_sha256=sha256(raw)
        new.sync_rules();require(new.rules_hash is not None,'恢复规则不可用')
        new.inventory=inspect_document(new.input_path);new.suggestions=suggest_paragraph_types(new.input_path,include_sections=new.mode=='academic')
        new.body=list(state['scope']['body']);new.paragraph_types=deepcopy(state['scope']['types'])
        from core.table_text import inventory as ti
        new.table_types={str(t['index']):'pending' for t in ti(new.input_path)['tables']}
        if state['scope'].get('table_scope'):
            new.table_enabled=True;new.table_types=deepcopy(state['scope']['table_scope']['table_types']);new.table_layout_options=deepcopy(state['scope']['table_scope'].get('layout_options'))
        new.material_exclusions=deepcopy(state['scope'].get('material_exclusions',{}))
        if state['scope'].get('caption_scope'):new.adopt_caption_scope(state['scope']['caption_scope'],confirmed=False)
        if state['scope'].get('reference_scope'):new.adopt_reference_scope(state['scope']['reference_scope'],confirmed=False)
        if state['scope'].get('note_scope'):new.adopt_note_scope(state['scope']['note_scope'],confirmed=False)
        if state['scope'].get('citation_scope'):new.adopt_citation_scope(state['scope']['citation_scope'],confirmed=False)
        if state['scope'].get('toc_scope'):new.adopt_toc_scope(state['scope']['toc_scope'],confirmed=False)
        if state['scope'].get('front_scope'):new.adopt_front_scope(state['scope']['front_scope'],confirmed=False)
        new.current_round=state['current_round'];new.generation_count=state['generation_count']
        new.project_checkpoint=deepcopy(state['checkpoint']);new.project_checkpoint_path=pending['paths'][state['checkpoint']['file']]
        for key,value in validate_editor(state['editor'],self.rules_path).items():
            setattr(new,key,set(value) if key in ('template_touched','draft_edited') else deepcopy(value))
        if new.ai_receipt:new.ai_receipt.update(historical_reuse=True,requests_this_action=0)
        if new.template_receipt:new.template_receipt.update(historical_reuse=True)
        new.workbench['origin']='restored';new.workbench['historical']=True
        new.template_generation+=1;new.draft_generation+=1
        new.project_notice='已恢复草稿；历史解析不是本次API调用。保存时预览和视觉结论未恢复为可用验收。'
        for saved in state['history']:
            oh=saved['output'];sc=saved['scope'];p=pending['paths'][oh];rulepath=pending['rulepaths'][saved['rule']]
            # Both reports are freshly read. Historical modification/preservation claims remain unverified.
            args=rule_args(rulepath,kinds[saved['rule']],saved['mode'],sc)
            after=check_document(p,sc['body'],**args)
            inputscope=deepcopy(saved.get('input_scope',{**sc,'file_sha256':saved['input']}))
            before=check_document(pending['paths'][saved['input']],inputscope['body'],**rule_args(rulepath,kinds[saved['rule']],saved['mode'],inputscope))
            from core.dependencies import problem_delta
            r={'before':before,'after':after,'changes':deepcopy(saved['changes']),'skipped_review_keys':[],
               'output':str(p),'output_body_manifest':{'input_sha256':oh,'body_paragraphs':sc['body'],'confirmation':'项目历史范围'},
               'preservation':None,'problem_delta':problem_delta(before,after),
               'round':{'number':saved['number'],'input_round':saved['parent'],'input_sha256':saved['input'],'original_sha256':state['original'],
                        'rules_version':after['rules']['version'],'rules_sha256':after['rules']['sha256']},
               'kind':saved['kind'],'restored_history':True}
            if saved['kind'] in ('caption_position','dynamic_text','section_pages','field_update'):r['input_classification_manifest']=rule_args(rulepath,kinds[saved['rule']],saved['mode'],inputscope)['classification_manifest']
            for change in r['changes']:
                change['verification']='review';change['restoration_note']='保存时修改记录；本次未验证该操作'
            if saved['mode']!='basic':r['output_classification_manifest']={'input_sha256':oh,'paragraph_types':sc['types'],'confirmed':True,'confirmation':'保存时分类（导入校验）',**({'material_exclusions':deepcopy(sc['material_exclusions'])} if sc.get('material_exclusions') else {}),**({'caption_scope':deepcopy(sc['caption_scope'])} if sc.get('caption_scope') and sc['caption_scope']['confirmed'] else {}),**({'reference_scope':deepcopy(sc['reference_scope'])} if sc.get('reference_scope') and sc['reference_scope']['confirmed'] else {}),**({'note_scope':deepcopy(sc['note_scope'])} if sc.get('note_scope') and sc['note_scope']['confirmed'] else {}),**({'citation_scope':deepcopy(sc['citation_scope'])} if sc.get('citation_scope') and sc['citation_scope']['confirmed'] else {}),**({'toc_scope':deepcopy(sc['toc_scope'])} if sc.get('toc_scope') and sc['toc_scope']['confirmed'] else {}),**({'front_scope':deepcopy(sc['front_scope'])} if sc.get('front_scope') and sc['front_scope']['confirmed'] else {}),**({'table_scope':deepcopy(sc['table_scope'])} if sc.get('table_scope') and sc['table_scope']['confirmed'] else {})}
            stem='restored-round-'+str(saved['number'])+'-'+uuid4().hex
            binding=(saved['mode'],after['rules']['sha256'],tuple(sorted(sc['types'].items())) if saved['mode']!='basic' else tuple(sc['body']))+((tuple(sorted(sc['table_scope']['table_types'].items())),) if sc.get('table_scope') and sc['table_scope']['confirmed'] else ())
            if sc.get('front_scope'):
                boundfront=deepcopy(sc['front_scope']);boundfront['input_sha256']=oh
                binding+=(sha256(json.dumps({k:boundfront[k] for k in ('objects','section_roles','template')},ensure_ascii=False,sort_keys=True).encode()),)
            if sc.get('toc_scope'):
                binding+=(sha256(json.dumps({k:sc['toc_scope'][k] for k in ('objects','covered_levels','complete','headings_complete','template')},ensure_ascii=False,sort_keys=True).encode()),)
            if sc.get('citation_scope'):
                binding+=(sha256(json.dumps({k:sc['citation_scope'][k] for k in ('scan','objects','complete','references_complete','template')},ensure_ascii=False,sort_keys=True).encode()),)
            if sc.get('note_scope'):
                from core.notes import digest as nd
                binding+=(nd({k:sc['note_scope'][k] for k in ('objects','template')}),)
            if sc.get('reference_scope'):
                from core.internal_refs import digest as rd
                binding+=(rd(sc['reference_scope']['template']),)
            if sc.get('caption_scope'):
                from core.captions import digest as cd
                binding+=(cd({k:sc['caption_scope'][k] for k in ('captions','chapter_map','associations','complete','chapters_complete','template')}),)
            if sc.get('table_scope',{}).get('layout_options'):binding+=(sha256(json.dumps(sc['table_scope']['layout_options'],ensure_ascii=False,sort_keys=True).encode()),)
            if sc.get('material_exclusions'):binding+=(sha256(json.dumps(sc['material_exclusions'],ensure_ascii=False,sort_keys=True).encode()),)
            from core.backmatter import binding as back_binding
            cfg=json.loads(pending['rulepaths'][saved['rule']].read_bytes())
            binding+=back_binding(saved['mode'],sc['types'],cfg.get('structure_version'))
            # Bundle uses freshly read attributes; no saved successful preservation/page claims enter it.
            bundle=new._collect_bundle(p,after,r.get('output_classification_manifest'),saved['number'],r)
            bundle['context']['validity']='导入历史，属性重新读取；修改/完整性/视觉结论未本次验收'
            new.history.append({'result':r,'stem':stem,'binding':binding,'reading_bundle':bundle,'restored':True,
                                'saved_record':deepcopy(saved['saved_summary']),'saved_changes':deepcopy(saved['changes']),
                                'project_rules_path':str(rulepath),'project_rules_kind':kinds[saved['rule']]})
            write_new(directory/(stem+'.json'),json_bytes(r))
            from core.report import markdown, modification_markdown
            write_new(directory/(stem+'-changes.md'),modification_markdown(r).encode());write_new(directory/(stem+'-recheck.md'),markdown(after).encode())
        if state['scope']['saved_confirmed']:
            if new.table_enabled and state['scope']['table_scope']['confirmed']:new.confirm_tables()
            if new.caption_enabled and state['scope']['caption_scope']['confirmed']:new.confirm_captions()
            if new.reference_enabled and state['scope']['reference_scope']['confirmed']:new.confirm_references()
            if new.note_enabled and state['scope']['note_scope']['confirmed']:new.confirm_notes()
            if new.citation_enabled and state['scope']['citation_scope']['confirmed']:new.confirm_citations()
            if new.toc_enabled and state['scope']['toc_scope']['confirmed']:new.confirm_toc()
            if new.front_enabled and state['scope']['front_scope']['confirmed']:new.confirm_front()
            require(new.confirm_and_check(),'本次恢复范围确认或重新检查失败')
            allowed={f['key'] for f in new.eligible()};new.set_selection([k for k in state['selected'] if k in allowed])
            dropped=[k for k in state['selected'] if k not in allowed]
            new.project_notice+=' 恢复时报告来自本次重新检查；改范围或规则后须重新确认。'+(f'已丢弃{len(dropped)}个不再可修正的选择：'+', '.join(dropped) if dropped else '')
        else:
            new.project_notice+=' 范围仍为草稿，请核对后点击确认检查。'
            if state['selected']:new.project_notice+=f"未恢复{len(state['selected'])}个待修正选择，确认检查后请重新选择。"
        # Only a fully prepared replacement invalidates the old owner's background jobs.
        self.invalidate_preview_jobs();self.project_pending=None
        return new

    def continue_history(self,identity,*,acknowledged=False):
        require(acknowledged is True,'请明确核对该轮保存的规则和范围后继续')
        h=next((h for h in self.history if h['stem']==identity),None);require(h is not None,'历史轮次不存在')
        self.history_bundle(identity)  # checks exact output hash, without switching
        r=h['result'];p=Path(r['output']);cfg=Path(h['project_rules_path'])
        # Validate both file and rules before changing current input.
        sc=manifest_scope(self,r['after'],r['after']['input_sha256'])
        Package(p);rules=effective_rules(**{('custom_rules_path' if h['project_rules_kind']=='custom' else 'rules_path'):cfg},mode=h['binding'][0])
        require(rules['sha256']==r['after']['rules']['sha256'],'历史规则发生变化，拒绝继续')
        self.custom_rules_path=cfg if h['project_rules_kind']=='custom' else None
        self.active_template=None;self.active_template_sha256=None
        if self.custom_rules_path:
            data=json.loads(cfg.read_bytes())
            if data.get('format')=='paper-grid-rule-bundle':
                self.active_template=deepcopy(data['modules']['main']['template']);self.active_template_sha256=sha256(cfg.read_bytes());self.workbench['active']=deepcopy(data)
            elif 'structure_version' in data:self.active_template=data;self.active_template_sha256=sha256(cfg.read_bytes())
        self.mode=h['binding'][0];self.sync_rules()
        require(self.rules_hash==r['after']['rules']['sha256'],'历史规则发生变化，拒绝继续')
        self.input_path=p;self.input_bytes=p.read_bytes();self.inventory=inspect_document(p);self.suggestions=suggest_paragraph_types(p,include_sections=self.mode=='academic')
        self.current_round=r['round']['number'];self.invalidate();self.body=sc['body'];self.paragraph_types=sc['types']
        self.material_exclusions=deepcopy(sc.get('material_exclusions',{}))
        self.table_enabled=bool(sc.get('table_scope'))
        if self.table_enabled:
            self.table_types=deepcopy(sc['table_scope']['table_types']);self.table_layout_options=deepcopy(sc['table_scope'].get('layout_options'));self.confirm_tables()
        self.caption_enabled=bool(sc.get('caption_scope'))
        if self.caption_enabled:self.adopt_caption_scope(sc['caption_scope'],confirmed=True)
        self.reference_enabled=bool(sc.get('reference_scope'))
        if self.reference_enabled:self.adopt_reference_scope(sc['reference_scope'],confirmed=True)
        self.note_enabled=bool(sc.get('note_scope'))
        if self.note_enabled:self.adopt_note_scope(sc['note_scope'],confirmed=True)
        self.citation_enabled=bool(sc.get('citation_scope'))
        if self.citation_enabled:self.adopt_citation_scope(sc['citation_scope'],confirmed=True)
        self.toc_enabled=bool(sc.get('toc_scope'))
        if self.toc_enabled:self.adopt_toc_scope(sc['toc_scope'],confirmed=True)
        self.front_enabled=bool(sc.get('front_scope'))
        if self.front_enabled:self.adopt_front_scope(sc['front_scope'],confirmed=True)
        return self.confirm_and_check()

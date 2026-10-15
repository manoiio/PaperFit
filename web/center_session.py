"""问题中心与阅读快照；只调用已有只读检查，历史绝不隐式切换输入。"""
from pathlib import Path
from copy import deepcopy
import json
from core import inspect_document
from core.widths import check_widths
from core.layout import suggest_pagination_aids
from core.package import DemoError,sha256,write_new
from .issues import project,next_steps
from .reading_report import portable,clean,html_report,markdown_report

OPERATIONS={'format':'格式修正','width':'宽度适配','pagination':'分页辅助','preview':'页面预览'}
KIND={'caption_position':'题注位置纠正','width_adaptation':'宽度适配','figure_layout':'图题相邻','pagination_layout':'分页辅助'}

class CenterSession:
    def init_center(self):
        self.center_selection_view=None;self.center_filter_identity=None;self.retired_history=[];self.operation='format';self.focus=None;self.reading_export=None;self.center_cache={}

    def invalidate_center(self):
        self.center_selection_view=None;self.center_filter_identity=None;self.focus=None;self.reading_export=None;self.center_cache={};self.operation='format'

    def history_rows(self):
        rows=deepcopy(self.retired_history)
        for h in self.history:
            r=h['result'];p=Path(r['output']);valid=p.is_file() and sha256(p.read_bytes())==r['output_body_manifest']['input_sha256']
            applicable=h['binding']==self._history_binding() and self.confirmed is not None
            d=r['problem_delta'];counts={'修改':len(r['changes']),'格式已解决':len(d['resolved_keys']),'格式剩余':r['after']['summary']['problem_count'],'格式新增':len(d['new_keys'])}
            if r.get('impact'):
                ic=r['impact']['counts'];counts.update({'格式已解决':ic['selected_resolved']+ic['natural_resolved'],'格式新增':ic['new_problem'],'转待复核':ic['problem_to_review'],'无法对齐':ic['unaligned']})
            if r.get('widths'):counts['宽度风险']=r['widths']['after']['summary']['risks']
            rows.append({'id':h['stem'],'round':r['round']['number'],'input_round':r['round']['input_round'],'operation':KIND.get(r.get('kind'),'格式修正'),
                         'status':'文件缺失或哈希变化，不可下载' if not valid else '导入的保存时历史；不是本次修改/完整性/视觉验收' if h.get('restored') else '适用于当前确认配置' if applicable else '不适用于当前状态（旧规则或范围）',
                         'downloadable':valid,'applicable':applicable,'counts':counts,'file_sha256':r['output_body_manifest']['input_sha256'],'rules_sha256':r['after']['rules']['sha256']})
        return rows

    def retire_center_history(self,preserve):
        if preserve:
            for h in self.history_rows():
                h.update(status='文件已清理，不适用于当前文件',downloadable=False,applicable=False)
                if h['id'] not in {x['id'] for x in self.retired_history}:self.retired_history.append(h)
        else:self.retired_history=[]

    def pagination_history(self,number,result=None):
        """Follow actual parent rounds; never imply that an old attribute check validated this file's pages."""
        graph={h['result']['round']['number']:h['result'] for h in self.history}
        if result:graph[result['round']['number']]=result
        seen=set();out=[]
        while number and number in graph and number not in seen:
            seen.add(number);r=graph[number]
            if r.get('layout'):out.append({'round':number,'rules_sha256':r['after']['rules']['sha256'],'file_sha256':r['output_body_manifest']['input_sha256'],
                                          'message':r['layout']['message'],'checks':deepcopy(r['layout']['checks']),'status':'该历史轮次属性读回；不证明当前轮实际分页'})
            number=r['round']['input_round']
        return list(reversed(out))

    def _collect_bundle(self,path,report,classification,number,result=None):
        raw=Path(path).read_bytes();hash_=sha256(raw)
        if hash_!=report['input_sha256']:raise DemoError('报告与文件哈希不匹配，拒绝展示或导出')
        context={'file_sha256':hash_,'round':number,'mode':report['rules'].get('mode',self.mode),'rules_sha256':report['rules']['sha256'],'validity':'对应文件哈希已核对'}
        cache_key=(hash_,context['rules_sha256'],self.mode,json.dumps(classification,sort_keys=True))
        cached=self.center_cache.get(cache_key)
        if cached is None:
            boundaries=list(report['coverage'].get('front_limits',[]))
            try:width=self.analysis('width',path)
            except Exception:width=None;boundaries.append('宽度检查失败：未检查，格式结果仍保留，请核对文档支持范围。')
            proposals=None
            if classification is not None and context['mode']!='basic':
                try:proposals=self.analysis('pagination',path,classification)
                except Exception:boundaries.append('分页关联读取失败：未检查，不执行关联建议。')
            cached={'width':width,'proposals':proposals,'inventory':self.analysis('inventory',path),'boundaries':boundaries}
            if len(self.center_cache)>=16:self.center_cache.pop(next(iter(self.center_cache)))
            self.center_cache[cache_key]=cached
        projection=project(report,cached['width'],cached['proposals'],inventory=cached['inventory'],context=context,boundaries=cached['boundaries'])
        from .scope_session import report_scope_summary
        return {'plan':deepcopy(result.get('plan')) if result else None,'impact':deepcopy(result.get('impact')) if result else None,'rehearsal':deepcopy(result.get('rehearsal')) if result else None,'scope_summary':report_scope_summary(report,classification),'context':context,'format':deepcopy(report),'width':deepcopy(cached['width']),'proposals':deepcopy(cached['proposals']),'projection':projection,
                'changes':deepcopy(result['changes']) if result else [],'delta':deepcopy(result['problem_delta']) if result else None,
                'pagination_applied':deepcopy(result.get('layout')) if result else None,'pagination_history':self.pagination_history(number,result),'preservation':deepcopy(result.get('preservation')) if result else None,
                'steps':next_steps(report,cached['width'],result,is_output=bool(result)),'preview':{'status':'未生成预览'},'visual':{'status':'未记录人工视觉复核'},'history':self.history_rows()}

    def capture_center_round(self,result):
        return self._collect_bundle(result['output'],result['after'],result.get('output_classification_manifest'),result['round']['number'],result)

    def current_bundle(self):
        self._current()
        if self.confirmed is None or self.report is None:raise DemoError('请先确认范围并检查')
        if self.result is not None:
            if not self.downloads():raise DemoError('当前修正结果已失效')
            r=self.result;bundle=self._collect_bundle(r['output'],r['after'],r.get('output_classification_manifest'),r['round']['number'],r);key='round-'+str(r['round']['number'])
        else:
            bundle=self._collect_bundle(self.input_path,self.report,self.classification_confirmed,self.current_round);key='input'
        bundle['target']=key;bundle['history']=self.history_rows()
        # A preview/visual review must match this exact file/configuration/round, not a previous input.
        try:
            meta=self.get_preview(key,verify_environment=False)
            if meta:
                bundle['preview']={k:deepcopy(meta[k]) for k in ('generated_at','renderer','renderer_version','page_count','preview_range','fonts','font_notes','document_sha256','render_config_sha256') if k in meta};bundle['preview']['status']='已生成本文件预览'
                bundle['preview']['environment_status']='生成时环境；新预览或刷新时重新核对'
                t=self.preview_targets()[key];review=self.visual_reviews.get(self._preview_binding(t,probe=False))
                if review:bundle['visual']=deepcopy(review)
        except Exception:bundle['preview']={'status':'匹配预览不可用，未作为视觉验收'}
        return bundle

    def focus_operation(self,area,target,keys=()):
        if area not in OPERATIONS:raise DemoError('操作区域无效')
        bundle=self.current_bundle()
        if target!=bundle['target']:raise DemoError('建议所属文件已变化，请重新查看')
        self.operation=area;self.focus={'area':area,'target':target,'keys':list(keys),'file_sha256':bundle['context']['file_sha256'],'rules_sha256':self.rules_hash}
        # Navigation changes no selected keys, classification, result, generation count or files.

    def prepare_reading_export(self,display_name='待检查文档.docx',include_excerpts=False):
        b=self.current_bundle();options=(display_name,bool(include_excerpts));old=self.reading_export
        if not old or old['signature']!=self._signature() or old['file_sha256']!=b['context']['file_sha256'] or old.get('options')!=options:
            data=portable(b,display_name=display_name,include_excerpts=include_excerpts)
            self.reading_export={'signature':self._signature(),'file_sha256':b['context']['file_sha256'],'data':data,'options':options}
        return self.reading_downloads()

    def reading_downloads(self):
        if not self.reading_export:return {}
        b=self.current_bundle();e=self.reading_export
        if e['signature']!=self._signature() or b['context']['file_sha256']!=e['file_sha256']:
            self.reading_export=None;return {}
        # Refresh only true read-only preview/visual/history metadata; no API or editing calls.
        d={**e['data'],**{k:clean(b[k]) for k in ('preview','visual','history')}}
        return self.cached_bytes('reading',d,lambda:{'report.html':html_report(d).encode(),'report.md':markdown_report(d).encode(),'report.json':(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()})

    def history_bundle(self,identity):
        h=next((h for h in self.history if h['stem']==identity),None)
        if not h:raise DemoError('此轮文件已清理，只有历史摘要')
        r=h['result'];p=Path(r['output'])
        if not p.is_file() or sha256(p.read_bytes())!=r['output_body_manifest']['input_sha256']:raise DemoError('此轮文件缺失或哈希变化，拒绝下载')
        row=next(x for x in self.history_rows() if x['id']==identity)
        b=deepcopy(h['reading_bundle']);b['history']=self.history_rows();b['context']['validity']=row['status']
        if h.get('restored'):b['saved_record']={'status':'项目包保存时记录，未经本次验真', 'record':clean(h['saved_record'])}
        for record in b['projection']['records']:record['context']['validity']=row['status']
        # A stored snapshot does not falsely claim a future preview was available then.
        return b

    def history_reading_downloads(self,identity):
        b=self.history_bundle(identity);h=next(h for h in self.history if h['stem']==identity);r=h['result'];d=portable(b)
        return {'fixed.docx':Path(r['output']).read_bytes(),'report.html':html_report(d).encode(),'report.json':json.dumps(d,ensure_ascii=False,indent=2).encode()}

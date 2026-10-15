"""会话私有、只存数据的有界缓存；每次使用仍校验文件内容。"""
from copy import deepcopy
from pathlib import Path
from io import BytesIO
import json,zipfile
from core.package import DemoError,sha256

def encoded(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()

class EfficiencySession:
    def init_efficiency(self):
        self.readonly_cache={};self.byte_cache={};self.package_cache=None

    def cached_data(self,key,compute):
        if key not in self.readonly_cache:
            if len(self.readonly_cache)>=16:self.readonly_cache.pop(next(iter(self.readonly_cache)))
            self.readonly_cache[key]=deepcopy(compute())
        return deepcopy(self.readonly_cache[key])

    def analysis(self,kind,path,classification=None):
        raw=Path(path).read_bytes()
        key=(kind,sha256(raw),self.rules_hash,self.mode,encoded(classification))
        def compute():
            if kind=='width':
                from core.widths import check_widths
                return check_widths(path,rules_sha256=self.rules_hash)
            if kind=='pagination':
                from core.layout import suggest_pagination_aids
                return suggest_pagination_aids(path,classification)
            from core import inspect_document
            return inspect_document(path)
        result=self.cached_data(key,compute)
        if Path(path).read_bytes()!=raw:raise DemoError('分析期间文件发生变化，请重新检查')
        return result

    def cached_bytes(self,kind,data,compute):
        key=(kind,sha256(encoded(data)))
        if key not in self.byte_cache:
            value=compute();size=sum(map(len,value.values()))
            if size>32*1024*1024:return value
            while self.byte_cache and (len(self.byte_cache)>=8 or sum(len(v) for item in self.byte_cache.values() for v in item.values())+size>32*1024*1024):
                self.byte_cache.pop(next(iter(self.byte_cache)))
            self.byte_cache[key]=value
        return dict(self.byte_cache[key])

    def confirm_and_check(self):
        try:self.confirm()
        except Exception as exc:
            from .session import public_error
            self.error=public_error(exc);return False
        return self.check()

    def classification_candidates(self,types=(),ambiguous_only=False):
        self._current()
        return [p['index'] for p in self.suggestions['paragraphs']
                if (not types or self.paragraph_types[str(p['index'])] in types)
                and (not ambiguous_only or p['ambiguous'])]

    def batch_types(self,numbers,target):
        from core.classification import TYPES
        self._current()
        if target not in TYPES or not numbers or any(type(n) is not int or str(n) not in self.paragraph_types for n in numbers) or len(set(numbers))!=len(numbers):
            raise DemoError('请选择当前文件中明确的段落编号及类型')
        items=deepcopy(self.paragraph_types)
        for n in numbers:items[str(n)]=target
        return self.set_types(items)

    def parse_paragraph_ranges(self,text):
        self._current();numbers=set();limit=len(self.paragraph_types)
        try:
            for token in text.replace('，',',').split(','):
                token=token.strip()
                if not token:continue
                parts=token.split('-')
                if len(parts)>2:raise ValueError()
                a=int(parts[0]);b=int(parts[-1])
                if not 1<=a<=b<=limit:raise ValueError()
                numbers.update(range(a,b+1))
        except ValueError:raise DemoError('编号范围无效，请使用当前文件编号，例如4-6,11') from None
        return sorted(numbers)

    def initial_adjustments(self):
        self._current()
        return [p['index'] for p in self.suggestions['paragraphs'] if self.paragraph_types[str(p['index'])]!=p['suggested_type']]

    def restore_types(self,*,confirmed=False):
        self._current()
        if confirmed is not True:raise DemoError('请先核对将被覆盖的人工调整，并明确确认恢复')
        return self.set_types({str(p['index']):p['suggested_type'] for p in self.suggestions['paragraphs']})

    def result_package(self,max_bytes=25*1024*1024):
        """每次都先重新核对文档/规则；ZIP仅固定成员，无原稿/路径/日志。"""
        files=self.downloads()
        if not files:raise DemoError('本轮结果不存在或已经失效')
        from .reading_report import portable,clean,html_report,markdown_report
        from core.report import markdown,modification_markdown
        b=self.current_bundle();d=portable(b)
        safe=clean(self.result);safe['output']='fixed.docx';safe['after']['input']='fixed.docx'
        if safe['after'].get('notes'):
            for row in safe['after']['notes']['inventory']['objects']:row.pop('preview',None)
            for f in safe['after']['findings']:
                if f['rule_id'] in ('R36','R37'):f.pop('excerpt',None)
        # Export the validated source bytes, retaining the actual configuration hash
        # and a supported reload schema rather than an engine projection.
        rule_bytes=Path(self.custom_rules_path or self.rules_path).read_bytes()
        def build():
            members={'fixed.docx':files['fixed.docx'],'changes.md':modification_markdown(safe).encode(),
                 'recheck.md':markdown(safe['after']).encode(),'report.html':html_report(d).encode(),
                 'report.json':encoded(d),'report.md':markdown_report(d).encode(),
                 'scope.json':encoded(self.result.get('output_classification_manifest',self.result['output_body_manifest'])),
                 'rules.json':rule_bytes,
                     'README.txt':('论文有格本轮结果包\n第'+str(self.result['round']['number'])+'轮；输出和规则哈希见报告。\n只代表启用规则及确认范围，分页另行目视核对；Word未验收。\n默认不含原稿、页面图片、日志、API记录或完整论文摘录。\n').encode()}
            members['scope-summary.json']=encoded(d['scope_summary'])
            if d.get('impact'):members['rehearsal-impact.json']=encoded({'impact':d['impact'],'adoption':d['rehearsal']})
            if self.mode=='academic':
                from core.academic_rules import PATH
                from core.extended import EXTENDED_RULES
                members['academic-rules.json']=PATH.read_bytes();members['extended-rules.json']=EXTENDED_RULES.read_bytes()
                if self.result['after']['rules'].get('backmatter_sha256'):
                    from core.backmatter import PATH as BACK_PATH
                    members['backmatter-rules.json']=BACK_PATH.read_bytes()
                if self.result['after']['coverage'].get('table_scope'):
                    from core.table_text import PATH as TABLE_PATH
                    members['table-rules.json']=TABLE_PATH.read_bytes()
                    opts=self.result['after']['coverage']['table_scope'].get('layout_options')
                    if opts:members['table-layout-options.json']=encoded(opts)
            if self.result['after']['coverage'].get('caption_scope'):
                members['caption-supplement.json']=encoded(self.result['after']['coverage']['caption_scope']['template'])
            if self.result.get('range_mapping'):members['range-mapping.json']=encoded(self.result['range_mapping'])
            if self.result['after']['coverage'].get('note_scope'):
                members['note-supplement.json']=encoded(self.result['after']['coverage']['note_scope']['template'])
            if self.result['after']['coverage'].get('citation_scope'):
                members['citation-supplement.json']=encoded(self.result['after']['coverage']['citation_scope']['template'])
            if self.result['after']['coverage'].get('toc_scope'):
                members['toc-supplement.json']=encoded(self.result['after']['coverage']['toc_scope']['template'])
            if self.result['after']['coverage'].get('front_scope'):
                members['front-supplement.json']=encoded(self.result['after']['coverage']['front_scope']['template'])
            if self.active_template:members['template.json']=rule_bytes
            if self.workbench['active']:members['rule-bundle.json']=rule_bytes
            return members
        members=self.cached_bytes('package-members',{'report':d,'result':safe,'rules_sha256':sha256(rule_bytes)},build)
        if sum(map(len,members.values()))>max_bytes:raise DemoError('结果包超过25MB上限，请使用单文件下载')
        binding=sha256(b''.join(name.encode()+sha256(data).encode() for name,data in sorted(members.items())))
        if not self.package_cache or self.package_cache[0]!=binding:
            out=BytesIO()
            with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
                for name,data in members.items():
                    info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
            self.package_cache=(binding,out.getvalue())
        # Reject a concurrent change occurring while rendering reports/packing.
        if self.downloads().get('fixed.docx')!=members['fixed.docx']:raise DemoError('打包期间文件变化，拒绝下载')
        return self.package_cache[1]

"""Task-local upload buffers, native extraction and strict reusable rule packages."""
from pathlib import Path
from copy import deepcopy
from core.package import DemoError,sha256,Package,q,write_new,NS,parse
from core.norms import extract_norm
from core import rule_bundle as rb,load_rules
from .scope_session import fingerprint

def file_input(model,data,name,encoding='auto'):
    if model.inventory is None:raise DemoError('请先载入待排版论文')
    kind=Path(name).suffix.lower().lstrip('.')
    if kind not in ('txt','docx'):raise DemoError('格式要求仅支持TXT/DOCX')
    path=None
    if kind=='docx':
        if not isinstance(data,bytes) or not data or len(data)>2*1024*1024:raise DemoError('格式要求DOCX最大2MB')
        folder=model.task_dir/'requirements-input';folder.mkdir(exist_ok=True)
        path=folder/(sha256(data)+'.docx')
        if not path.exists():write_new(path,data)
        if sha256(path.read_bytes())!=sha256(data):raise DemoError('要求文件缓存字节已变化')
    extracted=extract_norm(data,kind,encoding=encoding,path=path)
    unextracted=[n for n in extracted['notes'] if '未提取' in n and not n.startswith('只提取')]
    if kind=='docx':
        pkg=Package(path);body=pkg.root.find(q('body'))
        if any(n.tag not in (q('p'),q('tbl'),q('sectPr')) for n in body):unextracted.append('主文档含未提取的内容控件或其他容器')
        # Extra story content is outside the original norm extractor; never call
        # that limitation proof that it contained no requirements.
        types=parse(pkg.parts['[Content_Types].xml'])
        if any(any(t.get('ContentType','').endswith('.'+kind+'+xml') for kind in ('header','footer','footnotes','endnotes')) for t in types):unextracted.append('要求文件含页眉页脚/注释部件，原提取器未读取其中内容')
        if pkg.root.xpath('.//w:fldSimple',namespaces=NS):unextracted.append('简单字段中的内容未提取，不执行或刷新字段')
    extracted['unextracted']=unextracted
    from ai.file_spec import request_for
    request_for(extracted)  # Reject the entire over-budget file; never truncate.
    out={'kind':'file','name':Path(name).name,'extraction':extracted}
    out['seal']=fingerprint(out);return out

def saved_input(model,data,name):
    # Only native full packages here; old templates remain in the local workbench.
    b=rb.loads(data,load_rules(model.rules_path));rb.compile_bundle(b,load_rules(model.rules_path))
    out={'kind':'saved','name':Path(name).name,'file_sha256':sha256(data),'bundle':b}
    out['seal']=fingerprint(out);return out

def verify(source,model):
    if source is None:return
    if type(source) is not dict or source.get('seal')!=fingerprint({k:v for k,v in source.items() if k!='seal'}):raise DemoError('要求输入已变化，请重新上传或核对')
    if source['kind']=='file':
        from ai.file_spec import request_for
        request_for(source['extraction'])
    elif source['kind']=='saved':rb.compile_bundle(rb.validate(source['bundle'],load_rules(model.rules_path)),load_rules(model.rules_path))
    else:raise DemoError('未知要求来源')

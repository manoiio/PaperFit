"""显式、本机、独立配置的可选预览；不改变DOCX，不参与格式规则结论。"""
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timezone
import json,os,signal,subprocess,time,re
from xml.sax.saxutils import escape
from .package import Package,DemoError,sha256,write_new,parse,q
from .formats import Resolver,Unresolved

RUNTIME=Path(os.environ.get('PAPERFIT_PREVIEW_RUNTIME',str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies')))
RENDERER=Path(os.environ.get('PAPERFIT_PREVIEW_RENDERER',str(Path.home()/'.codex/plugins/cache/openai-primary-runtime/documents/26.1013.11914/skills/documents/render_docx.py')))
FONT_DIRS=['/System/Library/Fonts/Supplemental','/System/Library/Fonts','/Library/Fonts',str(Path.home()/'Library/Fonts'),'/Applications/Microsoft Word.app/Contents/Resources/DFonts']
CONFIG={'version':'preview-1.6','max_pages':10,'dpi':130,'timeout_seconds':45,
        'strong_font_aliases':['仿宋_GB2312'],
        'font_aliases':{'宋体':'Songti SC','黑体':'Heiti SC','楷体':'Kaiti SC','仿宋':'Songti SC','仿宋_GB2312':'FangSong'}}

def configuration():
    if not (RUNTIME/'python/bin/python3').is_file() or not RENDERER.is_file():raise DemoError('当前Mac未找到Codex bundled渲染运行时；仍可检查、修正及下载')
    try:
        version=subprocess.run([str(RUNTIME/'bin/override/soffice'),'--version'],capture_output=True,text=True,timeout=5,check=True,env={'PATH':str(RUNTIME/'bin/override')+':/usr/bin:/bin','LANG':'en_US.UTF-8'}).stdout.strip()
    except (OSError,subprocess.SubprocessError):raise DemoError('bundled渲染器不可用；检查、修正及下载仍可使用') from None
    font_files=[]
    for folder in FONT_DIRS:
        for root,dirs,files in os.walk(folder):
            for name in sorted(files):
                p=Path(root)/name
                try:
                    stat=p.stat();font_files.append((str(p),stat.st_size,stat.st_mtime_ns))
                except OSError:pass
    data={**CONFIG,'renderer_version':version,'font_environment_sha256':sha256(json.dumps(sorted(set(font_files))).encode()),'renderer':'Codex bundled LibreOffice / Poppler','bundle':'26.1013.11914',
          'renderer_script_sha256':sha256(RENDERER.read_bytes()),'font_resolver_sha256':sha256(Path(__file__).with_name('formats.py').read_bytes()),'note_parser_sha256':sha256(Path(__file__).with_name('notes.py').read_bytes()),'worker_sha256':sha256(Path(__file__).with_name('preview_worker.py').read_bytes())}
    return data,sha256(json.dumps(data,ensure_ascii=False,sort_keys=True).encode())

def _environment(conf):
    # No API credentials, .env contents, or all-environment serialization in renderer processes/logs.
    return {'PATH':str(RUNTIME/'bin/override')+':/usr/bin:/bin','FONTCONFIG_FILE':str(conf),
            'LANG':'en_US.UTF-8','TMPDIR':'/private/tmp'}

def _fonts(pkg,job,config,deadline=None):
    deadline=deadline or time.monotonic()+config["timeout_seconds"]
    def remaining(cap):
        left=deadline-time.monotonic()
        if left<=0:raise subprocess.TimeoutExpired("font check",config["timeout_seconds"])
        return min(cap,left)
    dirs=FONT_DIRS
    xml='<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig>'
    xml+=''.join('<dir>'+escape(d)+'</dir>' for d in dirs)+'<cachedir>'+escape(str(job/'font-cache'))+'</cachedir>'
    xml+=''.join('<alias binding="'+('strong' if k in config.get('strong_font_aliases',[]) else 'weak')+'"><family>'+escape(k)+'</family><prefer><family>'+escape(v)+'</family></prefer></alias>' for k,v in config['font_aliases'].items())+'</fontconfig>'
    conf=job/'fonts.conf';conf.write_text(xml,encoding='utf-8');env=_environment(conf)
    bins=RUNTIME/'native/poppler/poppler/bin'
    try:
        result=subprocess.run([str(bins/'fc-list'),'-f','%{family}\n'],env=env,capture_output=True,text=True,timeout=remaining(20),check=True)
        families={n.strip() for line in result.stdout.splitlines() for n in line.split(',')}
        required=set();theme=False;res=Resolver(pkg)
        font_roots=[pkg.root]+[parse(data) for name,data in pkg.parts.items() if re.fullmatch(r'word/(?:header|footer)[\w-]*\.xml',name)]
        from .notes import inventory as note_inventory
        font_roots.extend(parse(pkg.parts[name]) for name in note_inventory(pkg)['parts'].values())
        for p in (p for root in font_roots for p in root.iter(q('p'))):
            for r in p.iter(q('r')):
                try:
                    for slot in ('eastAsia','ascii','hAnsi'):
                        value=res.font(res.layers(p,r),slot)
                        if isinstance(value,str):required.add(value)
                        elif isinstance(value,dict):theme=True
                except Unresolved:theme=True
        matches=[];warnings=[]
        for name in sorted(required):
            match=subprocess.run([str(bins/'fc-match'),'-f','%{family}',name],env=env,capture_output=True,text=True,timeout=remaining(5),check=True).stdout.strip()
            exact=name in families
            matches.append({'target':name,'installed_exact':exact,'resolved_family':match})
            if not exact:warnings.append(f'目标字体“{name}”未安装，预览解析为“{match}”；替代可能改变分页，交付DOCX字体不改。')
        if theme:warnings.append('文档含主题或无法完全解析的字体；预览由LibreOffice解析，字体清单不是全字形审计。')
        return env,matches,warnings
    except subprocess.TimeoutExpired:
        raise DemoError('预览字体核对超时，本次预览未完成；检查、修正及下载仍可使用') from None
    except (OSError,subprocess.SubprocessError):
        raise DemoError('预览字体可用性核对失败；检查、修正及下载仍可使用') from None

def render_preview(input_path,job_root,*,context=None):
    # Synchronous callers remain supported; actual bundled renders serialize
    # with the same process-local gate used by background calls.
    from .preview_jobs import RENDER_LOCK
    if not RENDER_LOCK.acquire(timeout=45):raise DemoError('本机渲染器仍在忙，请稍后重新生成')
    try:return _render_preview(input_path,job_root,context=context)
    finally:RENDER_LOCK.release()

def _render_preview(input_path,job_root,*,context=None):
    started=time.monotonic()
    pkg=Package(input_path);config,cfg_hash=configuration()
    for name,data in pkg.parts.items():
        if name.endswith('.rels') and any(e.get('TargetMode')=='External' for e in parse(data)):
            raise DemoError('预览暂不支持含外部关系的DOCX，避免渲染读取外部内容；本地检查与下载仍可用')
    job=Path(job_root).resolve()/('preview-'+uuid4().hex);job.mkdir(parents=True,exist_ok=False)
    write_new(job/'source.docx',pkg.raw)
    env,fonts,warnings=_fonts(pkg,job,config,deadline=started+config['timeout_seconds'])
    request={**config,'renderer_script':str(RENDERER)}
    write_new(job/'request.json',json.dumps(request,ensure_ascii=False,indent=2).encode())
    proc=None
    try:
        proc=subprocess.Popen([str(RUNTIME/'python/bin/python3'),str(Path(__file__).with_name('preview_worker.py')),str(job)],
                              env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        proc.wait(timeout=max(0.01,config['timeout_seconds']-(time.monotonic()-started)))
        if proc.returncode:raise DemoError('本地渲染失败；原文件与格式处理结果保留，请检查文档兼容性')
        result=json.loads((job/'worker-result.json').read_text())
        pages=[job/f'page-{i}.png' for i in range(1,result['preview_pages']+1)]
        if not pages or any(not p.is_file() or p.stat().st_size==0 for p in pages):raise DemoError('渲染未得到有效页面')
    except subprocess.TimeoutExpired:
        raise DemoError('本地预览超时（45秒），本次预览未完成；检查、修正与下载仍可用') from None
    finally:
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        if Path(input_path).read_bytes()!=pkg.raw or (job/'source.docx').read_bytes()!=pkg.raw:
            raise DemoError('渲染输入哈希发生变化，预览已拒绝')
    meta={'document_sha256':pkg.hash,'render_config_sha256':cfg_hash,'generated_at':datetime.now(timezone.utc).isoformat(),
          'renderer':config['renderer'],'renderer_version':config['renderer_version'],'bundle':config['bundle'],'page_count':result['page_count'],
          'preview_range':[1,result['preview_pages']],'fonts':fonts,'font_notes':warnings,
          'context':context or {},'fallback_odt':result['fallback_odt'],'input_bytes_unchanged':True,
          'limitation':'不是Microsoft Word验收；分页可能不同。格式属性通过与可见排版复核分别记录。',
          'pages':[str(p) for p in pages],'pdf':result['pdf']}
    # Bind all produced bytes; a changed cached image/PDF cannot be served as the previous preview.
    meta['artifact_sha256']={str(p):sha256(p.read_bytes()) for p in [*pages,Path(result['pdf'])]}
    write_new(job/'preview.json',json.dumps(meta,ensure_ascii=False,indent=2).encode())
    return meta

def valid_artifacts(meta):
    try:
        if not meta.get('pages') or not meta.get('artifact_sha256') or not set(meta['pages']).issubset(meta['artifact_sha256']):return False
        return all(Path(p).is_file() and sha256(Path(p).read_bytes())==h for p,h in meta['artifact_sha256'].items())
    except (OSError,KeyError,TypeError):return False

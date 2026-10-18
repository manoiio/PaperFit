"""Local startup and explicit diagnostics. No document or credential logging."""
from pathlib import Path
import importlib,json,os,subprocess,sys,time,urllib.request,fcntl,socket,tempfile
ROOT=Path(__file__).resolve().parent
STATE=ROOT/'work/local'
URL='http://127.0.0.1:8501'

def renderer_environment(root=ROOT):
    env=os.environ.copy()
    if not env.get('PAPERFIT_PREVIEW_RENDERER'):
        base=Path.home()/'.codex/plugins/cache/openai-primary-runtime/documents'
        candidates=sorted(base.glob('*/skills/documents/render_docx.py'),reverse=True)
        if candidates:env['PAPERFIT_PREVIEW_RENDERER']=str(candidates[0])
    return env

def dependencies():
    result={}
    for name in ('docx','lxml','streamlit','typing_extensions'):
        try:importlib.import_module(name);result[name]=True
        except (ImportError,OSError):result[name]=False
    return result

def health():
    try:
        # Ignore user proxy settings for a loopback-only health check.
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(URL+'/_stcore/health',timeout=2) as response:return response.status==200 and response.read(16)==b'ok'
    except (OSError,ValueError):return False

def listeners():
    result=subprocess.run(['/usr/sbin/lsof','-nP','-iTCP:8501','-sTCP:LISTEN','-t'],capture_output=True,text=True,timeout=5)
    return sorted({int(p) for p in result.stdout.split() if p.isdigit()})

def owned(pid,root=ROOT):
    try:
        command=subprocess.run(['/bin/ps','-p',str(pid),'-o','command='],capture_output=True,text=True,timeout=5).stdout.strip()
        cwd=subprocess.run(['/usr/sbin/lsof','-a','-p',str(pid),'-d','cwd','-Fn'],capture_output=True,text=True,timeout=5).stdout.splitlines()
        # Health alone, a saved PID, or a matching process name never proves ownership.
        import re
        # macOS ps prints argv without preserving quotes. shlex would split a
        # legitimate absolute app path at spaces. Match our exact module prefix
        # and the entire known target, with an argument boundary, instead.
        match=re.fullmatch(r'(.+?) -m streamlit run (.+)',command)
        if not match or Path(match[1]).name not in ('python','python3','Python','python3.12','python3.13','python3.14'):return False
        target=match[2]
        known=(str(root.resolve()/'app.py'),'app.py')
        return 'n'+str(root.resolve()) in cwd and any(target==app or target.startswith(app+' --') for app in known)
    except (OSError,ValueError,subprocess.SubprocessError):return False

def launch(open_browser=True):
    STATE.mkdir(parents=True,exist_ok=True)
    with (STATE/'startup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        missing=[n for n,ok in dependencies().items() if not ok]
        if missing:raise RuntimeError('缺少基础依赖：'+', '.join(missing)+'。请由维护人员核对现有.venv与requirements.txt；启动器不会安装或升级。')
        pids=listeners()
        if pids:
            if not all(owned(pid) for pid in pids):raise RuntimeError('8501端口被其他服务占用，未结束任何进程。请先核对占用程序，或联系维护人员。')
            if not health():raise RuntimeError('本项目进程存在但健康检查未通过。请稍后再试；若持续失败，在环境与恢复中查看说明，不要重复启动。')
            action='reused'
        else:
            python=ROOT/'.venv/bin/python'
            if not python.is_file():raise RuntimeError('未找到现有.venv/bin/python；不会自动重建环境。')
            # Never retain arbitrary Streamlit tracebacks, paper text, or environment.
            process=subprocess.Popen([str(python),'-m','streamlit','run',str(ROOT/'app.py'),'--server.address','127.0.0.1','--server.port','8501','--server.fileWatcherType','none','--browser.gatherUsageStats','false'],cwd=ROOT,env=renderer_environment(),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                if process.poll() is not None:raise RuntimeError('服务启动后退出（状态 '+str(process.returncode)+'）。请先运行环境自检，确认.venv和端口；不会反复重启。')
                if health() and all(owned(p) for p in listeners()) and listeners():break
                time.sleep(.4)
            else:raise RuntimeError('30秒内服务未就绪。请运行“.venv/bin/python scripts/local_start.py --check”查看基础环境；论文与历史未删除。')
            action='started'
        with (STATE/'startup.jsonl').open('a') as f:f.write(json.dumps({'time':int(time.time()),'action':action,'port':8501})+'\n')
    if open_browser:subprocess.run(['/usr/bin/open',URL],check=True)
    return action

def probe_binding():
    from hashlib import sha256
    info=Path('/Applications/Microsoft Word.app/Contents/Info.plist')
    return sha256((info.read_bytes() if info.is_file() else b'')+(ROOT/'core/word_native.py').read_bytes()).hexdigest()

def environment():
    deps=dependencies();rows=[{'item':'基础检查与修正','state':'可用' if all(deps.values()) else '缺少依赖','detail':'现有Python依赖；未运行论文任务' if all(deps.values()) else '、'.join(k for k,v in deps.items() if not v)}]
    try:
        from ai.short_spec import settings
        settings();api=True
    except Exception:api=False
    rows.append({'item':'DeepSeek','state':'已配置，未调用' if api else '未配置或配置无效','detail':'普通自检不发送请求；本地检查修正不需要API'})
    from core.word_native import available
    installed=available();guard=Path(tempfile.gettempdir())/('paperfit-word-'+str(os.getuid())+'.uncertain')
    rows.append({'item':'Word自动化','state':'已安装，尚未实测' if installed else '未安装','detail':'需要明确深入检测；不代表权限或当前对话框状态正常'})
    if guard.exists():rows[-1].update(state='超时隔离中',detail='可能仍有任务运行；不自动结束Word或删除任务')
    runtime=Path(os.environ.get('PAPERFIT_PREVIEW_RUNTIME',str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies')))
    bins=runtime/'native/poppler/poppler/bin'
    rows.append({'item':'Word PDF与页图','state':'工具已找到，尚未实测' if installed and all((bins/n).is_file() for n in ('pdfinfo','pdftoppm')) else '可选工具不完整','detail':'PDF导出需Word权限；DOCX下载不依赖PDF'})
    renderer=Path(renderer_environment().get('PAPERFIT_PREVIEW_RENDERER','/nonexistent'))
    rows.append({'item':'LibreOffice备用预览','state':'工具已找到，尚未实测' if renderer.is_file() and (runtime/'bin/override/soffice').is_file() else '未找到可选工具','detail':'仅查本机文件，不启动Office或安装软件'})
    try:
        receipt=json.loads((STATE/'word-probe.json').read_text())
        if receipt.get('binding')==probe_binding() and receipt.get('status')=='Word PDF实际调用成功':
            rows[2]['detail']+='；最近公开样本探测成功（时间戳 '+str(receipt['time'])+'），不是本次普通自检调用'
            rows[3]['detail']+='；最近实测PDF及首张页图成功'
    except (OSError,ValueError,KeyError):pass
    return rows

def deep_check():
    """Explicit public synthetic probe, using the existing isolated Word adapter."""
    from core.word_native import export_pdf
    from core.package import sha256
    source=ROOT/'samples/correct.docx';raw=source.read_bytes();started=time.monotonic()
    STATE.mkdir(parents=True,exist_ok=True)
    from uuid import uuid4
    target=STATE/('word-probe-'+uuid4().hex+'.pdf')
    receipt=export_pdf(raw,target)
    pdf=target.read_bytes()
    if source.read_bytes()!=raw:raise RuntimeError('自检原稿发生变化')
    runtime=Path(os.environ.get('PAPERFIT_PREVIEW_RUNTIME',str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies')))
    bins=runtime/'native/poppler/poppler/bin'
    info=subprocess.run([str(bins/'pdfinfo'),str(target)],capture_output=True,text=True,timeout=10,check=True).stdout
    subprocess.run([str(bins/'pdftoppm'),'-f','1','-l','1','-scale-to','700','-singlefile','-png',str(target),str(target.with_suffix(''))],capture_output=True,timeout=30,check=True)
    image=target.with_suffix('.png')
    record={'binding':probe_binding(),'first_page_sha256':sha256(image.read_bytes()),'pdf_pages':next((v.strip() for v in info.splitlines() if v.startswith('Pages:')),'unknown'),'time':int(time.time()),'source':'samples/correct.docx','source_sha256':sha256(raw),'pdf_sha256':sha256(pdf),'seconds':round(time.monotonic()-started,3),'status':'Word PDF实际调用成功','receipt':receipt}
    STATE.mkdir(parents=True,exist_ok=True)
    (STATE/'word-probe.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
    return record

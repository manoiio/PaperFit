"""macOS Word calculator adapter; unique private copies, selected fields only."""
from pathlib import Path
from uuid import uuid4
import sys,os,json,subprocess,tempfile,time,fcntl,shutil
from .package import DemoError,sha256

def literal(s):return json.dumps(str(s),ensure_ascii=False)
def available():return sys.platform=='darwin' and Path('/Applications/Microsoft Word.app/Contents/Resources/Word.sdef').is_file()
def calculate(raw,codes,targets,*,update=True):
 if not available():raise DemoError('本机没有已验证的macOS Microsoft Word环境')
 root=Path(tempfile.gettempdir()).resolve()/'paperfit-word-calculator';root.mkdir(parents=True,exist_ok=True)
 folder=root/('PaperFit-'+uuid4().hex);folder.mkdir();path=folder/('pf-'+uuid4().hex+'.docx');path.write_bytes(raw)
 name=path.name;lockpath=Path(tempfile.gettempdir())/('paperfit-word-'+str(os.getuid())+'.lock');uncertain=lockpath.with_suffix('.uncertain')
 with lockpath.open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if uncertain.exists():raise DemoError('上次Word任务超时，尚不能证明已停止；请先自行退出Word，再在本地目录工具解除隔离；不会启动新更新')
  code_list='{'+','.join(literal(c) for c in dict.fromkeys([*codes,*[c.strip() for c in codes]]))+'}';names='{'+','.join(literal(n) for n in targets)+'}'
  script=f'''with timeout of 80 seconds
 tell application "Microsoft Word"
  repeat 50 times
   if exists document {literal(name)} then exit repeat
   delay 0.1
  end repeat
  set d to document {literal(name)}
  if posix full name of d is not {literal(path)} then error "document identity mismatch"
  try
   repaginate d
'''
  if update:
   script+=f'''   set allowedCodes to {code_list}
   repeat with phase from 1 to 2
    set countFields to count fields of d
    repeat with i from countFields to 1 by -1
     set c to content of field code of field i of d
     -- Exact original instructions, never all fields or external links.
     if c is in allowedCodes then
      if (phase is 1 and c contains "TOC") or (phase is 2 and c does not contain "TOC") then
       if locked of field i of d then error "selected field locked"
       set ok to update field (field i of d)
       if ok is false then error "Word field update returned false"
      end if
     end if
    end repeat
    repaginate d
   end repeat
   save d
'''
  script+=f'''   set answer to ""
   repeat with bn in {names}
    set rr to text object of bookmark (contents of bn) of d
    set rr to create range d start (start of content of rr) end ((start of content of rr) + 1)
    set a to get range information rr information type active end adjusted page number
    set b to get range information rr information type active end page number
    set answer to answer & (contents of bn) & "|" & a & "|" & b & linefeed
   end repeat
   close d saving no
   return answer
  on error msg number num
   try
    close document {literal(name)} saving no
   end try
   error msg number num
  end try
 end tell
end timeout'''
  try:
   t=time.monotonic();subprocess.run(['/usr/bin/open','-a','Microsoft Word',str(path)],check=True,capture_output=True);p=subprocess.run(['/usr/bin/osascript','-'],input=script,text=True,capture_output=True,timeout=90)
   if p.returncode:
    if '(-1712)' in p.stderr or 'document identity mismatch' in p.stderr or '(-1728)' in p.stderr:uncertain.write_text(name)
    raise DemoError('Word指定更新失败：'+p.stderr.strip()[-500:])
   pages={}
   for row in p.stdout.strip().splitlines():
    if not row:continue
    n,a,b=row.split('|');pages[n]={'adjusted':int(a),'physical':int(b)}
   if set(pages)!=set(targets) or any(v['adjusted']<1 or v['physical']<1 for v in pages.values()):raise DemoError('Word目标分页回执不完整')
   result={'raw':path.read_bytes(),'pages':pages,'seconds':round(time.monotonic()-t,3),'backend':'macOS Microsoft Word AppleScript','updated':update};shutil.rmtree(folder);return result
  except subprocess.TimeoutExpired:
   uncertain.write_text(name);raise DemoError('Word自动化超时；不代表Word已停止，结果不发布，任务副本隔离保留') from None
  except Exception:
   # Do not remove a potentially still open file or close unrelated documents.
   raise


def clear_timeout_guard():
 """Explicit operator recovery only after Word has actually exited, never kill it."""
 if subprocess.run(['/usr/bin/pgrep','-x','Microsoft Word'],capture_output=True).returncode==0:raise DemoError('Word仍在运行，不能证明超时任务已结束；请先自行关闭相关文档并退出Word')
 p=Path(tempfile.gettempdir())/('paperfit-word-'+str(os.getuid())+'.uncertain');p.unlink(missing_ok=True)

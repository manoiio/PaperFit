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
 alias=Path(str(path).removeprefix('/private'))
 identity_paths=[str(path)]+([str(alias)] if alias.resolve()==path.resolve() else [])
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
  if posix full name of d is not in {{{",".join(literal(n) for n in identity_paths)}}} then error "document identity mismatch"
  try
   repaginate d
'''
  if update:
   aliases=['PFCalc_'+uuid4().hex[:12]+'_'+str(i) for i in range(len(targets))]
   for target,alias in zip(targets,aliases):
    script+=f'   make new bookmark at d with properties {{name:{literal(alias)}, text object:text object of bookmark {literal(target)} of d}}\n'
   script+=f'''   set allowedCodes to {code_list}
   repeat with phase from 1 to 2
    set countFields to count fields of d
    repeat with i from countFields to 1 by -1
     set c to content of field code of field i of d
     -- Exact original instructions, never all fields or external links.
     if c is in allowedCodes then
      if (phase is 1 and c contains "TOC") or (phase is 2 and c does not contain "TOC") then
       if not locked of field i of d then
       if phase is 1 then
        set rs to start of content of result range of field i of d
        set foundToc to 0
        repeat with ti from 1 to count tables of contents of d
         if (start of content of text object of table of contents ti of d) < rs and (end of content of text object of table of contents ti of d) > rs then
          set foundToc to foundToc + 1
          update table of contents ti of d
         end if
        end repeat
        if foundToc is not 1 then error "selected TOC range identity mismatch"
       else
        set ok to update field (field i of d)
        if ok is false then error "Word field update returned false"
       end if
       end if
      end if
     end if
    end repeat
    if phase is 1 then
{''.join('     if not (exists bookmark '+literal(target)+' of d) then make new bookmark at d with properties {name:'+literal(target)+', text object:text object of bookmark '+literal(alias)+' of d}'+chr(10) for target,alias in zip(targets,aliases))}    end if
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
    set ls to list string of list format of rr
    set ll to list level number of list format of rr
    set answer to answer & (contents of bn) & "|" & a & "|" & b & "|" & ll & "|" & ls & linefeed
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
   t=time.monotonic();subprocess.run(['/usr/bin/open','-g','-a','Microsoft Word',str(path)],check=True,capture_output=True);p=subprocess.run(['/usr/bin/osascript','-'],input=script,text=True,capture_output=True,timeout=90)
   if p.returncode:
    if '(-1712)' in p.stderr or 'document identity mismatch' in p.stderr or '(-1728)' in p.stderr:uncertain.write_text(name)
    raise DemoError('Word指定更新失败：'+p.stderr.strip()[-500:])
   pages={};numbering={}
   for row in p.stdout.strip().splitlines():
    if not row:continue
    n,a,b,ll,ls=row.split('|',4);pages[n]={'adjusted':int(a),'physical':int(b)}
    if ls:numbering[n]={'level':int(ll),'display':ls}
   if set(pages)!=set(targets) or any(v['adjusted']<1 or v['physical']<1 for v in pages.values()):raise DemoError('Word目标分页回执不完整')
   result={'raw':path.read_bytes(),'pages':pages,'numbering':numbering,'seconds':round(time.monotonic()-t,3),'backend':'macOS Microsoft Word AppleScript','updated':update};shutil.rmtree(folder);return result
  except subprocess.TimeoutExpired:
   uncertain.write_text(name);raise DemoError('Word自动化超时；不代表Word已停止，结果不发布，任务副本隔离保留') from None
  except Exception:
   # Do not remove a potentially still open file or close unrelated documents.
   raise


def clear_timeout_guard():
 """Explicit operator recovery only after Word has actually exited, never kill it."""
 if subprocess.run(['/usr/bin/pgrep','-x','Microsoft Word'],capture_output=True).returncode==0:raise DemoError('Word仍在运行，不能证明超时任务已结束；请先自行关闭相关文档并退出Word')
 p=Path(tempfile.gettempdir())/('paperfit-word-'+str(os.getuid())+'.uncertain');p.unlink(missing_ok=True)


def export_pdf(raw,destination):
 """Export an owned, field-frozen copy. Never save a DOCX or touch other documents.

 Non-PAGE fields are locked in the export-only snapshot BEFORE Word opens it.
 PAGE and automatic list labels are display calculations, not DOCX cache writes.
 The same cross-process gate/timeout quarantine as the field calculator is used.
 """
 from .package import Package,parse,q,NS,write_new
 from lxml import etree as ET
 if not available():raise DemoError('本机没有可用的macOS Microsoft Word PDF后端')
 dest=Path(destination).resolve()
 if dest.exists():raise DemoError('PDF输出已存在，不覆盖原成果')
 root=Path(tempfile.gettempdir()).resolve()/'paperfit-word-export';root.mkdir(exist_ok=True)
 folder=root/('PaperFit-'+uuid4().hex);folder.mkdir();path=folder/('pf-'+uuid4().hex+'.docx');path.write_bytes(raw)
 try:
  pkg=Package(path);replacements={};locked=0;page=0;page_codes=set()
  if pkg.signed or any(n.startswith(('word/embeddings/','word/activeX/')) for n in pkg.parts):raise DemoError('签名、嵌入对象或活动控件暂不进入Word PDF；原DOCX保留')
  # Avoid opening arbitrary external links, attached templates or active content.
  for name,data in pkg.parts.items():
   if name.endswith('.rels') and any(e.get('TargetMode')=='External' for e in parse(data)):raise DemoError('Word输出暂不打开含外部关系的文件；DOCX仍可下载')
   if name.endswith('.xml') and name.startswith('word/'):
    tree=parse(data);changed=False
    stack=[]
    for e in tree.iter():
     if e.tag==q('fldChar') and e.get(q('fldCharType'))=='begin':stack.append([e,'',False])
     elif e.tag==q('instrText') and stack:stack[-1][1]+=e.text or ''
     elif e.tag==q('fldChar') and e.get(q('fldCharType'))=='separate' and stack:
      if stack[-1][2]:raise DemoError('重复域分隔符，未打开Word')
      stack[-1][2]=True
      if re_unsafe_field(stack[-1][1]):raise DemoError('Word输出含拆分的外部/动态域，未打开')
      if not simple_page_code(stack[-1][1]):stack[-1][0].set(q('fldLock'),'true');changed=True;locked+=1
      else:page+=1;page_codes.add(stack[-1][1])
     elif e.tag==q('fldChar') and e.get(q('fldCharType'))=='end':
      if not stack or not stack[-1][2]:raise DemoError('域边界/缓存分隔不完整，未打开Word')
      stack.pop()
     elif e.tag==q('fldChar') and e.get(q('fldCharType'))=='separate':raise DemoError('游离域分隔符，未打开Word')
     if e.tag==q('instrText') and re_unsafe_field(e.text or ''):raise DemoError('Word输出含外部/动态取值域，未打开；DOCX保持')
     if e.tag==q('fldSimple'):
      code=e.get(q('instr'),'')
      if re_unsafe_field(code):raise DemoError('Word输出含外部/动态取值域，未打开')
      if simple_page_code(code):page+=1;page_codes.add(code)
      else:e.set(q('fldLock'),'true');changed=True;locked+=1
    if stack:raise DemoError('域边界断裂，未打开Word')
    if changed:replacements[name]=ET.tostring(tree,xml_declaration=True,encoding='UTF-8',standalone=True)
  from io import BytesIO
  import zipfile
  output=BytesIO()
  with zipfile.ZipFile(output,'w') as z:
   z.comment=pkg.comment
   for info in pkg.infos:z.writestr(info,replacements.get(info.filename,pkg.parts[info.filename]))
  export_raw=output.getvalue() if replacements else raw
 except Exception:
  shutil.rmtree(folder,ignore_errors=True);raise
 path.write_bytes(export_raw);identity=[str(path)]
 alias=str(path).removeprefix('/private')
 if Path(alias).resolve()==path:identity.append(alias)
 lockpath=Path(tempfile.gettempdir())/('paperfit-word-'+str(os.getuid())+'.lock');uncertain=lockpath.with_suffix('.uncertain')
 # Word macOS cannot write a newly created arbitrary subfolder without a
 # sandbox prompt. Use an unpredictable, new flat file in the system temp folder.
 pdf=Path('/private/tmp')/('PaperFit-'+uuid4().hex+'.pdf');name=path.name
 if pdf.exists() or pdf.is_symlink():raise DemoError('PDF临时名称冲突')
 allowed_pages='{'+','.join(literal(c) for c in sorted({v for c in page_codes for v in (c,c.strip(),' '+c.strip()+' ')}))+'}'
 script=f'''with timeout of 80 seconds
 tell application "Microsoft Word"
  repeat 100 times
   if exists document {literal(name)} then exit repeat
   delay 0.1
  end repeat
  set d to document {literal(name)}
  if posix full name of d is not in {{{','.join(literal(n) for n in identity)}}} then error "document identity mismatch"
  try
   if print field codes of settings then error "Word configured to print field codes; export refused"
   if print hidden text of settings then error "Word prints hidden text; export refused"
   if not print drawing objects of settings then error "Word hides drawings in print; export refused"
   set allowedPages to {allowed_pages}
   set beforeResults to ""
   set pageFields to 0
   repeat with i from 1 to count fields of d
    set c to content of field code of field i of d
    if c is in allowedPages then
     set pageFields to pageFields + 1
    else
     set beforeResults to beforeResults & c & "|" & (content of result range of field i of d) & linefeed
    end if
   end repeat
   repaginate d
   save as d file name {literal(pdf)} file format format PDF add to recent files false
   set afterResults to ""
   repeat with i from 1 to count fields of d
    set c to content of field code of field i of d
    if c is not in allowedPages then set afterResults to afterResults & c & "|" & (content of result range of field i of d) & linefeed
   end repeat
   if beforeResults is not afterResults then error "unselected field display changed"
   close d saving no
   return pageFields as text
  on error msg number num
   try
    close document {literal(name)} saving no
   end try
   error msg number num
  end try
 end tell
end timeout'''
 with lockpath.open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if uncertain.exists():
   shutil.rmtree(folder,ignore_errors=True)
   raise DemoError('前次Word任务仍未证明停止，暂不启动PDF导出')
  t=time.monotonic()
  try:
   subprocess.run(['/usr/bin/open','-g','-a','Microsoft Word',str(path)],check=True,capture_output=True)
   result=subprocess.run(['/usr/bin/osascript','-'],input=script,text=True,capture_output=True,timeout=90)
   if result.returncode:
    if any(x in result.stderr for x in ('(-1712)','identity mismatch','(-1728)','(-609)')):uncertain.write_text(name)
    raise DemoError('Word PDF导出失败：'+result.stderr.strip()[-400:])
   if path.read_bytes()!=export_raw:raise DemoError('Word改写了导出专用DOCX，拒绝接入PDF')
   data=pdf.read_bytes()
   if not data.startswith(b'%PDF-') or len(data)>100*1024*1024:raise DemoError('Word未生成有效有界PDF')
   write_new(dest,data)
   return {'backend':'Microsoft Word / macOS PDF','source_sha256':sha256(raw),'export_snapshot_sha256':sha256(export_raw),'pdf_sha256':sha256(data),'seconds':round(time.monotonic()-t,3),'non_page_fields_frozen':locked,'main_page_fields':int(result.stdout.strip()),'non_page_display_unchanged_during_export':True,'docx_saved':False,'limitation':'非PAGE域在导出副本中锁定，未刷新目录/引用。未锁定PAGE及自动编号由Word计算显示；PDF不证明原DOCX缓存新鲜或全文合格。'}
  except subprocess.TimeoutExpired:
   uncertain.write_text(name);raise DemoError('Word导出超时；可能仍在执行，任务隔离，DOCX仍可下载') from None
  finally:
   if not uncertain.exists():
    shutil.rmtree(folder,ignore_errors=True);pdf.unlink(missing_ok=True)


def re_unsafe_field(code):
 import re
 return bool(re.search(r'\b(?:DDE|DDEAUTO|INCLUDETEXT|INCLUDEPICTURE|LINK|DATABASE|IMPORT|AUTOTEXT|MACROBUTTON)\b',code,re.I))


def simple_page_code(code):
 import re
 return bool(re.fullmatch(r'\s*(?i:PAGE)(?:\s+\\\*\s+(?:MERGEFORMAT|Arabic|ROMAN|roman|ALPHABETIC|alphabetic))*\s*',code))

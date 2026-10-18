"""Word PDF exported once; bounded page batches reuse the exact hashed PDF."""
from pathlib import Path
from uuid import uuid4
from datetime import datetime,timezone
import json,subprocess,time,plistlib
from .package import Package,DemoError,sha256,write_new
from .preview import RUNTIME,valid_artifacts
VERSION='word-pdf-1'
BINS=RUNTIME/'native/poppler/poppler/bin'

def configuration():
 from .word_native import available
 if not available():raise DemoError('本机Word原生输出不可用，可明确选择LibreOffice预览')
 plist=Path('/Applications/Microsoft Word.app/Contents/Info.plist')
 if not all((BINS/n).is_file() for n in ('pdfinfo','pdftoppm')):raise DemoError('缺少本地PDF页图工具')
 font=[]
 from .preview import FONT_DIRS
 for folder in FONT_DIRS:
  for p in Path(folder).rglob('*'):
   try:
    if p.is_file():s=p.stat();font.append((str(p),s.st_size,s.st_mtime_ns))
   except OSError:pass
 data={'version':VERSION,'engine':'word','renderer':'Microsoft Word / macOS PDF','renderer_version':plistlib.loads(plist.read_bytes()).get('CFBundleShortVersionString','unknown'),'word_app_sha256':sha256(plist.read_bytes()),'dpi':110,'max_pages':10,'batch_pages':10,'max_cached_pages':50,'max_image_bytes':100*1024*1024,'max_document_pages':2000,'font_environment_sha256':sha256(json.dumps(sorted(set(font))).encode()),'implementation_sha256':sha256(Path(__file__).read_bytes()+Path(__file__).with_name('word_native.py').read_bytes()),'poppler_sha256':sha256((BINS/'pdftoppm').read_bytes()),'timeout_seconds':90}
 return data,sha256(json.dumps(data,sort_keys=True).encode())

def batch(meta,page):
 if type(page) is not int or not 1<=page<=meta['page_count']:raise DemoError('页码超出实际PDF范围')
 if not valid_artifacts(meta):raise DemoError('PDF或已有页图哈希不匹配，请重新生成')
 pdf=Path(meta['pdf']);folder=pdf.parent;start=((page-1)//10)*10+1;end=min(start+9,meta['page_count'])
 out=dict(meta);out['page_map']=dict(meta.get('page_map',{str(i):p for i,p in enumerate(meta['pages'],1)}));out['artifact_sha256']=dict(meta['artifact_sha256'])
 if all(str(i) in out['page_map'] for i in range(start,end+1)):return out
 target=folder/('batch-'+uuid4().hex);target.mkdir()
 try:
  subprocess.run([str(BINS/'pdftoppm'),'-f',str(start),'-l',str(end),'-r','110','-png',str(pdf),str(target/'page')],capture_output=True,check=True,timeout=60,env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8'})
  paths=sorted(target.glob('page-*.png'),key=lambda p:int(p.stem.split('-')[-1]))
  if len(paths)!=end-start+1 or sum(p.stat().st_size for p in paths)>100*1024*1024:raise DemoError('页图批次不完整或超过100MB')
  for i,p in zip(range(start,end+1),paths):out['page_map'][str(i)]=str(p);out['artifact_sha256'][str(p)]=sha256(p.read_bytes())
  out['retired_artifacts']=[]
  out['batch_order']=[n for n in meta.get('batch_order',[]) if n!=start]+[start]
  while len(out['page_map'])>50 or sum(Path(p).stat().st_size for p in out['page_map'].values())>100*1024*1024:
   if len(out['batch_order'])<=1:raise DemoError('单批页图超过缓存边界')
   retired=out['batch_order'].pop(0)
   for number in range(retired,retired+10):
    old=out['page_map'].pop(str(number),None)
    if old:
     owned=Path(old)
     if owned.is_symlink() or owned.parent.parent.resolve()!=folder.resolve() or not owned.parent.name.startswith('batch-'):raise DemoError('页图所有权不符，未清理')
     out['retired_artifacts'].append(old);out['artifact_sha256'].pop(old,None)
  out['pages']=[out['page_map'][str(i)] for i in sorted(map(int,out['page_map']))];out['generated_page_numbers']=sorted(map(int,out['page_map']));return out
 except Exception as exc:
  import shutil
  shutil.rmtree(target,ignore_errors=True)
  if isinstance(exc,DemoError):raise
  raise DemoError('PDF页图生成失败；已生成的PDF/DOCX保持') from None

def render_preview(input_path,job_root,*,context=None,exporter=None):
 from .word_native import export_pdf
 started=time.monotonic();pkg=Package(input_path);config,cfg=configuration();job=Path(job_root).resolve()/('word-preview-'+uuid4().hex);job.mkdir(parents=True,exist_ok=False)
 pdf=job/'document.pdf';receipt=(exporter or export_pdf)(pkg.raw,pdf)
 if Path(input_path).read_bytes()!=pkg.raw or receipt['source_sha256']!=pkg.hash or receipt['pdf_sha256']!=sha256(pdf.read_bytes()):raise DemoError('Word PDF源文件绑定失败')
 try:
  info=subprocess.run([str(BINS/'pdfinfo'),str(pdf)],capture_output=True,text=True,check=True,timeout=10,env={'PATH':'/usr/bin:/bin','LANG':'en_US.UTF-8'}).stdout
  count=int(next(line.split(':',1)[1] for line in info.splitlines() if line.startswith('Pages:')))
 except (OSError,ValueError,StopIteration,subprocess.SubprocessError):raise DemoError('Word PDF页数读取失败') from None
 if not 1<=count<=2000:raise DemoError('Word PDF页数不在1–2000页边界内')
 meta={'document_sha256':pkg.hash,'render_config_sha256':cfg,'generated_at':datetime.now(timezone.utc).isoformat(),'renderer':config['renderer'],'engine':'word','renderer_version':config['renderer_version'],'page_count':count,'preview_range':[1,min(count,10)],'fonts':[],'font_notes':['Word按本机已安装字体显示；未将字体替代写回DOCX。'+receipt['limitation']],'context':context or {},'fallback_odt':False,'input_bytes_unchanged':True,'limitation':receipt['limitation'],'pages':[],'page_map':{},'pdf':str(pdf),'artifact_sha256':{str(pdf):sha256(pdf.read_bytes())},'word_export':receipt}
 # valid_artifacts also requires at least one page; bootstrap before first batch.
 stub=job/'bootstrap.png';stub.write_bytes(b'bootstrap');meta['pages']=[str(stub)];meta['artifact_sha256'][str(stub)]=sha256(stub.read_bytes());meta=batch(meta,1);meta['artifact_sha256'].pop(str(stub));stub.unlink();meta['pages']=[meta['page_map'][str(i)] for i in sorted(map(int,meta['page_map']))];meta['seconds']=round(time.monotonic()-started,3)
 write_new(job/'preview.json',json.dumps(meta,ensure_ascii=False,indent=2).encode());return meta


def retire_pages(meta):
 """Only after the owning session publishes the new map, never in the worker."""
 folder=Path(meta['pdf']).parent.resolve();done=deferred=0
 for old in meta.pop('retired_artifacts',[]):
  p=Path(old)
  if p.is_symlink() or p.parent.parent.resolve()!=folder or not p.parent.name.startswith('batch-'):
   deferred+=1;continue
  try:
   p.unlink(missing_ok=True);done+=1
   try:p.parent.rmdir()
   except OSError:pass
  except OSError:deferred+=1
 meta['page_cleanup']={'retired_files':done,'deferred_until_task_cleanup':deferred}
 return meta


def discard_batch(snapshot,result):
 """A cancelled batch removes only newly created PNGs, never its parent PDF."""
 folder=Path(snapshot['pdf']).parent.resolve()
 for name in set(result.get('artifact_sha256',{}))-set(snapshot['artifact_sha256']):
  p=Path(name)
  if p.suffix!='.png' or p.is_symlink() or p.parent.parent.resolve()!=folder or not p.parent.name.startswith('batch-'):raise DemoError('取消批次所有权不符，暂缓清理')
  p.unlink(missing_ok=True)
  try:p.parent.rmdir()
  except OSError:pass

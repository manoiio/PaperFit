"""Allowlisted public starter materials only; no recursive repository archiving."""
from pathlib import Path
from io import BytesIO
import json,hashlib,zipfile,argparse
ROOT=Path(__file__).resolve().parents[1]
FILES={
 'basic':['使用说明.md','原稿.docx','排版要求.json','独立错误清单.json','修正版.docx','修改摘要.md','报告.html','独立核对.json'],
 'complete':['使用说明.md','原稿.docx','排版要求.json','独立预期.json','修正版.docx','Word页面.pdf','修改摘要.md','报告.html','独立核对.json'],
}
def build(root=ROOT/'samples/start-here'):
 root=Path(root).resolve();buf=BytesIO();manifest=[]
 with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
  for folder,names in FILES.items():
   for name in names:
    path=root/folder/name
    if path.is_symlink() or path.resolve().parent!=root/folder:raise ValueError('样例文件边界不合法')
    data=path.read_bytes()
    if len(data)>20*1024*1024:raise ValueError('单文件超过公开样例预算')
    archive=folder+'/'+name;info=zipfile.ZipInfo(archive,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
    manifest.append({'file':archive,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
  z.writestr(zipfile.ZipInfo('文件与哈希清单.json',(2026,1,1,0,0,0)),json.dumps(manifest,ensure_ascii=False,indent=2).encode())
 if buf.tell()>30*1024*1024:raise ValueError('样例包超过30MB预算')
 return buf.getvalue()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('xb') as f:f.write(build())
 print('已生成公开样例包：'+str(out))

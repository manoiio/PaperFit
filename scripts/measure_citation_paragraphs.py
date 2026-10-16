"""Local proof/full-check costs; generated load remains synthetic and offline."""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import sys,json,time,statistics,platform,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.package import Package,q
from core import check_document
from core.citation_paragraphs import build
from core.table_text import rebind
from scripts.reproduce_citation_paragraph_demo import session

def median(fn):
 times=[]
 for _ in range(3):
  t=time.perf_counter();fn();times.append(time.perf_counter()-t)
 return {'runs':times,'median':statistics.median(times)}
def measure():
 with TemporaryDirectory() as td:
  s=session(Path(td)/'web');m=s._rules_arguments()['classification_manifest'];pkg=Package(s.input_path)
  short={'proof':median(lambda:build(pkg,m)),'check':median(lambda:check_document(s.input_path,s.confirmed,**s._rules_arguments()))}
  for label,count in [('long',400)]:
   p=Package(s.input_path);body=p.root.find(q('body'));source=p.paragraphs[2];sect=body.find(q('sectPr'));new=[]
   for i in range(count):
    e=deepcopy(source);body.insert(body.index(sect) if sect is not None else len(body),e);new.append(e)
   path=Path(td)/'long.docx';path.write_bytes(p.bytes(True));p=Package(path);mm=deepcopy(m);mm['input_sha256']=p.hash;rebind(mm,p.hash);mm['paragraph_types'].update({str(i):'body' for i in range(len(pkg.paragraphs)+1,len(p.paragraphs)+1)})
   start=len(pkg.paragraphs)+1
   for n in range(start,len(p.paragraphs)+1):mm['citation_scope']['scan'].append(n);mm['citation_scope']['objects'][f'c:{n}:6:9']='citation'
   long={'paragraph_count':len(p.paragraphs),'confirmed_citation_groups':len(mm['citation_scope']['objects']),'proof':median(lambda:build(p,mm)),'check':median(lambda:check_document(path,mode='academic',classification_manifest=mm,custom_rules_path=s.custom_rules_path))}
 return {'python':platform.python_version(),'platform':platform.system(),'repeats':3,'unit':'seconds','synthetic':short,'400_added_body_paragraphs':long,'API_requests':0,'automatic_renders':0,'boundary':'本地函数成本，不是浏览器等待；没有可比旧判定算法，不宣称提速百分比'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();result=measure();Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))

"""Local timings and old/new coverage on exactly the same authored source; no network."""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import json,time,statistics,sys,argparse,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import check_document
from core.package import Package,q,sha256
from scripts.reproduce_hyperlink_demo import session,selection,S

def measure():
 with TemporaryDirectory() as d:
  s=session(Path(d)/'web');read=[];rehearse=[];adopt=[];views=[]
  for i in range(3):
   start=time.perf_counter();r=check_document(s.input_path,s.confirmed,**s._rules_arguments());read.append(time.perf_counter()-start)
   s.set_selection(selection(s));start=time.perf_counter();assert s.rehearse(),s.rehearsal_error;rehearse.append(time.perf_counter()-start)
   start=time.perf_counter();assert s.rehearsal_view();views.append(time.perf_counter()-start)
   start=time.perf_counter();assert s.adopt_rehearsal(s.rehearsal['id'],acknowledged=True);adopt.append(time.perf_counter()-start)
   s.cancel_rehearsal();s.result=None
  p=Package(S/'errors.docx');body=p.root.find(q('body'));sample=p.paragraphs[7];section=body.find(q('sectPr'))
  for i in range(100):body.insert(body.index(section),deepcopy(sample))
  path=Path(d)/'long.docx';path.write_bytes(p.bytes(True));pp=Package(path);manifest={'input_sha256':pp.hash,'body_paragraphs':list(range(7,len(pp.paragraphs)+1)),'confirmation':'合成多链接负载，非准确率样本'};long=[]
  for _ in range(3):
   start=time.perf_counter();rr=check_document(path,manifest);long.append(time.perf_counter()-start)
  return {'environment':'macOS arm64 Python '+sys.version.split()[0],'source_bytes':len(s.input_bytes),'source_top_paragraphs':13,'qualified_link_text_runs':r['coverage']['hyperlink_text']['supported_text_locators'],'new_link_finding_records':r['coverage']['hyperlink_text']['finding_count'],'full_summary':r['summary'],'check_seconds':read,'rehearse_seconds':rehearse,'read_preview_seconds':views,'adopt_with_revalidation_seconds':adopt,'medians':{k:statistics.median(v) for k,v in [('check',read),('rehearse',rehearse),('view',views),('adopt',adopt),('long',long)]},'long_document':{'top_paragraphs':len(pp.paragraphs),'links':len(list(pp.root.iter(q('hyperlink')))),'bytes':path.stat().st_size,'check_seconds':long,'findings':len(rr['findings'])},'fix_calls_per_preview':1,'fix_calls_per_adoption':0,'API_calls':0,'automatic_renders':0,'not_a_speedup_or_accuracy_claim':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();path=Path(a.output)
 if path.exists():raise SystemExit('Refusing existing measurement')
 path.write_text(json.dumps(measure(),ensure_ascii=False,indent=2)+'\n')

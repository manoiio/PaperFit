"""Portable three-run local measurement. No network, preview or private fixtures."""
from pathlib import Path
import argparse,json,platform,sys,tempfile
from statistics import median
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.reproduce_scope_demo import session,old_check

def measure():
    rows=[]
    with tempfile.TemporaryDirectory() as root:
        for i in range(3):
            old=session(Path(root)/('old-'+str(i)));new=session(Path(root)/('new-'+str(i)))
            t=perf_counter();old_check(old);old_time=perf_counter()-t
            t=perf_counter();pre=new.scope_preflight();pre_time=perf_counter()-t
            t=perf_counter();assert new.confirm_scopes_and_check(pre['signature'],acknowledged=True),new.error;new_time=perf_counter()-t
            assert old.report['findings']==new.report['findings']
            rows.append({'old_confirm_and_check_seconds':old_time,'preflight_seconds':pre_time,'unified_confirm_and_check_seconds':new_time})
    return {'python':platform.python_version(),'platform':platform.platform(),'document_bytes':(ROOT/'samples/phase26/composite.docx').stat().st_size,
            'paragraphs':19,'tables':1,'sections':2,'notes':6,'runs':rows,'medians':{k:median(r[k] for r in rows) for k in rows[0]},'api_requests':0,
            'boundary':'本地函数计时；不含人工阅读和浏览器等待，不代表引擎提速。'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise SystemExit('Refusing existing file')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(measure(),ensure_ascii=False,indent=2)+'\n')

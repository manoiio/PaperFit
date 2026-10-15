"""Three matched local iterations; no network, renderer or historical output dependency."""
import sys,json,time,tempfile,statistics,argparse,platform
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.reproduce_scope_demo import session,old_check
from scripts.reproduce_rehearsal_demo import KEY

def run(output):
 p=Path(output)
 if p.exists():raise SystemExit('Refusing existing output')
 rows=[]
 with tempfile.TemporaryDirectory() as root:
  for i in range(3):
   a=session(Path(root)/f'direct-{i}');b=session(Path(root)/f'rehearsal-{i}')
   for s in (a,b):old_check(s);s.set_selection([KEY])
   import web.session as api
   with patch('web.session.fix_document',wraps=api.fix_document) as f:
    start=time.perf_counter();assert a.generate(),a.error;direct=time.perf_counter()-start
    start=time.perf_counter();assert b.rehearse(),b.rehearsal_error;rehearse=time.perf_counter()-start
    times=[]
    for _ in range(3):
     start=time.perf_counter();assert b.rehearsal_view();times.append(time.perf_counter()-start)
    start=time.perf_counter();assert b.adopt_rehearsal(b.rehearsal['id'],acknowledged=True),b.rehearsal_error;adopt=time.perf_counter()-start
    assert f.call_count==2 and a.downloads()['fixed.docx']==b.downloads()['fixed.docx']
   rows.append({'direct_full_round_seconds':direct,'rehearsal_seconds':rehearse,'repeat_view_median_seconds':statistics.median(times),'adopt_seconds':adopt,'fix_calls_direct':1,'fix_calls_rehearsal':1,'fix_calls_adopt':0,'rounds_each':1,'remaining_rehearsal_directories':len(list(b.task_dir.glob('rehearsal-*')))})
 data={'environment':{'os':platform.system(),'architecture':platform.machine(),'python':platform.python_version()},'runs':rows,
       'medians_seconds':{k:statistics.median(r[k] for r in rows) for k in rows[0] if k.endswith('_seconds')},
       'API_requests':0,'automatic_renders':0,'note':'相同源文件、规则、范围和选择；预演前置计算并增加绑定重验，不宣称总耗时缩短。'}
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)

"""Three matched local runs; engine timings are not browser or human interaction time."""
import argparse,json,tempfile,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.reproduce_plan_demo import run
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output)
 if out.exists():raise SystemExit('Refusing existing output')
 with tempfile.TemporaryDirectory() as tmp:
  runs=[]
  for i in range(3):
   root=Path(tmp)/str(i);run(root);runs.append(json.loads((root/'timings.json').read_text()))
 data={'environment':'Python '+sys.version.split()[0],'runs':runs,'medians_seconds':{k:statistics.median(r[k] for r in runs) for k in ('manual_engine_two_round_seconds','plan_rehearsal_seconds','view_median_seconds','adoption_with_revalidation_seconds')},'note':'每次采用真实重新校验、0次完整修正；计算两步不变，没有声称端到端提速。'}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

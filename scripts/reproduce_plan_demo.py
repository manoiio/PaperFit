"""Portable legal manual two-round versus actual plan; no work, API or renderer dependency."""
from pathlib import Path
from copy import deepcopy
import sys,json,argparse,time,statistics
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.package import Package,NS,q,sha256
from core.citations import inventory
from core import fix_document,check_document
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1];SAMPLE=ROOT/'samples/phase28'
def session(root,*,checked=True):
 ds=json.loads((SAMPLE/'scope.json').read_text());s=WebSession(root);s.set_mode('academic');assert s.load((SAMPLE/'errors.docx').read_bytes(),'分步计划合成论文.docx'),s.error
 s.set_types(ds['roles']);s.exclude_materials([18],ds['material_exclusions']['18']);s.enable_citations(True)
 d=deepcopy(s.citation_draft);d['objects']={r['id']:'excluded' if r['text']=='[8]' else 'citation' for r in s.citation_inventory()['objects']};s.edit_citations(d)
 if checked:
  s.confirm_citations()
  assert s.confirm_and_check(),s.error
 return s

def selection(s):
 ds=json.loads((SAMPLE/'scope.json').read_text());positions={(r['paragraph'],r['start'],r['end']) for r in ds['selected_citations']}
 return [f['key'] for f in s.eligible() if (f['rule_id'] in ('R03','R04','R05') and f['locator'].get('paragraph') in (3,4) and (f['locator'].get('run')==1 or f['rule_id']=='R05')) or (f['rule_id']=='R33' and (f['locator'].get('paragraph'),f['locator'].get('start'),f['locator'].get('end')) in positions)]

def run(output):
 output=Path(output)
 if output.exists():raise SystemExit('Refusing existing output directory')
 output.mkdir(parents=True);s=session(output/'session');s.set_selection(selection(s));p=s.correction_plan();assert p['two_steps'] and not p['blocked']
 from core.package import DemoError
 try:fix_document(s.input_path,output/'illegal.docx',s.confirmed,selected_keys=s.selected,**s._rules_arguments())
 except DemoError:pass
 else:raise AssertionError('Original same-round conflict guard bypassed')
 manual_start=time.perf_counter();one=fix_document(s.input_path,output/'manual-step-1.docx',s.confirmed,selected_keys=p['steps'][0]['keys'],**s._rules_arguments())
 mid=check_document(one['output'],one['output_body_manifest'],mode=s.mode,classification_manifest=one['output_classification_manifest'])
 # Independent literal expected offsets, not planner resolver or old finding keys.
 ds=json.loads((SAMPLE/'scope.json').read_text());coords={(x['paragraph'],x['start'],x['end']) for x in ds['selected_citations']}
 keys=[f['key'] for f in mid['findings'] if f['rule_id']=='R33' and f['status']=='problem' and (f['locator']['paragraph'],f['locator']['start'],f['locator']['end']) in coords]
 two=fix_document(one['output'],output/'manual-step-2.docx',one['output_body_manifest'],selected_keys=keys,mode=s.mode,classification_manifest=one['output_classification_manifest']);manual_time=time.perf_counter()-manual_start
 import web.session as api
 with patch('web.session.fix_document',wraps=api.fix_document) as fix:
  start=time.perf_counter();assert s.rehearse_plan(),s.rehearsal_error;preview=time.perf_counter()-start;v=s.rehearsal_view();identifier=s.rehearsal['id'];assert s.generation_count==0 and not s.history and s.result is None
  views=[]
  for _ in range(3):
   start=time.perf_counter();assert s.rehearsal_view();views.append(time.perf_counter()-start)
  assert fix.call_count==2
  start=time.perf_counter();assert s.adopt_plan(identifier,acknowledged=True),s.rehearsal_error;adopt=time.perf_counter()-start
  assert s.adopt_plan(identifier,acknowledged=True);assert fix.call_count==2
 steps=s.plan_step_downloads();assert steps[0]['fixed.docx']==Path(one['output']).read_bytes() and steps[1]['fixed.docx']==Path(two['output']).read_bytes()
 assert s.current_round==0 and s.generation_count==len(s.history)==2
 from scripts.verify_plan_output import verify
 proof=verify(s.input_path,Path(s.history[0]['result']['output']),Path(s.result['output']))
 for i,x in enumerate(steps,1):
  from web.reading_report import clean
  from core.report import markdown,modification_markdown
  rr=clean(s.history[i-1]['result']);rr['output']=f'step-{i}.docx';rr['after']['input']=rr['output'];rr['before']['input']='errors.docx' if i==1 else 'step-1.docx'
  (output/f'step-{i}.docx').write_bytes(x['fixed.docx']);(output/f'step-{i}-changes.md').write_text(modification_markdown(rr));(output/f'step-{i}-recheck.md').write_text(markdown(rr['after']))
 (output/'result.zip').write_bytes(s.result_package());(output/'project.zip').write_bytes(s.prepare_project());(output/'scope.json').write_text(json.dumps(s.result['output_classification_manifest'],ensure_ascii=False,indent=2)+'\n')
 from web.reading_report import clean
 (output/'plan.json').write_text(json.dumps(clean(s.result['plan']),ensure_ascii=False,indent=2)+'\n');(output/'independent-check.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 for n,b in s.prepare_reading_export().items():(output/n).write_bytes(b)
 timings={'manual_engine_two_round_seconds':manual_time,'plan_rehearsal_seconds':preview,'view_seconds':views,'view_median_seconds':statistics.median(views),'adoption_with_revalidation_seconds':adopt,'manual_engine_calls':2,'plan_engine_calls':2,'adoption_engine_calls':0,'formal_rounds':2,'current_input_round':0,'remaining_rehearsal_directories':len(list(s.task_dir.glob('rehearsal-*'))),'API_requests':0,'automatic_renders':0,'note':'预演增加前置计算；采用重新校验，不再修正。函数时间不等于人工操作时间。'}
 (output/'timings.json').write_text(json.dumps(timings,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'proof':proof,'timings':timings},ensure_ascii=False,indent=2));return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)

"""Portable explicit-v2 two-step run, manual equivalent and independent verification."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import sys,json,argparse,time,statistics
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.citations import upgrade_template
from core import check_document,fix_document
from core.package import Package
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1];SAMPLE=ROOT/'samples/phase30'
def session(root,checked=True,v2=True):
 ds=json.loads((SAMPLE/'scope.json').read_text());s=WebSession(root);s.set_mode('academic');assert s.load((SAMPLE/'errors.docx').read_bytes(),'组合区间引文合成论文.docx'),s.error
 s.set_types(ds['roles']);s.exclude_materials([18],ds['material_exclusions']['18']);s.enable_citations(True)
 d=deepcopy(s.citation_draft)
 if v2:d['template']=upgrade_template(d['template'])
 s.edit_citations(d);d=deepcopy(s.citation_draft);d['objects']={r['id']:'excluded' if r['text']=='[8]' or r['paragraph']==6 else 'citation' for r in s.citation_inventory()['objects']};d.update(complete=True,references_complete=True);s.edit_citations(d)
 if checked:s.confirm_citations();assert s.confirm_and_check(),s.error
 return s

def selection(s):return [f['key'] for f in s.eligible() if f['rule_id']=='R33' or f['rule_id'] in ('R03','R05') and f['locator'].get('paragraph') in (3,4)]
def run(output):
 output=Path(output)
 if output.exists():raise SystemExit('Refusing existing directory')
 output.mkdir(parents=True);s=session(output/'session');s.set_selection(selection(s));draft=s.correction_plan();assert draft['two_steps'] and not draft['blocked']
 t=time.perf_counter();one=fix_document(s.input_path,output/'manual-1.docx',s.confirmed,selected_keys=draft['steps'][0]['keys'],**s._rules_arguments())
 fresh=check_document(one['output'],one['output_body_manifest'],mode=s.mode,classification_manifest=one['output_classification_manifest']);literal=json.loads((SAMPLE/'scope.json').read_text())['selected_citations'];coords={(x['paragraph'],x['start'],x['end']) for x in literal};keys=[f['key'] for f in fresh['findings'] if f['rule_id']=='R33' and f['fixable'] and (f['locator']['paragraph'],f['locator']['start'],f['locator']['end']) in coords]
 two=fix_document(one['output'],output/'manual-2.docx',one['output_body_manifest'],mode=s.mode,classification_manifest=one['output_classification_manifest'],selected_keys=keys);manual=time.perf_counter()-t
 import web.session as api
 with patch('web.session.fix_document',wraps=api.fix_document) as engine:
  t=time.perf_counter();assert s.rehearse_plan(),s.rehearsal_error;rehearsal=time.perf_counter()-t;assert engine.call_count==2
  t=time.perf_counter();assert s.adopt_plan(s.rehearsal['id'],acknowledged=True),s.rehearsal_error;adopt=time.perf_counter()-t;assert engine.call_count==2
 for i,(h,m) in enumerate(zip(s.history,(one,two)),1):
  assert Path(h['result']['output']).read_bytes()==Path(m['output']).read_bytes()
  (output/f'step-{i}.docx').write_bytes(Path(h['result']['output']).read_bytes())
  from core.report import markdown,modification_markdown
  from web.reading_report import clean
  rr=clean(h['result']);rr['output']=f'step-{i}.docx';rr['before']['input']='errors.docx' if i==1 else 'step-1.docx';rr['after']['input']=rr['output']
  (output/f'step-{i}-changes.md').write_text(modification_markdown(rr));(output/f'step-{i}-recheck.md').write_text(markdown(rr['after']))
 from scripts.verify_citation_groups_output import verify
 proof=verify(SAMPLE/'errors.docx',output/'step-1.docx',output/'step-2.docx')
 (output/'independent-check.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');(output/'relations.json').write_text(json.dumps(s.result['after']['citations'],ensure_ascii=False,indent=2)+'\n');(output/'final.types.json').write_text(json.dumps(s.result['output_classification_manifest'],ensure_ascii=False,indent=2)+'\n')
 (output/'result.zip').write_bytes(s.result_package())
 for n,v in s.prepare_reading_export().items():(output/n).write_bytes(v)
 timing={'manual_seconds':manual,'rehearsal_seconds':rehearsal,'adoption_seconds':adopt,'engine_calls':2,'adoption_engine_calls':0,'formal_rounds':len(s.history),'API_requests':0,'automatic_renders':0,'remaining_temporary_directories':len(list(s.task_dir.glob('rehearsal-*'))),'byte_equal_to_manual':True};(output/'timings.json').write_text(json.dumps(timing,indent=2)+'\n');print(json.dumps({'proof':proof,'timing':timing},ensure_ascii=False,indent=2));return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)

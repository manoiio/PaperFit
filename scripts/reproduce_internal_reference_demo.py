"""Offline Stage32 check/fix/rehearsal and project reproducibility."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import sys,json,argparse,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.package import Package,sha256
from core import fix_document
from web.session import WebSession
S=Path(__file__).resolve().parents[1]/'samples/phase32'
def session(root,*,checked=True,text=True,source=None):
 plan=json.loads((S/'independent-plan.json').read_text());s=WebSession(root);s.set_mode('academic');assert s.load((source or S/'errors.docx').read_bytes(),'内部引用合成论文.docx'),s.error
 s.set_types(plan['roles']);s.exclude_materials([12],plan['protected_material']['12'])
 s.enable_notes(True);n=deepcopy(s.note_draft);n['objects']=plan['selected_notes'];s.edit_notes(n)
 s.enable_references(True);r=deepcopy(s.reference_draft);r['template']['internal_text']=text;s.edit_references(r)
 if checked:
  pre=s.scope_preflight();assert pre['ready'],pre['blockers'];assert s.confirm_scopes_and_check(pre['signature'],acknowledged=True),s.error
 return s

def selection(s):
 plan=json.loads((S/'independent-plan.json').read_text());keys=[]
 for f in s.eligible():
  loc=f['locator']
  if f['rule_id'] not in ('R05','R21','R36','R37'):continue
  prop=loc.get('property')
  if f['rule_id']!='R05' and prop not in ('size','font_size'):continue
  for r in plan['repairs']:
   if r['part']==f.get('story_part','word/document.xml') and all(loc.get(k)==v for k,v in r.items() if k not in ('part','pt')):keys.append(f['key']);break
 assert len(keys)==len(plan['repairs']),(len(keys),len(plan['repairs']));return keys

def run(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);s=session(out/'web');keys=selection(s);s.set_selection(keys)
 import web.session as api
 with patch('web.session.fix_document',wraps=api.fix_document) as f:
  start=time.perf_counter();assert s.rehearse(),s.rehearsal_error;rehearse=time.perf_counter()-start;i=s.rehearsal['id'];assert not s.history
  start=time.perf_counter();assert s.adopt_rehearsal(i,acknowledged=True),s.rehearsal_error;adopt=time.perf_counter()-start;assert s.adopt_rehearsal(i,acknowledged=True);assert f.call_count==1
 direct=fix_document(s.input_path,out/'direct.docx',s.confirmed,selected_keys=keys,**s._rules_arguments());assert Path(direct['output']).read_bytes()==s.downloads()['fixed.docx']==(S/'correct.docx').read_bytes()
 from scripts.verify_internal_reference_output import verify
 proof=verify(s.input_path,s.result['output']);(out/'independent-check.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 (out/'fixed.docx').write_bytes(s.downloads()['fixed.docx']);(out/'result.zip').write_bytes(s.result_package());(out/'project.zip').write_bytes(s.prepare_project());(out/'draft-project.zip').write_bytes(session(out/'draft',checked=False).prepare_project());(out/'fixed.types.json').write_text(json.dumps(s.result['output_classification_manifest'],ensure_ascii=False,indent=2)+'\n');(out/'internal-reference-supplement.json').write_bytes(s.reference_template_bytes())
 from core.report import modification_markdown,markdown
 from web.reading_report import clean
 r=clean(s.result);r['output']='fixed.docx';r['before']['input']='errors.docx';r['after']['input']='fixed.docx';(out/'changes.md').write_text(modification_markdown(r));(out/'recheck.md').write_text(markdown(r['after']))
 for n,b in s.prepare_reading_export().items():(out/n).write_bytes(b)
 (out/'structure-report.json').write_text(json.dumps(s.result['after']['internal_references'],ensure_ascii=False,indent=2)+'\n')
 (out/'efficiency.json').write_text(json.dumps({'rehearsal_seconds':rehearse,'adoption_seconds':adopt,'engine_calls':1,'adoption_engine_calls':0,'formal_rounds':1,'api_requests':0,'automatic_renders':0,'direct_control_byte_equal':True},indent=2)+'\n')
 print(json.dumps(proof,ensure_ascii=False));return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)

"""Offline actual check/fix/rehearsal equivalence; stable scope and authored whitelist."""
from pathlib import Path
from copy import deepcopy
import sys,json,argparse,time,zipfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import check_document,fix_document
from core.package import Package,q,NS,sha256
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'samples/phase29'
def session(root,checked=True):
 ds=json.loads((S/'scope.json').read_text());s=WebSession(root);s.set_mode('academic');assert s.load((S/'errors.docx').read_bytes(),'超链接合成论文.docx'),s.error;s.set_types(ds['roles']);s.exclude_materials([13],ds['materials']['13'])
 s.enable_notes(True);d=deepcopy(s.note_draft);d['objects']=ds['selected_notes'];s.edit_notes(d)
 s.enable_citations(True);d=deepcopy(s.citation_draft);d['objects']={r['id']:'citation' for r in s.citation_inventory()['objects']};s.edit_citations(d)
 if checked:
  p=s.scope_preflight();assert p['ready'],p['blockers'];assert s.confirm_scopes_and_check(p['signature'],acknowledged=True),s.error
 return s

def selection(s):
 repairs=json.loads((S/'independent-errors.json').read_text())['allowed_repairs'];out=[]
 for f in s.eligible():
  loc=f['locator'];prop=loc.get('property') or {'R03':'font_eastAsia','R04':'font_ascii','R05':'size'}.get(f['rule_id'])
  if f['rule_id'] in ('R36','R37'):prop={'font_cn':'font_eastAsia','font_size':'size'}.get(prop)
  for e in repairs:
   if e['part']!=f.get('story_part','word/document.xml') or e['property']!=prop:continue
   if all(loc.get(k)==v for k,v in e.items() if k not in ('part','property','value')):out.append(f['key']);break
 assert len(out)==len(repairs),(len(out),len(repairs));return out

def run(output):
 output=Path(output)
 if output.exists():raise SystemExit('Refusing existing output directory')
 output.mkdir(parents=True);s=session(output/'web');keys=selection(s);s.set_selection(keys)
 import web.session as api
 with patch('web.session.fix_document',wraps=api.fix_document) as fix:
  start=time.perf_counter();assert s.rehearse(),s.rehearsal_error;preview=time.perf_counter()-start;identifier=s.rehearsal['id'];assert s.generation_count==0
  start=time.perf_counter();assert s.adopt_rehearsal(identifier,acknowledged=True),s.rehearsal_error;adopt=time.perf_counter()-start;assert s.adopt_rehearsal(identifier,acknowledged=True);assert fix.call_count==1
 direct=fix_document(s.input_path,output/'direct.docx',s.confirmed,selected_keys=keys,**s._rules_arguments());assert Path(direct['output']).read_bytes()==s.downloads()['fixed.docx']==(S/'correct.docx').read_bytes()
 from scripts.verify_hyperlink_output import verify
 proof=verify(s.input_path,s.result['output']);(output/'independent-check.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 (output/'fixed.docx').write_bytes(s.downloads()['fixed.docx']);(output/'result.zip').write_bytes(s.result_package());(output/'project.zip').write_bytes(s.prepare_project());(output/'fixed.types.json').write_text(json.dumps(s.result['output_classification_manifest'],ensure_ascii=False,indent=2)+'\n')
 from core.report import markdown,modification_markdown
 from web.reading_report import clean
 safe=clean(s.result);safe['output']='fixed.docx';safe['after']['input']='fixed.docx';safe['before']['input']='errors.docx'
 (output/'changes.md').write_text(modification_markdown(safe));(output/'recheck.md').write_text(markdown(safe['after']))
 for n,b in s.prepare_reading_export().items():(output/n).write_bytes(b)
 (output/'coverage.json').write_text(json.dumps({'before':s.report['coverage'].get('hyperlink_text'),'after':s.result['after']['coverage'].get('hyperlink_text'),'before_summary':s.report['summary'],'after_summary':s.result['after']['summary'],'engine_calls':1,'adoption_fix_calls':0,'formal_rounds':1,'preview_seconds':preview,'adoption_seconds':adopt,'API_calls':0,'automatic_renders':0,'control_matches_bytes':True},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(proof,ensure_ascii=False,indent=2));return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)

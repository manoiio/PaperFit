"""Offline actual-fix rehearsal/adoption equivalence with independent XML/ZIP proof."""
import argparse,json,time,statistics,tempfile,sys,zipfile
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.reproduce_scope_demo import session,old_check,ROOT
from web.session import WebSession
from web.reading_report import clean
from core.package import Package,sha256,q,NS
from lxml import etree as E
KEY='R05:paragraph=8:run=1'

def run(output):
 output=Path(output)
 if output.exists():raise SystemExit('Refusing existing output directory')
 output.mkdir(parents=True)
 s=session(output/'web');p=s.scope_preflight();assert s.confirm_scopes_and_check(p['signature'],acknowledged=True),s.error
 s.set_selection([KEY]);source=s.input_path.read_bytes()
 # Independent direct engine path, equal input/rules/confirmed scope/selection.
 from core import fix_document
 direct_start=time.perf_counter()
 direct=fix_document(s.input_path,output/'direct.docx',s.confirmed,selected_keys=[KEY],**s._rules_arguments())
 direct_time=time.perf_counter()-direct_start
 import web.session as api
 with patch('web.session.fix_document',wraps=api.fix_document) as fix:
  start=time.perf_counter();assert s.rehearse(),s.rehearsal_error;first=time.perf_counter()-start
  i=s.rehearsal['id'];view=s.rehearsal_view();pending=s.generation_count;views=[]
  for _ in range(3):
   start=time.perf_counter();assert s.rehearsal_view();views.append(time.perf_counter()-start)
  start=time.perf_counter();assert s.adopt_rehearsal(i,acknowledged=True),s.rehearsal_error;adoption=time.perf_counter()-start
  assert s.adopt_rehearsal(i,acknowledged=True);assert fix.call_count==1
 files=s.downloads();assert source==s.input_path.read_bytes();assert files['fixed.docx']==Path(direct['output']).read_bytes()==(ROOT/'samples/phase26/fixed.docx').read_bytes()
 a,b=Package(s.input_path),Package(s.result['output']);left=E.fromstring(a.parts['word/document.xml']);right=E.fromstring(b.parts['word/document.xml'])
 old=left.find('w:body',NS).findall(q('p'))[7].findall(q('r'))[0].find('w:rPr/w:sz',NS);new=right.find('w:body',NS).findall(q('p'))[7].findall(q('r'))[0].find('w:rPr/w:sz',NS)
 assert (old.get(q('val')),new.get(q('val')))==('26','24');old.set(q('val'),'24');assert E.tostring(left,method='c14n')==E.tostring(right,method='c14n')
 assert all(v==b.parts[n] for n,v in a.parts.items() if n!='word/document.xml')
 assert not list(s.task_dir.glob('rehearsal-*'));assert len(s.history)==s.generation_count==1 and s.current_round==0 and pending==0
 # Export source/output-bound portable records, not private session paths.
 (output/'fixed.docx').write_bytes(files['fixed.docx']);(output/'result.zip').write_bytes(s.result_package())
 for name,data in s.prepare_reading_export().items():(output/name).write_bytes(data)
 for name in ('changes.md','recheck.md'):
  from core.report import modification_markdown,markdown
  safe=clean(s.result);safe['output']='fixed.docx';safe['before']['input']='composite.docx';safe['after']['input']='fixed.docx'
  (output/name).write_text(modification_markdown(safe) if name=='changes.md' else markdown(safe['after']))
 record={'input_sha256':sha256(source),'output_sha256':sha256(files['fixed.docx']),'direct_and_adopted_byte_equal':True,'matches_phase26_visually_accepted_file':True,'only_target_sz_26_to_24':True,'canonical_xml_equal_after_one_allowed_size_value':True,'other_parts_byte_equal':True,'source_unchanged':True,'rehearsal_fix_engine_calls':1,'direct_reference_fix_engine_calls':1,'fix_calls_at_adoption':0,'formal_rounds':1,'pending_rounds':pending,'current_input_round':0,'rehearsal_directories_after_adoption':0,'AI_requests':0,'automatic_renders':0}
 (output/'independent-check.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
 (output/'impact.json').write_text(json.dumps(clean(view),ensure_ascii=False,indent=2)+'\n')
 timings={'environment':'local Python '+sys.version.split()[0],'direct_engine_and_readback_seconds':direct_time,'first_rehearsal_seconds':first,'repeat_view_seconds':views,'repeat_view_median_seconds':statistics.median(views),'adoption_including_actual_recheck_seconds':adoption,'note':'预演前置执行一次修正；采用重新验证但不再次修正，不据此宣称端到端提速。'}
 (output/'timings.json').write_text(json.dumps(timings,ensure_ascii=False,indent=2)+'\n')
 # A project may restore selected drafts, never executable rehearsal authorization.
 (output/'project.zip').write_bytes(s.prepare_project())
 print(json.dumps({'independent':record,'timings':timings},ensure_ascii=False,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)

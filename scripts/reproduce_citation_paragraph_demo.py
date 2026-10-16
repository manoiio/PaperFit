"""Confirmed inline citation evidence, original pPr transactions and legal plans."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import sys,json,argparse,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import load_rules,check_document
from core.templates import make_template,defaults,ALL_FIELDS
from core.academic_templates import make
from core.academic_rules import flat_defaults
from core.citations import upgrade_template
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1];SAMPLE=ROOT/'samples/phase31'
def config():
 base=load_rules();main=make_template('用户确认的段落属性演示',defaults(base,extended=True),{n:{'kind':'default_inherited','quote':'','location':None} for n in ALL_FIELDS},[],base)
 vals=flat_defaults();src={n:{'kind':'default_inherited' if v is not None else 'not_enabled','quote':'','location':None} for n,v in vals.items()}
 for n,v in {'body__before':{'value':6,'unit':'pt'},'body__after':{'value':.5,'unit':'lines'},'body__alignment':'both'}.items():vals[n]=v;src[n]={'kind':'user_confirmed','quote':'','location':None}
 return make(main,vals,src,[],base)
def session(root,*,checked=True,path=None):
 meta=json.loads((SAMPLE/'independent-errors.json').read_text());s=WebSession(root);s.set_mode('academic');assert s.import_template(json.dumps(config(),ensure_ascii=False).encode()),s.template_error;assert s.apply_template(),s.template_error
 assert s.load(Path(path or SAMPLE/'errors.docx').read_bytes(),'已确认引文段落合成演示.docx'),s.error;s.set_types(meta['roles']);s.exclude_materials([18],meta['material_exclusions']['18']);s.enable_citations(True);d=deepcopy(s.citation_draft);d['template']=upgrade_template(d['template']);d['objects']={f"c:{r['paragraph']}:{r['start']}:{r['end']}":r['purpose'] for r in meta['citations']};s.edit_citations(d)
 if checked:s.confirm_citations();assert s.confirm_and_check(),s.error
 return s
def selection(s):return [f['key'] for f in s.eligible() if f['locator'].get('paragraph') in (3,4,7) and (f['rule_id'] in ('R06','R07') or f['rule_id']=='R13' and f['property'] in ('before','after','alignment'))]
def run(output):
 out=Path(output)
 if out.exists():raise SystemExit('Refusing existing output directory')
 out.mkdir(parents=True);s=session(out/'session');before=deepcopy(s.report);keys=selection(s);assert len(keys)==14
 import web.session as api
 with patch('web.session.fix_document',wraps=api.fix_document) as engine:
  s.set_selection(keys[:1]);t=time.perf_counter();assert s.rehearse(),s.rehearsal_error;first=time.perf_counter()-t;t=time.perf_counter();assert s.adopt_rehearsal(s.rehearsal['id'],acknowledged=True),s.rehearsal_error;adopt=time.perf_counter()-t;assert engine.call_count==1
  (out/'step-1.docx').write_bytes(Path(s.result['output']).read_bytes());assert s.next_round();s.set_selection(selection(s));assert s.rehearse(),s.rehearsal_error;assert s.adopt_rehearsal(s.rehearsal['id'],acknowledged=True),s.rehearsal_error;assert engine.call_count==2
 (out/'fixed.docx').write_bytes(Path(s.result['output']).read_bytes())
 from scripts.verify_citation_paragraph_output import verify
 proof=verify(SAMPLE/'errors.docx',out/'fixed.docx');(out/'independent-check.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 from web.reading_report import clean
 from core.report import markdown,modification_markdown
 r=clean(s.result);r['output']='fixed.docx';r['after']['input']='fixed.docx';r['before']['input']='step-1.docx'
 (out/'changes.md').write_text(modification_markdown(r));(out/'recheck.md').write_text(markdown(r['after']));(out/'before.json').write_text(json.dumps(clean(before),ensure_ascii=False,indent=2)+'\n');(out/'fixed.types.json').write_text(json.dumps(s.result['output_classification_manifest'],ensure_ascii=False,indent=2)+'\n')
 (out/'evidence.json').write_text(json.dumps(s.result['after']['coverage']['citation_paragraph_evidence'],ensure_ascii=False,indent=2)+'\n');(out/'template.json').write_bytes(s.template_download());(out/'result.zip').write_bytes(s.result_package())
 for n,v in s.prepare_reading_export().items():(out/n).write_bytes(v)
 (out/'timings.json').write_text(json.dumps({'first_rehearsal_seconds':first,'first_adoption_seconds':adopt,'engine_calls':2,'adoption_engine_calls':0,'formal_rounds':2,'API_requests':0,'automatic_renders':0,'temporary_rehearsal_directories':len(list(s.task_dir.glob('rehearsal-*')))},indent=2)+'\n')
 print(json.dumps({'before':before['summary'],'after':s.result['after']['summary'],'selected':len(keys),'proof':proof},ensure_ascii=False,indent=2));return s
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)

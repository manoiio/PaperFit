"""Original sequential-field reference, independent of the object editor's conversion.
Existing synthetic paper and rule package; no AI, renderer or historical work tree.
"""
import argparse,json,sys,zipfile,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import fix_document,rule_bundle as rb,load_rules
from scripts.reproduce_internal_reference_demo import session
from scripts.verify_workflow_equivalence import verify
ROOT=Path(__file__).resolve().parents[1]
EDITS={'font_cn':'楷体','font_size':13.,'line_spacing':2.}

def run(output,download=None,rules=None,project=None):
 out=Path(output);out.mkdir(parents=True,exist_ok=False);s=session(out/'task',checked=False)
 s.import_rule_bundle((ROOT/'samples/phase25/repaired-rule-bundle.json').read_bytes())
 before=s.current_rule_bundle();old=rb.flat('main',before['modules']['main'])
 for n,v in EDITS.items():s.workbench_edit('main',n,'manual',v)
 assert rb.flat('main',s.current_rule_bundle()['modules']['main'])==old
 if project:
  restored=session(out/'restore',checked=False);restored.stage_project(Path(project).read_bytes());restored=restored.restore_project(acknowledged=True)
  assert restored.workbench['draft']['fields']==s.workbench['draft']['fields']
  assert restored.workbench['active'] is None
 current=s.apply_workbench(acknowledged=True)
 if rules:
  actual=rb.loads(Path(rules).read_bytes(),load_rules())
  assert actual['provenance']==current['provenance']
  for m in rb.MODULES:assert (rb.flat(m,actual['modules'][m]) if actual['modules'][m] else None)==(rb.flat(m,current['modules'][m]) if current['modules'][m] else None)
 pre=s.scope_preflight();assert pre['ready'],pre['blockers'];assert s.confirm_scopes_and_check(pre['signature'],acknowledged=True),s.error
 key=next(f['key'] for f in s.eligible() if f['rule_id']=='R05' and all(f['locator'].get(k)==v for k,v in {'paragraph':3,'link':1,'link_run':2}.items()))
 r=fix_document(s.input_path,out/'fixed.docx',s.confirmed,selected_keys=[key],**s._rules_arguments())
 # Raw ZIP/XML independent assertion: exactly selected link-run size, not fonts or spacing.
 from lxml import etree as E
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};q=lambda n:'{'+ns['w']+'}'+n
 with zipfile.ZipFile(s.input_path) as a,zipfile.ZipFile(r['output']) as b:
  assert a.namelist()==b.namelist() and all(a.read(n)==b.read(n) for n in a.namelist() if n!='word/document.xml')
  x,y=E.fromstring(a.read('word/document.xml')),E.fromstring(b.read('word/document.xml'))
  assert x.xpath('//w:t/text()',namespaces=ns)==y.xpath('//w:t/text()',namespaces=ns)
  path='w:body/w:p[3]/w:hyperlink/w:r[2]/w:rPr/w:sz'
  assert y.find(path,ns).get(q('val'))=='26'
  for tree in (x,y):tree.find(path,ns).attrib.pop(q('val'))
  assert E.tostring(x,method='c14n')==E.tostring(y,method='c14n')
 proof={'fixture':'samples/phase32/errors.docx','rule_fixture':'samples/phase25/repaired-rule-bundle.json','input_sha256':hashlib.sha256(s.input_path.read_bytes()).hexdigest(),'edits':EDITS,'edited_sources':{n:current['provenance']['main'][n] for n in EDITS},'all_browser_rule_values_and_sources_equal':bool(rules),'saved_project_draft_fields_equal':bool(project),'selected_key':key,'after_summary':r['after']['summary'],'all_text_and_unselected_parts_preserved':True,'only_selected_size_attribute_changed':True,'API_requests':0,'render_requests':0}
 if download:proof['download_equivalence']=verify(r['output'],download)
 (out/'independent.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proof,ensure_ascii=False,indent=2));return proof
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--browser-download');p.add_argument('--browser-rules');p.add_argument('--draft-project');a=p.parse_args();run(a.output,a.browser_download,a.browser_rules,a.draft_project)

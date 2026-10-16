"""Stage35 UI-equivalent legal path; existing fixture, no browser/private state/API."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys,json,argparse,hashlib,zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.reproduce_internal_reference_demo import session
from core import fix_document,rule_bundle as rb,load_rules
from scripts.verify_workflow_equivalence import verify
ROOT=Path(__file__).resolve().parents[1]
EDITS={'font_cn':'楷体','font_size':13.,'body__before':{'value':.5,'unit':'lines'}}
def run(out,download=None,rules=None):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);s=session(out/'session',checked=False)
 s.import_rule_bundle((ROOT/'samples/phase25/repaired-rule-bundle.json').read_bytes())
 for n,v in EDITS.items():s.workbench_edit('main',n,'manual',v)
 s.apply_workbench(acknowledged=True)
 # Explicit UI classification intent: edit one paragraph, then restore body via batch.
 s.batch_types([3],'other');s.batch_types([3,4,12],'body');assert s.paragraph_types['12']=='other' and '12' in s.material_exclusions
 pre=s.scope_preflight();assert pre['ready'],pre['blockers'];assert s.confirm_scopes_and_check(pre['signature'],acknowledged=True),s.error
 k=next(f['key'] for f in s.eligible() if f['rule_id']=='R05' and all(f['locator'].get(a)==b for a,b in {'paragraph':3,'link':1,'link_run':2}.items()))
 r=fix_document(s.input_path,out/'direct.docx',s.confirmed,selected_keys=[k],**s._rules_arguments())
 current=s.current_rule_bundle()
 if rules:
  actual=rb.loads(Path(rules).read_bytes(),load_rules())
  assert actual['provenance']==current['provenance']
  assert all((rb.flat(m,actual['modules'][m]) if actual['modules'][m] else None)==(rb.flat(m,current['modules'][m]) if current['modules'][m] else None) for m in rb.MODULES)
 proof={'fixture':'samples/phase32/errors.docx','input_sha256':hashlib.sha256(s.input_path.read_bytes()).hexdigest(),'explicit_edits':EDITS,'edited_sources':{n:current['provenance']['main'][n] for n in EDITS},'selected_key':k,'after_summary':r['after']['summary'],'protected_material_ids':list(s.material_exclusions),'rules_all_values_and_sources_equal':bool(rules),'api_requests':0}
 if download:proof['download_equivalence']=verify(r['output'],download)
 # Independent ZIP/XML, no UI/new field projection used in this check.
 from lxml import etree as E
 ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};q=lambda x:'{'+ns['w']+'}'+x
 with zipfile.ZipFile(s.input_path) as a,zipfile.ZipFile(r['output']) as b:
  assert a.namelist()==b.namelist();assert all(a.read(n)==b.read(n) for n in a.namelist() if n!='word/document.xml')
  x,y=E.fromstring(a.read('word/document.xml')),E.fromstring(b.read('word/document.xml'))
  assert x.xpath('//w:t/text()',namespaces=ns)==y.xpath('//w:t/text()',namespaces=ns)
  p=y.find('w:body',ns).findall('w:p',ns)[2];sz=p.find('w:hyperlink/w:r[2]/w:rPr/w:sz',ns);assert sz.get(q('val'))=='26'
  # Strip only the independently authorized size attribute, then compare full trees.
  for tree in (x,y):
   el=tree.find('w:body',ns).findall('w:p',ns)[2].find('w:hyperlink/w:r[2]/w:rPr/w:sz',ns);el.attrib.pop(q('val'))
  assert E.tostring(x,method='c14n')==E.tostring(y,method='c14n')
 proof['independent_only_selected_size_changed']=True
 (out/'independent.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proof,ensure_ascii=False,indent=2));return proof
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--browser-download');p.add_argument('--browser-rules');a=p.parse_args();run(a.output,a.browser_download,a.browser_rules)

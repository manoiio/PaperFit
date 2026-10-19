"""Replay a real public browser project through original legal core transactions.
No defaults module, AI, Word or smart orchestration. Explicit accepted scope is
reused; expected attribute values and auxiliary keys are independently authored.
"""
from pathlib import Path
from copy import deepcopy
import sys,json,zipfile,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def run(project,folder):
 from core import fix_document,check_document,rule_bundle as rb,load_rules,page_layout,layout
 from core.package import Package,sha256
 from core.table_text import rebind
 from scripts.verify_smart_defaults import verify
 out=Path(folder);out.mkdir(parents=True,exist_ok=False)
 with zipfile.ZipFile(project) as z:
  p=json.loads(z.read('project.json'));h=p['state']['history'][0];source=out/'source.docx';source.write_bytes(z.read(p['documents'][0]['member']));rule=out/'rules.json';rule.write_bytes(z.read(p['rules'][0]['member']));scope=h['scope'];m={'input_sha256':Package(source).hash,'paragraph_types':scope['types'],'confirmed':True,'confirmation':'offline replay of actual browser accepted scope'}
  for k in ('caption_scope','reference_scope','table_scope'):
   if k in scope:m[k]=deepcopy(scope[k])
  m=rebind(m,Package(source).hash);before=check_document(source,{},custom_rules_path=rule,mode='academic',classification_manifest=m)
  selected=[f['key'] for f in before['findings'] if f['fixable']]
  r=fix_document(source,out/'01-format.docx',{},selected_keys=selected,custom_rules_path=rule,mode='academic',classification_manifest=m)
  assert Path(r['output']).read_bytes()==z.read(p['documents'][1]['member'])
  # Original requirement carrier, just the two new defaults and outer-edge decision removed.
  bundle=rb.loads(rule.read_bytes(),load_rules());vals=rb.flat('main',bundle['modules']['main']);ss=bundle['provenance']['main']
  for n in ('figure_caption__alignment','table_caption__alignment'):vals[n]=None;ss[n]=deepcopy(rb.EMPTY)
  bundle['modules']['main']=rb.make_main(bundle['name'],vals,ss,bundle['excerpt'],bundle['extraction'],load_rules());base=out/'baseline-rules.json';base.write_bytes(rb.raw(rb.validate(bundle,load_rules())))
  bm=deepcopy(m);bm['table_scope']['layout_options']['outer_edges']=False
  b=check_document(source,{},custom_rules_path=base,mode='academic',classification_manifest=bm)
  fix_document(source,out/'baseline.docx',{},selected_keys=[f['key'] for f in b['findings'] if f['fixable']],custom_rules_path=base,mode='academic',classification_manifest=bm)
  m=r['output_classification_manifest'];policy=p['state']['editor']['page_layout_draft']['policy'];regions=[{'start':1,'role':'body','format':'decimal','restart':1,'footer':'page','text':'','alignment':'center'}]
  plan=page_layout.propose(r['output'],m,policy,regions);r=page_layout.rehearse(r['output'],out/'02-pages.docx',m,plan,custom_rules_path=rule)
  assert Path(r['output']).read_bytes()==z.read(p['documents'][2]['member'])
  r=layout.apply_pagination_layout(r['output'],out/'fixed.docx',{},mode='academic',classification_manifest=r['output_classification_manifest'],confirmed_keys=['L01:6:7','L02:3:1'],custom_rules_path=rule)
  assert Path(r['output']).read_bytes()==z.read(p['documents'][3]['member'])
 proof=verify(source,r['output'],out/'baseline.docx',out/'01-format.docx');proof.update(same_bytes_as_actual_browser=True,API_requests=0,Word_calls=0)
 (out/'proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');return proof
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('project');p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(run(a.project,a.output),ensure_ascii=False,indent=2))

"""Public carrier extraction + saved real-response replay + original legal path. ZERO API."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.request import OpenerDirector
import argparse,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from web.session import WebSession
from web.requirements_input import file_input
from core import rule_bundle as rb
from core.package import sha256
from core.norms import source_group
from ai.file_spec import adapt,request_for
from scripts.reproduce_context_workflow import independent

def main(output):
 output=Path(output)
 if output.exists():raise SystemExit('Output must not exist')
 output.mkdir(parents=True);sample=ROOT/'samples/phase46';source=ROOT/'samples/phase44/supplement.docx';expected=json.loads((ROOT/'samples/phase44/expected-overrides.json').read_text())['fields'];record={}
 with TemporaryDirectory() as tmp,patch.object(OpenerDirector,'open',side_effect=AssertionError('No network in carrier replay')):
  for kind in ('txt','docx'):
   model=WebSession(Path(tmp)/kind);model.set_mode('academic');model.load(source.read_bytes(),'合成论文.docx');prior=model.current_rule_bundle()
   desc=file_input(model,(sample/('requirements.'+kind)).read_bytes(),'要求.'+kind);req=json.loads((sample/(kind+'-request.json')).read_text());r=request_for(desc['extraction']);r['fields']={k:{p:v for p,v in f.items() if p!='name'} for k,f in r['fields'].items()};assert sha256(json.dumps(r,ensure_ascii=False,sort_keys=True).encode())==req['input_sha256']
   response=json.loads((sample/(kind+'-response.json')).read_text());parsed=adapt(json.loads(response['choices'][0]['message']['content']),desc['extraction']);assert not parsed['notices'];assert set(parsed['draft']['fields'])==set(expected)
   for n,v in expected.items():assert parsed['draft']['fields'][n]['value']==v['value']
   with zipfile.ZipFile(sample/(kind+'-result.zip')) as z:raw=z.read('fixed.docx');scope=json.loads(z.read('scope.json'));bundle=json.loads(z.read('rules.json'))
   # Independently compare the downloaded active fields and untouched origins,
   # not the new parser's own interpretation as its standard answer.
   final=rb.flat('main',bundle['modules']['main']);before=rb.flat('main',prior['modules']['main'])
   for n,v in expected.items():
    assert final[n]==v['value'];origin=bundle['provenance']['main'][n];assert origin['location'][len(source_group(origin['location'])):] == ('TXT:L1' if kind=='txt' else 'DOCX:P1')
   for n,v in before.items():
    if n not in expected:assert final[n]==v and bundle['provenance']['main'][n]==prior['provenance']['main'][n]
   for module in ('front','toc','notes'):assert bundle['modules'][module]==prior['modules'][module] and bundle['provenance'][module]==prior['provenance'][module]
   assert desc['extraction']['file_sha256'] in bundle['name']
   model.import_rule_bundle(rb.raw(bundle));model.apply_workbench(acknowledged=True);model.set_types(scope['paragraph_types']);assert model.confirm_and_check(),model.error
   model.set_selection([f['key'] for f in model.eligible() if f['rule_id'].startswith('R') and f['rule_id']!='R35']);assert model.generate(),model.error;assert raw==model.downloads()['fixed.docx']
   assert raw==(sample/(kind+'.docx')).read_bytes();path=output/(kind+'.docx');path.write_bytes(raw)
   record[kind]={'sha256':sha256(raw),'original_legal_bytes_equal':True,'authored_16_values_and_physical_locations':True,'untouched_values_origins_and_other_modules_equal':True,'file_sha256_retained':True,'independent_XML_ZIP':independent(source,path),'replay_requests':0}
  assert (sample/'reuse.docx').read_bytes()==(sample/'txt.docx').read_bytes();record['reuse']={'browser_bytes_equal':True,'requirements_parse_requests':0}
 record['network_requests']=0;(output/'independent.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);main(p.parse_args().output)

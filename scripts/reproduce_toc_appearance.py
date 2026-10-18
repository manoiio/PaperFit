"""Public local reproduction; no paid API. --word explicitly controls isolated Word copies."""
from pathlib import Path
import sys,json,argparse,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def run(folder,word=False):
 from urllib.request import OpenerDirector
 from core.package import DemoError,sha256
 from core import word_fields
 source=ROOT/'samples/phase55/source.docx'
 if not word:return word_fields.inventory(source)
 from web.session import WebSession
 from web.onepass_session import start,poll_fields
 from web.page_ui import smart_seed
 from scripts.verify_toc_appearance import verify
 OpenerDirector.open=lambda *_a,**_k:(_ for _ in ()).throw(AssertionError('Network disabled'))
 out=Path(folder);out.mkdir(parents=True,exist_ok=False);s=WebSession(out/'session');s.set_mode('academic');s.load(source.read_bytes(),'公开合成目录.docx')
 seed=smart_seed(s);s.page_layout_draft={**seed,'input_sha256':s.inventory['input_sha256'],'regions':[]};s.field_updates_enabled=True;state={};started=time.monotonic()
 start(s,state,structure_runner=lambda *_:(_ for _ in ()).throw(DemoError('No API in this reproduction')))
 if state['status']=='waiting':raise DemoError('Unexpected question in public fixture: '+','.join(q['id'] for q in state['questions']))
 while state['status']=='updating':
  poll_fields(s,state)
  if time.monotonic()-started>120:raise DemoError('Timed out waiting; not a claim that Word has terminated')
  time.sleep(.1)
 if state['status']!='done' or state['audit'].get('field_update',{}).get('status')!='updated':raise DemoError('Update incomplete; inspect local output before publishing')
 path=out/'fixed.docx';path.write_bytes(s.downloads()['fixed.docx']);(out/'result.zip').write_bytes(s.result_package())
 r=s.result;proof=verify(r['round_input_path'],path);proof.update(seconds=round(time.monotonic()-started,3),API_requests=0,rounds=s.generation_count,original_unchanged=s.input_path.read_bytes()==source.read_bytes(),same_bytes_as_browser=path.read_bytes()==(ROOT/'samples/phase55/fixed.docx').read_bytes(),appearance=r['field_update']['validation']['toc_appearance'])
 (out/'proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');return proof
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--word',action='store_true');a=p.parse_args();print(json.dumps(run(a.output,a.word),ensure_ascii=False,indent=2))

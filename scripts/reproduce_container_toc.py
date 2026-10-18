"""Explicit synthetic integration. --word opens only isolated native Word copies."""
from pathlib import Path
import sys,json,time,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def run(folder,word=False):
 from core.package import Package,DemoError
 from core.word_fields import inventory
 source=ROOT/'samples/phase52/source.docx'
 if not word:return inventory(source)
 from urllib.request import OpenerDirector
 OpenerDirector.open=lambda *a,**k:(_ for _ in ()).throw(AssertionError('Network forbidden in local integration'))
 from web.session import WebSession
 from web.onepass_session import start,poll_fields
 from core.page_policy import DEFAULT
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=False);s=WebSession(folder/'session');s.set_mode('academic');s.load(source.read_bytes(),'公开合成论文.docx');s.page_layout_draft={'enabled':True,'policy':{**DEFAULT,'version':3,'targets':['cover','front','body'],'auxiliaries':'safe-layout-v1','pages':'front-body','footer':'chapter'},'regions':[],'input_sha256':s.inventory['input_sha256']};s.field_updates_enabled=True;state={};t=time.monotonic()
 start(s,state,structure_runner=lambda *_:(_ for _ in ()).throw(DemoError('No API in this local integration')))
 if state['status']=='waiting':
  (folder/'questions.json').write_text(json.dumps(state['questions'],ensure_ascii=False,indent=2));raise DemoError('Unexpected user question; inspect questions.json')
 while state['status']=='updating':
  poll_fields(s,state)
  if time.monotonic()-t>120:raise DemoError('Wait timed out; not a termination claim')
  time.sleep(.1)
 if state['status']!='done':raise DemoError(state.get('error','not done'))
 (folder/'fixed.docx').write_bytes(s.downloads()['fixed.docx']);(folder/'result.zip').write_bytes(s.result_package());(folder/'audit.json').write_text(json.dumps(state['audit'],ensure_ascii=False,indent=2)+'\n')
 proof={'seconds':round(time.monotonic()-t,3),'API_requests':0,'input_sha256':Package(source).hash,'output_sha256':Package(folder/'fixed.docx').hash,'field_update':state['audit'].get('field_update'),'rounds':s.generation_count,'current_input_unchanged':s.current_round==0}
 (folder/'proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');return proof
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--word',action='store_true');a=p.parse_args();print(json.dumps(run(a.output,a.word),ensure_ascii=False,indent=2))

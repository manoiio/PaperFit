"""Public structure transaction reproduction and equivalent local/smart commands."""
from pathlib import Path
import sys,json,argparse,zipfile
from urllib.request import OpenerDirector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.page_policy import DEFAULT
from core.package import sha256
from web.session import WebSession
from web.onepass_session import start
from web.assembly_session import execute_local

def run(out,browser=None):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 def blocked(*a,**kw):raise AssertionError('Reproduction forbids network')
 OpenerDirector.open=blocked
 sample=ROOT/'samples/phase48';roles=json.loads((sample/'roles.json').read_text());policy={**DEFAULT,'dynamic':True,'pages':'front-body','footer':'chapter'}
 def model(name):
  s=WebSession(out/name);s.set_mode('academic');s.load((sample/'existing.docx').read_bytes(),'公开合成论文.docx');s.set_types(roles);s.confirm_classification();s.page_layout_draft={'enabled':True,'policy':policy,'input_sha256':s.inventory['input_sha256'],'regions':[]};return s
 smart=model('smart');state={};start(smart,state,structure_runner=lambda *_:blocked());assert state['status']=='done',state.get('error')
 local=model('local');execute_local(local,{},acknowledged=True)
 a=smart.downloads()['fixed.docx'];b=local.downloads()['fixed.docx'];assert a==b
 (out/'fixed.docx').write_bytes(a);(out/'rules.json').write_bytes(smart.rule_bundle_download());(out/'result.zip').write_bytes(smart.result_package())
 for i,h in enumerate(smart.history,1):(out/('step'+str(i)+'.docx')).write_bytes(Path(h['result']['output']).read_bytes())
 # A single-section version exercises automatic safe boundary addition.
 s=model('single');s.load((sample/'single.docx').read_bytes(),'公开合成单节.docx');s.set_types(roles);s.confirm_classification();s.page_layout_draft={'enabled':True,'policy':policy,'input_sha256':s.inventory['input_sha256'],'regions':[]};st={};start(s,st,structure_runner=lambda *_:blocked());assert st['status']=='done',st.get('error');(out/'single-fixed.docx').write_bytes(s.downloads()['fixed.docx'])
 for i,h in enumerate(s.history,1):(out/('single-step'+str(i)+'.docx')).write_bytes(Path(h['result']['output']).read_bytes())
 from scripts.verify_page_output import verify,verify_single
 proof=verify(sample/'existing.docx',out/'step1.docx',out/'step2.docx',out/'fixed.docx')
 result={'API_requests':0,'local_smart_DOCX_bytes_equal':True,'steps':state['audit']['assembly_steps'],'independent':proof,'final_sha256':sha256(a),'single_section_independent':verify_single(out/'single-step2.docx',out/'single-fixed.docx')}
 if browser:
  with zipfile.ZipFile(browser) as z:assert z.read('fixed.docx')==a
  result['actual_browser_DOCX_bytes_equal']=True
 (out/'independent.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--browser-zip');args=p.parse_args();run(args.output,args.browser_zip)

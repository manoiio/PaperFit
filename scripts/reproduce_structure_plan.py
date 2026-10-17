"""Stage49: original local legal path, hand-labelled scope, no API or historical folders."""
from pathlib import Path
import sys,json,argparse,zipfile
from urllib.request import OpenerDirector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from web.session import WebSession
from web.assembly_session import execute_local
from core.package import sha256

def run(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 def blocked(*a,**kw):raise AssertionError('No network in reproduction')
 OpenerDirector.open=blocked
 # These are the accepted fresh-upload roles, not a call to the new classifier.
 roles={'1':'pending','2':'pending','3':'abstract_cn_title','4':'abstract_cn_body','5':'heading1','6':'body','7':'pending','8':'body','9':'heading1','10':'body','11':'pending','12':'body'}
 s=WebSession(out/'local');s.set_mode('academic');s.load((ROOT/'samples/phase48/existing.docx').read_bytes(),'existing.docx')
 s.import_rule_bundle((ROOT/'samples/phase49/rules.json').read_bytes());s.apply_workbench(acknowledged=True);s.set_types(roles);s.confirm_classification()
 state={};execute_local(s,state,acknowledged=True)
 raw=s.downloads()['fixed.docx'];expected=(ROOT/'samples/phase49/fixed.docx').read_bytes();assert raw==expected,'local legal path differs from actual browser download'
 for i,h in enumerate(s.history,1):(out/f'step{i}.docx').write_bytes(Path(h['result']['output']).read_bytes())
 (out/'fixed.docx').write_bytes(raw)
 from scripts.verify_structure_plan import verify
 proof=verify(ROOT/'samples/phase48/existing.docx',out/'step1.docx',out/'fixed.docx')
 result={'local_legal_path_browser_bytes_equal':True,'sha256':sha256(raw),'API_requests':0,'independent':proof}
 (out/'independent.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)

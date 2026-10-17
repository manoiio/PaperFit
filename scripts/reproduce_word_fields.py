"""Explicit macOS Word integration demo. Ordinary tests never invoke this backend."""
from pathlib import Path
import sys,argparse,json,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.package import DemoError,sha256

def run(out,use_word):
 from core.word_fields import inventory
 source=ROOT/'samples/phase50/errors.docx'
 if not use_word:print(json.dumps(inventory(source),ensure_ascii=False,indent=2));return
 from urllib.request import OpenerDirector
 def blocked(*a,**k):raise AssertionError('Local demonstration has no API/network')
 OpenerDirector.open=blocked
 from web.session import WebSession
 from web.assembly_session import execute_local
 from web.field_session import submit,receive,adopt
 out=Path(out);out.mkdir(parents=True,exist_ok=False);s=WebSession(out/'session');s.set_mode('academic');s.load(source.read_bytes(),'公开合成.docx')
 s.import_rule_bundle((ROOT/'samples/phase50/rules.json').read_bytes());s.apply_workbench(acknowledged=True);s.set_types(json.loads((ROOT/'samples/phase50/accepted-roles.json').read_text()));s.confirm_classification()
 execute_local(s,{},acknowledged=True);before=Path(s.result['output']).read_bytes();(out/'before-update.docx').write_bytes(before)
 state={};start=time.monotonic();submit(s,state)
 while True:
  status=receive(s,state)
  if status['state'] not in ('queued','running'):break
  if time.monotonic()-start>120:raise DemoError('等待超时；不表示Word已停止')
  time.sleep(.2)
 if status['state']!='succeeded':raise DemoError(status.get('error','Word未成功'))
 adopt(s,state);raw=s.downloads()['fixed.docx'];(out/'fixed.docx').write_bytes(raw);(out/'result.zip').write_bytes(s.result_package())
 assert raw==(ROOT/'samples/phase50/fixed.docx').read_bytes(),'local legal path differs from browser download'
 from scripts.verify_word_fields import verify
 proof=verify(out/'before-update.docx',out/'fixed.docx');proof.update(browser_bytes_equal=True,API_requests=0,Word_seconds=round(time.monotonic()-start,3),adoption_Word_calls=0)
 (out/'independent.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proof,ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--word',action='store_true',help='明确启动本机Word，只打开独立合成副本');a=p.parse_args();run(a.output,a.word)

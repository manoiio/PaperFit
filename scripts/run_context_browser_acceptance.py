"""Explicit synthetic browser fixture server. Not a production switch or live API.
Upload samples/phase44/supplement.docx and paste requirements.txt. All session
state, file checks, fixing, rehearsal and adoption still use the original app.
"""
from pathlib import Path
import argparse,json,sys,runpy,os
from urllib.request import OpenerDirector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=18544);args=parser.parse_args()
 import ai.smart_spec as spec
 from ai.short_spec import Settings
 from core.package import DemoError
 original=spec.parse_requirements;expected=(ROOT/'samples/phase44/requirements.txt').read_text().strip()
 response=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':(ROOT/'samples/phase44/expected-overrides.json').read_text()}}]})
 def mocked(text,**kwargs):
  if text!=expected:raise DemoError('受控夹具只处理指定公开补充；没有网络请求')
  return original(text,transport=lambda *_:response,config=Settings('synthetic-only'))
 spec.parse_requirements=mocked
 import ai.semantic_spec as semantic
 semantic.parse_requirements=mocked  # Historical authored mock; explicit legacy compatibility.
 raw_open=OpenerDirector.open
 def offline(self,request,*a,**kw):
  url=request.full_url if hasattr(request,'full_url') else str(request)
  if 'api.deepseek.com' in url:raise AssertionError('All paid HTTP blocked in controlled browser acceptance')
  return raw_open(self,request,*a,**kw)
 OpenerDirector.open=offline
 print('CONTROLLED SYNTHETIC RESPONSE: not live AI; paid HTTP blocked.',flush=True)
 os.chdir(ROOT);sys.argv=['streamlit','run','app.py','--server.address','127.0.0.1','--server.port',str(args.port),'--server.fileWatcherType','none']
 runpy.run_module('streamlit',run_name='__main__')
if __name__=='__main__':main()

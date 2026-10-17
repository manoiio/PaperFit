"""Local acceptance server: same UI and transactions, all paid HTTP hard blocked.
Never injects a model or session_state.
"""
from pathlib import Path
import argparse,sys
from urllib.request import OpenerDirector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18548);a=p.parse_args()
 original=OpenerDirector.open
 def guard(self,request,*args,**kwargs):
  url=request.full_url if hasattr(request,'full_url') else str(request)
  if 'api.deepseek.com' in url:raise AssertionError('Paid endpoint forbidden in local browser acceptance')
  return original(self,request,*args,**kwargs)
 OpenerDirector.open=guard
 from streamlit.web.cli import main as run
 sys.argv=['streamlit','run',str(ROOT/'app.py'),'--server.address','127.0.0.1','--server.port',str(a.port),'--server.fileWatcherType','none'];run()
if __name__=='__main__':main()

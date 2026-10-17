"""Explicit offline browser replay of REVIEWED PUBLIC real responses. ZERO HTTP API.
Only the fixed phase44 synthetic supplement and structure requests are accepted.
No session_state injection. Original command, engine and download paths execute.
"""
import argparse,json,runpy,sys,os
from pathlib import Path
from urllib.request import OpenerDirector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=18546);args=p.parse_args()
    from ai import semantic_spec,structure
    from ai.short_spec import Settings
    from ai.structure_ids import wire_request
    from core.package import DemoError,sha256
    fixture=ROOT/'samples/phase45'
    expected=(ROOT/'samples/phase44/requirements.txt').read_text().strip()
    parse=semantic_spec.parse_requirements;analyze=structure.analyze
    def receipt(result,label):
        r=result['receipt'];r.update(kind='mock_api',source='offline_replay_of_saved_live_response',request_count=0,historical_usage=r.get('usage'),usage=None)
        r['original_attempt_id']=json.loads((fixture/'api-records.json').read_text())['records'][0 if label=='supplement' else 2]['attempt_id']
        return result
    def spec(text,**kwargs):
        if text!=expected:raise DemoError('离线重放只接受固定公开补充输入')
        return receipt(parse(text,config=Settings('offline'),transport=lambda *_:(fixture/'supplement-response.json').read_text()),'supplement')
    def classify(request,**kwargs):
        wire=json.dumps(wire_request(request),ensure_ascii=False,sort_keys=True)
        stored=json.loads((fixture/'structure-request.json').read_text())
        if sha256(wire.encode())!=stored['input_sha256']:raise DemoError('离线重放结构输入不匹配')
        return receipt(analyze(request,config=Settings('offline'),transport=lambda *_:(fixture/'structure-response.json').read_text()),'structure')
    semantic_spec.parse_requirements=spec;structure.analyze=classify
    original=OpenerDirector.open
    def guard(self,request,*a,**kw):
        url=request.full_url if hasattr(request,'full_url') else str(request)
        if 'api.deepseek.com' in url:raise AssertionError('Paid HTTP forbidden in offline browser replay')
        return original(self,request,*a,**kw)
    OpenerDirector.open=guard
    print('OFFLINE REPLAY OF SAVED PUBLIC LIVE RESPONSES; ZERO NEW API REQUESTS',flush=True)
    os.environ.pop('PAPERFIT_PUBLIC_SYNTHETIC_POLICY',None)
    os.chdir(ROOT);sys.argv=['streamlit','run','app.py','--server.address','127.0.0.1','--server.port',str(args.port),'--server.fileWatcherType','none'];runpy.run_module('streamlit',run_name='__main__')
if __name__=='__main__':main()

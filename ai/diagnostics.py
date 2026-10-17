"""Opt-in, bounded PUBLIC SYNTHETIC diagnostics. No production content capture."""
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path
import json,os
from core.package import DemoError,sha256

_ACTIVE=ContextVar('synthetic_diagnostic',default=None)
LIMIT=256*1024
ROOT=Path(__file__).resolve().parents[1]/'work/phase45'
class DiagnosticError(DemoError):
    def __init__(self,records):
        self.diagnostics=records
        super().__init__('AI响应未通过本地校验；未应用，请查看技术诊断（'+str(len(records))+'项）。')

def problem(path,code,reason):return {'path':path,'code':code,'reason':reason}

def exact(data,keys,path):
    if type(data) is not dict:raise DiagnosticError([problem(path,'type','必须是JSON对象')])
    missing=set(keys)-set(data);extra=set(data)-set(keys)
    if missing or extra:raise DiagnosticError([problem(path,'keys','缺少 '+str(sorted(missing))+'；多余 '+str(sorted(extra)))])

class SyntheticCapture:
    def __init__(self,directory,allowed_input_hashes):
        self.directory=Path(directory).resolve();self.allowed=set(allowed_input_hashes)
        root=ROOT
        if not self.directory.is_relative_to(root.resolve()) or not self.allowed:raise DemoError('诊断仅允许本任务忽略目录和明确合成输入哈希')
    def write(self,attempt,kind,data):
        raw=json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2).encode()
        if len(raw)>LIMIT:raise DemoError('合成诊断记录超限；不会截断后继续')
        self.directory.mkdir(parents=True,exist_ok=True)
        path=self.directory/(attempt+'.'+kind+'.json')
        path.write_bytes(raw);path.chmod(0o600)
    def request(self,attempt,text,payload):
        if sha256(text.encode()) not in self.allowed:raise DemoError('未授权的输入不能写入合成诊断或发送')
        if len(list(self.directory.glob('*.request.json')))>=20:raise DemoError('本阶段20次合成请求预算已用尽，未发送')
        self.write(attempt,'request',{'format':'paperfit-synthetic-debug-1','input':text,'input_sha256':sha256(text.encode()),'payload':payload,'prompt_sha256':sha256(json.dumps(payload.get('messages',[])[:1],ensure_ascii=False,sort_keys=True).encode()),'protocol_version':json.loads(text).get('version') if text.startswith('{') else None,'public_synthetic':True})
    def response(self,attempt,raw):
        # Retain content before validation, but never reasoning_content or headers.
        from core.rule_config import strict_json
        try:
            outer=strict_json(raw.decode() if isinstance(raw,bytes) else raw)
            choices=outer.get('choices',[])
            clean=[{'finish_reason':c.get('finish_reason'),'message':{k:v for k,v in c.get('message',{}).items() if k in ('content','tool_calls','function_call')}} for c in choices[:1]]
            self.write(attempt,'response',{'choices':clean,'usage':outer.get('usage')})
        except DemoError as exc:
            self.write(attempt,'response-error',{'error':str(exc),'response_sha256':sha256(raw if isinstance(raw,bytes) else raw.encode())})
    def outcome(self,attempt,record,error=None):
        self.write(attempt,'outcome',{'attempt':record,'diagnostics':getattr(error,'diagnostics',[]),'error':str(error) if error else None})

@contextmanager
def synthetic_capture(directory,allowed_input_hashes):
    token=_ACTIVE.set(SyntheticCapture(directory,allowed_input_hashes))
    try:yield
    finally:_ACTIVE.reset(token)

def active():
    current=_ACTIVE.get()
    if current is not None:return current
    # Explicit synthetic debug service only. No flag is enabled by the app.
    policy=os.environ.get('PAPERFIT_PUBLIC_SYNTHETIC_POLICY')
    if not policy:return None
    path=Path(policy).resolve()
    if not path.is_relative_to(ROOT.resolve()) or path.stat().st_size>8192:raise DemoError('合成诊断配置位置或容量无效')
    from core.rule_config import strict_json
    data=strict_json(path.read_text())
    exact(data,('public_synthetic','allowed_input_hashes','directory'),'synthetic_policy')
    if data['public_synthetic'] is not True or type(data['allowed_input_hashes']) is not list or len(data['allowed_input_hashes'])>8 or any(type(h) is not str or len(h)!=64 for h in data['allowed_input_hashes']):raise DemoError('合成诊断声明无效')
    return SyntheticCapture(data['directory'],data['allowed_input_hashes'])

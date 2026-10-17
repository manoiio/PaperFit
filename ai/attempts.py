"""Bounded receipt journal. Never stores excerpts, responses, headers or secrets."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
import json,time
from urllib.error import HTTPError
from .short_spec import call_json
from core.package import DemoError,sha256

JOURNAL=Path(__file__).resolve().parents[1]/'work/api-attempts.jsonl'
TEST_MODE=False  # Set only by the offline test runner, never by the UI.

def tracked(text,payload,validator,*,purpose,config,transport,real,audit=None):
    real=real and not TEST_MODE
    record={'attempt_id':uuid4().hex,'purpose':purpose,'timestamp_utc':datetime.now(timezone.utc).isoformat(),
            'input_sha256':sha256(text.encode()),'model':config.model,'kind':'real_api' if real else 'mock_api',
            'dispatch_started':False,'sent':False,'response_received':False,'validation':'pending','usage':None,'billing_status':'unknown'}
    def save():
        if real:
            JOURNAL.parent.mkdir(parents=True,exist_ok=True)
            if JOURNAL.exists() and JOURNAL.stat().st_size>2*1024*1024:raise DemoError('请求记录已满，未追加付费请求')
            with JOURNAL.open('a',encoding='utf-8') as f:
                f.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n');f.flush()
        if audit:audit(deepcopy(record))
    from .diagnostics import active
    capture=active()
    if capture:capture.request(record["attempt_id"],text,payload)
    save()  # A failed pre-dispatch write prevents the request.
    started=time.monotonic()
    def once(req,timeout):
        record.update(dispatch_started=True,sent='unknown');save()
        try:response=transport(req,timeout)
        except HTTPError:
            record.update(sent=True,response_received=True);save();raise
        record.update(sent=True,response_received=True)
        if capture:capture.response(record['attempt_id'],response)
        try:
            from core.rule_config import strict_json
            data=strict_json(response.decode() if isinstance(response,bytes) else response)
            usage={k:v for k,v in (data.get('usage') or {}).items() if k in ('prompt_tokens','completion_tokens','total_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens') and type(v) is int and 0<=v<=1000000}
            record['usage']=usage or None
        except (DemoError,ValueError,TypeError,AttributeError):pass
        save();return response
    try:
        result=call_json(text,payload,validator,transport=once,config=config)
        record['validation']='accepted'
    except Exception as exc:
        record.update(validation='rejected',elapsed_seconds=round(time.monotonic()-started,3));save()
        if capture:capture.outcome(record['attempt_id'],record,exc)
        raise
    record['elapsed_seconds']=round(time.monotonic()-started,3);save()
    if capture:
        capture.write(record['attempt_id'],'adapted',result['draft'])
        capture.outcome(record['attempt_id'],record)
    result['receipt'].update(kind=record['kind'],attempt=deepcopy(record),usage=record['usage'])
    return result

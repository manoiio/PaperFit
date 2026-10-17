#!/usr/bin/env python3
"""Replay explicit synthetic snapshots. ZERO API, no settings or network access."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.rule_config import strict_json
from core.package import DemoError,sha256
from ai.short_spec import call_json,Settings
from ai.semantic_spec import adapt as supplement
from ai.structure_ids import adapt as structure

def replay(request,response):
    if request.get('format')!='paperfit-synthetic-debug-1' or request.get('public_synthetic') is not True or sha256(request['input'].encode())!=request['input_sha256']:raise DemoError('诊断输入快照哈希/声明无效')
    wire=strict_json(request['input'])
    if wire['version']=='supplement-ids-v1':validator=lambda d:supplement(d,wire['input'])
    elif wire['version']=='structure-ids-v1':validator=lambda d:structure(d,wire)
    else:raise DemoError('未知诊断协议')
    # Original envelope/protocol gates including finish reason and tool-call protection.
    result=call_json(request['input'],request['payload'],validator,transport=lambda *_:json.dumps(response,ensure_ascii=False),config=Settings('offline-synthetic'))
    return {'kind':'offline_replay','request_count':0,'draft':result['draft']}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('request',type=Path);p.add_argument('response',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    if any(f.stat().st_size>256*1024 for f in (a.request,a.response)):raise SystemExit('Snapshot exceeds 256KiB')
    try:result=replay(strict_json(a.request.read_text()),strict_json(a.response.read_text()))
    except DemoError as exc:result={'kind':'offline_replay','request_count':0,'error':str(exc),'diagnostics':getattr(exc,'diagnostics',[])}
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='draft'},ensure_ascii=False))

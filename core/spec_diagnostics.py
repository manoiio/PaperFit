"""Non-executable diagnosis. Strict rule_bundle validators remain the execution gate."""
from copy import deepcopy
import json,re
from .package import DemoError,sha256
from .rule_config import strict_json
from .norms import marked_text,verify_namespaces
from . import rule_bundle as rb

FORMAT='paper-grid-spec-diagnosis'
MAX_CONTENT=65536
MAX_RECORD=256*1024
MAX_HISTORY=3
MAX_EDITS=100

def require(ok,msg):
 if not ok:raise DemoError(msg)
def sensitive(text):
 return bool(re.search(r'(?:/Users/|/Volumes/|/private/|/tmp/|[A-Za-z]:\\|\bsk-[A-Za-z0-9_-]{8,}|Bearer\s+\S+|(?:API_KEY|Authorization)\s*[:=])',text,re.I))
def stamp():
 from datetime import datetime,timezone
 return datetime.now(timezone.utc).isoformat()
def make_record(segments,content,*,kind='synthetic',finish_reason='stop',tool_calls=False,receipt=None,protocol_error=None,failure_reason=None):
 rb.main.validate_segments(segments);verify_namespaces(segments)
 require(kind in ('synthetic','real_api','mock_api'),'诊断来源类别无效')
 digest=sha256((content or '').encode())
 if not isinstance(content,str):content=None;protocol_error=protocol_error or 'empty_response'
 elif len(content.encode())>MAX_CONTENT:content=None;protocol_error='response_limit'
 elif sensitive(content):content=None;protocol_error='sensitive_response_not_stored'
 r={'format':FORMAT,'version':1,'kind':kind,'segments':deepcopy(segments),'input_sha256':sha256(marked_text(segments).encode()),'content':content,'content_sha256':digest,'finish_reason':finish_reason,'tool_calls':bool(tool_calls),'receipt':deepcopy(receipt),'protocol_error':protocol_error,'edits':[],'failure_reason':failure_reason}
 return validate_record(r)
def validate_record(r):
 rb.exact({k:v for k,v in r.items() if k!='failure_reason'},('format','version','kind','segments','input_sha256','content','content_sha256','finish_reason','tool_calls','receipt','protocol_error','edits'),'诊断记录结构无效')
 require(r.get('failure_reason') is None or type(r['failure_reason']) is str and len(r['failure_reason'])<=200 and not sensitive(r['failure_reason']),'失败说明无效')
 require(r['format']==FORMAT and type(r['version']) is int and r['version']==1 and r['kind'] in ('synthetic','real_api','mock_api'),'诊断版本或来源无效')
 rb.main.validate_segments(r['segments']);verify_namespaces(r['segments'])
 require(r['input_sha256']==sha256(marked_text(r['segments']).encode()),'诊断规范快照哈希不符')
 require(type(r['content_sha256']) is str and re.fullmatch('[a-f0-9]{64}',r['content_sha256']),'诊断响应哈希无效')
 require(r['content'] is None or type(r['content']) is str and len(r['content'].encode())<=MAX_CONTENT and sha256(r['content'].encode())==r['content_sha256'] and not sensitive(r['content']),'诊断原始内容无效/超限/含敏感信息')
 require(r['content'] is not None or r['protocol_error'] is not None,'缺失原响应不能当作完整响应')
 require(r['finish_reason'] is None or type(r['finish_reason']) is str and len(r['finish_reason'])<=40 and not sensitive(r['finish_reason']),'结束状态无效')
 require(type(r['tool_calls']) is bool and (r['protocol_error'] is None or r['protocol_error'] in ('request_failed','protocol_failure','empty_response','response_limit','sensitive_response_not_stored')),'协议诊断状态无效')
 if r['receipt'] is not None:
  x=r['receipt'];rb.exact(x,('kind','model','timestamp_utc','request_count','elapsed_seconds'),'请求回执无效')
  require(x['kind'] in ('real_api','mock_api') and x['kind']==r['kind'] and x['model'] in ('deepseek-flash','deepseek-v4-pro'),'请求来源无效')
  from datetime import datetime
  try:datetime.fromisoformat(x['timestamp_utc'])
  except (TypeError,ValueError):raise DemoError('请求时间无效') from None
  require(type(x['request_count']) is int and x['request_count']==1 and type(x['elapsed_seconds']) in (float,int) and __import__('math').isfinite(x['elapsed_seconds']) and 0<=x['elapsed_seconds']<=3600,'请求计数或时间无效')
 require(type(r['edits']) is list and len(r['edits'])<=MAX_EDITS,'本地修复记录最多100项')
 for e in r['edits']:validate_edit(e)
 require(len(rb.raw(r))<=MAX_RECORD,'单份诊断记录超过256KB')
 return deepcopy(r)
def validate_edit(e):
 rb.exact(e,('path','action','data','reason'),'修复记录结构无效')
 require(type(e['path']) is str and re.fullmatch(r'(main|front|toc|notes)\.(fields\.[A-Za-z0-9_]+|issues\.\d{1,3})',e['path']),'修复定位无效')
 m,group,n=e['path'].split('.')
 require(group!='fields' or n in rb.FIELDS[m],'修复字段未知')
 require(e['action'] in (('candidate','manual','disabled') if group=='fields' else ('issue',)),'修复方式无效')
 rb.main.safe_text(e['reason'],200)
 if e['action']=='candidate':
  rb.exact(e['data'],('value','unit','quote','location','support'),'候选修复结构无效')
  require(len(rb.raw(e['data']))<=2048 and not sensitive(json.dumps(e['data'],ensure_ascii=False)),'修复字段超限/含敏感内容')
 elif e['action']=='manual':rb.validate_value(m,n,e['data']);require(e['data'] is not None,'手动值不得为空')
 elif e['action']=='disabled':require(e['data'] is None,'不检查决定不能带值')
 else:
  rb.exact(e['data'],('fields','quote','location','reason'),'提示修复结构无效')
  require(len(rb.raw(e['data']))<=4096 and not sensitive(json.dumps(e['data'],ensure_ascii=False)),'提示修复超限/含敏感内容')

def decoded(r):
 require(not r['tool_calls'],'tool_call')
 if r['protocol_error']:raise DemoError(r['protocol_error'])
 require(r['finish_reason']=='stop','incomplete_finish')
 require(type(r['content']) is str and r['content'].strip(),'empty_response')
 d=strict_json(r['content'])
 rb.exact(d,rb.MODULES,'unknown_or_missing_module')
 for m,p in d.items():
  rb.exact(p,('fields','issues'),'unknown_module_structure')
  require(type(p['fields']) is dict and set(p['fields'])<=set(rb.FIELDS[m]),'unknown_executable_field')
  require(type(p['issues']) is list and len(p['issues'])<=100,'issue_structure_limit')
 return d

def suggestion(f,segments):
 if not isinstance(f,dict) or not isinstance(f.get('quote'),str) or not f['quote'] or not re.fullmatch(r'L\d+',str(f.get('location'))):return None
 # Both the original line number and continuous quote must identify one source. Repeated text is ambiguous.
 containing=[s for s in segments if f['quote'] in s['text']]
 prefixes={s['location'].rsplit(':L',1)[0] for s in segments}
 matches=[s for s in containing if s['location'].endswith(':'+f['location'])]
 if len(containing)==len(matches)==len(prefixes)==1:return {'from':f['location'],'to':matches[0]['location'],'text':matches[0]['text']}
 return None

def diagnose(record):
 r=validate_record(record)
 out={'status':'isolated','network':'无网络（合成或历史导入）' if not r['receipt'] else '请求已记录；不等于规则通过','records':[],'fields':{},'issues':{},'unresolved':[],'strict_draft':None,'user_confirmed':[],'decisions':{},'summary':{}}
 try:d=decoded(r)
 except (DemoError,ValueError,TypeError,UnicodeError,KeyError,RecursionError) as exc:
  reason=str(exc)
  code='DUPLICATE_JSON_KEY' if '重复' in reason else 'INVALID_JSON' if 'JSON' in reason else 'TOOL_CALL' if reason=='tool_call' else 'INCOMPLETE_FINISH' if reason=='incomplete_finish' else 'RESPONSE_LIMIT' if reason=='response_limit' else 'REQUEST_FAILURE' if reason=='request_failed' else 'PROTOCOL_OR_STRUCTURE'
  out.update(status='rejected',code=code,reason=(r.get('failure_reason') or reason)+'；请求/协议或整体结构拒绝；不拼接JSON、不删除危险字段。',summary={'qualified':0,'isolated':0,'missing':0,'errors':1});return out
 edits={e['path']:e for e in r['edits']};tainted=set();block={m:set() for m in rb.MODULES};validissues={m:[] for m in rb.MODULES}
 def error(path,code,reason,raw,affected,methods):
  source=next((s['text'] for s in r['segments'] if isinstance(raw,dict) and s['location']==raw.get('location')),None)
  out['records'].append({'path':path,'module':path.split('.')[0],'code':code,'reason':reason,'raw':deepcopy(raw),'source':source or '找不到对应原文位置','affected':affected,'allowed':False,'methods':methods})
 for m,p in d.items():
  for i,original in enumerate(p['issues']):
   path=f'{m}.issues.{i}';e=edits.get(path);issue=e['data'] if e else original
   original_fields=original.get('fields') if isinstance(original,dict) else None
   original_known=[n for n in original_fields if type(n) is str and n in rb.FIELDS[m]] if type(original_fields) is list else []
   unknown=type(original_fields) is not list or len(original_known)!=len(original_fields)
   impacted=set(rb.FIELDS[m]) if unknown else set(original_known)
   if e:tainted.update(m+'.'+n for n in impacted)
   valid=True
   try:rb.validate_notices({x:[issue] if x==m else [] for x in rb.MODULES},r['segments'])
   except (DemoError,TypeError,ValueError):
    valid=False;error(path,'ISSUE_INVALID','提示字段、原因或连续原句/来源无效；原影响范围继续隔离',original,[m+'.'+n for n in sorted(impacted)],['修正提示来源与关联','明确改为无执行关联说明'])
   declared=issue.get('fields') if valid else None
   related=set(declared) if valid else impacted
   block[m].update(related)
   if not valid:out['unresolved'].append(path)
   else:
    validissues[m].append(deepcopy(issue))
    if related:error(path,'ISSUE_BLOCK','提示仍阻止这些字段；需明确手动取舍/不检查，或修正关联',original,[m+'.'+n for n in sorted(related)],['保留阻止关系','逐字段手动/不检查','明确修正关联'])
   out['issues'][path]={'original':deepcopy(original),'effective':deepcopy(issue),'valid':valid,'edited':bool(e),'affected':[m+'.'+n for n in sorted(related)]}
 strict={m:{'fields':{},'issues':validissues[m]} for m in rb.MODULES}
 for m in rb.MODULES:
  for n in rb.FIELDS[m]:
   path=f'{m}.fields.{n}';short=m+'.'+n;raw=d[m]['fields'].get(n);e=edits.get(path);candidate=e['data'] if e and e['action']=='candidate' else raw
   errors=[]
   def add(code,msg):errors.append(code);error(path,code,msg,raw,[short],['修复来源/连续原句','手动指定或不检查'])
   if candidate is not None:
    if type(candidate) is not dict or set(candidate)!=set(('value','unit','quote','location','support')):add('FIELD_STRUCTURE','已知字段的候选结构错误')
    else:
     try:rb.validate_value(m,n,candidate['value']);require(candidate['value'] is not None,'null')
     except (DemoError,TypeError,ValueError):add('VALUE','数值类型、范围或枚举无效')
     if candidate['unit']!=rb.FIELDS[m][n][2] or candidate['support']!='supported':add('UNIT_SUPPORT','单位或支持状态不符，不自动转换')
     source=next((s for s in r['segments'] if s['location']==candidate['location']),None)
     if source is None:add('LOCATION','来源标记不存在；可核对唯一映射')
     elif type(candidate['quote']) is not str or not candidate['quote'] or candidate['quote'] not in source['text']:add('QUOTE','quote不是该来源内的连续原文')
     try:rb.validate_candidate(m,n,candidate,r['segments'])
     except (DemoError,TypeError,ValueError):
      if not errors:add('OBJECT_OR_CONFLICT','对象/数值依据或整份规范存在冲突，需核对所有原句')
   if n in block[m]:errors.append('ISSUE_BLOCK')
   if short in tainted and e is None and candidate is not None:
    add('ASSOCIATION_DECISION','提示关联已改；此字段仍须明确核对后以用户确认值采用')
   if e and e['action'] in ('manual','disabled'):
    state='user_confirmed';out['decisions'][short]=deepcopy(e);out['user_confirmed'].append(short)
   elif errors:
    state='isolated';out['unresolved'].append(path)
   elif candidate is None:state='missing'
   else:
    state='user_confirmed' if e or short in tainted else 'qualified'
    strict[m]['fields'][n]=deepcopy(candidate)
    if state=='user_confirmed':out['user_confirmed'].append(short)
   out['fields'][short]={'state':state,'candidate':deepcopy(candidate),'raw':deepcopy(raw),'suggestion':suggestion(raw,r['segments']),'codes':errors,'allowed':state in ('qualified','user_confirmed'),'methods':['核对后采用'] if state=='qualified' else ['修复来源/原句','明确手动或不检查'] if state=='isolated' else []}
 # All local repairs still run the original full-source/module validator, without narrowing excerpts.
 if not out['unresolved']:
  try:rb.validate_draft(strict,r['segments']);out['strict_draft']=strict;out['status']='validated'
  except (DemoError,TypeError,ValueError):out['unresolved'].append('all');error('main.fields.font_size','FULL_VALIDATION','整份规范/模块重新校验未通过',None,[],['核对完整规范与全部决定'])
 counts={s:sum(f['state']==s for f in out['fields'].values()) for s in ('qualified','isolated','missing','user_confirmed')};counts['errors']=len(out['records']);out['summary']=counts
 return out

def revise(record,path,action,data,reason):
 r=validate_record(record);require(diagnose(r)['status']!='rejected','整体拒绝的响应不可本地改造成执行草稿')
 e={'path':path,'action':action,'data':deepcopy(data),'reason':reason};validate_edit(e)
 d=decoded(r);m,g,n=path.split('.');require(g=='fields' or int(n)<len(d[m]['issues']),'提示索引无效')
 if action=='candidate':rb.validate_candidate(m,n,data,r['segments'])
 if action=='issue':rb.validate_notices({x:[data] if x==m else [] for x in rb.MODULES},r['segments'])
 r['edits'].append(e);return validate_record(r)

def validate_store(store):
 rb.exact(store,('current','history','adopted_sha256'),'诊断存储结构无效')
 require(type(store['history']) is list and len(store['history'])<=MAX_HISTORY,'历史诊断最多3份；请明确导出/清理后继续')
 for r in store['history']+([store['current']] if store['current'] else []):validate_record(r)
 require(len(rb.raw(store))<=1024*1024,'诊断存储超过1MB')
 if store['adopted_sha256'] is not None:require(store['current'] is not None and store['adopted_sha256']==rb.digest(store['current']) and diagnose(store['current'])['status']=='validated','诊断采用状态无效')
 return deepcopy(store)

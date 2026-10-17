"""Isolate overlapping paragraph requirements before selection; never last-write wins."""
import json
from .paragraph_values import token

def isolate(report):
 groups={}
 for f in report['findings']:
  loc=f['locator'];prop=loc.get('property')
  if any(k in loc for k in ('run','link_run','start')) or not ('paragraph' in loc or 'note_paragraph' in loc):continue
  prop='line' if f['rule_id']=='R06' or prop in ('line','line_multiple','line_spacing') else 'indent' if f['rule_id']=='R07' or prop=='first_line_indent' else prop
  if prop not in ('line','indent','before','after','alignment') or f['status'] not in ('problem','pass'):continue
  d=f['expected'];d=d.get('multiple',d) if isinstance(d,dict) else d
  if prop=='line':value=token(d,'line')
  elif prop=='indent':
   if isinstance(d,dict) and set(d)=={'chars'}:d=d['chars']
   value=token(d,'first_line_indent')
  else:value=json.dumps(d,sort_keys=True)
  identity=(f.get('story_part'),*(loc.get(k) for k in ('paragraph','note_kind','note_id','note_paragraph')),prop)
  groups.setdefault(identity,[]).append((f,value))
 for group in groups.values():
  if len({v for _,v in group})<2:continue
  for f,_ in group:f.update(status='review',fixable=False,detail='同一段落属性存在不同规则要求，未按执行顺序覆盖；请调整规则。')
 s=report['summary']
 for status,name in [('problem','problem_count'),('review','review_findings'),('pass','pass_count'),('not_applicable','not_applicable_count')]:s[name]=sum(f['status']==status for f in report['findings'])
 s['review_count']=s['review_findings']+len(report['coverage_notes'])
 s['conclusion']='已覆盖检查发现问题' if s['problem_count'] else '已覆盖检查未发现问题'

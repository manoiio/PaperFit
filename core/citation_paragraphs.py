"""Evidence for a narrowly scoped paragraph exception, never an inline exemption.

Only confirmed, hash-bound citation characters may account for superscript.
Whitespace outside those intervals is NOT excused. Baseline whitespace is
retained in the range map but is never a point-indent size/width basis.
"""
from bisect import bisect_right
from copy import deepcopy
import json
from .package import q,sha256
from .formats import Resolver,Unresolved
from .citations import validate_scope,inventory,safe,text,syntax_mode
PROPERTIES=('R06.line_spacing','R07.first_line_indent','R13.before','R13.after','R13.alignment')
LIMIT='仅解除已确认引文上标对指定段落属性的阻止；引文行内字体/字号及原有复杂结构仍保护。XML声明符合不证明像素间距、实际分页或全文合格。'

def build(pkg,classification):
 if not classification or not classification.get('citation_scope'):return {}
 scope=validate_scope(pkg,classification['citation_scope'],classification)
 inv=inventory(pkg,scope['scan'],scope['template']);res=Resolver(pkg);grouped={n:[] for n in scope['scan']}
 for row in inv['objects']:grouped[row['paragraph']].append(row)
 result={};binding=sha256(json.dumps(scope,ensure_ascii=False,sort_keys=True).encode())
 for n,rows in grouped.items():
  p=pkg.paragraphs[n-1];all_text=text(p);citations=[r for r in rows if scope['objects'].get(r['id'])=='citation' and r['parsed']['supported'] and r['safe_structure']]
  out={'paragraph':n,'input_sha256':pkg.hash,'scope_sha256':binding,'syntax':syntax_mode(scope['template']),'scope_complete':scope['complete'],'structurally_safe':False,'has_superscript':False,'verified_citations':[{'id':r['id'],'start':r['start'],'end':r['end'],'raw':r['text'],'syntax':r['syntax'],'vertical_evidence':r['evidence']} for r in citations],'ordinary_ranges':[],'ordinary_basis_runs':[],'recognized_superscript':[],'blockers':[],'eligible_properties':[],'whitespace_policy':'基线空白保留且不作字号/宽度依据；引文范围外的上标空白也阻止放行；空run不推断用途。','limit':LIMIT}
  result[n]=out
  try:
   reason=safe(p,res)
   if reason:raise Unresolved(reason)
   if len(p.findall(q('pPr')))>1:raise Unresolved('重复段落属性容器')
   pl=res.layers(p,kind='pPr')
   for layer in pl:
    for tag in ('snapToGrid','contextualSpacing'):
     values=layer.findall(q(tag))
     if len(values)>1 or values and values[0].get(q('val'),'1') not in ('0','1','false','true','off','on'):raise Unresolved('重复或未知段落OnOff属性：'+tag)
   # Only an absent/default single grid proves no grid effect. Unknown or
   # duplicated grids stay conservative for the new exception, even if their
   # first declaration happens to look disabled. Alignment/char units remain
   # independently readable; no pixel/layout conclusion is inferred.
   grids=[s.findall(q('docGrid')) for s in pkg.sections]
   out['grid_active']=any(len(gs)>1 or any(g.get(q('type')) not in (None,'default') for g in gs) for gs in grids) and res.value(pl,'snapToGrid','1') not in ('0','false','off')
   if any(x.find(q('numPr')) is not None for x in pl):raise Unresolved('自动编号/列表依赖仍保护，不豁免段落属性')
   spans=[(r['start'],r['end']) for r in citations];ends=[b for a,b in spans];offset=0
   for i,r in enumerate(p.findall(q('r')),1):
    tx=text(r);stop=offset+len(tx);layers=res.layers(p,r)
    for layer in layers:
     for tag in ('position','rtl','cs','vanish','webHidden','w'):
      if len(layer.findall(q(tag)))>1:raise Unresolved('重复字符属性：'+tag)
    value=res.value(layers,'vertAlign','baseline')
    # Validate every other existing special guard on COPIES, after scope proof.
    copies=deepcopy(layers)
    for layer in copies:
     for e in list(layer.findall(q('vertAlign'))):layer.remove(e)
    other=res.special(r,copies)
    if other:raise Unresolved(other)
    covered=[];cursor=offset;j=bisect_right(ends,offset)
    while j<len(spans) and spans[j][0]<stop:
     a,b=spans[j];a=max(a,offset);b=min(b,stop)
     if cursor<a:out['ordinary_ranges'].append({'run':i,'start':cursor,'end':a,'non_whitespace':bool(all_text[cursor:a].strip())})
     covered.append((a,b));cursor=b;j+=1
    if cursor<stop:out['ordinary_ranges'].append({'run':i,'start':cursor,'end':stop,'non_whitespace':bool(all_text[cursor:stop].strip())})
    if value=='superscript':
     out['has_superscript']=True
     if sum(b-a for a,b in covered)!=len(tx):raise Unresolved(f'run{i}存在确认引文区间外的上标（包括空白），不能豁免整段')
     out['recognized_superscript'].append({'run':i,'start':offset,'end':stop,'value':value,'source':next((res._layer_origin(layer) for layer in reversed(layers) if layer.find(q('vertAlign')) is not None),'未知')})
    elif value!='baseline':raise Unresolved('非确认引文上标：下标/未知vertAlign继续保护')
    offset=stop
   if any(any(ch in '\u00b2\u00b3\u00b9' or 0x2070<=ord(ch)<=0x209f for ch in all_text[x['start']:x['end']]) for x in out['ordinary_ranges']):raise Unresolved('引文范围外存在Unicode上下标字符，未作为普通文字宽度依据')
   if not out['has_superscript']:raise Unresolved('本段没有需要有限放行的已确认引文上标；保持原检查路径')
   out['ordinary_basis_runs']=list(dict.fromkeys(x['run'] for x in out['ordinary_ranges'] if x['non_whitespace']))
   out.update(structurally_safe=True,eligible_properties=list(PROPERTIES))
  except Unresolved as exc:out['blockers'].append(str(exc))
 return result

def finalize(report):
 grouped={}
 for f in report['findings']:grouped.setdefault(f['locator'].get('paragraph'),[]).append(f)
 for proof in report['coverage'].get('citation_paragraph_evidence',[]):
  checks=[]
  for f in grouped.get(proof['paragraph'],[]):
   prop='line_spacing' if f['rule_id']=='R06' else 'first_line_indent' if f['rule_id']=='R07' else f.get('property') if f['rule_id']=='R13' else None
   key=f['rule_id']+'.'+str(prop)
   if key not in PROPERTIES:continue
   checks.append({'property':key,'key':f['key'],'status':f['status'],'fixable':f['fixable'],'reason':f['detail']})
   if proof['has_superscript'] or proof['recognized_superscript']:
    f['citation_paragraph_evidence']={'paragraph':proof['paragraph'],'scope_sha256':proof['scope_sha256'],'structurally_safe':proof['structurally_safe'],'syntax':proof['syntax']}
    if proof['structurally_safe']:
     f['detail']=(f['detail']+'；' if f['detail'] else '')+'上标仅位于精确确认引文内；本项独立读取段落属性，引文行内格式仍保护。'
    elif proof['blockers']:f['detail']+='；引文段落证据未放行：'+'；'.join(proof['blockers'])
  proof['checks']=checks;proof['allowed_properties']=[x['property'] for x in checks if proof['structurally_safe'] and x['status'] in ('pass','problem')]
  proof['property_blockers']=[{'property':x['property'],'reason':x['reason']} for x in checks if x['status']=='review']

"""L05 separate, atomic, exact object-permutation transaction and identity-based rebinding."""
from copy import deepcopy
from pathlib import Path
from lxml import etree as E
from .package import Package,DemoError,q,NS,sha256,new_path,write_new
from .captions import analyze,objects,SOURCE,LIMITS
from .classification import validate_classification
from .engine import _rules,_confirmed_scope,_check
from .table_text import rebind
from .dependencies import problem_delta

def canonical(e):return E.tostring(e,method='c14n')

def remap_manifest(pkg,m,old_paragraphs,old_toc,new_hash):
 """Identity mapping, never matching by text. No markers added to source."""
 from .toc import nodes
 newps=pkg.root.find(q('body')).findall(q('p'));pmap={str(n):str(newps.index(p)+1) for n,p in enumerate(old_paragraphs,1)}
 nt=nodes(pkg);dmap={'d:'+str(n):'d:'+str(nt.index(p)+1) for n,p in enumerate(old_toc,1)}
 allowed={'input_sha256','paragraph_types','confirmed','confirmation','material_exclusions','table_scope','front_scope','toc_scope','citation_scope','note_scope','caption_scope'}
 if set(m)-allowed:raise DemoError('存在未支持定位范围，禁止移动；请先人工核对其重绑能力')
 out=deepcopy(m);out['input_sha256']=new_hash;out['paragraph_types']={pmap[n]:v for n,v in m['paragraph_types'].items()}
 if m.get('material_exclusions'):out['material_exclusions']={pmap[n]:v for n,v in m['material_exclusions'].items()}
 if m.get('front_scope'):
  out['front_scope']['objects']={('p:'+pmap[k[2:]] if k.startswith('p:') else k):v for k,v in m['front_scope']['objects'].items()}
 if m.get('toc_scope'):out['toc_scope']['objects']={dmap[k]:v for k,v in m['toc_scope']['objects'].items()}
 if m.get('citation_scope'):
  s=out['citation_scope'];s['scan']=sorted(int(pmap[str(n)]) for n in s['scan']);os={}
  for key,v in s['objects'].items():
   tag,n,start,end=key.split(':');os[f'{tag}:{pmap[n]}:{start}:{end}']=v
  s['objects']=os
 if m.get('caption_scope'):
  s=out['caption_scope'];s['captions']={pmap[n]:v for n,v in s['captions'].items()};s['chapter_map']={pmap[n]:v for n,v in s['chapter_map'].items()};s['associations']={pmap[n]:('image:p:'+pmap[o[8:]] if o.startswith('image:p:') else o) for n,o in s['associations'].items()}
 rebind(out,new_hash)
 # Validate against a current in-memory view before writing output. Includes citation offsets/types.
 pkg.paragraphs=newps;previous=pkg.hash;pkg.hash=new_hash
 try:validate_classification(pkg,out)
 finally:pkg.hash=previous
 return out,{'paragraphs':pmap,'toc_objects':dmap,'table_ids':'unchanged','citation_offsets':'文字子树保持，段号按对象重绑；字符范围不变','material_exclusions':'按原始XML对象身份重绑，含重复文本也不合并','invalidated':['旧修正选择','旧布局/宽度计划','不匹配的预览和缓存'],'method':'执行前内存XML对象身份映射；无新增文档标记、无文字匹配'}

def mapped_delta(before,after,mapping):
 """Problem identity follows object permutation; no fake new issues from shifted p:N."""
 b=deepcopy(before);targets={(f['rule_id'],f.get('property',f['locator'].get('property')),str(sorted(f['locator'].items()))):f['key'] for f in after['findings']}
 for f in b['findings']:
  loc=f['locator'];n=loc.get('paragraph')
  if n is not None:loc['paragraph']=int(mapping['paragraphs'][str(n)])
  if loc.get('toc_object') is not None:loc['toc_object']=int(mapping['toc_objects']['d:'+str(loc['toc_object'])][2:])
  if 'citation' in loc and isinstance(loc['citation'],str) and loc['citation'].startswith('c:'):
   tag,n,a,z=loc['citation'].split(':');loc['citation']=f'{tag}:{mapping["paragraphs"][n]}:{a}:{z}'
  key=targets.get((f['rule_id'],f.get('property',f['locator'].get('property')),str(sorted(loc.items()))))
  if key:f['key']=key
 d=problem_delta(b,after);d['identity_basis']='已按XML对象映射比较；不把段号移动误计为新增/解决格式问题';return d

def apply_caption_positions(input_path,output_path,body=None,rules_path=None,*,custom_rules_path=None,mode='academic',classification_manifest=None,confirmed_keys=()):
 if mode!='academic':raise DemoError('L05须在单文档模式确认题注范围')
 new_path(output_path,input_path);pkg=Package(input_path);raw=pkg.raw;m=validate_classification(pkg,classification_manifest)
 if not m.get('caption_scope') or not m['caption_scope']['template']['position']:raise DemoError('请先明确启用、核对题注关联与位置检查')
 frozen=_rules(rules_path,custom_rules_path,mode);body,m=_confirmed_scope(pkg,body,mode,m);a=analyze(pkg,m['caption_scope'],m)
 keys=list(confirmed_keys)
 if not keys or len(set(keys))!=len(keys):raise DemoError('请明确选择唯一的L05位置纠正对象')
 plans={p['key']:p for p in a['positions']}
 if any(k not in plans or not plans[k]['movable'] for k in keys):raise DemoError('所选位置纠正不安全或已失效；请查看具体阻止原因，不能绕过保护')
 parent=pkg.root.find(q('body'));original=list(parent);oldps=list(pkg.paragraphs)
 from .toc import nodes
 oldtoc=nodes(pkg);obs=objects(pkg);pairs=[];used=set()
 for k in keys:
  plan=plans[k];c=oldps[plan['paragraph']-1];obj=obs[plan['object']]['element']
  if c in used or obj in used:raise DemoError('重叠或冲突的移动计划，禁止执行')
  used.update((c,obj));pairs.append((plan,c,obj))
 before=_check(pkg,body,frozen,m);baseline=[canonical(x) for x in original];root_before=canonical(pkg.root)
 expected=list(original)
 for plan,c,obj in pairs:
  ci=expected.index(c);oi=expected.index(obj)
  if abs(ci-oi)!=1:raise DemoError('关联不再紧邻，禁止移动')
  expected[ci],expected[oi]=expected[oi],expected[ci]
 # Reorder existing nodes only. No clear/copy, text/style edits or ancillary writes.
 for node in expected:parent.append(node)
 if any(canonical(x)!=baseline[original.index(x)] for x in expected):raise DemoError('位置事务改变了对象子树，已阻止')
 # Reverse the authorized permutation and compare the entire root, including attributes and tails.
 for node in original:parent.append(node)
 if canonical(pkg.root)!=root_before:raise DemoError('位置事务影响了其他结构，已阻止')
 for node in expected:parent.append(node)
 rawout=pkg.bytes(True);outhash=sha256(rawout)
 outm,mapping=remap_manifest(pkg,m,oldps,oldtoc,outhash)
 # No stale pre-move index is accepted into current output. Preflight complete before writing.
 if pkg.path.read_bytes()!=raw:raise DemoError('原稿执行期间变化，禁止保存')
 write_new(output_path,rawout,input_path)
 try:
  fresh=Package(output_path);after=_check(fresh,sorted(int(n) for n,t in outm['paragraph_types'].items() if t=='body'),frozen,outm)
  read_children=list(fresh.root.find(q('body')))
  if [canonical(e) for e in read_children]!=[baseline[original.index(e)] for e in expected]:raise DemoError('落盘对象排列或子树核对失败')
  if any(fresh.parts.get(name)!=content for name,content in pkg.parts.items() if name!='word/document.xml') or set(fresh.parts)!=set(pkg.parts):raise DemoError('未选部件字节发生变化')
  if Path(input_path).read_bytes()!=raw:raise DemoError('原稿哈希变化')
  from .captions import analyze as reanalyze
  positions=reanalyze(fresh,outm['caption_scope'],outm)['positions'];by={r['paragraph']:r for r in positions}
  changes=[]
  for plan,c,obj in pairs:
   n=int(mapping['paragraphs'][str(plan['paragraph'])]);r=by[n]
   if r['status']!='pass':raise DemoError('落盘结构位置复查未通过')
   changes.append({'rule_id':'L05','locator':{'paragraph':plan['paragraph']},'property':'caption_position','before':{'order':plan['current_order'],'caption_paragraph':plan['paragraph'],'body_object':plan['caption_body_object']},'after':{'order':r['current_order'],'caption_paragraph':n,'body_object':r['caption_body_object']},'verification':'pass','source':SOURCE})
  return {'kind':'caption_position','before':before,'after':after,'changes':changes,'output':str(output_path),'skipped_review_keys':[],'output_body_manifest':{'input_sha256':outhash,'body_paragraphs':after['coverage']['body_paragraphs'],'confirmation':'已验证XML对象映射后重绑'},'output_classification_manifest':outm,'input_classification_manifest':deepcopy(m),'range_mapping':mapping,'problem_delta':mapped_delta(before,after,mapping),'caption_move':{'message':'已纠正所选题注的XML结构位置','limitation':LIMITS[-1],'visual_status':'not_reviewed','authorized_keys':keys},'preservation':{'original_sha256_unchanged':True,'only_authorized_caption_permutation':True,'all_object_subtrees_equal':True,'remaining_objects_relative_order_equal':True,'other_zip_member_bytes_equal':True,'text_order':'仅授权题注位置变化；未声称全文文字顺序不变','verified_objects':['所有主文档XML子树','图片/表格/段落属性','关系/媒体/编号/样式/分节','未选部件逐字节']}}
 except Exception:
  Path(output_path).unlink(missing_ok=True);raise

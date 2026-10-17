"""Author-selected old legal transactions, not the new auxiliary planner.
Explicit --word integration; offline tests and inspection do not start Word.
"""
from pathlib import Path
import sys,json,argparse,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def run(out,use_word=False):
 if not use_word:raise SystemExit('Use --word explicitly for the native integration demo; ordinary offline tests use mocked Word.')
 from urllib.request import OpenerDirector
 def blocked(*a,**k):raise AssertionError('No network in local legal path')
 OpenerDirector.open=blocked
 from copy import deepcopy
 from core.package import Package,sha256
 from core import captions,caption_move,page_layout,widths,layout,word_fields
 from web.session import WebSession
 from web.smart_session import suggest,accept_scope,execute
 out=Path(out);out.mkdir(parents=True,exist_ok=False);started=time.monotonic();s=WebSession(out/'task');s.set_mode('academic');s.load((ROOT/'samples/phase51/source.docx').read_bytes(),'公开合成.docx');s.import_rule_bundle((ROOT/'samples/phase51/rules.json').read_bytes());s.apply_workbench(acknowledged=True)
 s.set_types(json.loads((ROOT/'samples/phase51/accepted-roles.json').read_text()));s.set_table_enabled(True);s.set_table_types({'1':'cover','2':'content','3':'pending'});s.confirm_tables();s.confirm_classification();s.confirm();assert s.check()
 plan=accept_scope(s,suggest(s),confirmation_text='作者预先核对的等价合法范围');execute(s,plan,{})
 source=Path(s.result['output']);(out/'01-format.docx').write_bytes(source.read_bytes());m=deepcopy(s.result['output_classification_manifest']);args=s._base_rules_arguments();records=[]
 c=captions.make_scope(Package(source));c.update(confirmed=True,confirmation='作者手写唯一关联，部分范围',captions={'10':'normal','13':'normal'},associations={'10':'image:p:11','13':'table:2'});m['caption_scope']=c
 r=caption_move.apply_caption_positions(source,out/'02-position.docx',mode='academic',classification_manifest=m,confirmed_keys=['L05:10:image:p:11'],**args);records.append(r);m=r['output_classification_manifest'];source=Path(r['output'])
 # Literal author-known region starts; not produced by automatic().
 policy=s.current_rule_bundle()['assembly'];regions=[{'start':n,'role':role,'format':fmt,'restart':start,'footer':'chapter' if role=='body' else 'page','text':title,'alignment':'center'} for n,role,fmt,start,title in [(1,'cover','decimal',None,''),(3,'front','lowerRoman',1,''),(8,'body','decimal',1,'第1章 合成方法'),(17,'body','decimal',None,'第2章 合成结果')]]
 p=page_layout.propose(source,m,policy,regions);r=page_layout.rehearse(source,out/'03-pages.docx',m,p,**args);records.append(r);m=r['output_classification_manifest'];source=Path(r['output'])
 p=widths.check_widths(source,rules_sha256=s.rules_hash);r=widths.apply_width_adaptation(source,out/'04-width.docx',mode='academic',classification_manifest=m,plan=p,selected_keys=['W02:paragraph=10','W01:table=2'],**args);records.append(r);m=r['output_classification_manifest'];source=Path(r['output'])
 m['table_scope']['layout_options']={'version':1,'outer_edges':False,'headers':{'2':1}}
 r=layout.apply_pagination_layout(source,out/'05-pagination.docx',mode='academic',classification_manifest=m,confirmed_keys=['L01:10:11','L03:3:4','L02:13:2'],**args);records.append(r);m=r['output_classification_manifest'];source=Path(r['output'])
 r=word_fields.update(source,out/'06-final.docx',m,word_fields.plan(source,m),artifact_dir=out/'word');records.append(r)
 browser=(ROOT/'samples/phase51/fixed.docx').read_bytes();actual=Path(r['output']).read_bytes();assert actual==browser,'Legal path output differs from actual browser download'
 proof={'same_bytes_as_browser':True,'sha256':sha256(actual),'manual_auxiliary_keys':{'position':['L05:10:image:p:11'],'width':['W02:paragraph=10','W01:table=2'],'pagination':['L01:10:11','L03:3:4','L02:13:2']},'API_requests':0,'seconds':round(time.monotonic()-started,3),'adoption_fix_calls':0,'Word_passes':r['proof']['passes']}
 (out/'proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in proof.items() if k!='Word_passes'},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--word',action='store_true');a=p.parse_args();run(a.output,a.word)

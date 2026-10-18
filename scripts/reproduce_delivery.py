"""Original legal transactions versus actual starter downloads. No paid HTTP.
--word explicitly uses this Mac's isolated Word calculator for the complete case.
"""
from pathlib import Path
import sys,json,argparse,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def run(folder,word=False,only=None):
 from urllib.request import OpenerDirector
 OpenerDirector.open=lambda *_a,**_kw:(_ for _ in ()).throw(AssertionError('Network forbidden'))
 from web.session import WebSession
 from web.smart_session import suggest,accept_scope
 from core import fix_document
 from core.package import sha256,Package
 from copy import deepcopy
 from core import captions,caption_move,page_layout,widths,layout,word_fields
 out=Path(folder);out.mkdir(parents=True,exist_ok=False);records={}
 for name in ([only] if only else ('basic','complete')):
  if name=='complete' and not word:continue
  source=ROOT/'samples/start-here'/name
  s=WebSession(out/name);s.set_mode('academic');s.load((source/'原稿.docx').read_bytes(),'原稿.docx');s.import_rule_bundle((source/'排版要求.json').read_bytes());s.apply_workbench(acknowledged=True)
  if name=='basic':
   s.set_table_enabled(True);s.set_table_types({'1':'content'});s.confirm_tables()
  if name=='complete':
   s.set_types(json.loads((ROOT/'samples/phase51/accepted-roles.json').read_text()));s.set_table_enabled(True);s.set_table_types({'1':'cover','2':'content','3':'pending'});s.confirm_tables();s.confirm_classification();s.confirm();s.check()
  p=accept_scope(s,suggest(s),confirmation_text='相同公开样本的合法范围');keys=p['keys'];before=sha256(s.input_path.read_bytes());t=time.monotonic()
  r=fix_document(s.input_path,out/(name+'-01-format.docx'),s.confirmed,selected_keys=keys,**s._rules_arguments());path=Path(r['output']);steps=[path]
  if name=='complete':
   m=deepcopy(r['output_classification_manifest']);args=s._base_rules_arguments()
   c=captions.make_scope(Package(path));c.update(confirmed=True,confirmation='作者手写唯一关联，部分范围',captions={'10':'normal','13':'normal'},associations={'10':'image:p:11','13':'table:2'});m['caption_scope']=c
   r=caption_move.apply_caption_positions(path,out/'complete-02-position.docx',mode='academic',classification_manifest=m,confirmed_keys=['L05:10:image:p:11'],**args);path=Path(r['output']);steps.append(path);m=r['output_classification_manifest']
   regions=[{'start':n,'role':role,'format':fmt,'restart':start,'footer':'chapter' if role=='body' else 'page','text':title,'alignment':'center'} for n,role,fmt,start,title in [(1,'cover','decimal',None,''),(3,'front','lowerRoman',1,''),(8,'body','decimal',1,'第1章 合成方法'),(17,'body','decimal',None,'第2章 合成结果')]]
   plan=page_layout.propose(path,m,s.current_rule_bundle()['assembly'],regions);r=page_layout.rehearse(path,out/'complete-03-pages.docx',m,plan,**args);path=Path(r['output']);steps.append(path);m=r['output_classification_manifest']
   plan=widths.check_widths(path,rules_sha256=s.rules_hash);r=widths.apply_width_adaptation(path,out/'complete-04-width.docx',mode='academic',classification_manifest=m,plan=plan,selected_keys=['W02:paragraph=10','W01:table=2'],**args);path=Path(r['output']);steps.append(path);m=r['output_classification_manifest']
   m['table_scope']['layout_options']={'version':1,'outer_edges':False,'headers':{'2':1}}
   r=layout.apply_pagination_layout(path,out/'complete-05-pagination.docx',mode='academic',classification_manifest=m,confirmed_keys=['L01:10:11','L03:3:4','L02:13:2'],**args);path=Path(r['output']);steps.append(path);m=r['output_classification_manifest']
   r=word_fields.update(path,out/'complete-06-final.docx',m,word_fields.plan(path,m),artifact_dir=out/'word');path=Path(r['output']);steps.append(path)
  record={'same_bytes':path.read_bytes()==(source/'修正版.docx').read_bytes(),'sha256':sha256(path.read_bytes()),'API_requests':0,'seconds':round(time.monotonic()-t,3),'stages':[{'name':p.name,'sha256':sha256(p.read_bytes())} for p in steps],'original_unchanged':sha256(s.input_path.read_bytes())==before}
  records[name]=record
 (out/'legal-path.json').write_text(json.dumps(records,ensure_ascii=False,indent=2));print(json.dumps(records,ensure_ascii=False,indent=2))
 if not all(r['same_bytes'] and r['original_unchanged'] for r in records.values()):raise SystemExit('Output differs; inspect exact stage before claiming equivalence')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--word',action='store_true');p.add_argument('--only',choices=['basic','complete']);a=p.parse_args();run(a.output,a.word,a.only)

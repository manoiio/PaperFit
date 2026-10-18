"""Public synthetic integration. --word explicitly permits native Word/PDF.

No network is used: --rules reuses the real browser-accepted bundle; otherwise
public-response.json is an explicitly labelled mock for protocol reproduction.
"""
from pathlib import Path
import sys,json,time,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def run(folder,word=False,rules=None):
 from urllib.request import OpenerDirector
 OpenerDirector.open=lambda *a,**k:(_ for _ in ()).throw(AssertionError('Network forbidden in reproduction'))
 from web.session import WebSession
 from web.onepass_session import start,poll_fields
 from core.page_policy import DEFAULT
 from core.package import Package,DemoError
 from ai.semantic_spec import parse_requirements
 from ai.short_spec import Settings
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=False);s=WebSession(folder/'session');s.set_mode('academic');s.load((ROOT/'samples/phase53/source.docx').read_bytes(),'公开视觉合成论文.docx')
 if rules:s.import_rule_bundle(Path(rules).read_bytes());s.apply_workbench(acknowledged=True)
 s.page_layout_draft={'enabled':True,'policy':{**DEFAULT,'version':3,'targets':['cover','front','body'],'auxiliaries':'safe-layout-v1','pages':'front-body','footer':'chapter'},'regions':[],'input_sha256':s.inventory['input_sha256']};s.field_updates_enabled=word
 def parser(t):return parse_requirements(t,config=Settings('synthetic'),transport=lambda *_:json.dumps({'choices':[{'finish_reason':'stop','message':{'content':(ROOT/'samples/phase53/public-response.json').read_text()}}]}))
 state={};t=time.monotonic();start(s,state,'' if rules else (ROOT/'samples/phase53/requirements.txt').read_text().strip(),spec_parser=parser,structure_runner=lambda *_:(_ for _ in ()).throw(DemoError('No API in reproduction')))
 while state['status']=='updating':
  poll_fields(s,state)
  if time.monotonic()-t>150:raise DemoError('Native update timed out; not a termination claim')
  time.sleep(.1)
 if state['status']!='done':raise DemoError(state.get('error',str(state.get('questions'))))
 (folder/'fixed.docx').write_bytes(s.downloads()['fixed.docx']);(folder/'result.zip').write_bytes(s.result_package());(folder/'rules.json').write_bytes(s.rule_bundle_download());(folder/'audit.json').write_text(json.dumps(state['audit'],ensure_ascii=False,indent=2)+'\n')
 for i,h in enumerate(s.history,1):
  r=h['result'];(folder/('stage-'+str(i)+'.docx')).write_bytes(Path(r['output']).read_bytes())
  (folder/('stage-'+str(i)+'-changes.json')).write_text(json.dumps(r['changes'],ensure_ascii=False,indent=2)+'\n')
 record={'input_sha256':Package(ROOT/'samples/phase53/source.docx').hash,'output_sha256':Package(folder/'fixed.docx').hash,'seconds':round(time.monotonic()-t,3),'API_requests':0,'rules_origin':'reused real browser bundle' if rules else 'public mock response, not real API','rounds':s.generation_count}
 if word:
  from core.word_preview import render_preview
  m=render_preview(folder/'fixed.docx',folder/'word');(folder/'fixed.pdf').write_bytes(Path(m['pdf']).read_bytes());record['word_preview']={k:v for k,v in m.items() if k not in ('pdf','pages','page_map','artifact_sha256')}
 (folder/'proof.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');return record
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',required=True);a.add_argument('--word',action='store_true');a.add_argument('--rules');v=a.parse_args();print(json.dumps(run(v.output,v.word,v.rules),ensure_ascii=False,indent=2))

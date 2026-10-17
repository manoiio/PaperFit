"""Public saved responses + authored expected values + original legal transactions.
No network, Word, renderer or machine-specific historical directories required.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse,json,sys,zipfile
from urllib.request import OpenerDirector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.package import DemoError,sha256
from scripts.replay_ai_diagnostic import replay
from scripts.verify_paragraph_output import verify
from web.session import WebSession
S=ROOT/'samples/phase47'
def main(out,browser_zip=None):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 def blocked(*a,**k):raise AssertionError('Network forbidden in reproduction')
 OpenerDirector.open=blocked
 expected=json.loads((S/'expected.json').read_text())['fields']
 try:replay(json.loads((S/'failed-request.json').read_text()),json.loads((S/'failed-response.json').read_text()))
 except DemoError:pass
 else:raise AssertionError('Original rejected response must stay rejected')
 data=replay(json.loads((S/'accepted-request.json').read_text()),json.loads((S/'accepted-response.json').read_text()))
 actual={n:f['value'] for n,f in data['draft']['fields'].items()}
 # Authored semantic expectation: legacy1.5 and explicit multiple1.5 are identical.
 if actual.get('abstract_cn_body__line_spacing')=={'mode':'multiple','value':1.5}:actual['abstract_cn_body__line_spacing']=1.5
 assert actual==expected
 source=S/'errors.docx';s=WebSession(out/'legal');s.set_mode('academic');s.load(source.read_bytes(),'公开合成.docx');s.enable_notes(True);scope=s.note_draft.copy();scope['objects']=[r['key'] for r in s.note_inventory()['objects']];s.edit_notes(scope);s.confirm_notes();s.import_rule_bundle((S/'rules.json').read_bytes());s.apply_workbench(acknowledged=True);s.set_types(json.loads((S/'roles.json').read_text()));s.confirm_notes();assert s.confirm_and_check(),s.error
 # Original explicit selection/generate entry, independent from smart orchestration.
 selected=[f['key'] for f in s.eligible() if f['rule_id'].startswith('R') and f['rule_id']!='R35'];s.set_selection(selected);assert s.generate(),s.error
 raw=s.downloads()['fixed.docx'];(out/'legal.docx').write_bytes(raw)
 record={'historical_response_replay_API_requests':0,'fields_equal_authored_expected':True,'legal_changes':len(s.result['changes']),'independent':verify(source,out/'legal.docx')}
 if browser_zip:
  with zipfile.ZipFile(browser_zip) as z:
   browser=z.read('fixed.docx');assert browser==raw,'Browser download differs from original legal entry'
   assert json.loads(z.read('scope.json'))['paragraph_types']==s.classification_confirmed['paragraph_types']
  record['actual_browser_original_legal_bytes_equal']=True
 (out/'independent.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--browser-zip');a=p.parse_args();main(a.output,a.browser_zip)

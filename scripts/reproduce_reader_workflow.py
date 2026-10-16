"""Existing built-in fixture: legal repair path and optional actual download comparison.
No renderer, API, Word, historical work directory or private browser state.
"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from web.session import WebSession
from scripts.verify_workflow_equivalence import verify
from core.package import sha256
ROOT=Path(__file__).resolve().parents[1]
def run(output,download=None):
 out=Path(output);out.mkdir(parents=True,exist_ok=False);s=WebSession(out/'task')
 source=(ROOT/'samples/errors.docx').read_bytes();preset=json.loads((ROOT/'samples/errors.body.json').read_text())
 assert s.load(source,'内置错误样本.docx',preset);s.confirm();assert s.check(),s.error
 s.set_selection([f['key'] for f in s.eligible()]);selected=len(s.selected);assert s.generate(),s.error
 data=s.downloads()['fixed.docx'];(out/'fixed.docx').write_bytes(data)
 assert s.input_path.read_bytes()==source and s.current_round==0 and s.generation_count==1
 proof={'fixture':'samples/errors.docx','input_sha256':sha256(source),'output_sha256':sha256(data),'selected':selected,'changes':len(s.result['changes']),'input_unchanged':True,'current_input_round':0,'output_round':1,'api_requests':0,'render_requests':0}
 if download:proof['browser_download_equivalence']=verify(out/'fixed.docx',download)
 (out/'independent.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proof,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--download');a=p.parse_args();run(a.output,a.download)

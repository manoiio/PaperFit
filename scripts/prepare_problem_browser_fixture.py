"""Wrap the existing 400-paragraph fixture and author roles as an unconfirmed project.
For real browser upload/restore only; no private UI state, checking, fixing or AI.
"""
import argparse,json,sys
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.package import write_new,sha256
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1]

def run(output):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    source=ROOT/'tests/fixtures/history/phase12/long-400.docx'
    roles=json.loads(source.with_suffix('.types.json').read_text())
    assert roles['input_sha256']==sha256(source.read_bytes())
    with TemporaryDirectory() as temp:
        model=WebSession(Path(temp));model.set_mode('extended')
        assert model.load(source.read_bytes(),'既有400段合成论文.docx')
        model.set_types(roles['paragraph_types'])
        assert model.confirmed is None and model.report is None and model.result is None
        model.prepare_project();write_new(output,model.project_download())
    print('Existing fixture, 390 body / 10 heading drafts; restore and explicit confirmation still required. No checking, API or rendering.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);run(parser.parse_args().output)

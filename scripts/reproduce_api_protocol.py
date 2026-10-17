"""Public real-response replay + independent original legal paths. ZERO API."""
from pathlib import Path
import argparse,json,sys
from urllib.request import OpenerDirector
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.replay_ai_diagnostic import replay
from core.rule_config import strict_json
from scripts.reproduce_context_workflow import main as verify_supplement
from scripts.verify_context_structure import verify as verify_structure
from core.package import sha256

def main(output):
    output=Path(output)
    if output.exists():raise SystemExit('Output must not exist')
    output.mkdir(parents=True);samples=ROOT/'samples/phase45';records={}
    with patch.object(OpenerDirector,'open',side_effect=AssertionError('Offline replay must never access network')):
        for label in ('supplement','structure-isolated','structure'):
            req=strict_json((samples/f'{label}-request.json').read_text());res=strict_json((samples/f'{label}-response.json').read_text())
            result=replay(req,res);records[label]={'request_count':result['request_count']}
            (output/f'{label}-replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
            if label=='supplement':
                expected=json.loads((ROOT/'samples/phase44/expected-overrides.json').read_text())['fields']
                assert set(result['draft']['fields'])==set(expected)
                for n,f in expected.items():assert result['draft']['fields'][n]['value']==f['value'],n
                records[label]['authored_16_values_equal']=True
            else:
                by={r['id']:r for r in result['draft']};assert by['t:2']['accepted'] and by['t:2']['role']=='content';assert not by['t:4']['accepted']
                records[label]['content_table_accepted_and_tiny_table_abstained']=True
        verify_supplement(output/'supplement',samples/'supplement-result.zip')
        verify_structure(samples/'structure-result.zip',output/'structure-independent.json',source_label='live API -> automatic content table; tiny table and short heading left pending')
    records['files']={n:sha256((samples/n).read_bytes()) for n in ('supplement.docx','structure.docx')}
    records['network_requests']=0
    (output/'summary.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n');print(json.dumps(records,ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);main(p.parse_args().output)

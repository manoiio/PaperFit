"""Semantic adapters still use native validators; all transports are simulated."""
from pathlib import Path
from copy import deepcopy
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json
from ai.semantic_spec import request_for,adapt,parse_requirements,VERSION,wire_fields
from ai.structure_ids import adapt as structure_adapt,VERSION as STRUCTURE_VERSION
from ai.diagnostics import DiagnosticError,synthetic_capture
from ai.short_spec import Settings
from core.package import DemoError,sha256
ROOT=Path(__file__).resolve().parents[1]
def response_for(text,expected):
    r=request_for(text)
    return {'version':VERSION,'items':[{'field':fid,'value':expected[f['name']]['value'],'source':next(s['id'] for s in r['sources'] if expected[f['name']]['quote'] in s['text'])} for fid,f in r['fields'].items()],'issues':[]}
def envelope(d,**message):return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(d,ensure_ascii=False),**message}}],'usage':{'total_tokens':7}},ensure_ascii=False)
class SemanticAcceptance(TestCase):
    def setUp(self):
        self.text=(ROOT/'samples/phase44/requirements.txt').read_text().strip();self.expected=json.loads((ROOT/'samples/phase44/expected-overrides.json').read_text())['fields'];self.data=response_for(self.text,self.expected)
    def test_all_16_values_native_sources_and_exact_character_ranges(self):
        result=adapt(self.data,self.text);self.assertEqual(set(result['fields']),set(self.expected))
        req=request_for(self.text)
        for s in req['sources']:self.assertEqual(self.text[s['start']:s['end']],s['text'])
        for n,c in result['fields'].items():self.assertEqual(c['value'],self.expected[n]['value']);self.assertIn(c['quote'],self.text);self.assertEqual(c['unit'],self.expected[n]['unit'])
        r=parse_requirements(self.text,config=Settings('synthetic'),transport=lambda *_:envelope(self.data));self.assertEqual(r['draft'],result)
    def test_multiple_errors_omissions_and_whole_input_conflict_never_partial(self):
        d=deepcopy(self.data);d['items'][0]['source']='invented';d['items'][1]['value']=True;d['items'][2]['field']='unknown'
        with self.assertRaises(DiagnosticError) as caught:adapt(d,self.text)
        self.assertGreaterEqual(len(caught.exception.diagnostics),4)
        for change in ('duplicate','missing','extra','unit','conflict'):
            d=deepcopy(self.data);text=self.text
            if change=='duplicate':d['items'].append(d['items'][0])
            if change=='missing':d['items'].pop()
            if change=='extra':d['items'][0]['confirmed']=True
            if change=='unit':d['items'][0]['value']={'value':.5,'unit':'cm'}
            if change=='conflict':text+='正文三号。'
            with self.assertRaises(DemoError):adapt(d,text)
    def test_protocol_finish_duplicate_keys_and_no_retry(self):
        raws=['{"version":1,"version":2}',envelope(self.data,tool_calls=[{}]),json.dumps({'choices':[{'finish_reason':'length','message':{'content':'{}'}}]})]
        for raw in raws:
            calls=[]
            with self.assertRaises(DemoError):parse_requirements(self.text,config=Settings('synthetic'),transport=lambda *_:(calls.append(1) or raw))
            self.assertEqual(len(calls),1)
    def test_candidate_isolation_and_duplicates_cannot_override(self):
        from web.session import WebSession
        from web.structure_session import prepare,run,merge
        with TemporaryDirectory() as tmp:
            s=WebSession(Path(tmp));s.set_mode('academic');s.load((ROOT/'samples/phase44/errors.docx').read_bytes(),'合成.docx');p=prepare(s,include_tables=True)
            data={'version':STRUCTURE_VERSION,'suggestions':[{'id':'t:2','role':'content','evidence':'r1:c2','reason':'数据列及实验上下文'},{'id':'t:4','role':'body','evidence':'invented','reason':'不可靠'}]}
            checked=structure_adapt(data,p['request']);self.assertTrue(checked[0]['accepted']);self.assertFalse(checked[1]['accepted']);self.assertIn('diagnostics',checked[1])
            r=run(s,p,{},config=Settings('synthetic'),transport=lambda *_:envelope(data));proposal=merge(s,p,r);self.assertEqual(proposal['draft']['table_types']['2'],'content');self.assertNotEqual(proposal['draft']['table_types'].get('4'),'content')
            data['suggestions'][0]['evidence']='r1:c1,r1:c2,r1:c3'
            self.assertTrue(structure_adapt(data,p['request'])[0]['accepted'])
            for evidence in ('r1:c1,invented','r1:c1,r1:c1',' r1:c1','r1:c1,'*10):
                data['suggestions'][0]['evidence']=evidence;self.assertFalse(structure_adapt(data,p['request'])[0]['accepted'])
            data['suggestions'].append(data['suggestions'][0])
            with self.assertRaises(DemoError):structure_adapt(data,p['request'])
    def test_explicit_capture_before_validation_and_offline_replay(self):
        from ai import diagnostics
        from scripts.replay_ai_diagnostic import replay
        with TemporaryDirectory() as tmp,patch.object(diagnostics,'ROOT',Path(tmp)):
            req=request_for(self.text);sent={**req,'fields':wire_fields(req['fields'])};content=json.dumps(sent,ensure_ascii=False,sort_keys=True)
            with synthetic_capture(Path(tmp)/'snapshots',[sha256(content.encode())]):
                parse_requirements(self.text,config=Settings('secret-never-record'),transport=lambda *_:envelope(self.data,reasoning_content='PRIVATE_THINKING'))
            a=next(Path(tmp).rglob('*.request.json'));b=next(Path(tmp).rglob('*.response.json'))
            self.assertNotIn('secret-never-record',a.read_text());self.assertNotIn('PRIVATE_THINKING',b.read_text())
            r=replay(json.loads(a.read_text()),json.loads(b.read_text()));self.assertEqual(r['request_count'],0);self.assertEqual(len(r['draft']['fields']),16)
            with synthetic_capture(Path(tmp)/'reject',[sha256(content.encode())]):
                bad=deepcopy(self.data);bad['items'][0]['source']='bad'
                with self.assertRaises(DemoError):parse_requirements(self.text,config=Settings('synthetic'),transport=lambda *_:envelope(bad))
            self.assertTrue(list((Path(tmp)/'reject').glob('*.response.json')))
            self.assertTrue(json.loads(next((Path(tmp)/'reject').glob('*.outcome.json')).read_text())['diagnostics'])

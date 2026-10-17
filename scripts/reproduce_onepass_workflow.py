"""Offline one-command vs original legal path; optional real browser ZIP/XML checks.
All transport responses here are MOCKS from prior author labels, never real API.
"""
from pathlib import Path
from copy import deepcopy
from lxml import etree as E
import argparse,json,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from web.session import WebSession
from web.onepass_session import start,continue_command
from web.structure_session import run as run_structure
from ai.short_spec import Settings
from core.package import NS,q,sha256
from core.rule_bundle import flat
TEXT='在SCUT要求基础上，正文改为四号、2倍行距'


def independent(source,output,protected,size=None,line=None):
    with zipfile.ZipFile(source) as z:a={n:z.read(n) for n in z.namelist()}
    with zipfile.ZipFile(output) as z:b={n:z.read(n) for n in z.namelist()}
    assert a.keys()==b.keys()
    assert all(a[n]==b[n] for n in a if n!='word/document.xml')
    x=E.fromstring(a['word/document.xml']);y=E.fromstring(b['word/document.xml'])
    assert ''.join(x.xpath('//w:t/text()',namespaces=NS))==''.join(y.xpath('//w:t/text()',namespaces=NS))
    for tag in ('tbl','drawing','hyperlink','bookmarkStart','bookmarkEnd','fldSimple','instrText'):
        assert [E.tostring(v,method='c14n') for v in x.iter(q(tag))]==[E.tostring(v,method='c14n') for v in y.iter(q(tag))],tag
    xp=x.find(q('body')).findall(q('p'));yp=y.find(q('body')).findall(q('p'))
    assert len(xp)==len(yp)
    for n in protected:assert E.tostring(xp[n-1],method='c14n')==E.tostring(yp[n-1],method='c14n'),n
    if size:
        for n in (10,12,14,15,16):
            p=yp[n-1];assert p.find('w:r/w:rPr/w:sz',NS).get(q('val'))==str(size*2)
            assert p.find('w:pPr/w:spacing',NS).get(q('line'))==str(line)
            assert p.find('w:pPr/w:spacing',NS).get(q('lineRule'))=='auto'
    return {'text_order_preserved':True,'unselected_parts_byte_equal':True,'objects_and_links_preserved':True,'protected_subtrees':protected,'body_size_pt':size,'body_line_240ths':line}


def run(out,browser_dir=None):
    out=Path(out)
    if out.exists():raise SystemExit('Refuse existing output directory')
    out.mkdir(parents=True);browser_dir=Path(browser_dir) if browser_dir else None;labels=json.loads((ROOT/'samples/phase41/labels.json').read_text())['paragraphs']
    def session(name,source):
        s=WebSession(out/name);s.set_mode('academic');assert s.load(source.read_bytes(),'合成.docx');s.set_table_enabled(False);s.enable_notes(False);return s
    def runner(m,p,store):
        rows=[{'id':c['id'],'role':'heading3' if c['id']=='p:13' else labels[int(c['id'][2:])-1]['role'],'evidence':c['text'],'reason':'作者夹具模拟'} for c in p['request']['candidates']]
        if p['request']['version']=='structure-v3-context':
            for row,c in zip(rows,p['request']['candidates']):
                row['evidence_location']=c['fragments'][0]['id'] if c.get('kind')=='table' else 'text';row['evidence']=c['fragments'][0]['text'] if c.get('kind')=='table' else c['text']
        return run_structure(m,p,store,transport=lambda *_:json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'version':'structure-ids-v1','suggestions':[{k:(r['evidence_location'] if k=='evidence' else r[k]) for k in ('id','role','evidence','reason')} for r in rows]} if p['request']['version']=='structure-v3-context' else {'suggestions':rows})}}]}),config=Settings('synthetic-placeholder'))
    def parser(text):
        return {'draft':{'font_size':{'value':14,'quote':'正文改为四号'},'line_spacing':{'value':2,'quote':'2倍行距'},'unsupported':[]},'receipt':{'kind':'mock_api','model':'deepseek-flash','timestamp_utc':'2026-10-17T00:00:00+00:00','request_count':1}}
    def reference(s,name,source):
        ref=session(name,source)
        if s.custom_rules_path:
            ref.import_rule_bundle(s.custom_rules_path.read_bytes());ref.apply_workbench(acknowledged=True)
        ref.set_types(s.paragraph_types);ref.confirm_and_check();ref.set_selection(s.selected);assert ref.generate(),ref.error
        return ref.downloads()['fixed.docx']
    evidence={'script_API_requests':0,'fixture_response_kind':'mock','cases':{}}
    for case,source in (('A',ROOT/'samples/phase31/errors.docx'),('B',ROOT/'samples/phase41/structure.docx')):
        s=session(case,source);state={};before=source.read_bytes();t=time.perf_counter();start(s,state,structure_runner=runner)
        if case=='B':
            assert state['status']=='waiting';assert len(state['questions'])==1
            assert not s.history and s.confirmed is None
            continue_command(s,state,'',{'paragraph:13':'heading2'})
        assert state['status']=='done',state.get('error')
        elapsed=time.perf_counter()-t;raw=s.downloads()['fixed.docx'];assert raw==reference(s,case+'-original',source)
        assert source.read_bytes()==before and s.current_round==0
        (out/(case+'.docx')).write_bytes(raw)
        row={'sha256':sha256(raw),'original_legal_path_byte_equal':True,'seconds':round(elapsed,3),'outcome':state['outcome'],
             'independent':independent(source,out/(case+'.docx'),[18] if case=='A' else [1,2,17,18,19],12 if case=='B' else None,360)}
        if browser_dir:
            assert (browser_dir/(case+'.docx')).read_bytes()==raw
            row['actual_browser_byte_equal']=True
            if (browser_dir/(case+'.zip')).exists():
                with zipfile.ZipFile(browser_dir/(case+'.zip')) as z:
                    assert z.read('fixed.docx')==raw
                    assert json.loads(z.read('scope.json'))['paragraph_types']==s.paragraph_types
        evidence['cases'][case]=row
        if case=='B':
            prior=s.current_rule_bundle();start(s,state,TEXT,spec_parser=parser)
            assert state['status']=='done',state.get('error');bundle=s.current_rule_bundle()
            for m,v in prior['modules'].items():
                if m!='main':assert v==bundle['modules'][m] and prior['provenance'][m]==bundle['provenance'][m]
            for n,value in flat('main',prior['modules']['main']).items():
                if n not in ('font_size','line_spacing'):
                    assert value==flat('main',bundle['modules']['main'])[n]
                    assert prior['provenance']['main'][n]==bundle['provenance']['main'][n]
            raw=s.downloads()['fixed.docx'];assert raw==reference(s,'C-original',source)
            (out/'C.docx').write_bytes(raw);row={'sha256':sha256(raw),'original_legal_path_byte_equal':True,'only_overrides':['font_size','line_spacing'],
                'independent':independent(source,out/'C.docx',[1,2,17,18,19],14,480)}
            if browser_dir:
                assert (browser_dir/'C.docx').read_bytes()==raw
                with zipfile.ZipFile(browser_dir/'C.zip') as z:
                    actual=json.loads(z.read('rule-bundle.json'));assert z.read('fixed.docx')==raw
                    for n,source_record in prior['provenance']['main'].items():
                        if n not in ('font_size','line_spacing'):assert actual['provenance']['main'][n]==source_record
                    for m in prior['modules']:
                        if m!='main':assert actual['modules'][m]==prior['modules'][m] and actual['provenance'][m]==prior['provenance'][m]
                row['actual_browser_byte_equal']=True;row['actual_browser_untouched_sources_preserved']=True
            evidence['cases']['C']=row
    (out/'independent.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n');print(json.dumps(evidence,ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--browser-dir');a=p.parse_args();run(a.output,a.browser_dir)

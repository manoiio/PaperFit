"""Offline author-labelled suggestions; optional ACTUAL browser download comparison.
Never invokes AI. Fixture labels were written before the real request.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from lxml import etree as E
import json,zipfile,sys,argparse,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from web.session import WebSession
from web.smart_session import suggest,accept_scope,execute
from core.package import sha256,NS,q

def independent(source,output):
    with zipfile.ZipFile(source) as z:old={n:z.read(n) for n in z.namelist()}
    with zipfile.ZipFile(output) as z:new={n:z.read(n) for n in z.namelist()}
    assert old.keys()==new.keys()
    assert all(old[n]==new[n] for n in old if n!='word/document.xml')
    a=E.fromstring(old['word/document.xml']);b=E.fromstring(new['word/document.xml'])
    assert ''.join(a.xpath('//w:t/text()',namespaces=NS))==''.join(b.xpath('//w:t/text()',namespaces=NS))
    ap=a.find(q('body')).findall(q('p'));bp=b.find(q('body')).findall(q('p'))
    assert len(ap)==len(bp)
    assert [''.join(p.xpath('.//w:t/text()',namespaces=NS)) for p in ap]==[''.join(p.xpath('.//w:t/text()',namespaces=NS)) for p in bp]
    # Author-pinned unselected cover, code, data, instruction-like material, all subtree exact.
    for n in (1,2,17,18,19):assert E.tostring(ap[n-1],method='c14n')==E.tostring(bp[n-1],method='c14n')
    # Independent physical OOXML values, not new classifier/engine used to read them.
    for n in (10,12,14,15,16):
        p=bp[n-1];assert p.find('w:r/w:rPr/w:sz',NS).get(q('val'))=='24'
        assert p.find('w:pPr/w:ind',NS).get(q('firstLineChars'))=='200'
    for n,sid in ((9,'Heading1'),(11,'Heading2'),(13,'Heading2')):
        assert bp[n-1].find('w:pPr/w:pStyle',NS).get(q('val'))==sid
    assert bp[20].find('w:r/w:rPr/w:sz',NS).get(q('val'))=='24'
    return {'all_text_order_preserved':True,'all_unselected_parts_byte_equal':True,'protected_paragraph_subtrees_equal':[1,2,17,18,19],'body_size_12pt_indent_2chars':True,'chapter_styles_independently_verified':True}

def run(output,browser_docx=None,browser_zip=None,receipt=None):
    output=Path(output)
    if output.exists():raise SystemExit('Refuse existing output')
    output.mkdir(parents=True)
    labels=json.loads((ROOT/'samples/phase41/labels.json').read_text())['paragraphs'];source=ROOT/'samples/phase41/structure.docx'
    def session(name):
        s=WebSession(output/name);s.set_mode('academic');s.load(source.read_bytes(),'合成.docx');return s
    # Pinned author labels, not a parsed AI result. Code/data deliberately pending.
    expected={str(n):r['role'] for n,r in enumerate(labels,1)}
    expected.update({'17':'pending','18':'pending'})
    a=session('shortcut');local=suggest(a);a.set_types(expected);plan=accept_scope(a,suggest(a))
    b=session('original');b.set_types(expected);b.confirm_and_check();b.set_selection(plan['keys']);assert b.generate(),b.error
    started=time.perf_counter();execute(a,plan,{});elapsed=time.perf_counter()-started
    raw=a.downloads()['fixed.docx'];assert raw==b.downloads()['fixed.docx']
    (output/'fixed.docx').write_bytes(raw)
    evidence={'source_sha256':sha256(source.read_bytes()),'output_sha256':sha256(raw),'original_legal_path_bytes_equal':True,'independent':independent(source,output/'fixed.docx'),
              'selected_records':len(plan['keys']),'repair_seconds':elapsed,'format_summary':a.result['after']['summary'],
              'local_included':sum(t not in ('pending','other') for t in local['draft']['paragraph_types'].values()),'final_included':sum(t not in ('pending','other') for t in expected.values()),'actual_AI_requests_in_this_script':0}
    evidence['local_candidate_comparison']={'correct':0,'wrong':0,'abstain':8,'definition':'本夹具8个未纳入候选；other/pending按范围弃权计，不表示全文分类准确率'}
    if browser_docx:assert Path(browser_docx).read_bytes()==raw;evidence['actual_browser_DOCX_byte_equal']=True
    if browser_zip:
        with zipfile.ZipFile(browser_zip) as z:
            assert z.read('fixed.docx')==raw
            assert json.loads(z.read('scope.json'))['paragraph_types']==expected
        evidence['actual_browser_ZIP_DOCX_and_scope_equal']=True
    if receipt:
        record=json.loads(Path(receipt).read_text());good=bad=abstain=0;details=[]
        for r in record['suggestions']:
            gold=labels[int(r['id'][2:])-1]['role'];status='abstain' if r['role'] in ('other','pending') and r['role']!=gold else 'correct' if gold==r['role'] else 'wrong'
            good+=status=='correct';bad+=status=='wrong';abstain+=status=='abstain';details.append({'id':r['id'],'gold':gold,'AI':r['role'],'result':status})
        evidence['actual_real_sample']={'correct':good,'wrong':bad,'abstain':abstain,'details':details,'receipt':record['receipt'],'manual_correction':{'p:13':'heading2'},'note':'保留第一次响应，没有重复调用挑选；仅合成小样本，不是服务成功率或总体准确率'}
    (output/'independent.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n');print(json.dumps(evidence,ensure_ascii=False,indent=2));return evidence
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--browser-docx');p.add_argument('--browser-zip');p.add_argument('--receipt');a=p.parse_args();run(a.output,a.browser_docx,a.browser_zip,a.receipt)

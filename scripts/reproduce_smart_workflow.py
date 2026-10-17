"""Run the shortcut + optional OOXML transaction; original legal path and raw XML proofs.
No historical work, network, AI, Word or renderer dependency.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys,argparse,json,time,zipfile
from copy import deepcopy
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.package import Package,q,NS,sha256
from core import fix_document
from web.session import WebSession
from web.smart_session import suggest,accept_scope,execute
from web.dynamic_session import preview,adopt
from scripts.build_smart_dynamic_fixture import build

def independent_format(a,b):
    old,new=Package(a),Package(b);root=E.fromstring(old.parts['word/document.xml']);ps=root.find(q('body')).findall(q('p'));secs=root.findall('w:body/w:p/w:pPr/w:sectPr',NS)+root.findall('w:body/w:sectPr',NS)
    # Author-defined expected twips/font/size/paragraph values, independent of our plan.
    for name,val in [('w','11906'),('h','16838')]:secs[0].find(q('pgSz')).set(q(name),val)
    secs[0].find(q('pgMar')).set(q('left'),'1417');secs[1].find(q('pgMar')).set(q('bottom'),'1417')
    ps[3].findall(q('r'))[1].find('w:rPr/w:sz',NS).set(q('val'),'24')
    run=ps[4].findall(q('r'))[0];rp=run.find(q('rPr'))
    if rp is None:rp=E.Element(q('rPr'));run.insert(0,rp)
    fonts=rp.find(q('rFonts'))
    if fonts is None:fonts=E.Element(q('rFonts'));rp.insert(0,fonts)
    fonts.set(q('eastAsia'),'宋体')
    for n in [4,5]:
        e=ps[n-1].find('w:pPr/w:spacing',NS);e.set(q('line'),'360');e.set(q('lineRule'),'auto')
    for n in [6,11]:
        pp=ps[n-1].find(q('pPr'));e=pp.find(q('ind'))
        if e is None:e=E.SubElement(pp,q('ind'))
        e.set(q('firstLineChars'),'200');e.set(q('firstLine'),'0')
    rp=ps[13].findall(q('r'))[1].find(q('rPr'));E.SubElement(rp,q('rFonts')).set(q('ascii'),'Times New Roman');E.SubElement(rp,q('sz')).set(q('val'),'24')
    assert E.tostring(root,method='c14n')==E.tostring(new.root,method='c14n')
    assert {k:v for k,v in old.parts.items() if k!='word/document.xml'}=={k:v for k,v in new.parts.items() if k!='word/document.xml'}
    return {'exact_author_expected_tree':True,'all_unselected_parts_byte_equal':True,'all_text_and_order_preserved':old.root.xpath('//w:t/text()',namespaces=NS)==new.root.xpath('//w:t/text()',namespaces=NS)}

def independent_dynamic(a,b):
    old,new=Package(a),Package(b);root=E.fromstring(old.parts['word/document.xml']);ps=root.find(q('body')).findall(q('p'))
    expected={4:['依据图1-','1与图2-','1，可比较合成结果。再次参见图1-1。'],5:['图1-1 示例曲线'],13:['图2-1 示例曲线']}
    for n,values in expected.items():
        nodes=ps[n-1].xpath('./w:r/w:t',namespaces=NS);assert len(nodes)==len(values)
        for node,val in zip(nodes,values):node.text=val
    assert E.tostring(root,method='c14n')==E.tostring(new.root,method='c14n')
    assert {k:v for k,v in old.parts.items() if k!='word/document.xml'}=={k:v for k,v in new.parts.items() if k!='word/document.xml'}
    return {'exact_author_numeric_changes_only':True,'all_run_properties_and_other_objects_preserved':True,'all_unselected_parts_byte_equal':True,'no_Word_calculation':True}

def run(output,browser_download=None,browser_dynamic=None):
    output=Path(output)
    if output.exists():raise SystemExit('Refusing existing output')
    output.mkdir(parents=True)
    s=WebSession(output/'task');s.load((ROOT/'samples/errors.docx').read_bytes(),'合成.docx')
    before=s.input_path.read_bytes();start=time.perf_counter();proposal=suggest(s);plan=accept_scope(s,proposal);scope_elapsed=time.perf_counter()-start
    assert s.body==[4,5,6,11,14,15] and not s.selected
    # Original legal path uses an independently pinned, complete body list.
    reference=WebSession(output/'reference');reference.load(before,'合成.docx');reference.set_body([4,5,6,11,14,15]);reference.confirm();reference.check();reference.set_selection([f['key'] for f in reference.eligible()]);assert reference.generate(),reference.error
    start=time.perf_counter();state={};outcome=execute(s,plan,state);elapsed=time.perf_counter()-start
    execute(s,plan,state);assert len(s.history)==1 and s.current_round==0
    raw=s.downloads()['fixed.docx'];assert raw==reference.downloads()['fixed.docx']
    (output/'smart-fixed.docx').write_bytes(raw);(output/'smart-result.zip').write_bytes(s.result_package())
    proof={'baseline_tests':1227,'scope_confirmation_seconds':scope_elapsed,'shortcut_seconds':elapsed,'shortcut':outcome,'original_legal_path_bytes_equal':True,
           'original_input_unchanged':s.input_path.read_bytes()==before,'format_independent':independent_format(s.input_path,output/'smart-fixed.docx'),'smart_sha256':sha256(raw),'API_requests':0,'render_requests':0}
    if browser_download:assert Path(browser_download).read_bytes()==raw;proof['browser_smart_bytes_equal']=True
    p,m=build(output/'dynamic-fixture');ds=WebSession(output/'dynamic-task');ds.set_mode('academic');ds.load(p.read_bytes(),'动态合成.docx');ds.set_types(m['paragraph_types']);ds.confirm_and_check()
    st={};start=time.perf_counter();dr=preview(ds,st,complete=True);assert not ds.history;preview_elapsed=time.perf_counter()-start
    start=time.perf_counter();adopt(ds,st);adoption_elapsed=time.perf_counter()-start;adopt(ds,st);assert len(ds.history)==1
    final=ds.downloads()['fixed.docx'];(output/'dynamic-fixed.docx').write_bytes(final);(output/'dynamic-result.zip').write_bytes(ds.result_package());(output/'project.zip').write_bytes(ds.prepare_project())
    proof['dynamic']={'preview_seconds':preview_elapsed,'adoption_seconds':adoption_elapsed,'rounds':len(ds.history),'adoption_fix_calls':0,'numeric_edits':len(dr['changes']),'sha256':sha256(final),'word':dr['dynamic']['word'],'independent':independent_dynamic(p,output/'dynamic-fixed.docx')}
    if browser_dynamic:assert Path(browser_dynamic).read_bytes()==final;proof['browser_dynamic_bytes_equal']=True
    from web.reading_report import clean
    (output/'dynamic-record.json').write_text(json.dumps(clean(ds.result),ensure_ascii=False,indent=2)+'\n')
    (output/'independent.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proof,ensure_ascii=False,indent=2));return proof
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--browser-download');p.add_argument('--browser-dynamic');a=p.parse_args();run(a.output,a.browser_download,a.browser_dynamic)

"""Offline table+note composition, original legal reference and raw ZIP/XML oracle.
The only generated API response is explicitly MOCKED from author labels.
"""
from pathlib import Path
from copy import deepcopy
import json,zipfile,sys,argparse,time
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from web.session import WebSession
from web.onepass_session import start
from web.structure_session import run
from ai.short_spec import Settings
from core.package import NS,q,sha256
SOURCE=ROOT/'samples/phase43/errors.docx'

def verify(output,body2=False):
    with zipfile.ZipFile(SOURCE) as z:a={n:z.read(n) for n in z.namelist()}
    with zipfile.ZipFile(output) as z:b={n:z.read(n) for n in z.namelist()}
    assert a.keys()==b.keys()
    allowed=('word/document.xml','word/footnotes.xml','word/endnotes.xml')
    assert all(a[n]==b[n] for n in a if n not in allowed)
    roots={}
    for part in allowed:
        x,y=E.fromstring(a[part]),E.fromstring(b[part]);roots[part]=(x,y)
        assert ''.join(x.xpath('//w:t/text()',namespaces=NS))==''.join(y.xpath('//w:t/text()',namespaces=NS))
        for tag in ('hyperlink','fldSimple','instrText','fldChar','footnoteReference','endnoteReference','footnoteRef','endnoteRef','separator','continuationSeparator','drawing','pict','sectPr'):
            if tag=='sectPr':continue
            assert [E.tostring(e,method='c14n') for e in x.iter(q(tag))]==[E.tostring(e,method='c14n') for e in y.iter(q(tag))],(part,tag)
    x,y=roots['word/document.xml'];xb,yb=x.find(q('body')),y.find(q('body'));xt,yt=xb.findall(q('tbl')),yb.findall(q('tbl'))
    assert len(xt)==len(yt)==3
    for n in (0,2):assert E.tostring(xt[n],method='c14n')==E.tostring(yt[n],method='c14n')
    for r in yt[1].findall('.//'+q('r')):
        if any('\u3400'<=c<='\u9fff' for c in ''.join(r.xpath('.//w:t/text()',namespaces=NS))):assert r.find('w:rPr/w:rFonts',NS).get(q('eastAsia'))=='宋体'
        assert r.find('w:rPr/w:sz',NS).get(q('val'))=='21'
    def strip_run(r,body=False):
        pr=r.find(q('rPr'))
        if pr is None:return
        fonts=pr.find(q('rFonts'))
        if fonts is not None:
            text=''.join(r.xpath('.//w:t/text()',namespaces=NS));names=[]
            if any('\u3400'<=c<='\u9fff' for c in text):names+=['eastAsia','eastAsiaTheme']
            if body and any(c.isascii() and c.isalnum() for c in text):names+=['ascii','hAnsi','asciiTheme','hAnsiTheme']
            for n in names:fonts.attrib.pop(q(n),None)
            if not fonts.attrib and not len(fonts):pr.remove(fonts)
        for n in ('sz',):
            e=pr.find(q(n))
            if e is not None:pr.remove(e)
        if not len(pr) and not pr.attrib:r.remove(pr)
    def strip_line(p,body=False):
        pr=p.find(q('pPr'))
        if pr is None:return
        e=pr.find(q('spacing'))
        if e is not None:
            for n in ('line','lineRule'):e.attrib.pop(q(n),None)
            if not e.attrib and not len(e):pr.remove(e)
        if body:
            e=pr.find(q('ind'))
            if e is not None:
                for n in ('firstLine','firstLineChars','hanging','hangingChars'):e.attrib.pop(q(n),None)
                if not e.attrib and not len(e):pr.remove(e)
        if not len(pr) and not pr.attrib:p.remove(pr)
    for root in (x,y):
        sect=root.find(q('body')).find(q('sectPr'))
        for tag,names in [('pgSz',('w','h','orient')),('pgMar',('top','bottom','left','right'))]:
            e=sect.find(q(tag))
            if e is not None:
                for n in names:e.attrib.pop(q(n),None)
                if not e.attrib and not len(e):sect.remove(e)
        for r in root.find(q('body')).findall(q('tbl'))[1].findall('.//'+q('r')):strip_run(r)
        if body2:
            p=root.find(q('body')).findall(q('p'))[1];strip_line(p,True)
            for r in p.findall(q('r')):strip_run(r,True)
    assert E.tostring(x,method='c14n')==E.tostring(y,method='c14n'),'Unselected main-document attributes changed'
    for part in allowed[1:]:
        x,y=roots[part]
        assert [(e.get(q('id')),e.get(q('type'))) for e in x]==[(e.get(q('id')),e.get(q('type'))) for e in y]
        for root in (x,y):
            for note in root:
                if note.get(q('type'),'normal')!='normal':continue
                for p in note.findall(q('p')):
                    if all(c.tag in (q('pPr'),q('r')) for c in p) and not p.xpath('.//w:fldChar|.//w:instrText',namespaces=NS):strip_line(p)
                    depth=0
                    for r in p.findall(q('r')):
                        fields=r.findall(q('fldChar'))
                        if fields:
                            depth+=sum(e.get(q('fldCharType'))=='begin' for e in fields)-sum(e.get(q('fldCharType'))=='end' for e in fields);continue
                        if depth or any(e.tag not in (q('rPr'),q('t'),q('tab'),q('br')) for e in r):continue
                        strip_run(r)
        assert E.tostring(x,method='c14n')==E.tostring(y,method='c14n'),'Unselected note attributes/structures changed'
    return {'all_text_order_equal':True,'unselected_parts_byte_equal':True,'cover_nested_tables_exact':True,'table2_song_10_5pt':True,'note_marker_system_relationships_exact':True,'selected_format_only':True}

def main(output,browser_zip=None):
    out=Path(output)
    if out.exists():raise SystemExit('Refuse existing output')
    out.mkdir(parents=True);labels=json.loads((ROOT/'samples/phase43/labels.json').read_text())
    def session(name):
        s=WebSession(out/name);s.set_mode('academic');assert s.load(SOURCE.read_bytes(),'合成.docx');return s
    def runner(s,p,store):
        rows=[{'id':c['id'],'role':labels['table_roles'][c['id'][2:]] if c.get('kind')=='table' else labels['paragraph_roles'][c['id'][2:]],'evidence':c['text'],'reason':'作者预先标注的模拟响应'} for c in p['request']['candidates']]
        return run(s,p,store,config=Settings('synthetic-placeholder'),transport=lambda *_:json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'suggestions':rows})}}]}))
    def legal(types,tables,notes):
        s=session('legal-'+str(time.time_ns()));s.set_types(types);s.set_table_enabled(True);s.set_table_types(tables);s.enable_notes(True);notes=deepcopy(notes);notes.update(input_sha256=s.inventory['input_sha256'],confirmed=False);s.edit_notes(notes);s.confirm_tables();s.confirm_notes();assert s.confirm_and_check(),s.error
        selected=[f['key'] for f in s.eligible() if f['rule_id'].startswith('R') and f['rule_id']!='R35'];s.set_selection(selected);assert s.generate(),s.error;return s
    s=session('intelligent');state={};t=time.perf_counter();start(s,state,structure_runner=runner);elapsed=time.perf_counter()-t
    assert state['status']=='done',state.get('error');ref=legal(s.paragraph_types,s.table_types,s.note_draft);raw=s.downloads()['fixed.docx'];assert raw==ref.downloads()['fixed.docx']
    (out/'fixed.docx').write_bytes(raw);(out/'result.zip').write_bytes(s.result_package())
    evidence={'actual_API_requests':0,'response_source':'mock from author labels','seconds':round(elapsed,3),'output_sha256':sha256(raw),'same_final_scope_original_legal_bytes_equal':True,'independent':verify(out/'fixed.docx',True),'outcome':state['outcome'],'auto_scope':state['audit']['processed_scope']}
    if browser_zip:
        with zipfile.ZipFile(browser_zip) as z:
            scope=json.loads(z.read('scope.json'));notes=scope['note_scope'];tables=scope['table_scope']['table_types'];br=z.read('fixed.docx')
        (out/'browser.docx').write_bytes(br);verify(out/'browser.docx',scope['paragraph_types']['2']=='body')  # prove same stable objects/text before source-hash rebind
        ref=legal(scope['paragraph_types'],tables,notes);assert br==ref.downloads()['fixed.docx']
        evidence['actual_browser']={'sha256':sha256(br),'original_legal_bytes_equal':True,'independent':verify(out/'browser.docx',scope['paragraph_types']['2']=='body')}
    (out/'independent.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n');print(json.dumps(evidence,ensure_ascii=False,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--browser-zip');a=p.parse_args();main(a.output,a.browser_zip)

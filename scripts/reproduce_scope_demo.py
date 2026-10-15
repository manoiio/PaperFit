"""Offline equivalence/atomic scope demo; no API, work/, renderer, or Word needed."""
from pathlib import Path
from copy import deepcopy
import argparse,json,tempfile,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from web.session import WebSession
from core.package import Package,NS,q,sha256

def prepare(s):
    ds=json.loads((ROOT/'samples/phase26/scope.json').read_text())
    s.set_types(ds['roles']);s.exclude_materials([13],ds['material_exclusions']['13'])
    s.set_table_enabled(True);s.set_table_types(ds['table_types'])
    s.enable_front(True);d=deepcopy(s.front_draft);d.update(objects=ds['cover_objects'],section_roles=ds['section_roles']);s.edit_front(d)
    s.enable_toc(True);d=deepcopy(s.toc_draft);d['objects']=ds['toc_objects'];s.edit_toc(d)
    s.enable_citations(True);d=deepcopy(s.citation_draft);d['objects']={r['id']:'citation' for r in s.citation_inventory()['objects'] if r['paragraph']==17};s.edit_citations(d)
    s.enable_notes(True);d=deepcopy(s.note_draft);d['objects']=[r['key'] for r in s.note_inventory()['objects']];s.edit_notes(d)
    s.enable_captions(True);d=deepcopy(s.caption_draft);d.update(captions=ds['caption_roles'],chapter_map=ds['chapter_map'],associations=ds['associations']);s.edit_captions(d)
    return s

def session(root):
    s=WebSession(root);s.set_mode('academic');assert s.load((ROOT/'samples/phase26/composite.docx').read_bytes(),'综合软件演示.docx'),s.error
    return prepare(s)

def old_check(s):
    for name in ('confirm_tables','confirm_front','confirm_toc','confirm_citations','confirm_notes','confirm_captions','confirm_classification'):getattr(s,name)()
    assert s.check(),s.error

def run(output):
    output=Path(output)
    if output.exists():raise SystemExit('Refusing existing output directory')
    output.mkdir(parents=True)
    a=session(output/'old');b=session(output/'unified')
    start=time.perf_counter();old_check(a);old_time=time.perf_counter()-start
    start=time.perf_counter();p=b.scope_preflight();pre_time=time.perf_counter()-start
    assert p['ready'],p['blockers'];assert b.confirm_scopes_and_check(p['signature'],acknowledged=True),b.error
    assert a.classification_confirmed==b.classification_confirmed
    assert a.report['findings']==b.report['findings'] and a.report['coverage_notes']==b.report['coverage_notes']
    # A small explicit correction, same selection through both paths.
    keys=[r['key'] for r in a.eligible() if r['rule_id']=='R05'][:1];assert keys
    for s in (a,b):s.set_selection(keys);assert s.generate(),s.error
    assert a.downloads()['fixed.docx']==b.downloads()['fixed.docx']
    source=Package(b.input_path);fixed=Package(b.result['output'])
    assert source.root.xpath('//w:t/text()',namespaces=NS)==fixed.root.xpath('//w:t/text()',namespaces=NS)
    assert all(v==fixed.parts[n] for n,v in source.parts.items() if n!='word/document.xml')
    # Independent XML whitelist: exactly the fixture's selected13→12pt value,
    # not merely text totals or this feature's own checker output.
    from lxml import etree as E
    left=E.fromstring(source.parts['word/document.xml']);right=E.fromstring(fixed.parts['word/document.xml'])
    old_size=left.find('w:body',NS).findall(q('p'))[7].findall(q('r'))[0].find('w:rPr/w:sz',NS)
    new_size=right.find('w:body',NS).findall(q('p'))[7].findall(q('r'))[0].find('w:rPr/w:sz',NS)
    assert old_size.get(q('val'))=='26' and new_size.get(q('val'))=='24'
    old_size.attrib.pop(q('val'));new_size.attrib.pop(q('val'))
    assert E.tostring(left,method='c14n')==E.tostring(right,method='c14n')

    assert source.root.xpath('//w:tbl',namespaces=NS)[0].xpath('.//w:t/text()',namespaces=NS)==fixed.root.xpath('//w:tbl',namespaces=NS)[0].xpath('.//w:t/text()',namespaces=NS)
    assert sha256(b.input_path.read_bytes())==source.hash
    for n,data in b.downloads().items():(output/n).write_bytes(data)
    for n,data in b.prepare_reading_export().items():(output/n).write_bytes(data)
    (output/'result.zip').write_bytes(b.result_package())
    (output/'scope-summary.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
    (output/'independent-check.json').write_text(json.dumps({'equivalent_manifest':True,'equivalent_findings':True,'equivalent_coverage_notes':True,'output_bytes_identical':True,'original_sha256':source.hash,'output_sha256':fixed.hash,'original_text_and_unselected_parts_preserved':True,'only_expected_run_size_changed_in_main_xml':True,'selected_keys':keys,'summary':b.result['after']['summary'],'preflight_seconds':pre_time,'old_confirmation_and_check_seconds':old_time,'api_requests':0},ensure_ascii=False,indent=2)+'\n')
    return b
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)

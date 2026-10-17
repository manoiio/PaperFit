"""Independent raw ZIP/XML checks plus the original explicit local legal path.
No new structure index/parser is used to define the expected table purpose/format.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import argparse,json,sys,zipfile
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from core.package import NS,q,sha256
from web.session import WebSession

def verify(pack,output):
 source=ROOT/'samples/phase44/errors.docx'
 with zipfile.ZipFile(source) as z:a={n:z.read(n) for n in z.namelist()}
 with zipfile.ZipFile(pack) as z:bundle={n:z.read(n) for n in z.namelist()}
 scope=json.loads(bundle['scope.json']);raw=bundle['fixed.docx']
 from io import BytesIO
 with zipfile.ZipFile(BytesIO(raw)) as z:b={n:z.read(n) for n in z.namelist()}
 assert a.keys()==b.keys();assert all(a[n]==b[n] for n in a if n not in ('word/document.xml','word/footnotes.xml','word/endnotes.xml'))
 for part in ('word/document.xml','word/footnotes.xml','word/endnotes.xml'):
  x,y=E.fromstring(a[part]),E.fromstring(b[part]);assert x.xpath('//w:t/text()',namespaces=NS)==y.xpath('//w:t/text()',namespaces=NS)
  for tag in ('drawing','pict','hyperlink','fldSimple','fldChar','instrText','footnoteReference','endnoteReference','footnoteRef','endnoteRef','separator','continuationSeparator','bookmarkStart','bookmarkEnd'):
   assert [E.tostring(e,method='c14n') for e in x.iter(q(tag))]==[E.tostring(e,method='c14n') for e in y.iter(q(tag))],(part,tag)
  if part!='word/document.xml':
   for left,right in zip(x,y):
    assert left.attrib==right.attrib
    if left.get(q('type'),'normal')!='normal':assert E.tostring(left,method='c14n')==E.tostring(right,method='c14n')
 x,y=E.fromstring(a['word/document.xml']),E.fromstring(b['word/document.xml']);xt=x.find(q('body')).findall(q('tbl'));yt=y.find(q('body')).findall(q('tbl'));assert len(xt)==len(yt)==5
 for n in (0,2,3,4):assert E.tostring(xt[n],method='c14n')==E.tostring(yt[n],method='c14n')
 for root in (xt[1],yt[1]):
  for r in root.findall('.//'+q('r')):
   pr=r.find(q('rPr'));assert pr is not None
   if root is yt[1]:
    assert pr.find(q('sz')).get(q('val'))=='21'
    if any('\u3400'<=c<='\u9fff' for c in ''.join(r.xpath('./w:t/text()',namespaces=NS))):assert pr.find(q('rFonts')).get(q('eastAsia'))=='宋体'
   fonts=pr.find(q('rFonts'))
   if fonts is not None:
    for n in ('eastAsia','eastAsiaTheme'):fonts.attrib.pop(q(n),None)
    if not fonts.attrib and not len(fonts):pr.remove(fonts)
   size=pr.find(q('sz'))
   if size is not None:pr.remove(size)
   if not len(pr) and not pr.attrib:r.remove(pr)
 assert E.tostring(xt[1],method='c14n')==E.tostring(yt[1],method='c14n')
 for i,(p,r) in enumerate(zip(x.find(q('body')).findall(q('p')),y.find(q('body')).findall(q('p'))),1):
  if scope['paragraph_types'][str(i)] in ('other','pending'):assert E.tostring(p,method='c14n')==E.tostring(r,method='c14n')
 with TemporaryDirectory() as tmp:
  s=WebSession(tmp);s.set_mode('academic');s.load(source.read_bytes(),'合成.docx');s.set_types(scope['paragraph_types']);s.set_table_enabled(True);s.set_table_types(scope['table_scope']['table_types']);s.enable_notes(True)
  notes=deepcopy(scope['note_scope']);notes.update(input_sha256=s.inventory['input_sha256'],confirmed=False);s.edit_notes(notes);s.confirm_tables();s.confirm_notes();assert s.confirm_and_check(),s.error
  s.set_selection([f['key'] for f in s.eligible() if f['rule_id'].startswith('R') and f['rule_id']!='R35']);assert s.generate(),s.error;assert raw==s.downloads()['fixed.docx']
 result={'source':'real API rejected, explicit table decisions then original local engines','sha256':sha256(raw),'original_legal_bytes_equal':True,'independent':{'text_and_order_equal':True,'unselected_ZIP_parts_equal':True,'cover_nested_ambiguous_code_tables_exact':True,'content_table_selected_font_size_only':True,'system_notes_and_markers_fields_links_exact':True,'excluded_top_paragraphs_exact':True},'remaining_note':'Independent oracle covers named protections; existing original transaction validates the complete format whitelist.'}
 Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('package');p.add_argument('--output',required=True);a=p.parse_args();verify(a.package,a.output)

"""Raw ZIP/XML oracle: no checker, hyperlink walker, selector, repair or mask imports."""
from pathlib import Path
from copy import deepcopy
from io import BytesIO
import sys,json,zipfile,hashlib
from lxml import etree as E
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main';NS={'w':W}
def q(n):return '{'+W+'}'+n
def canon(x):return E.tostring(x,method='c14n')
ROOT=Path(__file__).resolve().parents[1]
def put(parent,tag):
 found=parent.find(q(tag))
 if found is not None:return found
 e=E.Element(q(tag))
 if tag=='rPr':parent.insert(0,e)
 elif tag=='rFonts':parent.insert(1 if parent.find(q('rStyle')) is not None else 0,e)
 else:
  # sz must precede szCs/highlight/u and later properties, retain all earlier children.
  later={q(t) for t in ('szCs','highlight','u','effect','bdr','shd','fitText','vertAlign','rtl','cs','em','lang','eastAsianLayout','specVanish','oMath','rPrChange')}
  index=next((i for i,c in enumerate(parent) if c.tag in later),len(parent));parent.insert(index,e)
 return e

def verify(original,output,repairs=None):
 raw=Path(original).read_bytes();out=Path(output).read_bytes()
 with zipfile.ZipFile(BytesIO(raw)) as z:a={n:z.read(n) for n in z.namelist()}
 with zipfile.ZipFile(BytesIO(out)) as z:b={n:z.read(n) for n in z.namelist()}
 assert a.keys()==b.keys();repairs=repairs if repairs is not None else json.loads((ROOT/'samples/phase29/independent-errors.json').read_text())['allowed_repairs'];parts={r['part'] for r in repairs}
 for part in parts:
  root=E.fromstring(a[part]);new=E.fromstring(b[part]);expected=deepcopy(root)
  for e in repairs:
   if e['part']!=part:continue
   if 'paragraph' in e:p=expected.find(q('body')).findall(q('p'))[e['paragraph']-1]
   else:p=next(n for n in expected if n.get(q('id'))==e['note_id']).findall(q('p'))[e['note_paragraph']-1]
   r=p.findall(q('hyperlink'))[e['link']-1].findall(q('r'))[e['link_run']-1] if 'link' in e else p.findall(q('r'))[e['run']-1]
   rp=put(r,'rPr')
   if e['property']=='size':put(rp,'sz').set(q('val'),str(round(e['value']*2)))
   else:
    slot=e['property'][5:];rf=put(rp,'rFonts');rf.set(q(slot),e['value']);rf.attrib.pop(q(slot+'Theme'),None)
  assert canon(expected)==canon(new),'Not exactly selected attribute changes: '+part
  assert root.xpath('//w:t/text()',namespaces=NS)==new.xpath('//w:t/text()',namespaces=NS),'Text, whitespace or order changed'
  assert [(root.getroottree().getpath(h),dict(h.attrib)) for h in root.iter(q('hyperlink'))]==[(new.getroottree().getpath(h),dict(h.attrib)) for h in new.iter(q('hyperlink'))]
  for tag in ('rStyle','footnoteRef','endnoteRef','separator','continuationSeparator','bookmarkStart','bookmarkEnd','fldChar','fldSimple','instrText','tbl','drawing','sectPr'):
   assert [canon(e) for e in root.iter(q(tag))]==[canon(e) for e in new.iter(q(tag))],tag
  for r in new.iter(q('r')):
   if r.find(q('rPr')) is not None:assert r[0].tag==q('rPr') and len(r.findall(q('rPr')))==1
 for part,data in a.items():
  if part not in parts:assert data==b[part],part
 assert all(a[n]==b[n] for n in a if n.endswith('.rels'))
 assert Path(original).read_bytes()==raw
 return {'source_sha256':hashlib.sha256(raw).hexdigest(),'output_sha256':hashlib.sha256(out).hexdigest(),'authored_attribute_repairs':len(repairs),'only_selected_attributes_changed':True,'exact_text_whitespace_order':True,'all_relationship_files_byte_equal':True,'hyperlink_nodes_attributes_order_preserved':True,'styles_markers_separators_fields_tables_media_sections_preserved':True,'rPr_precedes_run_content':True,'unselected_parts_byte_equal':True,'original_unchanged':True,'external_targets_not_opened':True,'not_a_reachability_or_visual_verdict':True}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('original');p.add_argument('output');p.add_argument('--repairs');a=p.parse_args();print(json.dumps(verify(a.original,a.output,json.loads(Path(a.repairs).read_text()) if a.repairs else None),ensure_ascii=False,indent=2))

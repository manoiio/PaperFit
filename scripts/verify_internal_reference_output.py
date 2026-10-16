"""Independent raw ZIP/XML oracle. Does NOT import R44, traversal or engine masks."""
from pathlib import Path
import json,zipfile,argparse
from lxml import etree as E
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main';N={'w':W}
Q=lambda t:'{'+W+'}'+t
S=Path(__file__).resolve().parents[1]/'samples/phase32'
def verify(before,after,repairs=None):
 with zipfile.ZipFile(before) as z:a={n:z.read(n) for n in z.namelist()}
 with zipfile.ZipFile(after) as z:b={n:z.read(n) for n in z.namelist()}
 assert set(a)==set(b),'ZIP member set changed'
 allowed=json.loads((S/'independent-plan.json').read_text())['repairs'] if repairs is None else repairs
 roots={}
 for e in allowed:
  part=e['part'];old,new=roots.setdefault(part,(E.fromstring(a[part]),E.fromstring(b[part])))
  def locate(root):
   p=root.find(Q('body')).findall(Q('p'))[e['paragraph']-1] if part=='word/document.xml' else next(n for n in root if n.get(Q('id'))==e['note_id']).findall(Q('p'))[e['note_paragraph']-1]
   return p.findall(Q('hyperlink'))[e['link']-1].findall(Q('r'))[e['link_run']-1]
  x,y=locate(old),locate(new);assert y.find('w:rPr/w:sz',N).get(Q('val'))==str(e['pt']*2),'selected size missing'
  # Restore ONLY this selected attribute to its before value; compare entire trees.
  y.find('w:rPr/w:sz',N).set(Q('val'),x.find('w:rPr/w:sz',N).get(Q('val')))
 for part in a:
  if part in roots:assert E.tostring(roots[part][0],method='c14n')==E.tostring(roots[part][1],method='c14n'),part+' non-whitelisted change'
  else:assert a[part]==b[part],part+' unselected part bytes changed'
 return {'selected_size_attributes':len(allowed),'only_selected_attributes_changed':True,'all_bookmarks_link_attributes_fields_cache_text_whitespace_and_order_preserved':True,'relationship_members_byte_identical':True,'unselected_parts_byte_identical':True}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('before');p.add_argument('after');a=p.parse_args();print(json.dumps(verify(a.before,a.after),ensure_ascii=False,indent=2))

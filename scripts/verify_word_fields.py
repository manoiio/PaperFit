"""Independent raw ZIP/XML author oracle; no updater/indexer/planner imports."""
from pathlib import Path
from copy import deepcopy
import argparse,zipfile,json,hashlib
from lxml import etree as E
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}';N={'w':W[1:-1]}
def canon(e):return E.tostring(e,method='c14n',exclusive=True)
def verify(before,after):
 with zipfile.ZipFile(before) as z:a={n:z.read(n) for n in z.namelist()}
 with zipfile.ZipFile(after) as z:b={n:z.read(n) for n in z.namelist()}
 assert set(a)==set(b)
 assert all(a[n]==b[n] for n in a if n!='word/document.xml')
 x=E.fromstring(a['word/document.xml']);y=E.fromstring(b['word/document.xml']);body=x.find(W+'body');out=y.find(W+'body');old=body.findall(W+'p')[4];rows=out.findall(W+'p')[4:6]
 expected=[('第1章 合成研究','5',7),('第2章 合成结果','7',11)]
 for p,(title,page,original_n) in zip(rows,expected):
  links=p.findall(W+'hyperlink');assert len(links)==1;link=links[0];texts=link.xpath('.//w:t/text()',namespaces=N);assert ''.join(texts)==title+page
  anchor=link.get(W+'anchor');starts=y.xpath('.//w:bookmarkStart[@w:name=$n]',namespaces=N,n=anchor);assert len(starts)==1;target=starts[0].getparent();assert ''.join(target.xpath('.//w:t/text()',namespaces=N))==title
  # Author-known original heading identity, including duplicate-safe object order.
  assert anchor=='PFToc_'+hashlib.sha256(Path(before).read_bytes()).hexdigest()[:12]+'_'+str(original_n)
  ident=starts[0].get(W+'id');starts[0].getparent().remove(starts[0]);ends=y.xpath('.//w:bookmarkEnd[@w:id=$i]',namespaces=N,i=ident);assert len(ends)==1;ends[0].getparent().remove(ends[0])
 for p in rows:out.remove(p)
 out.insert(list(body).index(old),deepcopy(old))
 expected_fields={'REF CaptionOne \\h':'图1-2 合成曲线','PAGEREF ChapterTwo \\h':'7'}
 for code,value in expected_fields.items():
  original=[f for f in x.iter(W+'fldSimple') if f.get(W+'instr','').strip()==code];new=[f for f in y.iter(W+'fldSimple') if f.get(W+'instr','').strip()==code];assert len(original)==len(new)==1
  assert ''.join(new[0].xpath('.//w:t/text()',namespaces=N))==value
  # Exact node/format reverse mask; only cache text changes are authorised.
  clone=deepcopy(new[0]);cache=clone.xpath('.//w:t',namespaces=N);assert len(cache)==1
  cache[0].text=''.join(original[0].xpath('.//w:t/text()',namespaces=N));old_t=original[0].find('.//'+W+'t');space='{http://www.w3.org/XML/1998/namespace}space'
  if old_t.get(space) is None:assert cache[0].attrib=={space:'preserve'};cache[0].attrib.pop(space)
  assert canon(clone)==canon(original[0]);new[0].getparent().replace(new[0],deepcopy(original[0]))
 assert x.nsmap==y.nsmap
 assert canon(x)==canon(y),'unselected XML or content changed'
 return {'only_authorised_TOC_cache_REF_PAGEREF_and_two_bookmarks':True,'all_other_XML_exact_after_reverse_mask':True,'all_other_ZIP_parts_byte_equal':True,'missing_locked_SEQ_preserved':True,'source_sha256':hashlib.sha256(Path(before).read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(Path(after).read_bytes()).hexdigest(),'expected_TOC_pages':['5','7'],'physical_page_claim':'not inferred here; native Word observations recorded separately'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('before');p.add_argument('after');a=p.parse_args();print(json.dumps(verify(a.before,a.after),ensure_ascii=False,indent=2))

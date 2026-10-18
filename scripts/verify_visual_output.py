"""Independent ZIP/XML oracle. No planner, resolver, field or numbering imports."""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
from lxml import etree as E
import json,sys
N={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'};W='{'+N['w']+'}'
def c(e):return E.tostring(e,method='c14n')
def read(path):
 with ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}
def verify(source,before,final,expected):
 a,b,f=map(read,(source,before,final));ar,br,fr=[E.fromstring(p['word/document.xml']) for p in (a,b,f)]
 assert set(b)==set(f)
 for n in b:
  if n!='word/document.xml':assert b[n]==f[n],n
 assert a['word/numbering.xml']==f['word/numbering.xml'],'numbering definitions changed'
 ab=ar.find('w:body',N);bb=br.find('w:body',N);fb=fr.find('w:body',N)
 aps=ab.findall('w:p',N);fps=fb.findall('w:p',N);assert len(aps)==len(fps)==expected['top_level_paragraphs']
 for h in expected['headings']:
  x,y=aps[h['paragraph']-1],fps[h['paragraph']-1]
  assert x.xpath('.//w:t/text()',namespaces=N)==y.xpath('.//w:t/text()',namespaces=N)
  for path in ('w:pPr/w:numPr','w:pPr/w:pStyle'):
   u,v=x.find(path,N),y.find(path,N);assert (c(u) if u is not None else None)==(c(v) if v is not None else None)
 shell=fb.find('w:sdt',N);old=bb.find('w:sdt',N)
 assert dict(shell.attrib)==dict(old.attrib)
 for key in ('sdtPr','sdtEndPr'):
  x,y=shell.find(W+key),old.find(W+key);assert (c(x) if x is not None else None)==(c(y) if y is not None else None)
 assert c(shell.find('w:sdtContent/w:p',N))==c(old.find('w:sdtContent/w:p',N)),'outside-field directory title changed'
 entries=[]
 for link in shell.xpath('./w:sdtContent/w:p/w:hyperlink',namespaces=N):
  anchor=link.get(W+'anchor');found=fr.xpath('.//w:bookmarkStart[@w:name=$n]',namespaces=N,n=anchor);assert len(found)==1
  par=found[0].getparent();n=fps.index(par)+1;h=next(h for h in expected['headings'] if h['paragraph']==n)
  raw=''.join((e.text or '') if e.tag==W+'t' else '\t' if e.tag==W+'tab' else '' for e in link.iter());prefix=h['display']+'\t'+h['text']+'\t';assert raw.startswith(prefix),raw
  page=raw[len(prefix):];assert page.isdigit() and int(page)>0
  entries.append({'paragraph':n,'number':h['display'],'title':h['text'],'page':page,'anchor':anchor})
 assert len(entries)==4 and [x['paragraph'] for x in entries]==[5,15,25,35]
 # Remove only the exact new heading bookmark pairs; restore only the authorised
 # SDT cache paragraphs. The rest of the full document, including the shell,
 # other bookmarks, every paragraph and pPr/rPr, must be canonical-byte equal.
 names=set(br.xpath('.//w:bookmarkStart/@w:name',namespaces=N))
 for bm in list(fr.iter(W+'bookmarkStart')):
  name=bm.get(W+'name')
  if name in names:continue
  assert name.startswith('PFToc_')
  assert bm.getparent() in fps and fps.index(bm.getparent())+1 in (5,15,25,35)
  ends=fr.xpath('.//w:bookmarkEnd[@w:id=$i]',namespaces=N,i=bm.get(W+'id'));assert len(ends)==1 and ends[0].getparent() is bm.getparent()
  bm.getparent().remove(bm);ends[0].getparent().remove(ends[0])
 newcontent=shell.find(W+'sdtContent');oldcontent=old.find(W+'sdtContent')
 for p in list(newcontent)[1:]:newcontent.remove(p)
 from copy import deepcopy
 for p in list(oldcontent)[1:]:newcontent.append(deepcopy(p))
 assert c(fr)==c(br),'unauthorised document subtree changed'
 return {'passed':True,'final_sha256':sha256(Path(final).read_bytes()).hexdigest(),'numbering_xml_byte_equal':True,'all_other_field_stage_parts_byte_equal':True,'sdt_shell_and_outside_title_preserved':True,'top_level_identity_preserved':True,'heading_numPr_styles_and_text_preserved':True,'exact_reverse_mask_document_equal':True,'entries':entries}

def ordinary(folder):
 from copy import deepcopy
 a,b=map(read,(folder/'source.docx',folder/'format.docx'))
 assert set(a)==set(b)
 for name in a:
  if name!='word/document.xml':assert a[name]==b[name],name
 roots=[E.fromstring(x['word/document.xml']) for x in (a,b)]
 assert roots[0].xpath('//w:t/text()',namespaces=N)==roots[1].xpath('//w:t/text()',namespaces=N)
 changes=json.loads((folder/'stage-1-changes.json').read_text())
 allowed={}
 def permit(root,change):
  loc=change['locator'];rule=change['rule_id'];prop=loc.get('property','')
  if 'paragraph' in loc:
   p=root.find('w:body',N).findall('w:p',N)[loc['paragraph']-1]
   node=p.findall('w:r',N)[loc['run']-1] if 'run' in loc else p
  else:node=root.xpath('//w:sectPr',namespaces=N)[loc['section']-1]
  if rule=='R01':spec=[('w:pgSz',['w','h','orient'])]
  elif rule=='R02':spec=[('w:pgMar',['top','bottom','left','right'])]
  elif rule=='R03' or prop=='font_eastAsia':spec=[('w:rPr/w:rFonts',['eastAsia','eastAsiaTheme'])]
  elif rule=='R04':
   slots=set(change['after']);assert slots<={'ascii','hAnsi'};spec=[('w:rPr/w:rFonts',list(slots)+[x+'Theme' for x in slots])]
  elif rule=='R05' or prop=='size':spec=[('w:rPr/w:sz',['val'])]
  elif rule=='R06' or prop in ('line_spacing','line'):spec=[('w:pPr/w:spacing',['line','lineRule'])]
  elif rule=='R07':spec=[('w:pPr/w:ind',['firstLine','firstLineChars','hanging','hangingChars'])]
  elif prop in ('before','after'):spec=[('w:pPr/w:spacing',[prop,prop+'Lines',prop+'Autospacing'])]
  elif prop.startswith('text_'):
   tag={'shadow':'shadow','outline':'outline','emboss':'emboss','imprint':'imprint','scale':'w','character_spacing':'spacing','baseline':'position'}[prop[5:]]
   spec=[('w:rPr/w:'+tag,['val'])]
  else:raise AssertionError((rule,prop))
  for path,attrs in spec:
   x=node.find(path,N)
   if x is not None:
    for key in attrs:x.attrib.pop(W+key,None)
    if not len(x) and not x.attrib and not x.text:x.getparent().remove(x)
  # Remove only empty property containers created by the selected attributes.
  for path in ('w:rPr','w:pPr'):
   x=node.find(path,N)
   if x is not None and not len(x) and not x.attrib and not x.text:node.remove(x)
 for change in changes:
  assert change['verification']=='pass'
  for r in roots:permit(r,change)
 assert c(roots[0])==c(roots[1]),'unselected ordinary-format XML changed'
 # Hand-written actual normalization expectations, without the new resolver.
 raw=E.fromstring(b['word/document.xml']);ps=raw.find('w:body',N).findall('w:p',N)
 for number,tags in {6:{'shadow':'0','outline':'0','w':'100','spacing':'0','position':'0'},7:{'emboss':'0'},8:{'imprint':'0'}}.items():
  run=ps[number-1].find('w:r',N)
  for tag,value in tags.items():assert run.find('w:rPr/w:'+tag,N).get(W+'val')==value,(number,tag)
 for number in (15,25):
  fonts=ps[number-1].find('w:r/w:rPr/w:rFonts',N)
  assert fonts.get(W+'eastAsia')=='黑体' and fonts.get(W+'eastAsiaTheme') is None
 citation=ps[5].findall('w:r',N)[-1];old=E.fromstring(a['word/document.xml']).find('w:body',N).findall('w:p',N)[5].findall('w:r',N)[-1]
 assert c(citation)==c(old) and ''.join(citation.xpath('.//w:t/text()',namespaces=N))=='[1]'
 return {'selected_changes':len(changes),'all_other_parts_byte_equal':True,'reverse_exact_attribute_mask_equal':True,'handwritten_effect_values_pass':True,'superscript_run_byte_equal':True}

def structure(folder):
 a,b=map(read,(folder/'format.docx',folder/'pages.docx'));added=set(b)-set(a)
 assert added=={'word/footerPF'+str(i)+'.xml' for i in range(1,5)}
 special={'word/document.xml','word/_rels/document.xml.rels','[Content_Types].xml'}
 for name in a:
  if name not in special:assert a[name]==b[name],name
 ar,br=[E.fromstring(x['word/document.xml']) for x in (a,b)]
 aps=ar.find('w:body',N).findall('w:p',N);bps=br.find('w:body',N).findall('w:p',N);assert len(aps)==len(bps)==47
 for x,y in zip(aps,bps):assert [c(r) for r in x.findall('w:r',N)]==[c(r) for r in y.findall('w:r',N)]
 sections=br.xpath('//w:sectPr',namespaces=N);assert len(sections)==4
 for i,s in enumerate(sections):
  pn=s.find('w:pgNumType',N)
  if i==0:assert pn is None
  else:
   assert pn.get(W+'fmt')==('lowerRoman' if i==1 else 'decimal')
   assert pn.get(W+'start')==('1' if i in (1,2) else None)
  for key in ('pgSz','pgMar','headerReference','footnotePr','endnotePr','cols'):
   old=ar.xpath('//w:sectPr',namespaces=N)[0].find(W+key);new=s.find(W+key)
   assert (c(old) if old is not None else None)==(c(new) if new is not None else None),(i,key)
 reltag='{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'
 rel_a=E.fromstring(a['word/_rels/document.xml.rels']);rel_b=E.fromstring(b['word/_rels/document.xml.rels'])
 old_ids={x.get('Id') for x in rel_a}
 for r in rel_a:assert any(c(r)==c(x) for x in rel_b)
 new=[r for r in rel_b if r.get('Id') not in old_ids];assert len(new)==4
 for r in new:assert r.get('Type').endswith('/footer') and 'word/'+r.get('Target') in added
 ct_a=E.fromstring(a['[Content_Types].xml']);ct_b=E.fromstring(b['[Content_Types].xml'])
 for item in ct_a:assert any(c(item)==c(x) for x in ct_b)
 assert len(ct_b)-len(ct_a)==4
 for i in range(1,5):
  root=E.fromstring(b[f'word/footerPF{i}.xml']);texts=root.xpath('//w:t/text()',namespaces=N);codes=root.xpath('//w:instrText/text() | //w:fldSimple/@w:instr',namespaces=N)
  if i==1:assert not texts and not codes
  else:assert len(codes)==1 and codes[0].strip()=='PAGE'
  if i>2:assert ''.join(texts)=='研究方法  '
 # Reverse only exact authorised section locations/properties; pPr and all other
 # text outside these targets must remain identical.
 for p in bps:
  x=p.find('w:pPr/w:sectPr',N)
  if x is not None:
   assert bps.index(p)+1 in (1,4,34);x.getparent().remove(x)
 for n in (2,5):
  x=bps[n-1].find('w:pPr/w:pageBreakBefore',N)
  if x is not None:x.getparent().remove(x)
 body=br.find('w:body',N);body.replace(body.find('w:sectPr',N),E.fromstring(E.tostring(ar.find('w:body/w:sectPr',N))))
 for root in (ar,br):
  for p in root.find('w:body',N).findall('w:p',N):
   pp=p.find(W+'pPr')
   if pp is not None and not len(pp) and not pp.attrib:p.remove(pp)
 assert c(ar)==c(br),'unselected section-stage content changed'
 return {'new_footer_parts':4,'all_original_relationships_and_parts_preserved':True,'section_geometry_headers_notes_preserved':True,'run_subtrees_preserved':True,'exact_authorised_structure_mask_equal':True}

def pagination(folder):
 a,b=map(read,(folder/'pages.docx',folder/'before-update.docx'));assert set(a)==set(b)
 for n in a:
  if n!='word/document.xml':assert a[n]==b[n]
 roots=[E.fromstring(x['word/document.xml']) for x in (a,b)]
 for root in roots:
  p=root.find('w:body',N).findall('w:p',N)[1];pp=p.find(W+'pPr')
  for tag in ('keepNext','keepLines'):
   x=pp.find(W+tag)
   if x is not None:pp.remove(x)
 assert c(roots[0])==c(roots[1])
 return {'only_p2_keepNext_keepLines':True,'all_other_parts_equal':True}

def main(folder,comparison=None):
 folder=Path(folder);expected=json.loads((folder/'expected.json').read_text())
 result={'ordinary':ordinary(folder),'pages':structure(folder),'pagination':pagination(folder),'directory':verify(folder/'source.docx',folder/'before-update.docx',folder/'fixed.docx',expected)}
 bundle=json.loads((folder/'rules.json').read_text());template=bundle['modules']['main']['template'];text=(folder/'requirements.txt').read_text()
 for name,value in expected['fields'].items():
  assert template['final_values'][name]==value
  source=template['field_sources'][name]
  assert source['kind']=='ai_extracted' and source['quote'] in text and source['quote']
 with ZipFile(Path(__file__).resolve().parents[1]/'samples/phase52/result.zip') as baseline_zip:baseline=json.loads(baseline_zip.read('rule-bundle.json'))
 old=baseline['modules']['main']['template']
 for name,value in old['final_values'].items():
  if name not in expected['fields']:
   assert template['final_values'][name]==value and template['field_sources'][name]==old['field_sources'][name],name
 for name in set(template['final_values'])-set(old['final_values'])-set(expected['fields']):
  assert template['final_values'][name] is None and template['field_sources'][name]=={'kind':'not_enabled','location':None,'quote':''},name
 assert bundle['modules']['main']['disabled_fields']==baseline['modules']['main']['disabled_fields']
 for module in ('front','toc','notes'):assert bundle['modules'][module]==baseline['modules'][module]
 result['rules']={'handwritten_13_values_and_real_continuous_sources':True,'untouched_values_and_sources_equal_baseline':True,'other_modules_and_disabled_fields_equal':True}
 if comparison:
  result['browser_equals_local_bytes']=Path(comparison).read_bytes()==(folder/'fixed.docx').read_bytes();assert result['browser_equals_local_bytes']
 with ZipFile(folder/'result.zip') as z:
  assert z.read('fixed.docx')==(folder/'fixed.docx').read_bytes() and z.read('Word预览.pdf')==(folder/'fixed.pdf').read_bytes()
  record=json.loads(z.read('Word输出记录.json'));assert record['document_sha256']==result['directory']['final_sha256'];assert record['word_export']['pdf_sha256']==sha256((folder/'fixed.pdf').read_bytes()).hexdigest()
  result['pdf_bound_to_download_and_package']=True
 return result
if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('folder',nargs='?',default='samples/phase53');a.add_argument('--comparison');v=a.parse_args();print(json.dumps(main(v.folder,v.comparison),ensure_ascii=False,indent=2))

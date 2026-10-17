"""Current-stage offline mock orchestration + raw ZIP/XML and original legal path.
Expected supplement values are handwritten in samples, never parsed by this script.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
import json,sys,zipfile,argparse
from lxml import etree as E
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from web.session import WebSession
from web.onepass_session import start
from ai.smart_spec import parse_requirements
from ai.short_spec import Settings
from core.package import NS,q,sha256


def independent(source,output):
 with zipfile.ZipFile(source) as z:a={n:z.read(n) for n in z.namelist()}
 with zipfile.ZipFile(output) as z:b={n:z.read(n) for n in z.namelist()}
 assert a.keys()==b.keys();assert all(a[n]==b[n] for n in a if n!='word/document.xml')
 x,y=E.fromstring(a['word/document.xml']),E.fromstring(b['word/document.xml'])
 assert x.xpath('//w:t/text()',namespaces=NS)==y.xpath('//w:t/text()',namespaces=NS)
 for tag in ('hyperlink','bookmarkStart','bookmarkEnd','fldChar','instrText','drawing','tbl','footnoteReference','endnoteReference'):
  assert [E.tostring(e,method='c14n') for e in x.iter(q(tag))]==[E.tostring(e,method='c14n') for e in y.iter(q(tag))]
 ps=y.find(q('body')).findall(q('p'));assert len(ps)==6
 # Author-written expected XML, independent of the AI/new parser.
 for i in (1,3,5):
  p=ps[i];pr=p.find(q('pPr'));assert pr.find(q('ind')).get(q('firstLineChars'))=='200';spacing=pr.find(q('spacing'));assert spacing.get(q('line'))=='480' and spacing.get(q('lineRule'))=='auto';assert spacing.get(q('beforeLines'))=='50' and spacing.get(q('after'))=='120';assert pr.find(q('jc')).get(q('val'))=='left'
 for i,p in enumerate(ps):
  font='黑体' if i in (0,4) else '宋体';size='32' if i==0 else '24'
  for r in p.findall(q('r')):
   assert r.find('w:rPr/w:rFonts',NS).get(q('eastAsia'))==font;assert r.find('w:rPr/w:sz',NS).get(q('val'))==size
 def mask(root):
  for i,p in enumerate(root.find(q('body')).findall(q('p'))):
   pr=p.find(q('pPr'))
   if pr is not None:
    for tag in ('jc','spacing'):
     e=pr.find(q(tag))
     if e is not None:pr.remove(e)
   ind=pr.find(q('ind')) if pr is not None else None
   if ind is not None:
    for n in ('firstLine','firstLineChars','hanging','hangingChars'):ind.attrib.pop(q(n),None)
    if not ind.attrib and not len(ind):pr.remove(ind)
   if pr is not None and not len(pr) and not pr.attrib:p.remove(pr)
   for r in p.findall(q('r')):
    pr=r.find(q('rPr'))
    if pr is not None:
     e=pr.find(q('rFonts'))
     if e is not None:
      if i in (0,2,4):
       assert e.get(q('ascii')) in ('楷体','Times New Roman');e.attrib.pop(q('ascii'),None)
      for n in ('eastAsia','eastAsiaTheme'):e.attrib.pop(q(n),None)
      if not e.attrib and not len(e):pr.remove(e)
     e=pr.find(q('sz'))
     if e is not None:pr.remove(e)
     if not len(pr) and not pr.attrib:r.remove(pr)
  sect=root.find(q('body')).find(q('sectPr'))
  for tag,names in [('pgSz',('w','h','orient')),('pgMar',('top','bottom','left','right'))]:
   e=sect.find(q(tag))
   for n in names:e.attrib.pop(q(n),None)
 mask(x);mask(y);assert E.tostring(x,method='c14n')==E.tostring(y,method='c14n')
 return {'all_text_and_order_equal':True,'unselected_parts_byte_equal':True,'authored_font_size_line_indent_spacing_alignment':True,'other_XML_equal_after_explicit_format_mask':True}


def main(out,browser_zip=None):
 out=Path(out)
 if out.exists():raise SystemExit('Output must not exist')
 out.mkdir(parents=True);source=ROOT/'samples/phase44/supplement.docx';text=(ROOT/'samples/phase44/requirements.txt').read_text().strip();expected=json.loads((ROOT/'samples/phase44/expected-overrides.json').read_text())
 def session(name):
  s=WebSession(out/name);s.set_mode('academic');assert s.load(source.read_bytes(),'合成.docx');return s
 s=session('smart')
 def parser(t):return parse_requirements(t,config=Settings('synthetic'),transport=lambda *_:json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(expected)}}]}))
 state={};start(s,state,text,spec_parser=parser,structure_runner=lambda *_:(_ for _ in ()).throw(AssertionError('No structure POST needed')));assert state['status']=='done',state.get('error')
 (out/'fixed.docx').write_bytes(s.downloads()['fixed.docx']);(out/'result.zip').write_bytes(s.result_package())
 record={'source':'offline authored mock, not live API','mock_output_sha256':sha256(s.downloads()['fixed.docx']),'independent':independent(source,out/'fixed.docx')}
 for label,pack in [('mock',out/'result.zip')]+([('actual_browser',Path(browser_zip))] if browser_zip else []):
  with zipfile.ZipFile(pack) as z:raw=z.read('fixed.docx');scope=json.loads(z.read('scope.json'));bundle=z.read('rules.json')
  ref=session('legal-'+label);ref.import_rule_bundle(bundle);ref.apply_workbench(acknowledged=True);ref.set_types(scope['paragraph_types']);assert ref.confirm_and_check(),ref.error
  ref.set_selection([f['key'] for f in ref.eligible() if f['rule_id'].startswith('R') and f['rule_id']!='R35']);assert ref.generate(),ref.error;assert raw==ref.downloads()['fixed.docx']
  p=out/(label+'.docx');p.write_bytes(raw);record[label]={'sha256':sha256(raw),'original_legal_bytes_equal':True,'independent':independent(source,p)}
 (out/'independent.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--browser-zip');a=p.parse_args();main(a.output,a.browser_zip)

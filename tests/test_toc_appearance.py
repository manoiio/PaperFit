"""Author-value checks for published TOC appearance and old-command intent."""
import json,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from types import SimpleNamespace
from core.package import Package,q,NS,DemoError
from core import word_fields as wf
from core.toc_appearance import prepare
ROOT=Path(__file__).resolve().parents[1]
class AppearanceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.source=ROOT/'samples/phase50/errors.docx';self.pkg=Package(self.source);self.f=wf.fields(self.pkg)[0][0];self.m={'input_sha256':self.pkg.hash,'paragraph_types':json.loads((ROOT/'samples/phase50/roles.json').read_text()),'confirmed':True,'confirmation':'手写范围'}
 def test_missing_stops_all_levels_and_different_section_widths(self):
  from lxml import etree as E
  for width in (8640,7200):
   from core.widths import _sections
   owner=wf.field_block(self.pkg,self.f)[0];_,sp=_sections(self.pkg)[owner];size=sp.find(q('pgSz'));m=sp.find(q('pgMar'));size.set(q('w'),str(width+int(m.get(q('left')))+int(m.get(q('right')))))
   ts,r=prepare(self.pkg,self.f,{},[1,2,3]);self.assertEqual(r['state'],'applied')
   for level,p in ts.items():
    stop=p.find('w:tabs/w:tab[@w:val="right"]',NS);self.assertEqual(stop.get(q('pos')),str(width));self.assertEqual(stop.get(q('leader')),'dot');self.assertEqual(p.find(q('ind')).get(q('left')),str((level-1)*360));self.assertLess(list(p).index(p.find(q('tabs'))),list(p).index(p.find(q('ind'))))
 def test_correct_settings_are_kept_exactly(self):
  from lxml import etree as E
  ts,_=prepare(self.pkg,self.f,{},[1,2,3]);out,r=prepare(self.pkg,self.f,ts,[1,2,3]);self.assertEqual(r['state'],'already_satisfied');self.assertEqual([wf.canon(p) for p in ts.values()],[wf.canon(p) for p in out.values()])
 def test_implicit_builtin_toc_style_only_gets_explicit_geometry(self):
  from lxml import etree as E
  pr=E.Element(q('pPr'));E.SubElement(pr,q('pStyle')).set(q('val'),'TOC2');E.SubElement(pr,q('spacing')).set(q('line'),'260')
  ts,r=prepare(self.pkg,self.f,{2:pr},[2]);self.assertEqual(r['state'],'applied');self.assertEqual(ts[2].find(q('pStyle')).get(q('val')),'TOC2');self.assertEqual(ts[2].find(q('spacing')).get(q('line')),'260');self.assertIsNone(ts[2].find(q('rPr')))
 def test_nonordinary_direction_or_numbered_cache_keeps_original(self):
  from lxml import etree as E
  for tag in ('bidi','textDirection','numPr'):
   pr=E.Element(q('pPr'));e=E.SubElement(pr,q(tag));e.set(q('val'),'1' if tag=='bidi' else 'tbRl')
   out,r=prepare(self.pkg,self.f,{1:pr},[1]);self.assertEqual(r['state'],'kept');self.assertEqual(wf.canon(out[1]),wf.canon(pr))
 def test_complex_columns_keep_original_and_explain(self):
  from core.widths import _sections
  _,sp=_sections(self.pkg)[wf.field_block(self.pkg,self.f)[0]];sp.find(q('cols')).set(q('num'),'2');out,r=prepare(self.pkg,self.f,{},[1,2,3]);self.assertEqual(out,{});self.assertEqual(r['state'],'kept');self.assertIn('栏',r['reason'])
 def test_published_result_and_creation_use_the_same_appearance(self):
  from test_word_fields import WordFieldsTests
  mock=lambda *a,**k:WordFieldsTests.mock(SimpleNamespace(root=self.root),*a,**k)
  r=wf.update(self.source,self.root/'fixed.docx',self.m,wf.plan(self.source,self.m,appearance='standard'),calculator=mock)
  p=Package(r['output']);self.assertTrue(any(c['property']=='toc_appearance' for c in r['changes']));self.assertEqual(r['proof']['toc_appearance'][0]['state'],'applied')
  for f in wf.fields(p)[0]:
   if f['instruction'].strip().startswith('TOC'):
    for row in wf.field_block(p,f):self.assertIsNotNone(row.find('w:pPr/w:tabs/w:tab[@w:leader="dot"]',NS))
  for n in self.pkg.parts:
   if n!='word/document.xml':self.assertEqual(self.pkg.parts[n],p.parts[n])
  # A later refresh in preserve mode must keep all three levels, even without TOC style IDs.
  again=wf.update(r['output'],self.root/'refreshed.docx',r['classification'],wf.plan(r['output'],r['classification']),calculator=mock,artifact_dir=self.root/'refresh')
  self.assertEqual(Path(again['output']).read_bytes(),Path(r['output']).read_bytes())
  from core.toc import make_scope
  original=Package(self.source);f=original.root.xpath('.//w:fldSimple',namespaces=NS)[0];f.getparent().remove(f);path=self.root/'manual.docx';path.write_bytes(original.bytes(True));m=deepcopy(self.m);m['input_sha256']=Package(path).hash;scope=make_scope(path);scope.update(confirmed=True,objects={'d:4':'title','d:5':'level1'});m['toc_scope']=scope
  r=wf.update(path,self.root/'created.docx',m,wf.plan(path,m,[],{'start':5,'end':5,'levels':[1,2,3],'confirmed':True},'standard'),calculator=mock,artifact_dir=self.root/'creation')
  self.assertEqual(r['proof']['toc_appearance'][0]['state'],'applied')
 def test_standard_appearance_runs_through_background_archive_and_adoption(self):
  from test_word_fields import WordFieldsTests
  from web.session import WebSession
  from web import field_session
  from core.preview_jobs import PreviewJobs
  from unittest.mock import patch
  import time
  s=WebSession(self.root/'web');s.set_mode('academic');s.load(self.source.read_bytes(),'公开.docx');s.set_types(self.m['paragraph_types']);s.confirm_classification();s.page_layout_draft={'enabled':True,'explicit':True,'policy':dict(__import__('core.page_policy',fromlist=['DEFAULT']).DEFAULT),'input_sha256':s.inventory['input_sha256'],'regions':[],'toc_appearance':'standard','word_updates':True};state={};real=wf.update
  def controlled(*a,**kw):return real(*a,**kw,calculator=lambda *x,**y:WordFieldsTests.mock(SimpleNamespace(root=self.root),*x,**y))
  with patch('core.word_fields.update',side_effect=controlled):
   field_session.submit(s,state,appearance='standard',scheduler=PreviewJobs())
   for _ in range(300):
    status=field_session.receive(s,state)
    if status['state'] not in ('queued','running'):break
    time.sleep(.01)
   self.assertEqual(status['state'],'succeeded',status);field_session.adopt(s,state);field_session.adopt(s,state)
  self.assertEqual(s.generation_count,1);self.assertTrue(s.downloads());self.assertTrue(any(x['property']=='toc_appearance' for x in s.result['changes']))
  raw=s.prepare_project();other=WebSession(self.root/'restored');other.stage_project(raw);other=other.restore_project(acknowledged=True);self.assertEqual(other.page_layout_draft,s.page_layout_draft);self.assertTrue(other.history[-1]['result']['restored_history'])
 def test_unsafe_new_section_boundary_is_one_central_decision_not_silent_failure(self):
  from lxml import etree as E
  from web.session import WebSession
  from web.onepass_session import start
  from core.page_policy import DEFAULT
  p=Package(ROOT/'samples/phase55/source.docx');head=next(x for x in p.paragraphs if x.find('w:pPr/w:pStyle',NS) is not None and x.find('w:pPr/w:pStyle',NS).get(q('val'))=='Heading1');prev=p.paragraphs[p.paragraphs.index(head)-1];r=E.SubElement(prev,q('r'));E.SubElement(r,q('br')).set(q('type'),'page');path=self.root/'unsafe.docx';path.write_bytes(p.bytes(True))
  s=WebSession(self.root/'conflict');s.set_mode('academic');s.load(path.read_bytes(),'公开.docx');s.page_layout_draft={'enabled':True,'policy':{**DEFAULT,'pages':'front-body'},'regions':[]};state={};start(s,state,structure_runner=lambda *_:(_ for _ in ()).throw(DemoError('no API')))
  self.assertEqual(state['status'],'waiting',state.get('error'));self.assertTrue(any(q['id']=='page_conflict' for q in state['questions']));self.assertFalse(s.history);self.assertEqual(s.input_path.read_bytes(),path.read_bytes())
 def test_preserve_mode_and_invalid_mode(self):
  self.assertEqual(wf.plan(self.source,self.m)['appearance'],'preserve')
  with self.assertRaises(DemoError):wf.plan(self.source,self.m,appearance='guess')
 def test_smart_defaults_and_old_saved_intent(self):
  from web.page_ui import smart_seed
  model=SimpleNamespace(page_layout_draft=None,inventory=None,history=[],workbench={})
  r=smart_seed(model);self.assertTrue(r['enabled']);self.assertEqual(r['policy']['version'],3);self.assertEqual(r['toc_appearance'],'standard')
  model.inventory={'input_sha256':'test'};old={**__import__('core.page_policy',fromlist=['DEFAULT']).DEFAULT,'dynamic':True}
  model.current_rule_bundle=lambda:{'assembly':old};r=smart_seed(model);self.assertEqual(r['policy'],old);self.assertEqual(r['toc_appearance'],'preserve')
  from web.page_ui import word_seed
  self.assertFalse(word_seed(model,r));r['word_updates']=True;self.assertTrue(word_seed(model,r))
  model.current_rule_bundle=lambda:{};model.workbench={'origin':'restored'};self.assertFalse(smart_seed(model)['enabled'])
  model.page_layout_draft={'enabled':False,'explicit':True,'policy':old};self.assertEqual(smart_seed(model),model.page_layout_draft)

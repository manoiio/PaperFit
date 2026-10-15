"""第六阶段属性、会话、可选渲染失败及文件保护；渲染mock明确不作为视觉证据。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest.mock import patch
import json,unittest,subprocess
from lxml import etree as ET
from core.package import Package,DemoError,q,NS,sha256,write_new
from core.engine import _ensure
from core.layout import suggest_figure_pairs,apply_figure_layout
from core.preview import configuration,valid_artifacts,render_preview,_environment
from web.session import WebSession
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'work/phase5/final/fixed-B-current.docx';CFG=ROOT/'work/phase5/final/template-B-current.json'
M=json.loads(B.with_suffix('.types.json').read_text());CORRECT=ROOT/'samples/extended-correct.docx'

class PreviewAcceptance(unittest.TestCase):
    def setUp(self):self.tmp=TemporaryDirectory();self.dir=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def edit(self,fn):
        pkg=Package(B);fn(pkg);p=self.dir/('test-'+str(len(list(self.dir.glob('*.docx'))))+'.docx');write_new(p,pkg.bytes(True))
        m=deepcopy(M);m['input_sha256']=sha256(p.read_bytes());return p,m
    def fix(self,p=B,m=M,keys=('L01:15:16',)):
        return apply_figure_layout(p,self.dir/('out-'+str(len(list(self.dir.glob('*.docx'))))+'.docx'),custom_rules_path=CFG,classification_manifest=m,confirmed_keys=keys)
    def model(self):
        s=WebSession(self.dir);s.set_mode('extended');self.assertTrue(s.load(B.read_bytes(),'B.docx'))
        s.set_types(M['paragraph_types']);s.confirm();self.assertTrue(s.check());return s
    def fake(self,path,root,context):
        root.mkdir(parents=True,exist_ok=True);img=root/'fake.png';img.write_bytes(b'mock page, no visual assertion')
        _,cfg=configuration()
        return {'document_sha256':sha256(Path(path).read_bytes()),'render_config_sha256':cfg,'pages':[str(img)],'context':context,
                'preview_range':[1,1],'artifact_sha256':{str(img):sha256(img.read_bytes())}}
    def test_only_immediate_confirmed_caption_suggested(self):
        s=suggest_figure_pairs(B,M);self.assertEqual(len(s['pairs']),1);self.assertEqual(s['pairs'][0]['status'],'available')
        m=deepcopy(M);m['paragraph_types']['16']='other';self.assertEqual(suggest_figure_pairs(B,m)['pairs'][0]['status'],'review')
    def test_unconfirmed_and_hash_mismatch_cannot_modify(self):
        for field,val in [('confirmed',False),('input_sha256','wrong')]:
            m=deepcopy(M);m[field]=val
            with self.assertRaises(DemoError):self.fix(m=m)
        self.assertEqual(list(self.dir.glob('out-*.docx')),[])
    def test_explicit_nonempty_safe_keys_required(self):
        for keys in [[],['L01:1:16'],['L01:15:16','L01:15:16'],[True]]:
            with self.assertRaises(DemoError):self.fix(keys=keys)
    def test_no_remote_caption_across_table(self):
        def fn(pkg):pkg.paragraphs[14].addnext(ET.Element(q('tbl')))
        p,m=self.edit(fn);self.assertEqual(suggest_figure_pairs(p,m)['pairs'][0]['status'],'review')
    def test_floating_image_review_never_forced(self):
        def fn(pkg):pkg.paragraphs[14].find('.//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}inline').tag='{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}anchor'
        p,m=self.edit(fn)
        with self.assertRaises(DemoError):self.fix(p,m)
    def test_multiple_images_review(self):
        def fn(pkg):pkg.paragraphs[14].append(deepcopy(pkg.paragraphs[14].find(q('r'))))
        p,m=self.edit(fn);self.assertEqual(suggest_figure_pairs(p,m)['pairs'][0]['status'],'review')
    def test_caption_field_protected(self):
        def fn(pkg):_ensure(pkg.paragraphs[15],'r').append(ET.Element(q('fldChar')))
        p,m=self.edit(fn)
        with self.assertRaises(DemoError):self.fix(p,m)
    def test_forced_break_and_chain_conflicts_review(self):
        for tag in ('pageBreakBefore','keepNext'):
            p,m=self.edit(lambda pkg:_ensure(_ensure(pkg.paragraphs[15],'pPr'),tag).set(q('val'),'1'))
            with self.assertRaises(DemoError):self.fix(p,m)
    def test_properties_saved_and_rules_independently_rechecked(self):
        r=self.fix();p=Package(r['output'])
        self.assertEqual(p.paragraphs[14].find('w:pPr/w:keepNext',NS).get(q('val')),'1')
        self.assertEqual(p.paragraphs[15].find('w:pPr/w:keepLines',NS).get(q('val')),'1')
        self.assertEqual(r['before']['summary'],r['after']['summary']);self.assertEqual(r['after']['summary']['problem_count'],0)
        self.assertEqual(r['layout']['visual_status'],'not_reviewed');self.assertTrue(all(r['preservation'][k] for k in ('original_sha256_unchanged','document_except_selected_format_attributes_equal','other_zip_member_bytes_equal')))
    def test_unselected_content_size_sections_and_bytes_preserved(self):
        old=Package(B);r=self.fix();new=Package(r['output'])
        for i in range(len(old.paragraphs)):
            if i not in (14,15):self.assertEqual(ET.tostring(old.paragraphs[i]),ET.tostring(new.paragraphs[i]))
        self.assertEqual(old.parts['word/media/image1.png'],new.parts['word/media/image1.png'])
        self.assertEqual(old.root.xpath('//w:t/text()',namespaces=NS),new.root.xpath('//w:t/text()',namespaces=NS))
        self.assertEqual([ET.tostring(e) for e in old.sections],[ET.tostring(e) for e in new.sections])
        self.assertEqual(ET.tostring(old.paragraphs[14].find(q('r'))),ET.tostring(new.paragraphs[14].find(q('r'))))
        self.assertEqual(sha256(B.read_bytes()),M['input_sha256'])
    def test_oversized_group_not_claimed_solved(self):
        def fn(pkg):pkg.paragraphs[14].find('.//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}extent').set('cy','20000000')
        p,m=self.edit(fn);r=self.fix(p,m)
        self.assertEqual(r['layout']['visual_status'],'not_reviewed');self.assertIn('整体过高',r['layout']['limitation'])
    def test_refuse_original_existing_and_idempotent_new_copy(self):
        with self.assertRaises(DemoError):apply_figure_layout(B,B,classification_manifest=M,confirmed_keys=['L01:15:16'])
        r=self.fix();p=Path(r['output']);data=p.read_bytes()
        with self.assertRaises(DemoError):apply_figure_layout(B,p,classification_manifest=M,confirmed_keys=['L01:15:16'])
        r2=self.fix(p,r['output_classification_manifest']);self.assertEqual(r2['changes'],[]);self.assertEqual(Path(r2['output']).read_bytes(),data)
    def test_preview_cache_no_duplicate_and_tampering_rejected(self):
        s=self.model();calls=[]
        def fake(*a,**kw):calls.append(1);return self.fake(*a,**kw)
        self.assertTrue(s.generate_preview('input',fake));self.assertTrue(s.generate_preview('input',fake));self.assertEqual(len(calls),1)
        Path(s.get_preview('input')['pages'][0]).write_bytes(b'changed');self.assertIsNone(s.get_preview('input'))
    def test_preview_input_switch_and_sessions_isolate(self):
        s=self.model();s.generate_preview('input',self.fake);other=self.model();self.assertIsNone(other.get_preview('input'))
        s.load(CORRECT.read_bytes(),'new.docx');s.set_types(json.loads(CORRECT.with_suffix('.types.json').read_text())['paragraph_types']);s.confirm();s.check();self.assertIsNone(s.get_preview('input'))
        self.assertEqual(s.preview_cache,{})
    def test_scope_mode_rule_binding_invalidates_preview(self):
        s=self.model();s.generate_preview('input',self.fake);t=deepcopy(s.paragraph_types);t['8']='other';s.set_types(t);s.confirm();s.check();self.assertIsNone(s.get_preview('input'))
        s.set_mode('basic');self.assertEqual(s.preview_targets(),{})
    def test_failed_render_does_not_damage_fixed_template(self):
        s=self.model();report=deepcopy(s.report)
        def fail(*a,**kw):raise DemoError('本地预览超时')
        self.assertFalse(s.generate_preview('input',fail));self.assertEqual(s.report,report);self.assertIsNotNone(s.confirmed);self.assertIn('超时',s.preview_error)
    def test_bad_renderer_binding_never_displayed(self):
        s=self.model()
        def fake(*a,**kw):m=self.fake(*a,**kw);m['document_sha256']='wrong';return m
        self.assertFalse(s.generate_preview('input',fake));self.assertIsNone(s.get_preview('input'))
    def test_layout_round_duplicate_and_each_input_preserved(self):
        s=self.model();original=s.input_path.read_bytes();self.assertTrue(s.generate_layout('input',['L01:15:16']));first=Path(s.result['output']);data=first.read_bytes()
        self.assertTrue(s.generate_layout('input',['L01:15:16']));self.assertEqual(s.generation_count,1)
        self.assertEqual(s.downloads()['round-input.docx'],original);self.assertEqual(s.downloads()['fixed.docx'],data)
        self.assertTrue(s.generate_layout('round-1',['L01:15:16']));self.assertEqual(s.generation_count,2)
        self.assertEqual(first.read_bytes(),data);self.assertEqual(s.original_path.read_bytes(),original);self.assertEqual(s.result['round']['input_round'],1)
    def test_layout_failure_clears_success_and_does_not_overwrite(self):
        s=self.model();s.generate_layout('input',['L01:15:16']);p=Path(s.result['output']);data=p.read_bytes()
        self.assertFalse(s.generate_layout('input',['forged']));self.assertIsNone(s.result);self.assertEqual(p.read_bytes(),data)
    def test_visual_review_explicit_human_not_page_detection(self):
        s=self.model()
        with self.assertRaises(DemoError):s.record_visual_review('input','looked','')
        s.generate_preview('input',self.fake);s.record_visual_review('input','issues','人工发现图题跨页')
        r=next(iter(s.visual_reviews.values()));self.assertEqual(r['method'],'human');self.assertTrue(r['not_automatic_validation'])
    def test_renderer_environment_does_not_forward_key(self):
        with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'must-not-be-forwarded'}):
            self.assertNotIn('DEEPSEEK_API_KEY',_environment(self.dir/'fonts.conf'))
    def test_external_relationship_render_declined_without_mutation(self):
        def fn(pkg):
            from core.package import parse
            rel=parse(pkg.parts['word/_rels/document.xml.rels']);e=ET.SubElement(rel,'{http://schemas.openxmlformats.org/package/2006/relationships}Relationship');e.set('Id','outside');e.set('TargetMode','External');e.set('Target','https://example.com');e.set('Type','hyperlink');pkg.parts['word/_rels/document.xml.rels']=ET.tostring(rel)
        p,_=self.edit(fn);data=p.read_bytes()
        with self.assertRaisesRegex(DemoError,'外部关系'):render_preview(p,self.dir/'render')
        self.assertEqual(p.read_bytes(),data)
    def test_timeout_terminates_only_own_renderer_and_keeps_input(self):
        from unittest.mock import MagicMock
        proc=MagicMock();proc.pid=987654;proc.poll.return_value=None
        proc.wait.side_effect=[subprocess.TimeoutExpired('mock renderer',45),0]
        data=B.read_bytes();runtime_config=configuration()
        with patch('core.preview.configuration',return_value=runtime_config),patch('core.preview._fonts',return_value=({},[],[])),patch('core.preview.subprocess.Popen',return_value=proc),patch('core.preview.os.killpg') as kill:
            with self.assertRaisesRegex(DemoError,'超时'):render_preview(B,self.dir/'timeout')
            kill.assert_called_once();self.assertEqual(kill.call_args.args[0],987654)
        self.assertEqual(B.read_bytes(),data)
    def test_font_missing_reports_specific_substitution_without_docx_change(self):
        from core.preview import _fonts,CONFIG
        job=self.dir/'fonts';job.mkdir();data=B.read_bytes()
        def run(cmd,**kw):return subprocess.CompletedProcess(cmd,0,'Songti SC\nHeiti SC\n' if 'fc-list' in cmd[0] else 'Songti SC','')
        with patch('core.preview.subprocess.run',side_effect=run):
            env,fonts,notes=_fonts(Package(B),job,CONFIG)
        self.assertTrue(any('宋体' in n and 'Songti SC' in n for n in notes));self.assertEqual(B.read_bytes(),data)
        self.assertNotIn('DEEPSEEK_API_KEY',env)
    def test_font_probe_failure_is_explicit_optional_failure(self):
        from core.preview import _fonts,CONFIG
        job=self.dir/'fonts';job.mkdir()
        with patch('core.preview.subprocess.run',side_effect=FileNotFoundError):
            with self.assertRaisesRegex(DemoError,'字体可用性'):_fonts(Package(B),job,CONFIG)
    def test_renderer_configuration_change_cache_not_reused(self):
        s=self.model();s.generate_preview('input',self.fake)
        with patch('web.preview_session.configuration',return_value=({},'newconfig')):self.assertIsNone(s.get_preview('input'))
    def test_mutated_original_not_shown_after_next_round(self):
        s=self.model();s.generate_layout('input',['L01:15:16']);s.next_round();s.original_path.write_bytes(b'corrupted')
        with self.assertRaisesRegex(DemoError,'原稿副本'):s.preview_targets()
    def test_unselected_second_figure_pair_untouched(self):
        def fn(pkg):
            body=pkg.root.find(q('body'));body.insert(len(body)-1,deepcopy(pkg.paragraphs[14]));body.insert(len(body)-1,deepcopy(pkg.paragraphs[15]))
        p,m=self.edit(fn);m['paragraph_types'].update({'25':'other','26':'figure_caption'})
        self.assertEqual(len(suggest_figure_pairs(p,m)['pairs']),2)
        r=self.fix(p,m);before=Package(p);after=Package(r['output'])
        for n in (24,25):self.assertEqual(ET.tostring(before.paragraphs[n]),ET.tostring(after.paragraphs[n]))
    def test_superscript_caption_and_image_frame_skipped(self):
        for fn in [lambda pkg:_ensure(_ensure(pkg.paragraphs[15].find(q('r')),'rPr'),'vertAlign').set(q('val'),'superscript'),
                   lambda pkg:_ensure(_ensure(pkg.paragraphs[14],'pPr'),'framePr')]:
            p,m=self.edit(fn)
            with self.assertRaises(DemoError):self.fix(p,m)
    def test_worker_rasterizes_only_first_ten_of_twelve_pages(self):
        import runpy,sys,types,importlib.util
        job=self.dir/'worker';job.mkdir();(job/'request.json').write_text(json.dumps({'renderer_script':'mock','max_pages':10,'dpi':130}))
        (job/'source.docx').write_bytes(b'mock source')
        calls=[]
        class Image:
            def save(self,path):Path(path).write_bytes(b'mock png')
        def raster(path,**kw):calls.append(kw);return [Image() for _ in range(kw['last_page'])]
        fake=types.SimpleNamespace(pdfinfo_from_path=lambda p:{'Pages':12},convert_from_path=raster)
        spec=importlib.util.spec_from_loader('mockrenderer',loader=None)
        loader=types.SimpleNamespace(create_module=lambda spec:None,exec_module=lambda mod:setattr(mod,'convert_to_pdf',lambda *a:(str(job/'source.pdf'),'mock conversion')))
        spec.loader=loader
        with patch.dict(sys.modules,{'pdf2image':fake}),patch('sys.argv',['preview_worker',str(job)]),patch('importlib.util.spec_from_file_location',return_value=spec):
            runpy.run_path(str(ROOT/'core/preview_worker.py'))
        self.assertEqual(calls[0]['first_page'],1);self.assertEqual(calls[0]['last_page'],10)
        self.assertEqual(len(list(job.glob('page-*.png'))),10);self.assertEqual(json.loads((job/'worker-result.json').read_text())['page_count'],12)
    def test_missing_image_media_relationship_not_available(self):
        def fn(pkg):
            from core.package import parse
            rel=parse(pkg.parts['word/_rels/document.xml.rels'])
            for e in rel:
                if e.get('Type','').endswith('/image'):e.set('Target','media/missing.png')
            pkg.parts['word/_rels/document.xml.rels']=ET.tostring(rel)
        p,m=self.edit(fn)
        self.assertEqual(suggest_figure_pairs(p,m)['pairs'][0]['status'],'review')
        with self.assertRaises(DemoError):self.fix(p,m)
    def test_applied_template_change_same_document_invalidates_preview(self):
        s=self.model();s.generate_preview('input',self.fake);old=s.rules_hash;doc=s.inventory['input_sha256']
        self.assertTrue(s.import_template(CFG.read_bytes()));self.assertTrue(s.apply_template());self.assertIsNone(s.confirmed)
        s.confirm();self.assertTrue(s.check());self.assertNotEqual(s.rules_hash,old);self.assertEqual(s.inventory['input_sha256'],doc)
        self.assertIsNone(s.get_preview('input'))
    def test_inherited_floating_paragraph_frame_is_review(self):
        def fn(pkg):
            style=pkg.styles.find("w:style[@w:styleId='Normal']",NS)
            _ensure(_ensure(style,'pPr'),'framePr').set(q('w'),'1200')
            pkg.parts['word/styles.xml']=ET.tostring(pkg.styles)
        p,m=self.edit(fn);self.assertEqual(suggest_figure_pairs(p,m)['pairs'][0]['status'],'review')
        with self.assertRaises(DemoError):self.fix(p,m)

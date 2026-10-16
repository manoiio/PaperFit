from tests.ui_navigation import show, click as ui_click
"""扩展分类、标题/题注及多轮修正的实际行为验收；不调用付费API。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest.mock import patch
import hashlib,json,unittest
from lxml import etree as ET
from streamlit.testing.v1 import AppTest
from core import check_document,fix_document,suggest_paragraph_types,effective_rules
from core.package import Package,DemoError,q,NS,write_new
from core.engine import _ensure,DEFAULT_RULES
from core.extended import formatting_snapshot,snapshots_equal
from core.classification import title_number
from web.session import WebSession
from web.presentation import fmt

ROOT=Path(__file__).resolve().parents[1];ERROR=ROOT/'samples/extended-errors.docx';CORRECT=ROOT/'samples/extended-correct.docx'
MANIFEST=json.loads(ERROR.with_suffix('.types.json').read_text());CONTROL=json.loads(CORRECT.with_suffix('.types.json').read_text())
SPEC=ROOT/'tests/fixtures/history/phase3/final/real-api-record.json'

def hashfile(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class ExtendedAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.dir=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def check(self,path=ERROR,manifest=MANIFEST,**args):
        return check_document(path,mode='extended',classification_manifest=manifest,**args)
    def fix(self,ids=None,keys=None,path=ERROR,manifest=MANIFEST,**args):
        return fix_document(path,self.dir/(str(len(list(self.dir.glob('*.docx'))))+'.docx'),None,
                            selected_rules=ids or [],selected_keys=keys or [],mode='extended',classification_manifest=manifest,**args)
    def modified(self,edit):
        pkg=Package(ERROR);edit(pkg);p=self.dir/'modified.docx';write_new(p,pkg.bytes(True))
        m=deepcopy(MANIFEST);m['input_sha256']=hashfile(p)
        return p,m
    def session(self,path=ERROR):
        m=WebSession(self.dir);m.set_mode('extended');self.assertTrue(m.load(path.read_bytes(),path.name));return m

    def test_normal_suggestions_body_headings_captions_no_position_hardcoding(self):
        rows={x['index']:x for x in suggest_paragraph_types(ERROR)['paragraphs']}
        for n,t in {7:'heading1',9:'heading2',11:'heading3',13:'heading2',8:'body',16:'figure_caption',17:'table_caption'}.items():
            self.assertEqual(rows[n]['suggested_type'],t)
        self.assertTrue(rows[13]['ambiguous'])
        # Same text/style after inserting an unrelated top-level paragraph gets a new number.
        def edit(pkg):pkg.root.find(q('body')).insert(0,ET.Element(q('p')))
        path,_=self.modified(edit)
        shifted={x['index']:x for x in suggest_paragraph_types(path)['paragraphs']}
        self.assertEqual(shifted[14]['suggested_type'],'heading2')
        self.assertEqual(shifted[17]['suggested_type'],'figure_caption')

    def test_numeric_sentences_toc_abstract_references_and_tables_not_upgraded(self):
        s=suggest_paragraph_types(ERROR);rows={x['index']:x for x in s['paragraphs']}
        self.assertEqual(len(rows),24)
        self.assertEqual(rows[10]['suggested_type'],'body');self.assertEqual(rows[12]['suggested_type'],'body')
        for n in [1,2,4,6,15,22,23]:self.assertEqual(rows[n]['suggested_type'],'other')
        for text in ['1.5倍行距','1.5 倍行距','2026年实验结果','2026 年实验结果','1.1 这一段是普通句子。']:
            self.assertIsNone(title_number(text),text)

    def test_toc_entry_with_valid_heading_style_stays_excluded(self):
        def edit(pkg):
            p=pkg.paragraphs[5]
            p.xpath('.//w:t',namespaces=NS)[0].text='1.1 段落类型核对 3'
            _ensure(_ensure(p,'pPr'),'pStyle').set(q('val'),'Heading2')
        path,_=self.modified(edit)
        row=suggest_paragraph_types(path)['paragraphs'][5]
        self.assertEqual(row['suggested_type'],'other')

    def test_heading_style_conflict_not_unconditionally_trusted(self):
        def edit(pkg):
            p=pkg.paragraphs[8];_ensure(_ensure(p,'pPr'),'outlineLvl').set(q('val'),'0')
        path,_=self.modified(edit)
        row=suggest_paragraph_types(path)['paragraphs'][8]
        self.assertEqual(row['suggested_type'],'pending');self.assertTrue(row['ambiguous'])

    def test_unit_phrase_with_heading_style_and_numbered_reference_marker(self):
        def edit(pkg):
            p=pkg.paragraphs[8]
            for t in p.xpath('.//w:t',namespaces=NS):t.text=''
            p.xpath('.//w:t',namespaces=NS)[0].text='1.5倍行距'
            pkg.paragraphs[20].xpath('.//w:t',namespaces=NS)[0].text='第三章 参考文献'
        path,_=self.modified(edit)
        rows=suggest_paragraph_types(path)['paragraphs']
        self.assertEqual(rows[8]['suggested_type'],'pending');self.assertTrue(rows[8]['ambiguous'])
        self.assertEqual(rows[20]['suggested_type'],'other');self.assertEqual(rows[22]['suggested_type'],'other')

    def test_missing_builtin_heading_style_is_review_not_synthesized(self):
        def edit(pkg):
            style=pkg.styles.find("w:style[@w:styleId='Heading2']",NS)
            pkg.styles.remove(style);pkg.parts['word/styles.xml']=ET.tostring(pkg.styles)
        path,m=self.modified(edit)
        f=next(f for f in self.check(path,m)['findings'] if f['key']=='R11:paragraph=13')
        self.assertEqual(f['status'],'review');self.assertFalse(f['fixable']);self.assertIn('缺少',f['detail'])

    def test_unconfirmed_hash_missing_type_and_pending_protection(self):
        for edit in ['unconfirmed','hash','missing','unknown']:
            m=deepcopy(MANIFEST)
            if edit=='unconfirmed':m['confirmed']=False
            if edit=='hash':m['input_sha256']='bad'
            if edit=='missing':del m['paragraph_types']['1']
            if edit=='unknown':m['paragraph_types']['7']='heading4'
            with self.subTest(edit=edit),self.assertRaises(DemoError):self.check(manifest=m)
            with self.assertRaises(DemoError):self.fix(['R08'],manifest=m)
        m=deepcopy(MANIFEST);m['paragraph_types']['7']='pending'
        r=self.check(manifest=m)
        self.assertFalse(any(f['locator'].get('paragraph')==7 for f in r['findings']))
        self.assertTrue(any(n['locator']=={'paragraph':7} and '待确认' in n['detail'] for n in r['coverage_notes']))

    def test_independent_error_list_all_R08_R12_have_pass_and_problem(self):
        expected=json.loads((ROOT/'samples/extended-expected-errors.json').read_text())
        r=self.check();problems=[f for f in r['findings'] if f['status']=='problem']
        self.assertEqual(len(problems),expected['expected_problem_count'])
        actual={f['key']:f['expected'] for f in problems}
        wanted={x['rule']+':'+':'.join(f'{k}={v}' for k,v in x.items() if k in ('paragraph','run','property')):x['expected'] for x in expected['items']}
        self.assertEqual(actual,wanted)
        control=self.check(CORRECT,CONTROL)
        self.assertEqual(control['summary']['problem_count'],0);self.assertEqual(control['summary']['review_count'],0)
        for rid in ['R08','R09','R10','R11','R12']:
            self.assertTrue(any(f['rule_id']==rid and f['status']=='pass' for f in control['findings']))
            self.assertTrue(any(f['rule_id']==rid for f in problems))

    def test_title_later_run_and_character_style_inheritance(self):
        r=self.check();by={f['key']:f for f in r['findings']}
        self.assertEqual(by['R09:paragraph=9:run=2:property=size']['actual'],{'pt':14})
        self.assertEqual(by['R10:paragraph=11:run=2:property=size']['actual'],{'pt':12})
        self.assertEqual(by['R09:paragraph=9:run=1:property=size']['status'],'pass')

    def test_all_selected_extension_rechecks_and_objects_preserved(self):
        result=self.fix(['R08','R09','R10','R11','R12'])
        self.assertEqual(len(result['changes']),9);self.assertEqual(result['after']['summary']['problem_count'],0)
        self.assertEqual(result['after']['summary']['review_count'],0)
        independent=self.check(Path(result['output']),result['output_classification_manifest'])
        self.assertEqual(independent['summary']['problem_count'],0)
        a,b=Package(ERROR),Package(result['output'])
        for part,data in a.parts.items():
            if part!='word/document.xml':self.assertEqual(data,b.parts[part],part)
        for xpath in ('//w:t/text()','//w:drawing','//w:tbl','//w:fldChar','//w:instrText','//w:sectPr'):
            def data(pkg):return [ET.tostring(e,method='c14n') if hasattr(e,'tag') else str(e) for e in pkg.root.xpath(xpath,namespaces=NS)]
            self.assertEqual(data(a),data(b),xpath)
        self.assertEqual(hashfile(ERROR),MANIFEST['input_sha256'])
        self.assertEqual(result['output_classification_manifest']['input_sha256'],hashfile(result['output']))

    def test_R11_alone_preserves_effective_formats_and_shared_styles(self):
        result=self.fix(['R11']);a,b=Package(ERROR),Package(result['output'])
        self.assertEqual(len(result['changes']),1)
        self.assertTrue(snapshots_equal(formatting_snapshot(a,a.paragraphs[12]),formatting_snapshot(b,b.paragraphs[12])))
        self.assertEqual(a.parts['word/styles.xml'],b.parts['word/styles.xml'])
        self.assertEqual(result['after']['summary']['problem_count'],8)
        self.assertTrue(result['changes'][0]['preserved_format_patch'])
        self.assertIn('有效格式',result['changes'][0]['dependency_note'])

    def test_R11_preserves_higher_layer_theme_without_promoting_lower_literal(self):
        from core.formats import Resolver
        def edit(pkg):
            run=pkg.paragraphs[12].find(q('r'))
            _ensure(_ensure(run,'rPr'),'rFonts').set(q('eastAsiaTheme'),'majorEastAsia')
        path,m=self.modified(edit)
        before=Package(path)
        value=Resolver(before).font(Resolver(before).layers(before.paragraphs[12],before.paragraphs[12].find(q('r'))),'eastAsia')
        self.assertIsInstance(value,dict)
        result=self.fix(['R11'],path=path,manifest=m)
        after=Package(result['output'])
        actual=Resolver(after).font(Resolver(after).layers(after.paragraphs[12],after.paragraphs[12].find(q('r'))),'eastAsia')
        self.assertEqual(actual,value)
        self.assertEqual(next(f for f in result['after']['findings'] if f['key']=='R09:paragraph=13:run=1:property=font_eastAsia')['status'],'review')

    def test_unpreservable_heading_dependency_or_missing_builtin_review(self):
        def edit(pkg):
            style=pkg.styles.find("w:style[@w:styleId='Heading2']",NS)
            _ensure(_ensure(style,'pPr'),'tabs').append(ET.Element(q('tab'),{q('val'):'right',q('pos'):'1000'}))
            pkg.parts['word/styles.xml']=ET.tostring(pkg.styles)
        path,m=self.modified(edit);r=self.check(path,m)
        f=next(f for f in r['findings'] if f['key']=='R11:paragraph=13')
        self.assertEqual(f['status'],'review');self.assertFalse(f['fixable']);self.assertIn('tabs',f['detail'])
        out=self.fix(keys=[f['key']],path=path,manifest=m)
        self.assertEqual(out['changes'],[]);self.assertEqual(Path(out['output']).read_bytes(),path.read_bytes())

    def test_caption_only_font_size_not_spacing_indent_or_number(self):
        result=self.fix(['R12']);a,b=Package(ERROR),Package(result['output'])
        for n in [16,17]:
            self.assertEqual(ET.tostring(a.paragraphs[n-1].find(q('pPr'))),ET.tostring(b.paragraphs[n-1].find(q('pPr'))))
            self.assertEqual(a.paragraphs[n-1].xpath('.//w:t/text()',namespaces=NS),b.paragraphs[n-1].xpath('.//w:t/text()',namespaces=NS))
        self.assertEqual(result['after']['summary']['problem_count'],6)

    def test_no_caption_is_not_applicable_and_counts_not_invented(self):
        m=deepcopy(CONTROL)
        for k,t in m['paragraph_types'].items():
            if t.endswith('_caption'):m['paragraph_types'][k]='other'
        r=self.check(CORRECT,m)
        fs=[f for f in r['findings'] if f['rule_id']=='R12']
        self.assertEqual([f['status'] for f in fs],['not_applicable'])
        self.assertEqual(r['summary']['rule_count'],12);self.assertEqual(r['summary']['applicable_rule_count'],11)
        self.assertEqual(r['summary']['problem_count'],0)

    def test_special_structures_block_heading_fix_and_are_not_rewritten(self):
        m=deepcopy(MANIFEST);m['paragraph_types']['24']='heading2'
        r=self.check(manifest=m);fs=[f for f in r['findings'] if f['locator'].get('paragraph')==24]
        self.assertTrue(all(f['status']=='review' and not f['fixable'] for f in fs))
        result=self.fix(['R08','R09','R10','R11','R12'],manifest=m)
        self.assertEqual(ET.tostring(Package(ERROR).paragraphs[23]),ET.tostring(Package(result['output']).paragraphs[23]))

    def test_extended_modes_keep_old_fixed_semantics_and_sources(self):
        r=check_document(ROOT/'samples/errors.docx',ROOT/'samples/errors.body.json')
        self.assertEqual(r['summary']['rule_count'],7);self.assertEqual(r['summary']['problem_count'],11)
        self.assertEqual(set(effective_rules()['rules']),{f'R{i:02}' for i in range(1,8)})
        self.assertEqual(self.check()['rules']['mode'],'extended')
        self.assertEqual(next(f for f in self.check()['findings'] if f['rule_id']=='R11')['source']['label'],'产品结构规则')

    def test_custom_body_coexists_fixed_titles_and_exact_new_indent_cause(self):
        config=ROOT/'tests/fixtures/history/phase3/final/user-confirmed-rules.json'
        r=self.check(CORRECT,CONTROL,custom_rules_path=config)
        self.assertTrue(any(x['locator']['paragraph']==14 for x in r['modification_dependencies']))
        result=self.fix(['R05','R06'],path=CORRECT,manifest=CONTROL,custom_rules_path=config)
        self.assertEqual(result['after']['summary']['problem_count'],1)
        self.assertEqual(result['problem_delta']['new_keys'],['R07:paragraph=14'])
        self.assertIn('14pt后，24pt缩进不再等效两字符',result['problem_delta']['new_problem_causes'][0]['detail'])
        title=next(f for f in result['after']['findings'] if f['rule_id']=='R09' and f['locator'].get('property')=='size')
        self.assertEqual(title['expected'],{'pt':15});self.assertEqual(title['source']['physical_page'],18)
        self.assertEqual(next(f for f in r['findings'] if f['rule_id']=='R05')['source']['label'],'用户确认值')

    def test_partial_size_change_problem_to_review_is_not_resolved(self):
        def edit(pkg):
            p=pkg.paragraphs[13];r=p.find(q('r'));text=r.find(q('t'));raw=text.text
            second=deepcopy(r);text.text=raw[:20];second.find(q('t')).text=raw[20:];p.append(second)
            _ensure(_ensure(p,'pPr'),'ind').set(q('firstLine'),'600')
        path,m=self.modified(edit)
        result=self.fix(keys=['R05:paragraph=14:run=1'],path=path,manifest=m,
                        custom_rules_path=ROOT/'tests/fixtures/history/phase3/final/user-confirmed-rules.json')
        key='R07:paragraph=14'
        self.assertEqual(next(f for f in result['before']['findings'] if f['key']==key)['status'],'problem')
        self.assertEqual(next(f for f in result['after']['findings'] if f['key']==key)['status'],'review')
        self.assertNotIn(key,result['problem_delta']['resolved_keys'])
        self.assertIn(key,result['problem_delta']['unresolved_review_keys'])

    def test_two_rounds_current_hash_and_original_first_round_unchanged(self):
        m=self.session(CORRECT);self.assertTrue(m.load_historical_spec(SPEC));self.assertTrue(m.apply_draft())
        m.confirm_classification();self.assertTrue(m.check(),m.error)
        m.set_selection([f['key'] for f in m.eligible()]);self.assertTrue(m.generate(),m.error)
        first=m.result;firsthash=hashfile(first['output']);original=hashfile(m.original_path)
        self.assertEqual(first['after']['summary']['problem_count'],1)
        self.assertTrue(m.next_round(),m.error)
        self.assertEqual(m.current_round,1);self.assertEqual(m.input_path,Path(first['output']))
        self.assertEqual(m.classification_confirmed['input_sha256'],firsthash)
        self.assertEqual([f['rule_id'] for f in m.eligible()],['R07'])
        m.set_selection([f['key'] for f in m.eligible()]);self.assertTrue(m.generate(),m.error)
        self.assertEqual(m.result['round']['input_round'],1);self.assertEqual(m.result['round']['number'],2)
        self.assertEqual(m.result['after']['summary']['problem_count'],0);self.assertEqual(m.result['after']['summary']['review_count'],0)
        self.assertEqual(hashfile(first['output']),firsthash);self.assertEqual(hashfile(m.original_path),original)
        self.assertEqual(m.downloads()['original.docx'],CORRECT.read_bytes());self.assertEqual(len(m.history_downloads()),2)
        self.assertNotEqual(m.result['output'],first['output'])

    def test_classification_change_and_mode_switch_invalidate_download_bindings(self):
        m=self.session();m.confirm_classification();self.assertTrue(m.check())
        m.set_selection([f['key'] for f in m.eligible()]);self.assertTrue(m.generate(),m.error)
        old=m.result['output'];items=m.paragraph_types.copy();items['13']='other';m.set_types(items)
        self.assertIsNone(m.report);self.assertEqual(m.downloads(),{});self.assertEqual(m.history_downloads(),[])
        self.assertFalse(m.generate());self.assertTrue(Path(old).exists())
        m.confirm_classification();m.check();m.set_mode('basic')
        self.assertIsNone(m.confirmed);self.assertEqual(m.downloads(),{});self.assertEqual(m.history_downloads(),[])

    def test_input_change_and_two_sessions_isolate_classification_and_rounds(self):
        a=self.session();b=self.session(CORRECT)
        a.confirm_classification();a.check();a.set_selection([f['key'] for f in a.eligible()]);a.generate()
        b.set_types({**b.paragraph_types,'13':'other'});b.confirm_classification();b.check()
        self.assertEqual(a.paragraph_types['13'],'heading2');self.assertEqual(b.paragraph_types['13'],'other')
        self.assertEqual(b.history,[]);self.assertNotEqual(a.task_dir,b.task_dir)
        old=a.task_dir;a.load(CORRECT.read_bytes(),'new.docx');self.assertIsNone(a.classification_confirmed)
        self.assertEqual(a.history,[]);self.assertFalse(old.exists());self.assertTrue(b.input_path.exists())

    def test_output_overwrite_and_duplicate_round_protected(self):
        m=self.session();m.confirm_classification();m.check();m.set_selection([f['key'] for f in m.eligible()]);m.generate()
        output=m.result['output'];count=len(m.history)
        with patch('web.session.fix_document',side_effect=AssertionError('no reexecution')):
            self.assertTrue(m.generate());m.downloads()
        self.assertEqual(len(m.history),count)
        with self.assertRaises(DemoError):fix_document(ERROR,output,None,selected_rules=['R11'],mode='extended',classification_manifest=MANIFEST)

    def test_historical_real_record_explicit_no_new_API_and_sources(self):
        m=self.session(CORRECT)
        with patch('ai.short_spec.http_post',side_effect=AssertionError('no new API')):self.assertTrue(m.load_historical_spec(SPEC),m.ai_error)
        self.assertTrue(m.ai_receipt['historical_reuse']);self.assertEqual(m.ai_receipt['requests_this_action'],0)
        self.assertEqual(m.proposed_rules()['rules']['R05']['source']['kind'],'ai_extracted')
        self.assertEqual(m.proposed_rules()['rules']['R06']['expected'],2)

class ExtendedUIAcceptance(unittest.TestCase):
    def setUp(self):
        self.at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
    def tearDown(self):self.at.session_state['workflow'].reset()
    def click(self,label):
        ui_click(self.at,label);self.assertFalse(list(self.at.exception))
    def extended(self):
        show(self.at,1);next(x for x in self.at.radio if x.label=='检查模式').set_value('正文及标题题注检查').run()
        self.click('使用扩展错误样本');show(self.at,2,'paragraph')
    def test_confirm_adjust_and_real_extended_fix_controls(self):
        self.extended();m=self.at.session_state['workflow']
        self.assertTrue(next(b for b in self.at.button if b.label=='开始检查').disabled)
        self.click('确认分类并应用范围');self.click('开始检查')
        self.assertEqual(m.report['summary']['problem_count'],9)
        self.click('选择全部可修正问题');self.click('生成修正版')
        self.assertEqual(m.result['after']['summary']['problem_count'],0)
        show(self.at,2,'paragraph');next(s for s in self.at.selectbox if s.label=='调整段落编号').set_value(13).run()
        next(s for s in self.at.selectbox if s.label=='调整为').set_value('其他').run();self.click('应用分类调整')
        self.assertIsNone(m.result);self.assertIsNone(m.report);self.assertEqual(m.downloads(),{})
    def test_historical_AI_custom_extension_second_round_UI(self):
        self.extended();self.click('使用扩展正确对照');self.click('沿用已记录的真实解析B')
        m=self.at.session_state['workflow'];self.assertTrue(any('历史真实DeepSeek' in x.value for x in self.at.caption))
        self.click('确认并应用');self.click('确认分类并应用范围');self.click('开始检查')
        self.click('选择全部可修正问题');self.click('生成修正版')
        self.assertEqual(m.result['problem_delta']['new_keys'],['R07:paragraph=14'])
        show(self.at,4);self.assertTrue(any('可能影响首行缩进' in x.value for x in self.at.warning))
        self.click('以本轮修正版开始下一轮');self.assertEqual(m.current_round,1)
        self.click('选择全部可修正问题');self.click('生成修正版')
        self.assertEqual(m.result['after']['summary']['problem_count'],0)
        self.assertEqual(m.result['round']['number'],2)

    def test_basic_checkbox_state_rebinds_after_classification_body_change(self):
        self.click('使用正确对照')
        show(self.at,1);next(x for x in self.at.radio if x.label=='检查模式').set_value('正文及标题题注检查').run()
        show(self.at,2,'paragraph');next(s for s in self.at.selectbox if s.label=='调整段落编号').set_value(4).run()
        next(s for s in self.at.selectbox if s.label=='调整为').set_value('其他').run()
        self.click('应用分类调整')
        self.click('确认分类并应用范围')
        show(self.at,1);next(x for x in self.at.radio if x.label=='检查模式').set_value('基础检查').run()
        m=self.at.session_state['workflow'];show(self.at,2,'paragraph')
        checked=next(x for x in self.at.checkbox if x.label.startswith('段 4 ·'))
        self.assertFalse(checked.value);self.assertNotIn(4,m.body)

if __name__=='__main__':unittest.main(verbosity=2)

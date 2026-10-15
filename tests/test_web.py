"""网页的文件/范围/规则绑定、失效、错误、选择过滤及真实Streamlit重运行验收。"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import hashlib
import json
import unittest
from streamlit.testing.v1 import AppTest
from core import check_document
from core.engine import DEFAULT_RULES
from core.package import DemoError
from web.session import WebSession
from web.presentation import fmt, finding_table

ROOT = Path(__file__).resolve().parents[1]
DATA = (ROOT / 'samples/errors.docx').read_bytes()
PRESET = json.loads((ROOT / 'samples/errors.body.json').read_text())
CORRECT = (ROOT / 'samples/correct.docx').read_bytes()
CORRECT_PRESET = json.loads((ROOT / 'samples/correct.body.json').read_text())

class WebStateAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory( prefix='state-test-')
        self.root = Path(self.tmp.name)
        self.model = WebSession(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def checked(self):
        self.assertTrue(self.model.load(DATA, '演示.docx', PRESET))
        self.model.confirm()
        self.assertTrue(self.model.check(), self.model.error)
        return self.model

    def generated(self):
        m = self.checked()
        m.set_selection([f['key'] for f in m.eligible()])
        self.assertTrue(m.generate(), m.error)
        return m

    def test_uploaded_filename_or_identical_bytes_never_prefill_body(self):
        self.assertTrue(self.model.load(DATA, '../../samples/errors.docx'))
        self.assertEqual(self.model.input_path.name, 'input.docx')
        self.assertEqual(self.model.input_path.parent.parent, self.root.resolve())
        self.assertEqual(self.model.body, [])
        self.assertIsNone(self.model.confirmed)
        self.assertFalse(self.model.check())
        self.assertIsNone(self.model.report)

    def test_body_change_invalidates_confirmation_report_selection_and_downloads(self):
        m = self.generated()
        self.assertTrue(m.downloads())
        m.set_body([4])
        self.assertIsNone(m.confirmed)
        self.assertIsNone(m.report)
        self.assertIsNone(m.result)
        self.assertEqual(m.selected, [])
        self.assertEqual(m.downloads(), {})
        self.assertFalse(m.generate())

    def test_file_change_replaces_task_and_cannot_download_previous_result(self):
        m = self.generated()
        old = m.task_dir
        self.assertTrue(m.load(CORRECT, '对照.docx', CORRECT_PRESET))
        self.assertFalse(old.exists())
        self.assertNotEqual(m.task_dir, old)
        self.assertIsNone(m.report)
        self.assertIsNone(m.result)
        self.assertIsNone(m.confirmed)
        self.assertEqual(m.downloads(), {})
        self.assertEqual(m.input_bytes, CORRECT)

    def test_rules_configuration_change_invalidates_every_derived_result(self):
        config = self.root / 'rules.json'
        config.write_bytes(DEFAULT_RULES.read_bytes())
        self.model.rules_path = config
        m = self.generated()
        r = json.loads(config.read_text())
        r['version'] = '1.0.0-web-test'
        config.write_text(json.dumps(r, ensure_ascii=False))
        self.assertTrue(m.sync_rules())
        self.assertIsNone(m.confirmed)
        self.assertIsNone(m.report)
        self.assertIsNone(m.result)
        self.assertEqual(m.downloads(), {})

    def test_selection_filter_and_partial_fix_only_selected_key(self):
        m = self.checked()
        selected = next(f['key'] for f in m.eligible() if f['rule_id']=='R05' and f['locator']=={'paragraph':4,'run':2})
        passed = next(f['key'] for f in m.report['findings'] if f['status']=='pass')
        m.set_selection([selected, passed, 'forged-key', selected])
        self.assertEqual(m.selected, [selected])
        self.assertTrue(m.generate())
        self.assertEqual([c['key'] for c in m.result['changes']], [selected])
        self.assertEqual(m.result['after']['summary']['problem_count'], 10)
        self.assertEqual(check_document(m.result['output'], m.result['output_body_manifest'])['summary']['problem_count'], 10)

    def test_review_and_notes_are_excluded_from_correction_selection(self):
        m = self.checked()
        # Presentation/session selection consumes records, not inferred status.
        m.report['findings'][0]['status'] = 'review'
        m.report['findings'][0]['fixable'] = True  # even malformed flags cannot force a review through.
        key = m.report['findings'][0]['key']
        m.set_selection([key])
        self.assertEqual(m.selected, [])
        self.assertFalse(m.generate())
        self.assertIsNone(m.result)

    def test_failure_clears_success_and_download_binding(self):
        m = self.generated()
        m.set_selection([m.eligible()[0]['key']])
        with patch('web.session.fix_document', side_effect=DemoError('本次测试阻止修正')):
            self.assertFalse(m.generate())
        self.assertIsNone(m.result)
        self.assertIsNone(m.result_signature)
        self.assertEqual(m.downloads(), {})
        self.assertEqual(m.error, '本次测试阻止修正')

    def test_unexpected_engine_error_is_generic_without_traceback_or_private_path(self):
        m = self.checked()
        m.set_selection([m.eligible()[0]['key']])
        with patch('web.session.fix_document', side_effect=RuntimeError('/private/secret/internal traceback')):
            self.assertFalse(m.generate())
        self.assertIsNone(m.result)
        self.assertEqual(m.downloads(), {})
        self.assertNotIn('secret', m.error)
        self.assertNotIn('traceback', m.error)

    def test_duplicate_generation_and_downloads_do_not_execute_correction(self):
        m = self.generated()
        path = m.result['output']
        count = len(list(m.task_dir.glob('fixed-*.docx')))
        with patch('web.session.fix_document', side_effect=AssertionError('must not run')):
            self.assertTrue(m.generate())
            for _ in range(3):
                self.assertEqual(m.downloads()['fixed.docx'], Path(path).read_bytes())
        self.assertEqual(len(list(m.task_dir.glob('fixed-*.docx'))), count)

    def test_downloads_match_current_original_and_independently_recheck_fixed(self):
        m = self.generated()
        files = m.downloads()
        self.assertEqual(files['original.docx'], DATA)
        self.assertEqual(hashlib.sha256(m.input_path.read_bytes()).hexdigest(), PRESET['input_sha256'])
        copied = self.root / 'downloaded.docx'
        copied.write_bytes(files['fixed.docx'])
        manifest = json.loads(files['fixed.body.json'])
        after = check_document(copied, manifest)
        self.assertEqual(after['summary']['problem_count'], 0)
        self.assertEqual(after['summary']['review_count'], 0)
        self.assertIn('已覆盖检查未发现问题'.encode(), files['recheck.md'])

    def test_on_disk_input_or_output_change_revokes_download(self):
        m = self.generated()
        Path(m.result['output']).write_bytes(b'changed')
        with self.assertRaises(DemoError): m.downloads()
        self.assertIsNone(m.result)
        m = self.generated()
        m.input_path.write_bytes(CORRECT)
        with self.assertRaises(DemoError): m.downloads()
        self.assertIsNone(m.confirmed)
        self.assertIsNone(m.report)
        self.assertIsNone(m.result)

    def test_independent_sessions_and_reset_only_owned_task(self):
        m = self.generated()
        other = WebSession(self.root)
        self.assertTrue(other.load(CORRECT, '对照.docx', CORRECT_PRESET))
        self.assertNotEqual(m.task_dir, other.task_dir)
        self.assertIsNone(other.report)
        self.assertEqual(other.downloads(), {})
        own, sibling = m.task_dir, other.task_dir
        unrelated = self.root / 'keep.txt'
        unrelated.write_text('unrelated')
        m.reset()
        self.assertFalse(own.exists())
        self.assertTrue(sibling.exists())
        self.assertEqual(unrelated.read_text(), 'unrelated')
        self.assertEqual(other.input_path.read_bytes(), CORRECT)

    def test_empty_selection_corrupt_or_oversized_upload_cannot_succeed(self):
        m = self.checked()
        self.assertFalse(m.generate())
        self.assertIsNone(m.result)
        self.assertFalse(m.load(b'broken zip', 'broken.docx'))
        self.assertIsNone(m.inventory)
        self.assertIsNone(m.report)
        self.assertIsNone(m.result)
        self.assertTrue(m.error)
        self.assertFalse(m.load(b'0'*(10*1024*1024+1), 'large.docx'))
        self.assertIn('10MB', m.error)

    def test_natural_format_values_and_html_escapes_untrusted_text(self):
        self.assertEqual(fmt({'line_rule':'exact','pt':20,'multiple':None},'R06'),'固定20磅')
        self.assertEqual(fmt({'line_rule':'auto','multiple':1.5,'pt':None},'R06'),'1.5倍')
        self.assertEqual(fmt({'first_line_chars':2,'first_line_pt':None},'R07'),'首行2字符')
        m=self.checked()
        m.inventory['paragraphs'][3]['text']='<script>alert("injected")</script>'
        f=next(f for f in m.eligible() if f['locator'].get('paragraph')==4)
        rendered=finding_table([f],m.inventory)
        self.assertNotIn('<script>',rendered)
        self.assertIn('&lt;script&gt;',rendered)

class StreamlitAcceptance(unittest.TestCase):
    def setUp(self):
        self.at = AppTest.from_file(str(ROOT/'app.py'), default_timeout=20).run()

    def tearDown(self):
        self.at.session_state['workflow'].reset()

    def click(self, label):
        next(b for b in self.at.button if b.label==label).click().run()
        self.assertFalse(list(self.at.exception))

    def checked(self, correct=False):
        self.click('使用正确对照' if correct else '使用错误样本')
        self.assertTrue(next(b for b in self.at.button if b.label=='开始检查').disabled)
        self.click('确认正文范围')
        self.click('开始检查')
        return self.at.session_state['workflow']

    def generated(self):
        m=self.checked()
        self.click('选择全部可修正问题')
        self.click('生成修正版')
        return m

    def test_real_widgets_full_flow_and_rerun_no_additional_file(self):
        m=self.generated()
        self.assertEqual(m.body,[4,5,6,11,14,15])
        self.assertEqual(m.report['summary']['problem_count'],11)
        self.assertEqual(m.result['after']['summary']['problem_count'],0)
        before=list(m.task_dir.glob('fixed-*.docx'))
        self.at.run()
        self.assertEqual(list(m.task_dir.glob('fixed-*.docx')),before)
        self.assertTrue(next(b for b in self.at.button if b.label=='生成修正版').disabled)
        self.assertTrue(any('所选修改的落盘复查全部符合要求' in s.value for s in self.at.success))

    def test_scope_widget_change_removes_report_download_and_confirmation(self):
        m=self.generated()
        next(c for c in self.at.checkbox if c.label.startswith('段 4 ·')).uncheck().run()
        self.assertEqual(m.body,[5,6,11,14,15])
        self.assertIsNone(m.confirmed)
        self.assertIsNone(m.report)
        self.assertIsNone(m.result)
        self.assertEqual(list(self.at.get('download_button')),[])
        self.assertFalse(any('已生成新DOCX' in s.value for s in self.at.success))

    def test_switching_builtin_input_immediately_removes_old_results(self):
        m=self.generated()
        self.click('使用正确对照')
        self.assertIsNone(m.confirmed)
        self.assertIsNone(m.report)
        self.assertIsNone(m.result)
        self.assertEqual(list(self.at.get('download_button')),[])
        self.click('确认正文范围')
        self.click('开始检查')
        self.assertEqual(m.report['summary']['problem_count'],0)
        self.assertFalse(any(b.label=='生成修正版' for b in self.at.button))

    def test_empty_then_individual_selection_and_error_clears_success(self):
        m=self.checked()
        self.assertTrue(next(b for b in self.at.button if b.label=='生成修正版').disabled)
        key=next(f['key'] for f in m.eligible() if f['rule_id']=='R05')
        self.at.multiselect[0].set_value([key]).run()
        self.click('生成修正版')
        self.assertEqual(len(m.result['changes']),1)
        self.assertEqual(m.result['after']['summary']['problem_count'],10)
        self.click('清空选择')
        self.assertIsNone(m.result)
        self.assertEqual(list(self.at.get('download_button')),[])
        self.at.multiselect[0].set_value([key]).run()
        with patch('web.session.fix_document',side_effect=DemoError('验证错误提示')):
            self.click('生成修正版')
        self.assertTrue(any('验证错误提示' in s.value for s in self.at.error))
        self.assertFalse(any('已生成新DOCX' in s.value for s in self.at.success))

    def test_review_records_and_coverage_notes_both_rendered(self):
        m=self.checked()
        f=next(f for f in m.report['findings'] if f['rule_id']=='R03')
        f.update(status='review',fixable=False,actual={'eastAsia':{'theme':'minorEastAsia'}})
        m.report['coverage_notes']=[{'locator':{'paragraph':4,'run':2},'status':'review','detail':'覆盖提示独立可见'}]
        m.report['summary']['review_count']=2
        self.at.run()
        text='\n'.join(e.value for e in self.at.markdown)
        self.assertIn('主题字体（待复核）',text)
        self.assertTrue(any('覆盖提示独立可见' in s.value for s in self.at.warning))
        self.assertNotIn(f['key'], self.at.multiselect[0].options)

if __name__=='__main__':
    unittest.main(verbosity=2)

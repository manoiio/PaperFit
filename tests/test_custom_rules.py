"""模拟API自动验收，不调用网络、不消耗余额。默认47项继续单独保留。"""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import hashlib
import json
import math
import socket
import unittest
from streamlit.testing.v1 import AppTest
from core import check_document, fix_document, verify_document, load_rules, load_custom_rules
from core.engine import DEFAULT_RULES
from core.package import DemoError, Package, q, NS
from core.rule_config import strict_json
from core.spec_validation import validate_draft
from core.report import markdown
from ai.short_spec import Settings, parse_requirements, request_payload, settings
from web.session import WebSession

ROOT=Path(__file__).resolve().parents[1]
A='正文小四号，1.5倍行距'
B='正文四号，2倍行距'
BODY=[4,5,6,11,14,15]
CORRECT=ROOT/'samples/correct.docx'
PRESET=json.loads(CORRECT.with_suffix('.body.json').read_text())
DEFAULT_HASH=hashlib.sha256(DEFAULT_RULES.read_bytes()).hexdigest()
DRAFT_A={'font_size':{'value':12,'quote':'正文小四号'},'line_spacing':{'value':1.5,'quote':'1.5倍行距'},'unsupported':[]}
DRAFT_B={'font_size':{'value':14,'quote':'正文四号'},'line_spacing':{'value':2,'quote':'2倍行距'},'unsupported':[]}

def fake_parse(text,draft=None):
    if draft is None:draft=DRAFT_A if text==A else DRAFT_B
    def transport(request,timeout):
        assert timeout==30
        return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(draft,ensure_ascii=False)}}]}).encode()
    return parse_requirements(text,transport=transport,config=Settings('mock-key-never-network'))

class CustomRuleAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(dir=ROOT/'work/phase3',prefix='test-')
        self.root=Path(self.tmp.name)
        self.model=WebSession(self.root)
        self.assertTrue(self.model.load(CORRECT.read_bytes(),CORRECT.name,PRESET))
    def tearDown(self):self.tmp.cleanup()
    def parsed(self,text=B,draft=None):
        self.model.set_spec_text(text)
        self.assertTrue(self.model.parse_spec(parser=lambda x:fake_parse(x,draft)),self.model.ai_error)
        return self.model
    def applied(self,text=B):
        m=self.parsed(text)
        self.assertTrue(m.apply_draft(),m.ai_error)
        m.confirm();self.assertTrue(m.check(),m.error)
        return m

    def test_missing_field_stays_null_and_requires_explicit_choice(self):
        text='正文小四号'
        draft={'font_size':{'value':12,'quote':text},'line_spacing':None,'unsupported':[]}
        m=self.parsed(text,draft)
        self.assertIsNone(m.ai_draft['line_spacing'])
        self.assertEqual(m.draft_modes['R06'],'choose')
        self.assertFalse(m.apply_draft())
        m.edit_draft('R06','default')
        self.assertTrue(m.apply_draft(),m.ai_error)
        cfg=load_custom_rules(m.custom_rules_path)
        self.assertEqual(cfg['rules']['R06']['source']['kind'],'default_inherited')
        self.assertEqual(cfg['rules']['R05']['source']['kind'],'ai_extracted')
        self.assertEqual(cfg['rules']['R06']['source']['model'],None)

    def test_title_and_fixed_spacing_supported_only_as_non_executable_notes(self):
        text='标题四号，正文固定20磅行距'
        draft={'font_size':None,'line_spacing':None,'unsupported':[{'quote':'标题四号','reason':'title'},{'quote':'正文固定20磅行距','reason':'fixed_spacing'}]}
        self.assertEqual(validate_draft(draft,text),draft)
        for name,value,quote in [('font_size',14,'标题四号'),('line_spacing',2,'正文固定20磅行距')]:
            bad=deepcopy(draft);bad[name]={'value':value,'quote':quote}
            with self.assertRaises(DemoError):validate_draft(bad,text)

    def test_invalid_types_ranges_steps_unknown_keys_and_quotes_rejected(self):
        for value in (True,False,'14',None,float('nan'),float('inf'),10**1000,7.5,24.5,13.3):
            bad=deepcopy(DRAFT_B);bad['font_size']['value']=value
            with self.subTest(value=value),self.assertRaises(DemoError):validate_draft(bad,B)
        for value in (True,'2',1.1,1.75,3,float('-inf')):
            bad=deepcopy(DRAFT_B);bad['line_spacing']['value']=value
            with self.subTest(value=value),self.assertRaises(DemoError):validate_draft(bad,B)
        for mutation in ('unknown','tool','quote','path'):
            bad=deepcopy(DRAFT_B)
            if mutation=='unknown':bad['R01']={'value':1}
            if mutation=='tool':bad['font_size']['tool_call']='exec'
            if mutation=='quote':bad['font_size']['quote']='正文14磅'
            if mutation=='path':bad['unsupported']=[{'quote':'/Users/secret/file','reason':'unsupported'}]
            with self.subTest(mutation=mutation),self.assertRaises(DemoError):validate_draft(bad,B)
        for raw in ('{"x":NaN}','{"x":Infinity}','{"x":1,"x":2}'):
            with self.assertRaises(DemoError):strict_json(raw)

    def test_numeric_quote_mismatch_conflict_ambiguity_and_title_scope_rejected(self):
        for text,quote in [('正文12pt或14pt','正文12pt'),('正文12pt。正文14pt。','正文12pt'),('正文建议12pt','正文建议12pt'),('标题12pt，正文14pt','标题12pt')]:
            draft={'font_size':{'value':12,'quote':quote},'line_spacing':None,'unsupported':[]}
            with self.subTest(text=text),self.assertRaises(DemoError):validate_draft(draft,text)
        bad=deepcopy(DRAFT_B);bad['font_size']['value']=16
        with self.assertRaises(DemoError):validate_draft(bad,B)

    def test_request_contains_only_normative_text_json_mode_and_no_document_or_key(self):
        captured=[]
        def transport(request,timeout):
            captured.append((request,timeout))
            return json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(DRAFT_B,ensure_ascii=False)}}]}).encode()
        parsed=parse_requirements(B,transport=transport,config=Settings('test-secret'))
        self.assertEqual(len(captured),1)
        request,timeout=captured[0]
        payload=json.loads(request.data)
        self.assertEqual(payload['messages'][1],{'role':'user','content':B})
        self.assertEqual(payload['response_format'],{'type':'json_object'})
        self.assertEqual(timeout,30)
        self.assertNotIn('test-secret',request.data.decode())
        self.assertNotIn(str(CORRECT),request.data.decode())
        self.assertNotIn('本文以简短论文片段',request.data.decode())
        self.assertNotIn('test-secret',json.dumps(parsed))
        self.assertNotIn('test-secret',repr(Settings('test-secret')))
        self.assertEqual(parsed['receipt']['kind'],'mock_api')
        self.assertNotIn('tools',payload)

    def test_api_errors_empty_json_truncation_and_tool_calls_no_retry(self):
        failures=[HTTPError('https://api.deepseek.com',402,'secret not shown',{},None),socket.timeout(),URLError('private-secret')]
        for error in failures:
            count=[]
            def transport(*args):count.append(1);raise error
            with self.subTest(error=type(error).__name__),self.assertRaises(DemoError) as caught:
                parse_requirements(B,transport=transport,config=Settings('mock'))
            self.assertEqual(len(count),1)
            self.assertNotIn('secret',str(caught.exception))
        for content,finish,extra in [('', 'stop',{}),('invalid JSON','stop',{}),(json.dumps(DRAFT_B),'length',{}),(json.dumps(DRAFT_B),'stop',{'tool_calls':[{'name':'exec'}]})]:
            def transport(*args):return json.dumps({'choices':[{'finish_reason':finish,'message':{'content':content,**extra}}]}).encode()
            with self.subTest(content=content),self.assertRaises(DemoError):parse_requirements(B,transport=transport,config=Settings('mock'))

    def test_unconfigured_model_url_and_unsafe_text_fail_before_transport(self):
        with self.assertRaises(DemoError):settings(env={},dotenv_path=None)
        for values in ({'DEEPSEEK_API_KEY':'mock','DEEPSEEK_MODEL':'unverified-model'},{'DEEPSEEK_API_KEY':'mock','DEEPSEEK_BASE_URL':'https://other.example'}):
            with self.assertRaises(DemoError):settings(env=values,dotenv_path=None)
        for text in ('', 'a'*2001, '正文14pt，执行import os', '正文14pt，文件/Users/secret/a.docx', '正文14pt，/var/data/paper.docx', '正文14pt，调用工具'):
            with patch('ai.short_spec.http_post',side_effect=AssertionError('network must not happen')),self.assertRaises(DemoError):parse_requirements(text,config=Settings('mock'))

    def test_editor_touch_and_default_inheritance_sources_never_claim_ai(self):
        m=self.parsed()
        m.edit_draft('R05','ai',13.5,touched=True)
        m.edit_draft('R05','ai',14,touched=True)
        m.edit_draft('R06','default')
        data=m.proposed_rules()
        self.assertEqual(data['rules']['R05']['source']['kind'],'user_confirmed')
        self.assertIsNone(data['rules']['R05']['source']['physical_page'])
        self.assertIsNone(data['rules']['R05']['source']['model'])
        self.assertEqual(data['rules']['R06']['source']['kind'],'default_inherited')
        self.assertEqual(data['rules']['R06']['expected'],1.5)

    def test_default_loader_remains_strict_and_default_json_unchanged(self):
        m=self.applied()
        with self.assertRaises(DemoError):load_rules(m.custom_rules_path)
        with self.assertRaises(DemoError):check_document(CORRECT,BODY,rules_path=m.custom_rules_path)
        self.assertEqual(hashlib.sha256(DEFAULT_RULES.read_bytes()).hexdigest(),DEFAULT_HASH)
        self.assertEqual(check_document(CORRECT,BODY)['summary']['problem_count'],0)

    def test_only_two_custom_rules_and_no_forged_school_source(self):
        m=self.applied()
        data=json.loads(m.custom_rules_path.read_text())
        for mode in ('other_rule','source','value','unknown','fake_ai_value'):
            bad=deepcopy(data)
            if mode=='other_rule':bad['rules']['R07']['expected']=3
            if mode=='source':bad['rules']['R05']['source']['file']='school.pdf';bad['rules']['R05']['source']['physical_page']=18
            if mode=='value':bad['rules']['R06']['expected']=1.75
            if mode=='unknown':bad['execute']='tool'
            if mode=='fake_ai_value':bad['rules']['R05']['expected']=16
            path=self.root/(mode+'.json');path.write_text(json.dumps(bad,ensure_ascii=False))
            with self.subTest(mode=mode),self.assertRaises(DemoError):load_custom_rules(path)

    def test_A_keeps_original_check_result(self):
        m=self.applied(A)
        self.assertEqual(m.report['summary']['problem_count'],0)
        self.assertEqual(m.report['summary']['review_count'],0)
        self.assertEqual(m.report['rules']['name'],'用户确认的演示规则')
        self.assertEqual(m.report['rules']['sources']['R05']['quote'],'正文小四号')

    def test_B_really_changes_check_fix_and_disk_verification_preserving_unselected(self):
        m=self.applied()
        self.assertEqual(m.report['summary']['problem_count'],14)
        selected=[f['key'] for f in m.eligible()]
        m.set_selection(selected);self.assertTrue(m.generate(),m.error)
        self.assertEqual(len(m.result['changes']),14)
        after=verify_document(m.result['output'],m.result['output_body_manifest'],custom_rules_path=m.custom_rules_path)
        self.assertTrue(all(f['actual']['pt']==14 for f in after['findings'] if f['rule_id']=='R05'))
        self.assertTrue(all(f['actual']['multiple']==2 for f in after['findings'] if f['rule_id']=='R06'))
        self.assertTrue(all(c['verification']=='pass' for c in m.result['changes']))
        self.assertEqual(m.input_path.read_bytes(),CORRECT.read_bytes())
        a,b=Package(CORRECT),Package(m.result['output'])
        for part in a.parts:
            if part!='word/document.xml':self.assertEqual(a.parts[part],b.parts[part],part)
        self.assertEqual(a.root.xpath('//w:t/text()',namespaces=NS),b.root.xpath('//w:t/text()',namespaces=NS))
        self.assertEqual(a.styles.find("w:style[@w:styleId='DemoPointBody']/w:pPr/w:ind",NS).attrib,
                         b.styles.find("w:style[@w:styleId='DemoPointBody']/w:pPr/w:ind",NS).attrib)
        # R07 24pt point indent is intentionally NOT silently changed when font grows to14pt.
        self.assertEqual(after['summary']['problem_count'],1)
        self.assertEqual([f['rule_id'] for f in after['findings'] if f['status']=='problem'],['R07'])
        md=markdown(after)
        self.assertIn('用户确认的演示规则',md)
        self.assertIn('AI提取后用户确认',md)
        self.assertNotIn('None 物理页None',md)

    def test_draft_edit_does_not_apply_until_confirmation_and_then_invalidates(self):
        m=self.model;m.confirm();self.assertTrue(m.check())
        old=m.report
        self.parsed();m.edit_draft('R05','manual',13.5,touched=True)
        self.assertIs(m.report,old)
        self.assertIsNone(m.custom_rules_path)
        self.assertTrue(m.apply_draft())
        self.assertIsNone(m.confirmed);self.assertIsNone(m.report);self.assertIsNone(m.result)
        self.assertEqual(m.body,BODY)
        self.assertEqual(m.downloads(),{})

    def test_norm_text_change_invalidates_ai_only_active_rules_until_new_apply(self):
        m=self.applied();active=m.custom_rules_path;m.set_selection([m.eligible()[0]['key']]);m.generate()
        old=m.result
        m.set_spec_text(A)
        self.assertIsNone(m.ai_draft);self.assertIsNone(m.ai_receipt)
        self.assertEqual(m.custom_rules_path,active)
        self.assertIs(m.result,old)
        self.assertTrue(m.downloads())
        self.assertTrue(m.parse_spec(parser=fake_parse));self.assertTrue(m.apply_draft())
        self.assertIsNone(m.report);self.assertIsNone(m.result);self.assertIsNone(m.confirmed)
        self.assertEqual(m.downloads(),{})

    def test_api_failure_keeps_default_flow_and_does_not_emit_success(self):
        m=self.model;m.confirm();self.assertTrue(m.check());before=m.report
        m.set_spec_text(B)
        with patch('ai.short_spec.parse_requirements',side_effect=DemoError('API余额不足')):
            self.assertFalse(m.parse_spec())
        self.assertIsNone(m.ai_draft);self.assertIsNone(m.custom_rules_path)
        self.assertIs(m.report,before)
        self.assertEqual(m.report['summary']['problem_count'],0)
        self.assertTrue(m.check())

    def test_default_switch_invalidates_and_custom_survives_input_change_in_own_dir(self):
        m=self.applied();original=m.custom_rules_path
        self.assertTrue(m.load(CORRECT.read_bytes(),'new.docx',PRESET))
        self.assertIsNotNone(m.custom_rules_path);self.assertNotEqual(original,m.custom_rules_path)
        self.assertFalse(original.exists());self.assertIsNone(m.confirmed)
        self.assertEqual(m.active_custom_data['rules']['R05']['expected'],14)
        m.confirm();self.assertTrue(m.check())
        m.use_default_rules()
        self.assertIsNone(m.custom_rules_path);self.assertIsNone(m.report);self.assertIsNone(m.confirmed)
        m.confirm();self.assertTrue(m.check());self.assertEqual(m.report['summary']['problem_count'],0)

    def test_double_parse_is_not_a_second_request(self):
        calls=[]
        m=self.model;m.set_spec_text(B)
        def parser(text):calls.append(1);return fake_parse(text)
        self.assertTrue(m.parse_spec(parser=parser))
        self.assertFalse(m.parse_spec(parser=parser))
        self.assertEqual(len(calls),1)
        self.assertEqual(m.ai_receipt['kind'],'mock_api')

    def test_manual_configuration_without_text_reset_clears_all_draft_state(self):
        m=self.model
        m.edit_draft('R05','manual',14,touched=True)
        m.edit_draft('R06','manual',2,touched=True)
        self.assertTrue(m.apply_draft(),m.ai_error)
        m.reset()
        self.assertIsNone(m.active_custom_data)
        self.assertIsNone(m.ai_draft)
        self.assertEqual(m.draft_modes,{'R05':'choose','R06':'choose'})
        self.assertEqual(m.draft_edited,set())

    def test_two_sessions_do_not_share_custom_data_or_rule_files(self):
        m=self.applied()
        other=WebSession(self.root)
        self.assertTrue(other.load(CORRECT.read_bytes(),'other.docx',PRESET))
        self.assertIsNone(other.ai_draft);self.assertIsNone(other.custom_rules_path)
        other.confirm();self.assertTrue(other.check());self.assertEqual(other.report['summary']['problem_count'],0)
        other.set_spec_text(A);self.assertTrue(other.parse_spec(parser=fake_parse));self.assertTrue(other.apply_draft())
        self.assertNotEqual(m.custom_rules_path,other.custom_rules_path)
        self.assertEqual(load_custom_rules(m.custom_rules_path)['rules']['R05']['expected'],14)
        self.assertEqual(load_custom_rules(other.custom_rules_path)['rules']['R05']['expected'],12)
        other.reset();self.assertTrue(m.custom_rules_path.exists())

class CustomUIAcceptance(unittest.TestCase):
    def setUp(self):
        mocked=patch('web.custom_ui.config_status',return_value={'configured':True,'model':'deepseek-flash','message':'模拟配置，仅测试'})
        mocked.start();self.addCleanup(mocked.stop)
        self.at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
    def tearDown(self):self.at.session_state['workflow'].reset()
    def click(self,label):
        next(b for b in self.at.button if b.label==label).click().run()
        self.assertFalse(list(self.at.exception))
    def test_mock_parse_edit_confirm_and_default_restore_widgets(self):
        self.click('使用正确对照');self.click('填入示例B')
        with patch('ai.short_spec.parse_requirements',side_effect=fake_parse):self.click('解析要求')
        m=self.at.session_state['workflow']
        self.assertEqual(m.ai_receipt['kind'],'mock_api')
        self.assertTrue(any('模拟API响应' in e.value for e in self.at.caption))
        next(n for n in self.at.number_input if n.label.startswith('字号')).set_value(13.5).run()
        self.assertIsNone(m.custom_rules_path)
        self.click('确认并应用');self.assertIsNone(m.confirmed)
        self.assertEqual(m.active_custom_data['rules']['R05']['source']['kind'],'user_confirmed')
        self.click('确认正文范围');self.click('开始检查')
        self.assertEqual(m.report['rules']['name'],'用户确认的演示规则')
        self.click('切换回默认演示规则')
        self.assertIsNone(m.report);self.assertIsNone(m.custom_rules_path)
    def test_missing_mock_field_explicit_default_no_hidden_ai_fill(self):
        self.click('使用正确对照')
        text='正文小四号'
        next(t for t in self.at.text_area if t.label.startswith('短格式')).set_value(text).run()
        d={'font_size':{'value':12,'quote':text},'line_spacing':None,'unsupported':[]}
        with patch('ai.short_spec.parse_requirements',side_effect=lambda x:fake_parse(x,d)):self.click('解析要求')
        m=self.at.session_state['workflow']
        self.assertTrue(next(b for b in self.at.button if b.label=='确认并应用').disabled)
        next(s for s in self.at.selectbox if s.label=='正文行距来源处理').set_value('沿用默认值').run()
        self.click('确认并应用')
        self.assertEqual(m.active_custom_data['rules']['R06']['source']['kind'],'default_inherited')

if __name__=='__main__':unittest.main(verbosity=2)

"""Strict supplement adaptation; all requests simulated with explicit config."""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch
import json
from ai.smart_spec import VERSION,coverage,validate,parse_requirements
from ai.short_spec import Settings
from core.rule_bundle import FIELDS,flat
from core.package import DemoError
from web.session import WebSession
from web.onepass_session import start,continue_command,overlay
ROOT=Path(__file__).resolve().parents[1]
TEXT='正文宋体小四，首行缩进两字符；一级标题黑体三号居中；表内文字五号。'
EXPECTED={'font_cn':('宋体','正文宋体'),'font_size':(12,'正文宋体小四'),'first_line_indent':(2,'正文宋体小四，首行缩进两字符'),'heading1_font_cn':('黑体','一级标题黑体'),'heading1_font_size':(16,'一级标题黑体三号'),'heading1_alignment':('center','一级标题黑体三号居中'),'table_content__font_size':(10.5,'表内文字五号')}
def draft(values=EXPECTED):return {'version':VERSION,'fields':{n:{'value':v,'quote':q,'unit':FIELDS['main'][n][2],'location':'摘录:L1','support':'supported'} for n,(v,q) in values.items()},'issues':[]}
def parser(text):return parse_requirements(text,config=Settings('synthetic'),transport=lambda *_:json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(draft(),ensure_ascii=False)}}],'usage':{'total_tokens':100}}))

class SmartSupplementAcceptance(TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def session(self,name='a'):
  s=WebSession(self.root/name);s.set_mode('academic');s.load((ROOT/'samples/phase44/errors.docx').read_bytes(),'合成.docx');return s
 def test_compact_sizes_two_chars_once_and_original_sources_preserved(self):
  s=self.session();prior=s.current_rule_bundle();r=parser(TEXT);overlay(s,TEXT,r);after=s.current_rule_bundle()
  for n,(v,q) in EXPECTED.items():self.assertEqual(flat('main',after['modules']['main'])[n],v);self.assertEqual(after['provenance']['main'][n]['quote'],q)
  for n,origin in prior['provenance']['main'].items():
   if n not in EXPECTED:self.assertEqual(after['provenance']['main'][n],origin,n);self.assertEqual(flat('main',after['modules']['main'])[n],flat('main',prior['modules']['main'])[n],n)
  for m in ('front','toc','notes'):self.assertEqual(after['modules'][m],prior['modules'][m]);self.assertEqual(after['provenance'][m],prior['provenance'][m])
  self.assertEqual(r['receipt']['attempt']['validation'],'accepted');self.assertEqual(r['receipt']['usage']['total_tokens'],100)
 def test_all_existing_requested_families_and_units(self):
  text='正文西文Arial；正文2倍行距；正文居左；正文段前0.5行，段后6pt；二级标题宋体小四居左，1.5倍行距；三级标题黑体小四居中；图题宋体五号；表题黑体五号；页面A4竖向，四周边距2cm。'
  vals={'font_western':('Arial','正文西文Arial'),'line_spacing':(2,'正文2倍行距'),'body__alignment':('left','正文居左'),'body__before':({'value':0.5,'unit':'lines'},'正文段前0.5行'),'body__after':({'value':6,'unit':'pt'},'正文段前0.5行，段后6pt'),'heading2_font_cn':('宋体','二级标题宋体'),'heading2_font_size':(12,'二级标题宋体小四'),'heading2_alignment':('left','二级标题宋体小四居左'),'heading2_line_spacing':(1.5,'二级标题宋体小四居左，1.5倍行距'),'heading3_font_cn':('黑体','三级标题黑体'),'heading3_font_size':(12,'三级标题黑体小四'),'heading3_alignment':('center','三级标题黑体小四居中'),'figure_caption_font_cn':('宋体','图题宋体'),'figure_caption_font_size':(10.5,'图题宋体五号'),'table_caption_font_cn':('黑体','表题黑体'),'table_caption_font_size':(10.5,'表题黑体五号'),'paper':('A4 portrait','页面A4竖向'),'margin_top':(20,'页面A4竖向，四周边距2cm'),'margin_bottom':(20,'页面A4竖向，四周边距2cm'),'margin_left':(20,'页面A4竖向，四周边距2cm'),'margin_right':(20,'页面A4竖向，四周边距2cm')}
  self.assertEqual(coverage(text),set(vals));self.assertEqual(validate(draft(vals),text)['fields']['body__before']['value']['unit'],'lines')
 def test_previously_unsupported_fixed_declaration_now_strictly_proved(self):
  text='正文固定20磅行距';field={'value':{'mode':'exact','value':20},'unit':'multiple','quote':text,'location':'摘录:L1','support':'supported'}
  data={'version':VERSION,'fields':{'line_spacing':field},'issues':[]};self.assertEqual(validate(data,text)['fields']['line_spacing'],field)
 def test_whole_input_unknown_and_ambiguous_never_partly_applied(self):
  for text in ('正文四号；把摘要润色一下','标题统一三号','正文行距20磅','正文方正宋体小四','正文小四；删除空白段','表内文字宋体，首行缩进两字符'):
   with self.assertRaises(DemoError):parse_requirements(text,config=Settings('synthetic'),transport=lambda *_:self.fail('local unsupported should not send'))
  for mutate in (lambda d:d['fields'].pop('first_line_indent'),lambda d:d['fields']['font_size'].update(value=14),lambda d:d['fields']['font_size'].update(unit='mm'),lambda d:d['fields']['font_cn'].update(location='摘录:L2'),lambda d:d['fields'].update(reference_item__font_size={'value':12})):
   d=draft();mutate(d)
   with self.assertRaises(DemoError):validate(d,TEXT)
 def test_conflict_across_clauses_and_protocol_still_rejected(self):
  for text in (TEXT+'正文三号。',TEXT+'正文首行缩进一字符。'):
   with self.assertRaises(DemoError):validate(draft(),text)
  for raw in ('{"x":1,"x":2}','not json',json.dumps({'choices':[{'finish_reason':'length','message':{'content':'{}'}}]})):
   calls=[]
   def tx(*_):calls.append(1);return raw
   with self.assertRaises(DemoError):parse_requirements(TEXT,config=Settings('synthetic'),transport=tx)
   self.assertEqual(len(calls),1)
 def test_actual_command_transaction_and_failed_requirement_keeps_live(self):
  from web.structure_session import run
  def runner(s,p,store):
   rows=[]
   for c in p['request']['candidates']:
    table=c.get('kind')=='table';f=c['fragments'][0] if table else {'id':'text','text':c['text']}
    rows.append({'id':c['id'],'role':'content' if c['id']=='t:2' else 'pending','evidence':f['text'],'evidence_location':f['id'],'reason':'独立可见证据模拟'})
   return run(s,p,store,config=Settings('synthetic'),transport=lambda *_:json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'version':'structure-ids-v1','suggestions':[{k:(r['evidence_location'] if k=='evidence' else r[k]) for k in ('id','role','evidence','reason')} for r in rows]} if p['request']['version']=='structure-v3-context' else {'suggestions':rows})}}]}))
  s=self.session();old=s.rules_hash;st={};calls=[]
  def once(text):calls.append(1);return parser(text)
  start(s,st,TEXT,spec_parser=once,structure_runner=runner);self.assertEqual(st['status'],'waiting',st.get('error'));self.assertEqual(s.rules_hash,old);self.assertFalse(s.history)
  continue_command(s,st,TEXT,{'table:4':'pending'});self.assertEqual(st['status'],'done',st.get('error'));self.assertEqual(calls,[1]);self.assertTrue(s.downloads());self.assertEqual(s.current_round,0)
  for n,(v,_) in EXPECTED.items():self.assertEqual(flat('main',s.current_rule_bundle()['modules']['main'])[n],v)
  self.assertTrue(any(c['rule_id']=='R08' for c in s.result['changes']));self.assertTrue(any(c['rule_id']=='R23' for c in s.result['changes']))
  self.assertEqual(len(s.note_draft['objects']),6);self.assertTrue(any(c['rule_id']=='R36' for c in s.result['changes']));self.assertTrue(any(c['rule_id']=='R37' for c in s.result['changes']))
  b=self.session('invalid');before=deepcopy(b.current_rule_bundle());oldhash=b.rules_hash
  with patch('core.rule_bundle.compile_bundle',side_effect=DemoError('synthetic compile rejection')):
   with self.assertRaises(DemoError):overlay(b,TEXT,parser(TEXT))
  self.assertEqual(b.rules_hash,oldhash);self.assertEqual(b.current_rule_bundle()['provenance'],before['provenance']);self.assertEqual(flat('main',b.current_rule_bundle()['modules']['main']),flat('main',before['modules']['main']))
  c=self.session('confirmed');c.set_table_enabled(False);c.enable_notes(False);c.batch_types([9],'heading2');self.assertTrue(c.confirm_and_check(),c.error);prior=deepcopy(c.paragraph_types);state={}
  start(c,state,TEXT,spec_parser=parser,structure_runner=lambda *_:self.fail('Known user classifications must not be resent'))
  self.assertEqual(state['status'],'done',state.get('error'));self.assertEqual(c.paragraph_types,prior);self.assertTrue(state['audit']['prior_classification_preserved'])


 def test_point_spacing_not_size_or_indent_unit_and_authored_fixture(self):
  text=(ROOT/'samples/phase44/requirements.txt').read_text().strip();d=json.loads((ROOT/'samples/phase44/expected-overrides.json').read_text());validate(d,text)
  same='正文小四，首行缩进两字符，段后6pt。'
  vals={'font_size':(12,'正文小四'),'first_line_indent':(2,'正文小四，首行缩进两字符'),'body__after':({'value':6,'unit':'pt'},same.rstrip('。'))}
  validate(draft(vals),same)
  with self.assertRaises(DemoError):validate(draft(vals),same+'正文首行缩进2cm。')

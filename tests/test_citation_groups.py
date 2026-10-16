"""Explicit grammar upgrade, per-member evidence, exact XML and legal plan probes."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase,mock
import json,time,zipfile
from lxml import etree as E
from core.citation_syntax import parse,SINGLE,GROUPS,MAX_LENGTH,MAX_EXPANDED,position_groups,spans
from core.citations import inventory,template,upgrade_template,CONFIG,validate_scope
from core.package import Package,DemoError,q,NS
from core import check_document,fix_document
from scripts.reproduce_citation_groups_demo import session,selection,SAMPLE,run
from scripts.verify_citation_groups_output import verify
from tests.test_citations import rewrite,characters
class GroupGrammarTests(TestCase):
 def test_all_supported_literal_syntax_and_positions(self):
  for raw,expected in [('[1]',[1]),('[1,3]',[1,3]),('[1-3]',[1,2,3]),('[1–3]',[1,2,3]),('[1-3,5]',[1,2,3,5]),('[ 1 - 3 , 5 ]',[1,2,3,5])]:
   p=parse(raw,GROUPS);self.assertTrue(p['supported']);self.assertEqual(p['numbers'],expected);self.assertEqual(p['raw'],raw)
   for m in p['members']:self.assertEqual(raw[m['start']:m['end']],m['raw'])
 def test_v1_does_not_upgrade_or_allow_spaces(self):
  for raw in ('[1,3]','[1-3]','[ 1 ]'):self.assertFalse(parse(raw)['supported'])
  self.assertTrue(parse('[1]')['supported'])
 def test_exact_resource_bounds(self):
  p=parse('[1-100]',GROUPS);self.assertEqual(len(p['numbers']),MAX_EXPANDED)
  for raw in ('[1-101]','[1-100,1]','[1-60,1-60]','[3-1]','[0]','[0001]','[100000]','['+'9'*10000+']'):
   p=parse(raw,GROUPS);self.assertFalse(p['supported']);self.assertEqual(p['numbers'],[])
 def test_length_bound_preserves_complete_raw(self):
  raw='['+' '*509+'1]';self.assertEqual(len(raw),MAX_LENGTH);self.assertTrue(parse(raw,GROUPS)['supported']);self.assertFalse(parse(raw+' ',GROUPS)['supported'])
 def test_overlapping_members_retained_no_rewrite_or_school_error(self):
  p=parse('[1-3,2-4,1]',GROUPS);self.assertEqual(p['numbers'],[1,2,3,2,3,4,1]);self.assertEqual(p['unique_numbers'],[1,2,3,4]);self.assertEqual(p['notices'][0]['numbers'],[1,2,3])
 def test_ascii_only_and_no_tab_nbsp_other_dash(self):
  for raw in ('［1］','[1，3]','[1—3]','[1−3]','[1\t,3]','[1\u00a0,3]','[1,,2]','[1 3]','[1:3]','[1-2-3]','[True]'):self.assertFalse(parse(raw,GROUPS)['supported'],raw)
 def test_nested_and_unclosed_never_authorize_inner(self):
  for raw in ('[1,[2]]','[[1]]','[1,3','[1［2］]'):
   rows=list(spans(raw,GROUPS));self.assertEqual(len(rows),1);self.assertEqual(rows[0][2],raw);self.assertFalse(parse(raw,GROUPS)['supported'])
 def test_template_v2_explicit_required_and_strict(self):
  cfg=upgrade_template(CONFIG);self.assertEqual(cfg['syntax'],GROUPS);self.assertEqual(template(CONFIG),CONFIG)
  for k,v in [('syntax',SINGLE),('structure_version',True),('superscript',1),('extra','x')]:
   c=deepcopy(cfg);c[k]=v
   with self.assertRaises(DemoError):template(c)
  c=deepcopy(CONFIG);c['structure_version']=2
  with self.assertRaises(DemoError):template(c)
 def test_upgrade_keeps_switches_name_and_source(self):
  c=deepcopy(CONFIG);c['superscript']=False;c['name']='用户演示';self.assertEqual({k:v for k,v in upgrade_template(c).items() if k not in ('syntax','structure_version')},{k:v for k,v in c.items() if k!='structure_version'})
 def test_position_groups_not_internal_order(self):
  def row(raw,i):return {'id':str(i),'paragraph':i,'start':0,'end':len(raw),'text':raw,**{k:v for k,v in parse(raw,GROUPS).items() if k in ('numbers','unique_numbers')}}
  for values,risks in [(['[1,2]','[3]'],[False,False]),(['[2,1]','[3]'],[False,False]),(['[1,3]','[2]'],[True,False]),(['[1]','[1]','[2]'],[False,False,False])]:
   order,groups=position_groups([row(x,i) for i,x in enumerate(values)]);self.assertEqual([g['risk'] for g in groups],risks)
  order,groups=position_groups([row('[2,1]',0)]);self.assertEqual(order,[2,1]);self.assertEqual(groups[0]['raw_numbers'],[2,1])
 def test_large_number_no_prefix_expansion(self):
  t=time.monotonic();p=parse('[99999]',GROUPS);_,g=position_groups([{'id':'x','paragraph':1,'start':0,'end':7,'text':p['raw'],**p}]);self.assertEqual(g[0]['missing_prefix_count'],99998);self.assertLess(time.monotonic()-t,0.1)

class GroupFlowTests(TestCase):
 def setUp(self):self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name);self.s=session(self.d/'web')
 def custom(self,text,*,full=True,duplicate=False):
  def edit(pkg):
   p=pkg.paragraphs[2]
   for r in list(p.findall(q('r'))):p.remove(r)
   r=E.SubElement(p,q('r'));E.SubElement(r,q('t')).text=text
   if duplicate:pkg.paragraphs[8].find(q('r')).find(q('t')).text='[1] 重复编号演示'
  p=rewrite(SAMPLE/'errors.docx',self.d/'custom.docx',edit);s=session(self.d/'custom-web',checked=False);s.load(p.read_bytes(),'自定义合成.docx');s.set_types(json.loads((SAMPLE/'scope.json').read_text())['roles']);s.enable_citations(True);d=deepcopy(s.citation_draft);d['template']=upgrade_template(d['template']);d['scan']=[3];s.edit_citations(d);d=deepcopy(s.citation_draft);d['objects']={r['id']:'citation' for r in s.citation_inventory()['objects']};d.update(complete=full,references_complete=full);s.edit_citations(d)
  # Other body paragraphs stay intentionally unscanned -> full false unless explicitly narrow body.
  types=deepcopy(s.paragraph_types)
  for n in ('4','5','6'):types[n]='other'
  s.set_types(types);s.confirm_citations();self.assertTrue(s.confirm_and_check(),s.error);return s
 def test_literal_oracle_full_raw_and_repeated_distinct(self):
  spans=json.loads((SAMPLE/'scope.json').read_text())['selected_citations'];rows={r['id']:r for r in self.s.citation_inventory()['objects']}
  for t in spans:
   r=rows[f"c:{t['paragraph']}:{t['start']}:{t['end']}"];self.assertEqual(r['text'],t['raw']);self.assertEqual(r['numbers'],t['expected_numbers'])
  a=[r for r in rows.values() if r['text']=='[1,3]'];self.assertEqual(len(a),2);self.assertNotEqual(a[0]['id'],a[1]['id'])
 def test_not_just_first_number_missing_member(self):
  s=self.custom('[1,14]');row=s.report['citations']['rows'][0];self.assertEqual([m['status'] for m in row['members']],['pass','problem']);self.assertEqual(row['status'],'problem');self.assertEqual(s.report['citations']['counts']['member_problems'],1)
 def test_duplicate_reference_member_keeps_other_pass(self):
  s=self.custom('[1,3]',duplicate=True);row=s.report['citations']['rows'][0];self.assertEqual([m['status'] for m in row['members']],['review','pass']);self.assertEqual(row['status'],'review');self.assertEqual(len(row['members'][0]['references']),2)
 def test_partial_range_missing_review_and_no_full_order_pass(self):
  s=self.custom('[1,14]',full=False);self.assertEqual(s.report['citations']['rows'][0]['status'],'review');f=next(f for f in s.report['findings'] if f['rule_id']=='R34' and f['locator'].get('property')=='first_occurrence');self.assertEqual(f['status'],'review')
 def test_position_evidence_report_and_repetition(self):
  s=self.custom('[2,1] [3] [2,1]');c=s.report['citations'];self.assertEqual(c['order'],[2,1,3]);self.assertFalse(any(g['risk'] for g in c['order_groups']));self.assertEqual(c['order_groups'][-1]['first_numbers'],[]);self.assertEqual(c['counts']['groups'],3);self.assertEqual(c['counts']['expanded_members'],5)
 def test_gap_first_position_remains_even_later_filled(self):
  s=self.custom('[1,3] [2]');g=s.report['citations']['order_groups'];self.assertTrue(g[0]['risk']);self.assertEqual((g[0]['first_missing'],g[0]['earlier_higher_number']),(2,3));self.assertTrue(any(f['rule_id']=='R34' and f['status']=='problem' and f['locator'].get('property')=='first_occurrence' for f in s.report['findings']))
 def test_unsupported_stays_readonly_even_confirmed(self):
  s=self.custom('[3-1] [1，3]');self.assertTrue(all(f['status']=='review' and not f['fixable'] for f in s.report['findings'] if f['rule_id']=='R33'))
 def test_v1_old_groups_remain_review(self):
  s=session(self.d/'v1',v2=False);self.assertTrue(all(f['status']=='review' for f in s.report['findings'] if f['rule_id']=='R33' and f['excerpt'] in ('[1,3]','[1–3]','[1-3,5]')))
 def test_complete_raw_never_preview_truncated(self):
  raw='['+'1,'*60+'2]';s=self.custom(raw);r=s.citation_inventory()['objects'][0];self.assertEqual(r['text'],raw);self.assertEqual(r['end']-r['start'],len(raw));self.assertTrue(r['fixable'])
 def test_single_attribute_whole_group_only(self):
  s=self.s;f=next(f for f in s.eligible() if f['rule_id']=='R33');s.set_selection([f['key']]);before=characters(Package(s.input_path));self.assertTrue(s.rehearse(),s.rehearsal_error);identifier=s.rehearsal['id'];self.assertTrue(s.adopt_rehearsal(identifier,acknowledged=True));after=characters(Package(s.result['output']));loc=f['locator']
  for n,(aa,bb) in enumerate(zip(before,after),1):
   for i,(a,b) in enumerate(zip(aa,bb)):
    self.assertEqual((a[0],a[1],a[3]),(b[0],b[1],b[3]));self.assertEqual(b[2],'superscript' if n==loc['paragraph'] and loc['start']<=i<loc['end'] else a[2])
 def test_direct_conflict_still_refuses(self):
  s=self.s;s.set_selection(selection(s))
  with self.assertRaisesRegex(DemoError,'分轮'):fix_document(s.input_path,self.d/'bad.docx',s.confirmed,selected_keys=s.selected,**s._rules_arguments())
 def test_manual_two_round_byte_equivalence_independent_zip(self):
  out=self.d/'reproduce'
  with mock.patch('builtins.print'):run(out)
  proof=verify(SAMPLE/'errors.docx',out/'step-1.docx',out/'step-2.docx');self.assertTrue(proof['selected_whole_spans_superscript_only'])
 def test_plan_new_targets_mode_full_raw_fresh_keys(self):
  s=self.s;s.set_selection(selection(s));self.assertTrue(s.rehearse_plan(),s.rehearsal_error);targets=s.rehearsal['resolved'];self.assertTrue(all(t['syntax']==GROUPS for t in targets));self.assertEqual(len([t for t in targets if t['text']=='[1,3]']),2)
 def test_plan_target_grammar_change_refused(self):
  from core.correction_plan import resolve_targets
  s=self.s;s.set_selection(selection(s));self.assertTrue(s.rehearse_plan());tx=s.rehearsal['transactions'];targets=deepcopy(s.rehearsal['draft']['targets']);targets[0]['syntax']=SINGLE
  with self.assertRaises(DemoError):resolve_targets(Package(tx[0]['result']['output']),tx[0]['result']['output_classification_manifest'],targets,tx[1]['result']['before'])
 def test_upgrade_invalidates_report_confirmation_and_plan(self):
  s=self.s;s.set_selection(selection(s));self.assertTrue(s.rehearse_plan());d=deepcopy(s.citation_draft);d['template']=deepcopy(CONFIG);s.edit_citations(d);self.assertIsNone(s.report);self.assertIsNone(s.citation_confirmed);self.assertIsNone(s.rehearsal);self.assertFalse(s.selected)
 def test_scope_cache_bound_to_grammar(self):
  s=self.s;v2=s.citation_inventory();d=deepcopy(s.citation_draft);d['template']=deepcopy(CONFIG);s.edit_citations(d);v1=s.citation_inventory();self.assertTrue(v2['objects'][0]['numbers']);self.assertFalse(v1['objects'][0]['numbers'])
 def test_restore_preserves_mode_exclusions_without_authorization(self):
  from web.session import WebSession
  s=self.s;s.set_selection(selection(s));self.assertTrue(s.rehearse_plan());s.prepare_project();o=WebSession(self.d/'other');o.stage_project(s.project_download());r=o.restore_project(acknowledged=True);self.assertEqual(r.citation_draft,s.citation_draft);self.assertEqual(r.report['citations'],s.report['citations']);self.assertIsNone(r.rehearsal);self.assertTrue(r.material_exclusions)
 def test_two_sessions_modes_separate(self):
  o=session(self.d/'independent',v2=False);self.assertEqual(o.citation_draft['template']['structure_version'],1);self.assertEqual(self.s.citation_draft['template']['structure_version'],2)
 def test_exports_full_members_and_privacy(self):
  s=self.s;c=s.report['citations'];self.assertTrue(c['order_groups']);values=s.prepare_reading_export();h=values['report.html'].decode();self.assertIn('组合引文逐成员对应',h);self.assertIn('首次位置组证据',h);self.assertNotIn('合成参考文献',h);self.assertNotIn('/Volumes/',h)
 def test_final_repeat_stable_and_download_binding(self):
  s=self.s;s.set_selection([f['key'] for f in s.eligible() if f['rule_id']=='R33']);self.assertTrue(s.generate());p=Path(s.result['output']);before=p.read_bytes();m=s.result['output_classification_manifest'];v=fix_document(p,self.d/'again.docx',s.result['output_body_manifest'],mode='academic',classification_manifest=m,selected_rules=['R33']);self.assertEqual(Path(v['output']).read_bytes(),before);self.assertFalse(v['changes'])
 def test_original_hash_rules_and_span_preapply(self):
  from core.citations import apply
  f=next(f for f in self.s.eligible() if f['rule_id']=='R33');f=deepcopy(f);f['citation_target']['raw']='[9]'
  with self.assertRaises(DemoError):apply(Package(self.s.input_path),f)

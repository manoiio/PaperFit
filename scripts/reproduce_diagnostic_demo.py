"""Programmatic full-scope equivalence + independent XML/ZIP assertions. No API or rendering."""
from pathlib import Path
import sys,os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
import json,time,statistics,zipfile
from copy import deepcopy
from lxml import etree as E
from core import check_document,fix_document,rule_bundle as rb,spec_diagnostics as sd
from core.package import Package,NS,q,sha256
from core.report import markdown,modification_markdown
from tests.test_workbench import make_session,scopes
import argparse
parser=argparse.ArgumentParser(description='Offline synthetic diagnosis/repair/equivalence demo; no API or rendering.')
parser.add_argument('--output',required=True,help='New directory; refuses existing output')
args=parser.parse_args();W=Path(args.output).resolve()
if W.exists():raise SystemExit('Output already exists; choose a new directory')
W.mkdir(parents=True);D=W/'deliverables';D.mkdir()
s=make_session(W/'verified-task');s.load_synthetic_diagnostic();initial=deepcopy(s.diagnostic_store()['current']);t=time.perf_counter();a=s.diagnostic_analysis();paths=[m+'.fields.'+n for short,f in a['fields'].items() if f['suggestion'] for m,n in [short.split('.')]];s.repair_unique_sources(paths,acknowledged=True)
r=s.diagnostic_store()['current'];d=json.loads(r['content']);f=deepcopy(d['main']['fields']['line_spacing']);f['location']='TXT:L2';s.repair_diagnostic('main.fields.line_spacing','candidate',f,'重复原句不猜测：人工选定正文TXT:L2并核对全部规范')
for m,loc in [('main','TXT:L1'),('front','TXT:L14')]:
 i=deepcopy(d[m]['issues'][0]);i.update(fields=[],location=loc);s.repair_diagnostic(m+'.issues.0','issue',i,'用户核对免责声明/未规定说明，和执行字段无关')
s.repair_diagnostic('front.fields.cover_title__font_size','manual',24,'用户最终明确采用24pt，不宣称原文22pt支持24pt')
final_analysis=s.diagnostic_analysis();assert final_analysis['status']=='validated';elapsed=time.perf_counter()-t
(D/'diagnostics.json').write_bytes(s.diagnostic_download());(D/'initial-diagnosis.json').write_bytes(rb.raw(sd.diagnose(initial)));(D/'repaired-diagnosis.json').write_bytes(rb.raw(final_analysis));s.use_diagnostic_draft(acknowledged=True);s.workbench_policy('keep',acknowledged=True);bundle=s.apply_workbench(acknowledged=True);(D/'rule-bundle.json').write_bytes(s.rule_bundle_download());scopes(s);before=deepcopy(s.report);s.set_selection([f['key'] for f in s.eligible()]);assert s.generate(),s.error
out=Path(s.result['output']);(D/'fixed.docx').write_bytes(out.read_bytes());(D/'result.zip').write_bytes(s.result_package());(D/'result.json').write_bytes(rb.raw(s.result));(D/'changes.md').write_text(modification_markdown(s.result));(D/'before.json').write_bytes(rb.raw(before));scope=s.result['output_classification_manifest'];(D/'scope.json').write_bytes(rb.raw(scope));ind=check_document(out,custom_rules_path=D/'rule-bundle.json',mode='academic',classification_manifest=scope);(D/'independent-recheck.json').write_bytes(rb.raw(ind));(D/'independent-recheck.md').write_text(markdown(ind))
old=Path('tests/fixtures/history/phase24/browser-round2.docx');assert out.read_bytes()==old.read_bytes()
a=Package('samples/phase24/combined-errors.docx');b=Package(out)
assert a.root.xpath('//w:t/text()',namespaces=NS)==b.root.xpath('//w:t/text()',namespaces=NS)
assert E.tostring(a.paragraphs[12],method='c14n')==E.tostring(b.paragraphs[12],method='c14n')
assert b.paragraphs[0].find('w:r/w:rPr/w:sz',NS).get(q('val'))=='48'
changed=[n for n in a.parts if a.parts[n]!=b.parts[n]];assert set(changed)=={'word/document.xml','word/footnotes.xml','word/endnotes.xml'}
for part in ('word/footnotes.xml','word/endnotes.xml'):
 x=E.fromstring(a.parts[part]);y=E.fromstring(b.parts[part]);assert x.xpath('//w:t/text()',namespaces=NS)==y.xpath('//w:t/text()',namespaces=NS);assert x.xpath('//@w:id',namespaces=NS)==y.xpath('//@w:id',namespaces=NS)
for m,ss in bundle['provenance'].items():
 for n,src in ss.items():
  if sd.diagnose(initial)['fields'][m+'.'+n]['raw'] is not None:assert src['kind']=='user_confirmed'
# Independent inspection of ZIP: exact current DOCX/config, no diagnostics or original paper in reusable rule bundle.
with zipfile.ZipFile(D/'result.zip') as z:
 assert z.read('fixed.docx')==out.read_bytes();assert z.read('rule-bundle.json')==(D/'rule-bundle.json').read_bytes();assert not any('diagnos' in n for n in z.namelist())
 assert b'"content"' not in z.read('rule-bundle.json') and b'/Volumes/' not in z.read('rule-bundle.json')
# Warm local diagnosis, 3 samples, no API/network/rendering.
times=[]
for _ in range(3):
 t=time.perf_counter();sd.diagnose(initial);times.append(round(time.perf_counter()-t,4))
summary={'fixture':'synthetic equivalent; old input hash not verified','initial':sd.diagnose(initial)['summary'],'final':final_analysis['summary'],'new_api_requests':0,'source_mappings':len(paths),'individual_source_repairs':1,'issue_repairs':2,'manual_value_repairs':1,'local_program_repair_seconds':round(elapsed,4),'warm_diagnosis_seconds':times,'median_diagnosis_seconds':statistics.median(times),'output_equals_phase24_bytes':True,'docx_sha256':sha256(out.read_bytes()),'changed_parts':changed,'summary':ind['summary'],'selected_changes':len(s.result['changes']),'reusable_bundle_has_diagnostics':False,'visual':'Byte-identical to Stage24 Word/4-page render evidence; no new renderer or Word validation claimed.'}
(D/'independent-summary.json').write_bytes(rb.raw(summary));print(summary)

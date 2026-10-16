"""Local bounded parsing/checking median; no API, browser or renderer."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys,json,time,statistics,argparse,platform
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.citation_syntax import parse,GROUPS
from scripts.reproduce_citation_groups_demo import session
from core import check_document

def measure():
 out={'python':platform.python_version(),'platform':platform.system(),'repeats':3,'unit':'seconds','API_requests':0,'cases':{}}
 for label,raw in [('ordinary','[1-3,5]'),('limit100','[1-100]'),('overlap_rejected','[1-60,1-60]'),('huge_rejected','['+'9'*100000+']'),('descending','[99999-1]')]:
  runs=[]
  for _ in range(3):
   start=time.perf_counter()
   for i in range(1000):p=parse(raw,GROUPS)
   runs.append((time.perf_counter()-start)/1000)
  out['cases'][label]={'characters':len(raw),'supported':p['supported'],'expanded_members':len(p['numbers']),'runs':runs,'median':statistics.median(runs),'reason':p['reason']}
 with TemporaryDirectory() as td:
  s=session(Path(td)/'web');runs=[]
  for _ in range(3):
   start=time.perf_counter();r=check_document(s.input_path,s.confirmed,**s._rules_arguments());runs.append(time.perf_counter()-start)
  out['full_synthetic_check']={'runs':runs,'median':statistics.median(runs),'groups':r['citations']['counts']}
  from lxml import etree as E
  from copy import deepcopy
  from core.citations import make_scope,upgrade_template,CONFIG,inventory
  from core.package import Package,q
  out['group_checks']={}
  for name,raw in [('ordinary','[1-3,5]'),('limit100','[1-100]'),('rejected','[1-100,1]')]:
   pkg=Package(s.input_path);p=pkg.paragraphs[2]
   for child in list(p.findall(q('r'))):p.remove(child)
   E.SubElement(E.SubElement(p,q('r')),q('t')).text=raw
   file=Path(td)/(name+'.docx');file.write_bytes(pkg.bytes(True));pkg=Package(file);scope=make_scope(pkg,[3]);scope.update(template=upgrade_template(CONFIG),confirmed=True);scope['objects']={r['id']:'citation' for r in inventory(pkg,[3],scope['template'])['objects']}
   manifest=deepcopy(s._rules_arguments()['classification_manifest']);manifest.update(input_sha256=pkg.hash,citation_scope=scope)
   runs=[]
   for _ in range(3):
    start=time.perf_counter();report=check_document(file,mode='academic',classification_manifest=manifest);runs.append(time.perf_counter()-start)
   out['group_checks'][name]={'runs':runs,'median':statistics.median(runs),'counts':report['citations']['counts'],'scope':'单组局部范围，对应不完整则待复核'}
  from core.package import Package,q
  pkg=Package(s.input_path);p=pkg.paragraphs[2]
  for child in list(p.findall(q('r'))):p.remove(child)
  rr=E.SubElement(p,q('r'));E.SubElement(rr,q('t')).text=' '.join(['[1-100]']*500)
  path=Path(td)/'500-groups.docx';path.write_bytes(pkg.bytes(True));runs=[]
  from core.citations import inventory,upgrade_template,CONFIG
  for _ in range(3):
   start=time.perf_counter();rows=inventory(path,[3],upgrade_template(CONFIG))['objects'];runs.append(time.perf_counter()-start)
  out['500_limit_groups_inventory']={'runs':runs,'median':statistics.median(runs),'groups':len(rows),'expanded_members':sum(len(x['numbers']) for x in rows),'note':'库存/有效格式读取耗时，不是浏览器整页响应；每组上限不因重复绕过'}
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=measure();Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2))

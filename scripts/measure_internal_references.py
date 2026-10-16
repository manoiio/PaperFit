"""Local index and repeated O(1) lookups. No network/AI/renderer."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys,json,time,statistics,argparse,platform
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.package import Package,q
from core.internal_refs import inventory,resolve_target
from scripts.build_internal_reference_sample import write_parts,bookmark,link
from lxml import etree as E
S=Path(__file__).resolve().parents[1]/'samples/phase32'
def run(output):
 records=[]
 with TemporaryDirectory() as t:
  p=Package(S/'errors.docx');body=p.root.find(q('body'))
  for i in range(1000):
   par=E.Element(q('p'));r=E.SubElement(par,q('r'));E.SubElement(r,q('t')).text='合成负载';bookmark(par,'Load_'+str(i),100+i);par.append(link('Load_'+str(i),'相同显示文字'));body.insert(len(body)-1,par)
  p.parts['word/document.xml']=E.tostring(p.root);load=Path(t)/'load.docx';write_parts(load,p.parts)
  for label,path in [('small',S/'errors.docx'),('1000_extra_targets',load)]:
   trials=[]
   for _ in range(3):
    pkg=Package(path);start=time.perf_counter();d=inventory(pkg);cold=time.perf_counter()-start;start=time.perf_counter()
    for i in range(10000):resolve_target(pkg,'_TocTarget')
    hot=time.perf_counter()-start;trials.append({'index_seconds':cold,'10000_lookup_seconds':hot})
   records.append({'kind':label,'bytes':path.stat().st_size,'paragraphs':len(pkg.paragraphs),'bookmarks':len(d['bookmarks']),'reference_positions':len(d['references']),'trials':trials,'median_index_seconds':statistics.median(x['index_seconds'] for x in trials),'median_10000_lookup_seconds':statistics.median(x['10000_lookup_seconds'] for x in trials)})
 result={'environment':{'os':platform.system(),'python':platform.python_version()},'measurements':records,'scope':'本地函数，不是浏览器等待；每组3次，首次索引与重复查询分别计时','api_requests':0,'automatic_renders':0}
 Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);print(json.dumps(run(p.parse_args().output),ensure_ascii=False))

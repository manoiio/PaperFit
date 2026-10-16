"""R23: confirmed top-level tables, actual XML cells, read-only inheritance and surgical edits."""
from pathlib import Path
from copy import deepcopy
import json
from .package import Package,DemoError,q,NS,sha256
from .formats import Resolver,Unresolved,scripts,same_font,paragraph_unsafe

PATH=Path(__file__).resolve().parents[1]/'rules/scut_2015_tables.json'
TYPES={'content':'论文内容表格','cover':'封面或表单表格','other':'其他表格','pending':'待确认表格'}
def load_policy(raw=None):
 data=json.loads(PATH.read_bytes() if raw is None else raw)
 if type(data) is not dict or set(data)!={'version','name','font_cn','font_size','source'} or data['font_cn']!='宋体' or type(data['font_size']) not in (int,float) or data['font_size']!=10.5 or type(data['source']) is not dict or data['source'].get('physical_page')!=18 or data['source'].get('quote')!='插图（表）的标题和文字：五号，宋体。':raise DemoError('固定插表演示规则与已核对原文不一致；自定义须使用确认模板')
 return data

def tables(pkg):return pkg.root.find(q('body')).findall(q('tbl'))
def unlisted_tables(pkg):
 body=pkg.root.find(q('body'));top=set(tables(pkg));rows=[]
 for t in body.findall('.//'+q('tbl')):
  if t in top or any(a.tag==q('tbl') for a in t.iterancestors()):continue
  obj=next((a for a in t.iterancestors() if a.getparent() is body),None)
  rows.append({'body_object':list(body).index(obj)+1 if obj is not None else 0,'unlisted_table':len(rows)+1})
 return rows

def text(e):return ''.join(e.xpath('.//w:t/text()',namespaces=NS))
def inventory(input_path):
 pkg=Package(input_path);children=list(pkg.root.find(q('body')))
 from .widths import _sections
 try:mapping=_sections(pkg)
 except Unresolved:mapping={}
 rows=[]
 for n,t in enumerate(tables(pkg),1):
  rows.append({'index':n,'body_object':children.index(t)+1,'section':mapping[t][0] if t in mapping else None, 'rows':len(t.findall(q('tr'))),'columns':len(t.findall('w:tblGrid/w:gridCol',NS)),'nested':bool(t.findall('.//'+q('tbl'))),'merged':bool(t.xpath('.//w:gridSpan|.//w:vMerge|.//w:hMerge',namespaces=NS)),'text':text(t)[:100]})
 return {'input_sha256':pkg.hash,'tables':rows,'unlisted_tables':unlisted_tables(pkg),'indexing':'主文档顶层w:tbl独立编号；实际XML单元格，不展开合并单元格；不含嵌套表格编号'}

def validate_scope(pkg,scope,*,confirmed=True):
 if isinstance(scope,(str,Path)):
  try:scope=json.loads(Path(scope).read_text())
  except (OSError,ValueError):raise DemoError('表格范围不可读取') from None
 if type(scope) is not dict or set(scope)-{'layout_options'}!={'input_sha256','table_types','confirmed','confirmation'}:raise DemoError('表格范围结构无效')
 if scope['input_sha256']!=pkg.hash:raise DemoError('表格范围哈希不匹配，请重新核对')
 if type(scope['confirmed']) is not bool or (confirmed and scope['confirmed'] is not True) or type(scope['confirmation']) is not str or not scope['confirmation'].strip():raise DemoError('表格范围尚未明确确认')
 types=scope['table_types']
 if type(types) is not dict or set(types)!={str(i) for i in range(1,len(tables(pkg))+1)} or any(type(v) is not str or v not in TYPES for v in types.values()):raise DemoError('表格类型须完整覆盖稳定表格编号')
 if 'layout_options' in scope:
  from .table_edges import validate_options
  validate_options(pkg,scope['layout_options'],types)
 return deepcopy(scope)

def rebind(manifest,hash_):
 if manifest and manifest.get('caption_scope'):manifest['caption_scope']['input_sha256']=hash_
 if manifest and manifest.get('table_scope'):manifest['table_scope']['input_sha256']=hash_
 if manifest and manifest.get('front_scope'):manifest['front_scope']['input_sha256']=hash_
 if manifest and manifest.get('toc_scope'):manifest['toc_scope']['input_sha256']=hash_
 if manifest and manifest.get('reference_scope'):manifest['reference_scope']['input_sha256']=hash_
 if manifest and manifest.get('note_scope'):manifest['note_scope']['input_sha256']=hash_
 if manifest and manifest.get('citation_scope'):manifest['citation_scope']['input_sha256']=hash_
 return manifest

def _table_layers(res,t):
 styles=t.findall('w:tblPr/w:tblStyle',NS)
 if len(styles)>1:raise Unresolved('重复表格样式引用')
 if not styles and 'table' in res.conflicting_defaults:raise Unresolved('重复默认表格样式')
 ident=styles[0].get(q('val')) if styles else res.default_styles.get('table')
 chain=res.chain(ident,'table');layers=[];conditions=[]
 for s in chain:
  if len(s.findall(q('rPr')))>1:raise Unresolved('表格样式重复文字格式')
  if s.find(q('rPr')) is not None:layers.append(s.find(q('rPr')))
  for layer in [s.find(q('rPr')),*[c.find(q('rPr')) for c in s.findall(q('tblStylePr'))]]:
   if layer is not None and any(len(layer.findall(q(tag)))>1 for tag in ('rFonts','sz','lang','vertAlign')):raise Unresolved('表格样式重复文字属性，无法解析')
  for c in s.findall(q('tblStylePr')):
   if c.get(q('type'))=='wholeTable':
    if c.find(q('rPr')) is not None:layers.append(c.find(q('rPr')))
   elif c.find(q('rPr')) is not None:conditions.append(c)
 return layers,conditions

def _layers(res,t,p,r,prop):
 regular=res.layers(p,r);tl,conditions=_table_layers(res,t)
 # Font/size conditions are not guessed from row/column position or tblLook.
 direct=r.find(q('rPr'));tag='rFonts' if prop=='font_cn' else 'sz'
 explicit=direct is not None and direct.find(q(tag)) is not None
 if prop=='font_cn':explicit=explicit and any(direct.find(q(tag)).get(q(a)) is not None for a in ('eastAsia','eastAsiaTheme'))
 if any(c.xpath('.//w:vertAlign|.//w:cs|.//w:rtl|.//w:vanish|.//w:position|.//w:rPrChange',namespaces=NS) for c in conditions):raise Unresolved('条件样式可能影响特殊文字保护，不能视为普通片段')
 if not explicit and any(c.find('w:rPr/w:'+tag,NS) is not None for c in conditions):raise Unresolved('表格首行/分带等条件文字格式无法唯一确定；不以Normal替代')
 # Explicit paragraph/character/run formatting follows table styles; document defaults precede it.
 split=1 if regular and regular[0].getparent() is not None and regular[0].getparent().tag==q('rPrDefault') else 0
 if not explicit and tl and p.find('w:pPr/w:pStyle',NS) is None:
  default=[x for x in regular[split:] if x.getparent() is not None and x.getparent().tag==q('style') and x.getparent().get(q('type'))=='paragraph']
  if any(x.find(q(tag)) is not None for x in default) and any(x.find(q(tag)) is not None for x in tl):raise Unresolved('默认段落格式与表格文字样式同时指定；Word特殊优先关系本轮保守待复核')
 return regular[:split]+tl+regular[split:]

def requirements(rules):
 school=rules.get('table_policy') or load_policy();custom=rules.get('table_config')
 values=custom['values'] if custom else {'font_cn':None,'font_size':None} if 'kind' in rules else {k:school[k] for k in ('font_cn','font_size')}
 sources=custom['sources'] if custom else {k:school['source'] for k in values}
 return {'policy':deepcopy(school),'values':deepcopy(values),'sources':deepcopy(sources)}

def append_checks(report,pkg,scope,rules):
 scope=validate_scope(pkg,scope);settings=requirements(rules);school=settings['policy'];values=settings['values'];sources=settings['sources']
 fs=report['findings'];notes=report['coverage_notes'];res=Resolver(pkg);checked=0
 report['coverage']['table_scope']=scope;report['coverage']['excluded']=report['coverage'].get('excluded','').replace('表格内格式、','未确认表格及非普通文字、');report['coverage']['table_unchecked']={n:TYPES[t] for n,t in scope['table_types'].items() if t!='content'};report['coverage']['table_text_scope']='仅已确认论文内容表格实际XML单元格普通文字；西文槽位、段落属性及嵌套对象未套正文要求。'
 report['coverage']['table_disabled_properties']=[k for k,v in values.items() if v is None]
 def add(loc,prop,actual,status,detail='',safe=True):
  cfg=values.get(prop);key='R23:'+':'.join(f'{k}={v}' for k,v in {**loc,'property':prop}.items())
  f={'key':key,'rule_id':'R23','rule_name':'论文内容表格普通文字 · '+('中文字体' if prop=='font_cn' else '字号' if prop=='font_size' else '支持边界'),'object_type':'table_content','locator':{**loc,'property':prop},'actual':actual,'expected':cfg,'status':status,'fixable':status=='problem' and safe and not pkg.signed and not pkg.ambiguous_sections,'source':deepcopy(sources.get(prop,school['source'])),'detail':detail,'property':prop};fs.append(f);return f
 for n,t in enumerate(tables(pkg),1):
  if scope['table_types'][str(n)]!='content' or all(v is None for v in values.values()):continue
  if t.xpath('.//w:tbl|.//w:ins|.//w:del|.//w:sdt|.//w:customXml|.//w:tblPrChange|.//w:trPrChange|.//w:tcPrChange|.//w:tblPrEx|.//w:tblpPr',namespaces=NS) or any(c.tag not in (q('tblPr'),q('tblGrid'),q('tr')) for c in t):
   add({'table':n},'structure',{'unresolved':'嵌套、浮动、修订或复杂表格'},'review','整表文字未强制统一；请在Word核对',False);continue
  for rn,row in enumerate(t.findall(q('tr')),1):
   for cn,cell in enumerate(row.findall(q('tc')),1):
    vm=cell.find('w:tcPr/w:vMerge',NS)
    if vm is not None and (vm.get(q('val'),'continue') not in ('continue','restart') or (vm.get(q('val'),'continue')=='continue' and text(cell).strip())):
     add({'table':n,'row':rn,'cell':cn},'structure',None,'review','纵向合并续格带文字或属性异常；不能当作独立可见单元格重复处理',False);continue
    if any(x.tag not in (q('tcPr'),q('p')) for x in cell):add({'table':n,'row':rn,'cell':cn},'structure',None,'review','复杂单元格未检查',False);continue
    for pn,p in enumerate(cell.findall(q('p')),1):
     loc={'table':n,'row':rn,'cell':cn,'cell_paragraph':pn};reason='重复段落格式容器，不能确定有效格式' if len(p.findall(q('pPr')))>1 else paragraph_unsafe(p)
     if reason:add(loc,'structure',None,'review',reason+'；该单元格段落未改',False);continue
     for ri,r in enumerate(p.findall(q('r')),1):
      if not text(r).strip():continue
      rl={**loc,'run':ri}
      try:
       regular=res.layers(p,r);special='重复字符格式容器，不能确定有效格式' if len(r.findall(q('rPr')))>1 else res.special(r,regular)
      except Unresolved as exc:special=str(exc)
      if special:notes.append({'locator':rl,'status':'review','detail':special+'；表格特殊文字未检查、未修正'});continue
      checked+=1;cn_text,_,unknown=scripts(text(r))
      for prop,target in values.items():
       if target is None or (prop=='font_cn' and not cn_text):continue
       try:
        layers=_layers(res,t,p,r,prop)
        special=res.special(r,layers)
        if special:raise Unresolved(special+'；继承的特殊文字不能自动统一')
        if prop=='font_cn':
         evidence=res.font_info(layers,'eastAsia',text(r));actual=evidence['font']
         if actual is None:raise Unresolved(evidence['reason'])
         f=add(rl,prop,{'eastAsia':actual},'pass' if same_font(actual,target) else 'problem',safe=evidence['safe_to_fix_slot']);f['font_evidence']={'eastAsia':evidence};f['excerpt']=text(r)[:48]
        else:
         actual=res.size(layers)
         if actual is None:raise Unresolved('表内普通字号缺失或无效，不补默认')
         add(rl,prop,{'pt':actual},'pass' if actual==target else 'problem')['excerpt']=text(r)[:48]
       except Unresolved as exc:add(rl,prop,{'unresolved':str(exc)},'review',str(exc),False)
      if unknown:notes.append({'locator':rl,'status':'review','detail':'表格含未支持文字槽位；普通字号检查不证明其字体可判定'})
 report['coverage']['unlisted_table_objects']=unlisted_tables(pkg)
 if any(v is not None for v in values.values()):
  for loc in report['coverage']['unlisted_table_objects']:notes.append({'locator':loc,'status':'review','detail':'非顶层包裹或文本框表格未列入可确认清单；其文字未检查、未修正，请人工复核。'})
 report['coverage']['table_ordinary_runs_checked']=checked
 if not any(f['rule_id']=='R23' for f in fs):add({'document':1},'structure',None,'not_applicable','未选论文内容表格、无普通文字或受支持字段未启用',False)
 report['summary']['rule_count']+=1
 for state,name in [('problem','problem_count'),('pass','pass_count'),('not_applicable','not_applicable_count'),('review','review_findings')]:report['summary'][name]=sum(f['status']==state for f in fs)
 report['summary']['review_notes']=len(notes);report['summary']['review_count']=report['summary']['review_findings']+len(notes)
 report['summary']['applicable_rule_count']=len({f['rule_id'] for f in fs if f['status']!='not_applicable'})
 report['summary']['conclusion']='已覆盖检查发现问题' if report['summary']['problem_count'] else '已覆盖检查未发现问题'
 report['rules']['table_rules']={'version':school['version'],'sha256':rules.get('table_policy_sha256',sha256(PATH.read_bytes())),'values':values,'sources':sources}

def locate(root,loc):
 t=root.find(q('body')).findall(q('tbl'))[loc['table']-1];cell=t.findall(q('tr'))[loc['row']-1].findall(q('tc'))[loc['cell']-1]
 p=cell.findall(q('p'))[loc['cell_paragraph']-1];return p.findall(q('r'))[loc['run']-1]
def apply(pkg,f):
 from .engine import _ensure
 rp=_ensure(locate(pkg.root,f['locator']),'rPr')
 if f['property']=='font_cn':
  e=_ensure(rp,'rFonts');e.set(q('eastAsia'),f['expected']);e.attrib.pop(q('eastAsiaTheme'),None)
 else:_ensure(rp,'sz').set(q('val'),str(round(f['expected']*2)))
def mask(root,f):
 r=locate(root,f['locator']);e=r.find('w:rPr/w:'+('rFonts' if f['property']=='font_cn' else 'sz'),NS)
 if e is not None:
  for a in ('eastAsia','eastAsiaTheme') if f['property']=='font_cn' else ('val',):e.attrib.pop(q(a),None)

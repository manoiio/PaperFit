"""Opt-in R35 outer edges and L04 header intent. Never edits styles or table data."""
from copy import deepcopy
from lxml import etree as ET
from .package import q, NS, DemoError,sha256
import json
from .formats import Resolver, Unresolved
from .table_text import tables, text

SOURCE={'file':'本科毕业设计论文.pdf','label':'2015学校材料与产品对象解释','physical_page':18,'quote':'表格不加左、右列线','interpretation':'本演示仅将左右外侧边框作为检查对象；不要求删除内部竖线或改成三线表。'}
LIMIT='重复表头是独立阅读辅助，不补续表题注、编号或（续）；属性不证明实际重复，须在具体渲染环境查看。'

def validate_options(pkg, options, types):
 if type(options) is not dict or set(options)!={'version','outer_edges','headers'} or type(options['version']) is not int or options['version']!=1 or type(options['outer_edges']) is not bool or type(options['headers']) is not dict:raise DemoError('表格边框/表头补充配置结构无效')
 for ident,count in options['headers'].items():
  if type(ident) is not str or ident not in types or types[ident]!='content' or type(count) is not int or not 1<=count<len(tables(pkg)[int(ident)-1].findall(q('tr'))):raise DemoError('表头须为内容表格从首行开始的连续行，且保留数据行')
 return deepcopy(options)

def style_layers(pkg,t):
 res=Resolver(pkg);refs=t.findall('w:tblPr/w:tblStyle',NS)
 if len(refs)>1 or not refs and 'table' in res.conflicting_defaults:raise Unresolved('表格样式引用重复或默认样式冲突')
 chain=res.chain(refs[0].get(q('val')) if refs else res.default_styles.get('table'),'table');out=[]
 for s in chain:
  ident=s.get(q('styleId'))
  if len(s.findall(q('basedOn')))>1 or s.xpath('./w:link|./w:styleLink|./w:numStyleLink',namespaces=NS) or len(s.xpath('./w:tblStylePr[@w:type="wholeTable"]',namespaces=NS))>1:raise Unresolved('表格样式链接、重复basedOn或wholeTable冲突，待复核')
  for tag in ('tblPr','tcPr','trPr'):
   if len(s.findall(q(tag)))>1:raise Unresolved('样式存在重复属性容器')
  if s.xpath('.//w:tblpPr|.//w:tblPrChange|.//w:tcPrChange|.//w:trPrChange|.//w:tblPrEx|.//w:gridSpan|.//w:vMerge|.//w:hMerge|.//w:bidiVisual|.//w:textDirection|.//w:tblCellSpacing',namespaces=NS):raise Unresolved('样式含方向、间距、合并或浮动设置，本轮不解析其呈现')
  out.append((f'表格样式 {ident}',s))
  for c in s.findall(q('tblStylePr')):
   if c.get(q('type'))=='wholeTable':out.append((f'样式 {ident}/wholeTable',c))
   elif c.xpath('.//w:tblBorders|.//w:tcBorders|.//w:bidiVisual|.//w:tblCellSpacing|.//w:textDirection|.//w:tblHeader',namespaces=NS):raise Unresolved('条件表格样式影响边框/方向/重复表头，当前不解析其条件优先级')
 return out

def structural(pkg,t,*,headers=False,count=0):
 if pkg.signed or pkg.ambiguous_sections:raise Unresolved('数字签名或分节不明，不支持此辅助')
 if any(x.tag not in (q('tblPr'),q('tblGrid'),q('tr')) for x in t) or len(t.findall(q('tblPr')))>1 or len(t.findall(q('tblGrid')))!=1:raise Unresolved('表格属性或网格结构不明确')
 if t.xpath('.//w:tbl|.//w:tblpPr|.//w:ins|.//w:del|.//w:sdt|.//w:customXml|.//w:tblPrChange|.//w:trPrChange|.//w:tcPrChange|.//w:tblPrEx|.//w:cellIns|.//w:cellDel|.//w:cellMerge',namespaces=NS):raise Unresolved('嵌套、浮动、修订或表格行例外属性，不能安全确定影响范围')
 rows=t.findall(q('tr'));cols=len(t.findall('w:tblGrid/w:gridCol',NS))
 if not rows or cols<1:raise Unresolved('空表格或网格缺失')
 for row in rows:
  if any(x.tag not in (q('trPr'),q('tc')) for x in row) or len(row.findall(q('trPr')))>1:raise Unresolved('复杂表格行或重复行属性')
  cells=row.findall(q('tc'))
  if len(cells)!=cols or row.xpath('./w:trPr/w:gridBefore|./w:trPr/w:gridAfter',namespaces=NS):raise Unresolved('网格不规则或横向合并，本轮不自动处理')
  for c in cells:
   if len(c.findall(q('tcPr')))>1 or any(x.tag not in (q('tcPr'),q('p')) for x in c):raise Unresolved('复杂单元格结构')
   if c.xpath('./w:tcPr/w:gridSpan|./w:tcPr/w:hMerge',namespaces=NS):raise Unresolved('合并网格不能安全确定外侧')
   if c.find('w:tcPr/w:vMerge',NS) is not None:raise Unresolved('纵向合并可能跨表头/数据边界，本轮待复核')
   for tag in ('tcBorders','textDirection'):
    if len(c.findall('w:tcPr/w:'+tag,NS))>1:raise Unresolved('单元格重复边框或方向')
 if headers:
  if not 1<=count<len(rows):raise Unresolved('表头必须从首行连续选择，并保留数据行')
  if t.xpath('.//w:br[@w:type="page" or @w:type="column"]|.//w:pPr/w:sectPr|.//w:fldChar|.//w:fldSimple|.//w:pict|.//w:drawing|.//w:hyperlink|.//w:altChunk',namespaces=NS):raise Unresolved('表格含强制分页、域或复杂对象；不设置重复表头')
 return rows

def _one(parent,path):
 es=parent.findall(path,NS)
 if len(es)>1:raise Unresolved('重复边框/方向/间距属性')
 return es[0] if es else None

def _environment(pkg,t):
 layers=style_layers(pkg,t);pr=t.find(q('tblPr'));props=[(label,s.find(q('tblPr'))) for label,s in layers]+[('表格直接格式',pr)]
 for label,p in props:
  if p is None:continue
  direction=_one(p,'w:bidiVisual')
  if direction is not None and direction.get(q('val'),'1') not in ('0','false','off'):raise Unresolved('右到左或未知表格方向，left/right与start/end映射待复核')
  spacing=_one(p,'w:tblCellSpacing')
  if spacing is not None and (spacing.get(q('type'),'dxa')!='dxa' or spacing.get(q('w')) not in ('0',)):raise Unresolved('非零或不明单元格间距会改变边框冲突规则，待复核')
 for row in t.findall(q('tr')):
  if row.find('w:trPr/w:tblCellSpacing',NS) is not None:raise Unresolved('行级单元格间距例外，待复核')
 for c in t.findall('w:tr/w:tc',NS):
  d=c.find('w:tcPr/w:textDirection',NS)
  if d is not None and d.get(q('val'))!='lrTb':raise Unresolved('不支持的单元格文字方向，待复核')
 return layers

def border(container,side):
 if container is None:return None
 logical={'left':'start','right':'end'}[side];physical=_one(container,'w:'+side);relative=_one(container,'w:'+logical)
 if physical is not None and relative is not None and dict(physical.attrib)!=dict(relative.attrib):raise Unresolved('left/right与start/end定义冲突')
 e=relative if relative is not None else physical
 if e is None:return None
 if len(e) or set(e.attrib)-{q(a) for a in ('val','sz','space','color','themeColor','themeTint','themeShade','shadow','frame')}:raise Unresolved('边框含未知执行属性')
 val=e.get(q('val'))
 if val not in ('nil','none','single','double','dotted','dashed','dashSmallGap','dotDash','dotDotDash','triple','thick','wave','doubleWave','thinThickSmallGap','thickThinSmallGap','thinThickThinSmallGap','thinThickMediumGap','thickThinMediumGap','thinThickThinMediumGap','thinThickLargeGap','thickThinLargeGap','thinThickThinLargeGap','dashDotStroked','threeDEmboss','threeDEngrave','outset','inset'):raise Unresolved('边框值缺失或不支持')
 return {'value':val,'attributes':{ET.QName(k).localname:v for k,v in e.attrib.items()},'tag':ET.QName(e).localname,'both_aliases':physical is not None and relative is not None,'visible':val not in ('nil','none')}

def _inherit(old,new):
 if old and new and old['tag']!=new['tag'] and old['value']!=new['value'] and not new['both_aliases']:raise Unresolved('物理边框与逻辑边框跨继承层冲突，不能唯一判断覆盖优先级')
 return new

def evidence(pkg,t,side):
 rows=structural(pkg,t);layers=_environment(pkg,t);table=None;cell_style=None
 for label,s in layers:
  for path,kind in [('w:tblPr/w:tblBorders','table'),('w:tcPr/w:tcBorders','cell')]:
   v=border(_one(s,path),side)
   if v is not None:
    v['source']=label+'/'+path
    if kind=='table':table=_inherit(table,v)
    else:cell_style=_inherit(cell_style,v)
 v=border(_one(t,'w:tblPr/w:tblBorders'),side)
 if v is not None:v['source']='表格直接tblBorders';table=_inherit(table,v)
 edges=[]
 for n,row in enumerate(rows,1):
  cells=row.findall(q('tc'));idx=0 if side=='left' else len(cells)-1;c=cells[idx]
  cv=border(_one(c,'w:tcPr/w:tcBorders'),side)
  if cv is not None:
   cv=_inherit(cell_style,cv);cv['source']=f'单元格直接tcBorders 行{n}/格{idx+1}'
  else:cv=cell_style
  # A visible cell border takes precedence; no-cell/nil falls back to the table edge.
  effective=cv if cv and cv['visible'] else table if table and table['visible'] else cv or table
  edges.append({'row':n,'cell':idx+1,'effective':deepcopy(effective) if effective else {'value':'absent','visible':False,'source':'已完整解析的表格样式链与直接边框均未指定'},'cell_border':deepcopy(cv)})
 return {'side':side,'table_border':table,'cells':edges,'visible':any(x['effective']['visible'] for x in edges),'direction':'LTR/default；无方向或间距冲突','interpretation':SOURCE['interpretation']}

def append_checks(report,pkg,scope):
 opts=scope.get('layout_options')
 if not opts or not opts['outer_edges']:return
 fs=report['findings'];added=[]
 for n,t in enumerate(tables(pkg),1):
  if scope['table_types'][str(n)]!='content':continue
  for side in ('left','right'):
   try:actual=evidence(pkg,t,side);status='problem' if actual['visible'] else 'pass';detail='仅检查所选表格外侧；内部竖线未作为校规要求。修正将覆盖该侧表格及所有实际外侧单元格边框。'
   except Unresolved as exc:actual={'unresolved':str(exc)};status='review';detail=str(exc)+'；请在Word核对，当前侧不可自动修正。'
   if status=='problem':
    col=actual['cells'][0]['cell'];detail+=f' 影响范围：表格{n}的{side}及对应逻辑边框；行1–{len(actual["cells"])}，每行实际XML格{col}的同侧边框。顶部、底部、内部线及另一侧不修改。'
   added.append({'key':f'R35:table={n}:side={side}','rule_id':'R35','rule_name':'表格'+('左' if side=='left' else '右')+'外侧边框','object_type':'table_border','locator':{'table':n,'side':side},'actual':actual,'expected':'无外侧边框','status':status,'fixable':status=='problem','source':deepcopy(SOURCE),'detail':detail,'excerpt':text(t)[:48],**({'dependency_note':detail} if status=='problem' else {})})
 if not added:added=[{'key':'R35:not_applicable','rule_id':'R35','rule_name':'表格左右外侧边框','object_type':'table_border','locator':{'document':1},'actual':None,'expected':'无外侧边框','status':'not_applicable','fixable':False,'source':deepcopy(SOURCE),'detail':'未确认论文内容表格'}]
 fs.extend(added);report['summary']['rule_count']+=1
 for status,name in [('problem','problem_count'),('pass','pass_count'),('review','review_findings'),('not_applicable','not_applicable_count')]:report['summary'][name]=sum(f['status']==status for f in fs)
 report['summary']['review_count']=report['summary']['review_findings']+len(report['coverage_notes']);report['summary']['applicable_rule_count']=len({f['rule_id'] for f in fs if f['status']!='not_applicable'})
 report['summary']['conclusion']='已覆盖检查发现问题' if report['summary']['problem_count'] else '已覆盖检查未发现问题'
 report['rules']['table_layout_supplement']={'version':1,'outer_edges':True,'source':deepcopy(SOURCE),'name':'用户明确启用的表格边框/表头演示补充','sha256':sha256(json.dumps(opts,ensure_ascii=False,sort_keys=True).encode())}
 report['coverage']['table_border_scope']='仅明确启用并确认的内容表格左右外侧；0边框问题不代表表格整体合格。'

def patches(t,side):
 yield t,'tblPr','tblBorders'
 for row in t.findall(q('tr')):yield row.findall(q('tc'))[0 if side=='left' else -1],'tcPr','tcBorders'

def apply(pkg,f):
 from .engine import _ensure
 t=tables(pkg)[f['locator']['table']-1];side=f['locator']['side'];evidence(pkg,t,side)
 for obj,pr,container in patches(t,side):
  bs=_ensure(_ensure(obj,pr),container)
  for tag in (side,{'left':'start','right':'end'}[side]):
   e=_ensure(bs,tag)
   # Suppress both aliases for this selected LTR edge, including inherited aliases.
   e.attrib.clear();e.set(q('val'),'nil')

def mask(root,f):
 t=root.find(q('body')).findall(q('tbl'))[f['locator']['table']-1];side=f['locator']['side']
 for obj,pr,container in patches(t,side):
  bs=obj.find('w:'+pr+'/w:'+container,NS)
  if bs is not None:
   for tag in (side,{'left':'start','right':'end'}[side]):
    for e in bs.findall(q(tag)):bs.remove(e)
 prune(root)

def prune(root):
 for e in reversed(list(root.iter())):
  if e.tag in {q(x) for x in ('tblBorders','tcBorders','tblPr','tcPr','trPr')} and not len(e) and not e.attrib and not e.text:e.getparent().remove(e)

def header_value(row):
 es=row.findall('w:trPr/w:tblHeader',NS)
 if len(es)>1 or es and (len(es[0]) or set(es[0].attrib)-{q('val')}):raise Unresolved('重复或复杂tblHeader')
 val=es[0].get(q('val'),'1') if es else '0'
 if val not in ('0','false','off','1','true','on'):raise Unresolved('无法解析tblHeader')
 return val in ('1','true','on')

def header_plan(pkg,t,count):
 rows=structural(pkg,t,headers=True,count=count);layers=style_layers(pkg,t)
 for label,s in layers:
  if s.xpath('.//w:trPr/w:tblHeader',namespaces=NS):raise Unresolved('样式定义重复表头，当前不覆盖样式继承')
 return [{'row':n,'before':header_value(row),'text':text(row)[:64]} for n,row in enumerate(rows,1) if n<=count]

def header_suggestions(pkg,scope):
 out=[]
 for ident,count in scope.get('layout_options',{}).get('headers',{}).items():
  t=tables(pkg)[int(ident)-1];reason=None
  try:plan=header_plan(pkg,t,count)
  except Unresolved as exc:reason=str(exc);plan=[]
  out.append({'id':'L04','key':f'L04:{ident}:{count}','table_position':int(ident),'header_count':count,'header_plan':plan,'label':f'表格{ident} → 从第一行起{count}行重复表头','status':'review' if reason else 'available','reason':reason or '用户已确认连续表头行；只修改所选行tblHeader，不改变长表跨页能力','limitation':LIMIT})
 return out

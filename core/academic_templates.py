"""v4 extends the v3 value/source schema; null explicitly means not enabled."""
from copy import deepcopy
from datetime import datetime,timezone
import re,math,json
from .package import DemoError,sha256
from .academic_rules import FIELDS as EXTRA,PATH,flat_defaults,LABELS,NEW_TYPES,GENERIC_TYPES
from . import templates as old
V4_FIELDS={**old.ALL_FIELDS,**{n:(r,(NEW_TYPES.get(o,o)+' '+LABELS.get(p,p)), 'spacing' if p in ('before','after') else 'bool' if p in ('bold','enabled') or p.endswith('_bold') else 'font' if 'font_cn' in p or 'font_western' in p else 'pt' if 'font_size' in p else 'multiple' if p=='line_spacing' else 'chars' if p=='first_line_indent' else 'alignment') for n,(r,o,p) in EXTRA.items()}}
KINDS={**old.SOURCE_LABELS,'not_enabled':'未启用（未提及或用户明确选择）'}

def finite(v):
 try:return math.isfinite(v)
 except (TypeError,OverflowError):return False

def value(name,value):
 if name not in EXTRA:return old.validate_value(name,value)
 if value is None:return None
 _,obj,prop=EXTRA[name]
 if prop in ('line_spacing','first_line_indent'):
  from .paragraph_values import line,indent
  line(value) if prop=='line_spacing' else indent(value,hanging=obj=='reference_item')
  return deepcopy(value)
 _,obj,prop=EXTRA[name]
 if prop in ('bold','enabled') or prop.endswith('_bold'):
  if type(value) is not bool:raise DemoError('加粗/只读提示开关必须是布尔值')
 elif prop in ('before','after'):
  if type(value) is not dict or set(value)!={'value','unit'} or value['unit'] not in ('pt','lines'):raise DemoError('间距须明确数值及pt/lines单位')
  x=value['value'];limit=72 if value['unit']=='pt' else 3;step=2 if value['unit']=='pt' else 4
  if type(x) not in (int,float) or not finite(x) or not 0<=x<=limit or x*step!=round(x*step):raise DemoError('间距仅支持0–72pt/0.5pt步长或0–3行/0.25行步长')
 elif 'font_cn' in prop:
  if type(value) is not str or value not in old.CN:raise DemoError('中文字体枚举不支持')
 elif 'font_western' in prop:
  if type(value) is not str or value not in old.WEST:raise DemoError('西文字体枚举不支持')
 elif prop=='alignment':
  if type(value) is not str or value not in old.ALIGNMENTS:raise DemoError('对齐枚举不支持')
 else:
  if type(value) not in (float,int) or not finite(value):raise DemoError('格式值须有限数字，拒绝布尔值')
  if 'font_size' in prop and not (8<=value<=(36 if obj.endswith('title') else 24) and value*2==round(value*2)):raise DemoError('字号超范围或不符合0.5pt步长')
  if prop=='line_spacing' and value not in (1,1.25,1.5,2):raise DemoError('只支持指定倍数行距')
  if prop=='first_line_indent' and value not in (0,1,2):raise DemoError('只支持0/1/2字符首行缩进')
 return deepcopy(value)

def default_values(base):return {**old.defaults(base,extended=True),**flat_defaults()}

def base_v3(data):
 base={k:deepcopy(v) for k,v in data.items() if k not in ('academic_base_sha256','academic_compatibility')}
 base['structure_version']=3;base['supported_fields']=list(old.ALL_FIELDS)
 base['final_values']={n:base['final_values'][n] for n in old.ALL_FIELDS};base['field_sources']={n:base['field_sources'][n] for n in old.ALL_FIELDS}
 return base

def make(base_template,values,sources,segments,base,*,name=None):
 base_template=old.validate_template(base_template,base);from_version=base_template['structure_version']
 if base_template['structure_version']==2:base_template=old.upgrade_template(base_template,base)
 data=deepcopy(base_template);data.update(structure_version=4,name=name or data['name'],supported_fields=list(V4_FIELDS),academic_base_sha256=sha256(PATH.read_bytes()),academic_compatibility={'from_version':from_version,'new_fields':'explicit_confirmed_or_disabled'},norm_excerpt=deepcopy(segments))
 data['final_values'].update(deepcopy(values));data['field_sources'].update(deepcopy(sources));data['confirmation']={'method':'local_user','timestamp_utc':datetime.now(timezone.utc).isoformat(),'imported':base_template['confirmation']['imported']}
 return validate(data,base)

def validate(data,base):
 if type(data) is not dict or set(data)!=set(base_v3_keys())|{'academic_base_sha256','academic_compatibility'} or type(data.get('structure_version')) is not int or data.get('structure_version')!=4:raise DemoError('v4模板结构无效或含未知字段')
 if data['supported_fields']!=list(V4_FIELDS) or set(data.get('final_values',{}))!=set(V4_FIELDS) or set(data.get('field_sources',{}))!=set(V4_FIELDS):raise DemoError('v4模板必须列出全部值和来源，包括未启用字段')
 if data['academic_base_sha256']!=sha256(PATH.read_bytes()):raise DemoError('前后置演示基础规则版本已变化，请重新核对')
 compat=data['academic_compatibility']
 if type(compat) is not dict or set(compat)!={'from_version','new_fields'} or type(compat['from_version']) is not int or compat['from_version'] not in (2,3) or compat['new_fields']!='explicit_confirmed_or_disabled':raise DemoError('v4兼容转换信息无效')
 old.validate_template(base_v3(data),base)
 for name in EXTRA:
  v=value(name,data['final_values'][name]);s=data['field_sources'][name]
  if type(s) is not dict or set(s)!={'kind','quote','location'} or type(s['kind']) is not str or s['kind'] not in KINDS:raise DemoError('新增字段来源无效')
  old.safe_text(s['quote'],200,allow_empty=True)
  if v is None:
   if s['kind']!='not_enabled' or s['quote'] or s['location'] is not None:raise DemoError('未启用字段不能伪装成AI提取或学校默认值')
  elif s['kind']=='not_enabled':raise DemoError('未启用字段不得携带执行值')
  elif s['kind']=='default_inherited':
   if v!=flat_defaults()[name] or s['quote'] or s['location'] is not None:raise DemoError('默认继承值不匹配')
  elif s['kind']=='ai_extracted':
   if data['extraction']['kind']=='none':raise DemoError('AI来源缺少解析记录')
   validate_candidate(name,{'value':v,'unit':V4_FIELDS[name][2],'quote':s['quote'],'location':s['location'],'support':'supported'},data['norm_excerpt'])
  elif s['quote'] and not any(s['location']==p['location'] and s['quote'] in p['text'] for p in data['norm_excerpt']):raise DemoError('人工编辑保留的依据不真实')
  elif not s['quote'] and s['location'] is not None:raise DemoError('空依据不能携带位置')
 if len((json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())>64*1024:raise DemoError('v4模板超过64KB，请缩短规范摘录或依据后重新核对；不会导出无法重新载入的模板')
 return deepcopy(data)

def base_v3_keys():return ('structure_version','name','supported_fields','base_sha256','final_values','field_sources','norm_excerpt','norm_file_sha256','confirmation','extension_base_sha256','compatibility','extraction')

def context(obj,prop,quote):
 targets={'abstract_cn_title':r'中文摘要标题','abstract_cn_body':r'中文摘要(?:正文|内容)','abstract_en_title':r'(?:英文摘要标题|Abstract标题)','abstract_en_body':r'(?:英文摘要(?:正文|内容)|Abstract正文)','keywords_cn':r'(?:中文关键词|关键词标签|关键词内容)','keywords_en':r'(?:英文关键词|Keywords)','reference_title':r'参考文献标题','reference_item':r'参考文献(?!(?:标题))(?:条目|正文)?'}
 if obj in targets:
  if obj=='keywords_cn' and re.search('英文|Keywords',quote,re.I):return False
  if not re.search(targets[obj],quote,re.I):return False
 elif obj in GENERIC_TYPES:
  if obj=='body' and (not re.search('正文',quote) or re.search(r'附\s*录|致\s*谢|摘要|关键词|参考文献|标题',quote)):return False
  if obj!='body' and not re.search({'heading1':r'一级标题|标题1(?![.\d])','heading2':r'二级标题|标题2(?![.\d])','heading3':r'三级标题|标题3(?![.\d])','figure_caption':'图题','table_caption':'表题'}[obj],quote):return False
 if prop.startswith('label_') and not re.search('标签|标题|label',quote,re.I):return False
 if prop.startswith('content_') and not re.search('内容|正文|content',quote,re.I):return False
 # Multi-object or label+content clauses cannot prove a single field safely.
 objects=[k for k,pat in targets.items() if re.search(pat,quote,re.I) and not (k=='keywords_cn' and re.search('英文|Keywords',quote,re.I))]
 if obj in targets and any(k!=obj for k in objects):return False
 if prop.startswith('label_') and re.search('内容|content',quote,re.I):return False
 if prop.startswith('content_') and re.search('标签|label',quote,re.I):return False
 return True

def validate_candidate(name,f,segments):
 from .norms import evidence_segments
 if type(f) is dict:segments=evidence_segments(segments,f.get('location'))
 if type(f) is not dict or set(f)!={'value','unit','quote','location','support'} or f['support']!='supported':raise DemoError('新增AI字段结构无效')
 if f['unit']!=V4_FIELDS[name][2]:raise DemoError('字段单位不符，间距使用含单位的value对象')
 old.safe_text(f['quote'],200)
 if not any(p['location']==f['location'] and f['quote'] in p['text'] for p in segments):raise DemoError('AI原文短句或来源位置不存在')
 _,obj,prop=EXTRA[name]
 if name=='content_checks':raise DemoError('内容提示开关须用户明确选择，不由AI自报')
 if re.search('大约|任选|不超过|至多|不要求|未要求|未规定|不作要求|不强制|无要求|不限|可选|无需|不需要',f['quote']) or prop!='line_spacing' and '至少' in f['quote']:raise DemoError('含糊/不支持条款不可作为执行依据')

 if not context(obj,prop,f['quote']):raise DemoError('原文对象或标签/内容范围不明确，不能自动执行')
 v=value(name,f['value']);quote=f['quote']
 if prop in ('line_spacing','first_line_indent'):
  validate_candidate_for(obj,prop,f,segments);return deepcopy(f)
 if len(extracted_values(name,segments))>1:raise DemoError('同一对象属性存在冲突，须保留空值并由用户明确取舍')
 if v is None:raise DemoError('提取记录不能携带空执行值')
 if prop in ('before','after'):
  label='段前' if prop=='before' else '段后';m=re.search(label+r'\s*(\d+(?:\.\d+)?)\s*(pt|磅|行)',quote,re.I)
  if not m or float(m[1])!=v['value'] or ('lines' if m[2]=='行' else 'pt')!=v['unit']:raise DemoError('间距原文数值/单位不匹配，不折算行与磅')
 elif prop.endswith('bold') or prop=='bold':
  if '加粗' not in quote:raise DemoError('原文未要求加粗，不能补成true或false')
  if v is not (not bool(re.search('不加粗|非加粗',quote))):raise DemoError('加粗依据不匹配')
 elif 'font' in prop and 'size' not in prop:
  if old.font_candidates(re.sub(r'中文摘要(?:标题|正文|内容)|英文摘要(?:标题|正文|内容)|(?:中文|英文)?关键词(?:标签|内容)|参考文献(?:标题|条目|正文)|Abstract(?:标题|正文)|Keywords(?:标签|内容)|一级标题|二级标题|三级标题|图题|表题','',quote,flags=re.I),'font_cn' if 'cn' in prop else 'font_western')!={v}:raise DemoError('字体依据不匹配或含未知字体/冲突')
 elif prop=='alignment':
  if old.ALIGNMENTS[v] not in quote:raise DemoError('对齐依据不匹配')
 elif 'font_size' in prop:
  size_quote=re.split(r'段前|段后|行距|缩进|固定|最小|至少',quote)[0]
  nums=[float(n) for n in re.findall(r'(\d+(?:\.\d+)?)\s*(?:pt|磅)',size_quote,re.I)]
  from .spec_validation import FONT_NAMES
  nums += [FONT_NAMES[m.group(0).rstrip('号')] for m in re.finditer(r'小(?:二|三|四|五)(?:号)?|(?:二|三|四|五)号',size_quote)]
  if v not in nums:raise DemoError('字号依据不匹配')
 elif prop=='line_spacing':
  candidates=[float(n) for n in re.findall(r'(\d+(?:\.\d+)?)\s*倍',quote)]
  if '单倍' in quote:candidates.append(1.)
  if '双倍' in quote:candidates.append(2.)
  if v not in candidates:raise DemoError('倍数行距依据不匹配')
 elif prop=='first_line_indent':
  if v not in indent_values(quote):raise DemoError('字符缩进依据不匹配，不把厘米/磅换成字符')
 return deepcopy(f)

def validate_draft(data,segments):
 if type(data) is not dict or set(data)!=set(V4_FIELDS)|{'unsupported'}:raise DemoError('v4草稿字段不完整或含未知执行字段')
 old.validate_draft({**{n:data[n] for n in old.ALL_FIELDS},'unsupported':data['unsupported']},segments)
 for n in EXTRA:
  if data[n] is not None:
   try:validate_candidate(n,data[n],segments)
   except DemoError as exc:raise DemoError(V4_FIELDS[n][1]+'：'+str(exc)) from None
 return deepcopy(data)

def compile(data,base):
 data=validate(data,base);out=old.compile_template(base_v3(data),base);objects={obj:{} for obj in (*GENERIC_TYPES,*NEW_TYPES)};sources={obj:{} for obj in objects}
 for n,(_,obj,prop) in EXTRA.items():
  if obj=='document':continue
  objects[obj][prop]=deepcopy(data['final_values'][n]);s=deepcopy(data['field_sources'][n]);sources[obj][prop]={'file':None,'physical_page':None,'label':KINDS[s['kind']]+'（用户确认v4模板，不冒充学校原文）','quote':s['quote'],'location':s['location'],'kind':s['kind']}
 out.update(name=data['name'],version='template-demo-4.0.0',template_structure_version=4,academic_config={'objects':objects,'sources':sources,'content_checks':data['final_values']['content_checks'] is True});return out


def extracted_values(name,segments):
 _,obj,prop=EXTRA[name];found=[]
 for seg in segments:
  for clause in re.split('[。；;\n]',seg['text']):
   if not context(obj,prop,clause):continue
   if prop in ('before','after'):
    for n,u in re.findall(('段前' if prop=='before' else '段后')+r'\s*(\d+(?:\.\d+)?)\s*(pt|磅|行)',clause,re.I):found.append((float(n),u.lower().replace('磅','pt')))
   elif prop.endswith('bold') or prop=='bold':
    if re.search('加粗',clause):found.append(not bool(re.search('不加粗|非加粗',clause)))
   elif 'font' in prop and 'size' not in prop:
    found.extend(x for x in (old.CN if 'cn' in prop else old.WEST) if x in clause)
   elif prop=='alignment':found.extend(k for k,v in old.ALIGNMENTS.items() if v in clause)
   elif 'font_size' in prop:
    from .spec_validation import FONT_NAMES
    size_clause=re.split(r'段前|段后|行距|缩进|固定|最小|至少',clause)[0]
    found.extend(float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*(?:pt|磅)',size_clause,re.I))
    found.extend(FONT_NAMES[m.group(0).rstrip('号')] for m in re.finditer(r'小(?:二|三|四|五)(?:号)?|(?:二|三|四|五)号',size_clause))
   elif prop=='line_spacing':
    found.extend(float(x) for x in re.findall(r'(\d+(?:\.\d+)?)\s*倍',clause));found.extend([1.] if '单倍' in clause else []);found.extend([2.] if '双倍' in clause else [])
   elif prop=='first_line_indent':found.extend(float(x) for x in indent_values(clause))
 return {str(x) for x in found}


def indent_values(quote):
 out=[];mapping={'零':0,'一':1,'二':2,'两':2}
 for n in re.findall(r'首行(?:缩进|空)?\s*(?:为|：|:)?\s*([012零一二两])\s*(?:个)?(?:字符|汉字|字)',quote):out.append(mapping[n] if n in mapping else int(n))
 if re.search('无首行缩进|首行不缩进',quote):out.append(0)
 return out


def validate_candidate_for(obj,prop,f,segments):
 from .paragraph_values import prove,line,indent
 from .norms import evidence_segments
 if type(f) is not dict or set(f)!={'value','unit','quote','location','support'} or f['support']!='supported' or f['unit']!=('multiple' if prop=='line_spacing' else 'chars'):raise DemoError('段落字段协议不符')
 old.safe_text(f['quote'],200)
 if not any(s['location']==f['location'] and f['quote'] in s['text'] for s in segments) or not context(obj,prop,f['quote']):raise DemoError('段落对象或连续依据不符')
 line(f['value']) if prop=='line_spacing' else indent(f['value'],hanging=obj=='reference_item')
 prove(prop,f['value'],f['quote'],[c for s in evidence_segments(segments,f['location']) for c in re.split('[。；;\n]',s['text']) if context(obj,prop,c)])

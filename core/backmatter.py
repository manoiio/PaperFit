"""Optional appendix/ack roles and configuration; existing academic engine executes patches."""
from pathlib import Path
from copy import deepcopy
import json,re
from .package import DemoError,sha256,q
TYPES={'appendix_title':'附录标题','appendix_text':'附录普通文献文字','ack_title':'致谢标题','ack_text':'致谢普通文字'}
RULE_FOR=dict(zip(TYPES,('R38','R39','R40','R41')))
PROPS=('font_cn','font_western','font_size','alignment','line_spacing','before','after','first_line_indent','bold')
FIELDS={obj+'__'+p:(RULE_FOR[obj],obj,p) for obj in TYPES for p in PROPS}
PATH=Path(__file__).resolve().parents[1]/'rules/scut_2015_backmatter.json'
def school():return json.loads(PATH.read_bytes())
def defaults():return {n:deepcopy(school()['objects'][obj].get(p)) for n,(_,obj,p) in FIELDS.items()}
def activate(rules,classification):
 if rules.get('mode')!='academic' or not classification:return rules
 if not rules.get('back_config') and not set(classification['paragraph_types'].values())&set(TYPES):return rules
 if 'R38' in rules['rules']:return rules
 r=deepcopy(rules);custom=r.get('back_config');raw=PATH.read_bytes();p=school()
 cfg=custom['objects'] if custom else p['objects'] if 'kind' not in r else {o:{} for o in TYPES}
 r['academic_objects'].update(deepcopy(cfg))
 for obj in TYPES:r['rules'][RULE_FOR[obj]]={'name':TYPES[obj]+'格式','expected':deepcopy(cfg[obj]),'page':None,'quote':'按已确认对象及逐属性来源执行；未配置不检查'}
 r['back_sources']=deepcopy(custom['sources']) if custom else None;r['backmatter_sha256']=sha256(raw);r['back_policy']=deepcopy(p)
 return r

def validate_exclusions(pkg,data,types):
 if type(data) is not dict or any(type(n) is not str or n not in types or types[n] not in ('other','pending') or type(v) is not str or not v.strip() or len(v)>120 or any(ord(c)<32 for c in v) for n,v in data.items()):raise DemoError('材料排除必须绑定本文件有效段落、其他/待确认类型和简短原因')
 return deepcopy(data)

def material_hint(t):
 """Existing conservative code/data clue, never a confirmed material type."""
 return bool(re.match(r'^\s*(?:代码|程序|数据|运行(?:结果|输出)|输出)\s*[:：]',t) or (re.match(r'^\s*(?:def\s+\w+\s*\(|class\s+\w+|#include|(?:for|while|if)\s*\(|return\b|print\s*\()',t) and len(re.findall(r'[:;{}()=]',t))>=2) or re.fullmatch(r'[\d.,\-+\s\t]+',t))

def refine(rows,paragraphs=None):
 zone=None
 for r in rows:
  t=(''.join((e.text or '') if e.tag==q('t') else '\t' if e.tag==q('tab') else '' for e in paragraphs[r['index']-1].iter()) if paragraphs is not None else r['text']).strip();compact=re.sub(r'\s','',t)
  toc=bool(re.search(r'(?:\t|\.{3,}|…{2,})\s*[\divxIVX]+\s*$',t) or re.match('TOC',r.get('style_id') or '',re.I))
  if toc:zone=None;continue
  if re.fullmatch(r'附\s*录(?:\s*[A-ZＡ-Ｚ一二三四五六七八九十\d]+)?(?:\s+[^。！？；!?;]{1,50})?',t):
   zone='appendix';r.update(suggested_type='appendix_title',ambiguous=True,reason='独立附录标记/编号候选；须核对，后续材料不自动全当普通文字');continue
  if compact=='致谢':zone='ack';r.update(suggested_type='ack_title',ambiguous=True,reason='独立致谢章节标记；格式默认未配置，须确认');continue
  if r['suggested_type'] in ('heading1','heading2','heading3','reference_title','abstract_cn_title','abstract_en_title') or compact in ('目录','结论','总结'):zone=None;continue
  if zone:
   material=material_hint(t)
   if r['special'] or not t or material:
    r.update(suggested_type='other',ambiguous=True,reason='附录/致谢的特殊或疑似代码数据材料，仅作排除线索；请明确保护，不套普通文字规则');continue
   if len(t)>20 and re.search('[。！？；]',t):r.update(suggested_type='appendix_text' if zone=='appendix' else 'ack_text',ambiguous=True,reason='章节内连续叙述候选；须明确确认普通文字，附录代码/数据/图表排除')
   else:r.update(suggested_type='pending',ambiguous=True,reason='附录/致谢材料用途不明确，不自动当普通文字')

def binding(mode,types,template_version=None):
 # Only the opt-in new roles/config affect legacy state and cache signatures.
 if mode=='academic' and (set(types.values())&set(TYPES) or template_version==6):return (sha256(PATH.read_bytes()),)
 return ()

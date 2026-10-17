"""Deterministic section suggestions, explicit opt-in; never a probability or confirmation."""
import re

def refine(rows):
 zone=None;main=False
 for row in rows:
  value=row['text'].strip();compact=(row.get('marker_name') or re.sub(r'\s','',value)).lower();compact={'中文摘要':'摘要','英文摘要':'abstract'}.get(compact,compact);typ=None;ambiguous=False;reason=''
  if row.get('structure_boundary') and not row.get('section_marker'):
   zone=None;main=True;continue
  if compact=='摘要':zone='cn';main=False;typ='abstract_cn_title';reason='独立摘要章节标记（允许空格），不是正文内提及'
  elif compact=='abstract':zone='en';main=False;typ='abstract_en_title';reason='独立英文摘要章节标记'
  elif compact=='参考文献':zone='refs';main=False;typ='reference_title';reason='独立参考文献章节标记'
  elif compact in ('目录','致谢','附录','结论','总结') or row['suggested_type'].startswith('heading'):
   zone=None
   if compact in ('目录','致谢','附录','结论','总结'):main=False
  elif re.match(r'^关键词\s*[:：]',value):typ='keywords_cn';reason='段首关键词标签及冒号，可核对标签/内容边界';zone='postabstract'
  elif re.match(r'^Key\s*words\s*[:：]',value,re.I):typ='keywords_en';reason='段首英文关键词标签及冒号';zone='postabstract'
  elif zone=='postabstract' and re.fullmatch(r'Heading[123]',row.get('style_id') or '') and len(value)<60 and not re.search('[。！？;；]',value):
   typ='heading'+row['style_id'][-1];reason='摘要/关键词之后的真实标题样式及短文本；须人工核对';zone=None;main=True
  elif main and row['suggested_type'] in ('other','pending') and value and not row['special']:
   if re.fullmatch(r'Heading[123]',row.get('style_id') or '') and len(value)<60 and not re.search('[。！？;；]',value):typ='heading'+row['style_id'][-1];reason='正文区内标题样式及短文本'
   elif len(value)>35 or re.search('[。！？;；]',value):typ='body';reason='已核对章节线索之后的叙述段；数字/单位句子不升级标题'
  elif value and not row['special'] and zone in ('cn','en') and not (row['ambiguous'] and row.get('outline_level') in (0,1,2)):
   typ='abstract_'+zone+'_body';reason='摘要标题之后、关键词/下一节之前的普通段落；需人工核对区域'
  elif value and zone=='refs':
   typ='reference_item';ambiguous=not bool(re.match(r'^[\[［]\d+[\]］]',value));reason='参考文献章节内条目'+('，非[整数]形式，著录/编号需复核' if ambiguous else '，手工编号仅提供只读线索')
  if typ:
   row.update(suggested_type=typ,reason=reason,ambiguous=ambiguous or bool(row['special']))

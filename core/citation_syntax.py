"""Bounded literal grammar. No text normalization, I/O or implicit mode upgrade."""
import re
from .package import DemoError
SINGLE='single-v1'
GROUPS='ascii-groups-v2'
MAX_LENGTH=512
MAX_EXPANDED=100
MAX_NUMBER=99999

def parse(raw,mode=SINGLE):
 if mode not in (SINGLE,GROUPS):raise DemoError('未知引文语法模式')
 result={'raw':raw,'syntax':mode,'supported':False,'members':[],'numbers':[],'unique_numbers':[],'notices':[],'reason':None}
 def reject(reason):result['reason']=reason;return result
 if type(raw) is not str:raise DemoError('引文必须为原始文字')
 if len(raw)>MAX_LENGTH:return reject(f'单组超过{MAX_LENGTH}字符，未展开')
 if mode==SINGLE:
  if not re.fullmatch(r'\[[1-9][0-9]{0,4}\]',raw):return reject('v1仅支持ASCII单整数[1]；组合/区间/全角或异常编号只读')
  n=int(raw[1:-1]);result.update(supported=True,numbers=[n],unique_numbers=[n],members=[{'raw':raw[1:-1],'start':1,'end':len(raw)-1,'kind':'integer','first':n,'last':n}]);return result
 if not raw.startswith('[') or not raw.endswith(']'):return reject('仅支持ASCII方括号')
 tokens=raw[1:-1].split(',');members=[];offset=1;count=0
 for token in tokens:
  m=re.fullmatch(r' *([1-9][0-9]{0,4})(?: *([-–]) *([1-9][0-9]{0,4}))? *',token)
  if not m:return reject('仅支持ASCII逗号、连字符或en dash及普通空格；编号1–99999')
  first=int(m[1]);last=int(m[3]) if m[3] else first
  if last<first:return reject('倒序区间不展开')
  count+=last-first+1
  if count>MAX_EXPANDED:return reject(f'累计展开超过{MAX_EXPANDED}成员（重复和重叠也计入），未展开')
  members.append({'raw':token,'start':offset,'end':offset+len(token),'kind':'range' if m[2] else 'integer','first':first,'last':last,'separator':m[2]});offset+=len(token)+1
 # Expansion occurs only after all members and the cumulative bound have passed.
 numbers=[n for member in members for n in range(member['first'],member['last']+1)]
 unique=list(dict.fromkeys(numbers));duplicates=[n for n in unique if numbers.count(n)>1]
 result.update(supported=True,members=members,numbers=numbers,unique_numbers=unique)
 if duplicates:result['notices'].append({'code':'repeated_or_overlapping','numbers':duplicates,'reason':'重复成员或区间重叠，仅产品核对提示；不改原文、不作为学校格式错误'})
 return result

def position_groups(rows):
 """Members share one position. Prefix continuity is a product interpretation."""
 seen=set();order=[];groups=[];prefix=0;maximum=0
 for r in rows:
  unique=r['unique_numbers'];new=[n for n in unique if n not in seen];old=[n for n in unique if n in seen]
  seen.update(new);order.extend(new)
  if new:maximum=max(maximum,max(new))
  while prefix+1 in seen:prefix+=1
  gap_count=maximum-len(seen)
  groups.append({'citation':r['id'],'paragraph':r['paragraph'],'start':r['start'],'end':r['end'],'raw':r['text'],'raw_numbers':r['numbers'],'first_numbers':new,'previous_numbers':old,'missing_prefix_count':gap_count,'first_missing':prefix+1 if gap_count else None,'earlier_higher_number':maximum if gap_count else None,'risk':bool(new and gap_count),'reason':'同一组不区分内部首次先后；累计首次编号集合有缺口，较大编号先于缺口编号出现' if new and gap_count else '本位置无新增顺序风险'})
 return order,groups

def spans(text,mode=SINGLE):
 """Linear v2 scan keeps nested/malformed outer groups out of executable inner spans."""
 if mode==SINGLE:
  for m in re.finditer(r'[\[［][^\[\]［］\r\n]*[\]］]',text):yield m.start(),m.end(),m[0]
  return
 if mode!=GROUPS:raise DemoError('未知引文语法模式')
 start=None;depth=0
 for i,char in enumerate(text):
  if char in '[［':
   if start is None:start=i
   depth+=1
  elif char in ']］' and start is not None:
   depth-=1
   if depth==0:yield start,i+1,text[start:i+1];start=None
  elif char in '\r\n' and start is not None:
   yield start,i,text[start:i];start=None;depth=0
 if start is not None:yield start,len(text),text[start:]

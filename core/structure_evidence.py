"""Shared structural evidence. Suggestions are not user confirmation or page coordinates."""
import re
VERSION='structure-evidence-1'
def heading(row):
 text=row['text'].strip();level=row.get('number_level');outline=row.get('outline_level');style=row.get('style_id')
 if row.get('special') or row.get('toc_like') or not text or len(text)>60 or re.search('[。！？!?；;]',text):return None
 if not level or re.match(r'^\d+\s*(?:年|月|日|个|项|倍|磅|pt|mm|cm|%)',text,re.I):return None
 if outline==level-1 and style=='Heading'+str(level):return level
 if level==1 and re.match(r'^第[一二三四五六七八九十百零〇\d]+章\s*\S',text) and row.get('narrative_after'):return level
 return None

def index(rows,types=None,*,confirmed=False,excluded=(),approved=()):
 types=types or {str(r['index']):r['suggested_type'] for r in rows};chapters=[];markers=[];conflicts=[]
 for row in rows:
  n=str(row['index']);role=types[n];proof=heading(row)
  if n in excluded:continue
  if role.startswith('heading'):
   if confirmed or n in approved or proof==int(role[-1]):chapters.append({'paragraph':int(n),'role':role,'level':int(role[-1]),'source':'human_confirmed' if confirmed else 'user_decision' if n in approved else 'style_outline_number' if row.get('style_id') else 'chapter_and_context'})
   else:conflicts.append({'paragraph':int(n),'reason':'标题层级/正文边界证据不足'})
  if role.endswith('_title') or row.get('section_marker')=='toc' and role=='other' or re.fullmatch(r'目\s*录',row['text'].strip()):markers.append({'paragraph':int(n),'role':role if role!='other' else 'toc','source':'confirmed' if confirmed else 'independent_marker'})
 body=min((c['paragraph'] for c in chapters if c['level']==1),default=None)
 if body and not confirmed:
  previous=[r for r in rows if r['index']<body and str(r['index']) not in excluded and str(r['index']) not in approved and not r.get('toc_like') and r.get('outline_level')==0 and types[str(r['index'])] in ('pending','heading1') and heading(r) is None]
  if previous:
   conflicts.append({'paragraph':previous[0]['index'],'reason':'可靠章标题之前仍有用途未定的一级标题线索，正文最早起点待核对'});body=None
 starts=sorted({1,*[x['paragraph'] for x in markers],*[c['paragraph'] for c in chapters if c['level']==1]})
 regions=[]
 for i,n in enumerate(starts):
  role=types[str(n)];purpose='body' if body and n>=body and role not in ('reference_title','appendix_title','ack_title') else 'front' if role.startswith('abstract') or any(x['paragraph']==n and x['role']=='toc' for x in markers) else 'other'
  regions.append({'start':n,'end':starts[i+1]-1 if i+1<len(starts) else len(rows),'purpose':purpose,'role':role})
 return {'version':VERSION,'body_start':body,'chapters':chapters,'markers':markers,'regions':regions,'conflicts':conflicts,'physical_pages_computed':False}

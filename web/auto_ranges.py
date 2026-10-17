"""Bounded scope preparation only; original inventory, requirements and validators.
No network, confirmations or document writes. Never an alternate format engine.
"""
from copy import deepcopy
import re
from core.package import Package,q,NS
from core.table_text import tables,inventory as table_inventory,_table_layers
from core.formats import Resolver,Unresolved
from core.notes import inventory as note_inventory,make_scope
from ai.structure import redact,withheld

VERSION='auto-ranges-1'

def decisions(model):
    return {'table':getattr(model,'table_explicit_choice',None),'note':getattr(model,'note_explicit_choice',None),'restored':bool(model.project_notice)}

def prepare(model):
    out={'tables':{},'candidates':[],'protected':[],'notes':None,'note_counts':{},'limits':[]}
    if model.mode!='academic':return out
    pkg=Package(model.input_path);res=Resolver(pkg);body=list(pkg.root.find(q('body')));ti=table_inventory(model.input_path)
    keep_tables=not hasattr(model,'table_explicit_choice') or model.table_enabled or decisions(model)['table'] is not None or bool(model.project_notice) or any(v!='pending' for v in model.table_types.values())
    if keep_tables:
        out['limits'].append('表格沿用已准备/人工决定；恢复任务未证明为新范围时不自动开启。')
    elif not any(v is not None for v in model.table_requirements().values()):
        out['limits'].append('表格文字属性未配置，不补默认要求。')
    else:
        for row,t in zip(ti['tables'],tables(pkg)):
            n=str(row['index']);out['tables'][n]='pending';raw=''.join(t.xpath('.//w:t/text()',namespaces=NS))
            if withheld(raw) or re.search(r'(姓名|学号|身份证|电话|银行卡|密码|密钥|手机号|邮箱)|\b\w+\s*=\s*|\b(?:print|def|class)\s*\(',raw,re.I):
                out['tables'][n]='cover' if re.search('姓名|学号|指导教师',raw) else 'other';out['protected'].append({'id':'t:'+n,'reason':'身份/表单或代码/敏感线索，本地保护，不发送'});continue
            bad=row['nested'] or row['merged'] or bool(t.xpath('.//w:fldChar|.//w:fldSimple|.//w:hyperlink|.//w:sdt|.//w:ins|.//w:del|.//w:drawing|.//w:pict|.//w:tblpPr|.//m:oMath',namespaces={**NS,'m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}))
            for cell in t.findall('.//'+q('tc')):
                if any(c.tag not in (q('tcPr'),q('p')) for c in cell):bad=True
                for para in cell.findall(q('p')):
                    if any(c.tag not in (q('pPr'),q('r')) for c in para):bad=True
                    for run in para.findall(q('r')):
                        if any(c.tag not in (q('rPr'),q('t'),q('tab'),q('br'),q('cr')) for c in run):bad=True
            try:
                _,conditional=_table_layers(res,t)
                if conditional:bad=True
            except Unresolved:bad=True
            if bad:
                out['protected'].append({'id':'t:'+n,'reason':'合并/嵌套/浮动、条件样式或复杂内容，自动范围不放开'});continue
            pos=body.index(t);neighbors=[x for x in body[max(0,pos-12):pos] if x.tag==q('p') and ''.join(x.xpath('.//w:t/text()',namespaces=NS)).strip()][-2:]+[x for x in body[pos+1:pos+5] if x.tag==q('p')][:1]
            context=[redact(''.join(p.xpath('.//w:t/text()',namespaces=NS)),85) if not withheld(''.join(p.xpath('.//w:t/text()',namespaces=NS))) else '[保护片段不发送]' for p in neighbors]
            previous=body[pos-1] if pos else None
            caption=previous is not None and previous.tag==q('p') and re.match(r'^表\s*\d+(?:[-－.]\d+)?\s+\S', ''.join(previous.xpath('.//w:t/text()',namespaces=NS)))
            if caption:
                out['tables'][n]='content';continue
            out['candidates'].append({'id':'t:'+n,'kind':'table','text':redact(raw),'local_role':'pending','local_reason':'普通结构，用途尚未确认',
                'section':row['section'],'rows':row['rows'],'columns':row['columns'],'body_object':row['body_object'],'context':context})
    # Word note container identity is deterministic: never send notes to AI.
    keep_notes=not hasattr(model,'note_explicit_choice') or model.note_enabled or model.note_draft is not None or decisions(model)['note'] is not None or bool(model.project_notice)
    if keep_notes:out['limits'].append('注释沿用人工/既有范围；未重新猜测排除项。')
    else:
        draft=model.seed_workbench_module('notes',make_scope(pkg));ni=note_inventory(pkg)
        draft['objects']=[r['key'] for r in ni['objects'] if r['safe_relationship'] and any(v is not None for v in draft['template']['values'][r['kind']].values())]
        if draft['objects']:out['notes']=draft
        for kind in ('footnote','endnote'):out['note_counts'][kind]=sum(r['key'] in draft['objects'] and r['kind']==kind for r in ni['objects'])
        out['limits']+=['注释清单：'+x['reason'] for x in ni['issues']]
        out['protected'] += [{'id':r['key'],'reason':r['reason']} for r in ni['objects'] if not r['safe_relationship']]
    return out


def apply(model,proposal,prepared):
    """Add verified fresh drafts to the original proposal, never confirm them here."""
    auto=prepared.get('auto_ranges') or {};draft=proposal['draft'];questions=[]
    if auto.get('tables'):
        types=deepcopy(auto['tables']);types.update(draft.get('table_types',{}))
        # Only transmitted candidates can become a question; budget omissions stay pending.
        for c in prepared['request']['candidates']:
            if c.get('kind')=='table' and types[c['id'][2:]]=='pending':
                questions.append({'id':'table:'+c['id'][2:],'table':c['id'][2:],'text':c['text'],'context':' / '.join(c['context']),
                    'question':'这张表属于论文内容，还是封面/表单等其他用途？','options':{'content':'论文内容表格','cover':'封面或表单表格','other':'其他用途，不套表内文字要求','pending':'暂不处理这张表'}})
        draft.update(table_enabled=True,table_types=types)
    if auto.get('notes') is not None:draft.update(note_enabled=True,note_draft=deepcopy(auto['notes']))
    proposal['auto_ranges']={k:deepcopy(v) for k,v in auto.items() if k not in ('candidates','notes')}
    proposal['auto_ranges']['table_roles']=deepcopy(draft.get('table_types',model.table_types))
    return questions

"""完全离线、无脚本的阅读报告；显式白名单、默认无论文短文/私人路径。"""
import html,json,re
from pathlib import PurePath
from .issues import CATEGORIES,STATUS,locate
from core.rehearsal import LABELS as IMPACT_LABELS

CSS='body{font-family:system-ui,"PingFang SC",sans-serif;color:#172b42;background:white;max-width:1180px;margin:24px auto;padding:0 24px;line-height:1.65}h1,h2{color:#173e68}table{border-collapse:collapse;width:100%;font-size:14px;margin:12px 0}td,th{border:1px solid #dbe3eb;padding:8px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#eef3f8}.note{background:#f3f6fa;padding:12px}.review{color:#916100}.problem,.risk{color:#ad3030}.pass{color:#167647}details{margin:12px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}@media print{body{max-width:none;margin:0}details{display:block}tr{break-inside:avoid}}'

def clean(v):
    if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if not re.search(r'(author|creator|lastmodifiedby|api.?key|password|credential|secret|token|cookie|authorization|path|input$|output$)',k,re.I)}
    if isinstance(v,list):return [clean(x) for x in v]
    if isinstance(v,tuple):return [clean(x) for x in v]
    if isinstance(v,str):
        v=re.sub(r'(?:/Users/|/Volumes/|/private/|/tmp/)[^\s，；。<>"\']+','（本机路径已省略）',v)
        v=re.sub(r'[A-Za-z]:[\\/][^\s，；。<>"\']+','（本机路径已省略）',v)
        v=re.sub(r'\bsk-[A-Za-z0-9_-]+','（密钥已省略）',v)
        v=re.sub(r'(DEEPSEEK_API_KEY|API_KEY|password|Authorization)\s*[:=]\s*[^\s，；。]+',r'\1=（已省略）',v,flags=re.I)
    return v

def portable(bundle,*,display_name='待检查文档.docx',include_excerpts=False):
    # The HTML/portable JSON/Markdown share one projection. Full legacy JSON is a separate advanced download.
    name=str(display_name).replace('\\','/').split('/')[-1][:80] or '待检查文档.docx'
    p=bundle['projection'];rows=[];seen=set()
    for r in p['records']:
        row={k:r[k] for k in ('id','record_key','category','object','locator','position','status','title','actual','expected','reason','action','basis','context','raw')}
        # At most20 unique affected objects,48chars each; never export the complete paragraph inventory.
        if include_excerpts and r['status'] not in ('pass','not_applicable') and (r['object'] in seen or len(seen)<20):
            row['excerpt']=r['excerpt'];seen.add(r['object'])
        rows.append(row)
    out={'structure_version':1,'display_name':name,'context':bundle['context'],'rules':{k:bundle['format']['rules'][k] for k in ('name','version','sha256','kind','template_structure_version','compatibility','front_supplement','toc_supplement','citation_supplement','note_supplement','reference_supplement','caption_supplement','table_layout_supplement','backmatter_sha256','backmatter_version','workbench') if k in bundle['format']['rules']},
         'scope':p['coverage'],'format_summary':p['format_summary'],'width_summary':p['width_summary'],'pagination_summary':p['pagination_summary'],
         'records':rows,'preservation':bundle.get('preservation'),'changes':bundle.get('changes',[]),'delta':bundle.get('delta'),'pagination_applied':bundle.get('pagination_applied'),'pagination_history':bundle.get('pagination_history',[]),
         'preview':bundle.get('preview',{'status':'未生成预览'}),'visual':bundle.get('visual',{'status':'未记录人工视觉复核'}),'word_status':'未验收',
         'history':bundle.get('history',[]),'next_steps':bundle['steps'],'excerpt_policy':'最多20个对象、各48字符' if include_excerpts else '默认省略论文原文；按编号定位，完整论文不嵌入报告',
         'conclusion':'启用规则及确认范围内的结果，不代表全文排版合格。'}
    if bundle.get('dynamic'):out['dynamic']=clean(bundle['dynamic'])
    if bundle['format']['rules'].get('workbench'):
        wb=bundle['format']['rules']['workbench'];cov=bundle['format']['coverage'];out['workbench_modules']=[{'module':m,'configured':v['configured'],'version':v.get('version',6 if m=='main' else 1),'participates':m=='main' or {'front':'front_scope','toc':'toc_scope','notes':'note_scope'}.get(m) in cov} for m,v in wb['modules'].items()]
    if bundle['format'].get('captions'):
        c=bundle['format']['captions'];out['caption_summary']={k:c[k] for k in ('enabled','summary','scope_complete','sequences','actual_pagination','limits')}
    if bundle['format'].get('internal_references'):
        r=bundle['format']['internal_references'];out['internal_references']={'bookmarks':len(r['bookmarks']),'reference_positions':len(r['references']),'target_groups':len(r['groups']),'fault_groups':sum(g['status']!='pass' for g in r['groups']),'inventory_complete':r['complete'],'issues':r['issues'],'limits':r['limits'],'cache_status':'未刷新；保存结果不证明新鲜','jump_status':'未验收','page_status':'未核对'}
    if bundle['format'].get('notes'):
        n=bundle['format']['notes'];out['note_summary']={'selected_count':len(n['selected']),'automatic_markers_preserved':n['automatic_markers_preserved'],'system_objects_readonly':n['system_objects_readonly'],'limits':n['limits'],'reference_positions':[{'kind':x['kind'],'note_id':x['note_id'],'paragraph':x['paragraph']} for x in n['inventory']['references']],'relationship_issues':n['inventory']['issues']}
    if bundle['format'].get('citations'):
        c=bundle['format']['citations'];out['citation_summary']={k:c[k] for k in ('enabled','summary','scope_state','order','limits','unreferenced_state','r22_link','undecided')};out['citation_summary']['unreferenced_numbers']=[r['number'] for r in c['unreferenced']]
        if c.get('syntax'):
            out['citation_summary'].update(syntax=c['syntax'],counts=c['counts'],order_semantics=c['order_semantics'],order_groups=[{k:v for k,v in g.items() if k!='raw'} for g in c['order_groups']],member_details=[{'citation':r['id'],'members':[{**m,'references':[{'paragraph':x['paragraph'],'number':x['number']} for x in m['references']]} for m in r.get('members',[])]} for r in c['rows']])
    if bundle['format']['coverage'].get('citation_paragraph_evidence'):out['citation_paragraphs']=bundle['format']['coverage']['citation_paragraph_evidence']
    if bundle['format'].get('toc'):
        t=bundle['format']['toc'];out['toc_summary']={k:t[k] for k in ('scope_state','page_status','risk_count','review_count','normalization','hierarchy_notes','missing_candidates')}
    # Caption proposal labels contain document text; mask these by default as well as excerpt fields.
    if not include_excerpts:
        for row in out['records']:
            if row['raw'].get('object_type')=='caption_number':
                for field in ('actual','raw'):
                    val=row[field]
                    if isinstance(val,dict):
                        if val.get('parsed'):val['parsed'].pop('title',None)
                        if isinstance(val.get('actual'),dict) and val['actual'].get('parsed'):val['actual']['parsed'].pop('title',None)
                row['actual']='编号与章号证据见详细报告；原题注标题默认省略'
            if row['raw'].get('object_type') in ('citation','citation_relation','table_border','footnote','endnote'):row['raw'].pop('excerpt',None)
            if row['raw'].get('object_type')=='citation_relation':
                def redact(value):
                    if isinstance(value,dict):return {k:redact(v) for k,v in value.items() if k not in ('preview','raw')}
                    if isinstance(value,list):return [redact(v) for v in value]
                    return value
                row['raw']=redact(row['raw'])
                # actual is already presentation text; the raw numeric evidence remains below.
                if isinstance(row['raw'].get('actual'),list) and row['raw'].get('locator',{}).get('property')=='correspondence':row['actual']='逐成员编号、状态及位置见下方明细（条目原文省略）'
            if row['record_key'].startswith('toc-match:'):
                row['actual']='目录标题文字（默认省略，按目录对象定位）'
                row['basis']='内部链接或确认范围内精确文字；详见本机对应表'
                row['raw']={k:v for k,v in row['raw'].items() if k not in ('entry','candidates','targets','evidence')}
            if row['raw'].get('object_type') in ('toc_title','toc_entry'):row['raw'].pop('excerpt',None)
            if row['record_key'].startswith('L'):
                if 'header_plan' in row['raw']:row['raw']['header_plan']=[{k:v for k,v in x.items() if k!='text'} for x in row['raw']['header_plan']]
                row['actual']='见对象位置与关联关系（原文已省略）'
                row['raw']={k:v for k,v in row['raw'].items() if k not in ('text','caption_text','label')}
        if out['pagination_applied']:
            out['pagination_applied']={k:v for k,v in out['pagination_applied'].items() if k not in ('pairs',)}
    if bundle.get('plan'):out['plan']=bundle['plan']
    if bundle.get('scope_summary'):out['scope_summary']=bundle['scope_summary']
    if bundle.get('impact'):out['impact']=bundle['impact'];out['rehearsal']=bundle['rehearsal']
    if bundle.get('saved_record'):out['saved_record']=bundle['saved_record']
    return clean(out)

def esc(v):return html.escape(str(v),quote=True)

def table(headers,rows):return '<table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table>'

def change_value(v,rid):
    from .issues import value
    if rid.startswith('L') and isinstance(v,bool):return '开启' if v else '关闭'
    if isinstance(v,dict) and 'width_mm' in v:return f"{v['width_mm']:.2f}mm；"+('固定列宽' if v.get('layout')=='fixed' else '自动调整')
    if isinstance(v,dict) and 'size_emu' in v:return ' × '.join(f'{n/36000:.2f}mm' for n in v['size_emu'])
    return value(v,rid,type(v) in (float,int))

def html_report(data):
    s=data['format_summary'];c=data['context'];parts=['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'none\'; base-uri \'none\'; form-action \'none\'"><title>论文有格阅读报告</title><style>'+CSS+'</style></head><body>','<h1>论文有格阅读报告</h1>']
    parts+=[table(['文件显示名称','轮次','模式','报告状态'],[[data['display_name'],c['round'],{'basic':'基础检查 R01–R07','extended':'扩展检查 R01–R12'}.get(c['mode'],c['mode']),c.get('validity','当前文件匹配')]]),'<p class="note">'+esc(data['conclusion'])+' '+esc(data['excerpt_policy'])+'</p>','<h2>规则及确认范围</h2>',table(['规则名称','版本','模板结构版本','配置哈希'],[[data['rules']['name'],data['rules']['version'],data['rules'].get('template_structure_version','固定/兼容配置'),data['rules']['sha256']]]),'<p>已确认正文段落：'+esc(', '.join(map(str,data['scope']['body_paragraphs'])) or '无（页面/分类范围见详情）')+'</p>']
    if data.get('workbench_modules'):
        labels={'main':'正文与章节','front':'封面与页眉页脚','toc':'目录','notes':'脚注与尾注'}
        parts+=['<h3>统一规则包与本轮参与范围</h3>',table(['模块','结构版本','配置与参与状态'],[[labels[x['module']],x['version'],'未配置' if not x['configured'] else '已配置并参与本轮检查（不代表全部通过）' if x['participates'] else '已配置；本轮未确认对应对象，未执行' ] for x in data['workbench_modules']]),'<p>规则包不确认论文对象，不执行宽度、分页或位置辅助。明确不检查字段见精确记录及规则包。</p>']
    parts+=['<h2>结果统计（分别计数，不相加为合格分数）</h2>',table(['启用规则','实际适用规则','格式问题','格式待复核'],[[s['rule_count'],s['applicable_rule_count'],s['problem_count'],s['review_count']]]),'<p>格式待复核包含规则记录与覆盖提示；宽度按对象计数，分页是建议，边界说明不是新增问题。</p>',table(['宽度风险/待复核/范围内','分页建议/待复核'],[[f"风险{data['width_summary']['risks']} / 待复核{data['width_summary']['reviews']} / 范围内{data['width_summary']['passes']}" if data['width_summary'] else '未检查',f"建议{data['pagination_summary']['suggestions']} / 待复核{data['pagination_summary']['reviews']}" if data['pagination_summary'] else '未检查']])]
    if data.get('caption_summary'):
        t=data['caption_summary'];n=t['summary'];parts+=['<h2>题注编号、结构位置与实际分页</h2>',table(['编号只读问题','结构位置问题','复杂对象/范围待复核','实际同页'],[[n['numbering_problems'] if n['numbering_problems'] is not None else '未启用',n['position_problems'] if n['position_problems'] is not None else '未启用',n['complex_or_scope_reviews'],n['actual_pagination']]]),'<p>'+esc(t['actual_pagination'])+'</p>','<p>'+esc('；'.join(t['limits']))+'</p>']
    if data.get('internal_references'):
        r=data['internal_references'];parts+=['<h2>内部引用结构（R44产品检查）</h2>',table(['书签边界对象','引用位置','目标/解析组','非通过组','清单覆盖充分'],[[r['bookmarks'],r['reference_positions'],r['target_groups'],r['fault_groups'],r['inventory_complete']]]),'<p>'+esc('；'.join(r['limits']))+'</p>','<p>目标与引用位置分别计数；目录重复展示不另加为独立故障。域缓存未刷新；真实跳转与实际页码未验收。</p>']
    if data.get('note_summary'):
        n=data['note_summary'];parts+=['<h2>脚注与尾注检查范围</h2>',table(['确认注释数','保留的内部自动标记','只读系统对象'],[[n['selected_count'],n['automatic_markers_preserved'],n['system_objects_readonly']]]),'<p>'+esc('；'.join(n['limits']))+'</p>']
    if data.get('toc_summary'):
        t=data['toc_summary'];parts += ['<h2>目录对应风险与页码未核对</h2>',table(['对应风险','对应待复核','确认范围','实际页码'],[[t['risk_count'],t['review_count'],t['scope_state'],t['page_status']]]),'<p>目录格式通过不等于页码正确。修改可能改变分页，需人工更新目录后作为新输入检查。</p>']
    if data.get('citation_summary'):
        c=data['citation_summary'];parts+=['<h2>引文对应与顺序边界</h2>', '<p>'+esc(('R33上标未检查；' if not c['enabled']['superscript'] else '')+c['scope_state']+'；'+c['unreferenced_state']+'；编号对应不证明文献真实或引用准确')+'</p>',table(['首次出现顺序','尚未引用的编号'],[[c['order'],c['unreferenced_numbers']]])]
        if c.get('counts'):
            parts+=['<h3>组合引文逐成员对应</h3>','<p>'+esc(c['counts'])+'；'+esc(c['order_semantics'])+'</p>',table(['引文对象','成员','状态','条目位置','依据'],[[r['citation'],m['number'],STATUS[m['status']],str([x['paragraph'] for x in m['references']]),m['reason']] for r in c['member_details'] for m in r['members']]),'<h3>首次位置组证据</h3>',table(['位置','原始成员顺序','本组首次','之前已出现','缺口','风险'],[[g['citation'],g['raw_numbers'],g['first_numbers'],g['previous_numbers'],g['first_missing'],g['risk']] for g in c['order_groups']])]
    if data.get('citation_paragraphs'):
        parts+=['<h2>确认引文上标与指定段落属性</h2>','<p>引文行内字体字号仍保护；本次仅在精确范围证明后读取指定pPr。XML声明符合不证明可见分页。</p>',table(['段落','确认引文区间','正文依据run','可检查属性','结构阻止','属性待复核'],[[p['paragraph'],[(r['start'],r['end']) for r in p['verified_citations']],p['ordinary_basis_runs'],p.get('allowed_properties',[]),p['blockers'],p.get('property_blockers',[])] for p in data['citation_paragraphs']])]
    parts+=['<h2>建议下一步</h2>','<ul>'+''.join('<li>'+esc(x['title']+'：'+x['reason'])+'</li>' for x in data['next_steps'])+'</ul>']
    if data.get('scope_summary'):
        sc=data['scope_summary']
        parts+=['<h2>本轮实际范围与未检查事项</h2>',table(['区域','参与检查','对象数量','口径','说明'],[[r['name'],'是' if r['participates'] else '未启用/未确认',r['selected'],r['unit'],r['scope']] for r in sc['areas']])]
        parts+=['<p>'+esc(x)+'</p>' for x in sc['limits']]
    for cat,label in CATEGORIES.items():
        rows=[r for r in data['records'] if r['category']==cat];attention=[r for r in rows if r['status'] not in ('pass','not_applicable')];passed=[r for r in rows if r not in attention]
        def records_table(rs):return table(['记录/对象位置','状态','实际情况','要求或建议','原因/动作','依据'],[[r['title']+' · '+r['position']+(' · '+r['excerpt'] if r.get('excerpt') else ''),STATUS[r['status']],r['actual'],r['expected'],r['reason']+'；'+r['action'],r['basis']] for r in rs])
        parts+=['<h2>'+label+'</h2>',records_table(attention) if attention else '<p>没有此类需要处理的记录；未检查状态见支持边界。</p>']
        if passed:parts+=['<details><summary>符合与不适用（'+str(len(passed))+'条）</summary>'+records_table(passed)+'</details>']
    parts+=['<h2>本轮修改及落盘复查</h2>',table(['项目','位置','修改前','修改后','落盘复查'],[[x['rule_id'],locate(x['locator']),change_value(x['before'],x['rule_id']),change_value(x['after'],x['rule_id']),x['verification']] for x in data['changes']]) if data['changes'] else '<p>本文件没有本轮修改记录，展示检查结果。</p>']
    if data['delta'] and not data.get('impact'):parts+=['<p>已解决 '+str(len(data['delta']['resolved_keys']))+'；原有剩余 '+str(len(data['delta']['remaining_keys']))+'；新出现 '+str(len(data['delta']['new_keys']))+'；转待复核 '+str(len(data['delta'].get('unresolved_review_keys',[])))+'（格式记录，非布局总数）。</p>']
    if data.get('impact'):
        im=data['impact']
        parts+=['<h2>预演与正式采用的关联影响</h2>','<p>正式采用重新验证绑定及原事务白名单，复用预演副本；没有再次修正，尚未自动切换处理输入。这不构成视觉验收。</p>',table(['变化类别','记录数'],[[IMPACT_LABELS.get(k,k),v] for k,v in im['counts'].items()]),table(['规则','对象','变化','修改前','读回后','说明'],[[r['rule_id'],locate(r['locator']),r['label'],change_value(r['before'],r['rule_id']),change_value(r['after'],r['rule_id']),r['reason']] for r in im['records']])]
    if data.get('plan'):
        p=data['plan']['summary']
        parts+=['<h2>已采用分步计划（每步独立事务）</h2>','<p>采用时0次完整修正；当前输入尚未自动切换。结果包含最终DOCX及各步修改和复查，中间DOCX另行下载。</p>',table(['步骤','正式轮次','父轮次','输入哈希','输出哈希'],[[i+1,r['number'],r['parent'],r['input_sha256'],r['output_sha256']] for i,r in enumerate(p['rounds'])]),'<h3>整计划最终影响（不累加中间问题数）</h3>',table(['变化类别','记录数'],[[IMPACT_LABELS.get(k,k),v] for k,v in p['overall_impact']['counts'].items()])]
    layout=data['pagination_applied']
    parts+=['<h2>分页辅助应用结果</h2>']
    if layout:
        parts+=['<p>'+esc(layout['message'])+'；'+esc(layout['limitation'])+'</p>',table(['对象','落盘属性','值','属性复查'],[[c['key'],('表格'+str(p['table'])+' 行'+str(p['row']) if 'table' in p else '段'+str(p.get('paragraph'))) +' · '+p['property'],'开启' if p['value'] else '关闭',c['verification']] for c in layout.get('checks',[]) for p in c.get('properties',[])])]
    elif data.get('pagination_history'):
        parts+=['<p>当前轮未重复独立复查分页属性；下列实际祖先轮次曾设置属性，不能据此宣称当前文件同页。</p>',table(['来源轮次','历史应用结果','核对范围'],[[h['round'],h['message'],h['status']] for h in data['pagination_history']])]
    else:parts+=['<p>本轮及已记录的祖先轮次没有分页辅助应用记录；关联建议不等于跨页已解决。</p>']
    if data.get('dynamic'):parts+=['<h2>动态数字事务（独立授权）</h2><p>仅已列明数字与唯一纯文本引用同步；REF/PAGEREF、目录页码和真实分页未更新，Word未验收。</p>',table(['数字改动','未处理关联组','域/页码状态'],[[len(data['dynamic']['plan']['edits']),len(data['dynamic']['plan']['blocked_groups']),data['dynamic']['word']['reason']]])]
    pre=data['preview'];vis=data['visual']
    parts+=['<h2>预览与人工视觉复核</h2>','<p>Word：'+esc(data['word_status'])+'。预览图未默认嵌入，可作为另行附件。</p>',table(['预览状态','渲染环境','页数/预览范围','人工视觉记录'],[[pre.get('status','未生成预览'),pre.get('renderer_version','未检查'),str(pre.get('page_count','未检查'))+' / '+str(pre.get('preview_range','未检查')),{'looked':'人工已查看，不表示无问题','issues':'人工发现问题'}.get(vis.get('status'),vis.get('status','未记录'))]]),'<p>'+esc(pre.get('environment_status','环境记录对应预览生成时；未生成时未检查。'))+'</p>']
    for note in pre.get('font_notes',[]):parts+=['<p>'+esc(note)+'</p>']
    if pre.get('fonts'):parts+=[table(['文档目标字体','渲染匹配字体','实际安装'],[[f['target'],f['resolved_family'],'已匹配' if f['installed_exact'] else '替代，分页可能不同'] for f in pre['fonts']])]
    if vis.get('notes'):parts+=['<p>人工观察：'+esc(vis['notes'])+'</p>']
    parts+=['<h2>处理历史摘要</h2>',table(['轮次','操作','状态','修改/已解决/剩余/新增'],[[h['round'],h['operation'],h['status'],'；'.join(f'{k} {v}' for k,v in h['counts'].items())] for h in data['history']]),'<details><summary>精确数值及全部原始记录（转义，非可执行内容）</summary><pre>'+esc(json.dumps(data,ensure_ascii=False,indent=2))+'</pre></details></body></html>']
    return '\n'.join(parts)

def markdown_report(data):
    s=data['format_summary'];out=['# 论文有格阅读报告','',data['display_name']+' · 第'+str(data['context']['round'])+'轮',data['conclusion'],f"启用规则{s['rule_count']}；格式问题{s['problem_count']}；格式待复核{s['review_count']}", '宽度：'+json.dumps(data['width_summary'],ensure_ascii=False),'Word：未验收','']
    if data.get('impact'):out+=['预演与正式采用影响：'+json.dumps(data['impact'],ensure_ascii=False),'采用绑定核对：'+json.dumps(data['rehearsal'],ensure_ascii=False)]
    if data.get('plan'):out+=['分步计划及父子关系：'+json.dumps(data['plan'],ensure_ascii=False)]
    if data.get('scope_summary'):out+=['范围状态摘要：'+json.dumps(data['scope_summary'],ensure_ascii=False)]
    if data.get('citation_paragraphs'):out+=['确认引文段落的精确证据：'+json.dumps(data['citation_paragraphs'],ensure_ascii=False)]
    if data.get('citation_summary'):out+=['引文逐成员与首次位置证据：'+json.dumps(data['citation_summary'],ensure_ascii=False)]
    if data.get('caption_summary'):out+=['题注编号/结构位置/实际分页：'+json.dumps(data['caption_summary'],ensure_ascii=False)]
    for r in data['records']:out.append('- '+CATEGORIES[r['category']]+' · '+r['record_key']+' · '+r['position']+' · '+STATUS[r['status']]+'：'+r['actual']+' → '+r['expected']+'；'+r['reason'])
    if data.get('dynamic'):out+=['','动态数字事务：仅授权数字变化，域缓存/分页/目录页码未更新。',json.dumps(data['dynamic'],ensure_ascii=False)]
    out+=['','本轮修改：'+json.dumps(data['changes'],ensure_ascii=False),'预览/视觉：'+json.dumps({'preview':data['preview'],'visual':data['visual']},ensure_ascii=False)]
    return '\n'.join(out)+'\n'

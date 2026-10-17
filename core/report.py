"""JSON是机器报告，Markdown是人工可读报告；两者使用同一数据。"""
import json
from .package import write_new

LABELS = {'pass': '符合', 'problem': '问题', 'review': '待复核', 'not_applicable': '不适用'}

def basis(source):
    if source.get('file'):
        return (source['label']+'：' if source.get('label') else '')+f"{source['file']} 物理页{source['physical_page']}：{source['quote']}"
    return f"{source['label']}：{source['quote']}" + ('（模拟API响应）' if source.get('parse_kind') == 'mock_api' else '')

def _fmt(value):
    from .paragraph_values import label
    readable=label(value)
    if readable:return readable
    return json.dumps(value, ensure_ascii=False).replace('|', '\\|').replace('\n', ' ')

def markdown(report):
    s = report['summary']
    lines = ['# 论文有格检查报告', '', f"规则：{report['rules']['name']} v{report['rules']['version']}",
             f"规则配置SHA256：{report['rules']['sha256']}",
             f"输入：{report['input']}", f"SHA256：{report['input_sha256']}", '',
             f"启用规则 {s['rule_count']} 条；实际适用 {s.get('applicable_rule_count',s['rule_count'])} 条；问题 {s['problem_count']} 个；待复核 {s['review_count']} 个（规则记录 {s['review_findings']}，覆盖提示 {s['review_notes']}）。",
             f"结论：{s['conclusion']}。仅针对已覆盖范围，不表示全文合格。", '', '格式属性结果不包含实际分页和所有可见排版验收；页面预览及Word查看需另行人工复核。', '', '## 覆盖范围', '',
             _fmt(report['coverage']), '', '## 逐项检查', '',
             '| 规则 | 位置 | 实际值 | 要求值 | 状态 | 可修正 | 依据 |', '| --- | --- | --- | --- | --- | --- | --- |']
    if 'template_structure_version' in report['rules']:
        lines.insert(4,'模板结构版本：'+str(report['rules']['template_structure_version'])+'；兼容转换：'+_fmt(report['rules'].get('compatibility')))
    if report['rules'].get('workbench'):
        wb=report['rules']['workbench'];lines[4:4]=['统一规则包结构版本：'+str(wb['version'])+'；摘录哈希：'+wb['excerpt_sha256'],'四模块配置：'+_fmt(wb['modules']),'明确不检查字段：'+_fmt(wb['disabled_fields'])+'；配置不确认对象，参与范围以本轮coverage为准。']
    if report['rules'].get('front_supplement'):
        lines += ['', '封面/页眉页脚补充配置：'+_fmt(report['rules']['front_supplement']), '']
    for f in report['findings']:
        src = f['source']
        lines.append('| ' + ' | '.join([f['rule_id']+(' '+f['rule_name'] if f['rule_id'] in ('R33','R34') else ''), _fmt(f['locator']), _fmt(f['actual']), _fmt(f['expected']),
                        LABELS[f['status']] + ('：' + f['detail'] if f['detail'] else ''),
                        '是' if f['fixable'] else '否', basis(src).replace('|', '\\|')]) + ' |')
    if report.get('internal_references'):
        r=report['internal_references'];lines += ['', '## 内部引用结构（R44产品检查）',f"书签边界对象 {len(r['bookmarks'])}；引用位置 {len(r['references'])}；目标/解析组 {len(r['groups'])}。数量不可相加为独立缺陷；目录重复呈现共享目标证据。",'域缓存未刷新；目标存在不证明引用内容、真实跳转或实际页码已核对。',_fmt(r),'']
    lines += ['', '## 字体及编号只读解析证据', '', '文档指定字体用于属性检查；本机字体安装与替代由独立预览核对。']
    lines += [f"- {f['key']}："+_fmt({'font':f.get('font_evidence'), 'numbering':f.get('numbering_evidence')}) for f in report['findings'] if f.get('font_evidence') or f.get('numbering_evidence')]
    lines += ['', '## 修改依赖提示', '']
    lines += ['- '+x['detail'] for x in report.get('modification_dependencies',[])] or ['没有已预测的关联影响；不表示不存在其他未支持依赖。']
    lines += ['', '## 覆盖提示', '']
    lines += [f"- {_fmt(n['locator'])}：{n['detail']}" for n in report['coverage_notes']] or ['无额外提示；仍不包括未确认段落及报告所列覆盖外对象。']
    lines += ['', '## 封面、页眉页脚与页码边界', '']+['- '+n for n in report['coverage'].get('front_limits',[])]
    if report.get('captions'):
        lines += ['', '## 题注编号、结构位置和分页（分开核对）', '',_fmt(report['captions']), '题注补充配置：'+_fmt(report['rules'].get('caption_supplement'))]
    if report.get('toc'):
        lines += ['', '## 目录对应核对与页码边界', '', '实际页码未核对。保存页码及PAGEREF不代表真实页码；修改后建议在Word人工更新，再作为新输入检查。',_fmt(report['toc']), '目录补充模板：'+_fmt(report['rules'].get('toc_supplement'))]
    if report.get('notes'):
        n=report['notes'];lines += ['', '## 脚注与尾注正文范围（编号标记及系统对象只读）', '',f"确认{len(n['selected'])}条；保留内部自动标记{n['automatic_markers_preserved']}个；系统对象{n['system_objects_readonly']}个。",_fmt(n['inventory']),'注释补充配置：'+_fmt(report['rules'].get('note_supplement'))]+['- '+x for x in n['limits']]
    if report.get('citations'):
        lines += ['', '## 引文上标、对应关系与首次顺序（分别核对）', '',_fmt(report['citations']),'引文补充配置：'+_fmt(report['rules'].get('citation_supplement'))]
    return '\n'.join(lines) + '\n'

def modification_markdown(result):
    cfg=result['after']['rules']
    lines = ['# 论文有格修改记录', '', f"输出：{result['output']}",
             f"配置：{cfg['name']} v{cfg['version']}", f"配置SHA256：{cfg['sha256']}", '',
             '| 规则 | 位置 | 修改前 | 修改后 | 落盘复查 | 依据 |', '| --- | --- | --- | --- | --- | --- |']
    if 'template_structure_version' in cfg:lines.insert(4,'模板结构版本：'+str(cfg['template_structure_version']))
    for c in result['changes']:
        lines.append('| ' + ' | '.join([c['rule_id']+(' · '+c['property'] if c.get('property') else ''), _fmt(c['locator']), _fmt(c['before']), _fmt(c['after']), LABELS[c['verification']],basis(c['source']).replace('|','\\|')]) + ' |')
    cleanup=[c for c in result['changes'] if c.get('attribute_cleanup_note')]
    if cleanup:lines += ['', '## 所选属性清理说明', '']+[c['rule_id']+' '+_fmt(c['locator'])+'：'+c['attribute_cleanup_note'] for c in cleanup]
    if result.get('caption_move'):lines += ['',result['caption_move']['message'],result['caption_move']['limitation'],'授权的对象顺序变化及范围映射：'+_fmt(result['range_mapping'])]
    if 'layout' in result:lines += ['', result['layout']['message']+'。'+result['layout']['limitation'], '这是独立产品排版辅助，不计入R01–R12学校演示格式规则；尚未自动验证分页。']
    if result.get('page_layout'):lines += ['', '## 分节页码结构事务', '已生成PAGE并验证受控新增/克隆部件及分节。未计算域缓存、目录或实际页码；真实渲染/Word观察另行记录。',_fmt(result['page_layout']['validation'])]
    if result.get('assembly'):lines += ['', '完整整理各阶段及父子关系：'+_fmt(result['assembly'])]
    if result.get('dynamic'):lines += ['', '## 用户授权动态数字事务（不是普通格式修正）', '仅按清单修改题注及唯一纯文本引用数字；所有run格式与未选部件保持。REF/PAGEREF、目录页码及实际分页未更新，须在Word更新并复核。']
    if 'widths' in result:
        from .widths import width_markdown
        lines += ['', result['widths']['message'], result['widths']['limitation'], '', width_markdown(result['widths']['after'])]
    if result.get('impact'):lines += ['', '## 预演及采用影响',_fmt(result['impact']),'采用时重新核对：'+_fmt(result.get('rehearsal') or result.get('plan')),'预演及采用不等于视觉、目录页码或Word验收。']
    if 'round' in result:lines += ['', '轮次与输入来源：'+_fmt(result['round'])]
    if 'problem_delta' in result:lines += ['', ('兼容接口按key统计（run变化时不能替代稳定对齐结论）：' if result.get('impact') else '问题变化（已解决/原有剩余/新出现）：')+_fmt(result['problem_delta'])]
    for c in result['changes']:
        if c.get('dependency_note'):lines += ['', c['dependency_note'], '保留原有效格式的显式补丁：'+_fmt(c['preserved_format_patch'])]
    lines += ['', '未强制修正的待复核项：' + _fmt(result['skipped_review_keys']), '',
              '完整性验证：' + _fmt(result['preservation']), '']
    return '\n'.join(lines)

def write_report(path, data, input_path, modification=False):
    write_new(path, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode(), input_path)
    from pathlib import Path
    write_new(Path(path).with_suffix('.md'), (modification_markdown(data) if modification else markdown(data)).encode(), input_path)

"""网页可直接调用的同步引擎 API；不调用网络、Office 或全局环境。"""
from pathlib import Path
from copy import deepcopy
import json
import math
from lxml import etree as ET
from .package import Package, DemoError, q, NS, sha256, write_new, new_path
from .formats import Resolver, Unresolved, scripts, paragraph_unsafe, same_font
from .rule_config import read_custom_config

DEFAULT_RULES = Path(__file__).resolve().parents[1] / 'rules/scut_2015_demo.json'
IDS = tuple(f'R{i:02}' for i in range(1, 8))

def load_rules(path=DEFAULT_RULES):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get('rules'), dict) or set(data['rules']) != set(IDS):
        raise DemoError('第一阶段规则必须恰为R01–R07')
    if any(not isinstance(data['rules'][i], dict) or any(k not in data['rules'][i] for k in
           ('name', 'expected', 'page', 'quote')) for i in IDS) or any(k not in data for k in ('name', 'version', 'source_file')):
        raise DemoError('规则配置缺少名称、来源或值')
    # First phase supports one audited, fixed configuration, not arbitrary rules.
    expected = [{'width_mm': 210, 'height_mm': 297},
                {'top_mm': 25, 'bottom_mm': 25, 'left_mm': 25, 'right_mm': 25},
                '宋体', 'Times New Roman', 12, 1.5, 2]
    if [data['rules'][i]['expected'] for i in IDS] != expected:
        raise DemoError('此版本仅支持已核对的2015演示规则值')
    data['sha256'] = sha256(raw)
    return data

def load_custom_rules(path):
    """显式入口：兼容R05/R06短配置、版本2正文模板及版本3对象模板；默认load_rules仍严格固定。"""
    return read_custom_config(path, load_rules())

def _rules(value, custom_rules_path=None, mode="basic"):
    if mode not in ("basic", "extended", "academic"):
        raise DemoError("检查模式无效")
    base = _base_rules(value, custom_rules_path)
    if mode in ("extended", "academic"):
        from .extended import extend_rules
        base=extend_rules(base)
        if mode=='academic':
            from .academic_rules import extend
            base=extend(base)
            from .table_text import PATH as table_path
            table_raw=table_path.read_bytes()
            from .table_text import load_policy
            base['table_policy']=load_policy(table_raw);base['table_policy_sha256']=sha256(table_raw)
        return base
    return base

def _base_rules(value, custom_rules_path=None):
    # A path is the public input, so caller cannot inject an unvalidated dict.
    if custom_rules_path is not None:
        if value is not None:
            raise DemoError('默认规则路径和自定义配置不能同时指定')
        return load_custom_rules(custom_rules_path)
    return load_rules(DEFAULT_RULES if value is None else value)

def _text(p):
    return ''.join(p.itertext()) if p is None else ''.join(p.xpath('.//w:t/text()', namespaces=NS))

def _scope(pkg, body):
    if isinstance(body, (str, Path)):
        body = json.loads(Path(body).read_text(encoding='utf-8'))
    if isinstance(body, dict):
        if body.get('input_sha256') != pkg.hash:
            raise DemoError('正文清单文件哈希不匹配，请重新确认；不能用于另一份文件')
        body = body.get('body_paragraphs')
    if not isinstance(body, (list, tuple)) or any(type(n) is not int for n in body):
        raise DemoError('须显式指定正文段落编号列表或带input_sha256的清单')
    if len(set(body)) != len(body) or any(n < 1 or n > len(pkg.paragraphs) for n in body):
        raise DemoError('正文段落编号重复或越界（顶层段落，1起始）')
    return sorted(body)

def inspect_document(input_path):
    """返回顶层段落清单供人工确认；不自动分类。编号包括空段/图片段/分节段。"""
    p = Package(input_path)
    return {'input': str(p.path), 'input_sha256': p.hash, 'section_count': len(p.sections),
            'indexing': '主文档body直属w:p，1起始；不含表格单元格或文本框段落',
            'paragraphs': [{'index': i, 'text': _text(x), 'style_id': x.find('w:pPr/w:pStyle', NS).get(q('val'))
                            if x.find('w:pPr/w:pStyle', NS) is not None else None,
                            'special': paragraph_unsafe(x)} for i, x in enumerate(p.paragraphs, 1)]}

def _number(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (ValueError, TypeError):
        return None

def _check(pkg, body, rules, classification=None):
    from .backmatter import activate
    rules=activate(rules,classification)
    if rules.get('workbench'):
        from .rule_bundle import validate_scope_templates
        validate_scope_templates(rules,classification)
    from .internal_refs import configure
    configure(pkg,classification if rules.get('mode')=='academic' else None)
    from .citation_paragraphs import build as citation_paragraph_proofs
    paragraph_proofs=citation_paragraph_proofs(pkg,classification) if rules.get('mode')=='academic' else {}
    res = Resolver(pkg)
    findings, notes = [], []
    def add(rule, loc, actual, status, fixable=True, detail=''):
        key = rule + ':' + ':'.join(f'{k}={v}' for k, v in loc.items())
        cfg = rules['rules'][rule]
        findings.append({'key': key, 'rule_id': rule, 'rule_name': cfg['name'], 'locator': loc,
                         'actual': actual, 'expected': cfg['expected'], 'status': status,
                         'fixable': status == 'problem' and fixable and not pkg.signed and not pkg.ambiguous_sections,
                         'source': deepcopy(cfg['source']) if 'source' in cfg else
                           {'file': rules['source_file'], 'physical_page': cfg['page'], 'quote': cfg['quote'],
                            'interpretation': cfg.get('demo_interpretation')}, 'detail': detail})
    def note(loc, detail):
        notes.append({'locator': loc, 'status': 'review', 'detail': detail})
    if not pkg.sections:
        note({'document': 1}, '未找到标准分节属性，页面规则不能确定')
    if pkg.ambiguous_sections:
        for rule in ('R01', 'R02'):
            add(rule, {'document': 1}, None, 'review', False, '有嵌套或修订中的分节属性；无法可靠确定全部节，禁止修正该文件')
    for n, s in enumerate(pkg.sections, 1):
        loc = {'section': n}
        for rule, tag, attrs in [('R01', 'pgSz', ['w', 'h']), ('R02', 'pgMar', ['top', 'bottom', 'left', 'right'])]:
            e = s.find(q(tag))
            vals = {a: _number(e.get(q(a))) if e is not None else None for a in attrs}
            actual = {a + '_mm': round(v * 25.4 / 1440, 3) if v is not None else None for a, v in vals.items()}
            if any(v is None or (rule == 'R01' and v <= 0) for v in vals.values()):
                add(rule, loc, actual, 'review', False, '页面属性缺失或异常，不猜测Word默认值')
            else:
                expected = rules['rules'][rule]['expected']
                target = [expected['width_mm'], expected['height_mm']] if rule == 'R01' else [expected[a + '_mm'] for a in attrs]
                ok = all(abs(v * 25.4 / 1440 - t) <= 0.03 for v, t in zip(vals.values(), target))
                if rule == 'R01' and e.get(q('orient')) is not None:
                    actual['orientation'] = e.get(q('orient'))
                    if actual['orientation'] not in ('portrait','landscape'):
                        add(rule, loc, actual, 'review', False, '纸张方向属性无法确定')
                        continue
                    ok = ok and actual['orientation'] == 'portrait'
                add(rule, loc, actual, 'pass' if ok else 'problem')
    from .text_runs import walk,select_run,executable_run
    checked_runs = 0
    skipped_runs = 0
    for index in body:
        p = pkg.paragraphs[index - 1]
        loc = {'paragraph': index}
        unsafe = paragraph_unsafe(p)
        linked=walk(pkg,p) if p.find(q('hyperlink')) is not None else None
        partial=bool(linked and linked['supported_links'] and not linked['context_reason'])
        if partial:unsafe=None
        try:
            pl = res.layers(p, kind='pPr')
            # Table and numbering styles, list definitions and style cycles are not approximated.
            numbered = any(x.find(q('numPr')) is not None for x in pl)
            runs = [(x['locator'],x['node'],res.layers(p,x['node']),x['reason'],x['evidence']) for x in linked['rows']] if partial else [({'run':i},r,res.layers(p,r),None,None) for i,r in enumerate(p.findall(q('r')),1)]
        except Unresolved as e:
            unsafe = str(e)
            runs = []
        if unsafe:
            if linked and linked['issues']:unsafe+='；'+ '；'.join(x['detail'] for x in linked['issues'])
            for rule in IDS[2:]:
                add(rule, loc, {'unresolved': unsafe}, 'review', False, unsafe)
            note(loc, unsafe)
            continue
        ordinary, special = [], []
        proof=paragraph_proofs.get(index,{})
        recognized={r['run'] for r in proof.get('recognized_superscript',[])} if proof.get('structurally_safe') else set()
        if partial:
            note(loc,'仅普通链接及直属文字属性进入检查；链接段落的行距/缩进仍未检查；不访问目标。')
            for issue in linked['issues']:note({**loc,**issue['locator']},issue['detail'])
        for segment, r, layers, structure_reason, link_evidence in runs:
            reason = structure_reason or res.special(r, layers)
            i=segment.get('run',segment.get('link_run'))
            t = _text(r)
            if reason:
                skipped_runs += 1
                special.append(i)
                note({'paragraph':index,**segment}, reason + '：该run未检查、未修正'+('；已精确确认引文上标，行内字体/字号继续保护，指定段落属性另有独立证据' if i in recognized else ''))
                continue
            if not t.strip():
                continue
            checked_runs += 1
            run_finding_start=len(findings)
            ordinary.append((i, r, layers))
            cn, slots, unknown = scripts(t)
            rl = {'paragraph':index,**segment}
            for rule, wanted, font_slots in [('R03', cn, ['eastAsia']), ('R04', bool(slots), slots)]:
                if wanted:
                    evidence = {slot: res.font_info(layers, slot, t) for slot in font_slots}
                    value = {slot: (info['font'] if info['font'] is not None else {'unresolved':info['reason'],'slot':slot}) for slot,info in evidence.items()}
                    pending = any(v is None or isinstance(v, dict) for v in value.values())
                    add(rule, rl, value, 'review' if pending else
                        ('pass' if all(same_font(v,rules['rules'][rule]['expected']) for v in value.values()) else 'problem'),
                        fixable=all(info['safe_to_fix_slot'] for info in evidence.values()),
                        detail='；'.join(slot+'：'+info['reason'] for slot,info in evidence.items() if info.get('reason')) if pending else '')
                    findings[-1]['font_evidence']=evidence
                    if pending:
                        for slot,info in evidence.items():
                            if info['font'] is None:continue
                            add(rule,{**rl,'property':'font_'+slot},{slot:info['font']},'pass' if same_font(info['font'],rules['rules'][rule]['expected']) else 'problem',fixable=info['safe_to_fix_slot'],detail='混合片段中可判定的槽位独立检查；其余槽位仍待复核。'+info.get('dependency',''))
                            findings[-1]['font_evidence']={slot:info}
                    if not findings[-1]['fixable'] and not pending and findings[-1]['status']=='problem':findings[-1]['detail']='；'.join(info['dependency'] for info in evidence.values() if info.get('dependency')) or '字体映射可判定，但跨槽回退依赖不允许自动修正；请在Word核对并分离文字片段'
                else:
                    add(rule, rl, None, 'not_applicable', False, '无该类字符')
            if unknown:
                note(rl, '含未支持字体槽位的字符（如希腊文、符号、emoji）；其字体未验证')
            size = res.size(layers)
            add('R05', rl, {'pt': size}, 'review' if size is None else
                ('pass' if size == rules['rules']['R05']['expected'] else 'problem'))
            if link_evidence:
                for f in findings[run_finding_start:]:f['link_evidence']=deepcopy(link_evidence)
        if partial:
            for rule in ('R06','R07'):add(rule,loc,{'unresolved':'含链接段落属性仍保护'},'review',False,'普通文字已按受控范围检查；行距和缩进不修正')
            continue
        paragraph_special=bool(special) and not proof.get('structurally_safe',False)
        if not ordinary and not proof.get('structurally_safe',False):
            for rule in ('R06', 'R07'):
                add(rule, loc, None, 'review', False, '无可确认的普通正文文字')
            continue
        spacing = res.attrs(pl, 'spacing')
        line, mode = _number(spacing.get('line')), spacing.get('lineRule', 'auto')
        actual = {'line_rule': mode, 'multiple': line / 240 if line is not None and mode == 'auto' else None,
                  'pt': line / 20 if line is not None and mode in ('exact', 'atLeast') else None}
        # snapToGrid can make the actual 1.5 line layout uncertain. The XML value alone is not enough.
        grid = any(s.find(q('docGrid')) is not None and s.find(q('docGrid')).get(q('type')) in
                   ('lines', 'linesAndChars', 'snapToChars') for s in pkg.sections)
        pending = (proof.get('structurally_safe') and (proof.get('grid_active') or spacing.get('line') is not None and line is None)) or paragraph_special or mode not in ('auto', 'exact', 'atLeast') or (line is not None and line <= 0) or (
            grid and res.value(pl, 'snapToGrid', '1') not in ('0', 'false', 'off'))
        if pending:
            add('R06', loc, actual, 'review', False, '混有特殊run或文档网格，段落行距不自动修正')
        else:
            # absent line means single spacing when no inheritance provides it.
            actual['multiple'] = 1 if line is None else actual['multiple']
            add('R06', loc, actual, 'pass' if mode == 'auto' and actual['multiple'] == rules['rules']['R06']['expected'] else 'problem')
        ind = res.attrs(pl, 'ind')
        basis=[r for r in ordinary if r[0] in proof.get('ordinary_basis_runs',[])] if proof.get('structurally_safe') else ordinary
        sizes = {res.size(layers) for _, _, layers in basis}
        one_size = next(iter(sizes)) if len(sizes) == 1 and None not in sizes else None
        width_changed = any(res.value(l, 'w', '100') != '100' or res.value(l, 'spacing', '0') != '0'
                            for _, _, l in basis)
        chars = _number(ind.get('firstLineChars'))
        wanted_chars = rules['rules']['R07']['expected']
        pt = _number(ind.get('firstLine'))
        pt = pt / 20 if pt is not None else None
        hanging = any(k in ind for k in ('hanging', 'hangingChars'))
        inherited_ind = res.attrs([x for x in pl if x is not p.find(q('pPr'))], 'ind')
        inherited_hanging = any(k in inherited_ind for k in ('hanging', 'hangingChars'))
        malformed = any(_number(ind[k]) is None for k in ('firstLine', 'firstLineChars', 'hanging', 'hangingChars') if k in ind)
        actual = {'first_line_chars': chars / 100 if chars is not None else None, 'first_line_pt': pt,
                  'hanging': ind.get('hanging'), 'hanging_chars': ind.get('hangingChars'),
                  'uniform_size_pt': one_size}
        if paragraph_special or numbered or malformed or inherited_hanging:
            add('R07', loc, actual, 'review', False, '特殊run、编号、异常属性或继承悬挂缩进：不改段落缩进')
        elif hanging:
            add('R07', loc, actual, 'problem', detail='存在悬挂属性，与正文首行缩进冲突（包括零值）')
        elif chars is not None:
            if chars != wanted_chars * 100:
                add('R07', loc, actual, 'problem')
            elif wanted_chars == 0 and pt not in (None, 0):
                add('R07', loc, actual, 'problem', detail='零字符缩进与非零点值冲突')
            elif pt not in (None, 0) and (one_size is None or width_changed or proof.get('structurally_safe') and proof.get('grid_active')):
                add('R07', loc, actual, 'review', False, '字符和点值并存，但无法核对等效关系')
            elif pt not in (None, 0) and abs(pt - wanted_chars * one_size) > 0.05:
                add('R07', loc, actual, 'problem', detail='字符和点值缩进冲突，修正时清除冲突')
            else:
                add('R07', loc, actual, 'pass')
        elif pt in (None, 0):
            add('R07', loc, actual, 'pass' if wanted_chars == 0 else 'problem')
        elif wanted_chars == 0:
            add('R07', loc, actual, 'problem')
        elif one_size is None or width_changed or (proof.get('structurally_safe') and proof.get('grid_active')) or not any(scripts(_text(r))[0] for _, r, _ in basis):
            add('R07', loc, actual, 'review', False, '点值缩进无法可靠换算为要求的字符数')
        else:
            add('R07', loc, actual, 'pass' if abs(pt - wanted_chars * one_size) <= 0.05 else 'problem')
    if pkg.signed:
        note({'document': 1}, '含数字签名：禁止修正，避免生成失效签名副本')
    counts = {s: sum(f['status'] == s for f in findings) for s in ('pass', 'problem', 'review', 'not_applicable')}
    scope = {'body_paragraphs': body, 'total_top_level_paragraphs': len(pkg.paragraphs),
             'unconfirmed_paragraphs': [i for i in range(1, len(pkg.paragraphs) + 1) if i not in body],
             'ordinary_runs_checked': checked_runs, 'special_runs_skipped': skipped_runs,
             'section_count': len(pkg.sections), 'excluded': '标题/题注/未确认段落、表格格式、页眉页脚、脚注/文本框等不适用正文规则；不验证全文合格。'}
    if paragraph_proofs:scope['citation_paragraph_evidence']=list(paragraph_proofs.values())
    report = {'engine_version':'demo-10.0', 'schema_version': 1, 'input': str(pkg.path), 'input_sha256': pkg.hash,
            'rules': {'name': rules['name'], 'version': rules['version'], 'sha256': rules['sha256'],
                      **({'kind': rules['kind'], 'base_sha256': rules['base_sha256'],
                          'sources': {i: deepcopy(rules['rules'][i]['source']) for i,cfg in rules['rules'].items() if 'source' in cfg}} if 'kind' in rules else {})},
            'coverage': scope, 'summary': {'rule_count': 7, 'problem_count': counts['problem'],
              'review_count': counts['review'] + len(notes), 'review_findings': counts['review'],
              'review_notes': len(notes), 'pass_count': counts['pass'], 'not_applicable_count': counts['not_applicable'],
              'conclusion': '已覆盖检查未发现问题' if counts['problem'] == 0 else '已覆盖检查发现问题'},
            'findings': findings, 'coverage_notes': notes}

    if 'template_structure_version' in rules:
        report['rules']['template_structure_version']=rules['template_structure_version']
        report['rules']['compatibility']=deepcopy(rules.get('extension_config',{}).get('compatibility'))
    if classification is not None:
        if classification.get('material_exclusions'):report['coverage']['material_exclusions']=deepcopy(classification['material_exclusions'])
        from .extended import append_checks
        append_checks(report, pkg, classification, rules)
        if rules.get('mode')=='academic':
            from .academic import append_checks as academic_checks
            academic_checks(report,pkg,classification,rules)
            if classification.get('table_scope') is not None:
                from .table_text import append_checks as table_checks
                table_checks(report,pkg,classification['table_scope'],rules)
                from .table_edges import append_checks as edge_checks
                edge_checks(report,pkg,classification['table_scope'])
    if classification is not None and rules.get('mode')=='academic' and classification.get('front_scope'):
        from .front import append_checks as front_checks
        front_checks(report,pkg,classification['front_scope'])
    if classification is not None and rules.get('mode')=='academic' and classification.get('toc_scope'):
        from .toc import append_checks as toc_checks
        toc_checks(report,pkg,classification['toc_scope'],classification)
    if classification is not None and rules.get('mode')=='academic' and classification.get('citation_scope'):
        from .citations import append_checks as citation_checks
        citation_checks(report,pkg,classification['citation_scope'],classification)
    if classification is not None and rules.get('mode')=='academic' and classification.get('caption_scope'):
        from .captions import append_checks as caption_checks
        caption_checks(report,pkg,classification['caption_scope'],classification)
    if classification is not None and rules.get('mode')=='academic' and classification.get('note_scope'):
        from .notes import append_checks as note_checks
        note_checks(report,pkg,classification['note_scope'])
    if rules.get('workbench'):
        from .rule_bundle import project_checks
        project_checks(report,rules,classification)
    if classification is not None and rules.get('mode')=='academic':
        from .internal_refs import append_checks as reference_checks
        reference_checks(report,pkg,classification)
    from .dependencies import annotate_dependencies
    annotate_dependencies(report)
    if report.get('citations'):
        for n in sorted({f['locator']['paragraph'] for f in report['findings'] if f['rule_id']=='R33' and f['fixable']}):
            peers=[f['key'] for f in report['findings'] if f['fixable'] and f['rule_id']!='R33' and f['locator'].get('paragraph')==n and 'run' in f['locator']]
            if peers:report['modification_dependencies'].append({'trigger_keys':peers+[f['key'] for f in report['findings'] if f['rule_id']=='R33' and f['locator'].get('paragraph')==n and f['fixable']],'detail':f'段{n}的普通run字体字号修改与引文拆分须分轮选择：先完成普通格式，再修引文上标；不会改变未选字符。'})
    from .text_runs import annotate
    annotate(report)
    from .citation_paragraphs import finalize as finalize_paragraph_evidence
    finalize_paragraph_evidence(report)
    return report

def _confirmed_scope(pkg, body, mode, classification_manifest):
    if mode in ('extended','academic'):
        from .classification import validate_classification
        classification = validate_classification(pkg, classification_manifest)
        return sorted(int(n) for n,t in classification['paragraph_types'].items() if t == 'body'), classification
    if classification_manifest is not None:
        raise DemoError('分类清单仅用于显式扩展模式')
    return _scope(pkg, body), None

def effective_rules(rules_path=None, *, custom_rules_path=None, mode='basic'):
    return _rules(rules_path, custom_rules_path, mode)

def check_document(input_path, body=None, rules_path=None, *, custom_rules_path=None, mode='basic', classification_manifest=None):
    """旧body接口兼容；扩展模式必须传入绑定当前哈希、人工确认的完整分类清单。"""
    pkg = Package(input_path)
    scope, classification = _confirmed_scope(pkg, body, mode, classification_manifest)
    return _check(pkg, scope, _rules(rules_path, custom_rules_path, mode), classification)

def verify_document(output_path, body=None, rules_path=None, *, custom_rules_path=None, mode='basic', classification_manifest=None):
    return check_document(output_path, body, rules_path, custom_rules_path=custom_rules_path,
                          mode=mode, classification_manifest=classification_manifest)

# Order of properties in CT_PPr and CT_RPr: insert in schema order, never append after sectPr.
ORDER = {
 'tblPr':'tblStyle tblpPr tblOverlap bidiVisual tblStyleRowBandSize tblStyleColBandSize tblW jc tblCellSpacing tblInd tblBorders shd tblLayout tblCellMar tblLook tblCaption tblDescription tblPrChange'.split(),
 'tcPr':'cnfStyle tcW gridSpan hMerge vMerge tcBorders shd noWrap tcMar textDirection tcFitText vAlign hideMark headers cellIns cellDel cellMerge tcPrChange'.split(),
 'trPr':'cnfStyle divId gridBefore gridAfter wBefore wAfter cantSplit trHeight tblHeader tblCellSpacing jc hidden ins del trPrChange'.split(),
 'tblBorders':'top left start bottom right end insideH insideV'.split(),
 'tcBorders':'top left start bottom right end insideH insideV tl2br tr2bl'.split(),
 'pPr': 'pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr suppressLineNumbers pBdr shd tabs suppressAutoHyphens kinsoku wordWrap overflowPunct topLinePunct autoSpaceDE autoSpaceDN bidi adjustRightInd snapToGrid spacing ind contextualSpacing mirrorIndents suppressOverlap jc textDirection textAlignment textboxTightWrap outlineLvl divId cnfStyle rPr sectPr pPrChange'.split(),
 'rPr': 'rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow emboss imprint noProof snapToGrid vanish webHidden color spacing w kern position sz szCs highlight u effect bdr shd fitText vertAlign rtl cs em lang eastAsianLayout specVanish oMath rPrChange'.split()
}
def _ensure(parent, tag):
    found = parent.find(q(tag))
    if found is not None:
        return found
    element = ET.Element(q(tag))
    local = ET.QName(parent).localname
    if tag in ('pPr', 'rPr','tblPr','tcPr','trPr'):
        parent.insert(0, element)
    else:
        order = ORDER.get(local, [])
        rank = order.index(tag) if tag in order else len(order)
        for i, child in enumerate(parent):
            name = ET.QName(child).localname
            if name in order and order.index(name) > rank:
                parent.insert(i, element)
                break
        else:
            parent.append(element)
    return element

def _apply(pkg, f):
    if f['rule_id'] in ('R36','R37'):
        from .notes import apply
        return apply(pkg,f)
    if f['rule_id']=='R35':
        from .table_edges import apply
        return apply(pkg,f)
    if f['rule_id']=='R33':
        from .citations import apply
        return apply(pkg,f)
    rid, loc = f['rule_id'], f['locator']
    if rid in ('R30','R31','R32'):
        from .toc import apply
        apply(pkg,f);return
    if rid in ('R24','R26','R27'):
        from .front import apply
        apply(pkg,f);return
    if rid=='R23':
        from .table_text import apply
        apply(pkg,f);return
    if rid in ({f'R{i:02}' for i in range(13,23)}|{'R38','R39','R40','R41'}):
        from .academic import apply
        apply(pkg,f);return
    if rid not in IDS:
        from .extended import apply_extended
        apply_extended(pkg, f)
        return
    if 'section' in loc:
        s = pkg.sections[loc['section'] - 1]
        if rid == 'R01':
            e = _ensure(s, 'pgSz')
            e.set(q('w'), str(round(f['expected']['width_mm'] * 1440 / 25.4)))
            e.set(q('h'), str(round(f['expected']['height_mm'] * 1440 / 25.4)))
            e.attrib.pop(q('orient'), None)
        else:
            e = _ensure(s, 'pgMar')
            for a in ('top', 'bottom', 'left', 'right'):
                if a+'_mm' in f['expected']:e.set(q(a), str(round(f['expected'][a + '_mm'] * 1440 / 25.4)))
    else:
        p = pkg.paragraphs[loc['paragraph'] - 1]
        if rid in ('R03', 'R04', 'R05'):
            from .text_runs import executable_run,select_run
            r = executable_run(pkg,p,loc) if 'link' in loc else select_run(p,loc)
            rp = _ensure(r, 'rPr')
            if rid == 'R05':
                _ensure(rp, 'sz').set(q('val'), str(round(f['expected'] * 2)))
            else:
                rf = _ensure(rp, 'rFonts')
                slots = ['eastAsia'] if rid == 'R03' else list(f['actual'])
                for slot in slots:
                    rf.set(q(slot), f['expected'])
                    rf.attrib.pop(q(slot + 'Theme'), None)
        else:
            pp = _ensure(p, 'pPr')
            if rid == 'R06':
                spacing = _ensure(pp, 'spacing')
                spacing.set(q('line'), str(round(f['expected'] * 240)))
                spacing.set(q('lineRule'), 'auto')
            else:
                ind = _ensure(pp, 'ind')
                ind.set(q('firstLineChars'), str(round(f['expected'] * 100)))
                # A zero hanging attribute can still override firstLine; never introduce it.
                # Inherited hanging is deliberately unsupported (review, not fixable).
                ind.set(q('firstLine'), '0')
                for a in ('hanging', 'hangingChars'):
                    ind.attrib.pop(q(a), None)


def _preservation(pkg, changes):
    """白名单掩码：删除本次允许修改的属性，剩余整树必须完全一致。"""
    root = deepcopy(pkg.root)
    body = root.find(q('body'))
    ps = body.findall(q('p'))
    ss = body.findall('w:p/w:pPr/w:sectPr', NS) + body.findall('w:sectPr', NS)
    from .academic import canonical_keyword
    for n in {f['locator']['paragraph'] for f in changes if 'start' in f['locator']}:canonical_keyword(ps[n-1])
    for f in changes:
        loc, rid = f['locator'], f['rule_id']
        if rid in ('R36','R37'):continue
        if rid=='R35':
            from .table_edges import mask
            mask(root,f);continue
        if rid=='R33':
            from .citations import mask
            mask(ps[loc['paragraph']-1],f);continue
        if rid in ('R30','R31','R32'):
            from .toc import mask
            mask(root,f);continue
        if rid in ('R24','R26','R27'):
            if not f.get('story_part'):
                from .front import mask_main
                mask_main(root,f)
            continue
        if rid=='R23':
            from .table_text import mask
            mask(root,f);continue
        if rid in ({f'R{i:02}' for i in range(13,23)}|{'R38','R39','R40','R41'}):
            from .academic import mask
            mask(ps[loc['paragraph']-1],f);continue
        if rid not in IDS:
            from .extended import mask_extended
            mask_extended(ps[loc['paragraph']-1], f)
            continue
        if 'section' in loc:
            e = ss[loc['section'] - 1].find(q('pgSz' if rid == 'R01' else 'pgMar'))
            attrs = ('w', 'h', 'orient') if rid == 'R01' else tuple(a for a in ('top','bottom','left','right') if a+'_mm' in f['expected'])
        else:
            p = ps[loc['paragraph'] - 1]
            if rid in ('R03', 'R04', 'R05'):
                from .text_runs import select_run
                r = select_run(p,loc)
                e = r.find('w:rPr/w:' + ('sz' if rid == 'R05' else 'rFonts'), NS)
                slots = ['eastAsia'] if rid == 'R03' else list(f['actual']) if rid == 'R04' else []
                attrs = ['val'] if rid == 'R05' else slots + [s + 'Theme' for s in slots]
            else:
                e = p.find('w:pPr/w:' + ('spacing' if rid == 'R06' else 'ind'), NS)
                attrs = ['line', 'lineRule'] if rid == 'R06' else ['firstLineChars', 'firstLine', 'hanging', 'hangingChars']
        if e is not None:
            for a in attrs:
                e.attrib.pop(q(a), None)
    if any(f['rule_id'] in ('R24','R26','R27') for f in changes):
        from .front import prune
        prune(root)
    # Remove empty formatting containers that the patch is allowed to introduce.
    for e in reversed(list(root.iter())):
        if e.tag in {q(x) for x in ('rFonts', 'sz', 'spacing', 'ind', 'pPr', 'rPr')} and not len(e) and not e.attrib and not e.text:
            e.getparent().remove(e)
    from .front import story_fingerprint
    return ET.tostring(root, method='c14n')+b'\nSTORIES\n'+story_fingerprint(pkg,changes)

def fix_document(input_path, output_path, body, selected_rules=(), selected_keys=(), rules_path=None, *, custom_rules_path=None, mode='basic', classification_manifest=None):
    """选择规则/问题key，另存新DOCX，然后读回复查。待复核从不自动修正。

    返回before、after、changes、preservation；API不写报告，CLI负责报告输出。
    保存后复查或保留检查失败时删除本次生成的副本并抛出DemoError。
    """
    destination = new_path(output_path, input_path)
    if destination.suffix.lower() != '.docx':
        raise DemoError('输出必须为新的.docx路径')
    pkg, rules = Package(input_path), _rules(rules_path, custom_rules_path, mode)
    scope, classification = _confirmed_scope(pkg, body, mode, classification_manifest)
    from .backmatter import activate
    rules=activate(rules,classification)
    if rules.get('workbench'):
        from .rule_bundle import validate_scope_templates
        validate_scope_templates(rules,classification)
    before = _check(pkg, scope, rules, classification)
    if pkg.signed:
        raise DemoError('含数字签名，不支持修正')
    if pkg.ambiguous_sections:
        raise DemoError('有嵌套或修订分节，无法可靠确定全部节，不支持修正')
    ids, keys = set(selected_rules), set(selected_keys)
    if ids - (set(rules["rules"]) | ({"R44"} if mode=="academic" and classification and classification.get("reference_scope") else set()) | ({"R36","R37"} if mode=="academic" and classification and classification.get("note_scope") else set()) | ({"R33","R34"} if mode=="academic" and classification and classification.get("citation_scope") else set()) | ({"R30","R31","R32"} if mode=="academic" and classification and classification.get("toc_scope") else set()) | (set(__import__('core.front',fromlist=['IDS']).IDS) if mode=='academic' and classification and classification.get('front_scope') else set()) | (({'R23'} | ({'R35'} if classification['table_scope'].get('layout_options',{}).get('outer_edges') else set())) if mode=='academic' and classification and classification.get('table_scope') else set())) or keys - {f['key'] for f in before['findings']}:
        raise DemoError('选择含未知规则或问题key')
    if not ids and not keys:
        raise DemoError('须显式选择修正规则或问题key')
    selected = [f for f in before['findings'] if f['fixable'] and (f['rule_id'] in ids or f['key'] in keys)]
    skipped = [f for f in before['findings'] if (f['rule_id'] in ids or f['key'] in keys) and f['status'] == 'review']
    # Do not mix index-based ordinary-run patches with character-based splitting in one paragraph.
    citation_paras={f['locator']['paragraph'] for f in selected if f['rule_id']=='R33'}
    if any(f['rule_id']!='R33' and 'run' in f['locator'] and f['locator'].get('paragraph') in citation_paras for f in selected):
        raise DemoError('同段引文拆分与普通run字体字号修正须分轮选择：先完成普通格式，再修引文；未写输出')
    original_pkg=Package(input_path) if citation_paras else None
    baseline = _preservation(pkg, selected)
    # Freeze R11 inheritance before applying explicitly selected title-format changes.
    selected.sort(key=lambda f: f['rule_id'] != 'R11')
    for f in selected:
        if f['rule_id'] == 'R11':
            from .extended import formatting_snapshot, snapshots_equal
            p = pkg.paragraphs[f['locator']['paragraph']-1]
            effective_before = formatting_snapshot(pkg, p)
            _apply(pkg, f)
            if not snapshots_equal(effective_before, formatting_snapshot(pkg, p)):
                raise DemoError('标题样式改变了未选有效格式，未写输出')
        else:
            _apply(pkg, f)
    if original_pkg is not None:
        from .citations import partition_guard
        partition_guard(original_pkg,pkg,selected)
    if baseline != _preservation(pkg, selected):
        raise DemoError('修改超出允许的格式属性，未写输出')
    if Path(input_path).read_bytes() != pkg.raw:
        raise DemoError('原稿在处理中发生变化，未写输出')
    write_new(destination, pkg.bytes(bool(selected)), input_path)
    try:
        saved = Package(destination)
        # Reuse the SAME loaded rules object; no re-reading a changed config mid-transaction.
        saved_classification = deepcopy(classification) if classification else None
        if saved_classification is not None:
            saved_classification['input_sha256'] = saved.hash
            from .table_text import rebind
            rebind(saved_classification,saved.hash)
        after = _check(saved, scope, rules, saved_classification)
        after_by_key = {f['key']: f for f in after['findings']}
        if original_pkg is not None:partition_guard(original_pkg,saved,selected)
        preserved = baseline == _preservation(saved, selected)
        allowed_story_parts={f['story_part'] for f in selected if f.get('story_part')}
        others = all(saved.parts.get(n) == data for n, data in pkg.parts.items() if n != 'word/document.xml' and n not in allowed_story_parts) and set(saved.parts)==set(pkg.parts)
        main_bytes_equal=saved.parts['word/document.xml']==pkg.parts['word/document.xml']
        if selected and all(f.get('story_part') for f in selected) and not main_bytes_equal:raise DemoError('仅修改独立注释/故事部件时主文档字节必须保持')
        unchanged_other_members=all(saved.parts.get(n)==data for n,data in pkg.parts.items() if n!='word/document.xml')
        original = sha256(Path(input_path).read_bytes()) == pkg.hash
        if not preserved or not others or not original:
            raise DemoError('内容、包内对象或原稿完整性验证失败')
        changes = [{'key': f['key'], 'rule_id': f['rule_id'], 'locator': f['locator'],
                    'before': f['actual'], 'after': after_by_key[f['key']]['actual'],
                    'verification': after_by_key[f['key']]['status'], 'source': f['source'],
                    **({'dependency_note': f['dependency_note'], 'preserved_format_patch': f['preserved_format_patch']} if 'preserved_format_patch' in f else {}),
                    **({'attribute_cleanup_note':('引文必要run拆分仅改变所选字符上标；字号/字体/前后文字保留。通用正文会新增特殊run覆盖提示；run编号及问题key可能重新定位，不能把记录拆分直接当作属性新错或已解决。' if f['rule_id']=='R33' else f.get('dependency_note','关键词普通w:t片段安全拆分；按字符属性白名单验证，文字/其余属性保持'))} if f['rule_id']=='R33' or f['rule_id'] in {f'R{i:02}' for i in range(13,23)} else {})} for f in selected]
        if any(c['verification'] != 'pass' for c in changes):
            raise DemoError('选中修正项读回复查未通过')
    except Exception:
        destination.unlink()
        raise
    manifest = {'input_sha256': saved.hash, 'body_paragraphs': scope,
                'confirmation': '沿用本次人工确认的顶层段落编号；结构保留核对通过'}
    from .dependencies import problem_delta
    delta = problem_delta(before, after)
    return {'before': before, 'after': after, 'changes': changes,
            'problem_delta': delta,
            **({'output_classification_manifest': saved_classification} if saved_classification else {}),
            'skipped_review_keys': [f['key'] for f in skipped], 'output': str(destination), 'output_body_manifest': manifest,
            'preservation': {'original_sha256_unchanged': original, 'document_except_selected_format_attributes_equal': preserved,
              'other_zip_member_bytes_equal': unchanged_other_members, 'unselected_zip_member_bytes_equal':others,'selected_story_parts_format_only':preserved,'selected_story_part_count':len(allowed_story_parts),'main_document_bytes_equal':main_bytes_equal, 'verified_objects': 'document.xml与所选故事部件仅允许所选格式属性变化；未选ZIP成员字节一致，含文本、表格、媒体、关系、编号及分节结构。不证明全部显示行为。'}}

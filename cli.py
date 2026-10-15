#!/usr/bin/env python3
"""本地CLI。检查退出码：0覆盖内无问题，1有问题，2有待复核，3输入/执行错误。"""
import argparse
import json
import sys
from pathlib import Path
from core import inspect_document, check_document, fix_document, suggest_paragraph_types
from core.package import DemoError, new_path, write_new
from core.report import write_report


def ranges(value):
    result = []
    try:
        for part in value.split(','):
            pair = part.split('-')
            if len(pair) == 1:
                result.append(int(pair[0]))
            elif len(pair) == 2 and int(pair[0]) <= int(pair[1]):
                result.extend(range(int(pair[0]), int(pair[1]) + 1))
            else:
                raise ValueError()
    except ValueError as e:
        raise argparse.ArgumentTypeError('正文范围示例：4-6,11,14-15') from e
    return result


def preflight(paths, input_path):
    resolved = [Path(p).resolve() for p in paths]
    if len(resolved) != len(set(resolved)):
        raise DemoError('输出路径之间冲突')
    for p in paths:
        new_path(p, input_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description='论文有格课程Demo：基础R01–R07、显式扩展R01–R12、单文档academic R01–R22，人工确认范围')
    sub = parser.add_subparsers(dest='command', required=True)
    for cmd in ('inspect', 'classify', 'check', 'fix'):
        p = sub.add_parser(cmd)
        p.add_argument('input', type=Path)
        p.add_argument('--report', type=Path, required=True, help='新的JSON路径；check/fix同时生成同名.md')
        if cmd not in ('inspect','classify'):
            scope = p.add_mutually_exclusive_group(required=True)
            scope.add_argument('--body-manifest', type=Path, help='带输入SHA256的正文清单JSON')
            scope.add_argument('--classification-manifest', type=Path, help='人工确认且绑定输入哈希的完整分类清单；配合--mode extended/academic')
            p.add_argument('--mode',choices=['basic','extended','academic'],default='basic',help='默认保持R01–R07；extended R01–R12，academic R01–R22')
            scope.add_argument('--body-ranges', type=ranges, help='人工确认的顶层段落编号，1起始')
            config = p.add_mutually_exclusive_group()
            config.add_argument('--rules', type=Path, help='已核对的固定规则JSON路径')
            config.add_argument('--custom-rules', type=Path, help='显式确认的演示配置（旧R05/R06配置或R01–R07版本2模板）')
        if cmd == 'fix':
            p.add_argument('--output', type=Path, required=True)
            p.add_argument('--select', default='', help='逗号分隔规则ID，如R01,R02,R05')
            p.add_argument('--select-key', action='append', default=[], help='报告问题key，可多次指定')
            p.add_argument('--recheck-report', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.report.suffix != '.json':
            raise DemoError('--report须为.json路径')
        if args.command in ('inspect','classify'):
            preflight([args.report], args.input)
            data = inspect_document(args.input) if args.command=='inspect' else suggest_paragraph_types(args.input)
            write_new(args.report, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode(), args.input)
            print(f"段落建议/清单：{args.report}，{len(data['paragraphs'])}个顶层段落。请人工确认正文范围。")
            return 0
        body = args.body_manifest if args.body_manifest is not None else args.body_ranges
        rule_args = {'custom_rules_path':args.custom_rules} if args.custom_rules else {'rules_path':args.rules}
        rule_args.update(mode=args.mode,classification_manifest=args.classification_manifest)
        paths = [args.report, args.report.with_suffix('.md')]
        if args.command == 'fix':
            if args.recheck_report.suffix != '.json':
                raise DemoError('--recheck-report须为.json路径')
            manifest_path = args.output.with_suffix('.body.json')
            if args.mode!='basic':paths.append(args.output.with_suffix('.types.json'))
            paths += [args.output, args.recheck_report, args.recheck_report.with_suffix('.md'), manifest_path]
        preflight(paths, args.input)
        if args.command == 'check':
            data = check_document(args.input, body, **rule_args)
            write_report(args.report, data, args.input)
        else:
            ids = [s.strip() for s in args.select.split(',') if s.strip()]
            result = fix_document(args.input, args.output, body, ids, args.select_key, **rule_args)
            write_report(args.report, result, args.input, modification=True)
            data = result['after']
            write_report(args.recheck_report, data, args.input)
            write_new(manifest_path, (json.dumps(result['output_body_manifest'], ensure_ascii=False, indent=2) + '\n').encode(), args.input)
            if args.mode!='basic':write_new(args.output.with_suffix('.types.json'),(json.dumps(result['output_classification_manifest'],ensure_ascii=False,indent=2)+'\n').encode(),args.input)
            print(f"已生成修正版：{args.output}；{len(result['changes'])}项修改读回复查通过。")
        print(json.dumps(data['summary'], ensure_ascii=False))
        print(f"报告：{args.report}（同名.md供阅读）")
        return 1 if data['summary']['problem_count'] else 2 if data['summary']['review_count'] else 0
    except (DemoError, OSError, ValueError) as e:
        print(f'错误：{e}', file=sys.stderr)
        return 3

if __name__ == '__main__':
    raise SystemExit(main())

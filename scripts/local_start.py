"""Double-click entry's standard-library bootstrap; use the existing venv only."""
from pathlib import Path
import sys,argparse,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from local_tools import launch,environment,deep_check

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');p.add_argument('--deep-word',action='store_true');p.add_argument('--no-open',action='store_true');args=p.parse_args()
    try:
        if args.deep_word:print(json.dumps(deep_check(),ensure_ascii=False,indent=2))
        elif args.check:print(json.dumps(environment(),ensure_ascii=False,indent=2))
        else:print('已复用本项目服务，打开网页。' if launch(not args.no_open)=='reused' else '本项目服务已启动，打开网页。')
        return 0
    except Exception as exc:print('启动/自检未完成：'+str(exc),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())

"""Full local suite with a hard paid-endpoint guard. No real DeepSeek in tests."""
from pathlib import Path
import sys,unittest,os,argparse
from unittest.mock import patch
from urllib.request import OpenerDirector
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pattern',default='test*.py');args=parser.parse_args()
    original=OpenerDirector.open;blocked=[];word_blocked=[]
    def block_word(*a,**kw):
        word_blocked.append('Word');raise AssertionError('Real Word automation blocked by offline test runner')
    def guarded(self,request,*args,**kwargs):
        url=request.full_url if hasattr(request,'full_url') else str(request)
        if urlsplit(url).hostname=='api.deepseek.com':
            blocked.append('paid-endpoint');raise AssertionError('Real API request blocked by offline test runner')
        return original(self,request,*args,**kwargs)
    from ai.short_spec import settings
    # Every imported settings alias shares this function. Defaults omit the real
    # .env; explicit temporary config arguments in configuration tests still work.
    with patch.object(settings,'__defaults__',(None,None)),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'YOUR_DEEPSEEK_API_KEY'}),patch('ai.attempts.TEST_MODE',True),patch('core.word_native.calculate',block_word),patch('core.word_native.export_pdf',block_word),patch.object(OpenerDirector,'open',guarded):
        result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=args.pattern))
    print('Real paid requests sent: 0; blocked unmocked attempts:',len(blocked))
    print('Real Word automation calls: 0; blocked unmocked attempts:',len(word_blocked))
    return 0 if result.wasSuccessful() and not blocked and not word_blocked else 1
if __name__=='__main__':raise SystemExit(main())

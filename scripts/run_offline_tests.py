"""Full local suite with a hard paid-endpoint guard. No real DeepSeek in tests."""
from pathlib import Path
import sys,unittest
from unittest.mock import patch
from urllib.request import OpenerDirector
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    original=OpenerDirector.open;blocked=[]
    def guarded(self,request,*args,**kwargs):
        url=request.full_url if hasattr(request,'full_url') else str(request)
        if urlsplit(url).hostname=='api.deepseek.com':
            blocked.append('paid-endpoint');raise AssertionError('Real API request blocked by offline test runner')
        return original(self,request,*args,**kwargs)
    with patch.object(OpenerDirector,'open',guarded):
        result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
    print('Real paid requests sent: 0; blocked unmocked attempts:',len(blocked))
    return 0 if result.wasSuccessful() and not blocked else 1
if __name__=='__main__':raise SystemExit(main())

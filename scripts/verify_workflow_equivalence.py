"""Read actual browser downloads; compare bytes/ZIP independently of the engines."""
import argparse,hashlib,json,zipfile
from pathlib import Path

def verify(before,after):
 a,b=Path(before),Path(after)
 raw_a,raw_b=a.read_bytes(),b.read_bytes()
 assert raw_a==raw_b,'Downloaded DOCX bytes differ'
 with zipfile.ZipFile(a) as x,zipfile.ZipFile(b) as y:
  assert x.namelist()==y.namelist()
  assert all(x.read(n)==y.read(n) for n in x.namelist())
  parts=len(x.namelist())
 return {'docx_bytes_equal':True,'all_zip_members_equal':True,'sha256':hashlib.sha256(raw_a).hexdigest(),'bytes':len(raw_a),'zip_members':parts,'scope':'same existing input, rules, scope and explicit choices; website layout only'}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('before');p.add_argument('after');a=p.parse_args();print(json.dumps(verify(a.before,a.after),ensure_ascii=False,indent=2))

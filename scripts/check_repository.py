"""Read-only repository portability audit; no API, renderer, document modifications."""
import hashlib,json,re
from pathlib import Path
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]
errors=[]
for path in (ROOT/'tests').glob('test_*.py'):
 if re.search(r"(?:['\"])work/phase\d+",path.read_text()):errors.append(f'{path.name}: local historical fixture dependency')
for x in json.loads((ROOT/'tests/fixtures/history/manifest.json').read_text()):
 p=ROOT/'tests/fixtures/history'/x['file']
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=x['sha256']:errors.append('Fixture hash mismatch: '+x['file'])
for p in [ROOT/'README.md',*(ROOT/'docs').rglob('*.md')]:
 for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  target=unquote(target.split('#')[0].strip('<>'))
  if not (p.parent/target).exists():errors.append(f'{p.relative_to(ROOT)}: missing local link {target}')
if errors:raise SystemExit('\n'.join(errors))
print('OK: document links, fixture hashes, no test dependency on work/phase*')

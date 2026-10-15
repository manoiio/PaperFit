"""Explicit exclusions survive rounds and snapshots; bulk classification cannot override them."""
from copy import deepcopy
from core.package import DemoError
class MaterialSession:
 def exclude_materials(self,numbers,reason):
  self._current()
  if self.mode!='academic' or not numbers or type(reason) is not str or not reason.strip() or len(reason)>120 or any(ord(c)<32 for c in reason):raise DemoError('请明确选择有效段落和简短排除原因')
  if any(type(n) is not int or str(n) not in self.paragraph_types for n in numbers):raise DemoError('排除范围超出当前文件')
  for n in numbers:self.material_exclusions[str(n)]=reason;self.paragraph_types[str(n)]='other'
  self.body=sorted(int(n) for n,t in self.paragraph_types.items() if t=='body');self.invalidate(preserve_tables=True)
 def release_materials(self,numbers,*,acknowledged=False):
  self._current()
  if acknowledged is not True:raise DemoError('须明确确认解除材料保护；仍不自动改分类')
  for n in numbers:self.material_exclusions.pop(str(n),None)
  self.invalidate(preserve_tables=True)

#!/bin/bash
# Repository-relative; works when launched from Finder or another directory.
cd -- "$(dirname -- "$0")" || exit 1
if [ ! -x ".venv/bin/python" ]; then
  echo '未找到现有.venv。请联系维护人员恢复项目环境；启动器不会安装、升级或重建。'
  read -r -p '按回车关闭窗口…' _
  exit 1
fi
.venv/bin/python scripts/local_start.py
status=$?
if [ "$status" -ne 0 ] && [ -t 0 ]; then
  read -r -p '请保留上方错误；按回车关闭窗口…' _
fi
exit "$status"

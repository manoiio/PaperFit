# 第47阶段公开组合夹具与证据

所有文字为公开合成材料，无真实论文或个人信息。原始roles/expected由作者独立指定，非本轮模型生成。不要重新生成errors.docx后套用已有哈希或API回执。

- `errors.docx`：14个顶层段落、脚注尾注及保护内容；`roles.json`明确代码排除，`expected.json`手写12字段及XML声明。
- `requirements.txt`：真实API使用的固定用户示例；`rules.json`实际第三次调用后保存的完整要求，无论文及旧授权。
- `failed-request/response.json`：本轮第1次真实拒绝；`accepted-request/response.json`：第3次真实通过，均经公开合成内容审查。`api-records.json`记录全部3次，收费状态未知。
- `fixed.docx`、`result.zip`：第3次真实API参与的浏览器下载；包内含复查、范围、规则、阅读报告和变更。`independent.json`为原合法路径同字节及独立ZIP/XML结果。
- `dynamic-independent.json`：智能结果页单独授权既有动态流程的实际下载核对。输入复用仓库phase23/40夹具，未增加动态算法。
- `performance.json`：本机基本开销，不是速度/准确率提升。
- `screenshots/`：真实Chrome结果、原生控件与单独动态采用；`previews/`：真实LibreOffice原稿/最终各1页，已全部查看。Word本轮实际打开相同最终字节并关闭未保存，未将页图当作Word证据。

离线复现（新输出目录）：

```bash
.venv/bin/python scripts/reproduce_paragraph_workflow.py --output /tmp/paperfit47-proof --browser-zip samples/phase47/result.zip
```

已收响应零API重放 → 原严格验证 → 原合法检查/选择/生成 → 作者独立XML/ZIP oracle → 实际浏览器DOCX同字节。无需work、outputs、API配置、Word或渲染器。完整测试仍使用 `scripts/run_offline_tests.py`。

直接使用 `scripts/verify_paragraph_output.py` 可核对本组合文件（具体参数见脚本）。此oracle仅适用于手写标注的公开夹具，不是通用论文检查器。

完整范围、精度、调用记录和限制见[阶段验收](../../docs/acceptance/phase47.md)。格式声明通过不代表全文合格；动态数字同步未刷新域或真实页码。

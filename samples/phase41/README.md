# 第41阶段可移植验收材料

- `structure.docx` / `labels.json`：21个顶层段落的小型合成结构夹具，作者先行标注；无真实论文。含虚构身份字段、代码/数据和指令样文字，验证不作为AI候选及不被格式修改。
- `real-receipt.json`：一次真实DeepSeek结构请求的显式脱敏回执导出，只含建议角色/ID、哈希、usage，不含完整请求摘录、模型原始内容、密钥或路径。不是可导入范围授权。
- `fixed.docx` / `result.zip`：实际浏览器下载的最终文件，源文档仍为原稿；包含7项正确AI结构补充和1项人工层级纠正。结果剩余5个问题、12项待复核，不是全文合格。
- `independent.json`：独立原合法修正路径同字节对照、原始ZIP/XML断言及真实请求与人工标签逐项对照。AI第一次响应7正确、1错误、0弃权，没有重试挑选响应。无编号“实现步骤”层级错误须人工纠正。
- `screens/`：真实网页操作截图，不是Word或DOCX排版视觉验收。

```sh
python scripts/reproduce_structure_workflow.py --output /tmp/paperfit41-offline
```

输出目录必须不存在。无需API、Word、渲染器、学校PDF、历史work/outputs。本脚本不重放或伪造真实请求，只使用事先人工标注的最终分类，与原合法路径对照。

核对实际下载：

```sh
python scripts/reproduce_structure_workflow.py --output /tmp/paperfit41-download \
  --browser-docx samples/phase41/fixed.docx --browser-zip samples/phase41/result.zip \
  --receipt samples/phase41/real-receipt.json
```

目录/引文/注释等可选模块不自动启用，Word字段、动态编号能力没有扩展。本地与AI建议都仍需接受范围摘要；结构校验不能证明语义分类准确。

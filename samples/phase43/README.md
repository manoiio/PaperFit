# 第43阶段：两入口与自动范围

组合夹具复用[第21阶段脚注尾注原稿](../phase21/errors.docx)和[既有表格样本](../table-text-errors.docx)的嵌套表。没有真实论文或个人信息。

- [errors.docx](errors.docx)：身份封面表、普通内容表、嵌套保护表、3脚注/3尾注及正文引用、系统分隔符/域/链接等既有对象。
- [独立用途/错误清单](labels.json)：人工编写，未用AI响应生成答案；普通表2预期宋体10.5pt，注释仅原有宋体12pt/1.5倍。表1、3子树及全部标记/关系保持。
- [smart.docx](smart.docx) / [智能流实际结果包](smart.zip)：浏览器在明确无API配置进程中运行，同页手动确认一张表的用途，自动准备6条注释；不冒充真实AI识别。
- [local.docx](local.docx) / [本地流实际结果包](local.zip)：真实浏览器恢复项目、调整范围、预演明确采用、恢复内容表用途并批量处理；当前输入仍原稿。最终与智能下载同字节。
- [mock-structured.docx](mock-structured.docx) / [模拟结构结果包](mock-structured.zip)：作者标签构造的模拟批量响应参与实际原引擎处理；不是实网结果。相比无配置浏览器多纳入段落2，所以17项修改，不能拿它与不同范围的16项输出直接宣称同字节。
- [smart-audit.json](smart-audit.json)：本地/失败降级、明确决定、最终范围和本次命令授权记录，无原始请求全文。
- [independent.json](independent.json)：实际下载与相同最终范围的原合法路径同字节，原始ZIP/XML独立核对。
- [request-audit.json](request-audit.json)：早期测试漏模拟路径的离线审计；**早期实际计费次数不能核实，不宣称满足原3次预算。**用户追加授权1次后单列真实回执，不补造历史。

- [live.docx](live.docx) / [实网流程结果包](live.zip) / [实网回执与决定](live-audit.json)：额外授权的1次合成请求；模型对段落2与表2均返回pending，没有可接受AI建议。用户同页确认表2后自动处理16项，未再次请求；与上述离线浏览器及原合法路径同字节。不是AI成功识别表格用途的证据。

```bash
python scripts/reproduce_dual_entry_workflow.py --output /tmp/paperfit43-result --browser-zip samples/phase43/live.zip
python scripts/run_offline_tests.py
```

输出目录须不存在。复现只用作者标签的模拟响应，0API；不依赖work/outputs、学校PDF、Word、渲染器或密钥。脚本先独立证明字符/结构保留，再将输出范围哈希重新绑定固定原稿，按相同对象、规则与选择走原确认/修正路径。不是把导出成功声明当证据。

只允许所选普通文字属性变化；全部文字顺序、未选ZIP成员、封面和嵌套表、注释自动标记/系统对象、关系/媒体/域保持。表格数字“12”不强制改中文字体槽位，独立核对区分实际适用属性。

## 网页证据

[两入口及智能范围结果1280](screens/smart-result-1280.png) · [本地安全项方案1440](screens/local-plan-1440.png) · [本地结果与原输入身份1440](screens/local-result-1440.png) · [表格用途集中问题1280](screens/table-question-1280.png)。

[追加授权实网最终下载1280](screens/live-result-1280.png)。截图是网页，不是Word/渲染验收。智能流初次无配置后集中确认1张表，复查仍1问题/15待复核；没有宣称全文合格。原快捷页面已删除，其能力迁入五步工作台。完整迁移表、实际浏览器调试/修正过程及测试口径见[阶段记录](../../docs/acceptance/phase43.md)。

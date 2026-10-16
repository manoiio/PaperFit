# 第三十七阶段：真实网页与状态证据

复用仓库已有合成文档，没有新增演示论文、AI调用或渲染。以下1280×720前后对照均为相同内置错误样本、2015默认规则、6段正文；预演/输出均明确选择11项，当前处理输入为原稿。

| 状态 | 基线53ce2d2 | 本阶段 |
| --- | --- | --- |
| 首次进入，无文件 | [改版前](screens/before-empty-1280.png) | [改版后](screens/after-empty-1280.png)、[1440×900](screens/after-empty-1440.png) |
| 已载入，尚未检查 | [改版前](screens/before-loaded-1280.png) | [改版后](screens/after-loaded-1280.png) |
| 有效检查，未选择 | [改版前](screens/before-problems-1280.png) | [改版后](screens/after-problems-1280.png) |
| 真实预演待采用 | [改版前](screens/before-rehearsal-1280.png) | [改版后](screens/after-rehearsal-1280.png)、[1440×900](screens/after-rehearsal-1440.png) |
| 已采用，输入仍原稿 | [改版前](screens/before-output-1280.png) | [改版后](screens/after-output-1280.png)、[1440×900](screens/after-output-1440.png) |

其他真实流程：[范围编辑后原检查不可用](screens/invalidated-1280.png)；[已有阶段31正确对照，仅段3进入基础检查：0问题/3待复核](screens/zero-problems-review-1440.png)。这些是不同状态，不能混作同状态对照。

[单项字号下载独立核对](single-independent.json)：仅`R05:paragraph=4:run=2`，剩余10问题/0格式待复核，DOCX/全部18成员与原合法路径一致。[11项下载及结果包核对](all-independent.json)：DOCX/18成员一致，结果ZIP内DOCX与真实单文件下载一致。文件内容可从既有样本离线复现，不提交运行任务、私人路径、原稿或新排版产物。

```bash
python scripts/reproduce_reader_workflow.py --output /tmp/paperfit37-reference
# 可选，核对真实网页的11项选择下载
python scripts/reproduce_reader_workflow.py --output /tmp/paperfit37-compare --download DOWNLOADED.docx
python -m unittest tests.test_workspace_status tests.test_workflow_ui tests.test_reader_ui tests.test_decision_ui tests.test_editing_ui
```

输出目录须不存在。自动UI测试不是浏览器或Word验收；截图是网页，不是论文页图。输出相同字节，本阶段不重复Word/渲染，不冒充新增排版观察。[完整验收和限制](../../docs/acceptance/phase37.md)。

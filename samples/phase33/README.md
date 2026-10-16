# 第三十三阶段网页验收索引

仅复用既有合成样本，没有新增论文演示案例或排版规则。

- [基本原稿](../errors.docx)、[原正文范围](../errors.body.json)：前后均选全部11条安全格式问题，真实下载的DOCX逐字节相同。
- [独立等价核对](equivalence.json)：直接读取浏览器下载，未调用新比较器或检查引擎。
- 两步流程复用[阶段28原稿及范围](../phase28/README.md)；最终下载与原合法两轮路径核对，见[独立证据](plan-equivalence.json)。
- [完整验收、操作和限制](../../docs/acceptance/phase33.md)。本机实际下载及项目包位于`work/phase33/`，不作为仓库运行依赖。

## 同窗口、同状态前后截图

| 状态 | 1280×720 改版前 / 后 | 1440×900 改版前 / 后 |
| --- | --- | --- |
| 无文件 | [前](screenshots/before-empty-1280.png) / [后](screenshots/after-empty-1280.png) | [前](screenshots/before-empty-1440.png) / [后](screenshots/after-empty-1440.png) |
| 载入、范围待确认 | [前](screenshots/before-range-1280.png) / [后](screenshots/after-range-1280.png) | [前](screenshots/before-range-1440.png) / [后](screenshots/after-range-1440.png) |
| 检查问题 | [前](screenshots/before-problems-1280.png) / [后](screenshots/after-problems-1280.png) | [前](screenshots/before-problems-1440.png) / [后](screenshots/after-problems-1440.png) |
| 预演完成待采用 | [前](screenshots/before-rehearsal-1280.png) / [后](screenshots/after-rehearsal-1280.png) | [前](screenshots/before-rehearsal-1440.png) / [后](screenshots/after-rehearsal-1440.png) |
| 正式采用结果 | [前](screenshots/before-results-1280.png) / [后](screenshots/after-results-1280.png) | [前](screenshots/before-results-1440.png) / [后](screenshots/after-results-1440.png) |

旧长页的报告/预演/结果截图定位其对应标题；新页面保留顶部文件和步骤上下文。截图来自真实Streamlit页面，未拼接或重画。前后像素比较不作为DOCX验收。

附加真实流程：[长文跨页选择](screenshots/long-selection.png)、[范围改变后失效](screenshots/scope-invalidated.png)、[服务重启后恢复](screenshots/restored-project.png)、[两步计划预演](screenshots/two-step-plan.png)。

[规则编辑与明确应用](screenshots/rule-draft-applied.png)：未提交值切页保留，只有应用后检查失效；不是自动授权。

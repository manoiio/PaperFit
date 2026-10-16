# 第三十四阶段网页证据

仅复用既有合成样本，没有新增演示案例或论文内容。本目录包含真实Chrome页图及独立下载字节核对JSON；不含本机项目ZIP、DOCX、密钥、日志和私人路径。

## 同状态前后

内置错误样本、默认基础规则、相同正文范围；问题页未选择，预演页明确选择11项且未采用，结果页实际采用第1轮但输入仍为原稿。每对窗口一致。

| 页面/窗口 | 改版前 | 改版后 |
| --- | --- | --- |
| 问题 1280×720 | [前](screenshots/before-problems-1280.png) | [后](screenshots/after-problems-1280.png) |
| 问题 1440×900 | [前](screenshots/before-problems-1440.png) | [后](screenshots/after-problems-1440.png) |
| 预演 1280×720 | [前](screenshots/before-rehearsal-1280.png) | [后](screenshots/after-rehearsal-1280.png) |
| 预演 1440×900 | [前](screenshots/before-rehearsal-1440.png) | [后](screenshots/after-rehearsal-1440.png) |
| 结果 1280×720 | [前](screenshots/before-results-1280.png) | [后](screenshots/after-results-1280.png) |
| 结果 1440×900 | [前](screenshots/before-results-1440.png) | [后](screenshots/after-results-1440.png) |

## 复杂与交互状态

- [8问题、6可修正、2只读、44待复核](screenshots/complex-problems-1440.png)：阶段32原有合成项目。
- [仅改1项后仍有7问题/44待复核](screenshots/partial-results-1280.png)：没有用绿色结果块暗示全文合格。
- [长文页码2、119项选择、80项筛选外](screenshots/long-selection-retained.png)：既有400段明确范围，2015条finding，往返问题/预演后保留。
- [范围调整后失效](screenshots/scope-invalidated.png)：查看问题禁用，当前确认待核对。
- [两步计划预演](screenshots/two-step-rehearsal.png)、[正式采用结果](screenshots/two-step-results.png)：原阶段28多对象案例，新问题及无法对齐不隐藏；采用不自动切换输入。
- [重启恢复后重新检查](screenshots/restored-project.png)：网页保存、服务重启、真实上传和明确恢复。

## 下载独立核对

- [基本11项前后下载同字节](equivalence.json)：38,754字节/18个ZIP成员。
- [复杂对象仅一个链接run字号](partial-equivalence.json)：39,413字节/20个ZIP成员，与原合法直接路径逐字节一致。
- [两步最终副本](plan-equivalence.json)：38,201字节/18个ZIP成员，与手工合法两轮同字节。
- [自动/浏览器结果摘要与文件哈希](evidence.json)。

复用原有`python scripts/verify_workflow_equivalence.py BEFORE.docx AFTER.docx`独立读取ZIP与实际下载，不调用新呈现模块自证。可移植源样本、范围和复现器分别在[samples](../README.md)、[单轮](../../scripts/reproduce_rehearsal_demo.py)、[计划](../../scripts/reproduce_plan_demo.py)和[内部链接](../../scripts/reproduce_internal_reference_demo.py)。输出目录须不存在。

本轮没有DOCX内容或格式引擎变化，三种实际下载均同字节，故不重复整套Word/渲染。页图是网页界面验收，不是DOCX渲染或真实链接跳转验收；0新增AI、0自动渲染。

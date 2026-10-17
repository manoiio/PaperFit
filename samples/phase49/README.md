# 第49阶段公开证据

复用[第48阶段8页原稿](../phase48/existing.docx)，不含真实论文、密钥或私人请求。新上传、没有作者项目：上传→选择含章节页脚的完整方案→开始→下载，4个主要操作，0个边界决定、0API。另一个实网任务增加一次[补充文字](requirements.txt)，1次请求，没有额外人工决定或高级页面。

- [最终实际浏览器下载](fixed.docx)、[最终规则包](rules.json)、[完整结果包](result.zip)、[普通格式中间副本](step1.docx)。当前处理输入没有自动切换。
- [独立手写预期](expected.json)、[ZIP/XML证明](xml-proof.json)、[原合法路径同字节](independent.json)、[处理记录](audit.json)。原图表题/正文引用因关联证据不足保持，数字同步0处。
- [真实请求](public-request.json)、[原响应](public-response.json)、[本地适配](adapted.json)、[回执](api.json)。仅公开合成输入，789tokens、0.949秒；费用未知。不是模拟或历史响应冒充实网。
- [全部8页LibreOffice图](previews/all-pages.jpg)、[渲染记录](render-record.json)、[Word真实观察及哈希](word-observation.json)。Word截图：[封面](screenshots/word-cover.png)、[前置](screenshots/word-front.png)、[正文5/6](screenshots/word-body-5-6.png)、[跨章7/8](screenshots/word-body-7-8.png)。
- 网页：[旧分类模块仍询问正文起点](screenshots/before-body-question.png)（旧主分类＋当前UI适配，非整套旧版部署）、[新上传直接完成](screenshots/fresh-complete.png)、[实网页码策略完成](screenshots/real-policy-complete.png)、[必要问题共用一次答案](screenshots/shared-question.png)。
- [机器验收摘要](validation.json)、[文件哈希索引](manifest.json)。

默认新上传输出`13889564…`与第48阶段实际新上传后人工选择起点的副本一致；本目录最终实网输出`1587cea3…`将正文从5开始，封面/前置和章间连续方案按已选授权保留。前后截图不是Word排版引擎验收，XML也不替代实际页码观察。

复现无需API、Word、渲染器或本机历史目录：

```sh
python scripts/reproduce_structure_plan.py --output /tmp/paperfit49-proof
python scripts/replay_ai_diagnostic.py samples/phase49/public-request.json samples/phase49/public-response.json --output /tmp/paperfit49-replay.json
```

范围是实际接受范围，不是全文覆盖率。合成的“目录 — 前置第二页”不是独立目录标题，自动分类仍按摘要区普通文字；两处题注保持待核对。最终2项只读问题、29项待留意，不扩写摘要、不生成参考文献、不补造题注关联。完整源代码与测试边界见[阶段记录](../../docs/acceptance/phase49.md)。

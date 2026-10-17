# 第48阶段公开合成证据

只含作者构造的普通文字、题注和纯文本引用，无课程论文/个人资料。`roles.json`和`expected.json`先于处理、渲染和模型响应写定，不由新解析器生成标准答案。0真实API。

- [已有分节原稿](existing.docx)、[原本单节原稿](single.docx)：各8页，多页封面、两页前置、两章正文。简单共享页脚，首页/奇偶变体均启用。
- [最终实际浏览器下载](fixed.docx)、[普通格式中间稿](step1.docx)、[数字同步中间稿](step2.docx)、[单节新增分节结果](single-fixed.docx)。当前输入不会自动变为输出。
- [实际浏览器结果包](result.zip)：最终DOCX、最终完整报告、规则/范围及各步修改和复查摘要；不含中间DOCX，中间副本见上面的独立下载。
- [可复用要求](rules.json)：完整原规则包＋可选assembly策略，没有本篇分区ID。新文件仍需可靠起点。
- [明确文字要求](requirements.txt)、[作者分类](roles.json)、[独立预期](expected.json)。三条确定策略本地证明；不是新学校规范，也不是AI实际调用样本。
- [独立ZIP/XML核对](independent.json)、[阶段父子哈希](assembly-summary.json)、[结构计划与证明](page-layout.json)、[修改记录](changes.md)、[复查](recheck.md)。结构项与普通格式处数、数字变化分别计量。
- [实际Word观察](word-observation.json)：最终8页，关闭不保存，前后哈希相同。现场图像已观察，未另存Word截图；下方页图来自实际LibreOffice，不冒充Word。

[原稿全部8页](previews/original-all-pages.png) · [最终全部8页](previews/final-all-pages.png) · [单节结果全部8页](previews/single-all-pages.png)。另有可读全页[前置i](previews/final-3.png)、[第二章连续3](previews/final-7.png)与[渲染回执](render-record.json)。联系表均为真实渲染页图缩排；封面无页码、i/ii、1–4及章节页脚由全页图和Word分别核对，不以XML缓存猜数字。

[三阶段智能结果](screenshots/complete-result.png) · [新上传的部分范围结果](screenshots/partial-scope-result.png) · [本地完整方案结果](screenshots/local-result.png)。后者存在题注关联待核对，数字组未处理，不包装为全部自动成功。

```bash
python scripts/reproduce_page_workflow.py --output /tmp/paperfit48-proof --browser-zip samples/phase48/result.zip
python scripts/verify_page_output.py samples/phase48/existing.docx samples/phase48/step1.docx samples/phase48/step2.docx samples/phase48/fixed.docx
```

输出目录须不存在。硬拒网络，无密钥、Word、渲染器及work/outputs依赖。智能/本地使用同一最终范围、规则和计划时同字节；独立脚本只用ZIP/XML及手写预期，不调用页码规划器自证。当前页码方案是产品选项，不宣称SCUT唯一要求；不刷新目录、REF/PAGEREF或SEQ，不保证其他真实论文相同页数。

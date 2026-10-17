# 第50阶段公开合成证据

智能：上传 → 选择明确完整方案 →（本任务补充正文从5开始）→ 开始 → 后台等待 → 下载。5个主要操作，无例外确认，无AI。普通只读检查仍不启动Word。

- [原稿](errors.docx)、[手写范围](roles.json)、[新上传实际接受范围](accepted-roles.json)、[最终规则](rules.json)。沿用第48阶段公开材料组合，不含真实论文。
- [实际浏览器下载](fixed.docx)、[更新前最终排版副本](before-update.docx)、[完整结果包](result.zip)、[真实阶段记录](audit.json)、[更新清单/稳定性记录](update.json)。更新前的DOCX是字段计算阶段前的真实父文件，不是原稿。
- [独立XML/ZIP复查](independent.json)：目录5/7、REF当前题注、PAGEREF7，其他XML反向掩码精确相同，其他部件字节相同；缺失、锁定及SEQ保持。
- [受控失败降级](failure-proof.json)：模拟Word失败时只发布此前合法副本，不登记字段半轮；不是实机权限失败。
- [手工目录原稿](manual.docx)、[真实Word创建结果](created.docx)、[创建/重复稳定证明](creation-proof.json)。仅转换确认的普通目录条目，未顺带更新未选择引用。
- [实际重排原稿](reflow.docx)、[重排后目录](reflow-fixed.docx)、[前后页码/实际Word证据](reflow-proof.json)：原R05/R06后小节从3到4，最终目录2/4；Word实际内部跳转到4。
- [Word实际观察](word-observation.json)、[原生跳转与引用](screenshots/word-jump-refs.png)、[目录与正文](screenshots/word-toc-body.png)、[重排后第4页](screenshots/word-reflow-page4.png)。均关闭不保存，哈希保持。
- [主样本8页真实LO渲染](previews/all-pages.jpg)、[渲染差异](render-record.json)；LO在保护REF显示和重排样本分页上与Word不同，不冒充Word。
- [开始后的真实阶段](screenshots/browser-processing.png)、[最终源码完成与下载](screenshots/browser-complete.png)、[验收摘要](validation.json)、[文件哈希索引](manifest.json)。网页截图不代替Word或排版引擎验收。

本机明确执行（需要macOS Word，只打开独立任务副本，0API）：

```sh
python scripts/reproduce_word_fields.py --output /tmp/paperfit50-demo --word
```

只读清单可不加`--word`；普通自动测试模拟适配器，硬拦截真实Word及付费HTTP。无需Word的独立文件核对：

```sh
python scripts/verify_word_fields.py samples/phase50/before-update.docx samples/phase50/fixed.docx
```

不支持的目录容器、筛选、自动编号标题及复杂/锁定/缺失目标继续保持。动态编号关联组没有因Word可用就放宽，数字同步0不是全部编号合格。完整边界与环境探测失败见[验收记录](../../docs/acceptance/phase50.md)。

# 第三十二阶段合成验收文件

全部为软件作者构造的公开合成内容，无真实课程论文、作者资料或API输入。`correct.docx`是**所选文字属性的独立正确对照**，故意保留MissingTarget结构故障、未选缩进及参考文献数量提示；不是整篇正确或真实页码对照。

| 文件 | 用途 |
| --- | --- |
| [errors.docx](errors.docx) / [correct.docx](correct.docx) | 原稿与作者独立制作的5处链接字号对照 |
| [protected.docx](protected.docx) | 重复书签名称、边界异常的只读保护文件，不作为合法Word展示样本 |
| [independent-plan.json](independent-plan.json) | 手写目标、故障位置、角色、注释范围、修正白名单及材料排除，非检查器输出 |
| [fixed.docx](fixed.docx) | 原引擎单轮预演后采用；与直接合法路径及正确对照逐字节相同 |
| [browser-round1.docx](browser-round1.docx) / [browser-final.docx](browser-final.docx) | 真实网页1项、再4项的两轮下载；最终与fixed.docx同字节 |
| [changes.md](changes.md) / [recheck.md](recheck.md) | 实际修改与落盘复查 |
| [independent-check.json](independent-check.json) / [browser-independent.json](browser-independent.json) | 独立ZIP/XML核对，不调用R44索引或引擎掩码 |
| [structure-report.json](structure-report.json) | 完整目标、边界、引用位置、域及分组证据；保存结果存在不证明缓存新鲜 |
| [fixed.types.json](fixed.types.json) | 确认范围及新哈希；不包含执行授权 |
| [internal-reference-supplement.json](internal-reference-supplement.json) | 可复用产品检查与安全内部文字支持开关，不含论文定位 |
| [report.html](report.html) / [report.md](report.md) / [report.json](report.json) | 离线可阅读、Markdown和JSON报告，默认省略论文原文 |
| [result.zip](result.zip) | 正式结果包：最终DOCX、真实报告、配置和范围，不含原稿/页图 |
| [project.zip](project.zip) / [draft-project.zip](draft-project.zip) | 单轮已确认项目与未确认草稿，用于恢复重新检查；包含合成论文 |
| [browser-project.zip](browser-project.zip) | 网页两轮项目，实际重启导入恢复验证；旧页图和预演授权不恢复 |
| [clean-reproduction.json](clean-reproduction.json) | 最终干净目录1192项、源码绑定与离线复现记录 |
| [efficiency.json](efficiency.json) / [measurements.json](measurements.json) | 原始计时、3次索引/重复查询测量；不是用户等待或提速百分比 |
| [browser-acceptance.json](browser-acceptance.json) / [visual-record.json](visual-record.json) | 真实浏览器及本轮Word/LibreOffice观察，分别报告 |
| [pages/errors-1.png](pages/errors-1.png) / [pages/correct-1.png](pages/correct-1.png) / [pages/final-1.png](pages/final-1.png) | 真实DOCX渲染的全部页面，非手绘或网页HTML表格 |
| [缺失目标](screenshots/missing-target.png) / [有效目标](screenshots/valid-target.png) / [单属性预演](screenshots/one-attribute-rehearsal.png) | 实际网页截图 |
| [恢复](screenshots/restored-current.png) / [失效](screenshots/config-invalidated.png) | 本轮重启恢复及配置变化 |
| [Word原显示](screenshots/word-before-jump.png) / [目标导航](screenshots/word-target-navigation.png) / [链接实际跳转](screenshots/word-link-jumped.png) | 本轮Word16.80实际查看；最后一图显示点击参考文献链接后选中目标标题 |

复现（新建输出目录，不能覆盖旧目录）：

```bash
python scripts/reproduce_internal_reference_demo.py --output /tmp/paperfit-phase32-new
python scripts/verify_internal_reference_output.py samples/phase32/errors.docx /tmp/paperfit-phase32-new/fixed.docx
python scripts/measure_internal_references.py --output /tmp/paperfit-phase32-measure.json
```

最终仍有3条规则问题、44条待复核，其中R44为**1个MissingTarget故障、3处受影响引用**；其余为未选缩进及参考文献条目数量。0外网跳转、0AI请求、0自动渲染。页图仅主动验收生成，预览/Word不会回写交付文件。

# 组合与区间引文合成交付

全部是软件演示，非真实论文。原稿和正确对照独立按作者字面区间制作；语法支持是产品范围，学校材料仅规定顺序、方括号和上标对应。

| 文件 | 用途 |
| --- | --- |
| [errors.docx](errors.docx)、[correct.docx](correct.docx) | 合成原稿、独立对照；复杂REF缓存始终保护 |
| [independent-errors.json](independent-errors.json)、[scope.json](scope.json) | 作者预先定义区间/编号及角色、代码保护 |
| [citation-v1.json](citation-v1.json)、[citation-v2.json](citation-v2.json) | 原单整数配置与显式组合/区间配置 |
| [step-1.docx](step-1.docx)、[step-2.docx](step-2.docx) | 普通格式及整组上标两步正式副本 |
| [第一步修改](step-1-changes.md)、[第二步修改](step-2-changes.md) | 各步真实事务记录 |
| [第一步复查](step-1-recheck.md)、[第二步复查](step-2-recheck.md) | 实际落盘读回 |
| [relations.json](relations.json)、[final.types.json](final.types.json) | 完整逐成员关系/首次位置证据与最终范围 |
| [独立核对](independent-check.json)、[下载独立重读](download-recheck.json)、[实际调用与计时](timings.json) | 手工两轮同字节及XML/ZIP白名单 |
| [阅读HTML](report.html)、[JSON](report.json)、[Markdown](report.md)、[成果包](result.zip) | 完整报告与各步摘要；中间DOCX另行下载 |
| [浏览器部分副本](browser-partial.docx)、[中间](browser-middle.docx)、[最终](browser-final.docx) | 浏览器先R33一组，再普通格式/其余R33的实际三轮；与主两轮路径不同 |
| [浏览器独立核对](browser-independent.json)、[范围](browser-final.types.json)、[浏览器成果包](browser-result.zip)、[操作记录](browser-acceptance.json) | 实际下载及恢复流程 |
| [性能原始测量](measurements.json)、[干净目录复现](clean-reproduction.json)、[视觉记录](visual-record.json) | 各类证据分别记录 |

截图：[确认语法与范围](screenshots/v2-confirmed-scope.png)、[逐成员表](screenshots/member-details.png)、[首次位置组](screenshots/first-position-groups.png)、[完整计划预演](screenshots/two-step-rehearsal.png)、[重启恢复](screenshots/restored-results.png)。

真实页图：[原稿1](previews/original-1.png)、[2](previews/original-2.png)；[对照1](previews/control-1.png)、[2](previews/control-2.png)；[中间1](previews/middle-1.png)、[2](previews/middle-2.png)；[最终1](previews/final-1.png)、[2](previews/final-2.png)；[浏览器最终1](previews/browser-final-1.png)、[2](previews/browser-final-2.png)。

```bash
python scripts/reproduce_citation_groups_demo.py --output /tmp/paperfit-groups-new
python scripts/verify_citation_groups_output.py samples/phase30/errors.docx /tmp/paperfit-groups-new/step-1.docx /tmp/paperfit-groups-new/step-2.docx
python scripts/measure_citation_groups.py --output /tmp/paperfit-groups-measure-new.json
```

不依赖本机历史work/outputs、Word、渲染器、密钥或学校PDF。原稿及前轮保留；只修字体/字号和所选组上标，不改编号。主最终仍有顺序风险、未选格式和复杂覆盖提示，不能称全文合格。

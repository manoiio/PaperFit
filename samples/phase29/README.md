# 普通超链接文字合成验收

全部为软件演示内容，无真实论文或个人信息。链接目标使用保留演示域名，检查器不访问链接。直接run编号保持；链接使用独立link/link_run定位。

- [原稿](errors.docx)、[独立对照](correct.docx)、[复杂保护文件](protected.docx)：后者只作保护测试，不作为合法Word输出展示。
- [独立错误与允许修改清单](independent-errors.json)、[独立范围](scope.json)：正文7/8/12；参考文献10/11；脚注1、尾注1/3；代码13人工排除。正文12及其引文不在16项演示修正内。
- [实际修正版](fixed.docx)、[修改记录](changes.md)、[读回复查](recheck.md)、[独立核对](independent-check.json)、[成果包](result.zip)。
- [离线报告](report.html)、[原始阅读报告](report.json)、[完整范围](fixed.types.json)、[覆盖与计时](coverage.json)、[重复计时](measurements.json)、[旧版本相同输入比较](baseline-coverage.json)。
- [浏览器两轮独立核对](download-recheck.json)、[实际浏览器记录](browser-acceptance.json)、[两轮合成项目](browser-project.zip)、[实际视觉记录](visual-record.json)。

输出16条明确修改：正文普通前后文字4条、链接内部12条，涉及正文、参考文献、脚注和尾注。对照由作者白名单直接制作，未调用检查器产生答案；实际输出来自原fix_document与预演采用。对照仅指这些选定属性正确，仍有8问题/30待复核，不宣称全文合格。

本阶段只支持已确认正文、参考文献条目、脚注/尾注中关系明确的http/https普通链接文字。内部anchor、复杂域/TOC、修订/嵌套SDT、表格和页眉页脚链接仍未覆盖。含链接段落的段落属性和R33继续保护，不改目标、字符样式、颜色或下划线。

```bash
python scripts/reproduce_hyperlink_demo.py --output /tmp/paperfit-phase29-new
python scripts/verify_hyperlink_output.py samples/phase29/errors.docx /tmp/paperfit-phase29-new/fixed.docx
python scripts/measure_hyperlinks.py --output /tmp/paperfit-phase29-timing-new.json
python -m unittest tests.test_hyperlink_text
```

复现不依赖work/outputs、Word、渲染器、学校PDF、真实论文或API。输出目录须不存在。详细证据见[阶段验收](../../docs/acceptance/phase29.md)。

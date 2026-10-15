# 已知依赖的两步计划合成案例

本目录仅含公开合成内容，无真实论文或个人信息。两个普通段落的中文字体和字号出错；同段及另一段有4条待上标引文，包含重复文字、run中间和跨run。普通格式与引文必须使用原来的两个独立事务。

- [错误原稿](errors.docx)、[独立范围与明确选择](scope.json)、[预先制定的注入清单](independent-errors.json)。段18为人工排除代码，数组[8]被排除，复杂REF保持只读；表格和图片用于保留验证。
- [第1步普通格式副本](step-1.docx)、[修改记录](step-1-changes.md)、[落盘复查](step-1-recheck.md)。仅2个中文字体与4个字号属性发生变化。
- [第2步最终副本](step-2.docx)、[修改记录](step-2-changes.md)、[落盘复查](step-2-recheck.md)、[重新绑定的范围](final.types.json)。仅所选4个准确字符区间变成上标。
- [计划、父子关系及各步影响](plan.json)、[独立逐字符/XML/ZIP核对](independent-check.json)、[实际下载文件独立检查](download-recheck.json)。手工合法两轮与计划的两份输出均逐字节相同。
- [离线HTML](report.html)、[JSON](report.json)、[Markdown](report.md)、[成果ZIP](result.zip)。ZIP只含最终DOCX；中间副本单独下载；ZIP中steps目录保留每步修改和复查。
- [单次原始计时](timings.json)、[三次匹配测量及中位数](measurements.json)、[独立视觉记录](visual-record.json)、[完整验收及页图](../../docs/acceptance/phase28.md)。

最终仍有9个问题、32个待复核（含覆盖提示）。只修改明确选择，不追求清零。第1步新出现28pt缩进不等效两字符的问题；第2步特殊上标保护使它转为待复核，不能算解决。跨run变化不能可靠对齐的4条原记录保留为无法对齐；每步实际选择读回证据另列。复杂REF在LibreOffice显示找不到引用来源，Word显示保存的[1]；两者都未保存回正式DOCX。

```bash
python scripts/reproduce_plan_demo.py --output /tmp/paperfit-plan-new
python scripts/verify_plan_output.py samples/phase28/errors.docx /tmp/paperfit-plan-new/step-1.docx /tmp/paperfit-plan-new/step-2.docx
python scripts/measure_plan.py --output /tmp/paperfit-plan-measure-new.json
```

输出目录或文件必须不存在。复现不需要work、outputs、学校PDF、Word、密钥或渲染器。渲染图片只是实际环境中的视觉证据，不代表所有Word/WPS分页一致。

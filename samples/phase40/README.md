# 第四十阶段文件索引

均为仓库软件合成内容，不包含真实论文或个人资料。默认快捷使用既有[错误样本](../errors.docx)；动态样本由[作者脚本](../../scripts/build_smart_dynamic_fixture.py)在阶段23合成文件上注入明确错误，不是Word/渲染器自动生成的证明。

| 文件 | 作用 |
| --- | --- |
| [smart-fixed.docx](smart-fixed.docx) / [smart-result.zip](smart-result.zip) | 真实浏览器普通智能修正下载，11项格式修正；与原合法路径同字节 |
| [dynamic-errors.docx](dynamic-errors.docx) / [dynamic-scope.json](dynamic-scope.json) | 两章、图表和跨run纯文本引用；作者范围用于离线独立参考，网页另经自动建议和明确确认 |
| [independent-errors.json](independent-errors.json) | 作者预期：两处题注数字、三处正文引用数字；非程序检查器输出复制 |
| [dynamic-fixed.docx](dynamic-fixed.docx) / [dynamic-result.zip](dynamic-result.zip) | 真实浏览器动态预演后明确采用，5处数字变化；1问题/11待复核保留 |
| [dynamic-record.json](dynamic-record.json) | 脱敏的修改、目标、章号依据、独立验证及前后实际检查；Word未执行 |
| [independent.json](independent.json) | 原合法格式路径及作者手写XML树核对、真实下载同字节、调用数与本地函数时间 |
| [evidence.json](evidence.json) | 最终本地测试、浏览器事实、源码与文件哈希、失败尝试边界 |

真实网页截图（不是DOCX页图）：

- [1280×720自动范围摘要](screens/automatic-summary-1280.png)：上传后无需再点分析，不会自动确认。
- [1440×900快捷结果下载](screens/smart-result-1440.png)：当前输入仍原稿。
- [1280×720动态预演待采用](screens/dynamic-preview-1280.png)：没有正式输出，清单和未更新页码提示保留。
- [1280×720动态采用结果](screens/dynamic-result-1280.png)：5处数字变化，剩余事项不清零。

运行：

```bash
python scripts/reproduce_smart_workflow.py --output /tmp/paperfit40-result
```

输出目录须不存在。无需历史work/outputs、密钥、Word、渲染器或网络。命令生成独立任务、普通和动态副本、修改/复查记录、ZIP及可恢复项目。项目保存正式历史，未采用动态预演和快捷授权不恢复。目录/REF/PAGEREF实际求值、Word分页、真实跳转与页图均未验收。

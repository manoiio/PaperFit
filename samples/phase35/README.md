# 第三十五阶段：表单与范围核对证据

复用阶段32的内部引用合成论文、项目范围及阶段25合法规则包，没有新建演示论文或展示材料。真实Chrome截图；本目录不含DOCX、项目包、日志、密钥或私人路径。

| 同窗口与状态 | 改版前 | 改版后 |
| --- | --- | --- |
| 规则入口，1280×720 | [前](screenshots/before-rules-1280.png) | [后](screenshots/after-rules-1280.png) |
| 规则入口，1440×900 | [前](screenshots/before-rules-1440.png) | [后](screenshots/after-rules-1440.png) |
| 正文字号字段，1280×720 | [前](screenshots/before-field-1280.png) | [后](screenshots/after-field-1280.png) |
| 正文字号字段，1440×900 | [前](screenshots/before-field-1440.png) | [后](screenshots/after-field-1440.png) |
| 未确认的段落分类，1280×720 | [前](screenshots/before-classification-1280.png) | [后](screenshots/after-classification-1280.png) |
| 未确认的段落分类，1440×900 | [前](screenshots/before-classification-1440.png) | [后](screenshots/after-classification-1440.png) |

前后为同一原稿、未应用的同一导入规则包和相同原分类；字段截图均滚动到编辑区。规则入口图为页面顶部。改版前由基线`1a552be`的独立本地源码副本运行，不依赖记忆或图片编辑；基线临时服务已停止。后续应用/分类改变的图为额外流程证据，不混作同状态对照。

- [间距草稿](screenshots/spacing-draft.png)：数值与行单位分开，未应用。
- [重启恢复的13磅草稿/当前12磅](screenshots/restored-draft-before-apply.png)：恢复不自动应用。
- [完整文本与批量分类后的筛选](screenshots/classification-batch-filtered.png)。
- [代码段保护](screenshots/protected-material.png)、[最终只读材料不入编辑行](screenshots/protected-editable-list.png)。
- [实际采用及剩余事项](screenshots/actual-result.png)：单项字号修正后仍24问题/51待复核，输入仍原稿。
- [独立文件、配置来源和范围核对](independent.json)、[完整证据索引及SHA-256](evidence.json)。

离线复现（输出目录须不存在）：

```bash
python scripts/reproduce_editing_workflow.py --output /tmp/paperfit35
```

复现器复用既有样本及原合法路径，三字段明确用户编辑，材料段12保持排除，仅改段3/链接1/内部片段2字号。可用`--browser-download`和`--browser-rules`独立比较实际网页下载；所有文字和ZIP部件核对不依赖新UI映射器。

不声明新Word/渲染结果：实际DOCX与同配置合法路径逐字节一致。完整记录见[验收](../../docs/acceptance/phase35.md)。移动端、旧特殊编辑器未全面重做；未保存控件缓冲仅本会话，项目保存已保存草稿。

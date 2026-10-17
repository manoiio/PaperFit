# 第三十八阶段：问题浏览与选择证据

复用现有合成样本，无新演示论文。截图来自实际Chrome/Streamlit操作；不是DOCX渲染或Word验收。前图是`50e9af1`，后图为本阶段实现，使用相同文件、规则和范围。

| 状态 | 修改前 | 修改后 |
| --- | --- | --- |
| 内置错误样本，无选择，1280×720 | [前](screens/before-basic-1280.png) | [后](screens/after-basic-1280.png) |
| 同状态，1440×900 | [前](screens/before-basic-1440.png) | [后](screens/after-basic-1440.png) |
| 同两项选择及完整清单，1440×900 | [前](screens/before-two-selected-1440.png) | [后](screens/after-selected-list-1440.png) |
| 400段长文第1页、段2 | [前](screens/before-long-page1-1440.png) | [后](screens/after-long-page1-1440.png) |
| 同长文第2页、段20混合状态 | [前](screens/before-long-page2-1440.png) | [后](screens/after-long-page2-1440.png) |

长文两图的浏览对象和范围一致；后图已明确选择段2字号，以便同时观察跨页保留计数。此差别明确列出，不当作完全相同选择状态的对照。另有[降序及390–400筛选](screens/after-long-filter-1440.png)、[R44只读目标问题](screens/after-readonly-1440.png)。完整验收见[阶段38](../../docs/acceptance/phase38.md)。

[独立核对](independent.json)：内置错误样本6段正文，明确选择`R05:paragraph=4:run=2`及`R03:paragraph=5:run=1`，真实预演、采用并下载，与原直接合法路径整份DOCX及18个成员一致；结果包的DOCX与单文件下载一致。[验收数据](evidence.json)记录测试、实际浏览器边界和源文件/截图哈希。

```bash
python scripts/prepare_problem_browser_fixture.py --output /tmp/paperfit38-long-draft.zip
python scripts/reproduce_reader_workflow.py --output /tmp/paperfit38-two \
  --keys R05:paragraph=4:run=2 R03:paragraph=5:run=1
# 与实际浏览器下载比较，可另加 --download /path/to/download.docx
```

输出路径须不存在。长文项目包只封装现有[400段DOCX](../../tests/fixtures/history/phase12/long-400.docx)及作者角色清单（390正文/10一级标题），范围保持未确认；实际网页仍须导入核对并明确确认检查。它不执行检查、修正、API或预览，不注入浏览器私有状态。下载DOCX及项目可用命令复现，历史work目录不是测试或阅读前提。

相同任务“查看段4字号、段5中文字体→分别加入→核对完整清单”：原路径7次主要点击（两次打开/选对象、两次选择修正、展开清单）；新路径5次（两次点对象、两次加入、打开清单）。默认检查项恰好就是这两项，两条路径均无需额外切属性；不人为增加旧路径点击。滚动、等待、移除再加入和后续采用不计入这项比较，不据此推算耗时或百分比。主要改善是对象、检查项及混合状态可见，清单可直接逐项移除。

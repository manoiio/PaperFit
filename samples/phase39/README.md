# 第三十九阶段证据索引

使用现有[阶段32合成论文](../phase32/errors.docx)、[阶段25规则包](../phase25/repaired-rule-bundle.json)，无新演示论文。前图为main `150f13e`，后图为本阶段真实Chrome/Streamlit；各自滚动到同一正文对象编辑区。

| 状态 | 截图 |
| --- | --- |
| 原单字段正文编辑，1440×900 | [修改前](screens/before-object-1440.png) |
| 原单字段正文编辑，1280×720 | [修改前](screens/before-object-1280.png) |
| 同对象集中呈现未改值，1440×900 | [修改后](screens/after-object-1440.png) |
| 正文三项尚未保存，1440×900 / 1280×720 | [大窗口](screens/three-unsaved-1440.png) · [小窗口](screens/three-unsaved-1280.png) |
| 三项已保存仍未应用（恢复后同草稿），1440×900 / 1280×720 | [大窗口](screens/three-saved-1440.png) · [小窗口](screens/three-saved-1280.png) |
| 本组失败及段前间距定位，1440×900 | [真实错误](screens/group-error-1440.png) |

前图原有已保存三项，只能逐字段查看；最终停在行距字段。后图未保存和已保存状态分别标明，不把不同保存状态伪称完全相同状态。截图证明网页交互，不是DOCX/Word渲染。字段单位、空值和反馈在原生组件内，不含装饰性假页面。

- [实际确认规则包](confirmed-rule-bundle.json)：正文楷体、13pt、2倍；其他字段及模块保留原包决策和来源，不带论文或定位。
- [独立文件/来源核对](independent.json)：实际下载与原逐字段路径整份及20成员同字节；原始ZIP/XML证明只有明确选择的链接run字号变化，所有未选内容保持。
- [完整验收、操作量及边界](../../docs/acceptance/phase39.md)。
- [测试、源码/截图哈希及浏览器数据](evidence.json)。
- [可移植原逐字段参考](../../scripts/reproduce_object_rules_workflow.py)，不调用新UI转换或协调器自证。实际DOCX/结果ZIP可由该命令和正常网页流程复现，不要求复制本机历史目录。

```bash
python scripts/reproduce_object_rules_workflow.py --output /tmp/paperfit39-reference
```

三值、所有模块及来源逐项对照；包装生成时间可以不同。对象保存3→1、字段切换2→0；不推算未经测量的整体提速。0新增AI/渲染；合法候选的浏览器补验使用阶段24已有公开模拟规范/响应，经原API准备项目再真实导入，明确为历史模拟，不是本轮实时API。

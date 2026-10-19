# 智能缺省与覆盖核对合成样本

`source.docx`独立编写，含错误/正确/带缩进的普通题注、三张普通表格、独立合成流程图片、受保护SEQ题注及正常显示却缺失目标的REF。`expected.json`为作者预先手写值，未调用AI。

新任务上传后点击“开始智能排版”；普通题注应居中，完整整理对安全内容表清理左右外侧边框，内部竖线保留。带首行缩进的题注仍须提示视觉偏移，不默认清除未授权属性。缺失REF目标只读报问题，不能补造书签。PAGE/目录无对象时不伪造已更新。

“仅整理文字格式”不处理边框等辅助；旧包/明确空字段不自动补写。此样本证明实际能力与保护，不代表所有论文合格。


`fixed.docx`为真实浏览器下载，`rules.json`为实际保存要求；`word.pdf`/`word-page.png`为Word导出及页图。`independent.json`记载原合法逐步路径的同字节核对；`validation.json`区分浏览器、实机Word和自动测试。样本仍有缺失目标等只读问题，未包装成全文通过。

复查：`.venv/bin/python scripts/verify_smart_defaults.py samples/phase56/source.docx samples/phase56/fixed.docx`。完整逐轮复现需要先在网页保存本样本项目，再调用`scripts/reproduce_smart_defaults.py`；不提交含本机路径的任务项目包。

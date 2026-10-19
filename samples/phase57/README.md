# 公开合成目录样本

独立编写，无真实论文衍生内容。source.docx含中文摘要、Abstract、目录、1–3级标题、一个长标题和参考文献；原目录只要求1–2级且缓存过时，几何故意错误。roles.json与expected.json为作者独立预标注。

fixed.docx是原受限回填链路调用本机Word后的实际输出，7条目录含“目录 iii”；正文从5开始，三级长标题分三行，页码右对齐。word-toc.png为实际Word窗口，independent.json为不调用新模块的ZIP/XML核对，word-verification.json记录有界稳定性。

复查：`.venv/bin/python scripts/verify_toc_policy.py samples/phase57/source.docx samples/phase57/fixed.docx`。生成原稿：`.venv/bin/python scripts/build_toc_policy_fixture.py /新的公开输出目录`。Word集成不在普通自动测试内执行；无API。

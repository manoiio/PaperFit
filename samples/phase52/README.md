# 第52阶段公开证据

所有输入为公开合成，0AI，无私人论文。Word字段计算与自动测试分开。

- [原稿](source.docx)、[Word实际创作保存的母本](word-authored.docx)、[独立作者角色](roles.json)、[手写编号期望与母本操作](expected.json)。原稿在母本基础上故意缓存99，加入明确封面标记和安全分节空段。
- [实际浏览器下载](fixed.docx)、[最终Word计算前父副本](before-update.docx)、[实际下载结果包](result.zip)；ZIP含4阶段记录及最终报告，当前输入不自动切换。
- [原生字段稳定性与编号回执](field-proof.json)、[独立ZIP/XML](independent.json)、[本地原合法路径同字节](local-legal.json)、[原始智能路径事实](local-proof.json)。本地原合法路径全部HTTP硬拦截，Word实机重算；没有用同一新解析器自证。
- [手工/自动混合输入](mixed-source.docx)、[实机输出](mixed-fixed.docx)、[变体记录](mixed-proof.json)，该变体没有冒称浏览器路径。
- [原稿真实Word页序](source-pages.json)、[最终Word观察](word-observation.json)、[渲染差异](render-record.json)、[真实浏览器处理记录](browser-audit.json)、[浏览器及测试](validation.json)。
- [真实完成页](screenshots/browser-complete.png)、[Word目录](screenshots/word-toc.png)、[同名后章实际跳转](screenshots/word-target.png)、[全部LO页图](previews/all-pages.jpg)。Word10页，LO8页，后者部分标题叠印，不能当作Word验收。

运行：`python scripts/reproduce_container_toc.py --output /tmp/paperfit52 --word`。此命令明确打开本机Word独立副本，不请求网络；不加`--word`为只读清单。独立核对：`python scripts/verify_container_toc.py samples/phase52`。

[支持矩阵与限制](../../docs/acceptance/phase52.md)。编号连续性未检查，不修改numbering.xml，不把自动符号写进run；复杂/未知情况保持。旧常规方案不启动Word，恢复不恢复授权。

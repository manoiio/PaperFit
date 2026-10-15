# 修正预演合成案例

输入沿用[综合合成论文](../phase26/composite.docx)及[独立人工范围](../phase26/scope.json)，没有复制真实论文或作者资料。通过全部七区域原校验；所有完整范围声明仍为false，代码段13保持保护。

只选择 `R05:paragraph=8:run=1`：13pt→12pt。原24pt缩进保持不变，现在重新等效2字符。因此修改1条记录、1个XML属性，所选R05及未选R07两条问题符合；其余49问题、28待复核保留。不是全文合格。

- [实际副本](fixed.docx)、[修改记录](changes.md)、[落盘复查](recheck.md)。
- [预演完整影响](impact.json)、[独立核对](independent-check.json)、[阅读HTML](report.html)、[对应JSON](report.json)、[阅读Markdown](report.md)、[成果ZIP](result.zip)。
- [三次本地测量](local-timings.json)和[本次复现计时](timings.json)；前者才是同样完整轮次操作的比较，不能将纯引擎耗时与包含归档的采用耗时直接换算成提速。

```bash
python scripts/reproduce_rehearsal_demo.py --output /tmp/paperfit-rehearsal-new
python scripts/measure_rehearsal.py --output /tmp/paperfit-rehearsal-times-new.json
python -m unittest tests.test_rehearsal
```

输出目录/文件须不存在。无需work/outputs、密钥、API、学校PDF、Word或渲染器。

独立XML/ZIP证明：主文档只改目标w:sz的26→24半磅值；去除此唯一允许值后全树规范化XML一致，其他部件逐字节一致，原稿哈希不变。正式采用与直接合法路径及第二十六阶段已实际渲染/Word查看文件逐字节相同，SHA256为 `c51c4a8d88165279242f050425ae4ddd3b2577c6affb6f789bdd3a4352257d10`。本阶段准确复用该文件的既有视觉证据，没有宣称再次打开Word。

复现输出另含本机项目包和会话目录，仅用于恢复实验，不提交。项目保存选择草稿，不包含可执行预演授权；恢复必须重新检查与预演。预演JSON含当前明确范围和公开规范依据，不包含整篇论文或本机路径。

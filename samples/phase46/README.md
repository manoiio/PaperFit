# 第46阶段文件索引

使用第44/45阶段同一公开合成要求与论文，独立预期继续使用[手写16字段清单](../phase44/expected-overrides.json)，不是AI生成答案。

- 原要求载体：[TXT](requirements.txt)、[DOCX](requirements.docx)。内容相同，文件哈希及物理位置不同；不要求逐段勾选或粘到2000字符输入框。
- [实网回执](api-records.json)：2次，自动重试0，计费未知。真实响应、离线重放、模拟分别记录。
- TXT：[请求快照](txt-request.json)、[原始响应封装](txt-response.json)、[实际浏览器下载](txt.docx)、[结果包](txt-result.zip)。
- DOCX：[请求快照](docx-request.json)、[原始响应封装](docx-response.json)、[实际浏览器下载](docx.docx)、[结果包](docx-result.zip)。
- [用户实际保存的排版要求](rules.json)、[新会话复用下载](reuse.docx)。原完整规则包格式，不含论文、定位、选择、修改授权或密钥。
- [独立核对](independent.json)：16字段、物理位置、文件哈希、未触及值/来源/其他模块、原合法路径逐字节对照和独立XML/ZIP。
- 网页：[TXT已提取](screenshots/txt-ready.png)、[TXT完成](screenshots/txt-success.png)、[复用完成](screenshots/final-reuse.png)。是真实网页操作，不是Word/分页验收。

```bash
python scripts/reproduce_requirement_files.py --output /tmp/paperfit46-result
```

复现不读密钥，硬拦截网络。使用已收响应重新验证，不冒充实时API。源码测试用`python scripts/run_offline_tests.py`。完整说明见[阶段验收](../../docs/acceptance/phase46.md)。项目恢复包、调试目录和原始敏感请求不提交。

[最终8501服务复用页面](screenshots/final-reuse.png)：服务已清除调试捕获环境并加载最终代码，使用已保存要求再次实际下载，同字节、0规范解析。原生项目恢复包仅用于本机验证，不在本目录。

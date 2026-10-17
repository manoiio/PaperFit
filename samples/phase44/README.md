# 第44阶段文件索引

**实网2次均被校验拒绝，未证明AI实际识别或补充执行增益。**受控浏览器成功与实网失败分开。

- [errors.docx](errors.docx)、[独立可见信息标签](labels.json)：复用第43阶段注释/图/复杂表格，补充正常实验数据表、真正用途不明小表、代码保护及短标题。标签在请求前编写，不用作者意图逼模型选确定角色。
- [supplement.docx](supplement.docx)、[公开补充文字](requirements.txt)、[人工字段预期](expected-overrides.json)：明确正文和三级标题，共16个已有字段；预期不由AI生成。字体/字号等错误，段距显式0，便于核对真实写回。
- [API尝试及回执](api-records.json)：发送前哈希/时间/模型，发出/收到/校验/usage分开；共2POST、2响应、0采用，计费未知。没有原始敏感摘录或密钥。受控测试旧日志标签另作说明，不当作额外实网。
- [structure-fallback.docx](structure-fallback.docx)、[结果包](structure-fallback.zip)、[处理记录](structure-audit.json)、[独立核对](structure-independent.json)：实网结构拒绝后，用户同页确认内容表及暂不处理小表，再通过原本地引擎生成；不是AI正确识别证据。44项修改，仍3问题/16待复核。
- [template-fallback.docx](template-fallback.docx)、[处理记录](template-fallback-audit.json)：实网补充原句校验失败后，用户明确沿用原模板。**未执行补充要求**，不包装成成功输出。
- [controlled-fixed.docx](controlled-fixed.docx)、[结果包](controlled-result.zip)、[处理记录](controlled-audit.json)、[独立核对](controlled-independent.json)：原生浏览器+明确模拟HTTP响应；16字段实际应用、42项修改，与同规则/范围/选择的原合法路径同字节。1个参考文献数量提示、8个前后置范围待复核仍保留。
- [浏览器状态口径](browser-summary.json)、[默认SCUT零API记录](default-audit.json)：新会话3步、恢复重查、双会话和修改补充后的失效；不等于真实网络/Word兼容验收。
- [实网拒绝1440](screens/real-rejected-1440.png)、[受控实际下载1280](screens/controlled-result-1280.png)：真实网页截图，第二张的AI响应为模拟，不是实网成功或DOCX页图。

```bash
python scripts/run_offline_tests.py
# 可选：明确的模拟响应浏览器服务，非生产/非实网
python scripts/run_context_browser_acceptance.py --port 18544
python scripts/reproduce_context_workflow.py --output /tmp/paperfit44-result --browser-zip samples/phase44/controlled-result.zip
python scripts/verify_context_structure.py samples/phase44/structure-fallback.zip --output /tmp/paperfit44-structure.json
```

输出目录须不存在。复现本阶段使用手写预期和模拟响应，0实网，原合法路径及原始XML/ZIP独立核对；不依赖历史work/outputs、学校PDF、Word、渲染器或密钥。[验收及实际限制](../../docs/acceptance/phase44.md)。

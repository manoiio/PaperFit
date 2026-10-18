# 第53阶段公开证据

全部为合成内容，不包含真实论文或密钥。正例沿用第52阶段实际Word创建的SDT目录/自动编号结构，加入分段合法字符效果、上标引文及长文分页。独立预期在expected.json中，不由API生成。

- `source.docx`、`roles.json`、`expected.json`：合法正例及手写期望。
- `requirements.txt`：唯一一次真实请求的13字段规范；`rules.json`是真实解析后保存的完整要求。
- `real-api-request.json`、`real-api-response.json`、`real-api-adapted.json`、`real-api-outcome.json`：仅公开规范，已检查无密钥/请求头/思考链。真实API1次，结构请求0次。
- `public-response.json`：**模拟协议夹具**，不冒充真实响应。
- `conflicting-effects.docx`、`browser-audit-initial.json`：早期互斥效果反例与首轮历史API处理记录；其论文哈希不是最终正例。
- `format.docx`、`pages.docx`、`before-update.docx`、`fixed.docx`：实际浏览器项目中的4个正式父子副本。`stage-1..4-changes.json`、`history-summary.json`保留每步实际修改。
- `fixed.pdf`：实际浏览器下载的Word PDF，12页；`word-export.json`绑定最终DOCX/PDF；`result.zip`为实际下载，含相同DOCX/PDF及原完整报告，不含全部页图。
- `independent.json`：独立原始ZIP/XML核对；`local-equivalence.json`：本地合法路径0API、4轮、同字节证明；`final-word-measurement.json`：最终文件只读Word分页/编号实测，不是窗口人工观察。
- `source-word.pdf`、`source-word-all-pages.png`、`fixed-all-pages.png`：Word原稿10页、最终12页，全部页图总览。
- `result-1280.png`、`result-1440.png`、`word-page11-browser.png`、`word-compare.png`、`word-different-pages.png`、`local-effects.png`：真实浏览器截图，不是Word排版验收。
- `ghost-font.docx/pdf`、`ghost-bold.docx/pdf`、`ghost-record.json`、`ghost-controls.png`：第52阶段仅换字体/仅关加粗的独立控制，不是正式成果。原对照为第52阶段fixed.docx，未发现阴影类声明；根因限于阶段记录中的证据。
- `protected-fields.pdf`、`protected-field-export.json`：第50阶段fixed.docx的缺失/锁定域等输出，8个非PAGE域冻结，不刷新SEQ或缺失目标。
- `ghost-diagnosis.json`、`theme-coverage-regression.json`：重影的原始声明/字体/PDF证据，以及相同旧综合样本的新增字体可判定范围；`browser-batch-check.json`核对页11及明确复用均不重复导出。
- `manifest.json`：完整文件哈希索引；`validation.json`：最终本地验收结果。

```sh
python scripts/verify_visual_output.py samples/phase53
python scripts/reproduce_visual_output.py --output /tmp/paperfit53 --word --rules samples/phase53/rules.json
```

复现默认阻止网络。显式--word才使用本机Word；自动测试全部模拟且硬拦截Word/付费HTTP。最终结果保留8问题、91待留意，不是全文合格。本轮Word窗口观察因锁屏按用户要求延期，不能把PDF页图当作新增窗口人工验收。详情见[阶段记录](../../docs/acceptance/phase53.md)。

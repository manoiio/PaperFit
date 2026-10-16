# 第三十一阶段可移植交付

全部为软件演示合成内容，无真实论文、身份信息或API请求。沿用原规则编号；只扩大精确确认引文上标正文的R06/R07/R13判定，不改引文行内格式。

## 复现与独立核对

```bash
python scripts/check_repository.py
python -m unittest discover -s tests
python scripts/reproduce_citation_paragraph_demo.py --output /tmp/paperfit-phase31-new
python scripts/verify_citation_paragraph_output.py samples/phase31/errors.docx /tmp/paperfit-phase31-new/fixed.docx
python scripts/verify_citation_paragraph_output.py samples/phase31/errors.docx /tmp/paperfit-phase31-new/step-1.docx --only-line
python scripts/measure_citation_paragraphs.py --output /tmp/paperfit-phase31-measure-new.json
```

输出目录必须尚不存在；使用requirements.txt环境即可，不依赖历史work/outputs、学校PDF、密钥、Office或渲染器。原稿和独立对照可用`python scripts/build_citation_paragraph_sample.py`重新制作（仅覆盖本目录两份合成样本及作者清单）。

## 文件索引

| 文件 | 用途 |
|---|---|
| [errors.docx](errors.docx)、[correct.docx](correct.docx) | 合成错误原稿、独立作者正确对照；各2页 |
| [independent-errors.json](independent-errors.json) | 人工定义角色、准确引文字符范围、代码排除、错误及保护预期 |
| [template.json](template.json) | 现有v4自定义配置：R13正文段前6pt、段后0.5行、两端对齐；没有新增模板字段 |
| [step-1.docx](step-1.docx)、[fixed.docx](fixed.docx) | 仅修段3行距；第二轮修其余13条安全段落属性，原稿和前轮保留 |
| [changes.md](changes.md)、[recheck.md](recheck.md) | 最后一轮实际修改和落盘复查；第一轮及两轮关系见报告/ZIP |
| [before.json](before.json)、[evidence.json](evidence.json) | 实际初始检查、最终精确范围与属性证据 |
| [fixed.types.json](fixed.types.json) | 输出哈希绑定的真实分类/用途/代码排除；完整声明仍false |
| [report.html](report.html)、[report.json](report.json)、[report.md](report.md) | 同一真实结果投影；HTML离线、转义、默认脱敏 |
| [result.zip](result.zip) | 最终副本、修改、复查、规则、范围及预演影响；不含原稿/页图 |
| [independent-check.json](independent-check.json)、[browser-independent.json](browser-independent.json) | 独立全XML白名单、所有run子树与未选ZIP成员；真实浏览器下载与主复现同字节 |
| [baseline-comparison.json](baseline-comparison.json) | d08d16b与新引擎对同一文件、规则、范围的14条逐项变化 |
| [comparison-rules.json](comparison-rules.json)、[comparison-types.json](comparison-types.json) | 上述比较实际使用的同一规则与确认范围 |
| [plan-independent.json](plan-independent.json) | 浏览器普通格式→R33合法两步下载独立核对，与阶段28已验收文件同字节 |
| [measurements.json](measurements.json)、[timings.json](timings.json) | 3次本地成本原始数据、预演/采用调用次数 |
| [browser-acceptance.json](browser-acceptance.json) | 实际浏览器多轮、重启恢复、范围失效及双会话记录 |
| [visual-record.json](visual-record.json) | 原稿、对照、最终全部六页及Word两页的独立观察 |
| [clean-reproduction.json](clean-reproduction.json) | 无历史/密钥/渲染配置的干净目录验收 |

页图：[原稿1](pages/original-1.png)、[原稿2](pages/original-2.png)、[对照1](pages/control-1.png)、[对照2](pages/control-2.png)、[最终1](pages/final-1.png)、[最终2](pages/final-2.png)。最终与独立对照页图哈希一致；DOCX并非因此声称同字节。

截图：[精确证据](screenshots/paragraph-evidence.png)、[仅一项预演](screenshots/line-rehearsal.png)、[两步预演](screenshots/plan-preview.png)、[R33后段落证据](screenshots/plan-final-evidence.png)、[重启恢复](screenshots/restored-evidence.png)、[范围修改失效](screenshots/range-invalidated.png)、[未确认上标继续保护](screenshots/unconfirmed-protected.png)、[Word第一页](screenshots/word-page-1.png)、[Word第二页](screenshots/word-page-2.png)。

最终0格式问题、37待复核（19条规则记录+18条覆盖提示），是所选配置/范围内结果，不能称全文合格。段5未确认上标、段6区间外上标、段7无正文依据的点值缩进仍保护；引文行内字体字号均保持。

# 目录外观与默认智能整理验收

公开小样本由scripts/build_toc_appearance_fixture.py独立编写，与本地演示论文无内容关系。

- source.docx：三级标题、长标题和故意过期的目录。
- expected.json：手写预期与计量口径。
- fixed.docx：真实浏览器默认完整整理下载，原稿保留；仍有3问题/9待复核。
- word.pdf：该最终DOCX本机Word导出，4页；不是LibreOffice输出。
- independent.json：原始ZIP/XML独立核对。
- legal-path.json、local-equality.json：公开复现及本地同方案同字节对照。
- format-only-proof.json：仅格式路径与原fix_document逐字节一致。
- creation-proof.json、narrow-width-proof.json：真实Word普通目录转换及7200twips正文宽度核对。
- refresh-proof.json：真实Word再次刷新、保留外观，文件同字节。
- before/after-home、before-options、after-upload、format-only、result等PNG：实际网页，1280×720及1440×900。
- word-toc.png、word-jump.png：真实Word窗口目录与内部跳转。

运行（输出目录须不存在，--word明确操作本机Word隔离副本；不调用API）：

```sh
.venv/bin/python scripts/reproduce_toc_appearance.py --output work/目录外观复现 --word
.venv/bin/python scripts/verify_toc_appearance.py work/phase55/parent.docx samples/phase55/fixed.docx
```

第二条需要本地验收留存的父副本；全新克隆可使用第一条，它会生成自己的父子文件并调用独立核对。自动回归不启动Word：

```sh
.venv/bin/python scripts/run_offline_tests.py --pattern test_toc_appearance.py
```

目录默认缩进与点线为产品外观，不冒充学校规定。只处理可靠安全目录；原始报告保留剩余事项。本地指定脱敏演示输入及其衍生文件不在本目录或Git中。

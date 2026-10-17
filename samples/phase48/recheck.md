# 论文有格检查报告

规则：用户确认的组合演示要求（正文及标题题注）（段落及摘要关键词参考文献） vrule-bundle-1+template-demo-6.0.0+extended-demo-1.0.0+sections-demo-1.0
规则配置SHA256：b563cf9d638d4aabd08c8c9b379648544361516948e800177586411ce7225c8c
统一规则包结构版本：1；摘录哈希：e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
四模块配置：{"main": {"configured": true, "version": 6, "sha256": "abd3bc58799d7a9abb961acbdd7f5a99cf2748dea6103c6c59e114dd9f3dd008"}, "front": {"configured": false, "version": null, "sha256": null}, "toc": {"configured": false, "version": null, "sha256": null}, "notes": {"configured": false, "version": null, "sha256": null}}
明确不检查字段：[]；配置不确认对象，参与范围以本轮coverage为准。
模板结构版本：6；兼容转换：null
输入：fixed.docx
SHA256：8b8ecf63c59a30a92041c7633044cc65c9071e941dbeb3a6bfc2c3f87567c2fb

启用规则 26 条；实际适用 13 条；问题 1 个；待复核 27 个（规则记录 24，覆盖提示 3）。
结论：已覆盖检查发现问题。仅针对已覆盖范围，不表示全文合格。

格式属性结果不包含实际分页和所有可见排版验收；页面预览及Word查看需另行人工复核。

## 覆盖范围

{"body_paragraphs": [6, 8, 10, 12], "total_top_level_paragraphs": 12, "unconfirmed_paragraphs": [], "ordinary_runs_checked": 4, "special_runs_skipped": 0, "section_count": 4, "excluded": "其他/待确认段落、表格内格式、页眉页脚、脚注/文本框；特殊结构继续保护。不检查题注位置、编号及全文合格。", "paragraph_types": {"1": "other", "2": "other", "3": "abstract_cn_title", "4": "other", "5": "heading1", "6": "body", "7": "figure_caption", "8": "body", "9": "heading1", "10": "body", "11": "figure_caption", "12": "body"}, "classification_confirmation": "一站式开始命令授权（可安全识别对象，非旧勾选）：3dbdfb6fa82a49e7aaf438cc07fc2437:6fdd0f79f6695f11faaa15d970741222dd530724dc71a44cf9756858a105a4d2", "confirmed_typed_paragraphs": [3, 5, 6, 7, 8, 9, 10, 11, 12], "disabled_academic_properties": {"body": ["before", "after", "alignment", "bold"], "heading1": ["bold"], "heading2": ["bold"], "heading3": ["bold"], "figure_caption": ["before", "after", "alignment", "bold"], "table_caption": ["before", "after", "alignment", "bold"], "abstract_cn_title": ["font_western", "first_line_indent", "bold"], "abstract_cn_body": ["font_western", "before", "after", "alignment", "bold"], "abstract_en_title": ["font_cn", "first_line_indent", "bold"], "abstract_en_body": ["font_cn", "first_line_indent", "before", "after", "bold"], "keywords_cn": ["before", "after", "line_spacing", "first_line_indent", "label_font_western", "label_bold", "content_font_western", "content_bold"], "keywords_en": ["before", "after", "line_spacing", "first_line_indent", "label_font_cn", "content_font_cn", "content_bold"], "reference_title": ["font_western", "first_line_indent", "bold"], "reference_item": ["font_western", "first_line_indent", "before", "after", "alignment", "bold"], "appendix_title": ["font_western", "before", "after", "first_line_indent", "bold"], "appendix_text": ["font_western", "alignment", "line_spacing", "before", "after", "first_line_indent", "bold"], "ack_title": ["font_cn", "font_western", "font_size", "alignment", "line_spacing", "before", "after", "first_line_indent", "bold"], "ack_text": ["font_cn", "font_western", "font_size", "alignment", "line_spacing", "before", "after", "first_line_indent", "bold"]}, "academic_unchecked_requirements": ["外文参考文献2篇以上及主要文献身份、指导教师例外未自动判断（学校PDF物理页16）；需人工核对。", "中英文摘要/关键词的语义一致性、关键词层次及著录真实性未检查；不生成或改写内容。"], "academic_property_scope": "本清单列已启用的通用/章节属性（含确认附录致谢时R38–R41）；正文/标题/题注原R01–R12要求仍按其规则独立执行。", "backmatter_limits": ["附录和致谢按需存在，没有时不判缺项。", "附录普通文字须明确确认适用文献正文解释；代码、数据、运行输出、图表及其他材料不能整章套用。", "致谢范例物理页38仅显示标题与省略号，未提供可可靠执行的字体字号行距要求；致谢默认属性均未启用。", "内容、代码正确性、致谢是否适当、目录实际页码及所有排版行为未验证。"], "material_exclusions": {}, "backmatter_confirmed_objects": [], "explicitly_not_checked_fields": []}

## 逐项检查

| 规则 | 位置 | 实际值 | 要求值 | 状态 | 可修正 | 依据 |
| --- | --- | --- | --- | --- | --- | --- |
| R01 | {"section": 1} | {"w_mm": 210.009, "h_mm": 297.004} | {"width_mm": 210, "height_mm": 297} | 符合 | 否 | 用户确认的演示模板：纸张=A4 portrait：用户选择沿用默认值（默认PDF物理页20：编排并打印在标准A4纸上） |
| R02 | {"section": 1} | {"top_mm": 24.994, "bottom_mm": 24.994, "left_mm": 24.994, "right_mm": 24.994} | {"top_mm": 25, "bottom_mm": 25, "left_mm": 25, "right_mm": 25} | 符合 | 否 | 用户确认的演示模板：上边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm）；下边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm）；左边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm）；右边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm） |
| R01 | {"section": 2} | {"w_mm": 210.009, "h_mm": 297.004} | {"width_mm": 210, "height_mm": 297} | 符合 | 否 | 用户确认的演示模板：纸张=A4 portrait：用户选择沿用默认值（默认PDF物理页20：编排并打印在标准A4纸上） |
| R02 | {"section": 2} | {"top_mm": 24.994, "bottom_mm": 24.994, "left_mm": 24.994, "right_mm": 24.994} | {"top_mm": 25, "bottom_mm": 25, "left_mm": 25, "right_mm": 25} | 符合 | 否 | 用户确认的演示模板：上边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm）；下边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm）；左边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm）；右边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm） |
| R01 | {"section": 3} | {"w_mm": 210.009, "h_mm": 297.004} | {"width_mm": 210, "height_mm": 297} | 符合 | 否 | 用户确认的演示模板：纸张=A4 portrait：用户选择沿用默认值（默认PDF物理页20：编排并打印在标准A4纸上） |
| R02 | {"section": 3} | {"top_mm": 24.994, "bottom_mm": 24.994, "left_mm": 24.994, "right_mm": 24.994} | {"top_mm": 25, "bottom_mm": 25, "left_mm": 25, "right_mm": 25} | 符合 | 否 | 用户确认的演示模板：上边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm）；下边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm）；左边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm）；右边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm） |
| R01 | {"section": 4} | {"w_mm": 210.009, "h_mm": 297.004} | {"width_mm": 210, "height_mm": 297} | 符合 | 否 | 用户确认的演示模板：纸张=A4 portrait：用户选择沿用默认值（默认PDF物理页20：编排并打印在标准A4纸上） |
| R02 | {"section": 4} | {"top_mm": 24.994, "bottom_mm": 24.994, "left_mm": 24.994, "right_mm": 24.994} | {"top_mm": 25, "bottom_mm": 25, "left_mm": 25, "right_mm": 25} | 符合 | 否 | 用户确认的演示模板：上边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm）；下边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm）；左边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm）；右边距=25：用户选择沿用默认值（默认PDF物理页20：所有页面的上下左右页面边距为25mm） |
| R03 | {"paragraph": 6, "run": 1} | {"eastAsia": {"unresolved": "主题语言 ja-JP 未纳入当前唯一映射范围", "slot": "eastAsia"}} | "宋体" | 待复核：eastAsia：主题语言 ja-JP 未纳入当前唯一映射范围 | 否 | 用户确认的演示模板：正文中文字体=宋体：用户选择沿用默认值（默认PDF物理页18：正文：小四号，宋体，1.5倍行距） |
| R04 | {"paragraph": 6, "run": 1} | {"ascii": {"unresolved": "主题枚举与字体槽位不对应，需人工确认", "slot": "ascii"}} | "Times New Roman" | 待复核：ascii：主题枚举与字体槽位不对应，需人工确认 | 否 | 用户确认的演示模板：正文西文字体=Times New Roman：用户选择沿用默认值（默认PDF物理页18：英文单词：字号、行距与正文相同，字体为Times New Roman） |
| R05 | {"paragraph": 6, "run": 1} | {"pt": 12.0} | 12 | 符合 | 否 | 用户确认的演示模板：正文普通文字字号=12：用户选择沿用默认值（默认PDF物理页18：正文：小四号） |
| R06 | {"paragraph": 6} | 1.5倍 | 1.5 | 符合 | 否 | 用户确认的演示模板：正文倍数行距=1.5：用户选择沿用默认值（默认PDF物理页18：正文：小四号，宋体，1.5倍行距） |
| R07 | {"paragraph": 6} | {"first_line_chars": 2.0, "first_line_pt": 0.0, "hanging": null, "hanging_chars": null, "uniform_size_pt": 12.0} | 2 | 符合 | 否 | 用户确认的演示模板：正文首行缩进=2：用户选择沿用默认值（默认PDF物理页18：段首行缩进2个汉字） |
| R03 | {"paragraph": 8, "run": 1} | {"eastAsia": {"unresolved": "主题语言 ja-JP 未纳入当前唯一映射范围", "slot": "eastAsia"}} | "宋体" | 待复核：eastAsia：主题语言 ja-JP 未纳入当前唯一映射范围 | 否 | 用户确认的演示模板：正文中文字体=宋体：用户选择沿用默认值（默认PDF物理页18：正文：小四号，宋体，1.5倍行距） |
| R04 | {"paragraph": 8, "run": 1} | null | "Times New Roman" | 不适用：无该类字符 | 否 | 用户确认的演示模板：正文西文字体=Times New Roman：用户选择沿用默认值（默认PDF物理页18：英文单词：字号、行距与正文相同，字体为Times New Roman） |
| R05 | {"paragraph": 8, "run": 1} | {"pt": 12.0} | 12 | 符合 | 否 | 用户确认的演示模板：正文普通文字字号=12：用户选择沿用默认值（默认PDF物理页18：正文：小四号） |
| R06 | {"paragraph": 8} | 1.5倍 | 1.5 | 符合 | 否 | 用户确认的演示模板：正文倍数行距=1.5：用户选择沿用默认值（默认PDF物理页18：正文：小四号，宋体，1.5倍行距） |
| R07 | {"paragraph": 8} | {"first_line_chars": 2.0, "first_line_pt": 0.0, "hanging": null, "hanging_chars": null, "uniform_size_pt": 12.0} | 2 | 符合 | 否 | 用户确认的演示模板：正文首行缩进=2：用户选择沿用默认值（默认PDF物理页18：段首行缩进2个汉字） |
| R03 | {"paragraph": 10, "run": 1} | {"eastAsia": {"unresolved": "主题语言 ja-JP 未纳入当前唯一映射范围", "slot": "eastAsia"}} | "宋体" | 待复核：eastAsia：主题语言 ja-JP 未纳入当前唯一映射范围 | 否 | 用户确认的演示模板：正文中文字体=宋体：用户选择沿用默认值（默认PDF物理页18：正文：小四号，宋体，1.5倍行距） |
| R04 | {"paragraph": 10, "run": 1} | {"ascii": {"unresolved": "主题枚举与字体槽位不对应，需人工确认", "slot": "ascii"}} | "Times New Roman" | 待复核：ascii：主题枚举与字体槽位不对应，需人工确认 | 否 | 用户确认的演示模板：正文西文字体=Times New Roman：用户选择沿用默认值（默认PDF物理页18：英文单词：字号、行距与正文相同，字体为Times New Roman） |
| R05 | {"paragraph": 10, "run": 1} | {"pt": 12.0} | 12 | 符合 | 否 | 用户确认的演示模板：正文普通文字字号=12：用户选择沿用默认值（默认PDF物理页18：正文：小四号） |
| R06 | {"paragraph": 10} | 1.5倍 | 1.5 | 符合 | 否 | 用户确认的演示模板：正文倍数行距=1.5：用户选择沿用默认值（默认PDF物理页18：正文：小四号，宋体，1.5倍行距） |
| R07 | {"paragraph": 10} | {"first_line_chars": 2.0, "first_line_pt": 0.0, "hanging": null, "hanging_chars": null, "uniform_size_pt": 12.0} | 2 | 符合 | 否 | 用户确认的演示模板：正文首行缩进=2：用户选择沿用默认值（默认PDF物理页18：段首行缩进2个汉字） |
| R03 | {"paragraph": 12, "run": 1} | {"eastAsia": {"unresolved": "主题语言 ja-JP 未纳入当前唯一映射范围", "slot": "eastAsia"}} | "宋体" | 待复核：eastAsia：主题语言 ja-JP 未纳入当前唯一映射范围 | 否 | 用户确认的演示模板：正文中文字体=宋体：用户选择沿用默认值（默认PDF物理页18：正文：小四号，宋体，1.5倍行距） |
| R04 | {"paragraph": 12, "run": 1} | null | "Times New Roman" | 不适用：无该类字符 | 否 | 用户确认的演示模板：正文西文字体=Times New Roman：用户选择沿用默认值（默认PDF物理页18：英文单词：字号、行距与正文相同，字体为Times New Roman） |
| R05 | {"paragraph": 12, "run": 1} | {"pt": 12.0} | 12 | 符合 | 否 | 用户确认的演示模板：正文普通文字字号=12：用户选择沿用默认值（默认PDF物理页18：正文：小四号） |
| R06 | {"paragraph": 12} | 1.5倍 | 1.5 | 符合 | 否 | 用户确认的演示模板：正文倍数行距=1.5：用户选择沿用默认值（默认PDF物理页18：正文：小四号，宋体，1.5倍行距） |
| R07 | {"paragraph": 12} | {"first_line_chars": 2.0, "first_line_pt": 0.0, "hanging": null, "hanging_chars": null, "uniform_size_pt": 12.0} | 2 | 符合 | 否 | 用户确认的演示模板：正文首行缩进=2：用户选择沿用默认值（默认PDF物理页18：段首行缩进2个汉字） |
| R08 | {"paragraph": 5, "run": 1, "property": "font_ascii"} | {"slot": "ascii", "font": {"unresolved": "主题枚举与字体槽位不对应，需人工确认", "slot": "ascii"}} | {"slot": "ascii", "font": "Times New Roman"} | 待复核：主题枚举与字体槽位不对应，需人工确认 | 否 | 00-全员必看/本科毕业设计论文.pdf 物理页18：各章题序的阿拉伯数字用Times New Roman体；英文单词字体为Times New Roman |
| R08 | {"paragraph": 5, "run": 1, "property": "font_eastAsia"} | {"slot": "eastAsia", "font": {"unresolved": "主题语言 ja-JP 未纳入当前唯一映射范围", "slot": "eastAsia"}} | {"slot": "eastAsia", "font": "黑体"} | 待复核：主题语言 ja-JP 未纳入当前唯一映射范围 | 否 | 用户确认的演示模板：一级标题中文字体=黑体：用户选择沿用默认值 |
| R08 | {"paragraph": 5, "run": 1, "property": "size"} | {"pt": 18.0} | {"pt": 18} | 符合 | 否 | 用户确认的演示模板：一级标题字号=18：用户选择沿用默认值 |
| R08 | {"paragraph": 5, "property": "alignment"} | {"alignment": "center"} | {"alignment": "center"} | 符合 | 否 | 用户确认的演示模板：一级标题对齐=center：用户选择沿用默认值 |
| R08 | {"paragraph": 5, "property": "line"} | 1倍 | {"multiple": 1} | 符合 | 否 | 用户确认的演示模板：一级标题倍数行距=1：用户选择沿用默认值 |
| R11 | {"paragraph": 5} | {"style_id": "Heading1", "outline_level": 0} | {"style_id": "Heading1", "outline_level": 0} | 符合 | 否 | 产品结构规则：使用已存在且可验证的内置Heading 1–3及对应大纲级别；保持其他有效格式，不是学校明确规定英文样式名。 |
| R12 | {"paragraph": 7, "run": 1, "property": "font_ascii"} | {"slot": "ascii", "font": {"unresolved": "主题枚举与字体槽位不对应，需人工确认", "slot": "ascii"}} | {"slot": "ascii", "font": "宋体"} | 待复核：主题枚举与字体槽位不对应，需人工确认 | 否 | 00-全员必看/本科毕业设计论文.pdf 物理页18：插图（表）的标题和文字：五号，宋体 |
| R12 | {"paragraph": 7, "run": 1, "property": "font_eastAsia"} | {"slot": "eastAsia", "font": {"unresolved": "主题语言 ja-JP 未纳入当前唯一映射范围", "slot": "eastAsia"}} | {"slot": "eastAsia", "font": "宋体"} | 待复核：主题语言 ja-JP 未纳入当前唯一映射范围 | 否 | 用户确认的演示模板：图题中文字体=宋体：用户选择沿用默认值 |
| R12 | {"paragraph": 7, "run": 1, "property": "size"} | {"pt": 10.5} | {"pt": 10.5} | 符合 | 否 | 用户确认的演示模板：图题字号=10.5：用户选择沿用默认值 |
| R08 | {"paragraph": 9, "run": 1, "property": "font_ascii"} | {"slot": "ascii", "font": {"unresolved": "主题枚举与字体槽位不对应，需人工确认", "slot": "ascii"}} | {"slot": "ascii", "font": "Times New Roman"} | 待复核：主题枚举与字体槽位不对应，需人工确认 | 否 | 00-全员必看/本科毕业设计论文.pdf 物理页18：各章题序的阿拉伯数字用Times New Roman体；英文单词字体为Times New Roman |
| R08 | {"paragraph": 9, "run": 1, "property": "font_eastAsia"} | {"slot": "eastAsia", "font": {"unresolved": "主题语言 ja-JP 未纳入当前唯一映射范围", "slot": "eastAsia"}} | {"slot": "eastAsia", "font": "黑体"} | 待复核：主题语言 ja-JP 未纳入当前唯一映射范围 | 否 | 用户确认的演示模板：一级标题中文字体=黑体：用户选择沿用默认值 |
| R08 | {"paragraph": 9, "run": 1, "property": "size"} | {"pt": 18.0} | {"pt": 18} | 符合 | 否 | 用户确认的演示模板：一级标题字号=18：用户选择沿用默认值 |
| R08 | {"paragraph": 9, "property": "alignment"} | {"alignment": "center"} | {"alignment": "center"} | 符合 | 否 | 用户确认的演示模板：一级标题对齐=center：用户选择沿用默认值 |
| R08 | {"paragraph": 9, "property": "line"} | 1倍 | {"multiple": 1} | 符合 | 否 | 用户确认的演示模板：一级标题倍数行距=1：用户选择沿用默认值 |
| R11 | {"paragraph": 9} | {"style_id": "Heading1", "outline_level": 0} | {"style_id": "Heading1", "outline_level": 0} | 符合 | 否 | 产品结构规则：使用已存在且可验证的内置Heading 1–3及对应大纲级别；保持其他有效格式，不是学校明确规定英文样式名。 |
| R12 | {"paragraph": 11, "run": 1, "property": "font_ascii"} | {"slot": "ascii", "font": {"unresolved": "主题枚举与字体槽位不对应，需人工确认", "slot": "ascii"}} | {"slot": "ascii", "font": "宋体"} | 待复核：主题枚举与字体槽位不对应，需人工确认 | 否 | 00-全员必看/本科毕业设计论文.pdf 物理页18：插图（表）的标题和文字：五号，宋体 |
| R12 | {"paragraph": 11, "run": 1, "property": "font_eastAsia"} | {"slot": "eastAsia", "font": {"unresolved": "主题语言 ja-JP 未纳入当前唯一映射范围", "slot": "eastAsia"}} | {"slot": "eastAsia", "font": "宋体"} | 待复核：主题语言 ja-JP 未纳入当前唯一映射范围 | 否 | 用户确认的演示模板：图题中文字体=宋体：用户选择沿用默认值 |
| R12 | {"paragraph": 11, "run": 1, "property": "size"} | {"pt": 10.5} | {"pt": 10.5} | 符合 | 否 | 用户确认的演示模板：图题字号=10.5：用户选择沿用默认值 |
| R09 | {"document": 1} | null | {"font_cn": "黑体", "font_latin": "Times New Roman", "size_pt": 15, "alignment": "left", "line_multiple": 1} | 不适用：本次确认分类中没有该类对象，不凭空报错 | 否 | 用户确认的标题题注配置：二级标题中文字体=黑体：用户选择沿用默认值；二级标题字号=15：用户选择沿用默认值；二级标题对齐=left：用户选择沿用默认值；二级标题倍数行距=1：用户选择沿用默认值 |
| R10 | {"document": 1} | null | {"font_cn": "黑体", "font_latin": "Times New Roman", "size_pt": 14, "alignment": "left", "line_multiple": 1} | 不适用：本次确认分类中没有该类对象，不凭空报错 | 否 | 用户确认的标题题注配置：三级标题中文字体=黑体：用户选择沿用默认值；三级标题字号=14：用户选择沿用默认值；三级标题对齐=left：用户选择沿用默认值；三级标题倍数行距=1：用户选择沿用默认值 |
| R14 | {"paragraph": 3, "property": "before"} | {"unresolved": "有效继承路径也未设置before间距；未按0处理"} | {"value": 0.5, "unit": "lines"} | 待复核：有效继承路径也未设置before间距；未按0处理 | 否 | 用户选择沿用默认值（用户确认v4模板，不冒充学校原文）： |
| R14 | {"paragraph": 3, "property": "after"} | {"value": 0.5, "unit": "lines", "origin": ["docDefaults", "直接段落格式"], "raw": {"after": "0", "line": "240", "lineRule": "auto", "afterAutospacing": "0", "afterLines": "50"}} | {"value": 0.5, "unit": "lines"} | 符合 | 否 | 用户选择沿用默认值（用户确认v4模板，不冒充学校原文）： |
| R14 | {"paragraph": 3, "property": "alignment"} | {"unresolved": "对齐未设置/未支持或无法可靠继承"} | "center" | 待复核：对齐未设置/未支持或无法可靠继承 | 否 | 用户选择沿用默认值（用户确认v4模板，不冒充学校原文）： |
| R14 | {"paragraph": 3, "property": "line_spacing"} | 1倍 | {"multiple": 1} | 符合 | 否 | 用户选择沿用默认值（用户确认v4模板，不冒充学校原文）： |
| R14 | {"paragraph": 3, "run": 1, "property": "font_eastAsia"} | {"unresolved": "主题语言 ja-JP 未纳入当前唯一映射范围"} | "黑体" | 待复核：主题语言 ja-JP 未纳入当前唯一映射范围 | 否 | 未配置属性： |
| R14 | {"paragraph": 3, "run": 1, "property": "size"} | 18.0 | 18 | 符合 | 否 | 未配置属性： |
| R13 | {"paragraph": 5, "property": "before"} | {"value": 0.5, "unit": "lines", "origin": ["docDefaults", "paragraph样式:Heading1", "直接段落格式"], "raw": {"after": "0", "line": "240", "lineRule": "auto", "before": "0", "beforeAutospacing": "0", "beforeLines": "50", "afterAutospacing": "0", "afterLines": "50"}} | {"value": 0.5, "unit": "lines"} | 符合 | 否 | 用户选择沿用默认值（用户确认v4模板，不冒充学校原文）： |
| R13 | {"paragraph": 5, "property": "after"} | {"value": 0.5, "unit": "lines", "origin": ["docDefaults", "paragraph样式:Heading1", "直接段落格式"], "raw": {"after": "0", "line": "240", "lineRule": "auto", "before": "0", "beforeAutospacing": "0", "beforeLines": "50", "afterAutospacing": "0", "afterLines": "50"}} | {"value": 0.5, "unit": "lines"} | 符合 | 否 | 用户选择沿用默认值（用户确认v4模板，不冒充学校原文）： |
| R13 | {"paragraph": 9, "property": "before"} | {"value": 0.5, "unit": "lines", "origin": ["docDefaults", "paragraph样式:Heading1", "直接段落格式"], "raw": {"after": "0", "line": "240", "lineRule": "auto", "before": "0", "beforeAutospacing": "0", "beforeLines": "50", "afterAutospacing": "0", "afterLines": "50"}} | {"value": 0.5, "unit": "lines"} | 符合 | 否 | 用户选择沿用默认值（用户确认v4模板，不冒充学校原文）： |
| R13 | {"paragraph": 9, "property": "after"} | {"value": 0.5, "unit": "lines", "origin": ["docDefaults", "paragraph样式:Heading1", "直接段落格式"], "raw": {"after": "0", "line": "240", "lineRule": "auto", "before": "0", "beforeAutospacing": "0", "beforeLines": "50", "afterAutospacing": "0", "afterLines": "50"}} | {"value": 0.5, "unit": "lines"} | 符合 | 否 | 用户选择沿用默认值（用户确认v4模板，不冒充学校原文）： |
| R15 | {"document": 1} | null | null | 不适用：当前模板未配置或确认范围无该对象，不套正文规则 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R16 | {"document": 1} | null | null | 不适用：当前模板未配置或确认范围无该对象，不套正文规则 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R17 | {"document": 1} | null | null | 不适用：当前模板未配置或确认范围无该对象，不套正文规则 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R18 | {"document": 1} | null | null | 不适用：当前模板未配置或确认范围无该对象，不套正文规则 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R19 | {"document": 1} | null | null | 不适用：当前模板未配置或确认范围无该对象，不套正文规则 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R20 | {"document": 1} | null | null | 不适用：当前模板未配置或确认范围无该对象，不套正文规则 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R21 | {"document": 1} | null | null | 不适用：当前模板未配置或确认范围无该对象，不套正文规则 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R38 | {"document": 1} | null | null | 不适用：当前模板未配置或确认范围无该对象，不套正文规则 | 否 | 新对象未配置或当前范围无对象；不推定学校要求/已通过： |
| R39 | {"document": 1} | null | null | 不适用：当前模板未配置或确认范围无该对象，不套正文规则 | 否 | 新对象未配置或当前范围无对象；不推定学校要求/已通过： |
| R40 | {"document": 1} | null | null | 不适用：当前模板未配置或确认范围无该对象，不套正文规则 | 否 | 新对象未配置或当前范围无对象；不推定学校要求/已通过： |
| R41 | {"document": 1} | null | null | 不适用：当前模板未配置或确认范围无该对象，不套正文规则 | 否 | 新对象未配置或当前范围无对象；不推定学校要求/已通过： |
| R22 | {"document": 1, "property": "存在_abstract_cn_title"} | 1 | ">=1" | 符合：只统计确认类型；未发现时须核对分类，不能直接断言文档物理缺少或补写内容 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R22 | {"document": 1, "property": "存在_abstract_cn_body"} | 0 | ">=1" | 待复核：只统计确认类型；未发现时须核对分类，不能直接断言文档物理缺少或补写内容 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R22 | {"document": 1, "property": "存在_abstract_en_title"} | 0 | ">=1" | 待复核：只统计确认类型；未发现时须核对分类，不能直接断言文档物理缺少或补写内容 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R22 | {"document": 1, "property": "存在_abstract_en_body"} | 0 | ">=1" | 待复核：只统计确认类型；未发现时须核对分类，不能直接断言文档物理缺少或补写内容 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R22 | {"document": 1, "property": "存在_keywords_cn"} | 0 | ">=1" | 待复核：只统计确认类型；未发现时须核对分类，不能直接断言文档物理缺少或补写内容 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R22 | {"document": 1, "property": "存在_keywords_en"} | 0 | ">=1" | 待复核：只统计确认类型；未发现时须核对分类，不能直接断言文档物理缺少或补写内容 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R22 | {"document": 1, "property": "存在_reference_title"} | 0 | ">=1" | 待复核：只统计确认类型；未发现时须核对分类，不能直接断言文档物理缺少或补写内容 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R22 | {"document": 1, "property": "存在_reference_item"} | 0 | ">=1" | 待复核：只统计确认类型；未发现时须核对分类，不能直接断言文档物理缺少或补写内容 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |
| R22 | {"document": 1, "property": "参考文献条目数"} | 0 | "确认条目≥10（主要文献/外文身份另核对）" | 问题：按人工确认条目计数；不足时核对范围或资料，不生成文献；不判断主要文献身份、语种或所有著录格式 | 否 | 2015范例只读口径（用户明确启用，不由AI提取）：00-全员必看/本科毕业设计论文.pdf 物理页16：摘要400–600字，关键词3–5个，主要参考文献10篇以上/外文2篇以上；本程序只统计确认条目，外文与主要文献身份未判断。 |

## 字体及编号只读解析证据

文档指定字体用于属性检查；本机字体安装与替代由独立预览核对。
- R03:paragraph=6:run=1：{"font": {"eastAsia": {"font": null, "slot": "eastAsia", "source_type": "missing", "declared_at": "docDefaults", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "minorEastAsia", "reason": "主题语言 ja-JP 未纳入当前唯一映射范围"}}, "numbering": null}
- R04:paragraph=6:run=1：{"font": {"ascii": {"font": null, "slot": "ascii", "source_type": "missing", "declared_at": "docDefaults", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "minorHAnsi", "reason": "主题枚举与字体槽位不对应，需人工确认"}}, "numbering": null}
- R03:paragraph=8:run=1：{"font": {"eastAsia": {"font": null, "slot": "eastAsia", "source_type": "missing", "declared_at": "docDefaults", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "minorEastAsia", "reason": "主题语言 ja-JP 未纳入当前唯一映射范围"}}, "numbering": null}
- R03:paragraph=10:run=1：{"font": {"eastAsia": {"font": null, "slot": "eastAsia", "source_type": "missing", "declared_at": "docDefaults", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "minorEastAsia", "reason": "主题语言 ja-JP 未纳入当前唯一映射范围"}}, "numbering": null}
- R04:paragraph=10:run=1：{"font": {"ascii": {"font": null, "slot": "ascii", "source_type": "missing", "declared_at": "docDefaults", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "minorHAnsi", "reason": "主题枚举与字体槽位不对应，需人工确认"}}, "numbering": null}
- R03:paragraph=12:run=1：{"font": {"eastAsia": {"font": null, "slot": "eastAsia", "source_type": "missing", "declared_at": "docDefaults", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "minorEastAsia", "reason": "主题语言 ja-JP 未纳入当前唯一映射范围"}}, "numbering": null}
- R08:paragraph=5:run=1:property=font_ascii：{"font": {"ascii": {"font": null, "slot": "ascii", "source_type": "missing", "declared_at": "paragraph样式:Heading1", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "majorHAnsi", "reason": "主题枚举与字体槽位不对应，需人工确认"}}, "numbering": null}
- R08:paragraph=5:run=1:property=font_eastAsia：{"font": {"eastAsia": {"font": null, "slot": "eastAsia", "source_type": "missing", "declared_at": "paragraph样式:Heading1", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "majorEastAsia", "reason": "主题语言 ja-JP 未纳入当前唯一映射范围"}}, "numbering": null}
- R12:paragraph=7:run=1:property=font_ascii：{"font": {"ascii": {"font": null, "slot": "ascii", "source_type": "missing", "declared_at": "docDefaults", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "minorHAnsi", "reason": "主题枚举与字体槽位不对应，需人工确认"}}, "numbering": null}
- R12:paragraph=7:run=1:property=font_eastAsia：{"font": {"eastAsia": {"font": null, "slot": "eastAsia", "source_type": "missing", "declared_at": "docDefaults", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "minorEastAsia", "reason": "主题语言 ja-JP 未纳入当前唯一映射范围"}}, "numbering": null}
- R08:paragraph=9:run=1:property=font_ascii：{"font": {"ascii": {"font": null, "slot": "ascii", "source_type": "missing", "declared_at": "paragraph样式:Heading1", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "majorHAnsi", "reason": "主题枚举与字体槽位不对应，需人工确认"}}, "numbering": null}
- R08:paragraph=9:run=1:property=font_eastAsia：{"font": {"eastAsia": {"font": null, "slot": "eastAsia", "source_type": "missing", "declared_at": "paragraph样式:Heading1", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "majorEastAsia", "reason": "主题语言 ja-JP 未纳入当前唯一映射范围"}}, "numbering": null}
- R12:paragraph=11:run=1:property=font_ascii：{"font": {"ascii": {"font": null, "slot": "ascii", "source_type": "missing", "declared_at": "docDefaults", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "minorHAnsi", "reason": "主题枚举与字体槽位不对应，需人工确认"}}, "numbering": null}
- R12:paragraph=11:run=1:property=font_eastAsia：{"font": {"eastAsia": {"font": null, "slot": "eastAsia", "source_type": "missing", "declared_at": "docDefaults", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "minorEastAsia", "reason": "主题语言 ja-JP 未纳入当前唯一映射范围"}}, "numbering": null}
- R14:paragraph=3:run=1:property=font_eastAsia：{"font": {"eastAsia": {"font": null, "slot": "eastAsia", "source_type": "missing", "declared_at": "docDefaults", "hint": "default", "run_language": {"val": "en-US", "eastAsia": "en-US", "bidi": "ar-SA"}, "computer_font_installation_checked": false, "safe_to_fix_slot": false, "theme": "minorEastAsia", "reason": "主题语言 ja-JP 未纳入当前唯一映射范围"}}, "numbering": null}

## 修改依赖提示

没有已预测的关联影响；不表示不存在其他未支持依赖。

## 覆盖提示

- {"paragraph": 8, "run": 1}：含未支持字体槽位的字符（如希腊文、符号、emoji）；其字体未验证
- {"paragraph": 10, "run": 1}：含未支持字体槽位的字符（如希腊文、符号、emoji）；其字体未验证
- {"paragraph": 12, "run": 1}：含未支持字体槽位的字符（如希腊文、符号、emoji）；其字体未验证

## 封面、页眉页脚与页码边界

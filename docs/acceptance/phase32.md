# 第三十二阶段 内部引用结构及安全内部链接文字

2026-10-16。开工main=`fe441e2`，与origin一致，工作区干净。原1145项实跑161.298秒通过。本阶段新增**可选R44产品结构检查**，非2015学校格式规定；未新增学校字体、页码或编号要求。旧CLI、模板、项目没有reference_scope时语义和规则数保持。

## 官方依据与产品口径

实现前实际核对Microsoft primary documentation：

- [BookmarkStart与ID配对](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.bookmarkstart?view=openxml-3.0.1)：开始/结束按ID和文档顺序关联；列范围书签可能不是普通连续范围，首版待复核。
- [Word与标准的书签实现差异](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oe376/88454e96-31cb-4112-b7c2-e6b0f84a2637)：重复名称存在不同目标选择行为，产品不替用户选；名称首版仅明确ASCII字母/下划线开头、字母/数字/下划线、至多40字符。隐藏书签保留，大小写近似不猜测匹配。
- [Hyperlink结构](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.hyperlink?view=openxml-3.0.1)及[anchor属性](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.hyperlink.anchor?view=openxml-3.0.1)：只开放anchor单一内部目标；r:id/docLocation组合及未知属性保持保护。
- [REF说明](https://support.microsoft.com/en-us/word/field-codes-ref-field)、[PAGEREF说明](https://support.microsoft.com/en-us/word/field-codes-pageref-field)：区分指令、目标和保存结果。读取静态名称和已支持开关不代表求值、缓存新鲜或实际页码验证。不存在自动刷新/保存步骤。

官方允许的全部OOXML结构不等于本原型全部支持。名称、开关和容器边界是保守产品支持范围，不包装成新的校规。

## 覆盖表

| 对象/要求 | 检查与判定 | 修正范围 | 限制 |
| --- | --- | --- | --- |
| 主文档书签、anchor | 名称、ID、唯一边界、先后次序、精确目标 | R44全部只读 | 不创建/删除/改名，重复/近似名称待复核 |
| 验证关系和内容类型的页眉/页脚、脚注/尾注 | 同一索引列部件/故事/稳定XML位置；注释支持部件改名 | 页眉页脚链接文字不开放 | 不以文件名存在证明故事正常；注释引用异常保持不确定 |
| 简单/复杂REF/PAGEREF | 复用TOC字段栈，支持拆分instrText、跨段位置和嵌套/断裂状态 | 不改指令、边界、缓存、dirty/locked | 指令4096字符、128词元；未知或含糊开关/名称只读待复核 |
| PAGE/SEQ/STYLEREF | 指令清单，明确不是本R44书签引用 | 不求值或改号 | 缓存/实际数字未验收 |
| 缺失目标 | 覆盖充分、解析可靠时problem；不完整时review | 不自动补造 | 未覆盖故事也阻止对已知目标宣称全局唯一并授权文字修正 |
| 目录对应 | 启用R44时共用目标解析证据，保留原标题范围/文字比较 | 自动目录缓存仍只读 | 目录重复呈现与目标故障不直接相加 |
| 正文、参考文献、脚注/尾注普通内部链接 | 第二个开关明确启用；目标唯一有效、直属普通run、原对象已确认 | 原已配置文字属性，逐属性选择 | 只改所选rPr；不解链接、不改共享样式/关系/目标 |
| 链接段落pPr、R11、R33、表格和页眉页脚链接文字 | 原保护保持 | 未开放 | 不能借有效目标绕过字段、SDT、修订等复杂结构 |
| 真实跳转、实际页码、缓存新鲜、引用语义 | 独立人工/视觉观察 | 不自动处理 | 结构通过不是全文合格 |

## 实现与绑定

`core/internal_refs.py`组合已验证故事清单及不可变JSON索引，每个Package独立保存、无全局文档缓存或可变XML共享；目标查询使用只读字典。以部件、注释故事/ID、内部段落和XML序号定位，不把注释/SDT段落插入旧顶层编号。系统分隔注释不按ID正负推断，不作为普通文字跳转修正目标。

R44按目标/解析故障分组并保留每个受影响引用位置；无引用不判缺项，有效但未引用书签不判错。普通摘要没有大段目标正文。字节读取不访问链接、执行域或调用AI。故事节点/对象设上限，超限明确拒绝，不以部分扫描冒充完整。

`reference_scope`带输入哈希、确认及结构v1补充配置（integrity/internal_text/product_structure来源）；停用走原模块开关。旧载荷不增加字段或规则数。新状态进入分类原校验、统一预检/原子确认、执行版本哈希、预演、两步计划、历史、补充JSON、项目、HTML/JSON/Markdown和结果ZIP。L05只重绑本补充配置的哈希，移动后重新建索引；没有把旧目标位置复制到新文件。

普通内部文字复用`text_runs.walk`/`executable_run`、Resolver及原精确rPr事务。直属run序号保持，链接另用link/link_run；重复文字/相同anchor也按XML位置区分。未改变paragraph_unsafe的全局规则。注释只修改选中故事部件，主文档无意义重序列化被阻止。恢复必须实际重新读取；不恢复预演/采用授权或旧视觉结论。

## 合成结果及独立文件证据

[完整文件索引](../../samples/phase32/README.md)和[作者手写清单](../../samples/phase32/independent-plan.json)说明4个书签、12个引用位置、4个目标/解析组。MissingTarget由2处hyperlink及1处PAGEREF引用，保存缓存仍为7；R44报告**1个确定目标故障，3处受影响位置**。

原稿8条规则问题/44条待复核；只选择5处字号：正文p3后半run、p4重复文字链接之一、参考文献p10、脚注及尾注。修改后3问题/44待复核：保留R44目标故障、未选R07缩进、R22参考文献数量；其余复杂/段落属性覆盖继续保留。`correct.docx`只对这5处字体大小作作者独立正确对照，保留故障与未选项，不是整篇合规文件。

[独立ZIP/XML脚本](../../scripts/verify_internal_reference_output.py)不导入新索引、遍历器或引擎掩码：在手写位置核对实际sz，然后只还原这些属性，对完整XML树作canonical比较；所有其余ZIP成员逐字节核对。文字空白/顺序、全部书签边界/名称/ID、链接属性、关系、字符样式、未选颜色下划线、字段指令/缓存、分节及注释标记均保持。[独立结果](../../samples/phase32/independent-check.json)、[浏览器文件核对](../../samples/phase32/browser-independent.json)通过。原稿和前轮保持；正确文件重复修正无额外字节变化。

[单轮实际预演](../../scripts/reproduce_internal_reference_demo.py)与直接合法修正、独立正确对照、网页最终副本逐字节一致。预演一次完整修正、采用0次完整重修、重复采用只登记一轮。另有实际两步测试：普通内部链接文字与另一个安全段落的R33分别走原事务，R33含链接/书签段落继续保护。

## 自动、干净目录与复现

新增46项及多组子场景覆盖：目标与故障口径、无副作用与不可变索引、旧开关、跨部件/改名注释/页眉目标、内容类型及关系异常、重复/反向/孤立边界、隐藏书签/大小写近似、字段拆分/跨段/嵌套/断裂/开关/错误引号、未覆盖故事及容量、后半run/重复文字/字体槽位、精确事务与未选保护、单轮与两步、恢复/草稿/失效/双会话、TOC共享证据及离线报告。

原1145项修改后首次回归：一项原“所有区域已启用”的断言合理扩大为原七区域保持+新R44明确关闭；同输入、原对象断言保留。另一条预演在测试期间源码哈希变化被主动拒绝；稳定代码后的103项针对性回归通过。新增46项4.740秒通过，先前1189项完整166.437秒通过；最终冻结源码在干净目录完整1191项163.137秒通过；当前core/web/tests/scripts全部Python源文件逐字节匹配该快照。无work/outputs/.env/学校PDF和可用渲染器路径，显式移除API环境后的离线复现及独立核对通过。

```bash
python -m unittest discover -s tests
python scripts/reproduce_internal_reference_demo.py --output /tmp/paperfit-phase32-new
python scripts/verify_internal_reference_output.py samples/phase32/errors.docx /tmp/paperfit-phase32-new/fixed.docx
python scripts/measure_internal_references.py --output /tmp/paperfit-phase32-measure.json
python scripts/check_repository.py
```

干净目录只复制Git交付源码/合成夹具，无work/outputs/.env/真实论文/学校PDF，渲染路径指向不存在的位置，无API Key依赖。CI使用Ubuntu/Python3.12；只有推送后本次SHA的实际运行才能称远端通过，不借用旧阶段CI。

## 真实浏览器与状态验证

[本轮真实Chrome记录](../../samples/phase32/browser-acceptance.json)。网页项目上传/核对恢复载入合成草稿；明确开关R44，核对目标、局部位置及缓存存在；统一范围确认后实际检查。段3只选择一个链接run的一项R05，预演/明确采用/网页下载，独立核对只有一处字号变化。明确下一轮，再按“字号”筛选且明确选择4项，列表显示正文、参考文献、脚注和尾注，实际预演/采用/下载。过滤不代替选择。

保存网页两轮项目后，仅核对本项目8501进程命令与cwd再重启，网页重新导入/核对恢复，当前第2轮、配置、范围、材料保护、2轮历史保持，25条启用规则、3问题/44待复核来自本次重新检查；未恢复预演或有效页图。改变internal_text开关后当前确认/报告/修正下载失效，草稿保留。独立Chrome上下文初始没有第一会话的文档，载入另一个内置样本，R44和内部文字支持未启用，未串用文件或结果。

截图：[缺失目标与缓存](../../samples/phase32/screenshots/missing-target.png)、[有效目标](../../samples/phase32/screenshots/valid-target.png)、[单属性预演](../../samples/phase32/screenshots/one-attribute-rehearsal.png)、[恢复](../../samples/phase32/screenshots/restored-current.png)、[配置变化](../../samples/phase32/screenshots/config-invalidated.png)。截图等待筛选总数实际更新后保存；不把输入框刚改变、旧表格未重建的瞬间当验证结果。一次隐藏checkbox check()超时及几次下拉菜单因重运行关闭，重新读取UI并真实点击后完成，失败尝试不冒充通过或计时成绩。

## 全页渲染与本轮Word

[完整视觉记录](../../samples/phase32/visual-record.json)。使用workspace dependency核对的bundled LibreOfficeDev26.8/Poppler，原稿、独立格式对照、网页最终各1页，全部3页目视。5处文字字号变化可见，文字、颜色/下划线、前后内容、代码空白、脚注/尾注和标记保留，无新增裁切丢字。主题字体仍提示“不是全字形审计”，不宣称所有字体环境一致。前后DOCX哈希不变。

**渲染环境差异**：LibreOffice求值缺失PAGEREF显示“Error: Reference source not found”，并求值REF/PAGE/SEQ/STYLEREF；Word16.80实际打开本轮最终仍显示保存缓存7/合成目标标题/1。没有用LO错误文本作为R44算法输入，没有将渲染求值结果回写正式文件，也没有据物理页号判断印刷页码。

Word16.80本轮实际打开browser-final.docx，无修复提示，查看全页普通链接、参考文献、脚注和尾注。先用原生书签导航实际选中TargetTwo；随后实际点击参考文献链接，选中`_TocTarget`的“1 合成目标标题”，[真实点击后截图](../../samples/phase32/screenshots/word-link-jumped.png)。未点击外部网址；关闭未保存，最终哈希与对照/浏览器下载仍相同。最初坐标/键盘菜单尝试未产生跳转，未算成功；只有最终可观察的目标选择作为跳转证据。这个合成文件的1次已知链接跳转不证明全部引用、缓存或实际页码正确。

## 成本、限制及交付

[原始3次测量](../../samples/phase32/measurements.json)：macOS/Python3.14.5，小样本4书签/12引用，索引中位1.20ms，10000次重复查询12.60ms；增加1000目标后1004书签/1012引用，索引49.40ms，10000次查询12.64ms。索引一次建立后查字典，没有逐引用扫描全文；这是本地函数成本，非浏览器等待，无可比旧算法，不宣称提速比例。

[实际预演/采用数据](../../samples/phase32/efficiency.json)：一次修正调用、采用0次完整重修；约42ms预演、67ms采用，1正式轮，原页面浏览器另走1+4两轮。0新增AI、0检查时网络访问、0自动渲染。视觉页图仅主动验收生成。

尚不支持：所有Unicode书签名/大小写推断、列范围/系统分隔对象目标、未覆盖故事或异常关系、未知开关和目标形式、任意嵌套包装；不修书签/引用/目录/编号，不刷新域或计算实际页码。文字修正范围小于只读清单范围，R33、链接段落属性、表格/页眉页脚、自动目录等保持原保护。0文字格式问题也不证明目标完整、缓存新鲜或全文合格。

本阶段独立commit并正常push main；对应CI、最终完整/干净目录记录按本次提交核对。无历史work/outputs、密钥、学校PDF、组员资料或真实论文进入Git。

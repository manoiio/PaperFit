# 第53阶段：文字规范化、Word原生预览与PDF

实际基线main/571cab7，1379项；开工工作区干净、远端一致。顺序：复查第52阶段重影 → 公共文字属性及精确事务 → 原规则/短ID/表单/恢复 → 隔离Word PDF与有界页图队列 → 智能成果整合 → 浏览器、独立文件及离线回归。未新增规则编号或依赖，未触发远端完整CI。

## 用户怎样使用

普通默认仍为上传、开始、下载；没有明确效果要求，不自动清除字符效果。可填写“正文不使用阴影和轮廓，字符缩放100%，标准字符间距”，也可通过TXT/DOCX要求文件或已保存要求输入。仅覆盖明确字段，未提及的加粗、颜色、样式等保持。

可在开始前一次勾选“同时生成Word原生预览和PDF”。正式DOCX完成立即可下载，PDF后台生成；完成页集中提供DOCX、查看Word页面、PDF及可选含PDF结果包。没有勾选的旧任务不会追加渲染。两入口使用同一队列、缓存和文件绑定，本地工作台默认零API。

实际首轮合成API流程：上传、选择完整方案、填写补充、勾选PDF、开始、下载DOCX，6项主要操作；PDF下载另1次，0个例外、0次高级工作区。最终合法正例复用保存要求：上传、选方案、选已保存来源、上传规则、勾选PDF、开始、下载，7项；没有规范解析请求。不是“新增字段即提高准确率”。

## 实际能力矩阵

| 属性 | 支持 | 精确边界 |
|---|---|---|
| 字体 | 原中文/ASCII/Latin槽位、直接/字符/段落样式及可证明主题 | 保持既有字体白名单；同槽位主题优先关系按原局部写入器处理；补齐ja-JP→Jpan、ko-KR→Hang及ASCII/HAnsi主题别名解释；不写入预览别名、不替换缺失字体、不改编号符号 |
| 阴影/轮廓/浮雕/印入 | 有明确布尔要求，读有效继承/toggle及来源，局部显式覆盖 | 互斥组合拒绝；实际声明冲突保持待复核。开启效果若与未选既有效果冲突，不偷偷关闭另一属性；需先明确关闭并重查 |
| 水平缩放 | 50–200%，整数 | XML w:w；不改字符内容/字号 |
| 字符间距 | −5–20磅，0.05磅步长 | XML rPr/spacing，twip；不是段前后间距 |
| 基线偏移 | −20–20磅，0.5磅步长 | XML position，半磅；仅普通文字，未放开上标/下标、隐藏、fitText及其他特殊条件 |
| 对象 | 正文、一至三级标题、图/表题、中英文摘要标题/正文、参考文献标题/普通条目、附录/致谢标题及普通文字 | 仅原确认分类中安全直属普通run；本轮效果不扩展关键词片段、表内、注释或链接内部；这些对象原有字体能力继续原范围 |
| 规则 | 原整包格式1、可选v8模板、严格来源及原编译 | 旧v2–v7值与含义不变；缺少新字段为未启用；旧编辑状态补齐keep/None而非默认要求；旧协议不能带新效果 |
| Word PDF | 本机macOS Word16.80真实PDF导出，最终DOCX哈希绑定 | 外部关系、活动/嵌入对象、签名、危险域、断裂域拒绝；DOCX继续可下载。没有Windows后端、PDF输入或OCR |
| 页图 | 同一PDF一次生成；10页一批、最多50页/100MB缓存，PDF≤100MB且≤2000页 | 显式生成后续批次，不为翻页重新导出；独立引擎缓存，同页号不是内容自动对齐；LO仍最多前10页 |

新效果使用原检查、fix_document、精确mask、读回复查、预演/两步计划及采用链路。只允许选中run的选中rPr属性变化；没有全局样式清理或preservation放宽。规则/候选/草稿完整输入冲突校验保留。执行绑定涵盖新增core代码，onepass-9及新短ID协议使旧任务资格失效。

## 重影证据与尚未证明的部分

第52阶段实际下载的二/三级标题直接属性及继承链中，未发现shadow/outline/emboss/imprint/w/spacing/position效果声明或重复标题文字。文档其他6个字符样式含spacing声明，未把它们误当成本次标题的有效格式。有效主题ja-JP指向MS Gothic，标题继承加粗。原Word PDF嵌入MS-Gothic，相关字形使用填充＋描边（2 Tr）。[控制对照](../../samples/phase53/ghost-controls.png)分别只改二/三级中文字体、只关闭这两处加粗；编号定义及正文保持。换黑体后仍偏重，关闭加粗后双边观感明显减轻，支持“字形加粗描边参与该现象”的判断；没有证明Word内部字形合成的全部根因。不是阴影清理修好了第52阶段重影。

正式要求没有要求去掉加粗，因此正式文件保留加粗和蓝色。控制副本不冒充正式结果。Mac锁屏阻止本轮Word窗口人工观察，**用户明确要求留到下一阶段**；本轮有真实Word计算/PDF导出及页图观察，没有新增Word窗口人工验收或实际点击跳转结论。

## 实网、正反例及实际输出

仅1次公开规范请求，DeepSeek flash、非思考JSON；1.374秒，服务端prompt1196/completion214/total1410，计费状态未知。13字段全部与独立手写预期一致，真实值和来源已用于实际修正；结构候选由本地确定，结构API为0。原始公开请求、响应、适配及回执见[索引](../../samples/phase53/README.md)。普通测试模拟且硬拦截付费HTTP/Word。

首轮原稿把四种效果都放在同一字符样式中。查核官方约束后保留为[冲突反例](../../samples/phase53/conflicting-effects.docx)，不再把它当合法正例。最终正例将shadow+outline、emboss、imprint分放不同段落；**规范原文及唯一API响应没有改变**。最终浏览器用这次真实解析保存的13字段规则包重新开始，不人工替换模型答案，也没有追加API。首轮audit明确标为历史反例处理记录，不能套用它的论文哈希到最终正例。

最终[浏览器下载DOCX](../../samples/phase53/fixed.docx) SHA `8e2840016084d550617eeebb1a18b57d392579155f41d9c92a84fa950db92f22`，与本地原合法编排、同规则/范围/计划、独立Word重新计算的整份文件逐字节一致。本地29.767秒、4正式轮、0API。四阶段为普通格式169属性（其中新增效果7）、页码结构7项、相邻2项、目录1个；数量不相加为解决问题数。最终仍有8问题、91项需留意；效果清理后部分原受保护属性变得可判定，不自动追修新问题。

[独立ZIP/XML脚本](../../scripts/verify_visual_output.py)不导入新解析器、Resolver或mask：精确反向掩码选中属性后全XML一致；普通阶段其余部件逐字节一致；上标[1]整个run保持；页码阶段4个新footer及原关系/内容类型精确核对；仅p2的keepNext/keepLines变化；目录阶段仅授权SDT缓存及4个目标书签变化。numbering.xml、标题numPr/样式及原文字不变；原始规则JSON逐字段对照第52阶段默认包，13个预期值及连续来源正确，未触及值/来源、其他模块及禁用项相同，其余新效果字段仍为None/未启用。样本无图片/表格/注释，不能把这些对象的回归测试称为本样本的实机观察。

## Word输出、页面及真实浏览器

Word PDF在独立导出快照中先锁定非PAGE域，再打开、重新分页和导出；只关闭本任务副本，不保存DOCX、不全局关闭Word。与目录计算共用跨进程串行锁及超时隔离。Word document.fields返回的主故事非PAGE结果在导出前后比较，其他部件按XML预先锁定，未声称逐域实机观察了所有故事；PAGE及自动编号仍由Word显示计算；**PDF不是原DOCX缓存已新鲜的证明**。第50阶段缺失目标/锁定域/SEQ案例另做实机输出，8个非PAGE域冻结，缓存保持，原DOCX哈希不变；该保护案例PDF被Poppler读取时有xref重建提醒，未称其PDF结构无警告。主正例PDF无此提醒。外部/危险对象会明确降级。

正例实际Word PDF12页，原稿10页，全部页图已查看：普通效果可见变化、上标保持、目录/章节页脚存在，未观察到新增明显裁切；未把小比例总览当像素测量。目录4条页码1/2/3/6，对应最终Word只读测量物理3/4/5/8，编号1/1.1/1.1.1/5。实际下载、PDF和ZIP的源哈希与内容一致。导出约0.55秒（不含格式/目录阶段），初批页图全流程约1.5秒；PDF元数据时间可能不同，不以两次独立PDF字节比较替代来源核对。

1280×720、1440×900真实页面完成：明确PDF选项、真实API→修正→DOCX/PDF/ZIP下载；Word单份、同引擎并排、原稿10/最终12页缺页提示；页11/12按批生成，导航和下载不新增Word导出。LO显式生成仍可用，不自动双渲染。首轮发现ZIP反复重建造成卡顿、页图完成通知时序及缩放控件类型问题，均修复并加回归；未把中途终止套件算通过。重启后真实项目恢复重新检查、v8规则及4轮历史保留，预览/授权不恢复，不自动发API/Word；另一个浏览器会话保持独立。取消/Word不可用/缓存外改/队列及清理边界主要由受控测试验证，不冒称全部为实机故障演练。

[结果首屏](../../samples/phase53/result-1280.png)、[1440窗口](../../samples/phase53/result-1440.png)、[第11页](../../samples/phase53/word-page11-browser.png)、[不同页数](../../samples/phase53/word-different-pages.png)、[全部最终页](../../samples/phase53/fixed-all-pages.png)。DOCX先可下载，PDF失败不撤销合法DOCX。项目包不保存PDF/页图或后台授权，结果ZIP只有用户明确选择时增加PDF和生成记录，不打包全部页图。

## 测试及复现

最终冻结源码完整离线 **1398项通过，740.287秒**，付费HTTP/真实Word调用及漏模拟拦截均0，见[validation.json](../../samples/phase53/validation.json)；不触发远端完整CI。相关测试覆盖来源、互斥、未启用迁移、基线特殊保护、精确mask、字段文件、恢复、PDF批次/取消/缓存和UI重运行。后续页图批次成功接入后立即释放独立输入快照目录；PDF和现有页图保持，所有权/清理断言另有受控测试。旧正文、R11及TOC日本主题案例因新增可靠字体映射从review变为problem，保留相同输入及“未知主题/缺少Jpan映射仍只读、R11不把低层字面字体提升覆盖高层主题、非授权部件保持”的更强断言，没有删除保护场景。相同第51阶段综合夹具用旧Resolver重放为129处，当前为223处，新增94处全部是有可靠主题依据的字体属性（其中74处表内中文字体）；布局/动态阶段未增加。原流程测试据此更新精确数量及字体清单断言，见theme-coverage-regression.json。

```sh
python scripts/run_offline_tests.py
python scripts/check_repository.py
python scripts/verify_visual_output.py samples/phase53
python scripts/reproduce_visual_output.py --output /tmp/paperfit53 --word --rules samples/phase53/rules.json
```

最后一条明确调用本机Word，复用真实已保存规则，0HTTP；输出目录须不存在。去掉--word为模拟协议/普通格式复现，不冒充Word闭环。旧SCUT默认没有效果字段，仍按原要求执行。8501为本机服务，不部署。

官方依据：[Shadow](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.shadow?view=openxml-3.0.1)、[Emboss](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.emboss?view=openxml-3.0.1)、[字符间距](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.spacing?view=openxml-3.0.1)、[基线位置](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.position?view=openxml-3.0.1)。Word导出接口以本机Word.sdef和实际公开副本验证为准，不以字典存在代替成功。

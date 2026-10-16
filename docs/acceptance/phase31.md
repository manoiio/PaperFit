# 第三十一阶段：确认引文上标段落的安全段落属性

2026-10-16。开工main=`d08d16b`，与origin一致、工作区干净；原1118项147.495秒通过。扩大R06/R07/R13已有范围，无新增规则、模板字段、AI调用或自动渲染。旧CLI及未确认/复杂上标语义保持。

## 判定范围和实现

`core/citation_paragraphs.py`集中复用citation_scope原校验、当前v1/v2受限解析器及R33安全结构判断。按输入哈希、确认用途、准确字符范围、完整引文原文、语法及Resolver有效vertAlign/继承逐区间证明上标归属。只在确认正文且唯一额外特殊因素是这些上标时，有限放行R06行距、R07首行缩进、R13已配置段前/段后/对齐；没有全局删除special/superscript保护。

证据保存已验证引文区间、正文范围、字号依据run、识别的上标来源、结构阻止和逐属性允许/待复核。纯基线空白不作字号/文字宽度依据；区间外上标空白也阻止放行；空run或无普通w:t结构不猜用途。Unicode上下标正文继续保守保护。部分确认可局部判断，不把完整范围声明改成true。

R07字符单位、点值及二者冲突分别判断。点值依据只用确认引文之外的非空白普通正文；引文9pt/8pt、上标显示缩放及引文字宽不参与。普通正文混字号、未知字号、缩放/字间距异常、仅引文无可靠正文等保持待复核。字符单位不需要猜点值；若同时存在非零点值则仍核对冲突。直接悬挂按原规则报冲突，继承悬挂/自动编号继续保护。

R06固定、最小值、倍数区分保持；异常/重复属性、未知继承、网格/吸附保留。R13磅与行不互换，自动/上下文间距、单位冲突继续保护；未配置不检查。文档网格影响行单位段距时待复核，对齐独立读取。链接、域、书签、修订、公式、SDT、R11切换及R33边界均未扩大。

修正仍使用原fix_document、精确pPr白名单、落盘重读及事务完整性。只改变明确选择的属性，全部run子树与引文行内字体/字号/上标/样式保持。不改共享样式、不重写文字、没有第三步自动修正。预演执行哈希遍历全部core模块，新增代码纳入绑定。

## 实际变化与独立证据

[合成样本和完整索引](../../samples/phase31/README.md) · [作者独立清单](../../samples/phase31/independent-errors.json) · [同规则/范围前后比较](../../samples/phase31/baseline-comparison.json) · [最终DOCX](../../samples/phase31/fixed.docx) · [HTML](../../samples/phase31/report.html) · [ZIP](../../samples/phase31/result.zip)。

从d08d16b源码归档在独立目录运行，同一原稿、规则文件与分类/引文范围：旧0问题/51待复核（33规则+18覆盖），新14问题/37待复核（19规则+18覆盖）。14条是段3、4各R06/R07/R13三属性，段7的R06/R13三属性，从review变为真实问题；没有删除18条覆盖记录。普通正文/引文行内保护仍分别说明，不把待复核减少称准确率。

真实原事务分两轮：先仅段3的R06，再明确切换输入修其余13条；最终0问题/37待复核。段5未确认上标、段6引文外上标及段7仅引文点值缩进保持。原稿、第一轮及第二轮副本保留。首次预演约0.094秒、采用约0.183秒；两次实际修正、采用0次完整重修、2正式轮、归档后0临时预演目录。

[独立ZIP/XML](../../samples/phase31/independent-check.json)和[浏览器下载核对](../../samples/phase31/browser-independent.json)不导入新检查器、判定器或掩码：作者手写pPr属性目标，整棵XML白名单比较、逐run子树、文字空白/顺序、表格、媒体、关系、编号、分节和其他未选成员核对。浏览器部分/最终下载实际通过，最终与离线复现逐字节一致。独立正确对照由作者脚本生成，其最终页图与修正版一致。

原阶段28同一输入/选择在R33后，未选28pt首行缩进现在是可判定的R07问题（12pt正文应等效24pt），不再仅因上标返回review。保留原输入及更强的缩进未改断言后更新该旧测试预期；没有删除复杂或未确认测试。[浏览器两步下载证明](../../samples/phase31/plan-independent.json)确认两轮文件与原合法路径同字节，未自动追加R07。

## 自动验收与干净复现

原1118场景无回归；新增27项（含多个子场景）覆盖精确用途/区间、v1/v2、跨run/重复/部分上标、空白/空run、字符/点值/悬挂、混字号/未知/缩放、行距类型、网格、段距单位/自动/上下文、直接/字符样式继承、复杂结构、预演、两步、恢复、外改和双会话、完整报告。首次旧1118项151.303秒通过；最终本地1145项162.884秒、干净目录1145项163.195秒通过。

```bash
python scripts/check_repository.py
python -m unittest discover -s tests
python scripts/reproduce_citation_paragraph_demo.py --output /tmp/paperfit-phase31-new
python scripts/verify_citation_paragraph_output.py samples/phase31/errors.docx /tmp/paperfit-phase31-new/fixed.docx
python scripts/verify_citation_paragraph_output.py samples/phase31/errors.docx /tmp/paperfit-phase31-new/step-1.docx --only-line
python scripts/measure_citation_paragraphs.py --output /tmp/paperfit-phase31-measure-new.json
```

[干净目录记录](../../samples/phase31/clean-reproduction.json)：只复制Git交付源码及合成夹具，逐文件哈希核对；没有work/outputs/.env/.venv或学校PDF，移除API配置并指向不存在的渲染配置。完整测试、离线复现、独立输出核对及仓库链接审计分别执行。远端Ubuntu CI在正常推送后按本次SHA核对，不借用d08d16b结果。

## 真实浏览器及状态

[实际浏览器记录](../../samples/phase31/browser-acceptance.json)。Chrome/本地Streamlit，通过真实项目导入控件载入合成范围草稿，核对摘要、统一确认检查。查看原有上标及精确段落证据；问题中心仅筛段3/R06，明确选择1项、实际预演、核对采用、下载；明确下一轮选择其余13项，实际预演采用、下载DOCX/ZIP并独立核对。

独立浏览器会话初始无第一会话文件/结果，导入阶段28合成项目的10项明确选择意图，恢复时重新检查，完成普通文字→R33实际两步预演和采用、下载两步文件、明确从最终副本继续。新检查保留未选R07问题；引文复杂边界仍只读。两个会话分别拥有不同文件与历史。

第一会话保存真实网页项目包后，仅重启已核对命令/cwd属于本项目的8501服务，重新通过网页导入/核对恢复，当前第2轮、R13配置、v2用途/部分范围和代码排除保留；报告来自本次重新检查，0问题/37待复核，无旧预演授权或有效页图。随后将段3引文改为待确认草稿，旧确认/当前下载失效；重新确认检查后该段回到保护路径。

截图：[精确范围证据](../../samples/phase31/screenshots/paragraph-evidence.png)、[单属性预演](../../samples/phase31/screenshots/line-rehearsal.png)、[R33后段落证据](../../samples/phase31/screenshots/plan-final-evidence.png)、[重启恢复](../../samples/phase31/screenshots/restored-evidence.png)、[范围变化](../../samples/phase31/screenshots/range-invalidated.png)。部分自动操作因重运行、隐藏复选框或仍打开的下拉菜单超时；读取新UI后完成，失败尝试没有计作成功耗时或以私有状态注入绕过。

## 真实页面和Word

[完整视觉记录](../../samples/phase31/visual-record.json)：bundled LibreOfficeDev26.8/Poppler，原稿、独立对照、最终副本各2页，全部6页目视。引文持续上标，行距、首行缩进、段距和对齐变化可见；未确认上标、区间外上标、代码空白、表格及图片保留，未发现新增裁切、丢字或拉伸。字体宋体/Times New Roman/Calibri在此环境有匹配，主题/全字形审计仍有边界，不保证不同环境分页一致。渲染前后原DOCX哈希不变。

Word16.80本轮实际打开最终fixed.docx（与浏览器最终同字节），查看关键上标和段落及第二页代码、表格、图片，无修复提示，关闭未保存、哈希不变；[第一页](../../samples/phase31/screenshots/word-page-1.png)/[第二页](../../samples/phase31/screenshots/word-page-2.png)。只读观察未改全局设置。原生键盘/滚动若干尝试未导航成功，最后用实际滚动查看末页；不将尝试冒充查看。两步计划输出与阶段28已验收文件逐字节一致，本轮复用该文件既有视觉记录，未另宣称新增Word查看。

## 基本成本与剩余限制

[3次原始测量](../../samples/phase31/measurements.json)：macOS/Python3.14.5，小样本证据构建中位8.27ms、完整检查31.42ms；增加400个合成正文段（总420段/407个确认引文组）证据435ms、完整检查1.048s。是本地函数成本，不是浏览器等待；没有可比旧算法，不宣称提速百分比。0新增AI、0自动渲染，页图是主动验收。

仅已确认正文的五种属性；不扩展到任意上下标、公式、链接或其他章节。行内格式仍保护、未配置未检查、未知字号/复杂继承/编号/网格继续如实待复核。XML声明通过不证明像素行高、实际分页、目录页码、引文真实性或全文合格。commit、push及对应CI在交付后按本次SHA核对。

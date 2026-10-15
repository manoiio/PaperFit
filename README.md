# 论文有格课程 Demo 第一至二十四阶段

当前新增：**统一规范工作台**组合主模板v6、封面/页眉页脚、目录、脚注/尾注配置。一次明确点击只发一次DeepSeek请求，按模块核对草稿、决定未提及字段、查看整体差异后原子应用；完整规则包一次导出/导入，跨文档复用，论文对象范围仍分别确认。873项旧验收无回归，最终914项通过。详见[第二十四阶段验收](outputs/phase24/验收记录.md)、[规则包说明](outputs/phase24/规则包结构说明.md)。

本地CLI及Streamlit网页支持：选择DOCX → 确认对象范围 → 检查 → 选择安全修改 → 另存副本 → 落盘复查 → 多轮处理、下载与可选真实页面预览。基础R01–R07、正文及标题题注R01–R12、单文档扩展及可选R23–R43保持原含义；分页L01–L05、宽度适配与格式检查分别授权、分别报告。没有新增规则编号。

固定模板为**华工本科工理类2015演示规则**，仅依据项目所附材料，不宣称现行通用校规；自定义模板使用用户名称。v2–v6旧模板、独立补充JSON和旧CLI保留兼容。未配置、未确认、待复核和已通过分别说明；格式通过不等于页码准确或全文排版合格。

## 统一规范工作台操作

1. 选择“单文档扩展检查”。在工作台导入**格式要求**TXT/DOCX或输入公开文字；本机预览后明确选择摘录，最多12000字符，核对来源并确认。上传规范与待检查论文分开。
2. 点击“一次解析全部规范”。仅发送已确认规范及字段说明；不会发送论文、分类、封面个人信息或注释。失败不自动重试；如需再请求须明确操作。
3. 按模块查看提取、冲突和未支持要求。未提及字段可明确保留当前、不检查或手动指定；批量策略先展示影响字段并确认。编辑不改变生效规则。
4. 核对最终完整配置及差异，再“一次确认并应用全部规则”。任一模块或存储校验失败，原生效配置保持。人工修改标为用户确认值，保留旧值不会冒充本次AI提取。
5. 选择论文并核对分类、表格、封面/节用途、目录及注释范围，使用原检查/选择修正/读回复查流程。应用规则不会确认对象、声明范围完整、选择修正或执行辅助操作。
6. “准备完整规则包”后下载JSON，下次导入为待确认草稿、核对差异后应用，不调用AI。它不含论文、对象编号、范围或历史；**项目包**包含论文并用于继续工作，**结果包**用于取走本轮成果。

工作台是单文档主要规则入口；旧高级入口共用生效状态。已启用工作台时，补充对象区域显示当前规则并保留范围确认，避免重复维护两套配置。恢复默认会清理旧报告、选择和下载，保留人工分类草稿及材料排除，仍需重新确认。

本轮实际公开规范解析3次明确请求：2次被本地校验拒绝、1次成功（42字段）。封面22pt人工改为24pt并实际落盘；跨会话规则包重载0新增API。最终合成文件仍保留2项只读内容问题和24条待复核，没有把未检查对象算通过。原稿/最终各2页真实渲染；Word16.80本轮实际查看最终副本，未见修复提示、未保存，未测试所有链接跳转。

[演示规范](samples/phase24/unified-spec.txt) · [完整规则包](work/phase24/deliverables/final-rule-bundle.json) · [修正版](work/phase24/deliverables/final-fixed.docx) · [独立复查](work/phase24/deliverables/final-independent-recheck.md) · [结果包](work/phase24/deliverables/final-result.zip) · [文件索引](outputs/phase24/文件索引.md)。

## 安装与运行

在项目根目录使用独立虚拟环境。已在当前 Mac 的 Python 3.14.5 环境执行验收；建议 Python 3.11 及以上（其他版本未在本次实际验收）。运行时只需requirements.txt；CLI无需服务，网页使用本机Streamlit。无需Windows、Office或COM。固定模板无需外部API；可选规范解析调用DeepSeek。第六阶段提供可选本机bundled预览；渲染运行时缺失时，检查、修正及下载仍可使用。

```bash
cd '/Volumes/XD20/Developer/论文有格'
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

下面命令使用 `work/my-demo` 新目录。所有输出拒绝覆盖；重复演示请更换目录名，不要覆盖原稿或已有报告。

```bash
.venv/bin/python cli.py inspect samples/errors.docx --report work/my-demo/paragraphs.json

.venv/bin/python cli.py check samples/errors.docx \
  --body-manifest samples/errors.body.json \
  --report work/my-demo/check.json

.venv/bin/python cli.py fix samples/errors.docx \
  --body-manifest samples/errors.body.json \
  --select R01,R02,R03,R04,R05,R06,R07 \
  --output work/my-demo/fixed.docx \
  --report work/my-demo/changes.json \
  --recheck-report work/my-demo/recheck.json

.venv/bin/python cli.py check work/my-demo/fixed.docx \
  --body-manifest work/my-demo/fixed.body.json \
  --report work/my-demo/independent-recheck.json
```

检查错误样本的正常退出码是 **1**，不要把它当程序崩溃。退出码0表示覆盖内无问题且无待复核；1表示有问题；2表示无确定问题但有待复核；3表示输入或执行错误。输出结论始终限于覆盖范围。

可以只选择部分规则，例如 `--select R02,R05`；也可用报告中的 `key` 精确选一个问题：`--select-key 'R05:paragraph=4:run=2'`。二者取并集，仅修正状态为 problem 且 fixable 的记录。选择了待复核项仍不强制修正，修改报告列出跳过的 key。

## 正文必须明确确认

`inspect` 返回主文档 body 直属 `w:p` 清单，编号从1开始，包含空段、图片段和分节段；不包含表格、页眉页脚、文本框中的段落。样本正文为 `[4,5,6,11,14,15]`，其余段落和表格格式不套正文规则。

CLI 支持 `--body-ranges 4-6,11,14-15`；这表示操作者已人工确认该范围。更稳妥的方式是保存正文清单：

```json
{
  "input_sha256": "inspect报告中的实际SHA256",
  "body_paragraphs": [4, 5, 6, 11, 14, 15],
  "confirmation": "人工确认的正文段落"
}
```

输入哈希不匹配、重复编号、越界编号均拒绝处理。修正后自动生成新的 `fixed.body.json`，绑定修正版哈希并沿用已核对未变化的段落结构。不得把原稿清单强行复用于另一文档。API 使用数字列表时，确认与文件绑定由调用方负责。

## 检查与修正边界

- R01检查每个常见分节的210×297mm纸张；R02检查各节四边距25mm，误差容许0.03mm（DOCX单位取整）。缺失、无法确定的页面属性待复核。
- R03/R04分别读取 eastAsia、ascii/hAnsi 字体槽位。支持 docDefaults、常见段落/字符样式、basedOn及直接格式；第八阶段增加可唯一确定的major/minor主题映射。缺失、冲突、复杂文字槽位及未支持hint仍待复核，具体范围见第八阶段说明。
- R05检查全部普通文字run的12pt字号；R06区分1.5倍、固定值、最小值行距。
- R07支持 firstLineChars=200，以及统一字号、无文字宽度调整的中文段落中的等效点值（12pt字体对应24pt，不是48pt）。字符和点值不一致或直接悬挂属性会报问题；修正删除直接悬挂属性并显式写字符缩进。继承悬挂、混合字号点值缩进、编号缩进等不能可靠修正，待复核。
- 链接、公式、域、修订、内容控件等复杂段落整段跳过；上/下角标、图片、基线偏移、隐藏或复杂文字等特殊run跳过，同时阻止该段的行距和缩进自动修正。普通run可以单独检查；样式缺失、循环及重复相关属性待复核。
- 仅支持常见 Transitional DOCX，输入上限10MB、ZIP解压总量100MB；损坏、宏文档、签名修正、覆盖原稿及已有输出均拒绝。此限制用于课程演示，不是生产级文件安全沙箱。
- 已实现限定的确定性分类建议及人工确认后的对象检查；单文档模式另覆盖摘要、关键词和参考文献普通格式。未实现全自动识别、页码定位、目录/域重算、编号重写、交叉引用、参考文献著录重写、全文语义分析、数据库或远程部署。最新渲染及Word查看的具体范围见各阶段验收记录；第十五阶段默认合成原稿/修正版已实际用Word打开，本机渲染命中安装的宋体/黑体/TNR，不把历史替代字体或其他文件的观察当作当前验收。

旧范围只修改 `word/document.xml` 中选定位置的格式、页面或明确选择的布局属性；第十七阶段明确选择的安全页眉页脚普通文字可另改已有故事部件，其余部件仍保持字节，故事格式采用独立白名单验证；关键词标签局部格式可安全分裂普通run并保持字符及内容不变，不用 `paragraph.text` 重写，不重建DOCX。未选ZIP成员未压缩字节保持一致。每次修正先检查，再另存、重新读取、核对所选问题及完整性。失败时删除本次生成的副本，不生成“成功”结果。

完整性验证覆盖主文档除允许格式属性外的XML树和其他包成员字节；独立验收还比较正文和表格文字、图片XML与媒体字节、编号文件及分节属性。复杂公式、链接、修订等的显示行为仍待人工复核，不因XML未改变就宣称其排版已验证。

## 已生成的交付文件

- `samples/errors.docx`：脱敏合成错误输入，15个顶层段落、2节、1张图、1个简单表格。
- `samples/correct.docx`：相同内容的正确对照，覆盖内0问题、0待复核。
- `samples/expected_errors.json`：独立手工清单，7条规则共11处错误，位置及要求值逐项验收。
- `work/phase1/final/fixed.docx`：程序生成修正版，11项修改均读回复查通过。
- `work/phase1/final/check.json` / `.md`：输入检查报告。
- `work/phase1/final/changes.json` / `.md`：修改前后值、复查结果、保留验证与跳过项。
- `work/phase1/final/recheck.json` / `.md`：保存后复查报告。
- `work/phase1/acceptance.log`：验收运行记录；验收细目见 `tests/test_acceptance.py`。

已有组员脚本和样张未改动；合成样本不使用真实论文，不向外部服务上传文档。`samples/build_samples.py`用于追溯样本构造，已有样本时拒绝覆盖，日常演示直接使用现有样本。

## CLI与网页共用的引擎函数

```python
from core import inspect_document, check_document, fix_document, verify_document

inventory = inspect_document(input_path)  # 清单、原稿哈希，供人工确认
before = check_document(input_path, body_manifest_path)  # 或人工确认的编号列表
result = fix_document(
    input_path, new_output_path, body_manifest_path,
    selected_rules=["R02", "R05"], selected_keys=[]
)
after = result["after"]  # 已从保存的新文件读回，不是内存推测
again = verify_document(new_output_path, result["output_body_manifest"])
```

函数均返回可JSON序列化字典，抛出 `core.package.DemoError` 表示不支持或不安全。网页只需负责文件暂存、人工范围确认、选项与报告展示；输出路径必须唯一，当前引擎按单文档同步处理。`core.report.markdown()`可复用为可读报告。第一阶段接口保持兼容；第二阶段网页已直接调用这些函数，未修改core。

实现参考的主来源为项目学校PDF；OOXML细节核对了 [Microsoft字体槽位说明](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.runfonts?view=openxml-3.0.1)、[缩进属性继承说明](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.indentation?view=openxml-3.0.1)和[倍数行距单位说明](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.spacingbetweenlines.line?view=openxml-3.0.1)。未复制或集成GitHub项目。

## 第二阶段本地网页

已在当前Mac实际启动，地址为 **http://127.0.0.1:8501**。仅监听本机回环地址。启动命令（服务运行期间无需重复启动）：

```bash
cd '/Volumes/XD20/Developer/论文有格'
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py \
  --server.address 127.0.0.1 \
  --server.port 8501
```

若8501被其他服务占用，不停止其他服务；把命令端口换为8502，并访问对应地址。终端Ctrl+C停止本次服务。`.streamlit/config.toml`设置本机监听、10MB上传限制、白底深蓝主题，并关闭Streamlit使用统计。网页处理不调用外部服务；浏览器向本机服务传输上传文件，不能把它描述为浏览器从不发送文件。

### 操作流程

1. 点击“使用错误样本”或“使用正确对照”；也可上传不超过10MB的DOCX。上传入口不会按文件名或相同字节套用内置清单。
2. 核对已选正文的编号、文本、样式及特殊结构提示。在“选择或调整正文段落”中逐项勾选。编号是顶层段落位置，不是页码；表格内段落不在清单中。
3. 点击“确认正文范围”，再点击“开始检查”。未选正文时不执行检查。内置样本预填六个段落也必须确认。
4. 默认看问题记录；待复核与覆盖提示始终显示，符合和不适用记录折叠显示。页面不宣称全文合格。
5. 点击“选择全部可修正问题”，或在“逐项选择修正”中选具体问题，再点击“生成修正版”。默认没有选项，空选择禁用按钮；待复核项不能选。部分修正保留其他问题，结果不显示为失败。
6. 查看修改数量、剩余问题/待复核、完整性结果及保存后复查。可展开查看逐项修改前后值。下载修正版、原稿、修改记录Markdown和复查Markdown；高级详情另提供完整JSON及绑定修正版哈希的正文清单。

两分钟录屏的准备顺序可用：错误样本 → 核对六段 → 确认 → 检查11问题 → 全选 → 生成 → 看0问题/0待复核 → 下载。这里只提供操作顺序，本阶段没有录制最终视频。

### 状态与文件保护

网页仅通过`core`公开函数处理文档，不执行CLI子进程。`web/session.py`管理单个会话的任务、确认、报告、选择及结果；`web/presentation.py`只转换显示文字，不做规则判断。每次输入复制为`work/web/<随机任务ID>/input.docx`，不把上传文件名拼接到磁盘路径。

所有修正仍从本次原稿读取，输出使用新的随机名称并保留引擎拒绝覆盖的保护。改变输入、正文范围或固定规则文件的签名会撤销旧确认、报告与结果。改变修正选项后也会使旧修正版下载失效。相同选项已生成后禁用生成按钮，重复触发由请求绑定再挡一次；下载使用已生成字节与`on_click="ignore"`，不运行修正。

“重新开始”只清理当前会话持有的任务目录，不扫描或删除其他work内容。输入切换同样只清理自己的旧任务。网页刷新可能建立新会话；断开会话的目录不做后台定时清理，仍留在work/web中，后续需要时由操作者核对后清理。会话隔离已验收，这里未实现账号、鉴权或生产级上传系统。

### 第二阶段实际验收

`tests/test_web.py`新增19项必要自动验收，连同第一阶段28项共 **47项全部通过**。覆盖输入/范围/规则失效、非法选择过滤、错误与成功状态清除、重复生成、下载绑定、原稿和修正版复查、当前任务清理与独立会话；其中5项使用Streamlit AppTest操作真实控件与重运行。

真实Chrome浏览器已完成以下交互（不是静态截图替代）：

| 验收 | 结果 |
| --- | --- |
| 内置错误样本，人工确认六段 | 7条规则，11个问题，0待复核 |
| 全选11问题修正 | 11项保存后复查通过；剩余0问题、0待复核 |
| 单选段4后半段字号 | 只改1项；剩余10问题；下载文件独立复查一致 |
| 正确对照 | 覆盖内0问题、0待复核；不提供无意义的生成操作 |
| 输入或正文范围变化 | 旧确认、报告、修正版下载失效 |
| 双击生成、重复下载、重运行 | 无额外修正版；下载字节一致；没有覆盖文件 |
| 损坏DOCX与宏类型伪装DOCX | 显示提示，不产生成功结果 |
| 主题字体与上角标测试文件 | 0确定问题、4待复核；规则记录和coverage_notes实际可见 |
| 浏览器下载的原稿/修正版 | 原稿与输入字节一致；修正版用core独立复查为0问题、0待复核 |
| 两个独立浏览器Context | 各自输入与报告隔离；重置一个不影响另一个 |

验收记录在`work/phase2/acceptance.log`与`work/phase2/browser/`。真实网页区域截图：

- `work/phase2/screenshots/01-问题报告.png`
- `work/phase2/screenshots/02-修正结果.png`
- `work/phase2/screenshots/03-复查结果.png`

依然只有R01–R07与明确确认的正文范围；复杂对象按引擎返回待复核，未做自动识别。未在Microsoft Word实际打开，未录最终视频；未做DeepSeek、VPS、账号、数据库、目录页码或新标题规则。第一阶段core、组员资料与样张未改动。这是第二阶段的历史验收记录；第三阶段见下文。

网页状态及下载实现核对了[Streamlit会话状态文档](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)与[下载按钮文档](https://docs.streamlit.io/develop/api-reference/widgets/st.download_button)。

## 第三阶段：短规范与用户确认规则

当前已完成限定范围内的真实API及网页闭环验收。默认规则JSON没有改动，旧CLI参数与公开函数调用保持兼容。检查/修正/复查使用同一份确认配置，并记录名称、版本、SHA256和字段来源。配置仅扩展R05、R06；其他五条规则保持默认学校演示值。

### 本机配置

本项目`.env`已由用户在本机填写，文件权限为0600，已加入`.gitignore`。不要上传或分享该文件。其他机器可从示例复制后在本机编辑；示例不包含真实密钥：

```bash
cd '/Volumes/XD20/Developer/论文有格'
# 仅在.env不存在时复制，不覆盖已有配置
[ -e .env ] || cp .env.example .env
chmod 600 .env
```

需要三个变量：`DEEPSEEK_API_KEY`填本机密钥，`DEEPSEEK_BASE_URL=https://api.deepseek.com`，`DEEPSEEK_MODEL=deepseek-flash`。环境变量优先于`.env`，修改本地文件后下一次显式解析会重新读取。当前原型只接受官方HTTPS根地址或`/v1`；模型允许`deepseek-flash`、`deepseek-v4-pro`，实际验收使用前者。接口与模型于2026-10-13核对[官方Chat Completions文档](https://api-docs.deepseek.com/api/create-chat-completion/)及[JSON Output文档](https://api-docs.deepseek.com/guides/json_mode/)，不保证将来模型目录不变。

启动命令与第二阶段相同，当前服务地址为[本地网页](http://127.0.0.1:8501)。无密钥、余额不足、超时、空响应、JSON错误或本地校验失败时显示提示，固定模板仍可使用。只有点击“解析要求”才发送一次请求，超时约30秒，不自动重试；成功草稿重运行不再次请求。

### 操作步骤

1. 使用正确对照样本（或先载入自己的脱敏DOCX），展开“自定义格式要求”。输入公开短格式要求，最多2000字符。不要粘贴论文正文、作者信息或路径。
2. 示例A为“正文小四号，1.5倍行距”；示例B为“正文四号，2倍行距”。填入示例本身不调用API。点击“解析要求”，查看字段、数值、原文依据、未支持提示及真实调用标记。
3. 核对并编辑草稿。R05仅接受8–24pt、0.5pt步长；R06仅接受1、1.25、1.5、2倍。未提及字段保持空值，必须明确选“沿用默认值”或“手动指定”。标题字号、固定磅值及最小值行距不执行；冲突或含糊要求不自动应用。上述范围是课程原型边界，不是学校通用规范。
4. 查看完整七条规则预览，再点击“确认并应用”。来源分别标记为“AI提取后用户确认”“用户确认值”“沿用默认值”；用户编辑后的值不再声称原文精确支持，也不伪造学校PDF出处。
5. 重新确认正文范围，开始检查，选择问题，生成副本。保存后的复查显示实际读到的字号和倍数行距；下载自定义规则、修正版、修改记录及复查报告。

草稿与当前应用配置分开。改变规范文本会清除旧AI草稿，但在确认应用新配置前，当前文档仍使用原配置。应用新配置或切回默认，立即清除旧正文确认、报告、修正选项及下载；输入和正文选择可保留。不会把上一次修正版作为下一次原稿。不同会话不共享配置、规范文本、结果或下载。

本地校验严格拒绝未知字段、布尔值、非有限数字、伪造原文、代码、路径或工具指令。校验采用保守的中文正文范围与数值匹配，复杂措辞可能拒绝或要求手动确认，不能作为任意学校规范的通用解析器。只有规范文本和固定JSON提取提示发送到DeepSeek；文档处理仍在Mac完成，不能称整个系统完全离线。

### 共用接口与独立复查

`load_rules()`继续严格读取固定学校演示规则。新增显式入口`load_custom_rules(path)`；原有引擎函数追加可选关键字`custom_rules_path=path`，不复制检查器。`rules_path`与`custom_rules_path`不能同时使用。

```python
from core import check_document, fix_document, verify_document
before = check_document(input_path, body_manifest, custom_rules_path=confirmed_config)
result = fix_document(input_path, unique_output_path, body_manifest,
                      selected_keys=selected_keys, custom_rules_path=confirmed_config)
after = result['after']  # 同一配置，从落盘文件读回
```

CLI可显式使用已确认配置：

```bash
.venv/bin/python cli.py check work/phase3/final/fixed-B.docx \
  --body-manifest work/phase3/final/fixed-B.body.json \
  --custom-rules work/phase3/final/user-confirmed-rules.json \
  --report work/my-custom-check/recheck.json
```

此B样本的退出码1表示剩余R07问题，不是程序失败。请使用新的报告路径。

### 第三阶段实际验收与文件

自动验收使用模拟API，未消费余额：原47项加21项，共**68项全部通过**。新增验收覆盖空字段、标题/固定行距排除、非法值/结构/原文拒绝、来源准确、A/B配置的真实引擎行为、落盘复查、内容保留、状态失效、失败降级、单次请求载荷、双会话隔离及两个Streamlit AppTest交互。

真实API验收单独完成**一次**：2026-10-13 23:53:49（UTC+8），模型`deepseek-flash`，公开输入“正文四号，2倍行距”，JSON返回14pt及2倍，对应原文为“正文四号”“2倍行距”。耗时记录约1.088秒；本地校验通过。记录没有密钥、论文内容或文件路径。A仅在模拟API测试及网页明确默认继承方式下验收，没有真实API A调用声明。

真实Chrome完成B解析、字号编辑13.5再改回14、确认、重新确认六段正文、检查14问题、选择14项、修正、下载及保存后复查；14项所选修改全部通过。原稿与对照样本字节一致，下载文件再经core及独立CLI复查，实际R05普通文字均14pt、R06正文均2倍。另验证两个独立浏览器Context的配置隔离、文本变化清除草稿、确认新配置使旧报告/下载失效、默认恢复与A默认继承检查0问题。

**明确的剩余问题：**对照样本第11段原来继承24pt点值缩进，在12pt时等效两字符；改成14pt后不再等效。保留未选R07的属性，因此B复查剩余1个R07问题、0待复核；不能宣称全文合格或B全部规则通过。其他五条规则及内容、图片、表格、编号、分节继续受原保护。后续录屏可说明该边界，再由用户另选R07修正；如准备字符缩进的演示派生样本，应另存并明确标注，不改现有样张。

| 交付 | 本地位置 |
| --- | --- |
| 真实API脱敏记录 | `work/phase3/final/real-api-record.json` |
| 浏览器确认的B配置（R05用户编辑，R06真实AI提取） | `work/phase3/final/user-confirmed-rules.json` |
| 实际下载的原稿与B修正版 | `work/phase3/final/original.docx` / `fixed-B.docx` |
| 修改记录及落盘复查 | `work/phase3/final/changes.md` / `recheck.md` / `result.json` |
| 独立复查与正文清单 | `work/phase3/final/cli-independent-recheck.json` / `.md` / `fixed-B.body.json` |
| A的明确默认继承配置 | `work/phase3/final/rules-A-default-inherited.json` |
| 自动测试及浏览器脚本/记录 | `work/phase3/acceptance.log` / `work/phase3/browser/` |
| 规则确认界面真实截图 | `work/phase3/screenshots/01-规则确认.png` |
| B新规则落盘复查真实截图 | `work/phase3/screenshots/02-新规则复查.png` |

确认界面截图为浏览器手动填写B的完整草稿预览，两个字段明确标为用户确认值；未伪装新AI调用。真实AI与用户编辑混合来源的已应用B配置及完整浏览器流程记录另附。复查截图来自上述真实API流程生成文件。API故障的多种返回状态使用模拟自动验收，未人为消耗余额制造真实付费故障。

没有在Microsoft Word打开本阶段修正版，也没有录最终视频、部署、发送消息或改原始组员资料。建议最终录屏保留固定模板主流程，再用简短B规范说明“AI提出草稿，用户确认，确定性引擎修正并读回”；出现剩余R07应如实解释。以上为第三阶段历史验收；第四阶段产品扩展见下文。

## 第四阶段：分类建议、标题题注与多轮修正

默认仍为“基础检查”，R01–R07与旧CLI语义不变，原错误样本仍为11问题。选择“正文及标题题注检查”后才启用R01–R12。没有增加依赖、外部后端或文档上传服务，启动仍是：

```bash
cd '/Volumes/XD20/Developer/论文有格'
.venv/bin/python -m streamlit run app.py \
  --server.address 127.0.0.1 --server.port 8501
```

当前[本地网页](http://127.0.0.1:8501)仍在运行。测试命令不变：`.venv/bin/python -m unittest discover -s tests -v`。

### 分类与扩展操作

1. 先选检查模式，再选文件。扩展模式可一键载入“扩展错误样本”或“扩展正确对照”；上传文件同样获得确定性建议，不使用样本位置硬编码，也不发送论文内容给DeepSeek。
2. 页面提出正文、三级标题、图题、表题、其他、待确认等建议。依据已有Heading/大纲、编号和短文本、章节标记、相邻图表及叙述段，显示理由与歧义，不显示概率置信度。目录、摘要、参考文献、封面、图片段及表格内段落不会批量当正文。
3. 默认表只显示标题、题注、歧义及调整项；打开“查看全部段落”可核对正文和排除范围。直接编辑“核对类型”，或展开“按编号快速调整分类”。确认整份当前分类前不能检查和修正；仍为待确认的段落跳过并列入覆盖提示。
4. 点击“确认分类并应用范围”，再检查。分类、输入哈希、模式与配置共同绑定。改分类、文件、模式或确认配置后，旧确认、报告、选择和当前下载失效。基础模式保留原逐项人工正文选择。
5. 报告分别显示启用规则数、实际适用规则数、问题数、待复核数与已确认正文数。没有某类标题/题注时相应规则不适用，不把缺少题注报成错误。题注只检查字体字号，不套正文缩进或行距。

### 新规则及保护

R08–R10学校原文已重新核对PDF物理页17–20，值取18页：中文黑体，一级18pt居中，二级15pt居左，三级14pt居左，均单倍行距。标题题序阿拉伯数字采用Times New Roman；演示将西文/数字槽位映射到该字体，来源解释保留在报告中。没有添加加粗、颜色、段前段后、标题缩进、题注位置或编号规则。R12为宋体10.5pt，普通中文及西文/数字槽位按题注字体检查。

R08–R10按字体槽位、字号、对齐、行距分别形成可选择的问题，显示具体不符合属性，覆盖后半段run及常见样式继承。R11是产品结构规则，要求已确认标题引用现有可验证的Heading1–3及对应大纲0–2，不冒充学校要求英文样式名。

添加Heading时先生成显式保留补丁，冻结原有效字体、字号、颜色、加粗及常见间距等可能变化的属性；先证明有效格式一致，再执行用户明确选择的其他标题属性修改。共享`styles.xml`始终不修改。报告与修改记录包含保留说明及补丁，R11单选也有独立验收。缺少可验证的内置Heading、未知属性依赖（例如无法保持的制表位/缩进变化）、复杂样式切换型属性或特殊结构时列为待复核，禁止强行套样式。第八阶段自动编号标题的实际样式/大纲可读时正常检查；确定不符报告为不可自动修正的问题，不能切换样式影响编号。当前内置Heading识别支持规范ID `Heading1`、`Heading2`、`Heading3`及常见英文/中文名称；其他本地化ID需人工复核。

上角标等特殊run仍跳过；混有特殊run的段落不改段落格式或标题样式。公式、链接、域、修订等复杂段落整段保护。正文、标题文字、编号、题注内容、图片、表格内容、分节及其他包成员不重建。不会重算目录、引用或域。

默认`rules/scut_2015_demo.json`保持原字节；新增`rules/scut_2015_extended.json`只保存固定R08–R12。扩展规则配置哈希由正文配置哈希与固定扩展文件哈希组合，报告同时记录两者。自定义正文R05/R06与固定标题题注规则可共存，逐项来源仍区分学校、产品、AI、用户编辑或默认继承。此处是第四阶段记录；当前第九阶段支持版本3对象模板，见文末。

### 修改依赖与第二轮

对能预测的R05字号/点值缩进关系，选择修正后、执行前会提示“可能影响首行缩进”。第一轮保存后用同一规则读回，报告区分已解决、原有剩余、新出现的问题。新增R07会说明：“字号改为14pt后，24pt缩进不再等效两字符（应为28pt）；本轮未选择该缩进。”未选缩进不会暗改。

点击“以本轮修正版开始下一轮”才切换输入。页面明确显示当前是原稿还是第几轮副本；沿用结构保留已验证、绑定新文件哈希的清单，并重新读回检查。选择剩余问题后再生成独立文件，各轮DOCX、JSON、修改及复查Markdown留在当前任务目录。原有问题若转为待复核，不算已解决。原稿下载始终返回最初原稿，历史轮次下载单独标记；这不是逐项撤销栈。未点击切换时，改变选择仍从当前显示的输入生成另一份副本。

历史下载仅在同一确认范围、模式与配置下展示；切换后立即隐藏。输入切换/重新开始只清理自己的当前任务目录；要保留每轮文件，请先下载。不同会话独立，未实现账号或长期存储。

### 共用接口与CLI

```python
from core import suggest_paragraph_types, check_document, fix_document
suggestions = suggest_paragraph_types(input_path)  # confirmed=False，不可直接执行
manifest = {
    "input_sha256": suggestions["input_sha256"],
    "paragraph_types": user_confirmed_types,  # 字符串段落编号映射到type，覆盖所有顶层段落
    "confirmed": True,
    "confirmation": "人工核对"
}
report = check_document(input_path, mode="extended", classification_manifest=manifest)
result = fix_document(input_path, unique_output_path, None,
    selected_keys=selected_keys, mode="extended", classification_manifest=manifest)
# 自定义正文时同时传 custom_rules_path=confirmed_config，仍只允许R05/R06。
next_manifest = result["output_classification_manifest"]  # 绑定落盘副本哈希
```

类型值：`body`、`heading1`、`heading2`、`heading3`、`figure_caption`、`table_caption`、`other`、`pending`。清单必须完整且明确确认，哈希错配、越界、未知类型均拒绝。基础调用仍用原`body`清单；不能把原稿清单强行复用到副本。

CLI显式支持扩展模式，新报告路径请自行更换以避免覆盖：

```bash
.venv/bin/python cli.py classify samples/extended-errors.docx \
  --report work/my-extended-demo/suggestions.json

.venv/bin/python cli.py check samples/extended-errors.docx \
  --mode extended --classification-manifest samples/extended-errors.types.json \
  --report work/my-extended-demo/check.json

.venv/bin/python cli.py fix samples/extended-errors.docx \
  --mode extended --classification-manifest samples/extended-errors.types.json \
  --select R08,R09,R10,R11,R12 --output work/my-extended-demo/fixed.docx \
  --report work/my-extended-demo/changes.json \
  --recheck-report work/my-extended-demo/recheck.json

.venv/bin/python cli.py check work/my-extended-demo/fixed.docx \
  --mode extended --classification-manifest work/my-extended-demo/fixed.types.json \
  --report work/my-extended-demo/independent.json
```

`classify`输出只有建议，不能直接当确认清单使用；普通用户在网页核对。检查错误样本退出1表示检出问题；修正与独立复查退出0表示覆盖内无问题、无待复核。

### 第四阶段实际验收

原68项全部通过，新增27项，共**95项自动验收通过**，其中新增3项Streamlit AppTest交互。涵盖分类正常及误识别排除、样式冲突、目录中有效Heading仍排除、未确认/错哈希/非法分类保护、独立错误清单、R08–R12正确和错误、后半run与字符样式继承、R11有效格式与主题继承保留、缺失/危险依赖阻止、题注范围、无题注不适用、自定义共存、新R07解释、两轮哈希、重复执行/覆盖阻止、状态失效及双会话。

真实Chrome先通过上传入口载入合成DOCX，确认分类后检出9问题，证明不是只走内置入口。随后完成两条独立流程：扩展错误样本确认分类，检出9问题，全选9项后读回0问题/0待复核；调整分类使报告/下载失效，切回基础同样失效。另用扩展正确对照沿用历史真实AI B结果，检查10个R05/R06问题，预先提示缩进依赖；第一轮10项通过但新增R07，明确切换到第一轮副本，第二轮只改R07，读回0问题/0待复核。原稿、第一轮重新下载字节一致，两轮结果均可用现有CLI独立复查；两个浏览器会话及另一个会话的重置不互相影响。

本阶段**没有新真实API调用**。规则确认截图来自第三阶段真实DeepSeek记录的显式历史载入，两个字段均为AI提取，界面显示原时间、模型和“本次请求0次”，没有把手动草稿或模拟结果冒充AI。原记录仍为`work/phase3/final/real-api-record.json`。

| 交付 | 本地位置 |
| --- | --- |
| 扩展正确/错误样本 | `samples/extended-correct.docx` / `samples/extended-errors.docx` |
| 人工核对分类与独立错误清单 | `samples/extended-correct.types.json` / `extended-errors.types.json` / `extended-expected-errors.json` |
| 浏览器下载扩展修正版 | `work/phase4/final/extended-fixed.docx` |
| 扩展检查/修改/复查 | `work/phase4/final/extended-check.md` / `extended-changes.md` / `extended-recheck.md` / `extended-result.json` |
| R11单选保留证明 | `work/phase4/final/r11-only.docx` / `r11-only-result.json` / `.md` |
| 历史AI确认配置 | `work/phase4/final/custom-rules.json` |
| 自定义第一、二轮副本 | `work/phase4/final/custom-round1.docx` / `custom-round2.docx` |
| 两轮修改与复查报告 | `work/phase4/final/custom-round1-changes.md` / `custom-round1-recheck.md` / `custom-round2-changes.md` / `custom-round2-recheck.md` |
| 独立CLI复查 | `work/phase4/final/extended-independent.json` / `custom-round1-independent.json` / `custom-round2-independent.json`（均有同名.md） |
| 每轮分类清单 | `work/phase4/final/extended-fixed.types.json` / `custom-round1.types.json` / `custom-round2.types.json` |
| 自动与浏览器验收 | `work/phase4/acceptance.log` / `work/phase4/browser/` |
| 四张真实截图 | `work/phase4/screenshots/01-分类确认.png` / `02-标题题注报告.png` / `03-第二轮复查.png` / `04-AI历史解析规则确认.png` |

识别算法只是结构清楚文档的辅助建议，没有测定通用准确率。无正文起点、目录/正文边界不清、无分隔编号、异常本地化标题ID、自动编号、复杂字体/样式、公式域修订及非顶层对象仍需人工调整或复核。文件中的域和表格被核对保留，不表示其Word显示或更新已经验证。下载JSON保留当时work/web运行时路径；稳定交付副本在work/phase4/final，独立CLI报告使用这些稳定路径。

两份新输入和默认修正版各2页，自定义第二轮因字号及行距扩大为3页，已用运行时自带LibreOffice逐页渲染查看，未发现缺字、内容溢出或图表丢失；采用本机Songti SC/Heiti SC字体替代，不证明已安装规范原字体或Microsoft Word排版相同。页面重新流动是格式变化的正常影响，程序不保证页码、分页或目录一致。未用Microsoft Word打开验收。

没有录最终视频、制作整套PPT、更新Word方案、部署、Git提交/推送、改原始资料或发外部消息。第四阶段完成后停止，等待第五阶段指令。

## 第五阶段 规范文件与可复用模板

第五阶段已验收TXT/DOCX规范导入、选段与编辑、DeepSeek生成R01–R07草稿、逐字段确认、同引擎检查/修正/落盘复查，以及JSON模板导出和重新载入。旧R05/R06短文本入口保留为兼容入口。默认学校演示JSON未改；新模板结构版本为2，运行配置版本为`template-demo-2.0.0`，扩展模式再组合固定R08–R12版本和哈希。

### 启动与配置

```bash
cd '/Volumes/XD20/Developer/论文有格'
.venv/bin/python -m streamlit run app.py \
  --server.address 127.0.0.1 \
  --server.port 8501
```

访问 **http://127.0.0.1:8501**。仍使用现有本机`.env`或环境变量：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL=https://api.deepseek.com`、`DEEPSEEK_MODEL=deepseek-flash`。没有配置时固定规则和已确认模板仍可用。不要把密钥发到聊天、写入模板或报告；`.env`继续被忽略，`.env.example`只有占位值。接口、模型名及JSON Output于2026年10月14日再次核对[官方Chat Completions文档](https://api-docs.deepseek.com/api/create-chat-completion/)和[JSON Output说明](https://api-docs.deepseek.com/guides/json_mode/)。每次点击至多一次POST，30秒超时，不自动重试；新草稿输出预算4096 tokens，旧短规范入口仍1024。

### 操作顺序

1. 打开“规范文件与可复用模板（R01–R07）”。可输入文字，或上传**格式要求**TXT/DOCX（最大2MB），也可一键导入公开演示规范A/B。此入口与下方**待检查论文**DOCX入口不同。
2. 核对提取文本和来源位置，勾选规范段落/表格文字，点击“使用所选规范文字”；可继续编辑摘录。只有点击“已核对，确认待发送文本”再点击“解析R01–R07要求”才调用API。最多12000字符，含来源标记；超限须缩小范围，不会截断。不会发送论文、分类、作者资料或磁盘路径。
3. 查看提取值、原文、来源位置和不执行提示。每个空字段须明确选“沿用默认值”或“手动指定”，四边距各自决定。可以编辑数值和字体。最终表区分AI提取、用户确认值、用户选择默认；编辑值即使保留原文也不声称原文精确支持。
4. 给模板命名，核对完整配置，点击“确认并应用完整模板”。草稿编辑本身不改变正在使用的配置。应用后旧范围确认、报告、选择及下载失效；论文和段落类型选择可以保留，但须重新确认。
5. 选择基础或扩展模式，载入论文，核对正文/分类，检查、选择修正、下载，并查看**保存后复查**。新规则直接进入现有`core`，不运行CLI子进程，不复制检查器。
6. 点击“保存已确认JSON模板”。下次上传该JSON到“载入JSON模板”，预览并重新确认后应用，**无需再次调用AI**。导入显示“本次未调用AI”；模板中的解析来源记录不证明实时调用或学校认可。点击“恢复默认学校演示规则”可以恢复只读默认配置。

规范文件、待发送摘录、论文和输出分别绑定实际哈希。手动编辑摘录后，其来源改为“摘录:L…”；原文件哈希仍记录为关联来源，不再假装编辑文字精确出自原段落。规范或模板导入失败不会替换当前生效配置；旧报告立即失效，可用当前配置重新确认检查。更换论文时保留当前模板，并在新任务目录保存副本。每轮记录实际规则版本/哈希；第二轮仍须明确使用上一轮文件，不自动累计。

### 支持值与边界

| 规则/字段 | 可确认的值 | 不自动执行 |
| --- | --- | --- |
| R01纸张 | A4竖向210×297mm | 横向、其他纸张 |
| R02四边距 | 上/下/左/右分别10–50mm；cm×10 | 单位不明、超范围、只提左右时补上下 |
| R03中文字体 | 宋体、黑体、楷体、仿宋 | 未知字体、把西文字体要求套到中文槽位 |
| R04西文字体 | Times New Roman、Arial、Calibri | 未知字体、把中文/标题/摘要要求套到西文 |
| R05普通文字字号 | 8–24pt，0.5pt步长；已列常见中文字号转换 | 标题字号、含糊/冲突值、范围外字号 |
| R06倍数行距 | 1、1.25、1.5、2倍 | 固定值/最小值行距 |
| R07首行缩进 | 0、1、2字符；“无首行缩进”=0 | cm/mm/磅到字符的猜测换算 |
| R08–R12 | 扩展模式继续固定标题/结构/题注规则 | 本次AI自定义标题、摘要或题注 |

这是课程原型支持范围，不是学校通用标准。R07已经实际验证0/1/2字符的正确、错误及修正，以及无缩进、等效点值和冲突属性；不只是放宽配置校验。依赖提示按当前要求字符数计算，字号改变仍不会暗改未选缩进。字体分别改`eastAsia`和`ascii/hAnsi`，其他槽位不随意覆盖。R01也检查显式横向属性。原有内容保留、拒绝覆盖、样式继承和复杂结构待复核保护继续使用。

TXT自动模式只接受严格UTF-8和带BOM的UTF-16；GB18030须明确选择，改变解码选项会重新提取。非法字节、替换字符或异常控制字符报错，不忽略字节。DOCX按主文档普通段落、表格行/单元格/段落顺序提取，保留制表和换行，定位如`DOCX:P3`、`DOCX:T1:R1:C2:P1`；修订、字段、图形、文本框、嵌套表格等跳过并提示，不声称完整提取。文字总量超过100000须先缩小文件；仅选中摘录最多12000字符。

跨单元格的“字段名/单位/值”、跨段落的正文范围或复杂冲突措辞，可能无法通过保守原文校验，需要用户合并编辑摘录或明确手动决定。不能把标题、摘要、题注要求当正文，也不能把待确认当符合。PDF、OCR、任意复杂规范、打印和语义要求**暂缓/不支持**。现有主题字体、特殊run、字段公式、编号与分类局限仍见前文。

模板使用UTF-8 JSON，最大64KB，校验版本、字段白名单、有限数值、范围、引用文字与来源位置；拒绝重复字段、未知可执行字段、代码/路径/工具指令。模板含名称、支持字段、最终值、来源、规范摘录/文件哈希、本地确认和解析来源元数据，不含密钥、论文内容、私有路径或会话凭证。旧版第五阶段预览若缺解析收据，显示未验真的导入来源；不伪装为实时API。没有账号、数据库、共享缓存或模板中心，也没有签名证明导入文件的来源可信。

会话目录仅保存当前会话文件；重置只清理该会话论文和规范目录。Streamlit重运行和下载不重复修正。**完整刷新浏览器会建立新会话**，请重新载入模板/论文；没有做跨刷新持久会话。关闭后遗留目录没有后台清理，不能通过重置删除其他会话。

### 样本与实际验收

- 演示规范A：`samples/norm-A.txt`，接近默认值，包含不执行的双面打印要求；B：`samples/norm-B.docx`，正文黑体/Arial、14pt、2倍、一字符，边距上30/下20/左35/右30mm，另有标题固定20磅和打印要求。均为软件演示，不冒充学校正式文件。独立人工期望：`samples/norm-expected.json`。
- 使用同一`samples/extended-correct.docx`及其确认分类：A模拟API后实际core检查0问题/0待复核；B真实API并确认后24问题，全选24项保存读回0问题/0待复核。固定R08–R12保持通过。图片、表格、PAGE字段、正文及其他ZIP成员保留核对通过；原稿哈希不变。
- 原95项无回归；新增24项，共**119项自动验收通过**。自动测试全用模拟API，覆盖提取/选段/编码、单位换算、独立边距、非正文排除、非法值/结构/证据、来源、真实属性修正、0/1/2缩进、字体槽位、导入导出、失效、故障降级、双会话/多轮和篡改阻止。不能以数量推断通用规范准确率。
- 第五阶段真实请求**2次**，均只发送公开规范B；`deepseek-flash`，2026-10-13T17:54:00.113680+00:00（2.966秒）及2026-10-13T18:09:13.238475+00:00（2.116秒）。第二次对应最终规范DOCX和最终界面。两次均提取10字段，原文/位置及数值校验通过，标题固定值与打印不执行。A没有真实调用，明确保留模拟记录。
- 真实Chrome已完成规范DOCX上传、预览/确认、解析、字号13.5再改14（最终来源为用户确认）、命名/应用、论文上传/分类、24项修正、下载与实际复查；另一Context上传模板重新确认后同样24问题、0问题副本，结果属性和文件字节相同，无新API调用。还验证TXT上传、替换规范使报告/下载失效、恢复默认0问题、菜单Rerun和重复下载不生成新副本、会话隔离。独立CLI及core重新读取下载副本也通过。

| 交付 | 本地位置 |
| --- | --- |
| 演示规范A/B及独立期望 | `samples/norm-A.txt` / `samples/norm-B.docx` / `samples/norm-expected.json` |
| B浏览器导出、免API重载再确认模板 | `work/phase5/final/template-B-current.json` / `template-B-current-reusable.json` |
| B原稿、实际修正版 | `work/phase5/final/original-current.docx` / `fixed-B-current.docx` |
| B修改、复查、完整结果与分类 | `work/phase5/final/changes-B-current.md` / `recheck-B-current.md` / `result-B-current.json` / `fixed-B-current.types.json` |
| 模板重载副本与完整结果 | `work/phase5/final/fixed-B-current-reloaded.docx` / `result-B-current-reloaded.json` |
| 独立CLI/core复查 | `work/phase5/final/cli-current-recheck.json` / `.md` / `reloaded-independent.json` / `.md` |
| 真实API脱敏记录 | `work/phase5/final/real-api-B.json` / `real-api-B-current.json` |
| A模拟记录、模板及实际检查 | `work/phase5/final/parse-A-simulated.json` / `template-A-simulated.json` / `check-A-simulated.json` / `.md` |
| 自动与真实浏览器证据 | `work/phase5/acceptance.log` / `work/phase5/browser/` / `work/phase5/acceptance-summary.json` |
| 三张真实网页截图 | `work/phase5/screenshots/01-规范文件预览.png` / `02-规则确认.png` / `03-模板重新载入.png` |
| 另附实际落盘复查截图 | `work/phase5/screenshots/04-模板B落盘复查.png` |

旧CLI不变；确认模板可直接复用已有`--custom-rules`：

```bash
.venv/bin/python cli.py check work/phase5/final/fixed-B-current.docx \
  --classification-manifest work/phase5/final/fixed-B-current.types.json \
  --mode extended \
  --custom-rules work/phase5/final/template-B-current.json \
  --report work/my-phase5-recheck.json
```

报告路径必须新建。程序接口仍为`check_document`/`fix_document(..., custom_rules_path=模板路径)`，自动检查、修正和读回使用同一配置；`core.norms.extract_norm`提供本机提取，`ai.template_spec.parse_template_requirements`提供单次请求和校验，`core.templates`负责严格模板校验/编译。旧`make_custom_config`仍仅R05/R06，`load_rules`仍严格固定学校默认值。

最终规范DOCX1页，B修正版3页已用运行时LibreOffice逐页查看；字号/边距变化导致图与题注跨页及分页变化，程序没有修题注位置或重算目录页码。采用本机替代中文字体，不保证Microsoft Word排版一致，**未用Microsoft Word打开验收**。未录最终视频、做整套PPT、更新Word方案、部署或提交推送；第五阶段完成后停止，等待下一阶段指令。

## 第六阶段：本地页面预览与图题辅助

格式检查的“0问题、0待复核”只表示启用规则在已覆盖范围的属性检查结果；分页和所有可见排版需要另行查看。默认R01–R07、扩展R01–R12、模板、CLI和原调用兼容；新增 **L01** 是产品排版辅助，不计入学校格式规则数。

启动不变：

```bash
cd '/Volumes/XD20/Developer/论文有格'
.venv/bin/python -m streamlit run app.py \
  --server.address 127.0.0.1 --server.port 8501
```

实际地址：http://127.0.0.1:8501 。检查/修正后展开“本地页面预览、前后对比与图题辅助（可选）”：

1. 选择左、右文件（当前会话原稿、当前处理输入或同一确认配置下的某轮输出），分别点击生成页面预览。不会随下载、重运行自动渲染；相同文件/轮次、范围、规则及渲染配置复用匹配缓存。
2. 按页码并排查看。显示文件名、轮次、当前规则版本、渲染器、实际页数、生成时间和字体。最多预览前10页；少页或超出范围显示缺少对应页，不强行对齐。可以在详情记录本人“已查看/发现问题”及观察文字，记录不是程序视觉验收。
3. 扩展模式确认分类后，选择“本次辅助输入”，勾选图片段→紧邻图题段的关联，再点击“确认关联并生成排版副本”。只给图片段设置keep-with-next、给图题设置keep-lines；没有移动/缩放图片、改文字或编号。原稿及各轮副本均保留；新副本独立读回R01–R12及这两个属性，修改记录标L01及具体属性。
4. 选择新一轮输出，主动再次生成预览，人工查看是否同页。仅设置相邻属性不保证跨页解决；整体过高、现有强制分页、不同渲染器可能仍跨页。本阶段不处理表格题注相邻、标题孤行、浮动图片、多图、文本框、跨表格关系、复杂图题字段/链接/修订/上角标及不明样式。冲突对象列为待复核，不删除原分页属性、不强行关联远处图题。

渲染使用本机 **Codex bundled LibreOfficeDev 26.8.0.0.alpha0 / Poppler**（bundle26.1011.11113），通过documents技能原`convert_to_pdf`及Poppler真实栅格化。每次独立任务、配置、字体缓存及LibreOffice profile，仅传入任务中的DOCX副本，前后核对源文件及副本字节。单文件总预算约45秒；失败/超时/字体核对失败只影响预览，检查、修正、下载仍可使用。含任何外部关系的DOCX暂不预览（包括普通外部超链接），避免渲染读取外部内容。没有安装或控制桌面LibreOffice；没有调用外部服务。

预览不是通用安装依赖：运行时路径固定在`core/preview.py`的RUNTIME、RENDERER，适用本次已核对的Mac。换电脑或bundle版本，需要重新通过workspace dependency工具核对路径；缺失时网页提示预览不可用，不影响引擎。未更改requirements和全局Python。

字体配置读取系统、用户Fonts及本机已安装Word的DFonts。实际匹配宋体→SimSun、黑体→SimHei、Arial、Times New Roman，当前B样本无需字体替代。未额外下载或安装字体，也未修改Word全局设置。缺失字体时明确显示实际替代族；备用宋体→Songti SC、黑体→Heiti SC、楷体→Kaiti SC、仿宋→Songti SC仅用于预览，可能改变分页，DOCX目标字体不变。字体清单不保证每个字形、所有主题字体或每一软件的显示一致。字体环境/渲染器版本变更使旧缓存失效。

实际B验证：第五阶段B文件在bundled预览中图在第1页、图题在第2页；L01后图与图题一起位于第2页，仍为3页。独立R01–R12复查0问题/0待复核，原稿、上轮文件、文本、表格、图片尺寸/媒体、编号、PAGE字段及分节保留核对通过。原稿对照为2页。Word16.80已实际打开合成原稿、B及辅助副本，无修复提示，目视查看标题、字体、图片、图题、表格；B在Word中处理前后图题均已位于第1页，表格在第2页，且标题颜色与bundled预览有差异。本次不是逐页Word全面验收。最后Mac锁屏阻止恢复查看比例/关闭窗口，文件未保存或覆盖。

第六阶段原119项无回归，新增33项共152项自动验收通过（渲染失败、字体缺失等用明确模拟，不冒充真实页面）；实际渲染和真实Chrome交互记录另列。未增加标题孤行辅助，不录最终视频，不制作PPT，不部署。

| 本次证据 | 路径 |
| --- | --- |
| 合成原稿 | `samples/extended-correct.docx` |
| 辅助前B及确认模板 | `work/phase5/final/fixed-B-current.docx`、`template-B-current.json` |
| 辅助后B及分类 | `work/phase6/final/B-adjacent.docx`、`B-adjacent.types.json` |
| 修改记录、复查及独立检查 | `work/phase6/final/layout-changes.md`、`recheck.md`、`independent-recheck.json` |
| 原稿、B处理前/后真实PNG及元数据 | `work/phase6/final/original-page-*.png`、`B-before-page-*.png`、`B-after-page-*.png`；对应`*-preview.json` |
| 浏览器下载及独立复查 | `work/phase6/final/browser-adjacent.docx`、`browser-rules.json`、`browser-result.json`、`browser-independent.md` |
| 图题关联及前后截图 | `work/phase6/screenshots/` |
| 分开记录的验收 | `work/phase6/acceptance.log`、`acceptance-summary.json`、`visual-qa.md`、`browser/` |

网页继续直接调用同一核心检查器。新增入口为`core.suggest_figure_pairs(path, confirmed_classification)`、`core.apply_figure_layout(input, new_output, body, …, confirmed_keys=[…])`及可选`core.render_preview(path, task_job_root, context=…)`；L01使用原检查/复查规则对象和专用分页属性白名单，不复制检查器。人工视觉记录与属性报告分开。

## 第七阶段：表题与标题相邻辅助、课程文档适配

运行方式不变，当前实际地址为 `http://127.0.0.1:8501`：

```bash
cd '/Volumes/XD20/Developer/论文有格'
.venv/bin/python -m streamlit run app.py \
  --server.address 127.0.0.1 --server.port 8501
```

1. 选择“正文及标题题注检查”，上传DOCX，核对分类；表题标为“表题”，标题标为相应一级/二级/三级。编号属于顶层段落，不是页码。
2. 确认分类并检查，展开“本地页面预览、前后对比与排版辅助（可选）”。图片、表题、标题共用一个“本次辅助输入”，可选择原稿或明确的第几轮副本。
3. 勾选具体安全建议，点击“确认关联并生成排版副本”。默认不选；复杂关联另列待复核，人工确认不能绕过结构保护。
4. 下载新副本、修改记录、落盘复查；辅助属性与格式结果分开。可主动生成两侧真实页面预览并选择页码，再记录人工观察。点击下载或页面重运行不会重复执行。
5. 后续辅助直接选择上一轮文件；继续格式修正可用“以本轮修正版开始下一轮”。每轮新路径、输入哈希和规则版本均记录，原稿及前轮保留。改变分类/模式/输入/规则后旧确认和下载失效，需重新确认。

| 能力 | 实际支持 | 不支持或待复核 |
| --- | --- | --- |
| L01 | 原有单一普通内嵌图片→紧邻确认图题 | 浮动、多图、复杂或远处关系 |
| L02 | 顶层普通表题→XML中紧接普通表格；只给表题keepNext | 中间空段/内容、嵌套或浮动表格、字段修订、条件样式分页、首行连续相连属性等 |
| L03 | 确认标题→XML紧接确认普通正文；只给标题keepNext/keepLines | 后续空段、标题、表格或复杂对象、强制分页/分节、后续正文已有keepNext等 |

L02只连接表格开始部分，长表正常跨页，不改变表格内容、尺寸、列宽或合并。L03不把整章正文连续串联，不改标题样式/字体/间距，也不删除原分页。过长标题或表格开始部分仍可能放不下。“已设置相邻属性”不是“跨页/孤行已解决”，可见结论要在具体环境另查。原R01–R12、默认JSON和CLI语义保持不变。

核心新增 `from core import suggest_pagination_aids, apply_pagination_layout`，参数沿用扩展模式的哈希绑定分类清单、规则配置及`confirmed_keys`。L01原函数继续兼容；三种辅助复用同一事务、内容保留核对及格式读回，不另做检查器。

真实课程适配增加保守的多级十进制自动编号标题线索，始终标为歧义，仍需确认；普通列表、未定义编号、特殊章节和短文本不会因此自动变成已确认标题。含“软件演示样本”的正文可能被建议排除，请人工调整。预览对旧字体名“仿宋_GB2312”明确替代为Word只读DFonts中的FangSong，界面继续提示非完全字体匹配和分页风险，DOCX字体不改，缓存配置版本更新为preview-1.4。

验收分别记录：原152项保持通过，新增29项共181项自动验收；合成A/B在bundled LibreOffice的真实页面分别改善了表题跨页和标题孤行，长表仍跨页。真实Chrome完成表题/标题确认、分类调整、前后预览、下载、Rerun、双会话与组合辅助两轮；下载文件独立复查。排版案例只验证辅助，不把其所有填充段当格式正确对照；扩展正确样本组合两轮后独立R01–R12仍0问题/0待复核。

内部真实课程论文只选8个正文及3个标题核对，两轮修正、内容/浮动图/表格/自动编号/分节保护及前10页渲染；仍有10个未选问题、25待复核。本阶段没有向DeepSeek发送论文，也不公开原文/作者或截图。Word因Mac锁屏未完成实际打开；真实课程全文人工视觉及与Word差异仍未验收。没有通用学位论文准确率或学校合格结论。

| 交付 | 路径 |
| --- | --- |
| 两份合成原稿及清单 | samples/layout-table-before.docx、layout-heading-before.docx及同名.types.json |
| 辅助副本/修改/复查 | work/phase7/final/table-after.docx、heading-after.docx、各*-changes.md、*-recheck.md |
| 真页图及渲染记录 | work/phase7/final/previews/、各*-preview.json |
| 合成真实网页截图 | work/phase7/screenshots/ |
| 属性/视觉/内部适配范围结论 | work/phase7/visual-qa.md、acceptance-summary.json |
| 自动/浏览器/独立复查证据 | work/phase7/acceptance.log、browser/、independent-verification.json |
| 私有原文核对及两轮结果（不用于公开展示） | work/phase7/internal/ |

未录最终视频、制作PPT、重生成Word方案、提交推送Git、部署或修改组员原资料。第七阶段开发结束；Word及真实课程全页视觉保留为未验收，等待下一阶段指令。

## 第八阶段：字体证据与自动编号标题只读检查

运行与操作入口不变，继续使用基础R01–R07或扩展R01–R12，无新增规则编号、模块页面或AI调用：

```bash
cd '/Volumes/XD20/Developer/论文有格'
.venv/bin/python -m streamlit run app.py \
  --server.address 127.0.0.1 --server.port 8501
.venv/bin/python -m unittest discover -s tests -v
```

实际访问地址：<http://127.0.0.1:8501>。核对分类并确认后点击检查，报告新增“解析依据 / 处理建议”列。高级JSON和Markdown保留字体槽位、声明来源、继承路径、主题语言/映射及编号定义证据。待复核说明指出未检查对象和人工核对方法；其他已完成检查仍分别展示，人工视觉记录不会改变引擎状态。

| 读取能力 | 已支持的明确场景 | 保留的限制 |
| --- | --- | --- |
| 直接与样式字体 | docDefaults、实际默认段落样式、basedOn、字符样式、直接run；按槽位分别继承 | 缺失或循环/重复/冲突继承待复核，不补宋体或Times New Roman |
| 主题字体 | 常见Transitional DOCX实际主题关系；major/minor的Ascii、HAnsi、EastAsia；Latin及明确Hans/Hant映射，或无themeFontLang时明确的区域字体 | 缺失/损坏/外部主题、主题覆盖、未知语言/脚本、跨槽枚举及不唯一映射待复核 |
| hint与字符 | Basic Latin仍用ASCII，不因eastAsia hint把ASCII整体跳过；普通Latin默认hint与常见中文分别检查 | eastAsia hint下扩展Latin、复杂脚本和未支持字符保持待复核；Times New Roman东亚特殊回退可读但依赖性修改阻止 |
| 家族名称 | 稳定大小写及明确的SimSun/宋体、SimHei/黑体、KaiTi/楷体、FangSong/仿宋别名 | 不将新宋体、旧GB2312字体或预览替代字体视为目标字体；不检测安装就宣称已安装 |
| 自动编号标题 | 人工已确认类型；只读numPr→numId→abstractNumId→ilvl，简单十进制及明确覆盖；普通标题文字字体/字号独立检查 | 符号继承、序列连续性、样式链接、图片编号和冲突定义仍需复核；不改numbering.xml |
| 编号段落与R11 | 编号pPr没有待定对齐/行距依赖时正常读取这两项；R11检查真实Heading引用及大纲 | 已知不符可以报问题，但自动编号R11不可自动修正；不重写编号或用人工分类证明样式存在 |

这些是DOCX声明的字体证据，不是本机安装证明。预览另行报告实际字体匹配及替代，preview-1.5缓存指纹包含解析器版本；网页仍最多前10页。用户可以只选明确可修正的普通文字属性，原稿、编号、样式、页眉/页脚、媒体及未选项保护继续生效。同一个run含已知ASCII和待定Latin时，保留原待复核记录，并单列可判定槽位；安全判断不能证明未选槽位不变时不允许修改。

微软依据：[rFonts字符映射与hint](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/aef3c9a6-5d6c-434b-90b7-85e761fd8e62)、[主题语言](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.themefontlanguages?view=openxml-3.0.1)、[字体槽位](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.runfonts?view=openxml-3.0.1)、[编号符号rPr与文字分离](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.runproperties?view=openxml-3.0.1)。范围限定不等于实现整个Open XML字体或编号规范。

**验收分开记录**：原181项无回归，新增44项，共225项通过，全部无付费API。真实Chrome以合成样本验证原因、R11阻止、选择安全修正、独立下载复查、Rerun、双会话与模式失效。合成样本6问题/4待复核，选中5项安全修改后1问题/4待复核，未把剩余编号依赖或字体未知当通过。

真实课程内部使用第七阶段同一第二轮输入、8正文/3标题分类及同规则：10问题/25待复核→38问题/9待复核。13条原R04经独立raw XML核对为ASCII指定宋体，3个标题的字体/字号/对齐/行距可判断，3条R11确定不符但不可自动修正。另3个编号符号记录及6个覆盖提示保留。第三轮仅13处ASCII字体和3处标题字号，共16项，读回后22问题/9待复核；未选中文标题字体、对齐/行距、样式及原问题不改。

全页视觉已补齐：原稿、第二轮、第三轮各13页，实际逐页查看39张真实PNG。发现原页眉有VML图形及OLE关系：反复校徽的来源不能归因于正文浮图重复；本渲染环境中页顶裁切和位置差异仍待Word对照。页眉/OLE/媒体及主文档锚点未改，只证明结构字节保留，不证明OLE行为或所有软件视觉一致。内部核对在work/phase8/internal，未公开论文正文、作者或截图。Mac仍锁屏，Word合成案例及真实原稿/副本**未验收**，不宣称无修复提示或Word版面通过；第六阶段Word与LibreOffice差异观察保持原记录。

| 交付 | 本地路径 |
| --- | --- |
| 合成原因示例与人工清单 | work/phase8/samples/resolution-demo.docx、resolution-demo.types.json、check.json、check.md |
| 合成真实浏览器截图 | work/phase8/screenshots/01-resolution-reasons.png、02-safe-fix-result.png、03-pending-reasons.png |
| 自动/浏览器与独立下载复查 | work/phase8/acceptance.log、browser/accept-final-delivery.log、browser/independent-recheck.json及.md |
| 分别记录的状态与技术边界 | work/phase8/acceptance-summary.json、implementation-notes.md、visual-qa.md |
| 私有同输入逐项对照及独立读数 | work/phase8/internal/review-comparison.json及.md、independent-readings.json、independent-object-inventory.json |
| 私有第三轮副本与报告 | work/phase8/internal/round3-font-size.docx、round3.json、round3.types.json、round3-changes.md、round3-recheck.md |
| 私有全页视觉及保护 | work/phase8/internal/visual-pages.md、*-full-preview.json、full-previews/、final-preservation.json |

公开接口保持`inspect_document/check_document/fix_document`、原R01–R12配置及辅助/预览接口兼容；报告增加证据而不新增规则。第八阶段到此停止，不录视频、制作PPT、重生成Word方案、提交推送Git、部署、改组员原资料或发送外部消息。

## 第九阶段：标题、图题、表题自定义与版本3模板

运行方式不变，当前地址 <http://127.0.0.1:8501>：

```bash
cd '/Volumes/XD20/Developer/论文有格'
.venv/bin/python -m streamlit run app.py \
  --server.address 127.0.0.1 --server.port 8501
.venv/bin/python -m unittest discover -s tests -v
```

1. 选择“正文及标题题注检查”，展开“规范文件与可复用模板（R01–R12）”。可导入TXT/DOCX，也可一键导入“标题题注规范A/B”。规范文件与待检查论文仍是两个入口。
2. 核对提取文字、选段或编辑摘录，点击“已核对，确认待发送文本”，再点击“解析R01–R12要求”。只有此按钮会请求DeepSeek；不发送论文、段落分类或作者资料，一次点击最多一次请求，约30秒超时，无自动重试。
3. 按正文/页面、一级/二级/三级标题、图题、表题分别核对提取值与原文。未提到、冲突或含糊的字段保持空；必须逐项明确选默认/手动值，或主动点击“未提取字段全部沿用默认值（明确选择）”。这不是AI补出的要求。手动改值后来源为用户确认，保留原文也不宣称修改值精确受它支持。
4. 确认页对比三级标题和两类题注的最终值，完整逐字段配置另可展开。点击“确认并应用完整模板”后，旧论文范围确认、检查、选择、下载及不匹配预览失效；重新核对分类再检查。R08–R10/R12结果按属性拆分，可用key选择字号、字体、对齐或行距；R11样式保留与自动编号保护不取消。
5. 下载新DOCX、修改记录、落盘复查，可查看标题/题注的实际属性汇总；数据来自`result['after']`。保存JSON模板，下一会话上传、核对并重新确认后即可使用，无需再调用AI。恢复默认学校演示规则会撤销自定义作用。

| 对象/规则 | 可自定义 | 本阶段不自定义或不执行 |
| --- | --- | --- |
| 页面/正文R01–R07 | 原范围不变：A4竖向，四边距10–50mm，正文中文四族/西文三族，字号8–24pt半磅步长，倍数1/1.25/1.5/2，首行0/1/2字符 | 横向、未知字体、固定/最小行距、点/厘米缩进、打印/语义等 |
| 一级/二级/三级R08–R10 | 每级中文宋体/黑体/楷体/仿宋；字号8–36pt、0.5pt步长；居左/中/右/两端对齐；倍数1/1.25/1.5/2 | 西文字体仍Times New Roman；不自定义加粗、颜色、段前后、缩进、章前分页、编号或文字 |
| R11 | 继续实际Heading1–3及对应大纲结构检查 | 不让AI生成样式名；自动编号样式修改仍不可自动执行；不能因字体/人工分类就认为存在Heading |
| 图题/表题R12 | 各自中文字体四族；字号8–24pt、0.5pt步长；同一编号按确认类型取本对象标准和来源 | 西文槽位仍宋体；不新增位置、编号、对齐、行距、缩进、关联或图表重排 |

这是课程原型的支持边界，不是学校通用标准或任意规范理解能力。“标题小二”未给级别不能默认为一级；“标题1.1”或章节数字不能单靠数字猜级别；“各级标题均黑体”范围明确才分配到三级；同对象冲突不选最后一句。固定值行距、编号和打印等显示不支持；摘要要求不进入正文。源码读取的主题字体、特殊结构、自动编号符号与样式依赖边界继续见第八阶段。

**版本与来源**：新扩展草稿导出结构版本3，26个受支持字段按对象命名；规则数仍7/12。基础模式解析仍只请求原十个页面/正文字段并导出版本2，不执行标题题注。版本2导入先保留正文值，扩展部分明确显示沿用旧版本固定要求；可以直接确认按旧含义使用，或点击“升级到版本3并核对标题题注”，记录本地转换及`legacy_fixed`来源，再编辑/确认。旧R05/R06短规范JSON也继续有效。新导入拒绝未知字段、非法数值、版本、单位/依据或不一致来源；AI自报确认/置信度不接受。导入来源记录不是本次实时请求或学校认证。重新确认会刷新确认时间/导入标志，文件哈希可能变化，字段标准与检查结果必须一致；每次修正前后始终绑定同份确认配置。

**实际验收**：原225项无回归，新增25项，共250项通过，自动API全部模拟。包含对象/来源分配、缺失与冲突、TXT/DOCX位置、非法类型/枚举/单位/范围/依据、组合属性落盘、不同题注、单项修改与R11/编号保护、完整性、模板版本/重载、会话/状态及失败降级。基础API不能由模型意外扩大到标题范围。

真实API仅一次公开规范B，`deepseek-flash`，2026-10-14T04:37:54Z，约4.697秒，提取26项；编号/打印/介绍语义条款未执行。[DeepSeek官方JSON Output](https://api-docs.deepseek.com/guides/json_mode/)核对`json_object`、JSON提示与示例及模型。真实浏览器把一级字号20pt改为20.5pt，准确记录用户确认来源；其余标题17/13.5pt，图题9pt、表题12pt。规范A的真实API未调用：自动测试模拟A解析，交付A模板是用户明确继承默认，未冒充AI。

同一合成`extended-correct.docx`、独立清单的5正文及已确认标题/题注：A检查0问题/0待复核，B检查50问题，选择50项后落盘与独立复查0问题/0待复核。原稿、编号、样式、图像/表格/域及未选属性保留。新会话导入B无需API，输出与首次正确范围文件字节一致；下载/Rerun、规范变更失效、恢复默认和两会话另有真实Chrome记录。浏览器调试中误用旧范围假设并选了封面段落的副本归入debug，不作为交付或验收；最终分类与独立样本清单逐项相同，不从程序建议复制黄金答案。

**可见排版**：原稿2页、B副本3页，五页均用bundled LibreOfficeDev26.8.0.0.alpha0/Poppler真正渲染并目视。标题与题注可读，图题9/表题12的差异可见；图/图题/表题/表格均第2页，未见明显裁切或丢失。六种使用字体实际匹配，无替代提示，源文件哈希不变。但原表格160mm宽，B的新正文区145mm，越过正文右边界约15mm，仍需人工处理；没有偷偷改表格或规范消除差异。原分节造成第2/3页留白；PAGE域在预览显示3而原缓存保留2，是渲染器求值，DOCX字段/编号未改，目录不重算。属性0问题不代表所有排版合适。Word仍因Mac锁屏未打开验收，不用此渲染器代替Word。本阶段没有改真实论文VML或任何原组员资料。

| 交付 | 路径 |
| --- | --- |
| 合成短规范A/B及说明 | samples/norm9-A.txt、norm9-B.txt、规范对象样本说明.md |
| 新版A/B模板 | work/phase9/final/template-A.json（默认继承）；template-B.json（首次编辑确认）、template-B-active.json（交付修正实际采用） |
| 实际B副本与记录 | work/phase9/final/B-fixed.docx、B-result.json、B-changes.md、B-recheck.md、B-types.json、B-independent-recheck.json及.md |
| A/B输入检查与保护 | work/phase9/final/A-check.json及.md、B-before.json及.md、independent-verification.json |
| 旧版/转换范例与比较 | work/phase9/final/legacy-v2.json、legacy-upgraded-v3.json、legacy-compatibility.json |
| 真正规则确认/重载/读回截图 | work/phase9/screenshots/01-real-object-confirmation.png、02-edited-object-confirmation.png、04-template-reload.png、05-object-disk-values.png |
| 真正预览与视觉边界 | work/phase9/final/A-original-page-1.png及-2.png、B-fixed-page-1.png至-3.png、对应preview.json、layout-boundary.json；work/phase9/visual-qa.md |
| 分开验收与真实API | work/phase9/acceptance.log、acceptance-summary.json、real-api-record.json、browser/ |

下一阶段继续直接调用同一`check_document/fix_document`，传`custom_rules_path`及扩展分类清单；规范入口`ai.template_spec.parse_template_requirements(segments, extended=True)`，模板接口`make_template/validate_template/upgrade_template`。不复制检查器。第九阶段停止，等待下一阶段指令；不录视频、制作PPT、重生成Word方案、提交推送、部署或发送外部消息。


## 第十阶段：页面宽度检查与按需适配

“页面可用宽度 · 独立布局检查”在确认范围后可见，显示当前文件/轮次、W01表格与W02内嵌图片的风险、待复核及尺寸范围内对象；不改变R01–R12或旧CLI统计。改变边距的格式修正版同样可选作输入，原稿和所有轮次均保留。

1. 按原流程选模板、文件、确认正文/分类并检查。
2. 查看布局风险，展开“尺寸依据与确认适配（可选）”：核对节、纸张、左右边距、装订线、对象缩进、声明与可用宽度。
3. 表格逐列比较原/目标尺寸；若原为自动调整，先明确同意改为固定列宽，再勾选具体对象。图片只等比例缩小、默认不放大。
4. 点击“按确认尺寸生成新副本”；落盘后分别显示格式规则复查和宽度复查，下载DOCX、修改记录和复查报告。宽度记录同时在完整JSON和修改Markdown中。
5. 需要第二轮时点击“以本轮修正版开始下一轮”，或在宽度输入下拉框明确选择某轮副本。展开页面预览，主动生成原稿与新副本页图；不会因下载或重运行重新渲染/适配。

支持：常见Transitional DOCX、明确页面设置的单栏节、普通左侧装订线；按实际XML终止节映射对象。简单未合并顶层表格的tblW、网格、全部tcW一致时计算首选几何尺寸，支持绝对宽度与一致自动宽度适配；百分比宽度相对正文区，仅只读，一旦与网格冲突待复核。表格样式常见标量继承、缩进/对齐纳入判断；固定列宽不代表排版器永不覆盖首选尺寸。普通单一内嵌图片要求可靠媒体关系、相等内外extent、点值段落缩进可确定；同时更新外extent和内部变换尺寸，保持媒体、裁剪、题注及分页属性。

不自动处理：多栏/镜像/书籍或复杂装订、分节不明、嵌套/浮动/复杂合并/网格冲突/条件几何样式/行宽度例外、现有固定行高、字段/对象单元格；百分比表格仅只读。图片浮动、VML、文本框、多图、旋转/效果扩展、尺寸冲突以及无法可靠转换的字符缩进待复核。不将图片段继承firstLineChars=200猜成固定点值；B图片因此仍有一条独立布局待复核，不是格式规则待复核。

缩小列后若小于10mm，阻止并提示人工调整页面方向/内容；这是原型保护下限，不是学校要求。只改所选尺寸定义，不改内容/字体/编号/边框/合并，不设置固定行高；可增加换行、高度、页数，不保证图题同页或像素级正文边界。API：`core.check_widths(path, rules_sha256=...)`；`core.apply_width_adaptation(...)`接收完整当前计划、selected_keys及confirmed_fixed_keys，使用原引擎读回复查与白名单完整性保护。无需新运行依赖。

验收：286项自动（原250无回归，新增36），见`work/phase10/acceptance-final.log`；真实浏览器风险/确认/部分适配/第二轮/下载、Rerun、隔离及失效验证。最新真实渲染10页已逐页看，bundled LibreOffice/Poppler；Word仍锁屏未验收，没有外部API请求。测试数量不是通用文档准确率。

交付以`work/phase10/final-v2/`为准：B表格160.02→145.009mm，列4536/4536→4111/4110twips，属性规则仍0问题/0待复核；独立宽度0风险/1待复核（图片字符缩进）。合成表格179.987→145.009mm；内嵌图180×45→145.009×36.252mm；正常100mm表格/60mm图保留，复杂合并表格仍待复核及越界。B3页、合成2页不变，长文字每格2行→3行。查看`work/phase10/visual-qa.md`中的具体布局限制，不能称全文排版合格。

- 输入：`work/phase9/final/B-fixed.docx`；`samples/width-demo-final.docx`及独立`width-expected.json`。
- 副本：`work/phase10/final-v2/B-adapted.docx`、`width-demo-adapted.docx`。
- 修改/格式/尺寸/独立核对：同目录`*-changes.md`、`*-recheck.md`、`*-before-width.*`、`*-after-width.*`、`*-independent-*.json`及完整`*-result.json`。
- 真正页图：同目录`previews/`，路径与哈希见`*-before-preview.json`、`*-after-preview.json`。
- 网页图：`work/phase10/screenshots/01-width-risks.png`、`02-table-plan.png`、`04-second-round.png`、`09-B-real-page2-comparison.png`及B专用06–08。

服务仍为http://127.0.0.1:8501，启动命令不变。第十阶段停止；不录视频、制作PPT、部署、提交推送Git或修改真实课程原稿。


几何实现依据：[Microsoft TableWidth（首选表宽及百分比参照）](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.tablewidth?view=openxml-3.0.1)、[TableLayout](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.tablelayout?view=openxml-3.0.1)、[SectionProperties](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.sectionproperties?view=openxml-3.0.1)。表宽是首选值，渲染器可以因内容覆盖它，本功能因此始终保留主动预览和人工视觉判断。


## 第十一阶段：统一问题中心与离线阅读报告

首屏显示当前输入、原稿/轮次、模式、确认规则及是否需重新确认。确认范围并检查后，统一问题中心汇总四类：确定格式问题、宽度风险、可确认分页建议、待复核/支持边界。格式原问题数/待复核数不变，宽度按对象、分页按建议分别显示，不相加成“合格分数”。可按类别、对象、状态筛选，同对象展开多条原key；符合、不适用及边界可折叠，所有原始记录仍在导出中。

简化流程：

1. 选择规则及文件，核对正文/分类并确认，再检查。
2. 看“建议下一步”，优先处理纸张/页边距；字号与点值缩进依赖继续提示。点击建议只定位对象和操作区域，不勾选或执行。
3. 在“当前操作”选择格式、宽度、分页或预览，可点击“进入当前操作区域”。宽度建议直接针对当前查看的那一轮，展开具体尺寸确认；分页仍需明确确认关联。
4. 生成副本后看新文件剩余事项。需要修剩余格式时，明确点击“以本轮修正版继续处理”；查看历史不会暗中更换输入。
5. 历史表显示各轮修改、已解决/剩余/新增及适用状态，打开“查看某轮详情与下载”才提供该轮下载。换规则/分类后旧轮标不适用；换文件按原逻辑清理旧任务，只保留不可下载摘要。重新开始清理当前任务及摘要，其他会话不动。
6. 展开“导出可阅读报告”，填写脱敏显示名，点击“准备可阅读报告”，下载离线HTML、对应阅读Markdown/JSON。旧完整引擎JSON/Markdown仍保留为高级记录。

HTML来自已存在的格式、宽度、关联及轮次记录，不新增检查器；包含完整范围/来源、实际值/要求、修改及落盘复查、剩余/待复核、预览环境/字体、视觉状态和历史。若祖先轮曾应用分页属性但当前轮未重复复查，明确写历史来源，不冒充当前页验证。未生成预览、未记录用户视觉复核和未验收Word分别明示。分页建议不是错误，属性成功不是实际同页。

报告默认使用匿名显示名、按位置定位、省略论文原文，过滤私人路径及凭证类元数据；可明确启用短文，最多20个对象每个48字符并加省略号。所有字段、文件名、规范摘录/AI来源及原始详情都转义；内联CSS、无脚本/CDN/远程资源，CSP禁止执行。HTML不默认嵌入或打包页图，稳定PNG可另行选作附件。精确值在展开详情及JSON中保留；界面尺寸通常2位小数。

公开函数：`web.issues.project/filter_records/group_records/next_steps`只投影/筛选；`CenterSession.current_bundle/prepare_reading_export/history_bundle`维护绑定；`web.reading_report.portable/html_report/markdown_report`输出同份阅读数据。原核心检查、修正、CLI、模板和值保护保持兼容。新增祖先轮追踪仅汇总真实历史应用记录，不进行分页检测。

环境修复：Codex bundled工具更新到26.1013.11914，旧渲染脚本目录不在；仅更新`core/preview.py`的已核对路径和缓存元数据版本，保留原45秒/前10页/独立配置/哈希保护。没有安装桌面LibreOffice或Office。

验收：原286项无回归，新增32项共318项自动通过；浏览器流程A默认模板11→0格式问题，流程B载入已记录规范模板50→0、再做宽度第2轮、历史查看、真实预览、报告导出。B没有本轮实时DeepSeek调用，来源仍标导入模板。离线打开及恶意HTML验收无脚本执行/外部请求，统计/规则哈希/文件哈希/记录数与原始报告一致。默认A网页报告准确记录导出时未预览；后续QA渲染不篡改它。B网页有匹配3页预览，但用户未记录人工视觉，报告如实保留。

交付：`work/phase11/final/A-report.html`、`B-report.html`及同名前缀的阅读JSON/Markdown；对应`A/B-raw-result.json`、`*-legacy-recheck.md`、`*-legacy-changes.md`、`A/B-fixed.docx`、`B-active-template.json`。当前HTML在真实下载数据上做最终中文/单位展示整理，所有判断和精确原始值未改，核对记录为`*-report-verification.json`。PNG和环境记录见`final/previews/`、`B-preview-records.json`及`A-preview-record.json`。

真实界面截图在`work/phase11/screenshots/`：01下一步、10最终同对象问题中心、07两轮历史、05离线HTML。流程与7页目视、Word边界详见`work/phase11/visual-and-UX.md`；自动日志`acceptance-final.log`。Word只读取已打开合成原稿窗口，本轮新副本打开对照未完成，未保存或修改全局设置；报告保持未验收，不借原窗口/LibreOffice宣布Word通过。

限制：模板更换后旧记录仅作历史；文件切换的旧任务不可恢复下载，重要副本应先下载保存。导航不会一键解决全部排版；图段字符缩进、复杂对象及旧阶段布局边界不变。快照只存当前会话/任务目录，无长期项目库或同步。阅读报告隐私默认不能替代对使用者自行命名/规范摘录的人工脱敏核对。

本机启动命令与地址http://127.0.0.1:8501不变。第十一阶段完成后停止，不录最终视频、制作PPT、部署或提交推送Git。


## 第十二阶段：效率、批量分类与结果包

先建立3次重复的本地基线，再优化会话内重复分析与报告生成。新增能力仍调用原核心：缓存的是只读数据/不可变字节，不共享可变XML；输入、规则、范围、模式和轮次变化使旧结果失效。操作开始、输出下载/打包时仍校验内容哈希，外部修改不能依靠同名或mtime绕过。默认模板、旧CLI及全部318项原验收保留，当前352项自动验收通过。

操作：

1. 选择文件和规则。在扩展分类区域打开“批量调整与恢复初始建议”，按当前类型/歧义筛选候选，再明确多选编号或填写`8-10,20`。筛选不等于选中；查看数量/短文、明确目标类型后应用，更新的是草稿，尚未检查。恢复前先核对覆盖编号并勾选确认。
2. 完整核对范围/分类，点“核对完成并开始检查”。歧义/待确认项仍保留提示并跳过，确认失败不执行检查。原“确认…/开始检查”分步入口保留。相同绑定的普通检查复用只读结果；高级“重新检查”强制重新读核心。
3. 按问题中心选择具体格式/宽度/分页操作，另存及落盘复查。结果区点“下载本轮结果包”，一次得到本轮DOCX、修改记录、复查、离线HTML/阅读JSON/Markdown、规则/模板、范围清单及说明。包内固定安全文件名，默认不含原稿、页图、API记录、日志或整篇论文摘录；修正版本身自然包含待检查内容。未压缩成员合计上限25MiB，超过时用单文件下载。原单文件下载保留。
4. 主动生成预览。普通查看使用生成时的环境信息，不重新探测字体；“刷新预览环境”重新核对，不自动渲染。每次明确生成/复用仍核对当前环境和页面/PDF哈希，有效结果不再渲染。API `get_preview` 的默认验证行为兼容；网页只读展示明确使用生成时记录。首次仍同步执行，45秒超时、前10页限制不变。

只读/中心缓存各至多16项；不可变字节缓存至多8组、32MiB，只在当前WebSession中。新执行修正仍独立读取XML、保存、读回与完整性验证；历史仍独立核验文件，不用全局文档缓存或mtime快捷验证。重复快捷检查不重复写同一分类确认文件；重运行/下载不会触发AI、修正或渲染。

实际改善：普通预览查看不再重复探测（原路径约0.89s，基础样本热查看约2.5ms）；扩展宽度/分页重复读取约9.2/49.2ms降至约0.2ms；内部课程样本重复准备阅读报告约110.9→18.0ms。首次渲染仍约4–5.5秒，没有证明浏览器整条流程更快。相同A按钮12→11、B10→9，范围确认次数保持；A快捷+包6个主按钮（传统核心+四份文件下载11个）。单次浏览器时间有下载/客户端噪声，不推导提升比例。

证据与文件：

- [性能方法、原始记录及取舍](work/phase12/performance-and-acceptance.md)；`baseline.json`、`optimized-final.json`、`repeat-*.json`、`full-scope.json`、`cold-start.json`、`preview-matrix.json`。初始400段全待确认另行说明；补充390正文+10标题控制试验不冒称修改前数据。
- [默认结果包](work/phase12/final/A-results.zip)、[自定义两轮结果包](work/phase12/final/B-results.zip)；`final/bundle-verification.json`、`A/B-independent-recheck.json`。包内`rules.json`为实际已校验的源配置字节；B的`template.json`可按原界面重新导入，哈希和标准保持。
- `work/phase12/screenshots/batch-final.png`、`shortcut-final.png`、`A-package.png`、`B-preview.png`、`B-history.png`：真实网页；`browser/batch-final.log`、`isolation.log`、`comparable-A.log`、`optimized-B-final.log`及`acceptance-final.log`。

本轮没有新API或Word实际打开验收，Word仍未验收。真实课程仅本地性能测量，不公开正文和页图。首次渲染及长文首次报告仍需等待；后台队列暂缓以保留课程原型的简单生命周期。未增加排版检测领域，未提交推送、部署或录制最终视频。启动命令不变：

```bash
cd '/Volumes/XD20/Developer/论文有格'
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

访问 `http://127.0.0.1:8501`。验收：`.venv/bin/python -m unittest discover -s tests -v`。


## 第十三阶段：长文按需报告与后台预览

完整检查范围不变，问题中心默认每页20个对象。类别、状态、段落编号范围、关键词和编号排序均只影响展示；“查看所选对象详情”列出该对象全部记录和依据。符合、不适用及完整边界按需筛选；原始完整JSON需明确打开。HTML/Markdown/JSON/ZIP仍保存全部结果。

修正选择绑定finding key，提供“选择本页”“选择当前筛选”“清空全部”。跨页/筛选后保留明确选择，并显示本页、全部及筛选外数量。生成前统一表格列出全部选择，包含隐藏项。高级全选仍保留，没有默认全选。换文件/模板/模式/分类旧选择失效。

预览按钮提交后台任务，状态显示排队/运行/成功/失败/取消/失效和真实经过时间。等待时继续筛选、查看历史及下载已有结果；成功后点“查看预览”。该按钮只改变预览目标，不切换当前处理输入。其他已提交目标有独立状态，不自动把旧任务变成新副本预览。

队列最多1执行+2等待，不共享会话分析和文件；重复绑定复用任务、有效缓存不排队。2秒局部刷新仅读任务状态，完成时由主线程核对文件、规则、范围、轮次、环境、页图再接入。后台仅渲染独立快照，不调用Streamlit或写会话。同步generate_preview/render_preview兼容保留，真实渲染使用进程内锁。前台回调串行避免加载半成品状态。

取消排队会阻止开始；运行取消表示停止接收结果，**不表示子进程已经停止**，仍占用槽直到退出/超时。失败或队列已满可稍后明确请求；检查和下载继续可用。切文件/模板/模式/轮次或重新开始使旧任务失效，清理只限自己任务。应用重启不恢复任务，需重新生成。

实际验收：原352项+新增31项，共383项。400段明确范围的2015 finding完整保留，浏览器跨两页选119项、全部落盘通过，仍有1083问题/800待复核。旧长文60秒未完成末尾按钮，新页实测约0.33秒，初始4表格/12展开区；旧值是等待下界，不计算提升比例。预览运行期间下载约47ms、筛选约1.30s；成功可见约6.77秒，渲染未证明加速。真实双会话排队/取消/重试、缓存及17页长文前10页预览已验证。本轮无新AI请求、Word打开、远程部署或提交推送。

- [完整性能、失败记录与边界](work/phase13/performance-and-acceptance.md)
- [长文结果包](work/phase13/final/long-results.zip)、[独立复查](work/phase13/final/long-independent-recheck.json)、[阅读报告](work/phase13/final/long-report.html)
- 截图：`work/phase13/screenshots/cross-page-selection.png`、`paged-report.png`、`task-running.png`、`task-queued.png`、`running-cancel.png`、`visible-real-preview.png`。
- 原始日志：`work/phase13/acceptance-final.log`、`browser/finish-measure.log`、`long-actions.log`、`async-flow-final.log`、`two-sessions-final.log`、`running-cancel-passed.log`、`sort-confirm.log`、`long-preview.log`。

启动命令及127.0.0.1:8501不变。不持久队列、不立即停止运行任务；首次渲染、单对象大量run详情和完整导出仍有成本，不宣称Word或全文排版合格。

## 第十四阶段：保存项目、导入恢复与续做

“保存项目 / 恢复项目”在页面顶部折叠区域。它用于继续工作；“下载本轮结果包”仍用于取走成果。**项目包含论文原稿和副本**，仅点击保存后在本机下载，不自动上传。

1. 点击“保存项目”，再“下载项目包（含论文）”。默认保存原稿、当前输入、最多30轮副本与记录、模式、规则、范围/分类草稿及确认状态、待修正选择。同一DOCX按SHA256只保存一次。可明确选择仅保存原稿及当前输入，省略历史并留下带原编号的检查点；不静默丢弃。
2. 刷新/服务重启/新会话后上传项目ZIP，点击“校验项目包并查看摘要”。核对当前轮次、完整规则和段落范围；现有工作不会在校验时被替换。可先保存现有工作或取消恢复。
3. 勾选已核对，再点击“核对并恢复项目”。保存时确认的范围在此明确核对后重新确认和检查；未完成范围、模板及规范草稿仍为草稿。不会再次调用DeepSeek。恢复的解析来源是历史记录，不是实时请求。
4. 历史详情只查看/下载，不切换输入。要继续旧轮次，核对其规则与范围后点击“以历史第N轮继续处理”；当前输出继续沿用原“以本轮修正版开始下一轮”。新轮次编号高于所有保存轮次，输出唯一，不覆盖导入文件。

项目格式为`paper-grid-project`版本1：`project.json`白名单JSON清单，`documents/0000.docx`及`rules/0000.json`等内部固定成员名；清单以哈希引用原稿、当前文件、规则、完整范围和无循环父轮次关系。规则保留原始字节/哈希，兼容版本2/3模板及旧R05/R06配置。导入使用现有DOCX、规则、模板、草稿、分类校验，并在新任务目录写入固定名称，不按包内路径解压。

限制：压缩包/外层解压总量100MB，全部DOCX内部展开数据另限100MB；单DOCX10MB、单规则64KB、清单8MB、100成员、30轮历史。拒绝重复成员、绝对/穿越路径、符号链接、加密ZIP、未知字段/版本、缺失/哈希错误、轮次错配、循环及非法模板。失败只清理本次暂存目录，当前任务保留。保存/下载准备仍按内容哈希核对，外部修改或状态变化后旧包拒用；准备过的ZIP仅在当前会话复用。

旧修改记录、完整性和视觉结论仅标为保存时记录；历史属性重新读取但不证明旧操作真实发生。当前报告由本次实际检查生成。恢复时筛掉已不存在或不可修正的key并提示。页面图片、有效预览缓存、任务、子进程、环境/密钥/日志/私人路径和Python对象不保存。只有规范摘录和来源摘要保存，规范原文件不打包；以后需要重新选段时再次导入规范文件。运行中的本会话预览停止接收结果，等待其退出；排队任务取消。不会终止其他会话或Office进程。

本阶段439项自动验收（原383+56）；服务安全重启后从项目包重新恢复第3轮也已实际验证。真实网页完成自定义分类与两轮逐项处理、保存、刷新恢复、重新检查、第三轮修正及下载独立复查，也验证未完成分类和20pt标题模板草稿恢复后仍未应用。第三轮仅解决选中的一项，剩43问题/0待复核，不宣称全文合格。报告、原稿和前轮均保留。本轮无新AI、渲染或Word打开验收；既有视觉结论不升级。

三次合成测量中位数：首次准备11.5ms、复用准备9.6ms（仍核对所有文件）、导入校验13.2ms、恢复+范围确认+检查约183.8ms、单次强制检查约14.3ms。浏览器准备包138ms、导入摘要146ms、明确恢复至可操作约874ms；小样本、自动化交互及当前Mac的观察，不是通用性能承诺。完整证据、操作对照和失败尝试见`work/phase14/performance-and-acceptance.md`，演示包与实际网页下载副本见`work/phase14/final/`。

HTTP上传上限已调整为100MB；DOCX控件/引擎10MB、规范2MB及模板64KB保护不变。另用约11.86MB项目ZIP（每份DOCX约5.93MB）真实上传、核对恢复第1轮及重新检查10问题通过，记录browser/large-upload.log；这验证超过旧10MB HTTP上限，不宣称已实测最大100MB。大包合成噪声图片只作上传体积验收，不作视觉排版样本。暂存文件被外部修改时，恢复界面显示提示并仅清理导入目录，当前工作保留；不泄漏堆栈。

## 第十五阶段：单文档段落与前后置章节

新增显式 **单文档扩展检查**（CLI/API `mode='academic'`）启用R01–R22。基础仍7条，原扩展仍12条，默认JSON和旧CLI含义不变。R13检查按类型配置的段前/段后、对齐与加粗；R14–R21分别检查中英文摘要标题/正文、两类关键词行、参考文献标题/条目；R22提供只读的存在、字数、数量和手工编号提示。正文、三级标题、图表题注仍走原引擎。

学校出处与逐项边界见 [单文档覆盖表](outputs/phase15/单文档覆盖表.md)。固定新增配置 `rules/scut_2015_sections.json`：物理页17/18字体字号等，22/23/26/28/36范例标题前后各0.5行，16页摘要400–600字、关键词3–5个及主要参考10篇以上。英文关键词标签加粗依据23页。未明确的加粗、参考文献西文字体/缩进/间距、英文摘要首行缩进等不自动启用。文献最低数量只按确认条目计数；主要文献身份、外文2篇及导师例外、著录真实性和中英文一致性仍须人工核对。

操作：

1. 选“单文档扩展检查”，使用“摘要参考文献错误样本”或上传DOCX。
2. 核对新增类型建议，必要时按编号调整；建议尚未执行。样本第2段为软件说明，明确改为“其他”，再点击“核对完成并开始检查”。
3. 在问题中心按确认对象类型筛选；关键词的跨run片段以字符范围区分，选择保持finding key绑定。
4. 逐项或按当前筛选选择可修正格式；字数、数量、编号等只读提示不能自动修正。生成后读取落盘复查；继续下一轮必须明确点击按钮。
5. 自定义时打开“单文档规范与模板”，导入规范、核对摘录、主动解析。按对象编辑，未提及字段须明确选默认/手动/未启用，再确认完整v4模板。旧v2/v3模板升级保留旧值，新增字段全部未启用，明确核对后才能启用。
6. 保存JSON后可重新载入确认，无需再调用AI；保存项目也保留v4规则、来源和新增分类。应用规则/改分类后，旧报告、选择、下载及不匹配预览失效。

间距支持0–72pt（0.5pt步长）或0–3行（0.25行步长），行与磅不互换；未设置不补0。自动/冲突/上下文间距待复核；继承行单位无法安全切为磅值时不改共享样式。对齐读取有效继承；未要求加粗不补true/false，多层切换型加粗保守复核。新对象中文字体限宋/黑/楷/仿宋，西文限TNR/Arial/Calibri；普通文字8–24pt、标题8–36pt（0.5pt步长），倍数1/1.25/1.5/2，首行0/1/2字符。它们是原型边界，不是学校通用取值范围。关键词只处理普通w:t、明确的段首“关键词/Keywords/Key words”及冒号；可安全跨run定位/局部分裂，链接、字段、公式、修订等不能靠分类确认绕过保护。未填手动值须显式采用，不会静默变成未启用。

v4完整模板最大64KB；较长摘录/重复依据超限时须缩小范围，不导出无法重载的模板。检查、修正、复查使用同一确认配置，逐项显示属性和来源。修正不改共享样式，不改摘要内容、关键词标点/词序、文献文字或编号。摘要字数按确认正文的非空白Unicode字符计，含标点/数字，不含标题/关键词；关键词按分号拆分非空项；手工[整数]编号只读，不推广到所有著录类型。

```bash
.venv/bin/python cli.py check samples/academic-errors.docx \
  --mode academic --classification-manifest samples/academic-errors.types.json \
  --report work/my-academic/check.json

.venv/bin/python cli.py fix samples/academic-errors.docx \
  --mode academic --classification-manifest samples/academic-errors.types.json \
  --select R13,R14,R15,R16,R17,R18,R19,R20,R21 \
  --output work/my-academic/fixed.docx --report work/my-academic/changes.json \
  --recheck-report work/my-academic/recheck.json
```

原439项加61项，共500项通过。默认正误样本分别0/18问题、均0待复核；真实浏览器只修1项后剩17，第二轮修17后0/0，下载文件独立复查通过。公开规范B真实DeepSeek调用2次（14.142/14.995秒，各61字段）；实际网页将摘要字号14编辑为13.5，来源记用户确认，91项修改后独立复查0/0；模板重载无新API。详细交付、截图、失败尝试和兼容验收见 [阶段验收记录](outputs/phase15/验收记录.md)。

原稿/对照/默认修正版各2页已用bundled LibreOffice全页查看；Word16.80也打开最终合成原稿及默认修正版，无修复提示、关闭未保存、哈希不变。自定义B在LibreOffice为3页，英文摘要标题位于第1页末而正文起第2页，参考文献正常跨页。**0属性问题不代表可见排版合适**；本轮未自动给摘要标题加相邻属性或移动内容。Word与LibreOffice的主题颜色、换行和分页可能不同。Word观察的具体文件范围及B状态单独记录，不用另一渲染器代替。

## 第十六阶段：确认表格文字及前后置标题相邻

在“单文档扩展检查”中打开“核对表格范围 · 表内文字R23”，主动启用后逐表核对用途：论文内容、封面/表单、其他、待确认。表格编号按主文档顶层XML表格排列，与段落编号独立。明确确认表格范围，再核对段落分类并开始检查。没有启用表格范围时旧单文档仍22条规则；确认范围后另计R23，不改变R01–R22含义。

R23采用学校PDF物理页18“插图（表）的标题和文字：五号，宋体”，本轮解释为**确认的论文内容表格普通中文字体宋体、普通文字字号10.5pt**。西文字体、行距、缩进、对齐等未指定要求不套正文规则。逐个实际XML单元格、段落、普通run检查，合并不通过虚拟网格展开。来源、完整位置和覆盖范围保留在报告中。只修选中的字体槽位/字号，列宽、行高、边框、合并、媒体及内容保持；可能改变换行或高度，应重新核对宽度并主动预览。

直接、常见段落/字符样式以及明确整表样式可读取。首行/分带条件文字格式不能唯一解析时待复核；明确直接属性可以独立判断。默认段落与表格格式优先关系无法可靠确定时不假定Normal胜出。嵌套、浮动、修订、复杂包裹表格本轮不自动处理，未列入普通清单的包裹/文本框表格另有提示；纵向合并续格带文字等异常待复核。公式、链接、字段、上角标等保护保留。正确对照中故意含边界对象，因此“0问题”仍有待复核，不能称整表/全文合格。

新版**v5模板**增加 `table_content__font_cn` 与 `table_content__font_size`：中文宋/黑/楷/仿宋，8–24pt、0.5pt步长。v2–v4保持原值，新表格要求不会静默启用；明确升级v5草稿后新字段为未启用，须人工值/默认/AI提取值明确选择。规范解析只针对明确“表内文字”，不把表题或正文要求写入表格；仍只发送用户确认摘录。模板、表格范围及编辑状态可保存到原有项目包，恢复后重新核对检查，旧版本项目兼容。原有CLI参数和JSON分类兼容；新增范围可作为分类清单的可选 `table_scope`，结构示例见表格样本 `.types.json`。

L03另支持已确认中文摘要标题→中文摘要正文、英文摘要标题→英文摘要正文、参考文献标题→参考文献条目。进入“分页辅助”，核对具体编号和紧接XML对象，只勾选需要的关联，再生成独立副本。只改标题keepNext/keepLines，不跨空段、表格、强制分页或复杂对象，不给后续整个摘要/文献列表连续相连。报告只写“已设置相邻属性”，主动预览后另记可见结果。

样本：`samples/table-text-correct.docx`、`table-text-errors.docx`及对应范围；独立错误清单 `table-text-expected-errors.json`。包含封面、多段单元格、继承、合并、特殊文字、嵌套和条件样式。具体测试、真实浏览器、渲染、Word状态及剩余限制见 [第十六阶段验收记录](outputs/phase16/验收记录.md)。

本轮最终549项自动验收通过（原500+49）。完整样本5问题/9待复核修至0/9；网页只确认普通表2时2→1→0、0待复核；实际v5楷体11.5pt模板12→0，下载独立复查及项目重启恢复通过。本轮AI只做模拟验收，无新真实调用。

指定第十五阶段B在bundled LibreOffice的Abstract由第1页末移至第2页与正文同页；Word16.80也实际查看了该B辅助前后并观察到关键页改善。默认表格副本也用Word打开，无修复提示；v5另行全页渲染但未新增Word查看。不得把这份B的结论套到第六阶段不同B样本，也不保证跨软件一致。修改记录仅写属性设置，视觉结果另存验收记录。

CLI同样可使用样本中的可选表格范围（输出目录请每次更名，拒绝覆盖）：

```bash
.venv/bin/python cli.py check samples/table-text-errors.docx \
  --mode academic --classification-manifest samples/table-text-errors.types.json \
  --report work/my-table-demo/check.json
.venv/bin/python cli.py fix samples/table-text-errors.docx \
  --mode academic --classification-manifest samples/table-text-errors.types.json \
  --select R23 --output work/my-table-demo/fixed.docx \
  --report work/my-table-demo/changes.json \
  --recheck-report work/my-table-demo/recheck.json
```

这份完整样本修后仍有9条待复核；复查有待复核的退出码不是全文通过。`core.inspect_tables`可提供独立表格清单；确认后将绑定输入哈希的table_scope附在原分类清单，检查/修正仍调用原公开接口。项目恢复核对页会列出具体表格用途及R23值；0问题后也可明确使用本轮副本继续，不会因此自动生成新文件。

## 第十七阶段：封面、页眉页脚与页码基础检查

在“单文档扩展检查”中展开 **封面、页眉页脚与页码**，明确启用后才增加R24–R29。旧基础、扩展、R01–R22及R23的原有调用、默认JSON、v2–v5模板保持原含义。最新范围与学校出处见 [第十七阶段覆盖表](outputs/phase17/单文档覆盖表.md)。

1. 上传合成样本 `samples/front-errors.docx` 或正确对照 `front-correct.docx`。先逐个指定封面对象：`p:2`是本样本论文标题，`t:1:1:2:1`是表1/行1/实际格2/段1。程序不按上传文件名套清单；顶层段落编号与表格内定位相互独立。未填写、占位或重复候选只提示核对，不填造姓名、学号等资料。
2. 核对真实分节及关系，为各节指定封面、前置、正文及后置、其他或混合用途。对象范围是XML顺序，不是物理页码。可查看首页/奇偶设置、继承/共享故事、域指令与保存结果。不要为了让检查通过而把混合用途强行改成单一用途。
3. 核对补充配置并点击“已核对封面对象、补充规则与节用途并确认”，再确认段落分类并检查。论文标题学校演示值为黑体二号22pt、加粗、居中；页眉/页脚距离15mm。学校正文页眉居中不直接套前置页眉。未规定的普通页眉/页脚字体字号保持未启用。
4. 在问题中心按“封面论文标题”“封面字段”“节与页眉页脚”筛选。R24逐属性选择；R26分别选择header/footer距离；R27仅支持安全普通文字，选中共享故事会列出全部受影响节，影响未确认或混合用途节时禁止修正。不会自动断链、复制故事或重写字段。
5. 生成新副本后看落盘复查。以本轮副本继续才进入下一轮；不暗中累计修改。R25/R28/R29及打印清单不能被“全选可修正”执行。主动请求预览后另行查看页面与页码；0格式问题不等于页码或全文排版准确。

### 补充模板与规范摘录

采用独立JSON格式 `paper-grid-front-supplement`、`structure_version:1`，与原正文/表格模板组合。可导入、编辑、确认及导出；字段来源与配置哈希单独写入报告和轮次。旧模板不静默增加封面/故事要求。自定义名称不能冒充学校官方规范。

支持封面中文字体宋体/黑体/楷体/仿宋、8–36pt半磅步长、加粗及四种对齐；普通页眉页脚支持上述中文字体、已有三种西文字体、8–24pt及对齐；距离0–50mm。属性缺失保持未启用。`work/phase17/delivery/front-supplement.json`额外以**用户确认值**要求演示前置页眉居中，其他有出处值仍记录学校来源；不是AI实时结果。

可选AI入口只发送用户单独核对的公开规范摘录，最多2000字符；不读取封面个人资料、论文内容或页眉文本。一次按钮最多一个约30秒请求，无自动重试。缺失不补默认，冲突/单位/枚举/范围/原文不符在本地拒绝。解析草稿必须载入编辑并再次确认才生效。本阶段新增字段为模拟响应验收，真实API调用0次；不将手工模板称为AI解析。未采用的AI解析编辑器临时状态不随补充模板导出；已采用的配置、来源及对象/节草稿随项目保存，恢复后仍重新核对检查。

### 页码检查的含义

识别常见简单及平衡复杂PAGE字段、指令、保存结果与可判断字号，读取分节格式、start及连续编号意图；不搜索纯文本“PAGE”冒充域。没有可识别域先待复核，不直接断言真实缺失。PAGE存在、编号设置符合、保存显示、实际渲染页号分别呈现。物理页19要求页脚居中，物理页20要求主体外侧下脚，位置冲突保留人工确认；章标题页眉及1磅横线未完整自动核验。不生成页码，不刷新域，不增删节，不以段落数量推算页码。

### 本轮验收与交付

608项自动验收通过（原549项及新增59项）。范围包含封面普通/单元格定位、后半run及继承、共享故事保护、简单/复杂域、重复修正、配置/文件失效、项目两轮恢复、结果包与会话隔离。自动验收不代替真实浏览器和渲染，具体记录见 [第十七阶段验收](outputs/phase17/验收记录.md)。

- 样本：`samples/front-errors.docx`、`front-correct.docx`、各自`.types.json`及独立`front-expected-errors.json`。短样本只覆盖本轮范围，并非完整学位论文；默认R22仍提示确认的参考文献不足10条，不能将正确对照称作全文合格。
- 副本及报告：`work/phase17/delivery/cover-round1.docx`、`section-round2.docx`、`round1/2-changes.md`、`round1/2-recheck.md`、`independent.json`。
- 真实渲染：错误、对照和修正版各4页，12页逐页查看，输入字节不变。前后观察与实际页码风险见 `work/phase17/visual-qa.md`。混合用途节原有重启“1”保留，不假称已修正连续性。
- Word工具报告Mac锁定，本轮未完成Word实际打开验收，不绕过锁屏。真实课程论文页眉VML/OLE及历史裁切限制保持，不删除、替换或重画。

CLI无需新模式；明确带有`front_scope`的分类清单即可在academic模式执行，旧清单不增加规则。示例输出目录必须不存在：

```bash
.venv/bin/python cli.py check samples/front-errors.docx \
  --mode academic --classification-manifest samples/front-errors.types.json \
  --report work/front-demo/check.json

.venv/bin/python cli.py fix samples/front-errors.docx \
  --mode academic --classification-manifest samples/front-errors.types.json \
  --select R24,R26,R27 --output work/front-demo/fixed.docx \
  --report work/front-demo/changes.json --recheck-report work/front-demo/recheck.json
```

页码/结构仍待复核与R22只读问题会使CLI退出码非0，这是报告状态，不是程序异常。网页启动命令与前阶段相同，仅监听127.0.0.1:8501。本阶段停止，不继续新增领域或部署。

补充模板JSON用于专用导入框，CLI通过分类清单的`front_scope.template`使用；不能把它误当作原`--custom-rules`对象模板。已确认封面对象须与正文/标题分类、论文内容表格R23范围分开；重叠时要求人工核对，程序不自动改分类。旧coverage排除字段描述旧正文类型检查，新对象执行范围另看`front_scope`及`front_limits`。

## 第十八阶段：目录格式与正文对应核对

单文档模式增加**可选**目录范围确认与R30–R32；基础、扩展、旧CLI、旧JSON模板不会静默启用。学校2015材料物理18的目录明确条文：标题黑体18pt、居中、1倍；一级条目黑体14pt、居左、1.5倍；二/三级宋体12pt、居左、1.5倍。范例物理24另记，没有自行增加制表位、点线、缩进、西文字体或段距要求。

操作：

1. 选“单文档扩展检查”，上传待检查DOCX，在“目录范围、层级与补充格式”启用目录。
2. 查看目录候选及结构线索，载入候选为草稿，再按明确对象批量指定标题/一二三级或移出范围。d:N包含内容控件段落；旧顶层段号不变，不是页码。清单每页20个对象，只对明确选中的本页对象应用草稿，之前已经应用的其他页类型保留。模糊条目保持未知级别待复核。
3. 核对完整目录/正文标题范围与覆盖层级。未完整确认不判整篇目录缺项，只列两级不要求三级。与正文/标题分类重叠会显示影响并阻止检查，须在原分类表明确调整，程序不静默移出正文。
4. 按需编辑目录补充配置；空值不检查或修正。自定义支持中文字体宋/黑/楷/仿宋、字号8–36pt（0.5pt步长）、四种对齐、1/1.25/1.5/2倍。确认目录范围/配置，再核对完整段落分类并检查。
5. 问题中心按目录对象查看、选择独立格式属性；生成新副本，读回复查。自动目录域/缓存、超链接、PAGEREF和复杂对象只读，不会出现在可修正选择里。手工目录全部普通run检查，原题序、文字、页码、制表符和点线不改。
6. 对应表每页20条，支持状态和关键词筛选，显示内部目标或有限空白归一的精确文字依据。缺失目标、同名、多候选、文字不同和级别冲突分别说明；自动编号的显示序号不计算。
7. 需要继续时明确点“以本轮修正版开始下一轮”。目录补充模板可单独JSON保存/重载，项目包保留范围、层级、配置、来源、草稿和多轮关系；恢复实际重新检查。结果包含toc-supplement.json及真实报告，HTML/JSON/Markdown区分格式、对应风险及页码未核对。

**实际页码始终另行核对。** 保存数字及PAGEREF不是实际页码证明；格式和宽度等改变后可能需要在Word人工更新。人工更新并保存的DOCX应作为新输入检查，不能复用旧哈希结论。本阶段没有刷新、生成或重建目录。自动目录缓存格式也未修正，避免破坏域/书签/链接，不能把0目录格式问题称作页码正确或全文排版合格。

独立补充格式`paper-grid-toc-supplement`版本1，与旧v2–v5模板组合；新增属性不回填到旧模板。目录字段的AI草稿校验以模拟数据验证，尚未加入实时AI解析按钮；人工编辑/导入后可实际应用，不冒充实时AI。本轮真实API请求0，不发送论文和标题清单。

合成样本、正确对照、独立错误清单见`samples/phase18/`。核心两轮目录6→5→0；浏览器流程同样6→5→0，其他未选项保留。最终**643项验收通过（原608+新增35）**；真实浏览器验证两轮、下载、自动目录只读、层级变更失效、项目冷恢复及继续处理；6份合成文档共6页完成真实LibreOffice渲染目视检查。Word16.80实际打开目录修正版及自动目录，未出现修复提示，并观察首条内部链接跳转；未更新或保存文件，实际页码仍未验收。

启动命令保持：

```bash
cd /Volumes/XD20/Developer/论文有格
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

访问 http://127.0.0.1:8501 。详见[第十八阶段覆盖表](outputs/phase18/单文档覆盖表.md)、[验收记录](outputs/phase18/验收记录.md)、[文件索引](outputs/phase18/文件索引.md)。未做多文档、最终PPT/视频、部署或Git提交推送，完成后等待下一阶段。

目录检查暂时关闭、在未携带目录范围的轮次继续后，重新启用会按新哈希清空旧目录对象，保留补充模板供核对；需要再次选择并确认范围。


## 第十九阶段 正文引文与参考文献核对

新增显式可选R33/R34；旧CLI、默认模板和R01–R32计数语义保持。默认单文档模式仍R01–R22，其他补充规则须明确启用。

1. 单文档扩展模式上传DOCX，核对正文和参考文献条目分类。
2. 展开“正文引文范围与用途”，启用后核对扫描段；分类改变时可明确同步正文范围，旧草稿不会偷偷套新段落。
3. 候选/关系每页20项，可按用途、上下文、编号、状态及段落筛选。明确多选候选后批量设置“确认引文/排除/待确认”。数组等须排除；筛选不等于选中。
4. 核对两项完整范围声明和R33/R34开关，采用草稿、确认引文，再“核对完成并开始检查”。未完整或含复杂编号时不判全文缺失/顺序通过。
5. 问题中心按“正文引文”“引文对应/顺序”筛选。选择具体上标项，生成新副本并读回复查。R34和未引用提示只读，不进入自动修正。
6. 明确进入下一轮处理剩余项。下载DOCX、修改记录、复查、HTML和ZIP；引文补充配置可保存/载入。项目包保留用途、排除、范围、配置和多轮关系，重启后导入并实际重新检查，无需调用AI。

安全可执行语法为ASCII `[1]`单个1–99999正整数；支持run中间、跨多个普通run、重复出现、部分上标及字符样式继承。只设置所选字符的vertAlign，不缩小字号、改字体/编号/文字。组合、区间、全角等保留待复核，不自动转换。含域、链接、书签、修订、公式等段落不拆分；自动编号文献不猜显示编号。R22与R34复用同一手工编号证据；混合自动/手工编号时连续性待复核，明确重复仍报告，不从手工子序列断言全文跳号。

同段普通run字体字号修改与引文拆分要求分轮，并有报告关联提示/事务阻止；先普通格式，再引文。必要拆分后run编号/问题key可能重新定位，通用正文仍保护上标run，因此记录数与待复核可能增加。没有删除未检查项追求清零，独立逐字符比较证明未选属性保持。

引文补充模板结构版本1，与原对象模板及补充模板组合；不改旧模板版本，也不新增AI字段。本模块仅本地处理，不发送论文、引用或文献给API。恢复的历史解析不是新请求。

验收：原643项无回归，最终683项（新增40项）；真实浏览器完成确认/排除、部分修正、下一轮、下载独立复查、范围失效、服务重启恢复及双会话隔离。安全上标4→3→0；复杂域及首次顺序仍保留3条引文待复核。浏览器最终还保留9项未选择的旧格式问题，不能称全文合格。Word16.80实际打开精确最终副本，无修复提示、上标可见；REF保存结果与LibreOffice预览求值差异单独记录，未更新或保存。

[本阶段覆盖与学校出处](outputs/phase19/单文档覆盖表.md) · [验收记录](outputs/phase19/验收记录.md) · [文件与截图索引](outputs/phase19/文件索引.md) · [离线报告](outputs/phase19/report.html)。

启动保持：

```sh
cd /Volumes/XD20/Developer/论文有格
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

访问 http://127.0.0.1:8501 。独立API仍为check_document/fix_document；新范围通过显式classification_manifest.citation_scope传入，候选由core.citations.inventory提供，配置与范围须先严格校验和人工确认。旧调用不启用R33/R34。


## 第二十阶段：左右外侧边框与重复表头

本轮在既有单文档模式中增加可选R35与独立L04，不改变旧R01–R34、默认模板、v2–v5模板或CLI原含义。725项自动验收通过，原683项无回归；范围及真实观察见[覆盖表](outputs/phase20/单文档覆盖表.md)、[验收记录](outputs/phase20/验收记录.md)、[视觉记录](outputs/phase20/视觉记录.md)与[文件索引](outputs/phase20/文件索引.md)。

运行仍为：

```bash
cd /Volumes/XD20/Developer/论文有格
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

1. 选择“单文档扩展检查”，上传DOCX；展开“核对表格范围”。沿用现有用途，明确把需要检查的表设为“论文内容表格”，不选择封面/签字/布局表。
2. 需要时单独启用左右外侧边框R35；查看来源和复杂对象原因。首两行是表头时，填2并查看两行摘要，点击保存辅助草稿。此时尚未修改DOCX。
3. 确认表格用途，再确认分类并检查。在问题中心按“表格左右外侧边框”筛选，分别选择表格的左或右侧；执行确认摘要说明行格影响范围。只选左侧会保留右侧错误，不会删除内部竖线或套三线表。
4. 生成、下载、看落盘复查。继续时明确使用“以本轮修正版开始下一轮”，保留原稿及所有副本。
5. 表头辅助位于“操作区域→分页辅助”。明确选择本次输入，勾选L04，再生成排版副本；L02等其他建议不默认选择。只设置所选连续表头行tblHeader，不改整表keepNext或固定行高。
6. 主动生成原稿/修正版本地预览，选择第2页及后续页人工查看。右侧目标与当前处理输入分别显示，查看预览不会切换输入。重复表头不是续表标题、编号与“（续）”，不代表满足全部续表规范。

补充配置是绑定本文件哈希的table_scope.layout_options v1（version、outer_edges、headers）。旧清单省略它就不启用新功能；网页可导出/载入本文件补充JSON，不能用另一份文件的表格编号绕过核对。项目保存恢复保留表格用途、配置、表头草稿及确认状态，恢复后实际重新检查，不恢复旧任务或假成功预览。结果包附带补充配置和范围。

安全范围：普通顶层矩形表、可确定直接/无条件表格样式继承及LTR边框。条件边框、合并、不规则网格、嵌套、浮动、间距/方向/继承冲突待复核。L04还保护域、复杂对象、强制分页及跨表头边界合并。用户确认不能绕过引擎保护。仅修改明确选择的外侧边框或表头属性，不重建表格，不更改文字、字体、列宽、行高、内部线、编号和关系。

本轮长表在bundled LibreOffice中前后均4页，辅助后第2–4页实际重复两行表头；Word16.80本轮实际打开原稿及最终字节相同副本，第二页同样观察到重复，未出现修复提示、未保存。两环境的分页位置不同，不能互相替代。0边框问题不代表表格整体合格。没有新增AI字段或调用，表格内容不发送外部API。


## 第二十一阶段：Word脚注与尾注正文

新增明确启用的R36脚注、R37尾注，复用原引擎、继承解析和事务保护。原725项无回归，新增47项，共772项验收通过。学校材料物理页16允许页末注/篇末注，物理页18注释正文要求小四宋体、1.5倍；本轮解释到确认的Word对象，不判断注释必要性。详见[覆盖表](outputs/phase21/单文档覆盖表.md)、[验收记录](outputs/phase21/验收记录.md)、[视觉记录](outputs/phase21/视觉记录.md)和[文件索引](outputs/phase21/文件索引.md)。

操作：

1. 保持本地启动方式，选择“单文档扩展检查”，上传`samples/phase21/errors.docx`。
2. 展开“脚注与尾注范围 · 可选”，明确启用。核对类型、ID、引用段落、局部文本和复杂原因；筛选后明确选择本页或当前筛选对象。筛选本身不会选中，系统分隔对象不可选。
3. 在“注释要求与补充配置”核对宋体、12pt、1.5倍，也可分别修改或不启用某属性。中文字体限四种已有字体，字号8–24pt/半磅步长，行距1/1.25/1.5/2倍。编辑后来源为用户确认值；补充JSON可导出重载，不新增AI调用。
4. 点击“已核对注释范围与要求并确认”，再核对整份顶层分类并开始检查。纯注释演示可将6个顶层段落明确设为其他，不能据此声称已检查正文。
5. 问题中心按脚注/尾注、ID关键词和状态筛选。每条字体、字号、行距独立选择；先只修一项，可下载后明确进入下一轮处理其余安全项。复杂/关系异常记录不能加入自动修正。
6. 下载修改记录、复查、离线报告和结果包；主动生成原稿/修正版预览。中断前保存“项目包”，重启后导入、核对恢复并实际重新检查。恢复不再次请求AI，也不恢复旧预览为当前验收。

默认模板、旧CLI、旧项目不自动增加注释规则。程序通过主文档实际包关系、内容类型和对象类型识别，不凭文件名或ID正负猜测。只改普通文字eastAsia、sz或段落行距，不改西文字体、缩进、段距、对齐、自动标记、系统分隔、编号、共享样式及正文。只修改注释部件时主文档字节保持；所选注释部件仅格式白名单变化，其他部件字节保持，报告不再将其混称为所有非主文档部件字节不变。

手工篇末注、括号说明、注释内容正确性和语义未覆盖。域缓存首版整条只读；链接、公式、表格、修订等按安全片段检查，复杂段行距待复核。缺失继承不默认通过。无注释不报缺少注释。格式改动可能改变分页，预览与Word观察独立记录，不保证页数不变。

本轮9项已知注释错误按1+8两轮实际修正，R36/R37问题9→8→0；仍保留链接段2条注释待复核。完整单文档报告还保留未选择处理的R22数量问题及其他未确认章节边界。最终DOCX、独立字节/XML核对和浏览器下载一致，Word16.80实际打开同哈希副本，无修复提示，脚注/尾注导航正常，未保存文件；不是通用Word或学校验收。

## 第二十二阶段：附录、致谢及目录联动

在**单文档扩展检查**中核对“附录标题、附录普通文献文字、致谢标题、致谢普通文字”四类。多个附录只是候选，不自动确认；“详见附录”等句中提及不是章节。批量分类继续按稳定顶层段号操作。

1. 上传`samples/backmatter-errors.docx`，按`samples/backmatter-errors.types.json`核对分类。标题8/15、普通文献文字9/10/17、致谢标题18、普通文字19/20；7是正文，其余按清单排除。
2. 展开“附录特殊材料排除”，明确保护11/12/13/14/16的代码、数据和图表材料。保护范围不能被批量设置普通文字或“恢复初始建议”覆盖；解除须另行确认。
3. 默认R38检查黑体18pt/居中/单倍，R39仅宋体12pt；致谢R40/R41默认未配置。学校原文在PDF物理页19；致谢范例物理页38未给可靠字体标注。附录/致谢按需存在，不判缺项。
4. 可以导入`samples/norm22-B.txt`，核对摘录后点击“解析单文档要求”。新v6按四对象提取，缺失字段明确选默认/人工/未启用。编辑并确认应用后重新核对范围，再检查与选择具体属性。未配置不修正；代码范围说明不是执行授权。
5. v2–v5模板继续可用。编辑器可明确升级v6，新字段初始全部未启用；保存v6重载保留最终值和来源，不再次调用AI。历史解析有明确标签。
6. 目录对应可将已确认附录/致谢标题作为目标；L03只支持紧接且类型匹配的普通文字。标题后代码/空段/表格不能强行相邻。属性落盘后主动预览，不能据此宣称孤行消失。
7. 多轮、项目包、HTML/Markdown/JSON/结果ZIP沿用原入口。更换模板需重新核对目录等补充范围，再确认分类。项目恢复实际重新检查，不恢复旧预览为当前验收。

本轮实际 **817项自动验收**（保留原772项）；真实Chrome已验证部分修正、AI提取后人工编辑、B配置落盘、多轮/L03、目录、模板重载、服务重启项目恢复、范围失效和双会话。两次真实API请求：首次依据校验拒绝，补强位置约束后的明确请求成功；无自动重试。只发送公开合成规范，不发送论文、代码、数据或致谢正文。

最终B的新四对象格式0问题/0待复核；启用目录补充后仍有10项未选目录格式问题、1条“致谢/致 谢”对应待复核，实际页码未核对。原稿、对照、B和L03最终各2页，已真实渲染逐页查看；Word16.80实际打开最终文件，无修复提示、未保存且哈希不变。Word图片在第1页，LibreOffice在第2页，不能互套分页结论；两者中致谢本来已同页，不宣称L03产生可见改善。

[覆盖表](outputs/phase22/单文档覆盖表.md) · [验收](outputs/phase22/验收记录.md) · [视觉](outputs/phase22/视觉记录.md) · [文件索引](outputs/phase22/文件索引.md)


## 第二十三阶段：题注编号与位置

1. 启动网页，选择“单文档扩展检查”，上传论文，核对段落类型。演示可用`samples/phase23/caption-errors.docx`；一级标题、图题和表题建议仍需人工核对。
2. 展开“题注编号、章节与图表关联”，明确启用。核对章号来源；自动编号或无法读取时可手工填写明确章号，不用标题排列顺序代替章号。
3. 编辑本页题注用途/关联，或明确采用本页普通题注与唯一相邻建议；续表、分图、附录编号应标只读/待复核。完整范围是独立声明，未纳入确认的题注不会因勾选完整就变成已检查。
4. 确认题注范围，再“核对完成并开始检查”。编号风险只读；结构位置、实际同页和相邻属性分别展示。筛选不授权修正。
5. 有安全反向紧邻项时进入“题注位置纠正操作”。明确选择，核对唯一移动题注及目标顺序，再授权生成新副本。L05单独一轮，不与普通格式、引文拆分或宽度适配混做。
6. 下载并复查；点击“以本轮修正版开始下一轮”后继续其他项。分类、章号、目录d:N、封面p:N、材料排除及引文偏移经过XML对象身份映射验证；旧选择、计划和不匹配预览失效。原稿与前轮保留。
7. 可导出题注补充配置；既有模板内容不变，旧调用不静默启用R42/R43。保存项目可恢复用途、关联、章号、完整范围及每轮前后范围，恢复后实际重新检查。发生移动或导入检查点后，原稿只用于渲染，不将当前段号套回原稿执行。
8. 主动生成原稿/修正版预览。位置正确不保证同页；修正版仍可单独选择L01/L02，相邻属性也不等于实际同页。

当前只支持普通手工“图1-1 标题”“表 2-3 标题”，明确阿拉伯章号及常见中文1–99章号，或用户1–999章号映射。图/表分开计序；部分/冲突/未解析范围不判完整起始或缺号。SEQ/STYLEREF仅展示指令和保存结果，不求值、改缓存或重编号。

自动位置纠正仅支持同一主文档容器内紧邻的单一普通内嵌图片段/普通非合并顶层表格和独立普通题注；不跨空段、分节、强制分页、书签/域边界，不移动浮动、多图、复杂题注、嵌套/合并表格。不改文字、格式、图片尺寸、表格结构、关系、样式和编号文件。

新公开入口：`core.inspect_captions(path, classification)`；`core.apply_caption_positions(..., mode='academic', classification_manifest=manifest, confirmed_keys=[...])`。原`check_document/fix_document`兼容，只有确认清单显式带`caption_scope`才追加检查。L05有独立精确排列事务，不放宽通用格式白名单。

[覆盖和出处](outputs/phase23/单文档覆盖表.md) · [范围映射](outputs/phase23/范围映射说明.md) · [验收](outputs/phase23/验收记录.md) · [视觉记录](outputs/phase23/视觉记录.md) · [文件索引](outputs/phase23/文件索引.md)。本阶段AI0次；未做最终PPT/视频、部署或提交推送。

# 第45阶段：可公开的实网与离线证据

复用[第44阶段合成输入及独立预期](../phase44/README.md)，未换成更简单的文字。所有请求只包含这些合成/公开文字的有限片段。这里是经过审查的选定回归材料，不是完整work调试目录。

## 实网

- [请求回执及哈希](api-records.json)：实际3次，自动重试0，服务端usage已记录，计费未知；预算由4次经用户追加为20次，未用满。
- [原16字段请求快照](supplement-request.json)、[原始响应封装](supplement-response.json)：实网通过，字段/来源短ID，由本地原校验证明。
- [首次结构请求快照](structure-isolated-request.json)、[原始响应](structure-isolated-response.json)：表2角色content，但多证据ID被旧适配隔离；并非整稿语义失败。
- [修复后的结构请求快照](structure-request.json)、[原始响应](structure-response.json)：表2自动进入处理；小表pending，无编号短标题仍须人工判断。
- [适配前重放记录](structure-replay-before.json)、[适配后重放记录](structure-replay-after.json)：同一份已收响应，0新增API。前后记录明确不能称为两次实网。

这些快照不含HTTP头/密钥/模型思考链。保留实际提示及合成摘录以便精确重放；生产默认不保存此类内容。第44阶段没有原响应，不能拿本阶段响应冒充它的历史重放。

## 浏览器实际下载及独立核对

| 任务 | 实际文件 | 完整结果 | 独立核对 |
| --- | --- | --- | --- |
| 16字段补充 | [修正版](supplement.docx) | [结果包](supplement-result.zip) | [逐字段/原合法路径](supplement-independent.json) |
| 结构识别 | [修正版](structure.docx) | [结果包](structure-result.zip) | [保护对象/原合法路径](structure-independent.json) |

结果包含真实下载的固定文件、规则、范围、修改与复查，不含调试目录或请求内容。两份DOCX与同最终规则/范围/选择的原合法路径同字节。结果包及报告内仍按真实结果保留问题与待复核，不能据此宣称全文合格。

## 网页截图

- [结构实网：集中决定](screenshots/structure-decisions.png)
- [结构实网：下载结果](screenshots/structure-success.png)
- [补充：已收实网响应的离线浏览器重放](screenshots/supplement-offline-replay.png)，0新增API，不冒充新实网截图；与原实网下载字节一致。

截图是实际网页，不是Word/分页验收。未重复渲染已同字节的DOCX。

## 零API复现

```bash
python scripts/reproduce_api_protocol.py --output /tmp/paperfit45-result
python scripts/run_api_replay_browser.py --port 18546
```

在仓库根目录执行。前者禁止所有网络，通过原校验/原合法路径和独立XML脚本核对；后者是明确的实网响应离线重放服务，不注入私有session_state，不读取真实API配置。完整验收与限制见[阶段记录](../../docs/acceptance/phase45.md)。

[未触及规则的独立对照](untouched-rules.json)：原WebSession命令前规则包与实际浏览器结果包比较，排除独立手写16字段后，其余main值/来源及其他模块完全一致。

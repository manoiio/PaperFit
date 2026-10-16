# 第三十六阶段：阅读区证据

仅复用仓库既有合成文件，未新建演示论文、使用真实论文或生成装饰性假页图。截图来自真实Chrome；页面来自本机bundled LibreOffice/Poppler，不是Word验收。

| 同一原稿/规则/范围与第0轮查看目标 | 基线双列页面 | 新阅读区 |
| --- | --- | --- |
| 1280×720 | [改版前](screenshots/before-compare-1280.png) | [单份](screenshots/after-single-1280.png)、[并排](screenshots/after-compare-1280.png) |
| 1440×900 | [改版前](screenshots/before-compare-1440.png) | [单份](screenshots/after-single-1440.png)、[并排](screenshots/after-compare-1440.png) |

上述均为既有内置错误样本、2015默认规则、同6段正文范围、尚无正式输出，原稿/当前输入第0轮。旧版只有双列；基线由`d114176`真实运行页面取得。新旧各自明确生成真实页图，未伪造跨重启缓存。以下为额外实际流程，不能混作同状态对照：

- [实际原稿/第1轮副本](screenshots/after-output-compare-1440.png)：内置样本选择11项、预演采用后两份均实际2页，当前处理输入仍原稿。
- [后台正在运行、已有原稿可看](screenshots/after-task-running.png)：期间实际返回问题和下载，未阻塞其他操作。
- [运行取消语义](screenshots/cancelled-task.png)：停止接收结果，不表示子进程已停止。
- [长文17/16页及前10页边界](screenshots/different-page-counts.png)：400段既有夹具，只有第2段正文参与属性检查；预览仍渲染整个文件。仅选择已有R01后副本16页，未自动更改字号或分页。第17页分别显示超预览范围/不存在。
- [失败原因](screenshots/failed-preview.png)：既有阶段29外部关系保护，本地检查/下载仍可用。
- [独立辅助入口](screenshots/layout-separate.png)：原有L01/L02/L03候选，默认不勾选，明确勾选才允许提交；未自动执行辅助。
- [实际下载与合法路径同字节](independent.json)、[验证数据和文件哈希](evidence.json)。

离线复现既有合法路径，不调用浏览器、AI、渲染器或Word：

```bash
python scripts/reproduce_reader_workflow.py --output /tmp/paperfit36-reader
# 可选：与实际网页下载逐字节比较
python scripts/reproduce_reader_workflow.py --output /tmp/paperfit36-check --download DOWNLOADED.docx
```

输出目录须不存在。实际下载与18个ZIP成员全部一致，预览/翻页前后DOCX哈希保持。目录不含DOCX、页面PDF/独立页图、任务目录、私人路径或密钥；真实运行文件留在本机任务目录，以上命令能从仓库既有样本复现。详见[验收记录](../../docs/acceptance/phase36.md)。

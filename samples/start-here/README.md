# 从两套公开样例开始

所有内容均为公开合成。基础样例不需要Word或API；完整样例复用已保存要求，结构本地可识别，不需API，目录更新/PDF需要本机Word。

- [基础排版：输入、实际修正版、要求与独立清单](basic/使用说明.md)
- [完整整理：输入、实际DOCX、Word PDF与报告](complete/使用说明.md)

想严格不使用API，请选本地精细工作台。智能入口在没有API时仍可处理可靠本地部分；基础样例中的软件声明存在1个歧义候选，配置API后可能分析它，不能宣称必然零API。本阶段智能实测明确停用API，0次付费请求。完整样例本地证据充分，结构请求0次。

生成小型公开ZIP：

    .venv/bin/python scripts/build_starter_pack.py --output work/论文有格_开始使用.zip

只打包清单材料及SHA256，不递归打包仓库。没有.venv、密钥、任务目录、私人论文、浏览器状态或旧授权。PDF/HTML不是任意论文全部合格的证明。

原合法路径复现（显式调用Word，0HTTP）及独立ZIP/XML核对：

    .venv/bin/python scripts/reproduce_delivery.py --output work/本地样例复现 --word
    .venv/bin/python scripts/verify_delivery.py --stages work/本地样例复现

输出目录须不存在。不带--word仅复现基础样例。独立核对不调用格式引擎或新分类器生成预期。

[直接下载公开开始使用ZIP](论文有格_开始使用.zip)；343KB左右，17份公开材料＋哈希清单。不包含本机环境。

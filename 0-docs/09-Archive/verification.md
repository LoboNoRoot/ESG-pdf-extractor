# 整理验收记录

日期：2026-10-28。目标目录：`D:\ESGMiner`。

## 版本选择

两处 ESGMiner RAR 的 SHA-256 均为 `75372E3CCFFF1AD1EF4906871B049F6B2FE99A6659DBF1C0023C106C70E33C8E`，两处爬虫 ZIP 均为 `9A81D28088E10EB6077B9792725D64BBE484421999BA9E8E593AA337DFF7FCCC`。

RAR 解压所得 91 个文件与桌面解压工程逐项一致，无新增、缺失或内容差异。因此选用该共同版本，不依据压缩包日期假定存在更新版本。主工程文件迁入 `2-esg-miner` 后全部保持原内容。

独立爬虫与主工程采集脚本完全一致，SHA-256 为 `2B3FDD5C5947808A5C0E87291362147362AC3B2402250FC5DA1D2044C18D4433`。独立入口改名为 `3-crawler/collect_a_share_esg_reports.py`，仅调整独立爬虫 README 的工作目录和输出路径。

## 完整性

- 251 个源文件全部记录于 migration-manifest.json。
- 240 个文件复制；8 个内容重复来源指向已复制文件；3 个日志/Office 锁文件排除。
- 对全部源文件重新计算哈希，确认桌面原件未改变。
- 对每条迁移记录核验目标文件存在及 SHA-256；修改过的爬虫 README 单独记录目标哈希。
- 14 份 PDF、15 份 XLSX 位于 `1-data/annotations`。
- 初始化本地 Git 仓库；数据、模型凭据、node_modules、构建物、临时产物和报名证明材料设为忽略。未创建提交或远程仓库，未上传资料。

## 运行验证

| 检查 | 结果 |
|---|---|
| 原版完整 pytest | 26 passed |
| 迁移后完整 pytest | 26 passed |
| Python 主工程语法解析 | 通过 |
| CLI --help | 正常列出 scan/run/extract/review/eval/retrieval-eval |
| 真实报告 scan | 55 页，选择 12 页 MinerU 候选，生成扫描与计划文件 |
| 真实报告 extract --no-llm + local 检索 | 162 个 chunks、60 项字段记录、0 次模型调用；无真实模型提取值 |
| FastAPI TestClient | /health、/、/jobs 均返回 200 |
| npm ci | 153 个包安装成功，使用原 package-lock.json |
| npm run build | Vite 8.0.16 构建成功；保留原有大于 500 kB 的 bundle 警告 |

Python 使用既有 Conda esgminer 环境（3.11.16）；Node 24.16.0、npm 11.13.0。

最初系统默认 Python 缺少 openai；改用既有 esgminer 环境解决。首次测试目录权限受限，改用仓库内新临时目录后通过。npm 初次下载受沙箱网络限制（EACCES），获准联网后按锁文件安装成功。这些问题均未通过修改业务代码绕过。

## 验证范围

未执行在线爬虫、收费 LLM/embedding、MinerU 模型推理、PostgreSQL 或 Docker 集成验证；未重新评估字段抽取准确率。测试集分卷仅完成复制哈希核验，未解压验证。历史报告辅助脚本保留原样，可能仍引用桌面路径。

本轮验证支持“目录迁移完整、现有单元测试通过、离线处理及本地前后端入口可用”，不等同于生产部署或模型效果验收。

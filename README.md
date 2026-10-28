# ESGMiner · 智析万卷

面向 ESG 报告的选择性 PDF 解析、60 项指标抽取与人工复核系统。

整理日期：2026-10-28。主工程来自桌面项目的提交代码包，经逐文件核对，解压目录与两份 RAR 内容相同。原版和迁移后均通过 26 项单元测试。

## 目录

| 目录 | 用途 |
|---|---|
| [0-docs](0-docs/README.md) | 导航、运行环境、版本选择和迁移清单 |
| [1-data](1-data/README.md) | 14 份 PDF、15 份标注/模板表格及原始数据分卷包 |
| [2-esg-miner](2-esg-miner/README.md) | 主工程：Python 后端、React 前端、备用静态前端、测试和 Docker |
| [3-crawler](3-crawler/README.md) | 独立运行的报告采集脚本 |
| [8-reference](8-reference/README.md) | 交易所指引、获奖案例和参考文档 |
| [9-project-materials](9-project-materials/README.md) | 项目报告历史、图稿、视频和报名材料 |

## 本机启动

在 PowerShell 中执行：

```powershell
conda activate esgminer
Set-Location D:\ESGMiner\2-esg-miner
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
if (-not (Test-Path .env)) { Copy-Item configs\.env.example .env }
python -m uvicorn esg_selective_mineru.api:app --host 127.0.0.1 --port 8000
```

打开 <http://127.0.0.1:8000>。本地默认 SQLite，无需先启动 PostgreSQL。模型调用需要在 `.env` 中填写自己的密钥；默认目标报告年度为 2024，需要处理其他年度时修改 `TARGET_REPORT_YEAR`。

React 生产页面需在 `2-esg-miner/frontend-react` 执行 `npm ci` 和 `npm run build`。未构建时后端使用自带静态前端。新环境安装、开发和离线检查见 [运行说明](0-docs/06-Environment/README.md)。

所有应用命令从 `2-esg-miner` 执行：其配置读取依赖当前工作目录。`1-data` 存放共享原始数据；应用运行产生的上传、数据库和缓存仍在 `2-esg-miner/data`、`2-esg-miner/output`。

## 版本与资料

主工程内部路径保持原样，避免破坏包导入、配置加载与 Docker 构建。两套前端是现有应用的不同入口，不是重复版本。独立爬虫与主工程内采集脚本内容一致，日常主流程使用主工程内脚本。

桌面源文件保留。历史报告按阶段归档，不把文件名含“最新版”视为已经验证的最终报告。精确来源、内容去重和排除理由见 [迁移清单](0-docs/09-Archive/migration-manifest.json)，验证情况见 [验收记录](0-docs/09-Archive/verification.md)。

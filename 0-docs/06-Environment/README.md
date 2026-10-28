# 环境与运行

本机已存在 `D:\Anaconda3\envs\esgminer\python.exe`，Python 3.11.16。系统默认 Python 来自另一环境，不应直接假定其依赖完整。

## 新环境

```powershell
conda create -n esgminer python=3.11
conda activate esgminer
Set-Location D:\ESGMiner\2-esg-miner
python -m pip install -e .
python -m pip install pytest httpx
if (-not (Test-Path .env)) { Copy-Item configs\.env.example .env }
```

已有本机环境时跳过创建、安装步骤。MinerU 是可选的额外部署，具体要求见主工程 README 和 requirements-mineru.txt；本轮不安装模型或启动 GPU 服务。

## 后端与前端

```powershell
Set-Location D:\ESGMiner\2-esg-miner
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m uvicorn esg_selective_mineru.api:app --host 127.0.0.1 --port 8000
```

另开一个终端开发 React 前端：

```powershell
Set-Location D:\ESGMiner\2-esg-miner\frontend-react
npm ci
npm run dev
```

`npm run build` 生成 dist，后端启动时自动优先选用它。Docker Compose 命令也从 `2-esg-miner` 执行。

## 单元测试

```powershell
Set-Location D:\ESGMiner\2-esg-miner
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m pytest tests -q
```

从仓库根目录运行时，应把 `2-esg-miner` 和 `2-esg-miner/src` 同时加入 PYTHONPATH，测试中的 configs 导入才能解析。

## 离线数据检查

```powershell
Set-Location D:\ESGMiner\2-esg-miner
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$pdf = Get-ChildItem ..\1-data\annotations\*.pdf | Select-Object -First 1
python -m esg_selective_mineru.cli scan $pdf.FullName --output output\sample-scan
$env:RETRIEVER_VECTOR_BACKEND = 'local'
$env:MINERU_LLM_REVIEW_ENABLED = 'false'
python -m esg_selective_mineru.cli extract $pdf.FullName --output output\sample-extract --no-llm
```

`--no-llm` 禁用字段抽取模型，但默认 embedding 检索仍可能访问模型服务，因此离线运行必须同时选择 local 向量后端。这项检查验证链路和文件产出，不代表真实字段准确率。

## 采集新报告

```powershell
Set-Location D:\ESGMiner\2-esg-miner
python scripts\collect_a_share_esg_reports.py --output ..\1-data\a_share_esg_reports --limit 100
python scripts\preprocess_esg_pdfs.py --manifest ..\1-data\a_share_esg_reports\a_share_esg_reports_manifest.csv --output ..\1-data\a_share_esg_reports
```

模型凭据只放在本地 `.env`。本轮未复制任何现成 `.env`，也未调用在线模型服务。

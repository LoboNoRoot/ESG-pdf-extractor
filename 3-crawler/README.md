# A 股 ESG 报告采集脚本说明

本目录为独立爬虫入口；代码与主工程 `2-esg-miner/scripts/collect_a_share_esg_reports.py` 完全一致。为避免分叉，后续修改请同步两个入口。

`collect_a_share_esg_reports.py` 用于从巨潮资讯网检索并下载 A 股上市公司 ESG、社会责任和可持续发展相关 PDF 公告，生成本地 PDF 数据集和清单文件，供后续预处理、MinerU 解析、RAG 检索和 60 字段抽取流程使用。

## 功能概览

- 按关键词调用巨潮资讯公告检索接口。
- 自动翻页检索指定日期范围内的公告。
- 仅保留 PDF 附件，并按公告附件地址去重。
- 下载 PDF 到本地 `raw` 目录。
- 生成 CSV 和 JSON 两份采集清单。
- 支持通过 `--keyword` 追加自定义检索词。
- 支持通过 `--stock` 指定股票代码过滤。

## 环境要求

脚本只使用 Python 标准库，不需要额外安装第三方依赖。

建议在 `D:\ESGMiner\3-crawler` 目录运行：

```powershell
python --version
```

Python 版本建议为 3.9 及以上。

## 快速开始

在 `D:\ESGMiner\3-crawler` 目录执行：

```powershell
python collect_a_share_esg_reports.py `
  --output ..\1-data\a_share_esg_reports `
  --limit 100 `
  --se-date "2023-01-01~2026-12-31"
```

运行完成后会生成：

```text
..\1-data\a_share_esg_reports\
  raw\                                  # 下载的原始 PDF
  a_share_esg_reports_manifest.csv       # CSV 清单
  a_share_esg_reports_manifest.json      # JSON 清单
```

## 常用参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--output` | `../1-data/a_share_esg_reports` | 输出目录。PDF 会写入该目录下的 `raw` 子目录。 |
| `--limit` | `100` | 最多成功下载的报告数量。 |
| `--keyword` | 内置 ESG 相关关键词 | 可重复传入，用于覆盖或扩展检索关键词。 |
| `--se-date` | `2023-01-01~2026-12-31` | 巨潮资讯检索日期范围，格式为 `YYYY-MM-DD~YYYY-MM-DD`。 |
| `--pages` | `20` | 每个关键词最多检索页数。 |
| `--page-size` | `30` | 每页公告数量。 |
| `--sleep` | `0.8` | 请求间隔秒数，用于降低访问频率。 |
| `--stock` | 空字符串 | 指定股票代码过滤，例如 `000001`。 |

## 示例

采集 20 份近年报告：

```powershell
python collect_a_share_esg_reports.py `
  --output ..\1-data\a_share_esg_reports_sample `
  --limit 20 `
  --se-date "2024-01-01~2026-12-31"
```

使用自定义关键词：

```powershell
python collect_a_share_esg_reports.py `
  --output ..\1-data\a_share_esg_reports_custom `
  --limit 50 `
  --keyword "ESG报告" `
  --keyword "可持续发展报告" `
  --keyword "环境、社会和公司治理报告"
```

按单只股票采集：

```powershell
python collect_a_share_esg_reports.py `
  --output ..\1-data\a_share_esg_reports_000001 `
  --stock "000001" `
  --limit 5 `
  --se-date "2021-01-01~2024-12-31"
```

## 清单字段

脚本会为每份成功下载的报告写入以下字段：

| 字段 | 说明 |
| --- | --- |
| `report_id` | 本地报告编号，包含证券代码、公司简称、公告年份和序号。 |
| `sec_code` | 证券代码。 |
| `sec_name` | 证券简称。 |
| `org_id` | 巨潮资讯返回的机构 ID。 |
| `title` | 公告标题。 |
| `announcement_time` | 公告发布时间。 |
| `search_keyword` | 命中该公告的检索关键词。 |
| `pdf_url` | PDF 下载地址。 |
| `local_pdf` | 本地 PDF 路径。 |
| `download_bytes` | 下载文件大小，单位为字节。 |

## 后续处理

采集完成后，可继续运行项目中的 PDF 预处理脚本：

```powershell
python scripts\preprocess_esg_pdfs.py `
  --manifest ..\1-data\a_share_esg_reports\a_share_esg_reports_manifest.csv `
  --output ..\1-data\a_share_esg_reports
```

预处理会生成统一命名 PDF、页级文本、页面扫描结果、MinerU 解析计划、表格候选页和 RAG chunks，供后续抽取流程使用。

## 注意事项

- 巨潮资讯接口和静态文件地址依赖外部网络，网络波动或接口策略变化可能导致下载失败。
- 脚本遇到单个 PDF 下载失败时会打印 `download_failed` 并继续采集下一份报告。
- 如果最终成功数量少于 `--limit`，脚本会以 `only_collected_<数量>_reports` 退出，表示没有采够目标数量。
- 建议保留较小的 `--sleep` 间隔，避免高频请求。
- 采集到的真实报告 PDF 和清单可能包含公司公告原文与下载地址，提交代码时不要把大批量真实数据纳入版本库。

## 整理说明

当前仓库版本已经整理过：

- 默认关键词已恢复为正常中文。
- 已支持 `--stock` 参数，可按股票代码过滤。
- CSV 和 JSON 清单统一使用 `a_share_esg_reports_manifest` 作为文件名前缀。
- 运行结束会输出 `seen_pdf`、`downloaded`、`failed` 和清单路径，便于确认采集结果。

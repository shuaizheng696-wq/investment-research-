# investment-research

投资研究工具库 — Python 脚本集合，覆盖期权扫描、财报分析、行情采集、社交媒体情绪追踪。

## 功能模块

| 脚本 | 功能 | 数据源 |
|------|------|--------|
| `scripts/options_scan.py` | 期权链扫描 — IV、Greeks、Put/Call比、最大持仓 | yfinance |
| `scripts/earnings_analysis.py` | 财报分析 — 财报日历、三大报表、EPS预期 | yfinance + SEC EDGAR |
| `scripts/market_data.py` | 行情采集 — 美股+A股指数、热门个股、宏观指标 | yfinance + akshare |
| `scripts/sentiment_tracker.py` | 情绪追踪 — X/Reddit/StockTwits 讨论热度 | StockTwits + Reddit API |
| `scripts/event_calendar.py` | 事件日历 — FOMC、CPI、非农、财报 | 固定日历 + yfinance |
| `.github/workflows/daily-scan.yml` | 定时自动采集 | GitHub Actions |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行单个模块
python scripts/options_scan.py       # 期权扫描
python scripts/earnings_analysis.py  # 财报分析
python scripts/market_data.py        # 行情采集
python scripts/sentiment_tracker.py  # 情绪追踪
python scripts/event_calendar.py     # 事件日历
```

## 自动采集

GitHub Actions 配置为**周一至周五 UTC 00:00（北京时间早8点）**自动运行所有脚本，数据自动提交到仓库。

## 目录结构

```
investment-research/
├── scripts/              # Python 脚本
├── data/                 # 采集的数据
│   ├── daily-market/     # 每日行情快照
│   ├── options/          # 期权链数据
│   ├── earnings/         # 财报数据
│   ├── sentiment/        # 情绪数据
│   └── events/           # 事件日历
├── .github/workflows/    # GitHub Actions
├── requirements.txt      # Python 依赖
└── README.md
```

## 与 WorkBuddy 配合

- **GitHub Actions** → 定时采集原始数据，存入仓库
- **WorkBuddy 自动化** → AI 分析数据，生成可读报告（`outputs/` 目录）
- **GitHub 仓库** → 版本历史，数据可追溯

## 许可

MIT

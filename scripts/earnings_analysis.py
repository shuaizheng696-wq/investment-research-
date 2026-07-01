"""
Earnings & Financial Report Analyzer
=====================================
从SEC EDGAR获取10-K/10-Q财报，解析关键财务指标

美股: edgartools (10-K, 10-Q, 8-K)
A股: akshare (东方财富/新浪财报)

输出: data/earnings/{ticker}-{date}.json
       reports/earnings/{ticker}-analysis-{date}.md
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    from edgar import Company, set_identity
    set_identity("investment-research@github.com")
except ImportError:
    pass

# ===== 配置 =====
WATCHLIST = [
    "AAPL", "NVDA", "MSFT", "TSLA", "META",
    "GOOGL", "AMZN", "AMD", "INTC", "NFLX",
]

EARNINGS_OUTPUT = Path(__file__).parent.parent / "data" / "earnings"
REPORT_OUTPUT = Path(__file__).parent.parent / "reports" / "earnings"


def get_upcoming_earnings(ticker: str) -> dict:
    """获取即将发布的财报信息"""
    stock = yf.Ticker(ticker)
    info = stock.info

    result = {
        "ticker": ticker,
        "company_name": info.get("longName", ticker),
        "current_price": info.get("regularMarketPreviousClose"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "earnings_date": None,
        "earnings_estimate": None,
        "revenue_estimate": None,
    }

    # 从calendar获取财报日期
    try:
        calendar = stock.calendar
        if calendar is not None:
            earnings_dates = calendar.get("Earnings Date", [])
            if len(earnings_dates) > 0:
                result["earnings_date"] = str(earnings_dates[0])
            result["earnings_low"] = calendar.get("Earnings Low")
            result["earnings_high"] = calendar.get("Earnings High")
            result["earnings_average"] = calendar.get("Earnings Average")
    except Exception:
        pass

    return result


def get_financial_statements(ticker: str) -> dict:
    """获取最近几期的财务报表数据"""
    stock = yf.Ticker(ticker)

    result = {"ticker": ticker}

    try:
        # 利润表
        income = stock.income_stmt
        if income is not None and not income.empty:
            result["income_statement"] = _clean_df(income)

        # 资产负债表
        balance = stock.balance_sheet
        if balance is not None and not balance.empty:
            result["balance_sheet"] = _clean_df(balance)

        # 现金流量表
        cashflow = stock.cashflow
        if cashflow is not None and not cashflow.empty:
            result["cashflow"] = _clean_df(cashflow)

    except Exception as e:
        result["error"] = str(e)

    return result


def _clean_df(df: pd.DataFrame) -> dict:
    """清理DataFrame并转为字典"""
    # 取最近4期
    recent = df.iloc[:, :4]
    return recent.to_dict()


def generate_report(ticker: str) -> str:
    """生成财报分析报告"""
    lines = []

    # 基本信息
    info = get_upcoming_earnings(ticker)
    name = info.get("company_name", ticker)
    price = info.get("current_price")
    market_cap = info.get("market_cap")
    pe = info.get("pe_ratio")

    lines.append(f"## {name} ({ticker}) 财报分析")
    lines.append(f"> 数据时间: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")

    if price:
        lines.append(f"**现价**: ${price:.2f}")
    if market_cap:
        cap_b = market_cap / 1e9
        lines.append(f"**市值**: ${cap_b:.1f}B")
    if pe:
        lines.append(f"**PE(TTM)**: {pe:.2f}")

    # 财报日期
    earnings_date = info.get("earnings_date")
    if earnings_date:
        lines.append(f"\n### 财报日历")
        lines.append(f"**下次财报**: {earnings_date}")
        low = info.get("earnings_low")
        high = info.get("earnings_high")
        avg = info.get("earnings_average")
        if avg:
            lines.append(f"**EPS预期**: ${avg:.2f} (范围: ${low:.2f} - ${high:.2f})")

    # 财务数据
    financials = get_financial_statements(ticker)
    if "error" in financials:
        lines.append(f"\n⚠️ 财务报表获取失败: {financials['error']}")
    else:
        income = financials.get("income_statement", {})
        if income:
            lines.append(f"\n### 利润表 (最近4期)")
            # 提取关键指标
            for key_col in income:
                for metric, val in income[key_col].items():
                    if metric in ["Total Revenue", "Gross Profit", "EBITDA", "Net Income"]:
                        val_str = f"${val/1e9:.2f}B" if val and val > 1e9 else f"${val/1e6:.0f}M"
                        lines.append(f"- {metric}: {val_str}")

    return "\n".join(lines)


def scan_all():
    """扫描所有关注股的财报信息"""
    today = datetime.now().strftime("%Y-%m-%d")
    EARNINGS_OUTPUT.mkdir(parents=True, exist_ok=True)
    REPORT_OUTPUT.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  财报分析扫描 — {today}")
    print(f"{'='*60}")

    # 先找近期有财报的
    upcoming = []
    for ticker in WATCHLIST:
        info = get_upcoming_earnings(ticker)
        upcoming.append(info)
        if info.get("earnings_date"):
            print(f"  📅 {ticker}: {info['earnings_date']}")
        else:
            print(f"  ⚪ {ticker}: 近期无财报")

    # 保存扫描结果
    scan_file = EARNINGS_OUTPUT / f"earnings-calendar-{today}.json"
    with open(scan_file, "w", encoding="utf-8") as f:
        json.dump(upcoming, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 财报日历已保存: {scan_file}")

    # 找出未来30天内要发财报的
    import datetime as dt
    urgent = []
    for item in upcoming:
        if item.get("earnings_date"):
            try:
                ed = item["earnings_date"]
                if isinstance(ed, (int, float)):
                    ed = dt.datetime.fromtimestamp(ed)
                else:
                    ed = pd.Timestamp(ed).to_pydatetime()
                days_left = (ed - dt.datetime.now()).days
                item["days_to_earnings"] = days_left
                if 0 <= days_left <= 30:
                    urgent.append(item)
            except Exception:
                pass

    if urgent:
        print(f"\n⚠️  {len(urgent)} 只股票未来30天内有财报:")
        for item in urgent:
            print(f"  🔴 {item['ticker']} — {item['days_to_earnings']}天后")


if __name__ == "__main__":
    scan_all()

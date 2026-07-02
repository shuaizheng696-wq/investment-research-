"""
Options Chain Scanner
=====================
扫描美股/港股期权链，输出关键指标：行权价、IV、Greeks、成交量、持仓量

数据源: yfinance (Yahoo Finance)
输出: data/options/{ticker}-{date}.csv
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path

import yfinance as yf
import pandas as pd
import math

# ===== 配置 =====
# 要扫描的股票列表
WATCHLIST = [
    "AAPL", "NVDA", "MSFT", "TSLA", "META",
    "GOOGL", "AMZN", "AMD", "INTC", "NFLX",
]

# 输出目录
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "options"

# 扫描范围：最近N个到期日
MAX_EXPIRIES = 3


def scan_options_chain(ticker: str) -> dict:
    """扫描单只股票的期权链"""
    print(f"  [*] 扫描 {ticker} ...")

    try:
        stock = yf.Ticker(ticker)
        expiries = stock.options

        if not expiries:
            print(f"  [!] {ticker} 没有期权数据")
            return {"ticker": ticker, "error": "无期权数据"}

        # 取最近N个到期日
        selected = expiries[:MAX_EXPIRIES]

        results = {
            "ticker": ticker,
            "fetched_at": datetime.now().isoformat(),
            "underlying_price": None,
            "expiries": {},
        }

        # 获取标的价格
        info = stock.info
        results["underlying_price"] = info.get("regularMarketPreviousClose")

        for expiry in selected:
            try:
                chain = stock.option_chain(expiry)

                def process_df(df, option_type):
                    """处理期权链DataFrame，提取关键字段"""
                    if df.empty:
                        return []

                    # 标准化列名
                    col_map = {
                        "strike": "strike",
                        "lastPrice": "lastPrice",
                        "bid": "bid",
                        "ask": "ask",
                        "volume": "volume",
                        "openInterest": "openInterest",
                        "impliedVolatility": "IV",
                    }

                    records = []
                    for _, row in df.iterrows():
                        rec = {
                            "strike": row.get("strike"),
                            "last": row.get("lastPrice"),
                            "bid": row.get("bid"),
                            "ask": row.get("ask"),
                            "volume": row.get("volume"),
                            "openInterest": row.get("openInterest"),
                            "IV": row.get("impliedVolatility"),
                        }
                        rec["type"] = option_type
                        records.append(rec)
                    return records

                calls = process_df(chain.calls, "call")
                puts = process_df(chain.puts, "put")

                # 计算 Put/Call 比率
                pc_ratio = None
                pc_vol = sum(r["volume"] for r in puts if r["volume"] is not None)
                call_vol = sum(r["volume"] for r in calls if r["volume"] is not None)
                if call_vol and call_vol > 0:
                    pc_ratio = round(pc_vol / call_vol, 3)

                # 找出成交量最大的行权价
                all_records = calls + puts
                max_vol = max(all_records, key=lambda x: x["volume"] or 0)

                results["expiries"][expiry] = {
                    "days_to_expiry": (datetime.strptime(expiry, "%Y-%m-%d") - datetime.now()).days,
                    "calls_count": len(calls),
                    "puts_count": len(puts),
                    "put_call_ratio": pc_ratio,
                    "max_volume": max_vol,
                    "calls": calls,
                    "puts": puts,
                }

            except Exception as e:
                results["expiries"][expiry] = {"error": str(e)}

        return results

    except Exception as e:
        print(f"  [!] {ticker} 扫描失败: {e}")
        return {"ticker": ticker, "error": str(e)}


def safe_int(val, default=0):
    """安全转换数值为int，处理NaN"""
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


def safe_float(val, default=None):
    """安全转换数值为float，处理NaN"""
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def analyze_and_summarize(results: dict) -> str:
    """生成可读摘要"""
    lines = []

    ticker = results.get("ticker", "?")
    price = results.get("underlying_price")
    error = results.get("error")

    if error:
        return f"### {ticker} — 数据获取失败: {error}\n"

    if price is not None and not (isinstance(price, float) and math.isnan(price)):
        lines.append(f"### {ticker} — 现价 ${price:.2f}")
    else:
        lines.append(f"### {ticker}")

    for expiry, exp_data in results.get("expiries", {}).items():
        if "error" in exp_data:
            lines.append(f"  - {expiry}: {exp_data['error']}")
            continue

        dte = exp_data.get("days_to_expiry", "?")
        pc = exp_data.get("put_call_ratio", "N/A")
        max_vol = exp_data.get("max_volume", {})

        lines.append(f"  **{expiry}** ({dte}天到期) | P/C Ratio: {pc}")
        if max_vol.get("strike"):
            strike = safe_float(max_vol.get("strike"))
            vol = safe_int(max_vol.get("volume"))
            oi = safe_int(max_vol.get("openInterest"))
            iv = max_vol.get("IV", "N/A")
            lines.append(
                f"    最大成交量: {max_vol['type']} @ ${strike:.1f} "
                f"(成交量: {vol}, 持仓: {oi}, IV: {iv})"
            )

    return "\n".join(lines) + "\n"


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_summaries = []
    all_details = {}

    print(f"\n{'='*60}")
    print(f"  期权链扫描 — {today}")
    print(f"{'='*60}")

    for ticker in WATCHLIST:
        results = scan_options_chain(ticker)
        all_details[ticker] = results
        summary = analyze_and_summarize(results)
        all_summaries.append(summary)
        time.sleep(1)  # 礼貌等待，避免被限速

    # 保存详细数据 (JSON)
    detail_file = OUTPUT_DIR / f"options-detail-{today}.json"
    with open(detail_file, "w", encoding="utf-8") as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 详细数据已保存: {detail_file}")

    # 保存摘要 (Markdown)
    summary_file = OUTPUT_DIR / f"options-summary-{today}.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(f"# 期权链扫描 — {today}\n\n")
        f.write("\n".join(all_summaries))
    print(f"✅ 摘要已保存: {summary_file}")

    # 输出到stdout（供GitHub Actions日志查看）
    print("\n" + "="*60)
    print("\n".join(all_summaries))


if __name__ == "__main__":
    main()

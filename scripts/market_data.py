"""
Market Data Collector
=====================
采集美股+A股每日行情快照、指数数据、宏观经济指标

美股: yfinance
A股: akshare
宏观: yfinance + WebFetch

输出: data/daily-market/{date}.json
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import akshare as ak
except ImportError:
    ak = None

# ===== 配置 =====
# 美股指数
US_INDICES = {
    "^GSPC": "标普500",
    "^IXIC": "纳斯达克",
    "^DJI": "道琼斯",
}

# 美股热门个股
US_TICKERS = [
    "AAPL", "NVDA", "MSFT", "TSLA", "META",
    "GOOGL", "AMZN", "AMD", "INTC", "NFLX",
]

# A股指数
CN_INDICES = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
}

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "daily-market"


def collect_us_market() -> dict:
    """采集美股数据"""
    print("  [*] 采集美股数据...")

    result = {
        "fetched_at": datetime.now().isoformat(),
        "indices": {},
        "tickers": {},
    }

    # 指数
    for symbol, name in US_INDICES.items():
        try:
            idx = yf.Ticker(symbol)
            info = idx.info
            history = idx.history(period="5d")

            result["indices"][symbol] = {
                "name": name,
                "price": info.get("regularMarketPrice") or info.get("regularMarketPreviousClose"),
                "change": info.get("regularMarketChange"),
                "change_pct": info.get("regularMarketChangePercent"),
                "5d_change_pct": None,
            }

            # 计算5日涨跌幅
            if not history.empty:
                close_series = history["Close"]
                if len(close_series) >= 2:
                    pct = (close_series.iloc[-1] - close_series.iloc[0]) / close_series.iloc[0] * 100
                    result["indices"][symbol]["5d_change_pct"] = round(pct, 2)

        except Exception as e:
            result["indices"][symbol] = {"name": name, "error": str(e)}

    # 个股
    for ticker in US_TICKERS:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            result["tickers"][ticker] = {
                "name": info.get("longName") or info.get("shortName", ticker),
                "price": info.get("regularMarketPrice") or info.get("regularMarketPreviousClose"),
                "change_pct": info.get("regularMarketChangePercent"),
                "market_cap": info.get("marketCap"),
                "pe": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "volume": info.get("regularMarketVolume"),
                "avg_volume": info.get("averageVolume"),
                "volume_ratio": None,
            }

            # 量比
            vol = info.get("regularMarketVolume")
            avg_vol = info.get("averageVolume")
            if vol and avg_vol and avg_vol > 0:
                result["tickers"][ticker]["volume_ratio"] = round(vol / avg_vol, 2)

        except Exception as e:
            result["tickers"][ticker] = {"error": str(e)}

    return result


def collect_cn_market() -> dict:
    """采集A股数据"""
    print("  [*] 采集A股数据...")

    result = {"fetched_at": datetime.now().isoformat(), "indices": {}}

    if ak is None:
        result["error"] = "akshare未安装"
        return result

    for symbol, name in CN_INDICES.items():
        try:
            # 上证
            if symbol.startswith("sh"):
                df = ak.stock_zh_index_daily(symbol="sh000001")
            elif symbol.startswith("sz"):
                df = ak.stock_zh_index_daily(symbol="sz399001")

            if not df.empty:
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) >= 2 else None

                change = None
                pct_change = None
                if prev is not None:
                    change = round(float(latest.get("close", 0)) - float(prev.get("close", 0)), 2)
                    pct_change = round(change / float(prev["close"]) * 100, 2)

                result["indices"][symbol] = {
                    "name": name,
                    "date": str(latest.get("date", "")),
                    "price": float(latest.get("close", 0)),
                    "open": float(latest.get("open", 0)),
                    "high": float(latest.get("high", 0)),
                    "low": float(latest.get("low", 0)),
                    "volume": int(latest.get("volume", 0)),
                    "change": change,
                    "change_pct": pct_change,
                }

        except Exception as e:
            result["indices"][symbol] = {"name": name, "error": str(e)}

    return result


def collect_macro_data() -> dict:
    """采集宏观经济指标"""
    print("  [*] 采集宏观数据...")

    result = {}

    # 用几个关键ETF反推宏观情绪
    macro_symbols = {
        "^VIX": "VIX恐慌指数",
        "^TNX": "10年期美债收益率",
        "DX-Y.NYB": "美元指数",
    }

    for symbol, name in macro_symbols.items():
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            result[symbol] = {
                "name": name,
                "value": info.get("regularMarketPrice") or info.get("regularMarketPreviousClose"),
                "previous_close": info.get("regularMarketPreviousClose"),
            }
        except Exception:
            result[symbol] = {"name": name, "error": "获取失败"}

    return result


def generate_summary(us_data: dict, cn_data: dict, macro_data: dict) -> str:
    """生成每日摘要Markdown"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# 每日市场数据 — {today}", ""]

    # 美股指数
    lines.append("## 美股指数")
    lines.append("")
    for symbol, data in us_data.get("indices", {}).items():
        n = data.get("name", symbol)
        p = data.get("price")
        cp = data.get("change_pct")
        if p:
            arrow = "🔴" if cp and cp >= 0 else "🟢"
            lines.append(f"- {arrow} **{n}**: {p:.2f} ({cp:+.2f}%)")
        else:
            lines.append(f"- {n}: 数据获取失败")

    # A股指数
    lines.append("")
    lines.append("## A股指数")
    lines.append("")
    for symbol, data in cn_data.get("indices", {}).items():
        n = data.get("name", symbol)
        p = data.get("price")
        cp = data.get("change_pct")
        if p:
            arrow = "🔴" if cp and cp >= 0 else "🟢"
            lines.append(f"- {arrow} **{n}**: {p:.2f} ({cp:+.2f}%)")
        else:
            lines.append(f"- {n}: 数据获取失败")

    # 宏观
    lines.append("")
    lines.append("## 宏观指标")
    lines.append("")
    for symbol, data in macro_data.items():
        n = data.get("name", symbol)
        v = data.get("value")
        lines.append(f"- **{n}**: {v}" if v else f"- **{n}**: 获取失败")

    # 热门个股
    lines.append("")
    lines.append("## 美股热门个股")
    lines.append("")
    for ticker, data in us_data.get("tickers", {}).items():
        if "error" in data:
            lines.append(f"- {ticker}: 获取失败")
            continue
        name = data.get("name", ticker)
        price = data.get("price")
        change = data.get("change_pct")
        pe = data.get("pe")
        vol_ratio = data.get("volume_ratio")
        arrow = "🔴" if change and change >= 0 else "🟢"
        info_parts = [f"{arrow} **{name} ({ticker})**: ${price:.2f} ({change:+.2f}%)"]
        if pe:
            info_parts.append(f"PE: {pe:.1f}")
        if vol_ratio:
            info_parts.append(f"量比: {vol_ratio}")
        lines.append("- " + " | ".join(info_parts))

    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'='*60}")
    print(f"  市场数据采集 — {today}")
    print(f"{'='*60}")

    # 采集美股
    us_data = collect_us_market()

    # 采集A股
    cn_data = collect_cn_market()

    # 采集宏观数据
    macro_data = collect_macro_data()

    # 合并保存
    all_data = {
        "date": today,
        "us": us_data,
        "cn": cn_data,
        "macro": macro_data,
    }

    data_file = OUTPUT_DIR / f"daily-{today}.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 数据已保存: {data_file}")

    # 生成摘要
    summary = generate_summary(us_data, cn_data, macro_data)
    summary_file = OUTPUT_DIR / f"summary-{today}.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"✅ 摘要已保存: {summary_file}")

    print("\n" + summary)


if __name__ == "__main__":
    main()

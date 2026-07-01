"""
Event Calendar Tracker
======================
追踪未来经济事件、财报发布、FOMC会议等重要日期

数据源:
- yfinance earnings calendar
- akshare 经济日历
- FOMC Calendar (网页抓取)

输出: data/events/{date}.json
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

# 关注股票列表
WATCHLIST = [
    "AAPL", "NVDA", "MSFT", "TSLA", "META",
    "GOOGL", "AMZN", "AMD", "INTC", "NFLX",
]

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "events"

# 已知的2026年FOMC会议日期
FOMC_DATES_2026 = [
    "2026-01-28", "2026-03-18", "2026-05-06",
    "2026-06-17", "2026-07-29", "2026-09-16",
    "2026-11-04", "2026-12-15",
]


def get_fomc_calendar() -> list:
    """获取FOMC会议日历"""
    now = datetime.now()
    upcoming = []
    for date_str in FOMC_DATES_2026:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        days_left = (dt - now).days
        if days_left >= 0:
            upcoming.append({
                "date": date_str,
                "event": "FOMC 议息会议",
                "days_left": days_left,
                "importance": "high",
            })
    return sorted(upcoming, key=lambda x: x["days_left"])


def get_key_economic_events() -> list:
    """返回关键经济事件周期（固定日历）"""
    now = datetime.now()
    events = []

    # CPI发布（月中，约13号）
    for month_offset in range(3):
        target = now.replace(day=13) + timedelta(days=30 * month_offset)
        target = target.replace(day=13)
        days_left = (target - now).days
        if days_left >= 0:
            events.append({
                "date": target.strftime("%Y-%m-%d"),
                "event": "CPI 消费者价格指数 (预估)",
                "days_left": days_left,
                "importance": "high",
            })

    # 非农数据（每月第一个周五）
    for month_offset in range(3):
        target = now.replace(day=1) + timedelta(days=30 * month_offset)
        while target.weekday() != 4:  # Friday
            target += timedelta(days=1)
        days_left = (target - now).days
        if days_left >= 0:
            events.append({
                "date": target.strftime("%Y-%m-%d"),
                "event": "非农就业数据",
                "days_left": days_left,
                "importance": "high",
            })

    # GDP发布（季末后约1个月）
    for month_offset in [1, 4, 7, 10]:
        target = now.replace(month=month_offset % 12 + 1, day=28) if month_offset < 12 else now
        # 简化处理
        pass

    # 去重并排序
    seen = set()
    unique = []
    for e in events:
        key = (e["date"], e["event"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return sorted(unique, key=lambda x: x["days_left"])[:15]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'='*60}")
    print(f"  事件日历 — {today}")
    print(f"{'='*60}")

    result = {
        "date": today,
        "fetched_at": datetime.now().isoformat(),
        "events": [],
        "earnings": [],
    }

    # FOMC
    print("\n[*] FOMC 会议日历...")
    fomc = get_fomc_calendar()
    result["events"].extend(fomc)
    for e in fomc:
        print(f"  🏛️  {e['date']}: {e['event']} ({e['days_left']}天后)")

    # 经济事件
    print("\n[*] 关键经济事件...")
    econ = get_key_economic_events()
    for e in econ:
        if e["event"] not in [x["event"] for x in result["events"]]:
            result["events"].append(e)
            emoji = "📊" if "CPI" in e["event"] else "💼"
            print(f"  {emoji} {e['date']}: {e['event']} ({e['days_left']}天后)")

    # 财报日历
    print("\n[*] 财报日历...")
    import yfinance as yf
    for ticker in WATCHLIST:
        try:
            stock = yf.Ticker(ticker)
            calendar = stock.calendar
            if calendar is not None:
                earnings_date = calendar.get("Earnings Date", [None])
                date_val = earnings_date[0] if len(earnings_date) > 0 else None
                if date_val:
                    result["earnings"].append({
                        "ticker": ticker,
                        "earnings_date": str(date_val),
                        "eps_estimate": calendar.get("Earnings Average"),
                    })
                    print(f"  📅 {ticker}: {date_val}")
        except Exception as e:
            print(f"  ❌ {ticker}: {e}")

    # 保存
    output_file = OUTPUT_DIR / f"events-{today}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 事件日历已保存: {output_file}")

    # 生成摘要
    summary_lines = [f"# 经济事件日历 — {today}", ""]
    summary_lines.append("## 近期重要事件")
    for e in result["events"][:10]:
        emoji = "🔴" if e["days_left"] <= 7 else "🟡"
        summary_lines.append(f"- {emoji} **{e['date']}**: {e['event']} ({e['days_left']}天后)")

    summary_lines.append("\n## 近期财报")
    for e in result["earnings"]:
        summary_lines.append(f"- 📅 **{e['ticker']}**: {e['earnings_date']} (EPS预期: ${e.get('eps_estimate', 'N/A')})")

    summary = "\n".join(summary_lines)
    summary_file = OUTPUT_DIR / f"events-summary-{today}.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)

    print("\n" + summary)


if __name__ == "__main__":
    main()

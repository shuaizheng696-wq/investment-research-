#!/usr/bin/env python3
"""
经济事件日历脚本
- 从 Investing.com 抓取全球经济事件（FOMC/CPI/非农等）
- 使用 investpy 或 akshare 获取经济日历
- 输出到 data/calendar/ 目录
"""

import json
import os
from datetime import datetime, timedelta

try:
    import investpy
    INVESTPY_AVAILABLE = True
except ImportError:
    INVESTPY_AVAILABLE = False
    print("⚠️ investpy 未安装，尝试使用 akshare")

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("⚠️ akshare 未安装")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "calendar")


def get_economic_calendar_investpy(days_ahead: int = 7) -> list:
    """使用 investpy 获取经济日历"""
    if not INVESTPY_AVAILABLE:
        return []

    events = []
    try:
        # 获取未来 N 天的经济日历
        from_date = datetime.now().strftime("%d/%m/%Y")
        to_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%d/%m/%Y")
        
        calendar = investpy.news.economic_calendar(
            from_date=from_date,
            to_date=to_date,
        )
        
        # 转换为字典列表
        for _, row in calendar.iterrows():
            events.append({
                "date": str(row.get("date", "")),
                "time": str(row.get("time", "")),
                "zone": str(row.get("zone", "")),
                "event": str(row.get("event", "")),
                "importance": str(row.get("importance", "")),
                "actual": str(row.get("actual", "")),
                "forecast": str(row.get("forecast", "")),
                "previous": str(row.get("previous", "")),
            })
        
        print(f"  ✅ 通过 investpy 获取到 {len(events)} 个经济事件")
        
    except Exception as e:
        print(f"  ⚠️ investpy 获取失败: {e}")
    
    return events


def get_economic_calendar_akshare(days_ahead: int = 7) -> list:
    """使用 akshare 获取经济日历（中国+全球）"""
    if not AKSHARE_AVAILABLE:
        return []

    events = []
    try:
        # 获取财经日历
        df = ak.tool_trade_date_hist_sina()
        
        # akshare 还有其他经济日历接口
        # 尝试获取全球重要经济事件
        try:
            # 获取美联储重要事件（通过新闻API间接获取）
            news_df = ak.stock_news_em(symbol="美联储")
            if not news_df.empty:
                for _, row in news_df.head(10).iterrows():
                    events.append({
                        "date": str(row.get("发布时间", "")),
                        "event": f"美联储相关: {row.get('新闻标题', '')}",
                        "source": "akshare",
                    })
        except Exception as e:
            print(f"  ⚠️ akshare 新闻获取失败: {e}")
        
        print(f"  ✅ 通过 akshare 获取到 {len(events)} 个事件")
        
    except Exception as e:
        print(f"  ⚠️ akshare 获取失败: {e}")
    
    return events


def get_important_events() -> list:
    """
    手动维护重要事件列表（FOMC/CPI/非农等）
    这些是市场最重要的事件，优先追踪
    """
    # 2026年重要事件（需要手动更新）
    important_events = [
        {"date": "2026-07-30", "event": "FOMC利率决议", "importance": "高"},
        {"date": "2026-07-30", "event": "美国Q2 GDP初值", "importance": "高"},
        {"date": "2026-08-01", "event": "非农就业数据", "importance": "高"},
        {"date": "2026-08-13", "event": "美国CPI数据", "importance": "高"},
        {"date": "2026-09-17", "event": "FOMC利率决议", "importance": "高"},
    ]
    
    # 过滤掉已过期的事件
    today = datetime.now().date()
    upcoming = [
        e for e in important_events
        if datetime.strptime(e["date"], "%Y-%m-%d").date() >= today
    ]
    
    return upcoming


def run_calendar_collection() -> dict:
    """主函数：收集经济事件日历"""
    print("📅 开始收集经济事件日历...")
    
    results = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "sources": {},
        "important_events": [],
        "upcoming_7days": [],
    }
    
    # 方法1: investpy
    if INVESTPY_AVAILABLE:
        print("\n📊 方法1: investpy")
        events = get_economic_calendar_investpy(days_ahead=7)
        results["sources"]["investpy"] = events
    
    # 方法2: akshare
    if AKSHARE_AVAILABLE:
        print("\n📊 方法2: akshare")
        events = get_economic_calendar_akshare(days_ahead=7)
        results["sources"]["akshare"] = events
    
    # 重要事件
    results["important_events"] = get_important_events()
    
    # 统计未来7天的重要事件
    today = datetime.now().date()
    all_events = []
    for source, events in results["sources"].items():
        all_events.extend(events)
    
    for event in all_events:
        try:
            event_date = datetime.strptime(event.get("date", ""), "%Y-%m-%d").date()
            if 0 <= (event_date - today).days <= 7:
                results["upcoming_7days"].append(event)
        except:
            pass
    
    return results


def save_results(results: dict):
    """保存结果到文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 保存 JSON
    json_path = os.path.join(OUTPUT_DIR, f"calendar-{date_str}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 JSON 已保存: {json_path}")
    
    # 保存可读报告
    md_path = os.path.join(OUTPUT_DIR, f"calendar-{date_str}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 经济事件日历 — {date_str}\n\n")
        
        # 重要事件（优先显示）
        if results["important_events"]:
            f.write("## 🔥 重点关注事件\n\n")
            for event in results["important_events"]:
                f.write(f"### {event['date']} - {event['event']}\n")
                f.write(f"重要程度: {event['importance']}\n\n")
        
        # 未来7天事件
        if results["upcoming_7days"]:
            f.write("## 📅 未来7天经济事件\n\n")
            for event in results["upcoming_7days"]:
                f.write(f"- **{event.get('date', '')}** ")
                f.write(f"{event.get('event', '')} ")
                f.write(f"({event.get('zone', '')})\n")
            f.write("\n")
        
        # 原始数据
        f.write("## 📊 原始数据（按数据源）\n\n")
        for source, events in results["sources"].items():
            f.write(f"### {source}\n\n")
            if not events:
                f.write("无数据\n\n")
                continue
            for event in events[:20]:  # 只显示前20条
                f.write(f"- {event.get('date', '')} ")
                f.write(f"{event.get('event', '')} ")
                if event.get('importance'):
                    f.write(f"[重要程度: {event['importance']}]")
                f.write("\n")
            if len(events) > 20:
                f.write(f"\n...还有 {len(events) - 20} 条事件，详见 JSON 文件\n")
            f.write("\n")
    
    print(f"📄 报告已保存: {md_path}")


if __name__ == "__main__":
    results = run_calendar_collection()
    save_results(results)
    print("\n✅ 经济日历收集完成")

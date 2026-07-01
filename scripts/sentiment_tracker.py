"""
Social Sentiment Tracker
========================
从 X(Twitter) / Reddit / YouTube 采集股票相关讨论和情绪信号

此脚本专注于通过公开数据源抓取社交媒体情绪：
- Twitter/X cashtag搜索（通过WebSearch + WebFetch）
- StockTwits趋势（公开页面）
- Reddit r/wallstreetbets 热门讨论

注意：X API v2 需要付费订阅，此脚本使用公开网页作为数据源。

输出: data/sentiment/{source}-{date}.json
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

# ===== 配置 =====
WATCHLIST = ["AAPL", "NVDA", "MSFT", "TSLA", "META"]
KEYWORDS = ["stock market", "fomc", "inflation", "rate cut", "CPI"]

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "sentiment"


def search_stocktwits_sentiment(ticker: str) -> dict:
    """
    通过 StockTwits 公开页面获取情绪数据
    注意：StockTwits 限制了机器人访问，此方法可能返回受限数据
    """
    try:
        import urllib.request

        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        messages = data.get("messages", [])
        sentiment_counts = {"bullish": 0, "bearish": 0, "neutral": 0}
        trending_terms = {}

        for msg in messages[:100]:
            sentiment = msg.get("entities", {}).get("sentiment")
            if sentiment:
                sentiment_counts[sentiment.get("basic", "neutral")] += 1

        total = sum(sentiment_counts.values()) or 1
        return {
            "ticker": ticker,
            "total_messages": len(messages),
            "sentiment": {
                "bullish_pct": round(sentiment_counts["bullish"] / total * 100, 1),
                "bearish_pct": round(sentiment_counts["bearish"] / total * 100, 1),
                "neutral_pct": round(sentiment_counts["neutral"] / total * 100, 1),
            },
            "fetched_at": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def build_reddit_url(subreddit: str, ticker: str) -> str:
    """构建Reddit搜索URL"""
    return f"https://www.reddit.com/r/{subreddit}/search.json?q={ticker}&sort=hot&limit=25"


def search_reddit_sentiment(ticker: str) -> dict:
    """
    通过 Reddit API 搜索讨论
    注意：Reddit API 需要 App 注册，但公开 endpoint 有基础限流
    """
    try:
        import urllib.request

        subreddits = ["wallstreetbets", "stocks", "investing", "options"]
        all_posts = []

        for sub in subreddits:
            url = build_reddit_url(sub, ticker)
            req = urllib.request.Request(url, headers={"User-Agent": "InvestmentResearch/1.0"})

            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    posts = data.get("data", {}).get("children", [])
                    for p in posts:
                        post_data = p.get("data", {})
                        all_posts.append({
                            "subreddit": sub,
                            "title": post_data.get("title", ""),
                            "score": post_data.get("score", 0),
                            "num_comments": post_data.get("num_comments", 0),
                            "created_utc": post_data.get("created_utc", 0),
                        })
            except Exception:
                continue

        total_score = sum(p.get("score", 0) for p in all_posts)
        total_comments = sum(p.get("num_comments", 0) for p in all_posts)

        return {
            "ticker": ticker,
            "total_posts": len(all_posts),
            "total_score": total_score,
            "total_comments": total_comments,
            "avg_score": round(total_score / len(all_posts), 1) if all_posts else 0,
            "top_posts": sorted(all_posts, key=lambda x: x.get("score", 0), reverse=True)[:5],
            "fetched_at": datetime.now().isoformat(),
        }

    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def generate_sentiment_report(all_data: list) -> str:
    """生成情绪分析报告"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# 社交媒体情绪报告 — {today}", ""]

    for source, data in all_data:
        lines.append(f"## {source}")
        lines.append("")

        if isinstance(data, list):
            for item in data:
                ticker = item.get("ticker", "?")
                if "error" in item:
                    lines.append(f"- **{ticker}**: ❌ {item['error']}")
                    continue

                sentiment = item.get("sentiment", {})
                if sentiment:
                    bull = sentiment.get("bullish_pct", 0)
                    bear = sentiment.get("bearish_pct", 0)
                    emoji = "🐂" if bull > bear else "🐻"
                    lines.append(
                        f"- {emoji} **{ticker}**: "
                        f"看涨 {bull}% / 看跌 {bear}% / 中性 {sentiment.get('neutral_pct', 0)}%"
                    )
                else:
                    posts = item.get("total_posts", 0)
                    comments = item.get("total_comments", 0)
                    avg_score = item.get("avg_score", 0)
                    lines.append(f"- **{ticker}**: {posts}个帖子, {comments}条评论, 平均分{avg_score}")
        lines.append("")

    return "\n".join(lines)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'='*60}")
    print(f"  社交媒体情绪扫描 — {today}")
    print(f"{'='*60}")

    all_data = []

    # StockTwits
    print("\n[*] 采集 StockTwits 数据...")
    stocktwits_data = []
    for ticker in WATCHLIST:
        result = search_stocktwits_sentiment(ticker)
        stocktwits_data.append(result)
        if "error" in result:
            print(f"  ❌ {ticker}: {result['error']}")
        else:
            s = result.get("sentiment", {})
            print(f"  ✅ {ticker}: 看涨{s.get('bullish_pct',0)}% / 看跌{s.get('bearish_pct',0)}%")
    all_data.append(("StockTwits", stocktwits_data))

    # Reddit
    print("\n[*] 采集 Reddit 数据...")
    reddit_data = []
    for ticker in WATCHLIST:
        result = search_reddit_sentiment(ticker)
        reddit_data.append(result)
        if "error" in result:
            print(f"  ❌ {ticker}: {result['error']}")
        else:
            print(f"  ✅ {ticker}: {result.get('total_posts',0)}个帖子, {result.get('total_comments',0)}条评论")
    all_data.append(("Reddit", reddit_data))

    # 保存
    report = generate_sentiment_report(all_data)
    report_file = OUTPUT_DIR / f"sentiment-{today}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n✅ 情绪报告已保存: {report_file}")

    print("\n" + report)


if __name__ == "__main__":
    main()

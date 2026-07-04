#!/usr/bin/env python3
"""
Twitter/X 股票信息抓取脚本
- 使用 twscrape（无需付费 API Key）
- 搜索股票相关关键词，采集最新讨论
- 输出到 data/twitter/ 目录
"""

import json
import os
from datetime import datetime
from typing import List, Dict

try:
    from twscrape import API
    TWScrape = True
except ImportError:
    TWScrape = False
    print("⚠️ twscrape 未安装，跳过 Twitter 抓取")

# 搜索关键词
SEARCH_QUERIES = [
    "$AAPL OR #AAPL",
    "$NVDA OR #NVDA",
    "$TSLA OR #TSLA",
    "stock market OR SPY OR QQQ",
    "FOMC OR Fed rate",
    "earnings season OR财报",
]

# 重点追踪的股票
WATCHLIST = ["AAPL", "NVDA", "MSFT", "TSLA", "META", "GOOGL", "AMZN", "AMD"]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "twitter")


async def init_twitter_accounts(api: API) -> bool:
    """初始化 Twitter 账号（首次使用需要登录）"""
    # twscrape 需要预先添加账号，这里检查是否有可用账号
    accounts = await api.pool.get_accounts()
    if not accounts:
        print("⚠️ 未配置 Twitter 账号")
        print("   请运行: python -m twscrape add_accounts")
        print("   或手动添加账号到 twscrape 账号池")
        return False
    return True


async def search_tweets(api: API, query: str, limit: int = 20) -> List[Dict]:
    """搜索推文"""
    tweets = []
    try:
        async for tweet in api.search(query, limit=limit):
            tweets.append({
                "id": tweet.id,
                "user": tweet.user.username,
                "display_name": tweet.user.display_name,
                "text": tweet.rawContent,
                "created_at": str(tweet.date),
                "likes": tweet.likeCount,
                "retweets": tweet.retweetCount,
                "replies": tweet.replyCount,
                "url": f"https://twitter.com/{tweet.user.username}/status/{tweet.id}",
            })
    except Exception as e:
        print(f"  ⚠️ 搜索 '{query}' 失败: {e}")

    return tweets


async def run_twitter_scan() -> dict:
    """主函数：扫描所有关键词"""
    if not TWScrape:
        return {"error": "twscrape 未安装", "queries": []}

    print("🐦 开始 Twitter/X 股票信息抓取...")
    print(f"   搜索关键词: {len(SEARCH_QUERIES)} 个")

    api = API()
    
    # 检查账号
    has_accounts = await init_twitter_accounts(api)
    if not has_accounts:
        return {
            "error": "需要配置 Twitter 账号，twscrape 才能工作",
            "setup_guide": "https://github.com/vladkens/twscrape",
            "queries": [],
        }

    results = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "queries": {},
        "top_tweets": [],  # 按互动量排序的热门推文
    }

    all_tweets = []

    for query in SEARCH_QUERIES:
        print(f"\n🔍 搜索: {query}")
        tweets = await search_tweets(api, query, limit=20)
        results["queries"][query] = tweets
        all_tweets.extend(tweets)
        print(f"   找到 {len(tweets)} 条推文")

    # 按互动量排序，取 Top 20
    all_tweets.sort(key=lambda x: x["likes"] + x["retweets"] * 2, reverse=True)
    results["top_tweets"] = all_tweets[:20]

    # 统计提到关注股票的次数
    stock_mentions = {ticker: 0 for ticker in WATCHLIST}
    for tweet in all_tweets:
        text_upper = tweet["text"].upper()
        for ticker in WATCHLIST:
            if ticker in text_upper:
                stock_mentions[ticker] += 1
    results["stock_mentions"] = stock_mentions

    return results


def save_results(results: dict):
    """保存结果到文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")

    # 保存 JSON
    json_path = os.path.join(OUTPUT_DIR, f"twitter-{date_str}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 JSON 已保存: {json_path}")

    # 保存可读报告
    md_path = os.path.join(OUTPUT_DIR, f"twitter-{date_str}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Twitter/X 股票讨论汇总 — {date_str}\n\n")

        if results.get("error"):
            f.write(f"⚠️ {results['error']}\n\n")
            if results.get("setup_guide"):
                f.write(f"配置指南: {results['setup_guide']}\n")
        else:
            # 股票提及统计
            f.write("## 📊 关注股票提及次数\n\n")
            for ticker, count in results.get("stock_mentions", {}).items():
                if count > 0:
                    f.write(f"- **{ticker}**: {count} 次提及\n")
            f.write("\n")

            # 热门推文
            f.write("## 🔥 热门推文（按互动量排序）\n\n")
            for i, tweet in enumerate(results.get("top_tweets", [])[:10], 1):
                f.write(f"### {i}. @{tweet['user']} ({tweet['display_name']})\n\n")
                f.write(f"> {tweet['text'][:200]}...\n\n")
                f.write(f"- 👍 {tweet['likes']} | 🔄 {tweet['retweets']} | 💬 {tweet['replies']}\n")
                f.write(f"- [查看原推文]({tweet['url']})\n")
                f.write(f"- 发布时间: {tweet['created_at']}\n\n")

    print(f"📄 报告已保存: {md_path}")


if __name__ == "__main__":
    import asyncio

    results = asyncio.run(run_twitter_scan())
    save_results(results)
    print("\n✅ Twitter 抓取完成")

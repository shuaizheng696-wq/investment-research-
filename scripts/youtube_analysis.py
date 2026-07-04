#!/usr/bin/env python3
"""
YouTube 财经视频分析脚本
- 使用 youtube-transcript-api 获取视频字幕（无需 API Key）
- 分析热门财经频道的最新视频
- 输出摘要到 data/youtube/ 目录
"""

import json
import os
from datetime import datetime
from typing import Optional

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    print("⚠️ youtube-transcript-api 未安装，跳过 YouTube 分析")

# 关注的财经 YouTube 频道（中文+英文）
CHANNELS = {
    # 英文频道
    "Investing with Tom": "UCj8hJMK-rymodelJmPfR3v8Q",
    "Stock Moe": "UCFw7V_YYtRUAvsBwxRV04MA",
    "Ticker Symbol YOU": "UC_brzv3mAWMLUHZcIfVGqbg",
    "Meet Kevin": "UCjF8P3dxyOLHbXjYiUQds_w",
    "Andrei Jikh": "UCGy7SkBjcIAgTiwkXEtPc9Q",
    # 中文频道（示例，可按需替换）
    "财经郎眼": "UCjL6Jgnu2IGDRep3PZTagdw",
}

# 重点追踪的股票关键词
WATCHLIST = ["AAPL", "NVDA", "MSFT", "TSLA", "META", "GOOGL", "AMZN", "AMD"]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "youtube")


def get_video_id_from_url(url: str) -> Optional[str]:
    """从 YouTube URL 提取视频 ID"""
    import re
    patterns = [
        r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def search_channel_videos(channel_name: str, max_results: int = 3) -> list:
    """
    通过 YouTube RSS Feed 获取频道最新视频（无需 API Key）
    返回 [{"title": ..., "video_id": ..., "url": ...}, ...]
    """
    import re
    import urllib.request
    import xml.etree.ElementTree as ET

    # 频道 ID 到 RSS URL 的映射（需要手动维护或通过搜索获取）
    # 这里用一个简化方案：直接搜索视频
    videos = []

    try:
        # 使用 YouTube RSS feed（无需 API）
        # 格式: https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
        channel_id = CHANNELS.get(channel_name)
        if not channel_id:
            return videos

        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        with urllib.request.urlopen(rss_url, timeout=10) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        entries = root.findall("atom:entry", ns)
        for entry in entries[:max_results]:
            title = entry.find("atom:title", ns).text
            video_id = entry.find("atom:videoId", ns).text
            link = entry.find("atom:link", ns).get("href")
            published = entry.find("atom:published", ns).text

            videos.append({
                "title": title,
                "video_id": video_id,
                "url": link,
                "published": published,
            })

    except Exception as e:
        print(f"  ⚠️ 获取频道 {channel_name} 视频失败: {e}")

    return videos


def get_transcript(video_id: str, languages: list = None) -> Optional[str]:
    """获取视频字幕文本"""
    if not YOUTUBE_AVAILABLE:
        return None

    if languages is None:
        languages = ["en", "zh-Hans", "zh-Hant", "zh"]

    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=languages
        )
        # 合并所有文本片段
        full_text = " ".join([item["text"] for item in transcript])
        return full_text
    except TranscriptsDisabled:
        print(f"  ⚠️ 视频 {video_id} 字幕已关闭")
        return None
    except NoTranscriptFound:
        print(f"  ⚠️ 视频 {video_id} 无可用字幕")
        return None
    except Exception as e:
        print(f"  ⚠️ 获取字幕失败: {e}")
        return None


def summarize_transcript(text: str, max_length: int = 500) -> str:
    """简单摘要：截取前 N 字符，并标注是否提到关注股票"""
    if not text:
        return "无字幕内容"

    # 检查是否提到关注股票
    mentions = [ticker for ticker in WATCHLIST if ticker in text.upper()]

    summary = text[:max_length]
    if len(text) > max_length:
        summary += "..."

    result = f"内容摘要：{summary}"
    if mentions:
        result += f"\n\n📌 提到关注股票：{', '.join(mentions)}"

    return result


def analyze_video(video: dict) -> dict:
    """分析单个视频"""
    video_id = video["video_id"]
    print(f"  📹 分析: {video['title']}")

    transcript = get_transcript(video_id)
    summary = summarize_transcript(transcript) if transcript else "无法获取字幕"

    return {
        "channel": video.get("channel", ""),
        "title": video["title"],
        "url": video["url"],
        "published": video["published"],
        "summary": summary,
        "has_transcript": transcript is not None,
    }


def run_youtube_analysis() -> dict:
    """主函数：分析所有频道的最新视频"""
    if not YOUTUBE_AVAILABLE:
        return {"error": "youtube-transcript-api 未安装", "channels": []}

    print("🎬 开始 YouTube 财经视频分析...")
    print(f"   关注频道: {len(CHANNELS)} 个")
    print(f"   关注股票: {', '.join(WATCHLIST)}")

    results = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "channels": {},
        "mentions": [],  # 提到关注股票的所有视频
    }

    for channel_name in CHANNELS:
        print(f"\n📺 频道: {channel_name}")
        videos = search_channel_videos(channel_name, max_results=2)

        if not videos:
            print(f"  ⚠️ 未获取到视频")
            continue

        channel_results = []
        for video in videos:
            analysis = analyze_video(video)
            channel_results.append(analysis)

            # 记录提到关注股票的视频
            if analysis.get("summary") and any(
                ticker in analysis["summary"] for ticker in WATCHLIST
            ):
                results["mentions"].append({
                    "channel": channel_name,
                    "title": analysis["title"],
                    "url": analysis["url"],
                })

        results["channels"][channel_name] = channel_results

    return results


def save_results(results: dict):
    """保存结果到文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")

    # 保存 JSON
    json_path = os.path.join(OUTPUT_DIR, f"youtube-{date_str}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 JSON 已保存: {json_path}")

    # 保存可读报告
    md_path = os.path.join(OUTPUT_DIR, f"youtube-{date_str}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# YouTube 财经视频分析 — {date_str}\n\n")

        if results.get("error"):
            f.write(f"⚠️ {results['error']}\n")
        else:
            # 提到关注股票的视频（重点）
            if results["mentions"]:
                f.write("## 📌 提到关注股票的视频\n\n")
                for m in results["mentions"]:
                    f.write(f"- **{m['channel']}**: [{m['title']}]({m['url']})\n")
                f.write("\n")

            # 按频道分组
            f.write("## 各频道最新视频\n\n")
            for channel_name, videos in results["channels"].items():
                f.write(f"### {channel_name}\n\n")
                for v in videos:
                    f.write(f"**[{v['title']}]({v['url']})**\n")
                    f.write(f"- 发布时间: {v['published']}\n")
                    f.write(f"- 字幕可用: {'✅' if v['has_transcript'] else '❌'}\n")
                    if v["has_transcript"]:
                        f.write(f"\n{v['summary'][:300]}...\n")
                    f.write("\n")

    print(f"📄 报告已保存: {md_path}")


if __name__ == "__main__":
    results = run_youtube_analysis()
    save_results(results)
    print("\n✅ YouTube 分析完成")

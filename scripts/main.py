"""
main.py
安全资讯RSS聚合工具 — 主入口

用法：
  # 每日简报（默认）
  python scripts/main.py

  # 每周简报
  python scripts/main.py --mode weekly

  # 自定义输出目录
  python scripts/main.py --mode daily --output-dir /tmp/news

  # 使用自定义 OPML URL
  python scripts/main.py --opml-url https://example.com/feeds.opml
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as a top-level script from the repo root
sys.path.insert(0, str(Path(__file__).parent))

from opml_fetcher import fetch_feeds_from_opml, OPML_URL
from rss_fetcher import fetch_all_articles
from deduplicator import deduplicate_articles
from summarizer import analyze_hotspots
from formatter import format_report

_WINDOW_HOURS = {
    "daily": 24,
    "weekly": 168,
}


def build_output_path(output_dir: str, mode: str, report_date: datetime) -> Path:
    """Return the output Markdown file path for the given mode and date."""
    date_str = report_date.strftime("%Y-%m-%d")
    subdir = Path(output_dir) / mode
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir / f"{date_str}.md"


def run(
    mode: str = "daily",
    output_dir: str = "output",
    opml_url: str = OPML_URL,
    print_output: bool = False,
) -> str:
    """Execute the full RSS → Markdown pipeline.

    Args:
        mode: 'daily' or 'weekly'.
        output_dir: Root directory where reports are saved.
        opml_url: URL of the OPML file listing RSS feeds.
        print_output: If True, also print the report to stdout.

    Returns:
        The generated Markdown report as a string.
    """
    report_date = datetime.now(tz=timezone.utc)
    window_hours = _WINDOW_HOURS.get(mode, 24)

    print(f"\n{'=' * 60}")
    print(f"  安全资讯RSS聚合工具  |  模式: {mode}  |  {report_date.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'=' * 60}\n")

    # Step 1: fetch RSS feed list from OPML
    feeds = fetch_feeds_from_opml(opml_url)
    if not feeds:
        print("[ERROR] 未能获取任何RSS订阅源，退出。")
        sys.exit(1)

    # Step 2: fetch articles from all feeds
    articles = fetch_all_articles(feeds, window_hours=window_hours)

    if not articles:
        print("[WARN] 在时间窗口内未获取到任何资讯，将生成空报告。")

    # Step 3: deduplicate
    unique_articles = deduplicate_articles(articles)

    # Step 4: hotspot analysis
    hotspots, _ = analyze_hotspots(unique_articles)

    # Step 5: format Markdown report
    report = format_report(hotspots, unique_articles, mode=mode, report_date=report_date)

    # Step 6: save to file
    out_path = build_output_path(output_dir, mode, report_date)
    out_path.write_text(report, encoding="utf-8")
    print(f"\n[OUTPUT] 报告已保存至: {out_path}")

    if print_output:
        print("\n" + "=" * 60)
        print(report)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="安全资讯RSS订阅聚合工具 — 生成每日/每周Markdown简报",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly"],
        default="daily",
        help="输出模式：daily（每日）或 weekly（每周），默认 daily",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Markdown报告输出目录，默认 output/",
    )
    parser.add_argument(
        "--opml-url",
        default=OPML_URL,
        help="OPML订阅源文件URL",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        dest="print_output",
        help="同时将报告打印到标准输出",
    )
    args = parser.parse_args()

    run(
        mode=args.mode,
        output_dir=args.output_dir,
        opml_url=args.opml_url,
        print_output=args.print_output,
    )


if __name__ == "__main__":
    main()

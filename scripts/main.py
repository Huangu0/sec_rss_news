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

  # 使用自定义配置文件（YAML/JSON）
  python scripts/main.py --config config/default.yaml
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as a top-level script from the repo root
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import load_config
from opml_fetcher import fetch_feeds_from_opml, OPML_URL
from rss_fetcher import fetch_all_articles
from deduplicator import deduplicate_articles
from summarizer import analyze_hotspots
from scorer import score_and_rank_hotspots
from formatter import format_report
from persistence import ArticlePersistence

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
    config_path: str | None = None,
) -> str:
    """Execute the full RSS → Markdown pipeline.

    Args:
        mode: 'daily' or 'weekly'.
        output_dir: Root directory where reports are saved.
        opml_url: URL of the OPML file listing RSS feeds (overrides config).
        print_output: If True, also print the report to stdout.
        config_path: Optional path to a YAML/JSON config file.

    Returns:
        The generated Markdown report as a string.
    """
    report_date = datetime.now(tz=timezone.utc)

    # Load config and apply mode-specific overrides
    cfg = load_config(config_path)
    mode_cfg = cfg.get("schedule", {}).get("modes", {}).get(mode, {})
    window_hours = mode_cfg.get("window_hours", _WINDOW_HOURS.get(mode, 24))
    fetch_cfg = cfg.get("fetch", {})
    dedup_cfg = cfg.get("dedup", {})
    scoring_cfg = cfg.get("scoring", {})
    persistence_cfg = cfg.get("persistence", {})

    print(f"\n{'=' * 60}")
    print(f"  安全资讯RSS聚合工具  |  模式: {mode}  |  {report_date.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'=' * 60}\n")

    # Step 1: fetch RSS feed list from OPML
    feeds = fetch_feeds_from_opml(opml_url)
    # Merge any static sources from config
    static_sources = cfg.get("feeds", {}).get("sources") or []
    if static_sources:
        feeds.extend(static_sources)
    if not feeds:
        print("[ERROR] 未能获取任何RSS订阅源，退出。")
        sys.exit(1)

    # Step 2: fetch articles from all feeds
    articles = fetch_all_articles(
        feeds,
        window_hours=window_hours,
        max_items=fetch_cfg.get("max_items_per_source", 20),
        timeout=fetch_cfg.get("timeout_seconds", 15),
        max_workers=fetch_cfg.get("max_workers", 10),
    )

    if not articles:
        print("[WARN] 在时间窗口内未获取到任何资讯，将生成空报告。")

    # Step 3: deduplicate
    unique_articles = deduplicate_articles(
        articles,
        similarity_threshold=dedup_cfg.get("title_similarity_threshold", 0.8),
    )

    # Step 3b: persistent dedup (cross-run, optional)
    if persistence_cfg.get("enabled", False):
        store = ArticlePersistence(
            db_path=persistence_cfg.get("path", "data/seen_articles.db"),
            retention_days=int(persistence_cfg.get("retention_days", 30)),
        )
        unique_articles = store.filter_new(unique_articles)
        store.mark_seen(unique_articles)

    # Step 4: hotspot analysis
    hotspots, _, keyword_counts = analyze_hotspots(
        unique_articles,
        top_n=scoring_cfg.get("top_keywords", 20),
        min_articles=scoring_cfg.get("min_articles_per_hotspot", 2),
        return_keyword_counts=True,
    )

    # Step 4b: score and rank hotspots
    source_weights = {
        s.get("title", s.get("url", "")): float(s.get("weight", 1.0))
        for s in static_sources
    }
    hotspots = score_and_rank_hotspots(
        hotspots,
        now=report_date,
        time_decay_hours=float(scoring_cfg.get("time_decay_hours", 24)),
        source_weights=source_weights if scoring_cfg.get("source_weight_enabled", True) else {},
        keyword_boosts=scoring_cfg.get("keyword_boost") or None,
    )
    max_hotspots = min(mode_cfg.get("max_hotspots", 10), 10)
    hotspots = hotspots[:max_hotspots]

    summary_top_keywords = [
        {"keyword": kw, "count": count}
        for kw, count in keyword_counts.most_common(min(10, scoring_cfg.get("top_keywords", 20)))
    ]
    summary_attention = []
    for h in hotspots[:3]:
        articles_for_hotspot = h.get("articles") or []
        primary = articles_for_hotspot[0] if articles_for_hotspot else {}
        summary_attention.append(
            {
                "keyword": h.get("keyword", ""),
                "count": h.get("count", 0),
                "headline": primary.get("title", ""),
                "link": primary.get("link", ""),
                "source": primary.get("source", ""),
            }
        )
    summary = {
        "top_keywords": summary_top_keywords,
        "attention": summary_attention,
    }

    # Step 5: format Markdown report
    report = format_report(
        hotspots, unique_articles, summary=summary, mode=mode, report_date=report_date
    )

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
    parser.add_argument(
        "--config",
        default=None,
        metavar="PATH",
        help="YAML/JSON配置文件路径（覆盖默认配置）",
    )
    args = parser.parse_args()

    run(
        mode=args.mode,
        output_dir=args.output_dir,
        opml_url=args.opml_url,
        print_output=args.print_output,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()

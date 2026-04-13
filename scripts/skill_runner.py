"""
skill_runner.py
agentskill.io Skill 入口模块。

提供标准的 ``run_skill(input) → output`` 接口，遵循 agentskill.io 输入/输出契约。

────────────────────────────────────────────────────────────
输入契约（Input Schema）
────────────────────────────────────────────────────────────
  mode          : "daily" | "weekly"   （默认 "daily"）
  config_path   : str | null           （YAML/JSON 配置文件路径，null 则使用默认配置）
  output_format : "json" | "markdown"  （默认 "json"）
  max_hotspots  : int                  （默认 10，覆盖配置中的值）

────────────────────────────────────────────────────────────
输出契约（Output Schema）
────────────────────────────────────────────────────────────
  hotspots : list[{keyword, score, count, articles}]  按热度降序排列
  articles : list[article]                            去重后的全量资讯
  report   : str                                      Markdown 报告（output_format="markdown" 时填充）
  metadata : {total_articles, unique_articles, hotspot_count, generated_at, mode}
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow running as a standalone script from any directory
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import load_config
from opml_fetcher import fetch_feeds_from_opml, OPML_URL
from rss_fetcher import fetch_all_articles
from deduplicator import deduplicate_articles
from summarizer import analyze_hotspots
from scorer import score_and_rank_hotspots
from formatter import format_report
from persistence import ArticlePersistence


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _serialise_article(article: Dict) -> Dict:
    """Convert one article dict to a JSON-serialisable form."""
    pub: Optional[datetime] = article.get("published")
    return {
        "title": article.get("title", ""),
        "link": article.get("link", ""),
        "summary": article.get("summary", ""),
        "published": pub.isoformat() if pub is not None else None,
        "source": article.get("source", ""),
        "category": article.get("category", ""),
    }


def _serialise_articles(articles: List[Dict]) -> List[Dict]:
    return [_serialise_article(a) for a in articles]


def _serialise_hotspots(hotspots: List[Dict]) -> List[Dict]:
    return [
        {
            "keyword": h.get("keyword", ""),
            "score": h.get("score", 0.0),
            "count": h.get("count", 0),
            "articles": _serialise_articles(h.get("articles", [])),
        }
        for h in hotspots
    ]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_skill(input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute the full RSS → hotspot-ranking pipeline and return structured output.

    This function is the callable entry point registered in ``skill.json``.

    Args:
        input: Parameter dict matching the Input Schema described in this module's
               docstring.  All fields are optional; defaults are applied.

    Returns:
        Dict matching the Output Schema described in this module's docstring.
    """
    if input is None:
        input = {}

    mode: str = input.get("mode", "daily")
    config_path: Optional[str] = input.get("config_path", None)
    output_format: str = input.get("output_format", "json")
    max_hotspots_override: Optional[int] = input.get("max_hotspots", None)

    # ── Load configuration ────────────────────────────────────────────────────
    cfg = load_config(config_path)

    mode_cfg: Dict = cfg.get("schedule", {}).get("modes", {}).get(mode, {})
    window_hours: int = mode_cfg.get("window_hours", 24 if mode == "daily" else 168)
    max_hotspots: int = (
        int(max_hotspots_override)
        if max_hotspots_override is not None
        else mode_cfg.get("max_hotspots", 10)
    )

    fetch_cfg: Dict = cfg.get("fetch", {})
    dedup_cfg: Dict = cfg.get("dedup", {})
    scoring_cfg: Dict = cfg.get("scoring", {})
    persistence_cfg: Dict = cfg.get("persistence", {})
    feeds_cfg: Dict = cfg.get("feeds", {})

    now = datetime.now(tz=timezone.utc)

    # ── Step 1 : Load feed list ───────────────────────────────────────────────
    feeds: List[Dict] = []
    opml_url: Optional[str] = feeds_cfg.get("opml_url")
    if opml_url:
        feeds = fetch_feeds_from_opml(opml_url)

    static_sources: List[Dict] = feeds_cfg.get("sources") or []
    if static_sources:
        feeds.extend(static_sources)

    if not feeds:
        # Absolute fallback
        feeds = fetch_feeds_from_opml(OPML_URL)

    # ── Step 2 : Fetch articles ───────────────────────────────────────────────
    articles: List[Dict] = fetch_all_articles(
        feeds,
        window_hours=window_hours,
        max_items=fetch_cfg.get("max_items_per_source", 20),
        timeout=fetch_cfg.get("timeout_seconds", 15),
        max_workers=fetch_cfg.get("max_workers", 10),
    )
    total_articles = len(articles)

    # ── Step 3 : In-memory deduplication ─────────────────────────────────────
    unique_articles: List[Dict] = deduplicate_articles(
        articles,
        similarity_threshold=dedup_cfg.get("title_similarity_threshold", 0.8),
    )

    # ── Step 4 : Persistent dedup (cross-run) ────────────────────────────────
    persistence: Optional[ArticlePersistence] = None
    if persistence_cfg.get("enabled", False):
        persistence = ArticlePersistence(
            db_path=persistence_cfg.get("path", "data/seen_articles.db"),
            retention_days=int(persistence_cfg.get("retention_days", 30)),
        )
        unique_articles = persistence.filter_new(unique_articles)

    # ── Step 5 : Hotspot analysis ─────────────────────────────────────────────
    hotspots, _ = analyze_hotspots(
        unique_articles,
        top_n=scoring_cfg.get("top_keywords", 20),
        min_articles=scoring_cfg.get("min_articles_per_hotspot", 2),
    )

    # ── Step 6 : Score and rank hotspots ──────────────────────────────────────
    source_weights: Dict[str, float] = {
        s.get("title", s.get("url", "")): float(s.get("weight", 1.0))
        for s in static_sources
    }
    hotspots = score_and_rank_hotspots(
        hotspots,
        now=now,
        time_decay_hours=float(scoring_cfg.get("time_decay_hours", 24)),
        source_weights=source_weights if scoring_cfg.get("source_weight_enabled", True) else {},
        keyword_boosts=scoring_cfg.get("keyword_boost") or None,
    )
    hotspots = hotspots[:max_hotspots]

    # ── Step 7 : Mark seen ────────────────────────────────────────────────────
    if persistence is not None:
        persistence.mark_seen(unique_articles)

    # ── Build output ──────────────────────────────────────────────────────────
    metadata: Dict[str, Any] = {
        "total_articles": total_articles,
        "unique_articles": len(unique_articles),
        "hotspot_count": len(hotspots),
        "generated_at": now.isoformat(),
        "mode": mode,
    }

    result: Dict[str, Any] = {
        "hotspots": _serialise_hotspots(hotspots),
        "articles": _serialise_articles(unique_articles),
        "report": "",
        "metadata": metadata,
    }

    if output_format == "markdown":
        result["report"] = format_report(
            hotspots, unique_articles, mode=mode, report_date=now
        )

    return result


# ---------------------------------------------------------------------------
# CLI wrapper
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="sec-rss-news agentskill.io Skill 命令行运行器"
    )
    parser.add_argument("--mode", default="daily", choices=["daily", "weekly"])
    parser.add_argument("--config", default=None, metavar="PATH", help="YAML/JSON 配置文件路径")
    parser.add_argument(
        "--format", default="json", choices=["json", "markdown"], dest="output_format"
    )
    parser.add_argument("--max-hotspots", type=int, default=None)
    args = parser.parse_args()

    result = run_skill(
        {
            "mode": args.mode,
            "config_path": args.config,
            "output_format": args.output_format,
            "max_hotspots": args.max_hotspots,
        }
    )

    if args.output_format == "markdown":
        print(result["report"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()

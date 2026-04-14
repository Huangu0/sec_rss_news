"""
formatter.py
将热点资讯和全量资讯列表格式化为 Markdown 报告。
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Tuple

_MODE_META = {
    "daily": {
        "title_prefix": "🔐 安全资讯日报",
        "window_label": "近 24 小时",
        "emoji": "📅",
    },
    "weekly": {
        "title_prefix": "🔐 安全资讯周报",
        "window_label": "近 7 天",
        "emoji": "📆",
    },
}

_HOTSPOT_EMOJIS = ["🔥", "🚨", "⚡", "🎯", "🛡️", "💣", "🔍", "📡", "🕵️", "🧨"]


def _fmt_time(dt: datetime | None) -> str:
    """Format a datetime to a short readable string."""
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


def _fmt_article_line(article: Dict) -> str:
    """Format a single article as a Markdown list item."""
    title = article.get("title", "（无标题）")
    link = article.get("link", "")
    source = article.get("source", "")
    pub = _fmt_time(article.get("published"))

    parts = []
    if link:
        parts.append(f"[{title}]({link})")
    else:
        parts.append(title)

    meta_parts = []
    if source:
        meta_parts.append(f"`{source}`")
    if pub:
        meta_parts.append(pub)
    if meta_parts:
        parts.append(" — " + " · ".join(meta_parts))

    return "- " + "".join(parts)


def format_report(
    hotspots: List[Dict],
    articles: List[Dict],
    summary: Dict | None = None,
    mode: str = "daily",
    report_date: datetime | None = None,
) -> str:
    """Build the full Markdown report string.

    Args:
        hotspots: Output from summarizer.analyze_hotspots / scorer.
        articles: Deduplicated article list.
        summary: Dict with keys top_keywords (list) and attention (list).
        mode: 'daily' or 'weekly'.
        report_date: Report reference date (defaults to UTC now).

    Returns:
        Complete Markdown string.
    """
    if report_date is None:
        report_date = datetime.now(tz=timezone.utc)

    meta = _MODE_META.get(mode, _MODE_META["daily"])
    date_str = report_date.strftime("%Y-%m-%d")
    now_str = report_date.strftime("%Y-%m-%d %H:%M UTC")

    lines: List[str] = []
    summary = summary or {}
    summary_keywords = summary.get("top_keywords") or []
    summary_attention = summary.get("attention") or []

    # ── Header ───────────────────────────────────────────────────────────────
    lines.append(f"# {meta['title_prefix']} · {date_str}")
    lines.append("")
    lines.append(
        f"> {meta['emoji']} 数据来源：[SecurityRSS-Lite](https://github.com/arch3rPro/SecurityRSS)  "
    )
    lines.append(
        f"> 统计范围：{meta['window_label']}  "
    )
    stats_line = f"> 共收录 **{len(articles)}** 条资讯"
    stats_line += f"，发现 **{len(hotspots)}** 个热点话题" if hotspots else ""
    lines.append(stats_line)
    lines.append(
        f"> 热点条数已限制在 10 条以内"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Hotspot Summary ───────────────────────────────────────────────────────
    if hotspots:
        lines.append("## 🔥 热点信息")
        lines.append("")
        for i, hotspot in enumerate(hotspots):
            emoji = _HOTSPOT_EMOJIS[i % len(_HOTSPOT_EMOJIS)]
            kw = hotspot["keyword"]
            cnt = hotspot["count"]
            lines.append(f"### {emoji} 热点 {i + 1}：{kw}（{cnt} 条相关资讯）")
            lines.append("")
            for art in hotspot["articles"]:
                lines.append(_fmt_article_line(art))
            lines.append("")

        lines.append("---")
        lines.append("")

    # ── Summary Section ───────────────────────────────────────────────────────
    lines.append("## 🧭 总结信息")
    lines.append("")
    if summary_keywords:
        kw_parts = [f"{item.get('keyword', '')}（{item.get('count', 0)}）" for item in summary_keywords[:10]]
        lines.append("- **高频关键词**：" + " · ".join(kw_parts))
    else:
        lines.append("- **高频关键词**：暂无数据")

    if summary_attention:
        lines.append("- **需要注意**：")
        for item in summary_attention:
            keyword = item.get("keyword", "")
            count = item.get("count", 0)
            headline = item.get("headline", "")
            link = item.get("link", "")
            source = item.get("source", "")

            meta = f"{keyword}（{count}条）" if keyword else ""
            if headline:
                if link:
                    detail = f"[{headline}]({link})"
                else:
                    detail = headline
                if source:
                    detail += f" — `{source}`"
            else:
                detail = source or ""
            joined = " — ".join([p for p in [meta, detail] if p])
            lines.append(f"- {joined}" if joined else "- （暂无详情）")
    else:
        lines.append("- **需要注意**：暂无需要特别关注的内容")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ── Full Article List ─────────────────────────────────────────────────────
    lines.append("## 📰 全部资讯（附录）")
    lines.append("")

    # Group by category
    by_category: Dict[str, List[Dict]] = defaultdict(list)
    for art in articles:
        by_category[art.get("category", "未分类")].append(art)

    for category, cat_articles in by_category.items():
        lines.append(f"### {category}")
        lines.append("")
        for art in cat_articles:
            lines.append(_fmt_article_line(art))
        lines.append("")

    # ── Footer ────────────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append(f"*报告生成时间：{now_str}*")
    lines.append("")

    return "\n".join(lines)

"""
scorer.py
计算资讯热度分数，并对热点列表重新排序。

打分维度：
  1. 时间衰减（time decay）    — 越新的文章得分越高，指数衰减
  2. 来源权重（source weight） — 可在配置中为每个 RSS 源设置权重
  3. 关键词加权（keyword boost）— 标题包含指定关键词时，热度分翻倍
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional

DEFAULT_TIME_DECAY_HOURS: float = 24.0
DEFAULT_KEYWORD_BOOST: List[str] = [
    "CVE", "漏洞", "勒索", "攻击", "0day", "RCE", "供应链", "APT", "数据泄露"
]


def score_article(
    article: Dict,
    now: Optional[datetime] = None,
    time_decay_hours: float = DEFAULT_TIME_DECAY_HOURS,
    source_weights: Optional[Dict[str, float]] = None,
    keyword_boosts: Optional[List[str]] = None,
) -> float:
    """Calculate hotness score for a single article.

    Score formula::

        score = time_decay × source_weight × keyword_multiplier

    where:
        * ``time_decay``        = exp(-age_hours / decay_hours), ∈ (0, 1]
        * ``source_weight``     = per-source weight from config (default 1.0)
        * ``keyword_multiplier``= 2.0 if any boost keyword is found in title, else 1.0

    Args:
        article: Article dict with keys 'published', 'source', 'title'.
        now: Reference datetime for age calculation (UTC). Defaults to now.
        time_decay_hours: Half-life in hours. Smaller = faster decay.
        source_weights: Mapping of source name → weight multiplier.
        keyword_boosts: Keywords that trigger a ×2 score boost.

    Returns:
        Float hotness score ≥ 0.
    """
    if now is None:
        now = datetime.now(tz=timezone.utc)
    if source_weights is None:
        source_weights = {}
    if keyword_boosts is None:
        keyword_boosts = DEFAULT_KEYWORD_BOOST

    # 1. Time decay
    pub_dt: Optional[datetime] = article.get("published")
    if pub_dt is not None and pub_dt.tzinfo is not None:
        age_hours = max(0.0, (now - pub_dt).total_seconds() / 3600.0)
        time_score = math.exp(-age_hours / max(time_decay_hours, 1.0))
    else:
        time_score = 0.5  # unknown date → moderate recency

    # 2. Source weight
    source = article.get("source", "")
    weight = source_weights.get(source, 1.0)

    # 3. Keyword boost
    title_upper = article.get("title", "").upper()
    keyword_multiplier = (
        2.0 if any(kw.upper() in title_upper for kw in keyword_boosts) else 1.0
    )

    return time_score * weight * keyword_multiplier


def score_and_rank_hotspots(
    hotspots: List[Dict],
    now: Optional[datetime] = None,
    time_decay_hours: float = DEFAULT_TIME_DECAY_HOURS,
    source_weights: Optional[Dict[str, float]] = None,
    keyword_boosts: Optional[List[str]] = None,
) -> List[Dict]:
    """Score each hotspot by summing its constituent articles' scores, then sort.

    Each hotspot dict is mutated in place to add a ``'score'`` field.

    Args:
        hotspots: List of hotspot dicts from :func:`summarizer.analyze_hotspots`.
        now: Reference datetime (UTC). Defaults to now.
        time_decay_hours: Passed through to :func:`score_article`.
        source_weights: Mapping of source name → weight multiplier.
        keyword_boosts: Keywords that trigger a ×2 score boost.

    Returns:
        The same list, sorted by ``'score'`` descending.
    """
    if now is None:
        now = datetime.now(tz=timezone.utc)

    for hotspot in hotspots:
        articles = hotspot.get("articles", [])
        if not articles:
            hotspot["score"] = 0.0
            continue
        total = sum(
            score_article(
                a,
                now=now,
                time_decay_hours=time_decay_hours,
                source_weights=source_weights,
                keyword_boosts=keyword_boosts,
            )
            for a in articles
        )
        hotspot["score"] = round(total, 6)

    hotspots.sort(key=lambda h: h.get("score", 0.0), reverse=True)
    return hotspots

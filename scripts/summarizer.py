"""
summarizer.py
从资讯标题中提取关键词，聚合热点话题，返回按热度排序的热点列表。
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

# Try to use jieba for Chinese word segmentation; fall back to simple splitting
try:
    import jieba  # type: ignore

    jieba.setLogLevel(20)  # suppress debug output
    _JIEBA_AVAILABLE = True
except ImportError:
    _JIEBA_AVAILABLE = False

# Chinese & English stop words for security domain
_STOP_WORDS = {
    # Chinese common stop words
    "的", "了", "和", "是", "在", "有", "与", "为", "及", "对", "等", "中",
    "以", "被", "从", "到", "个", "其", "该", "这", "那", "也", "并",
    "已", "将", "可", "能", "而", "但", "或", "如", "上", "下", "来",
    "去", "于", "由", "后", "前", "内", "外", "大", "小", "多", "少",
    "通过", "进行", "使用", "发现", "发布", "公开", "分析", "研究",
    "披露", "导致", "影响", "针对", "关于", "一种", "一个", "一些",
    "如何", "什么", "为什么", "怎样", "可以", "包括", "以及",
    # English common stop words
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "of",
    "for", "with", "by", "from", "is", "are", "was", "were", "be",
    "been", "has", "have", "had", "not", "no", "new", "how", "why",
    "what", "when", "where", "which", "that", "this", "it", "its",
    "can", "could", "would", "should", "may", "might", "will",
    # Common single chars/noise
    " ", "\t", "\n",
}

_MIN_KEYWORD_LEN = 2
_TOP_KEYWORDS = 20
_MIN_ARTICLES_PER_HOTSPOT = 2


def _extract_keywords(title: str) -> List[str]:
    """Extract meaningful keywords from a title string."""
    if _JIEBA_AVAILABLE:
        words = list(jieba.cut(title, cut_all=False))
    else:
        # Simple split on non-Chinese, non-alphanumeric characters
        words = re.split(r"[\s\W]+", title)

    keywords: List[str] = []
    for w in words:
        w = w.strip()
        if len(w) < _MIN_KEYWORD_LEN:
            continue
        if w.lower() in _STOP_WORDS:
            continue
        # Skip pure digits or single ASCII chars
        if re.fullmatch(r"[\d\W]+", w):
            continue
        keywords.append(w)

    return keywords


def _index_keywords(articles: List[Dict]) -> Tuple[Dict[str, List[Dict]], Counter]:
    """Build keyword → articles mapping and frequency counter."""
    keyword_to_articles: Dict[str, List[Dict]] = defaultdict(list)
    keyword_counts: Counter = Counter()

    for article in articles:
        seen_keywords: set = set()
        for kw in _extract_keywords(article.get("title", "")):
            kw_lower = kw.lower()
            if kw_lower in seen_keywords:
                continue
            keyword_to_articles[kw].append(article)
            keyword_counts[kw] += 1
            seen_keywords.add(kw_lower)

    return keyword_to_articles, keyword_counts


def analyze_hotspots(
    articles: List[Dict],
    top_n: int = _TOP_KEYWORDS,
    min_articles: int = _MIN_ARTICLES_PER_HOTSPOT,
    return_keyword_counts: bool = False,
) -> Tuple[List[Dict], List[Dict]] | Tuple[List[Dict], List[Dict], Counter]:
    """Analyze articles and return hotspot topics.

    Args:
        articles: Deduplicated article list.
        top_n: Maximum number of hot keywords to surface.
        min_articles: Minimum articles required for a keyword to be a hotspot.
        return_keyword_counts: When True, also return the keyword frequency Counter.

    Returns:
        Tuple containing hotspots and the original articles; when
        ``return_keyword_counts`` is True, a third element (Counter) is returned.
          - hotspots: list of dicts with keys 'keyword', 'count', 'articles'
            sorted by count descending.
          - articles: original articles list (unchanged).
          - keyword_counts (optional): Counter of keyword → occurrence count.
    """
    keyword_to_articles, keyword_counts = _index_keywords(articles)

    top_keywords = [kw for kw, _ in keyword_counts.most_common(top_n * 3)]

    # Build hotspot list, deduplicating articles across hotspots
    hotspots: List[Dict] = []
    covered_links: set = set()

    for kw in top_keywords:
        if len(hotspots) >= top_n:
            break
        arts = keyword_to_articles[kw]
        if len(arts) < min_articles:
            continue
        # Exclude already-covered articles from this hotspot's list
        unique_arts = [
            a for a in arts
            if (a.get("link") or a.get("title")) not in covered_links
        ]
        if len(unique_arts) < min_articles:
            continue

        for a in unique_arts:
            covered_links.add(a.get("link") or a.get("title"))

        hotspots.append(
            {
                "keyword": kw,
                "count": len(unique_arts),
                "articles": unique_arts[:10],
            }
        )

    print(f"[SUMMARIZER] 识别出 {len(hotspots)} 个热点话题")
    if return_keyword_counts:
        return hotspots, articles, keyword_counts
    return hotspots, articles


def keyword_summary(articles: List[Dict], top_n: int = 10) -> List[Dict[str, int]]:
    """Return the top keyword frequencies from *articles*."""
    _, keyword_counts = _index_keywords(articles)
    return [
        {"keyword": kw, "count": count}
        for kw, count in keyword_counts.most_common(top_n)
    ]

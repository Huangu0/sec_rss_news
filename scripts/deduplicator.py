"""
deduplicator.py
对资讯列表进行去重：
  1. URL 精确匹配去重（相同 URL 只保留最新一篇）
  2. 标题相似度模糊去重（SequenceMatcher ratio >= threshold 时保留最新一篇）
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import List, Dict

DEFAULT_SIMILARITY_THRESHOLD = 0.8


def _normalize_title(title: str) -> str:
    """Lowercase and strip common punctuation for comparison."""
    for ch in "【】『』「」《》〈〉（）()[]{}「」'\",.!?，。！？、；：":
        title = title.replace(ch, " ")
    return title.lower().strip()


def _title_similarity(a: str, b: str) -> float:
    """Return SequenceMatcher similarity ratio between two titles."""
    return SequenceMatcher(None, _normalize_title(a), _normalize_title(b)).ratio()


def deduplicate_articles(
    articles: List[Dict],
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> List[Dict]:
    """Remove duplicate articles from *articles* (sorted newest-first).

    Deduplication strategy (applied in order):
    1. **URL dedup**: keep only the first occurrence of each URL.
    2. **Title fuzzy dedup**: if two titles have similarity >= *threshold*,
       keep the article that appeared earlier in the list (newest due to sort).

    Args:
        articles: List of article dicts (expected newest-first).
        similarity_threshold: Minimum similarity ratio to consider titles as duplicates.

    Returns:
        Deduplicated list preserving the original order.
    """
    seen_urls: set = set()
    unique: List[Dict] = []

    for article in articles:
        link = (article.get("link") or "").strip()

        # 1. URL exact dedup
        if link:
            if link in seen_urls:
                continue
            seen_urls.add(link)

        # 2. Title fuzzy dedup
        title = article.get("title", "")
        is_dup = False
        for kept in unique:
            if _title_similarity(title, kept.get("title", "")) >= similarity_threshold:
                is_dup = True
                break
        if is_dup:
            continue

        unique.append(article)

    removed = len(articles) - len(unique)
    print(f"[DEDUP] 去重前 {len(articles)} 条 → 去重后 {len(unique)} 条（移除 {removed} 条重复）")
    return unique

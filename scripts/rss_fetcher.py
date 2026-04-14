"""
rss_fetcher.py
并发抓取多个RSS订阅源的文章，按时间窗口过滤并统一返回。
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Optional

import feedparser
import requests
from dateutil import parser as dateutil_parser
from datetime import timedelta

DEFAULT_TIMEOUT = 15
DEFAULT_MAX_WORKERS = 10
DEFAULT_MAX_ITEMS = 20


def _parse_date(entry) -> Optional[datetime]:
    """Try to extract a timezone-aware datetime from a feedparser entry."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    # Fallback: try parsing raw string fields
    for attr in ("published", "updated", "created"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                dt = dateutil_parser.parse(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
    return None


def _build_request_kwargs(feed_info: Dict) -> Dict:
    """Build keyword arguments for ``requests.get`` based on feed auth config.

    Supported auth types (configured under the ``auth`` key of a feed dict):
      * ``basic``   — HTTP Basic Authentication (username + password)
      * ``api_key`` — Custom header-based API key (header + key)

    Args:
        feed_info: Feed dict that may contain an ``auth`` sub-dict.

    Returns:
        Dict of extra kwargs to pass to ``requests.get``.
    """
    kwargs: Dict = {"headers": {"User-Agent": "sec-rss-news/1.0"}}
    auth_cfg = feed_info.get("auth")
    if not auth_cfg:
        return kwargs

    auth_type = str(auth_cfg.get("type", "")).lower()
    if auth_type == "basic":
        username = auth_cfg.get("username", "")
        password = auth_cfg.get("password", "")
        if username or password:
            kwargs["auth"] = (username, password)
    elif auth_type == "api_key":
        header = auth_cfg.get("header", "Authorization")
        key = auth_cfg.get("key", "")
        if key:
            kwargs["headers"][header] = key

    return kwargs


def _fetch_single_feed(
    feed_info: Dict,
    window_hours: int,
    max_items: int,
    timeout: int,
) -> List[Dict]:
    """Fetch one RSS feed and return a list of article dicts."""
    url = feed_info["url"]
    source_title = feed_info.get("title", url)
    category = feed_info.get("category", "未分类")
    articles: List[Dict] = []

    try:
        # feedparser can handle the request itself but doesn't support timeout;
        # download the raw bytes with requests first.
        request_kwargs = _build_request_kwargs(feed_info)
        resp = requests.get(url, timeout=timeout, **request_kwargs)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        if getattr(parsed, "bozo", False):
            # Malformed feeds slow things down; skip them directly.
            print(f"[RSS] ✗ {source_title} — 解析异常，跳过 ({parsed.bozo_exception})")
            return articles
    except requests.exceptions.RequestException as exc:
        print(f"[RSS] ✗ {source_title} — 访问异常，已跳过 ({exc.__class__.__name__})")
        return articles
    except Exception as exc:
        print(f"[RSS] ✗ {source_title} — 解析失败，已跳过 ({exc})")
        return articles

    now = datetime.now(tz=timezone.utc)
    cutoff = None
    if window_hours > 0:
        cutoff = now.replace(microsecond=0) - timedelta(hours=window_hours)

    count = 0
    for entry in parsed.entries:
        if count >= max_items:
            break

        pub_date = _parse_date(entry)

        # Apply time window filter only when we have a valid date
        if cutoff and pub_date and pub_date < cutoff:
            continue

        link = getattr(entry, "link", "") or ""
        if not link:
            links = getattr(entry, "links", []) or []
            for l in links:
                href = ""
                if isinstance(l, dict):
                    href = l.get("href", "")
                else:
                    href = getattr(l, "href", "")
                if href:
                    link = href
                    break
        title = getattr(entry, "title", "").strip()
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""

        if not title:
            continue

        articles.append(
            {
                "title": title,
                "link": link,
                "summary": summary[:500],
                "published": pub_date,
                "source": source_title,
                "category": category,
            }
        )
        count += 1

    print(f"[RSS] ✓ {source_title} — {len(articles)} 条")
    return articles


def fetch_all_articles(
    feeds: List[Dict[str, str]],
    window_hours: int = 24,
    max_items: int = DEFAULT_MAX_ITEMS,
    timeout: int = DEFAULT_TIMEOUT,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> List[Dict]:
    """Fetch articles from all *feeds* concurrently.

    Args:
        feeds: List of feed dicts from opml_fetcher.
        window_hours: Only include articles published within this many hours.
                      Use 0 to disable time filtering.
        max_items: Maximum articles to collect per feed.
        timeout: HTTP request timeout in seconds.
        max_workers: Thread pool size.

    Returns:
        Combined list of article dicts, newest first.
    """
    all_articles: List[Dict] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _fetch_single_feed, feed, window_hours, max_items, timeout
            ): feed
            for feed in feeds
        }
        for future in as_completed(futures):
            try:
                all_articles.extend(future.result())
            except Exception as exc:
                feed = futures[future]
                print(f"[RSS] 线程异常 {feed.get('title', '')}: {exc}")

    # Sort newest first; entries without a date go to the end
    all_articles.sort(
        key=lambda a: a["published"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    print(f"[RSS] 共获取 {len(all_articles)} 条资讯（时间窗口 {window_hours}h）")
    return all_articles

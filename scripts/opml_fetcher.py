"""
opml_fetcher.py
解析OPML文件，提取RSS订阅源信息（标题、URL、分类）。

支持标准的 OPML XML 格式，并对常见的格式错误（如未闭合标签）提供
基于正则表达式的降级解析方案。
"""

import re
import xml.etree.ElementTree as ET
from html import unescape
from typing import List, Dict

import requests

OPML_URL = "https://raw.githubusercontent.com/arch3rPro/SecurityRSS/main/SecurityRSS-Lite.opml"

# Regex to extract individual <outline> tag attributes from raw OPML text.
# Handles both self-closing and non-self-closing outline tags.
_OUTLINE_RE = re.compile(r"<outline\b([^>]*?)(?:/>|>)", re.DOTALL)
_ATTR_RE = re.compile(r'(\w+)=["\']([^"\']*)["\']')


def _extract_attr(tag_content: str, attr: str) -> str:
    """Extract a named attribute value from an outline tag's inner content."""
    for name, value in _ATTR_RE.findall(tag_content):
        if name.lower() == attr.lower():
            return unescape(value).strip()
    return ""


def _parse_opml_xml(content: str) -> List[Dict[str, str]]:
    """Parse well-formed OPML XML and return feed dicts."""
    feeds: List[Dict[str, str]] = []
    root = ET.fromstring(content)

    for category_node in root.findall("./body/outline"):
        category_name = category_node.get("title", "未分类")
        for feed_node in category_node.findall("./outline"):
            url = feed_node.get("xmlUrl", "").strip()
            if url:
                feeds.append(
                    {
                        "title": feed_node.get("title", ""),
                        "url": url,
                        "category": category_name,
                    }
                )
    return feeds


def _parse_opml_regex(content: str) -> List[Dict[str, str]]:
    """Fallback: parse OPML using regex for malformed/non-standard files.

    Reconstructs category context by tracking non-self-closing category outlines
    that appear before feed outlines (outlines with xmlUrl attributes).
    """
    feeds: List[Dict[str, str]] = []
    current_category = "未分类"

    for match in _OUTLINE_RE.finditer(content):
        attrs_str = match.group(1)
        url = _extract_attr(attrs_str, "xmlUrl")
        title = _extract_attr(attrs_str, "title")

        if url:
            # This is a feed outline
            feeds.append(
                {
                    "title": title,
                    "url": url,
                    "category": current_category,
                }
            )
        elif title and not url:
            # Likely a category grouping outline
            current_category = title

    return feeds


def parse_opml_content(content: str) -> List[Dict[str, str]]:
    """Parse OPML XML string and return a list of RSS feed dicts.

    Attempts strict XML parsing first; falls back to regex-based parsing
    when the XML is malformed (e.g., missing closing tags).

    Each returned dict contains:
      - title    : display name of the feed
      - url      : RSS/Atom feed URL (``xmlUrl`` attribute)
      - category : parent outline title used as category label
    """
    try:
        return _parse_opml_xml(content)
    except ET.ParseError:
        print("[OPML] XML格式异常，启用正则解析降级方案")
        return _parse_opml_regex(content)


def fetch_feeds_from_opml(opml_url: str = OPML_URL) -> List[Dict[str, str]]:
    """Download and parse the OPML file at *opml_url*.

    Returns a list of feed dicts on success, or an empty list on error.
    """
    try:
        response = requests.get(opml_url, timeout=30)
        response.raise_for_status()
        feeds = parse_opml_content(response.text)
        print(f"[OPML] 共加载 {len(feeds)} 个RSS订阅源")
        return feeds
    except Exception as exc:
        print(f"[OPML] 获取OPML失败: {exc}")
        return []

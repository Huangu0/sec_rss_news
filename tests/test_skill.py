"""
Unit tests for the sec_rss_news skill modules.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Allow imports from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# ---------------------------------------------------------------------------
# opml_fetcher tests
# ---------------------------------------------------------------------------

SAMPLE_OPML_GOOD = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
  <head><title>Test OPML</title></head>
  <body>
    <outline text="安全资讯" title="安全资讯">
      <outline text="FreeBuf" title="FreeBuf" type="rss" xmlUrl="https://www.freebuf.com/feed"/>
      <outline text="安全客" title="安全客" type="rss" xmlUrl="https://api.anquanke.com/data/v1/rss"/>
    </outline>
    <outline text="博客论坛" title="博客论坛">
      <outline text="PaperBlog" title="PaperBlog" type="rss" xmlUrl="http://paper.seebug.org/rss/"/>
    </outline>
  </body>
</opml>"""

# Malformed OPML: last category outline missing its closing tag
SAMPLE_OPML_MALFORMED = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
  <head><title>Test OPML</title></head>
  <body>
    <outline text="安全资讯" title="安全资讯">
      <outline text="FreeBuf" title="FreeBuf" type="rss" xmlUrl="https://www.freebuf.com/feed"/>
    </outline>
    <outline text="CTF&amp;靶场" title="CTF&amp;靶场">
      <outline text="CTFSite" title="CTFSite" type="rss" xmlUrl="https://ctfsite.example.com/feed"/>
  </body>
</opml>"""


class TestOpmlFetcher:
    def test_parse_good_opml(self):
        from opml_fetcher import parse_opml_content

        feeds = parse_opml_content(SAMPLE_OPML_GOOD)
        assert len(feeds) == 3
        urls = [f["url"] for f in feeds]
        assert "https://www.freebuf.com/feed" in urls
        assert "https://api.anquanke.com/data/v1/rss" in urls
        assert "http://paper.seebug.org/rss/" in urls

    def test_parse_opml_categories(self):
        from opml_fetcher import parse_opml_content

        feeds = parse_opml_content(SAMPLE_OPML_GOOD)
        by_cat = {f["url"]: f["category"] for f in feeds}
        assert by_cat["https://www.freebuf.com/feed"] == "安全资讯"
        assert by_cat["http://paper.seebug.org/rss/"] == "博客论坛"

    def test_parse_malformed_opml_falls_back_to_regex(self):
        from opml_fetcher import parse_opml_content

        feeds = parse_opml_content(SAMPLE_OPML_MALFORMED)
        assert len(feeds) >= 2
        urls = [f["url"] for f in feeds]
        assert "https://www.freebuf.com/feed" in urls
        assert "https://ctfsite.example.com/feed" in urls


# ---------------------------------------------------------------------------
# deduplicator tests
# ---------------------------------------------------------------------------

def _make_article(title: str, link: str = "", published=None, source="Test"):
    return {
        "title": title,
        "link": link,
        "summary": "",
        "published": published,
        "source": source,
        "category": "安全资讯",
    }


class TestDeduplicator:
    def test_url_dedup(self):
        from deduplicator import deduplicate_articles

        articles = [
            _make_article("文章A", "https://example.com/a"),
            _make_article("文章A (重复)", "https://example.com/a"),
            _make_article("文章B", "https://example.com/b"),
        ]
        result = deduplicate_articles(articles)
        assert len(result) == 2
        links = [a["link"] for a in result]
        assert links.count("https://example.com/a") == 1

    def test_title_fuzzy_dedup(self):
        from deduplicator import deduplicate_articles

        articles = [
            _make_article("CVE-2024-1234漏洞分析与利用", "https://example.com/1"),
            _make_article("CVE-2024-1234漏洞分析与利用研究", "https://example.com/2"),
            _make_article("完全不同的文章：Linux提权技术", "https://example.com/3"),
        ]
        result = deduplicate_articles(articles, similarity_threshold=0.8)
        # First two are very similar → should keep only one
        assert len(result) == 2

    def test_no_duplicates_preserved(self):
        from deduplicator import deduplicate_articles

        articles = [
            _make_article("文章A", "https://example.com/a"),
            _make_article("文章B", "https://example.com/b"),
            _make_article("文章C", "https://example.com/c"),
        ]
        result = deduplicate_articles(articles)
        assert len(result) == 3

    def test_empty_input(self):
        from deduplicator import deduplicate_articles

        assert deduplicate_articles([]) == []


# ---------------------------------------------------------------------------
# summarizer tests
# ---------------------------------------------------------------------------

class TestSummarizer:
    def _build_articles(self, titles):
        return [_make_article(t, f"https://example.com/{i}") for i, t in enumerate(titles)]

    def test_hotspot_grouping(self):
        from summarizer import analyze_hotspots

        articles = self._build_articles([
            "CVE漏洞利用技术分析",
            "CVE漏洞预警发布",
            "CVE漏洞修复方案",
            "Linux提权研究",
        ])
        hotspots, _ = analyze_hotspots(articles, min_articles=2)
        assert len(hotspots) >= 1
        keywords = [h["keyword"] for h in hotspots]
        # "CVE" or "CVE漏洞" should be a hotspot since 3 articles mention it
        assert any("CVE" in kw for kw in keywords)

    def test_empty_input(self):
        from summarizer import analyze_hotspots

        hotspots, articles = analyze_hotspots([])
        assert hotspots == []
        assert articles == []

    def test_returns_original_articles(self):
        from summarizer import analyze_hotspots

        orig = self._build_articles(["文章1", "文章2"])
        _, returned = analyze_hotspots(orig)
        assert returned is orig


# ---------------------------------------------------------------------------
# formatter tests
# ---------------------------------------------------------------------------

class TestFormatter:
    def _sample_article(self, title="Sample Title", link="https://example.com/1"):
        return {
            "title": title,
            "link": link,
            "summary": "Sample summary",
            "published": datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc),
            "source": "TestSource",
            "category": "安全资讯",
        }

    def test_daily_report_header(self):
        from formatter import format_report

        report_date = datetime(2026, 4, 13, tzinfo=timezone.utc)
        report = format_report([], [], mode="daily", report_date=report_date)
        assert "安全资讯日报" in report
        assert "2026-04-13" in report

    def test_weekly_report_header(self):
        from formatter import format_report

        report_date = datetime(2026, 4, 13, tzinfo=timezone.utc)
        report = format_report([], [], mode="weekly", report_date=report_date)
        assert "安全资讯周报" in report

    def test_hotspots_in_output(self):
        from formatter import format_report

        hotspots = [
            {
                "keyword": "CVE漏洞",
                "count": 3,
                "articles": [self._sample_article("CVE漏洞文章" + str(i)) for i in range(3)],
            }
        ]
        report = format_report(hotspots, [], mode="daily")
        assert "热点" in report
        assert "CVE漏洞" in report

    def test_articles_in_output(self):
        from formatter import format_report

        articles = [self._sample_article("测试文章标题")]
        report = format_report([], articles, mode="daily")
        assert "测试文章标题" in report
        assert "https://example.com/1" in report

    def test_markdown_structure(self):
        from formatter import format_report

        report = format_report([], [], mode="daily")
        assert report.startswith("#")
        assert "---" in report
        assert "生成时间" in report

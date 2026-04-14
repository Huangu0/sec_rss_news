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

    def test_keyword_summary_counts(self):
        from summarizer import keyword_summary

        articles = self._build_articles([
            "CVE漏洞分析",
            "CVE漏洞通告",
            "安全公告",
        ])
        summary = keyword_summary(articles, top_n=5)
        keywords = {item["keyword"] for item in summary}
        assert any("CVE" in kw for kw in keywords)


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

    def test_summary_section_present(self):
        from formatter import format_report

        summary = {
            "top_keywords": [{"keyword": "CVE", "count": 3}],
            "attention": [
                {
                    "keyword": "CVE",
                    "count": 3,
                    "headline": "CVE-2026-0001 漏洞预警",
                    "link": "https://example.com/cve",
                    "source": "TestSource",
                }
            ],
        }
        report = format_report([], [self._sample_article("占位")], summary=summary, mode="daily")
        assert "高频关键词" in report
        assert "需要注意" in report
        assert "CVE-2026-0001" in report
        assert "https://example.com/cve" in report


# ---------------------------------------------------------------------------
# scorer tests
# ---------------------------------------------------------------------------

class TestScorer:
    def _article(self, title="CVE漏洞分析", hours_ago=1.0, source="TestSource"):
        from datetime import timedelta
        pub = datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)
        return {
            "title": title,
            "link": "https://example.com/1",
            "summary": "",
            "published": pub,
            "source": source,
            "category": "安全资讯",
        }

    def test_newer_article_scores_higher(self):
        from scorer import score_article

        now = datetime.now(tz=timezone.utc)
        new = self._article(hours_ago=1)
        old = self._article(hours_ago=20)
        assert score_article(new, now=now) > score_article(old, now=now)

    def test_keyword_boost_doubles_score(self):
        from scorer import score_article

        now = datetime.now(tz=timezone.utc)
        base = self._article(title="普通文章")
        boosted = self._article(title="CVE漏洞高危预警")
        # Both same age; boosted should be ~2× score
        s_base = score_article(base, now=now, keyword_boosts=["CVE"])
        s_boost = score_article(boosted, now=now, keyword_boosts=["CVE"])
        assert abs(s_boost - s_base * 2) < 1e-9

    def test_source_weight_scales_score(self):
        from scorer import score_article

        now = datetime.now(tz=timezone.utc)
        art = self._article(source="WeightedSource")
        s1 = score_article(art, now=now, source_weights={"WeightedSource": 1.0})
        s2 = score_article(art, now=now, source_weights={"WeightedSource": 3.0})
        assert abs(s2 - s1 * 3) < 1e-9

    def test_no_date_gives_moderate_score(self):
        from scorer import score_article

        art = self._article()
        art["published"] = None
        score = score_article(art)
        assert 0 < score <= 2.0  # moderate, not zero

    def test_score_and_rank_hotspots_sorted(self):
        from scorer import score_and_rank_hotspots
        from datetime import timedelta

        now = datetime.now(tz=timezone.utc)
        hotspots = [
            {
                "keyword": "旧话题",
                "count": 2,
                "articles": [self._article(hours_ago=22), self._article(hours_ago=23)],
            },
            {
                "keyword": "新话题",
                "count": 2,
                "articles": [self._article(hours_ago=1), self._article(hours_ago=2)],
            },
        ]
        ranked = score_and_rank_hotspots(hotspots, now=now)
        assert ranked[0]["keyword"] == "新话题"
        assert ranked[0]["score"] > ranked[1]["score"]

    def test_score_and_rank_adds_score_field(self):
        from scorer import score_and_rank_hotspots

        hotspots = [{"keyword": "kw", "count": 1, "articles": [self._article()]}]
        result = score_and_rank_hotspots(hotspots)
        assert "score" in result[0]
        assert isinstance(result[0]["score"], float)


# ---------------------------------------------------------------------------
# persistence tests
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_filter_new_removes_seen(self, tmp_path):
        from persistence import ArticlePersistence

        store = ArticlePersistence(db_path=str(tmp_path / "test.db"))
        articles = [
            {"title": "文章A", "link": "https://example.com/a"},
            {"title": "文章B", "link": "https://example.com/b"},
        ]
        store.mark_seen(articles[:1])  # mark only article A

        new_only = store.filter_new(articles)
        assert len(new_only) == 1
        assert new_only[0]["title"] == "文章B"

    def test_mark_seen_idempotent(self, tmp_path):
        from persistence import ArticlePersistence

        store = ArticlePersistence(db_path=str(tmp_path / "test.db"))
        articles = [{"title": "文章A", "link": "https://example.com/a"}]
        store.mark_seen(articles)
        store.mark_seen(articles)  # second call should not raise
        assert store.count() == 1

    def test_count_returns_correct_number(self, tmp_path):
        from persistence import ArticlePersistence

        store = ArticlePersistence(db_path=str(tmp_path / "test.db"))
        assert store.count() == 0
        store.mark_seen([
            {"title": "文章A"},
            {"title": "文章B"},
            {"title": "文章C"},
        ])
        assert store.count() == 3

    def test_filter_new_empty_store(self, tmp_path):
        from persistence import ArticlePersistence

        store = ArticlePersistence(db_path=str(tmp_path / "test.db"))
        articles = [{"title": "新文章1"}, {"title": "新文章2"}]
        result = store.filter_new(articles)
        assert result == articles

    def test_purge_old_entries(self, tmp_path):
        """Articles marked more than retention_days ago should be purged."""
        import sqlite3
        from datetime import timedelta
        from persistence import ArticlePersistence, _fingerprint

        store = ArticlePersistence(db_path=str(tmp_path / "test.db"), retention_days=1)
        # Manually insert an old entry
        old_date = (datetime.now(tz=timezone.utc) - timedelta(days=2)).isoformat()
        with sqlite3.connect(store.db_path) as conn:
            conn.execute(
                "INSERT INTO seen_articles VALUES (?, ?, ?, ?)",
                (_fingerprint("old article"), "old article", old_date, old_date),
            )
            conn.commit()
        assert store.count() == 1

        # Calling mark_seen triggers purge
        store.mark_seen([{"title": "new article"}])
        # Old entry should be gone
        fps = store.get_seen_fingerprints()
        assert _fingerprint("old article") not in fps


# ---------------------------------------------------------------------------
# config_loader tests
# ---------------------------------------------------------------------------

class TestConfigLoader:
    def test_load_default_config_has_feeds_key(self):
        from config_loader import load_config

        cfg = load_config(None)
        assert "feeds" in cfg
        assert "schedule" in cfg

    def test_deep_merge(self):
        from config_loader import _deep_merge

        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 100}, "c": 4}
        result = _deep_merge(base, override)
        assert result["a"]["x"] == 1       # preserved from base
        assert result["a"]["y"] == 99      # overridden
        assert result["a"]["z"] == 100     # new key from override
        assert result["b"] == 3            # preserved from base
        assert result["c"] == 4            # new from override

    def test_load_json_config(self, tmp_path):
        import json
        from config_loader import load_config

        cfg_file = tmp_path / "my.json"
        cfg_file.write_text(json.dumps({"fetch": {"timeout_seconds": 99}}))
        cfg = load_config(str(cfg_file))
        assert cfg["fetch"]["timeout_seconds"] == 99

    def test_load_yaml_config(self, tmp_path):
        from config_loader import load_config

        cfg_file = tmp_path / "my.yaml"
        cfg_file.write_text("fetch:\n  timeout_seconds: 77\n")
        cfg = load_config(str(cfg_file))
        assert cfg["fetch"]["timeout_seconds"] == 77

    def test_missing_config_returns_defaults(self):
        from config_loader import load_config

        cfg = load_config("/nonexistent/path/config.yaml")
        assert isinstance(cfg, dict)

    def test_default_config_opml_url_present(self):
        from config_loader import load_config

        cfg = load_config(None)
        assert cfg.get("feeds", {}).get("opml_url", "")


# ---------------------------------------------------------------------------
# rss_fetcher auth tests
# ---------------------------------------------------------------------------

class TestRssFetcherAuth:
    def test_no_auth_returns_default_headers(self):
        from rss_fetcher import _build_request_kwargs

        kwargs = _build_request_kwargs({"url": "https://example.com/rss"})
        assert "User-Agent" in kwargs["headers"]
        assert "auth" not in kwargs

    def test_basic_auth_sets_auth_tuple(self):
        from rss_fetcher import _build_request_kwargs

        feed = {
            "url": "https://example.com/rss",
            "auth": {"type": "basic", "username": "alice", "password": "secret"},
        }
        kwargs = _build_request_kwargs(feed)
        assert kwargs["auth"] == ("alice", "secret")

    def test_api_key_auth_sets_header(self):
        from rss_fetcher import _build_request_kwargs

        feed = {
            "url": "https://example.com/rss",
            "auth": {"type": "api_key", "header": "X-API-Key", "key": "mykey123"},
        }
        kwargs = _build_request_kwargs(feed)
        assert kwargs["headers"]["X-API-Key"] == "mykey123"

    def test_api_key_default_header_name(self):
        from rss_fetcher import _build_request_kwargs

        feed = {
            "url": "https://example.com/rss",
            "auth": {"type": "api_key", "key": "tok"},
        }
        kwargs = _build_request_kwargs(feed)
        assert kwargs["headers"]["Authorization"] == "tok"


# ---------------------------------------------------------------------------
# skill_runner tests
# ---------------------------------------------------------------------------

class TestSkillRunner:
    """Smoke tests for skill_runner.run_skill using mocked network calls."""

    def _make_article(self, title: str, hours_ago: float = 1.0):
        from datetime import timedelta
        return {
            "title": title,
            "link": f"https://example.com/{title}",
            "summary": "",
            "published": datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago),
            "source": "TestSource",
            "category": "安全资讯",
        }

    def test_run_skill_returns_expected_keys(self, monkeypatch):
        from skill_runner import run_skill

        monkeypatch.setattr(
            "skill_runner.fetch_feeds_from_opml",
            lambda *a, **kw: [{"title": "T", "url": "u", "category": "c"}],
        )
        monkeypatch.setattr(
            "skill_runner.fetch_all_articles",
            lambda *a, **kw: [self._make_article(f"CVE-2024-{i:04d}漏洞预警") for i in range(6)],
        )

        result = run_skill({"mode": "daily", "output_format": "json"})
        assert "hotspots" in result
        assert "articles" in result
        assert "metadata" in result
        assert "report" in result
        assert "summary" in result

    def test_run_skill_metadata_counts(self, monkeypatch):
        from skill_runner import run_skill

        articles = [self._make_article(f"文章{i}") for i in range(5)]
        monkeypatch.setattr(
            "skill_runner.fetch_feeds_from_opml",
            lambda *a, **kw: [{"title": "T", "url": "u", "category": "c"}],
        )
        monkeypatch.setattr(
            "skill_runner.fetch_all_articles",
            lambda *a, **kw: articles,
        )

        result = run_skill({"mode": "daily"})
        assert result["metadata"]["total_articles"] == 5
        assert result["metadata"]["unique_articles"] <= 5

    def test_run_skill_markdown_output(self, monkeypatch):
        from skill_runner import run_skill

        monkeypatch.setattr(
            "skill_runner.fetch_feeds_from_opml",
            lambda *a, **kw: [{"title": "T", "url": "u", "category": "c"}],
        )
        monkeypatch.setattr(
            "skill_runner.fetch_all_articles",
            lambda *a, **kw: [self._make_article(f"CVE-2024-{i}") for i in range(4)],
        )

        result = run_skill({"mode": "daily", "output_format": "markdown"})
        assert result["report"].startswith("#")

    def test_run_skill_empty_feeds_uses_fallback(self, monkeypatch):
        from skill_runner import run_skill
        import skill_runner as sr

        calls = []

        def fake_fetch(url=None, *a, **kw):
            calls.append(url)
            return [{"title": "T", "url": "u", "category": "c"}]

        monkeypatch.setattr("skill_runner.fetch_feeds_from_opml", fake_fetch)
        monkeypatch.setattr(
            "skill_runner.fetch_all_articles",
            lambda *a, **kw: [],
        )
        # Force config to have no opml_url so fallback is triggered
        monkeypatch.setattr("skill_runner.load_config", lambda *a, **kw: {"feeds": {}})

        run_skill({"mode": "daily"})
        # Should have called fetch_feeds_from_opml (fallback)
        assert len(calls) >= 1

    def test_hotspots_have_score_field(self, monkeypatch):
        from skill_runner import run_skill

        monkeypatch.setattr(
            "skill_runner.fetch_feeds_from_opml",
            lambda *a, **kw: [{"title": "T", "url": "u", "category": "c"}],
        )
        # Enough articles so hotspots can form
        monkeypatch.setattr(
            "skill_runner.fetch_all_articles",
            lambda *a, **kw: [self._make_article(f"CVE漏洞预警{i}") for i in range(5)],
        )

        result = run_skill({"mode": "daily"})
        for h in result["hotspots"]:
            assert "score" in h
            assert isinstance(h["score"], float)

    def test_hotspots_capped_and_summary_present(self, monkeypatch):
        from skill_runner import run_skill

        def _build_articles():
            arts = []
            for i in range(12):
                arts.append(self._make_article(f"Topic{i} alert A"))
                arts.append(self._make_article(f"Topic{i} alert B"))
            return arts

        monkeypatch.setattr(
            "skill_runner.fetch_feeds_from_opml",
            lambda *a, **kw: [{"title": "T", "url": "u", "category": "c"}],
        )
        monkeypatch.setattr("skill_runner.deduplicate_articles", lambda arts, **kw: arts)
        monkeypatch.setattr("skill_runner.fetch_all_articles", lambda *a, **kw: _build_articles())

        result = run_skill({"mode": "daily", "max_hotspots": 20})
        assert len(result["hotspots"]) <= 10
        assert "summary" in result
        assert result["summary"]["top_keywords"]

---
name: sec-rss-news
description: >
  Periodically fetches configured RSS feeds, deduplicates articles by title similarity,
  scores them with configurable hotness rules (time decay, source weight, keyword boost),
  and produces a sorted structured hotspot article list.
  Use this skill when you need a hot-topic digest from multiple security RSS sources,
  want to track trending CVEs or threat topics, or need to generate a daily/weekly
  security news briefing in Markdown or JSON format.
license: MIT
compatibility: Python 3.9+; requires pip install -r requirements.txt
metadata:
  author: sec_rss_news
  version: "1.1.0"
  tags: security, rss, aggregation, hotspot, deduplication
---

# sec-rss-news — Security RSS Hotspot Aggregator

## Overview

This skill fetches articles from one or more RSS feeds, deduplicates them by title
(exact URL match + fuzzy title-similarity), scores each article's hotness using a
configurable formula (`time_decay × source_weight × keyword_boost`), clusters articles
into hotspot topics via keyword frequency, and returns a ranked list of hot topics
together with the full deduplicated article list.

Cross-run persistence (SQLite) is supported to avoid re-surfacing already-seen articles
across scheduling cycles.

---

## When to Use This Skill

- You need a structured security news digest (daily or weekly).
- You want to surface trending CVEs, threat campaigns, or vulnerability disclosures.
- You need to aggregate multiple RSS sources, remove duplicates, and rank by recency and relevance.
- You want Markdown briefing reports auto-generated on a schedule.

---

## Inputs

| Parameter      | Type               | Required | Default   | Description                                        |
|----------------|--------------------|----------|-----------|----------------------------------------------------|
| `mode`         | `"daily"\|"weekly"` | No       | `"daily"` | Time window: `daily` = last 24 h, `weekly` = last 7 d |
| `config_path`  | `string\|null`     | No       | `null`    | Path to a custom YAML/JSON config file             |
| `output_format`| `"json"\|"markdown"`| No      | `"json"`  | Output format                                      |
| `max_hotspots` | `integer\|null`    | No       | `null`    | Cap on returned hotspots (overrides config)        |

---

## Outputs

```json
{
  "hotspots": [
    {
      "keyword": "CVE漏洞",
      "score": 3.8742,
      "count": 5,
      "articles": [
        {
          "title": "CVE-2024-XXXX 高危漏洞预警",
          "link": "https://example.com/article",
          "summary": "...",
          "published": "2026-04-13T08:00:00+00:00",
          "source": "FreeBuf",
          "category": "安全资讯"
        }
      ]
    }
  ],
  "articles": [ /* full deduplicated article list */ ],
  "report": "# 🔐 安全资讯日报 ...",
  "metadata": {
    "total_articles": 120,
    "unique_articles": 84,
    "hotspot_count": 8,
    "generated_at": "2026-04-13T12:00:00+00:00",
    "mode": "daily"
  }
}
```

The `report` field contains a Markdown briefing (only when `output_format = "markdown"`).

---

## How to Invoke

### Python entry point (agentskill.io)

```python
from scripts.skill_runner import run_skill

result = run_skill({
    "mode": "daily",
    "output_format": "json",
    "max_hotspots": 10
})
```

### Command line — JSON output

```bash
python scripts/skill_runner.py --mode daily --format json
```

### Command line — Markdown report

```bash
python scripts/skill_runner.py --mode daily --format markdown
```

### Command line — legacy main (saves to output/ directory)

```bash
python scripts/main.py --mode daily --config config/default.yaml
```

---

## Configuration

All behaviour is governed by `config/default.yaml`. Pass a custom YAML/JSON file via
`--config <path>` or the `config_path` input to override any section.

### Key configuration sections

```yaml
feeds:
  opml_url: "https://..."       # OPML source list
  sources:                       # optional static sources with per-source auth & weight
    - title: MyFeed
      url: https://example.com/rss
      weight: 1.5
      auth:
        type: basic              # "basic" | "api_key"
        username: alice
        password: secret

scoring:
  time_decay_hours: 24           # exponential decay half-life
  source_weight_enabled: true    # use per-source weights from feeds.sources
  keyword_boost: [CVE, 漏洞, …] # title keywords that double the score

persistence:
  enabled: true                  # enable cross-run SQLite dedup
  path: data/seen_articles.db
  retention_days: 30
```

See `config/default.yaml` for all available options and inline comments.

---

## Hotness Score Formula

```
score(article) = time_decay × source_weight × keyword_multiplier

time_decay        = exp(−age_hours / decay_hours)   ∈ (0, 1]
source_weight     = per-source weight from config    (default 1.0)
keyword_multiplier = 2.0 if title contains a boost keyword, else 1.0
```

Hotspot score = sum of constituent articles' scores.

---

## Pipeline

```
OPML / static sources
        ↓
  fetch_all_articles()       [scripts/rss_fetcher.py]   — concurrent HTTP, auth support
        ↓
  deduplicate_articles()     [scripts/deduplicator.py]  — URL exact + title fuzzy dedup
        ↓
  ArticlePersistence         [scripts/persistence.py]   — SQLite cross-run dedup (opt.)
        ↓
  analyze_hotspots()         [scripts/summarizer.py]    — jieba keyword clustering
        ↓
  score_and_rank_hotspots()  [scripts/scorer.py]        — time decay + weight scoring
        ↓
  format_report() / JSON     [scripts/formatter.py]     — Markdown or JSON output
```

---

## Files

| Path                        | Purpose                                              |
|-----------------------------|------------------------------------------------------|
| `SKILL.md`                  | This file — agentskills.io skill manifest            |
| `config/default.yaml`       | Default configuration (feeds, scoring, persistence)  |
| `scripts/skill_runner.py`   | agentskill.io entry point (`run_skill`)              |
| `scripts/main.py`           | CLI entry point (saves Markdown to `output/`)        |
| `scripts/rss_fetcher.py`    | Concurrent RSS fetcher with Basic/API-key auth       |
| `scripts/deduplicator.py`   | URL-exact + fuzzy title deduplication                |
| `scripts/scorer.py`         | Hotness scoring and hotspot re-ranking               |
| `scripts/persistence.py`    | SQLite fingerprint store for cross-run dedup         |
| `scripts/summarizer.py`     | jieba keyword extraction and hotspot clustering      |
| `scripts/formatter.py`      | Markdown report formatter                            |
| `scripts/config_loader.py`  | YAML/JSON config loader with deep-merge              |
| `scripts/opml_fetcher.py`   | OPML parser (strict XML + regex fallback)            |
| `references/`               | Extended documentation                               |
| `workflow.yml`              | Skill pipeline definition                            |
| `requirements.txt`          | Python dependencies                                  |

---

## Dependencies

Install with:

```bash
pip install -r requirements.txt
```

Required packages: `feedparser`, `requests`, `python-dateutil`, `jieba`, `pyyaml`.
SQLite3 is bundled with Python's standard library.

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

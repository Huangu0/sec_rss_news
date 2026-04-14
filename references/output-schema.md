# Output Schema Reference

Detailed documentation for the JSON output of `run_skill()`.

---

## Top-level fields

| Field        | Type    | Description |
|--------------|---------|-------------|
| `hotspots`   | array   | Ranked hotspot topics (descending by `score`) |
| `articles`   | array   | Full deduplicated article list |
| `summary`    | object  | Digest of high-frequency keywords and watchlist items |
| `report`     | string  | Markdown briefing (`""` when `output_format = "json"`) |
| `metadata`   | object  | Run statistics |

---

## `hotspots[]`

Each element represents one keyword-based hotspot cluster.

| Field      | Type    | Description |
|------------|---------|-------------|
| `keyword`  | string  | The hot keyword or phrase |
| `score`    | float   | Aggregate hotness score (sum of constituent article scores) |
| `count`    | integer | Number of articles in this hotspot |
| `articles` | array   | Up to 10 representative articles (see `articles[]` schema below) |
> Returned hotspot count is always capped at 10 even if a higher value is requested.

---

## `articles[]`

| Field       | Type            | Description |
|-------------|-----------------|-------------|
| `title`     | string          | Article title |
| `link`      | string          | Article URL |
| `summary`   | string          | First 500 characters of the article summary |
| `published` | string \| null  | ISO 8601 datetime string, or `null` if unknown |
| `source`    | string          | RSS feed display name |
| `category`  | string          | Feed category |

---

## `summary`

Brief digest accompanying the hotspots.

| Field            | Type    | Description |
|------------------|---------|-------------|
| `top_keywords`   | array   | Ordered list of `{keyword, count}` pairs representing the most frequent keywords in the window |
| `attention`      | array   | Items that need attention, each with `{keyword, count, headline, link, source}`; derived from the top hotspots |

---

## `metadata`

| Field             | Type    | Description |
|-------------------|---------|-------------|
| `total_articles`  | integer | Raw article count before deduplication |
| `unique_articles` | integer | Article count after all deduplication steps |
| `hotspot_count`   | integer | Number of hotspots returned |
| `generated_at`    | string  | ISO 8601 UTC timestamp of the run |
| `mode`            | string  | `"daily"` or `"weekly"` |

---

## Full example response (JSON)

```json
{
  "hotspots": [
    {
      "keyword": "CVE漏洞",
      "score": 4.2189,
      "count": 4,
      "articles": [
        {
          "title": "CVE-2026-0001 RCE漏洞预警",
          "link": "https://www.freebuf.com/articles/cve-2026-0001",
          "summary": "研究人员披露了一个影响主流Web框架的高危RCE漏洞...",
          "published": "2026-04-13T08:00:00+00:00",
          "source": "FreeBuf",
          "category": "安全资讯"
        }
      ]
    }
  ],
  "articles": [ "..." ],
  "report": "",
  "metadata": {
    "total_articles": 98,
    "unique_articles": 67,
    "hotspot_count": 8,
    "generated_at": "2026-04-13T12:00:00+00:00",
    "mode": "daily"
  }
}
```

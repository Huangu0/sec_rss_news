# Configuration Reference

Full documentation for `config/default.yaml`.

---

## `feeds`

Controls which RSS sources are fetched.

| Key        | Type     | Default | Description |
|------------|----------|---------|-------------|
| `opml_url` | string   | SecurityRSS-Lite URL | URL of an OPML file listing RSS feeds |
| `sources`  | list     | `[]`    | Static RSS source entries (merged with OPML) |

### `feeds.sources[]` entry

| Key        | Type   | Default | Description |
|------------|--------|---------|-------------|
| `title`    | string | URL     | Display name used as source label |
| `url`      | string | —       | RSS/Atom feed URL (required) |
| `category` | string | `"未分类"` | Category label for grouping |
| `weight`   | float  | `1.0`   | Source weight for hotness scoring |
| `auth`     | object | `null`  | Optional authentication config |

### `feeds.sources[].auth`

Supported `type` values:

**`basic`** — HTTP Basic Authentication

```yaml
auth:
  type: basic
  username: alice
  password: secret123
```

**`api_key`** — Custom header-based API key

```yaml
auth:
  type: api_key
  header: X-API-Key    # request header name (default: Authorization)
  key: your-api-key
```

---

## `schedule`

| Key         | Type   | Default   | Description |
|-------------|--------|-----------|-------------|
| `frequency` | string | `"daily"` | Default mode when none is specified |

### `schedule.modes.daily`

| Key            | Type    | Default | Description |
|----------------|---------|---------|-------------|
| `window_hours` | integer | `24`    | Only fetch articles from the last N hours |
| `max_hotspots` | integer | `10`    | Maximum hotspots to return |

### `schedule.modes.weekly`

| Key            | Type    | Default | Description |
|----------------|---------|---------|-------------|
| `window_hours` | integer | `168`   | 7 days |
| `max_hotspots` | integer | `15`    | Maximum hotspots to return |

---

## `fetch`

| Key                   | Type    | Default | Description |
|-----------------------|---------|---------|-------------|
| `timeout_seconds`     | integer | `15`    | HTTP request timeout per feed |
| `max_workers`         | integer | `10`    | Thread pool size for concurrent fetching |
| `max_items_per_source`| integer | `20`    | Maximum articles collected per feed |

---

## `dedup`

| Key                          | Type    | Default | Description |
|------------------------------|---------|---------|-------------|
| `title_similarity_threshold` | float   | `0.8`   | SequenceMatcher ratio threshold (0–1). Titles above this are considered duplicates |
| `use_fingerprint`            | boolean | `false` | Reserved for future SHA-256 fingerprint matching |

---

## `scoring`

| Key                       | Type     | Default | Description |
|---------------------------|----------|---------|-------------|
| `time_decay_hours`        | float    | `24`    | Exponential decay half-life in hours |
| `source_weight_enabled`   | boolean  | `true`  | Whether to apply per-source weights |
| `keyword_boost`           | list     | see YAML| Keywords that multiply article score by ×2 |
| `top_keywords`            | integer  | `20`    | Max keywords extracted per run |
| `min_articles_per_hotspot`| integer  | `2`     | Articles needed for a keyword to become a hotspot |

### Hotness score formula

```
score(article) = time_decay × source_weight × keyword_multiplier

time_decay        = exp(−age_hours / time_decay_hours)
source_weight     = weight from feeds.sources[].weight  (default 1.0)
keyword_multiplier = 2.0  if title contains a keyword_boost entry
                   = 1.0  otherwise
```

Hotspot score = Σ score(article) for each article in the hotspot.

---

## `persistence`

| Key              | Type    | Default                    | Description |
|------------------|---------|----------------------------|-------------|
| `enabled`        | boolean | `false`                    | Enable cross-run SQLite dedup |
| `type`           | string  | `"sqlite"`                 | Storage backend (currently only `sqlite`) |
| `path`           | string  | `"data/seen_articles.db"`  | SQLite database file path |
| `retention_days` | integer | `30`                       | Fingerprints older than this many days are purged |

When enabled, every run persists the SHA-256 fingerprints of processed article titles.
The next run filters out any articles whose fingerprint was already stored, preventing
re-surfacing of previously seen content.

---

## `output`

| Key      | Type   | Default      | Description |
|----------|--------|--------------|-------------|
| `format` | string | `"markdown"` | Default output format for `main.py` (`markdown` \| `json`) |
| `dir`    | string | `"output"`   | Root directory for saved Markdown reports |

---

## Example: minimal custom config

```yaml
# my-config.yaml
feeds:
  sources:
    - title: My Internal Feed
      url: https://internal.example.com/rss
      weight: 2.0
      auth:
        type: api_key
        header: Authorization
        key: Bearer my-token

scoring:
  time_decay_hours: 12
  keyword_boost:
    - 勒索软件
    - ransomware

persistence:
  enabled: true
  path: /var/lib/sec-rss/seen.db
```

Run with:

```bash
python scripts/skill_runner.py --config my-config.yaml --mode daily --format markdown
```

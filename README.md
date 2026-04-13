# sec_rss_news

信息安全资讯 RSS 订阅整理 Skill — 遵循 [agentskills.io](https://agentskills.io) 规范打包。

定期抓取配置的 RSS 源，按标题去重并产出按热度排序的结构化热点文章列表，支持 Markdown 和 JSON 两种输出格式。

---

## Skill 规范（agentskills.io）

本项目遵循 [agentskills.io specification](https://agentskills.io/specification) 打包：

| 文件 / 目录 | 说明 |
|---|---|
| **`SKILL.md`** | Skill 清单（YAML frontmatter + Markdown 使用说明） |
| `scripts/` | 可执行脚本 |
| `references/` | 扩展文档（配置参考、输出 Schema） |
| `assets/` | 资源文件（预留） |

Skill 清单 `SKILL.md` 包含：
- `name: sec-rss-news`（唯一标识，小写，连字符分隔）
- `description`（技能用途及使用时机）
- `license`, `compatibility`, `metadata`（可选）
- Markdown 正文：输入/输出、调用方式、配置说明、Pipeline 图

---

## 功能特性

- **多源聚合**：从 OPML URL 或静态列表加载 RSS 源，并发抓取
- **认证支持**：每个源可独立配置 Basic 认证或 API Key 认证
- **过滤去重**：URL 精确去重 + 标题相似度模糊去重（SequenceMatcher，可配置阈值）
- **跨周期持久去重**：基于 SQLite 存储已见文章标题 SHA-256 指纹，防止重复推送
- **热度打分排序**：`score = time_decay × source_weight × keyword_multiplier`
  - `time_decay`：指数衰减（越新越高）
  - `source_weight`：可按源名配置权重
  - `keyword_multiplier`：标题命中关键词时 ×2
- **Markdown / JSON 输出**：结构清晰的日报/周报，可直接嵌入 Agent 工作流
- **YAML/JSON 配置**：所有参数集中在 `config/default.yaml`，支持自定义覆盖

---

## 项目结构

```
sec_rss_news/
├── SKILL.md                        # agentskills.io Skill 清单（必需）
├── workflow.yml                    # Skill Pipeline 定义
├── requirements.txt                # Python 依赖
├── config/
│   └── default.yaml               # 默认配置（feeds、scoring、persistence 等）
├── scripts/
│   ├── skill_runner.py             # agentskill.io 入口（run_skill）
│   ├── main.py                     # CLI 入口（保存 Markdown 到 output/）
│   ├── config_loader.py            # YAML/JSON 配置加载与深度合并
│   ├── opml_fetcher.py             # OPML 解析（支持格式降级）
│   ├── rss_fetcher.py              # 并发 RSS 抓取（Basic/API Key 认证）
│   ├── deduplicator.py             # URL 精确 + 标题模糊去重
│   ├── persistence.py              # SQLite 跨周期指纹持久化
│   ├── scorer.py                   # 热度打分与排序
│   ├── summarizer.py               # jieba 关键词分析与热点聚合
│   └── formatter.py                # Markdown 报告生成
├── references/
│   ├── configuration.md            # 配置项完整说明
│   └── output-schema.md            # 输出字段说明
├── tests/
│   └── test_skill.py               # 单元测试（41 个）
├── output/
│   ├── daily/                      # 每日报告（YYYY-MM-DD.md）
│   └── weekly/                     # 每周报告（YYYY-MM-DD.md）
└── .github/workflows/
    └── news.yml                    # GitHub Actions 自动化
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行 Skill（agentskill.io 入口）

```python
from scripts.skill_runner import run_skill

result = run_skill({
    "mode": "daily",          # "daily" | "weekly"
    "output_format": "json",  # "json" | "markdown"
    "max_hotspots": 10
})
# result["hotspots"]  — 按热度排序的热点列表（含 score 字段）
# result["articles"]  — 去重后全量资讯
# result["metadata"]  — 统计元数据
```

### 3. 命令行运行

```bash
# JSON 输出（标准输出）
python scripts/skill_runner.py --mode daily --format json

# Markdown 输出（标准输出）
python scripts/skill_runner.py --mode daily --format markdown

# 使用自定义配置
python scripts/skill_runner.py --config config/default.yaml --mode weekly

# 生成并保存 Markdown 报告到 output/ 目录
python scripts/main.py --mode daily --config config/default.yaml
```

---

## 配置

所有配置位于 `config/default.yaml`，通过 `--config` 参数或 `config_path` 输入覆盖。

关键配置示例：

```yaml
feeds:
  opml_url: "https://..."       # OPML 订阅源
  sources:
    - title: 内部情报
      url: https://internal.example.com/rss
      weight: 2.0
      auth:
        type: api_key
        header: X-API-Key
        key: your-key

scoring:
  time_decay_hours: 24          # 衰减半衰期（小时）
  keyword_boost: [CVE, 漏洞, RCE]

persistence:
  enabled: true                 # 开启跨周期去重
  path: data/seen_articles.db
  retention_days: 30
```

详见 [`references/configuration.md`](./references/configuration.md)。

---

## 输出示例

```json
{
  "hotspots": [
    { "keyword": "CVE漏洞", "score": 4.22, "count": 4, "articles": [...] }
  ],
  "articles": [...],
  "metadata": { "total_articles": 98, "unique_articles": 67, "hotspot_count": 8, ... }
}
```

Markdown 模式输出示例：

```markdown
# 🔐 安全资讯日报 · 2026-04-13

> 统计范围：近 24 小时
> 共收录 **67** 条资讯，发现 **8** 个热点话题

## 📊 热点话题

### 🔥 热点 1：CVE漏洞（4 条相关资讯）
- [CVE-2026-0001 RCE漏洞预警](https://...) — `FreeBuf` · 2026-04-13 08:00
...
```

---

## 运行测试

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## 自动化（GitHub Actions）

`.github/workflows/news.yml` 配置了两个定时任务：

| 触发 | 模式 | Cron |
|------|------|------|
| 每日 | daily | `0 2 * * *`（UTC 02:00） |
| 每周一 | weekly | `0 2 * * 1`（UTC 02:00 周一） |

---

## RSS 源

默认使用 [arch3rPro/SecurityRSS](https://github.com/arch3rPro/SecurityRSS) 提供的
`SecurityRSS-Lite.opml`，包含安全资讯、博客论坛、官网文章、国外博客、漏洞库等 9 个分类 140+ 个订阅源。
也可通过 `config/default.yaml` 的 `feeds.sources` 添加自定义源。

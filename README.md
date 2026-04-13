# sec_rss_news

信息安全资讯RSS订阅整理Skill

通过RSS源获取安全资讯，完成资讯的过滤去重，并整理输出热点资讯总结（Markdown格式），支持每日和每周两种模式。

---

## 功能特性

- **多源聚合**：从 [SecurityRSS-Lite](https://github.com/arch3rPro/SecurityRSS) OPML 文件中加载 140+ 个安全资讯RSS订阅源
- **过滤去重**：URL精确去重 + 标题相似度模糊去重（可配置阈值）
- **热点分析**：基于 jieba 中文分词的关键词频率统计，自动聚合热点话题
- **Markdown输出**：结构清晰的日报/周报 Markdown 文件
- **每日/每周**：支持 `daily`（近24小时）和 `weekly`（近7天）两种报告模式
- **自动化**：内置 GitHub Actions 工作流，每日/每周自动生成并提交报告

---

## 项目结构

```
sec_rss_news/
├── workflow.yml                    # 流程定义（Skill Pipeline）
├── requirements.txt                # Python依赖
├── scripts/
│   ├── main.py                     # 主入口（CLI）
│   ├── opml_fetcher.py             # 解析OPML获取RSS订阅源列表
│   ├── rss_fetcher.py              # 并发抓取RSS资讯
│   ├── deduplicator.py             # 去重过滤
│   ├── summarizer.py               # 热点关键词分析
│   └── formatter.py                # Markdown报告生成
├── tests/
│   └── test_skill.py               # 单元测试
├── output/
│   ├── daily/                      # 每日报告（YYYY-MM-DD.md）
│   └── weekly/                     # 每周报告（YYYY-MM-DD.md）
└── .github/workflows/
    └── news.yml                    # GitHub Actions 自动化
```

---

## Skill 流程定义

```
OPML解析 → RSS抓取（并发） → 去重过滤 → 热点分析 → Markdown输出
```

详见 [`workflow.yml`](./workflow.yml)。

---

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 生成每日简报

```bash
python scripts/main.py --mode daily
```

### 生成每周简报

```bash
python scripts/main.py --mode weekly
```

### 查看报告

报告默认保存至 `output/daily/YYYY-MM-DD.md` 或 `output/weekly/YYYY-MM-DD.md`。

### 更多选项

```
usage: main.py [-h] [--mode {daily,weekly}] [--output-dir OUTPUT_DIR]
               [--opml-url OPML_URL] [--print]

选项:
  --mode {daily,weekly}   输出模式：daily（近24h）或 weekly（近7天），默认 daily
  --output-dir OUTPUT_DIR Markdown报告输出目录，默认 output/
  --opml-url OPML_URL     OPML订阅源文件URL
  --print                 同时将报告打印到标准输出
```

---

## 输出示例

```markdown
# 🔐 安全资讯日报 · 2024-01-15

> 📅 数据来源：SecurityRSS-Lite
> 统计范围：近 24 小时
> 共收录 **42** 条资讯，发现 **8** 个热点话题

---

## 📊 热点话题

### 🔥 热点 1：CVE漏洞（5 条相关资讯）

- [CVE-2024-XXXX 高危漏洞分析](https://example.com/...) — `FreeBuf` · 2024-01-15 08:00
- ...

---

## 📰 全部资讯

### 安全资讯
- [标题](URL) — `来源` · 时间
...
```

---

## 自动化（GitHub Actions）

`.github/workflows/news.yml` 配置了两个定时任务：

| 触发 | 模式 | Cron |
|------|------|------|
| 每日 | daily | `0 2 * * *`（UTC 02:00） |
| 每周一 | weekly | `0 2 * * 1`（UTC 02:00 周一） |

也可在 Actions 页面手动触发并选择模式。

---

## 运行测试

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## RSS源

本项目使用 [arch3rPro/SecurityRSS](https://github.com/arch3rPro/SecurityRSS) 提供的
`SecurityRSS-Lite.opml`，包含安全资讯、博客论坛、官网文章、国外博客、漏洞库、漏洞预警、
实验室团队、武器工具库、CTF靶场等 9 个分类共 140+ 个订阅源。

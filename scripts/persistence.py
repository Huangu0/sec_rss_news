"""
persistence.py
基于 SQLite 的跨周期去重持久化。

将已处理文章的标题指纹（SHA-256）存入本地 SQLite 数据库，
下次运行时自动过滤已见文章，防止重复推送。
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Set


def _fingerprint(title: str) -> str:
    """Return SHA-256 hex digest of the lowercased, stripped title."""
    normalized = title.lower().strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class ArticlePersistence:
    """SQLite-backed store for seen article title fingerprints.

    Attributes:
        db_path: Path to the SQLite database file.
        retention_days: Fingerprints older than this many days are purged on
                        each :meth:`mark_seen` call.
    """

    def __init__(self, db_path: str = "data/seen_articles.db", retention_days: int = 30) -> None:
        self.db_path = Path(db_path)
        self.retention_days = retention_days
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create the database file and schema if they do not already exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_articles (
                    fingerprint TEXT PRIMARY KEY,
                    title       TEXT NOT NULL,
                    first_seen  TEXT NOT NULL,
                    last_seen   TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _purge_old(self, conn: sqlite3.Connection) -> None:
        """Delete fingerprints whose last_seen is older than retention_days."""
        cutoff = (
            datetime.now(tz=timezone.utc) - timedelta(days=self.retention_days)
        ).isoformat()
        conn.execute("DELETE FROM seen_articles WHERE last_seen < ?", (cutoff,))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_seen_fingerprints(self) -> Set[str]:
        """Return the full set of stored fingerprints."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT fingerprint FROM seen_articles").fetchall()
        return {r[0] for r in rows}

    def filter_new(self, articles: List[Dict]) -> List[Dict]:
        """Return only articles whose title fingerprint has not been seen before.

        Args:
            articles: List of article dicts (each must have a 'title' key).

        Returns:
            Subset of *articles* with unseen fingerprints.
        """
        seen = self.get_seen_fingerprints()
        return [a for a in articles if _fingerprint(a.get("title", "")) not in seen]

    def mark_seen(self, articles: List[Dict]) -> None:
        """Persist fingerprints for the given articles and purge old records.

        Uses ``INSERT OR REPLACE`` semantics so that ``last_seen`` is updated
        for articles that were already stored.

        Args:
            articles: List of article dicts to mark as seen.
        """
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            self._purge_old(conn)
            for article in articles:
                fp = _fingerprint(article.get("title", ""))
                title = article.get("title", "")
                conn.execute(
                    """
                    INSERT INTO seen_articles (fingerprint, title, first_seen, last_seen)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(fingerprint) DO UPDATE SET last_seen = excluded.last_seen
                    """,
                    (fp, title, now_iso, now_iso),
                )
            conn.commit()

    def count(self) -> int:
        """Return the total number of stored fingerprints."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM seen_articles").fetchone()[0]

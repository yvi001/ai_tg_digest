from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def migrate(conn: sqlite3.Connection, migrations_dir: Path = Path("migrations")) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
    applied = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
    for path in sorted(migrations_dir.glob("*.sql")):
        if path.name in applied:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_migrations(name) VALUES (?)", (path.name,))
    conn.commit()


def upsert_sources(conn: sqlite3.Connection, sources: Iterable[dict]) -> None:
    for s in sources:
        conn.execute(
            """
            INSERT INTO sources(id_or_username,type,weight,enabled)
            VALUES(?,?,?,?)
            ON CONFLICT(id_or_username) DO UPDATE SET type=excluded.type, weight=excluded.weight, enabled=excluded.enabled
            """,
            (s["id_or_username"], s["type"], s["weight"], int(s["enabled"])),
        )
    conn.commit()


def insert_raw_message(conn: sqlite3.Connection, payload: dict) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO raw_messages(
          source_id,tg_message_id,permalink,posted_at,text,views,forwards,reactions_count,comments_count,known_urls_json,dedup_status,canonical_news_id
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            payload["source_id"],
            payload["tg_message_id"],
            payload.get("permalink"),
            payload["posted_at"],
            payload.get("text"),
            payload.get("views"),
            payload.get("forwards"),
            payload.get("reactions_count"),
            payload.get("comments_count"),
            json.dumps(payload.get("known_urls", []), ensure_ascii=False),
            payload.get("dedup_status"),
            payload.get("canonical_news_id"),
        ),
    )


def create_canonical(conn: sqlite3.Connection, item: dict) -> int:
    cur = conn.execute(
        """
        INSERT INTO canonical_news(title_ru,summary_bullets_json,why_important_ru,labels_json,event_type,main_event_ru,importance_score,first_seen_at,last_seen_at,sources_count,raw_count,metadata_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            item.get("title_ru"),
            json.dumps(item.get("bullets_ru", []), ensure_ascii=False),
            item.get("why_important_ru"),
            json.dumps(item.get("labels", []), ensure_ascii=False),
            item.get("event_type"),
            item.get("main_event_ru"),
            item.get("importance_score", 0),
            item.get("first_seen_at", datetime.utcnow().isoformat()),
            item.get("last_seen_at", datetime.utcnow().isoformat()),
            item.get("sources_count", 1),
            item.get("raw_count", 1),
            json.dumps(item.get("metadata", {}), ensure_ascii=False),
        ),
    )
    return int(cur.lastrowid)

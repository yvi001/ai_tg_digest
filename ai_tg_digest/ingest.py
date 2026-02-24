from __future__ import annotations

from datetime import datetime, timedelta

from telethon import TelegramClient

from ai_tg_digest import db
from ai_tg_digest.config import AppSettings


def sync_sources(conn, settings: AppSettings) -> None:
    db.upsert_sources(conn, [s.model_dump() for s in settings.sources])


async def ingest_new_messages(conn, settings: AppSettings, limit_per_source: int = 200) -> int:
    sync_sources(conn, settings)
    total = 0
    async with TelegramClient(settings.tg_session, settings.tg_api_id, settings.tg_api_hash) as client:
        rows = conn.execute("SELECT id, id_or_username FROM sources WHERE enabled=1").fetchall()
        for row in rows:
            since = datetime.utcnow() - timedelta(days=settings.dedup_window_days)
            async for msg in client.iter_messages(row["id_or_username"], limit=limit_per_source):
                if not msg.message:
                    continue
                dt = msg.date.replace(tzinfo=None)
                if dt < since:
                    break
                known_urls = []
                if getattr(msg, "entities", None):
                    for e in msg.entities:
                        if hasattr(e, "url"):
                            known_urls.append(e.url)
                payload = {
                    "source_id": row["id"],
                    "tg_message_id": msg.id,
                    "permalink": f"https://t.me/{row['id_or_username'].lstrip('@')}/{msg.id}",
                    "posted_at": dt.isoformat(),
                    "text": msg.message,
                    "views": getattr(msg, "views", None),
                    "forwards": getattr(msg, "forwards", None),
                    "reactions_count": sum((r.count for r in getattr(getattr(msg, "reactions", None), "results", []) or []), 0),
                    "comments_count": getattr(msg, "replies", None).replies if getattr(msg, "replies", None) else None,
                    "known_urls": known_urls,
                }
                db.insert_raw_message(conn, payload)
                total += 1
        conn.commit()
    return total

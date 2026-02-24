from __future__ import annotations

from datetime import datetime, timedelta

from telethon import Button, TelegramClient, events

from ai_tg_digest.config import AppSettings


async def queue_digest(conn, settings: AppSettings, period: str, preview_text: str) -> int:
    auto_publish_at = datetime.utcnow() + timedelta(minutes=settings.auto_publish_after_minutes)
    cur = conn.execute(
        "INSERT INTO digests(period, scheduled_for, preview_text, status, auto_publish_at) VALUES(?,?,?,?,?)",
        (period, datetime.utcnow().isoformat(), preview_text, "queued", auto_publish_at.isoformat()),
    )
    digest_id = int(cur.lastrowid)
    conn.commit()

    async with TelegramClient(settings.tg_session, settings.tg_api_id, settings.tg_api_hash) as client:
        await client.send_message(
            settings.admin_dm_target,
            f"Предпросмотр дайджеста #{digest_id}\n\n{preview_text}",
            buttons=[
                [Button.inline("✅ Approve", data=f"approve:{digest_id}"), Button.inline("❌ Reject", data=f"reject:{digest_id}")]
            ],
        )
    return digest_id


async def publish_digest(conn, settings: AppSettings, digest_id: int) -> None:
    row = conn.execute("SELECT * FROM digests WHERE id=?", (digest_id,)).fetchone()
    if not row or row["status"] == "published":
        return
    async with TelegramClient(settings.tg_session, settings.tg_api_id, settings.tg_api_hash) as client:
        msg = await client.send_message(settings.target_channel, row["preview_text"])
    conn.execute("UPDATE digests SET status='published', published_message_id=? WHERE id=?", (msg.id, digest_id))
    conn.execute(
        "INSERT INTO publish_log(digest_id, target_channel, result, details) VALUES(?,?,?,?)",
        (digest_id, settings.target_channel, "ok", "manual/auto"),
    )
    conn.commit()


async def process_auto_publish(conn, settings: AppSettings) -> int:
    rows = conn.execute(
        "SELECT id FROM digests WHERE status='queued' AND auto_publish_at <= ?",
        (datetime.utcnow().isoformat(),),
    ).fetchall()
    for row in rows:
        await publish_digest(conn, settings, row["id"])
    return len(rows)


async def run_moderation_listener(conn, settings: AppSettings) -> None:
    client = TelegramClient(settings.tg_session, settings.tg_api_id, settings.tg_api_hash)

    @client.on(events.CallbackQuery)
    async def handler(event):  # noqa: ANN001
        data = event.data.decode("utf-8")
        action, digest_id = data.split(":", 1)
        digest_id = int(digest_id)
        if action == "approve":
            await publish_digest(conn, settings, digest_id)
            conn.execute("INSERT INTO moderation_actions(digest_id, action, actor) VALUES(?,?,?)", (digest_id, "approve", str(event.sender_id)))
            await event.answer("Опубликовано")
        else:
            conn.execute("UPDATE digests SET status='rejected' WHERE id=?", (digest_id,))
            conn.execute("INSERT INTO moderation_actions(digest_id, action, actor) VALUES(?,?,?)", (digest_id, "reject", str(event.sender_id)))
            await event.answer("Отклонено")
        conn.commit()

    await client.start()
    await client.run_until_disconnected()

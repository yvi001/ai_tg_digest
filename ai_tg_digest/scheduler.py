from __future__ import annotations

import asyncio

from apscheduler.schedulers.blocking import BlockingScheduler

from ai_tg_digest import db
from ai_tg_digest.config import load_settings
from ai_tg_digest.ingest import ingest_new_messages
from ai_tg_digest.moderation import process_auto_publish, queue_digest
from ai_tg_digest.pipeline import build_digest_text, process_new_messages


def run_scheduler(config_file: str = "config.yaml") -> None:
    settings = load_settings(config_file)
    conn = db.connect(settings.db_path)
    db.migrate(conn)

    sched = BlockingScheduler()

    def cycle_ingest():
        asyncio.run(ingest_new_messages(conn, settings))
        process_new_messages(conn, settings)
        asyncio.run(process_auto_publish(conn, settings))

    def queue_period(period: str):
        preview = build_digest_text(conn, period, settings)
        asyncio.run(queue_digest(conn, settings, period, preview))

    hm1 = settings.morning_time.split(":")
    hm2 = settings.evening_time.split(":")
    sched.add_job(cycle_ingest, "interval", minutes=15)
    sched.add_job(lambda: queue_period("morning"), "cron", hour=int(hm1[0]), minute=int(hm1[1]))
    sched.add_job(lambda: queue_period("evening"), "cron", hour=int(hm2[0]), minute=int(hm2[1]))
    sched.start()

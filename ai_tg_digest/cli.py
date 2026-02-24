from __future__ import annotations

import asyncio

import typer

from ai_tg_digest import db
from ai_tg_digest.config import load_settings
from ai_tg_digest.ingest import ingest_new_messages, sync_sources
from ai_tg_digest.moderation import queue_digest
from ai_tg_digest.pipeline import build_digest_text, process_new_messages
from ai_tg_digest.scheduler import run_scheduler

app = typer.Typer()
sources_app = typer.Typer()
db_app = typer.Typer()
app.add_typer(sources_app, name="sources")
app.add_typer(db_app, name="db")


@app.command("ingest")
def ingest_cmd(config: str = "config.yaml"):
    settings = load_settings(config)
    conn = db.connect(settings.db_path)
    db.migrate(conn)
    count = asyncio.run(ingest_new_messages(conn, settings))
    typer.echo(f"Ingested {count} raw messages")


@app.command("process")
def process_cmd(config: str = "config.yaml"):
    settings = load_settings(config)
    conn = db.connect(settings.db_path)
    db.migrate(conn)
    count = process_new_messages(conn, settings)
    typer.echo(f"Processed {count} messages")


@app.command("build-digest")
def build_digest(period: str = typer.Option(..., help="morning|evening"), dry_run: bool = True, config: str = "config.yaml"):
    settings = load_settings(config)
    conn = db.connect(settings.db_path)
    db.migrate(conn)
    text = build_digest_text(conn, period, settings)
    typer.echo(text)
    if not dry_run:
        typer.echo("Use queue-digest for moderation flow")


@app.command("queue-digest")
def queue_digest_cmd(period: str = typer.Option(..., help="morning|evening"), config: str = "config.yaml"):
    settings = load_settings(config)
    conn = db.connect(settings.db_path)
    db.migrate(conn)
    text = build_digest_text(conn, period, settings)
    digest_id = asyncio.run(queue_digest(conn, settings, period, text))
    typer.echo(f"Queued digest #{digest_id}")


@app.command("run-scheduler")
def run_scheduler_cmd(config: str = "config.yaml"):
    run_scheduler(config)


@sources_app.command("list")
def list_sources(config: str = "config.yaml"):
    settings = load_settings(config)
    conn = db.connect(settings.db_path)
    db.migrate(conn)
    for row in conn.execute("SELECT * FROM sources ORDER BY id"):
        typer.echo(f"{row['id']}: {row['id_or_username']} ({row['type']}) w={row['weight']} enabled={row['enabled']}")


@sources_app.command("add")
def add_source(id_or_username: str, type: str = "channel", weight: float = 1.0, enabled: bool = True, config: str = "config.yaml"):
    settings = load_settings(config)
    conn = db.connect(settings.db_path)
    db.migrate(conn)
    db.upsert_sources(conn, [{"id_or_username": id_or_username, "type": type, "weight": weight, "enabled": enabled}])
    typer.echo("Added")


@sources_app.command("remove")
def remove_source(id_or_username: str, config: str = "config.yaml"):
    settings = load_settings(config)
    conn = db.connect(settings.db_path)
    db.migrate(conn)
    conn.execute("DELETE FROM sources WHERE id_or_username=?", (id_or_username,))
    conn.commit()
    typer.echo("Removed")


@db_app.command("init")
@db_app.command("migrate")
def migrate_cmd(config: str = "config.yaml"):
    settings = load_settings(config)
    conn = db.connect(settings.db_path)
    db.migrate(conn)
    sync_sources(conn, settings)
    typer.echo("DB ready")


if __name__ == "__main__":
    app()

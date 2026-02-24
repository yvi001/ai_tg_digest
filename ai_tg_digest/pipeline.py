from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from ai_tg_digest import db
from ai_tg_digest.config import AppSettings
from ai_tg_digest.llm import OpenAICompatClient, load_prompt, render
from ai_tg_digest.utils import normalize_url, text_similarity

LABELS = ["NLP", "RAG", "AGENTS", "GRAPHS", "CLASSIC_ML", "TIME_SERIES", "FRAMEWORKS"]


def compute_importance(raw: dict, source_weight: float, hours_old: float) -> float:
    base = (
        (raw.get("forwards") or 0) * 4
        + (raw.get("reactions_count") or 0) * 3
        + (raw.get("views") or 0) * 1
        + (raw.get("comments_count") or 0) * 0.5
    )
    decay = 1 / (1 + hours_old / 24)
    score = min(100.0, base * source_weight * decay / 5)
    return round(score, 2)


def find_or_create_canonical(conn, extracted: dict, text: str, settings: AppSettings) -> int:
    urls = [u.get("normalized_url") for u in extracted.get("external_urls", []) if u.get("normalized_url")]
    if urls:
        q = "SELECT canonical_news_id FROM canonical_links WHERE normalized_url IN ({}) LIMIT 1".format(",".join("?" * len(urls)))
        row = conn.execute(q, urls).fetchone()
        if row:
            return row["canonical_news_id"]

    since = (datetime.utcnow() - timedelta(days=settings.dedup_window_days)).isoformat()
    candidates = conn.execute("SELECT id, main_event_ru FROM canonical_news WHERE last_seen_at >= ?", (since,)).fetchall()
    for c in candidates:
        if text_similarity(text, c["main_event_ru"] or "") >= settings.sim_threshold:
            return c["id"]

    return db.create_canonical(conn, {"main_event_ru": extracted.get("main_event_ru"), "event_type": extracted.get("event_type")})


def process_new_messages(conn, settings: AppSettings) -> int:
    llm = OpenAICompatClient(settings.openai_base_url, settings.openai_api_key, settings.openai_model)
    s_ext, u_ext = load_prompt("prompt_a_extraction.txt")
    s_cls, u_cls = load_prompt("prompt_b_multilabel.txt")
    s_sum, u_sum = load_prompt("prompt_c_summary.txt")

    rows = conn.execute(
        """
        SELECT rm.*, s.weight FROM raw_messages rm
        JOIN sources s ON s.id=rm.source_id
        WHERE rm.canonical_news_id IS NULL
        ORDER BY rm.posted_at DESC
        """
    ).fetchall()

    for row in rows:
        extracted = llm.complete_json(
            s_ext,
            render(
                u_ext,
                post_text=row["text"] or "",
                post_permalink=row["permalink"] or "",
                known_urls_from_api_json=row["known_urls_json"] or "[]",
            ),
        )
        canonical_id = find_or_create_canonical(conn, extracted, row["text"] or "", settings)
        cls = llm.complete_json(
            s_cls,
            render(
                u_cls,
                title_ru=extracted.get("main_event_ru") or "",
                main_event_ru=extracted.get("main_event_ru") or "",
                post_text=row["text"] or "",
                external_urls_json=extracted.get("external_urls", []),
            ),
        )
        summary = llm.complete_json(
            s_sum,
            render(
                u_sum,
                title_hint=extracted.get("main_event_ru") or "",
                main_event_ru=extracted.get("main_event_ru") or "",
                event_type=extracted.get("event_type") or "прочее",
                post_text=row["text"] or "",
                external_urls_json=extracted.get("external_urls", []),
                signals_json=extracted.get("signals", {}),
            ),
        )

        hours_old = (datetime.utcnow() - datetime.fromisoformat(row["posted_at"])).total_seconds() / 3600
        importance = compute_importance(dict(row), row["weight"], hours_old)

        conn.execute(
            "UPDATE raw_messages SET canonical_news_id=?, dedup_status=? WHERE id=?",
            (canonical_id, "linked", row["id"]),
        )
        for link in extracted.get("external_urls", []):
            norm = normalize_url(link.get("normalized_url") or link.get("url") or "")
            if norm:
                conn.execute(
                    "INSERT OR IGNORE INTO canonical_links(canonical_news_id, normalized_url, domain) VALUES(?,?,?)",
                    (canonical_id, norm, link.get("domain")),
                )
        conn.execute(
            """
            UPDATE canonical_news
            SET title_ru=?, summary_bullets_json=?, why_important_ru=?, labels_json=?, event_type=?, main_event_ru=?, importance_score=MAX(importance_score,?),
                last_seen_at=?, raw_count=raw_count+1
            WHERE id=?
            """,
            (
                summary.get("title_ru"),
                __import__("json").dumps(summary.get("bullets_ru", []), ensure_ascii=False),
                summary.get("why_important_ru"),
                __import__("json").dumps(cls.get("labels", []), ensure_ascii=False),
                extracted.get("event_type"),
                extracted.get("main_event_ru"),
                importance,
                datetime.utcnow().isoformat(),
                canonical_id,
            ),
        )
    conn.commit()
    return len(rows)


def build_digest_text(conn, period: str, settings: AppSettings) -> str:
    rows = conn.execute(
        "SELECT * FROM canonical_news ORDER BY importance_score DESC LIMIT ?",
        (settings.max_items_per_digest,),
    ).fetchall()
    per_cat = defaultdict(int)
    sections: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        labels = __import__("json").loads(r["labels_json"] or "[]")
        sorted_labels = sorted(labels, key=lambda x: x.get("confidence", 0), reverse=True)
        best = sorted_labels[0]["label"] if sorted_labels else "FRAMEWORKS"
        if per_cat[best] >= settings.max_items_per_category:
            continue
        per_cat[best] += 1
        bullets = __import__("json").loads(r["summary_bullets_json"] or "[]")
        tags = [x["label"] for x in sorted_labels[1:]]
        body = f"• {r['title_ru']}" + (f" [теги: {', '.join(tags)}]" if tags else "")
        for b in bullets[:6]:
            body += f"\n  - {b}"
        body += f"\n  Почему важно: {r['why_important_ru']}"
        links = conn.execute("SELECT normalized_url FROM canonical_links WHERE canonical_news_id=? LIMIT 3", (r["id"],)).fetchall()
        if links:
            body += "\n  Источники: " + ", ".join(l["normalized_url"] for l in links)
        sections[best].append(body)

    title = "Утренний" if period == "morning" else "Вечерний"
    text = [f"{title} AI-дайджест", ""]
    for cat in LABELS:
        if sections.get(cat):
            text.append(f"## {cat}")
            text.extend(sections[cat])
            text.append("")
    return "\n".join(text).strip()

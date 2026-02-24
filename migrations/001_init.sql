CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  id_or_username TEXT UNIQUE NOT NULL,
  type TEXT NOT NULL,
  weight REAL NOT NULL DEFAULT 1.0,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id INTEGER NOT NULL,
  tg_message_id INTEGER NOT NULL,
  permalink TEXT,
  posted_at TEXT NOT NULL,
  text TEXT,
  views INTEGER,
  forwards INTEGER,
  reactions_count INTEGER,
  comments_count INTEGER,
  known_urls_json TEXT,
  dedup_status TEXT,
  canonical_news_id INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(source_id, tg_message_id)
);

CREATE TABLE IF NOT EXISTS canonical_news (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title_ru TEXT,
  summary_bullets_json TEXT,
  why_important_ru TEXT,
  labels_json TEXT,
  event_type TEXT,
  main_event_ru TEXT,
  importance_score REAL DEFAULT 0,
  first_seen_at TEXT,
  last_seen_at TEXT,
  sources_count INTEGER DEFAULT 0,
  raw_count INTEGER DEFAULT 0,
  metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS canonical_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  canonical_news_id INTEGER NOT NULL,
  normalized_url TEXT NOT NULL,
  domain TEXT,
  UNIQUE(canonical_news_id, normalized_url)
);

CREATE TABLE IF NOT EXISTS digests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  period TEXT NOT NULL,
  scheduled_for TEXT NOT NULL,
  preview_text TEXT,
  status TEXT NOT NULL,
  published_message_id INTEGER,
  auto_publish_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS moderation_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  digest_id INTEGER NOT NULL,
  action TEXT NOT NULL,
  actor TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS publish_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  digest_id INTEGER NOT NULL,
  target_channel TEXT NOT NULL,
  result TEXT NOT NULL,
  details TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

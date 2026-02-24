# AI Telegram Digest (MVP)

Python MVP для агрегации AI/ML новостей из Telegram (каналы+группы), дедупликации, multi-label разметки, сборки RU-дайджеста и очереди модерации с авто-публикацией.

## Возможности
- Ingest через user session Telethon (поддержка приватных источников).
- Дедуп: сильное совпадение по normalized URL + fallback по semantic similarity.
- Importance score 0..100 по сигналам: forwards > reactions > views > comments + weight + time decay.
- OpenAI-compatible LLM пайплайн: extraction, multi-label, summary (JSON only, retries).
- Два дайджеста в день (утро/вечер), лимиты по количеству и категориям.
- Модерация: preview в DM с кнопками Approve/Reject + авто-публикация по таймауту.
- SQLite + SQL migrations.

## Быстрый старт
1. Установить зависимости:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[test]
```
2. Скопировать конфиг:
```bash
cp config.example.yaml config.yaml
```
3. Заполнить Telegram/OpenAI параметры и sources.
4. Инициализировать БД:
```bash
aidigest db init --config config.yaml
```

## Telegram session
- `TG_SESSION` можно дать как имя файла сессии (Telethon создаст локально `.session`).
- При первом запуске `aidigest ingest` Telethon попросит код входа в Telegram.

## CLI
```bash
aidigest ingest --config config.yaml
aidigest process --config config.yaml
aidigest build-digest --period morning --dry-run --config config.yaml
aidigest queue-digest --period evening --config config.yaml
aidigest run-scheduler --config config.yaml

aidigest sources list --config config.yaml
aidigest sources add @new_source --type channel --weight 1.3 --config config.yaml
aidigest sources remove @new_source --config config.yaml

aidigest db migrate --config config.yaml
```

## Scheduler
`run-scheduler` запускает:
- ingest/process/auto-publish каждые 15 минут;
- queue morning/evening дайджестов по `MORNING_TIME` и `EVENING_TIME`.

## Тесты
```bash
pytest
```

## Prompt templates
Промпты находятся в `prompts/`:
- `prompt_a_extraction.txt`
- `prompt_b_multilabel.txt`
- `prompt_c_summary.txt`

## Troubleshooting: `pip install -e .[test]`
Если видите ошибку `Multiple top-level packages discovered in a flat-layout`, обычно причина — конфликт при merge в `pyproject.toml` и потеря секции setuptools.

Проверьте, что в `pyproject.toml` есть блок:
```toml
[tool.setuptools]
packages = ["ai_tg_digest"]
include-package-data = true
```

И что в репозитории присутствуют `setup.py` и `setup.cfg` с явным пакетом `ai_tg_digest` (fallback для разных связок pip/setuptools).

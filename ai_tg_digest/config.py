from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SourceConfig(BaseModel):
    id_or_username: str
    type: Literal["channel", "group"] = "channel"
    weight: float = 1.0
    enabled: bool = True


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    db_path: Path = Path("digest.db")

    tg_api_id: int = Field(alias="TG_API_ID")
    tg_api_hash: str = Field(alias="TG_API_HASH")
    tg_session: str = Field(alias="TG_SESSION")

    target_channel: str = Field(alias="TARGET_CHANNEL")
    admin_dm_target: str = Field(default="self", alias="ADMIN_DM_TARGET")

    openai_base_url: str = Field(alias="OPENAI_BASE_URL")
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_model: str = Field(alias="OPENAI_MODEL")

    dedup_window_days: int = Field(default=7, alias="DEDUP_WINDOW_DAYS")
    sim_threshold: float = Field(default=0.85, alias="SIM_THRESHOLD")

    morning_time: str = Field(default="09:00", alias="MORNING_TIME")
    evening_time: str = Field(default="19:00", alias="EVENING_TIME")
    max_items_per_digest: int = Field(default=10, alias="MAX_ITEMS_PER_DIGEST")
    max_items_per_category: int = Field(default=3, alias="MAX_ITEMS_PER_CATEGORY")

    auto_publish_after_minutes: int = Field(default=120, alias="AUTO_PUBLISH_AFTER_MINUTES")

    sources: list[SourceConfig] = Field(default_factory=list)


def load_settings(config_file: str = "config.yaml") -> AppSettings:
    path = Path(config_file)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    return AppSettings(**data)

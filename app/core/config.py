# रिपॉजिटरी पथ: rti_backend/app/core/config.py
"""ऐप की कॉन्फ़िगरेशन environment variables से पढ़ें."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """संवेदनशील मान केवल hosting environment में रखें."""

    app_name: str = os.getenv("APP_NAME", "RTI Intelligence Platform API")
    app_env: str = os.getenv("APP_ENV", "production")
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")
    database_url: str | None = os.getenv("DATABASE_URL")
    database_connect_timeout: int = int(os.getenv("DATABASE_CONNECT_TIMEOUT", "5"))
    admin_id: str | None = os.getenv("ADMIN_ID")
    admin_pass: str | None = os.getenv("ADMIN_PASS")
    admin_session_secret: str | None = os.getenv("ADMIN_SESSION_SECRET")
    crawler_timeout_seconds: int = int(os.getenv("CRAWLER_TIMEOUT_SECONDS", "20"))
    crawler_max_bytes: int = int(os.getenv("CRAWLER_MAX_BYTES", "12000000"))
    crawler_poll_seconds: int = int(os.getenv("CRAWLER_POLL_SECONDS", "2"))
    # After a completed job, poll again after two seconds; keep jobs sequential.
    crawler_idle_seconds: int = int(os.getenv("CRAWLER_IDLE_SECONDS", "2"))
    crawler_links_per_page: int = int(os.getenv("CRAWLER_LINKS_PER_PAGE", "25"))
    crawler_max_pages_per_source: int = int(os.getenv("CRAWLER_MAX_PAGES_PER_SOURCE", "250"))
    crawler_recrawl_hours: int = int(os.getenv("CRAWLER_RECRAWL_HOURS", "24"))
    scheduler_token: str | None = os.getenv("OFFICIAL_DISCOVERY_TOKEN")
    scheduler_max_jobs_per_run: int = int(os.getenv("OFFICIAL_DISCOVERY_MAX_JOBS", "6"))
    data_gov_api_key: str | None = os.getenv("DATA_GOV_API_KEY")
    data_gov_resource_ids: str = os.getenv("DATA_GOV_RESOURCE_IDS", "")
    data_gov_api_page_limit: int = int(os.getenv("DATA_GOV_API_PAGE_LIMIT", "100"))
    # Optional OpenAI-compatible gateway (e.g. self-hosted FreeLLMAPI).
    llm_api_base_url: str | None = os.getenv("LLM_API_BASE_URL")
    llm_api_key: str | None = os.getenv("LLM_API_KEY")
    llm_model: str | None = os.getenv("LLM_MODEL")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))


settings = Settings()

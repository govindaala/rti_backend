# रिपॉजिटरी पथ: rti_backend/app/core/config.py
"""ऐप की कॉन्फ़िगरेशन को environment variables से पढ़ें."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """ऐप की आवश्यक सेटिंग्स; संवेदनशील मान source code में न रखें."""

    app_name: str = os.getenv("APP_NAME", "RTI Intelligence Platform API")
    app_env: str = os.getenv("APP_ENV", "development")
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")
    firestore_project_id: str | None = os.getenv("FIRESTORE_PROJECT_ID")


# पूरे ऐप में एक ही immutable configuration उपयोग करें।
settings = Settings()

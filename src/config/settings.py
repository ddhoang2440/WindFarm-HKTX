from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "WindFarm Monitoring System"
    app_version: str = "0.1.0"
    environment: str = "development"   # development | staging | production
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: list[str] = ["*"]

    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "windfarm"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Datadog
    dd_agent_host: str = "localhost"
    dd_trace_agent_port: int = 8126
    dd_service: str = "windfarm-backend"
    dd_env: str = "development"
    dd_api_key: str = ""
    dd_app_key: str = ""

    # AI Model
    model_path: str = "src/modules/AI_Agent/model_weights/fault_classifier.pkl"

    # Encryption (cho Settings module)
    encryption_key: str = "change-me-32-bytes-key-in-production"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
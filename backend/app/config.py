from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "student-evaluation-system-backend"
    APP_ENV: str = "dev"
    API_PREFIX: str = "/api"
    CORS_ORIGINS: str | None = None

    # DB
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "student_evaluation_system"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # Azure AI / Semantic Kernel
    AZURE_AI_AGENT_ENDPOINT: str | None = None
    AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME: str | None = None
    # Prefer user's env var naming if present
    AZURE_BING_CONNECTION_NAME: str | None = None
    AZURE_BING_GROUNDING_CONNECTION_NAME: str | None = None
    
    # Supported models configuration
    SUPPORTED_MODELS: str = "gpt-4o,o3-mini"
    DEFAULT_MODEL: str = "gpt-4o"

    # Storage
    STORAGE_DIR: str = "./storage"

    # Azure Document Intelligence
    AZURE_DI_ENDPOINT: str | None = None
    AZURE_DI_KEY: str | None = None

    # Pairwise comparison (Bradley–Terry) config
    PAIRWISE_K: int = 1
    PAIRWISE_EPS: float = 0.3

    # Special institution context files (optional)
    CHINA_RULES_TXT_PATH: str | None = None
    INDIA_RULES_TXT_PATH: str | None = None

    # JWT Authentication
    JWT_SECRET_KEY: str = "your-secret-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def celery_broker(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def celery_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    @property
    def bing_connection_name(self) -> str | None:
        return self.AZURE_BING_CONNECTION_NAME or self.AZURE_BING_GROUNDING_CONNECTION_NAME
    
    @property
    def supported_models(self) -> list[str]:
        return [model.strip() for model in self.SUPPORTED_MODELS.split(",") if model.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

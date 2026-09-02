from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    database_url: str
    project_repository: str
    llm_provider: str
    gemini_api_key: str
    gemini_model: str
    cors_origins: tuple[str, ...]
    integration_service_token: str
    export_signing_secret: str

    @classmethod
    def from_env(cls) -> "Settings":
        repository = os.getenv("PROJECT_REPOSITORY", "memory").lower()
        provider = os.getenv("LLM_PROVIDER", "mock").lower()
        database_url = os.getenv("DATABASE_URL", "")
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if repository == "postgres" and not database_url:
            raise RuntimeError("DATABASE_URL is required when PROJECT_REPOSITORY=postgres.")
        if provider == "gemini" and not gemini_key:
            raise RuntimeError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini.")
        origins = tuple(item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:3000,https://content-gen-automator.replit.app").split(",") if item.strip())
        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            database_url=database_url,
            project_repository=repository,
            llm_provider=provider,
            gemini_api_key=gemini_key,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            cors_origins=origins,
            integration_service_token=os.getenv("INTEGRATION_SERVICE_TOKEN", ""),
            export_signing_secret=os.getenv("EXPORT_SIGNING_SECRET", "development-export-secret"),
        )


settings = Settings.from_env()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./security_auditor.db"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    deepseek_api_key: str = ""
    max_file_size_mb: int = 20

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


settings = Settings()

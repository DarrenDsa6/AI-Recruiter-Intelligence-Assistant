from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_BASE_URL")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")

    jwt_secret: str = Field(default="", alias="JWT_SECRET")

    database_url: str = Field(default="", alias="DATABASE_CONNECTION_STRING")

    upstash_redis_url: str = Field(default="", alias="UPSTASH_REDIS_REST_URL")
    upstash_redis_token: str = Field(default="", alias="UPSTASH_REDIS_REST_TOKEN")

    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")
    resend_from_email: str = Field(default="", alias="RESEND_FROM_EMAIL")

    github_token: str = Field(default="", alias="GITHUB_TOKEN")

    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    @property
    def database_url_async(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        base = ["http://localhost:3000", "http://127.0.0.1:3000"]
        if self.cors_origins:
            base.extend(o.strip() for o in self.cors_origins.split(",") if o.strip())
        return base


settings = Settings()

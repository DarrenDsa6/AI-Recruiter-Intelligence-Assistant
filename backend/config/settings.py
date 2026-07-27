import sys

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="https://generativelanguage.googleapis.com/v1beta/openai", alias="LLM_BASE_URL")
    llm_model: str = Field(default="gemini-2.0-flash", alias="LLM_MODEL")

    llm_fallback_api_key: str = Field(default="", alias="LLM_FALLBACK_API_KEY")
    llm_fallback_base_url: str = Field(default="https://api.groq.com/openai/v1", alias="LLM_FALLBACK_BASE_URL")
    llm_fallback_model: str = Field(default="llama-3.3-70b-versatile", alias="LLM_FALLBACK_MODEL")

    jwt_secret: str = Field(default="", alias="JWT_SECRET")

    database_url: str = Field(default="", alias="DATABASE_CONNECTION_STRING")

    upstash_redis_url: str = Field(default="", alias="UPSTASH_REDIS_REST_URL")
    upstash_redis_token: str = Field(default="", alias="UPSTASH_REDIS_REST_TOKEN")

    brevo_api_key: str = Field(default="", alias="BREVO_API_KEY")
    brevo_from_email: str = Field(default="", alias="BREVO_FROM_EMAIL")
    brevo_from_name: str = Field(default="AI Resume Tailor", alias="BREVO_FROM_NAME")

    github_token: str = Field(default="", alias="GITHUB_TOKEN")

    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    metrics_api_key: str = Field(default="", alias="METRICS_API_KEY")

    @field_validator("jwt_secret")
    @classmethod
    def _validate_jwt_secret(cls, v: str) -> str:
        if not v:
            print("FATAL: JWT_SECRET is not set. Authentication will be insecure.", file=sys.stderr)
            sys.exit(1)
        return v

    @property
    def database_url_async(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        base = ["http://localhost:3000", "http://127.0.0.1:3000"]
        if self.cors_origins:
            base.extend(o.strip() for o in self.cors_origins.split(",") if o.strip())
        return base


settings = Settings()

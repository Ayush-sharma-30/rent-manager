from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "local"
    DATABASE_URL: str = "postgresql+asyncpg://rent:rent@postgres:5432/rent_manager"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://rent:rent@postgres:5432/rent_manager"
    REDIS_URL: str = "redis://redis:6379/0"

    @model_validator(mode="after")
    def _derive_db_urls(self) -> "Settings":
        """Managed hosts (Render, Heroku, Neon, …) inject a single bare
        ``postgres(ql)://…`` URL. SQLAlchemy needs an explicit driver, so when we
        get a bare URL we derive both the async (asyncpg) and sync (psycopg2)
        variants from it. URLs that already name a driver (the local default,
        docker-compose) are left untouched.
        """
        raw = self.DATABASE_URL
        if raw.startswith("postgres://"):  # Heroku/Render legacy scheme
            raw = "postgresql://" + raw[len("postgres://") :]
        scheme = raw.split("://", 1)[0] if "://" in raw else ""
        if scheme == "postgresql":  # bare, no "+driver"
            parts = urlsplit(raw)
            query = dict(parse_qsl(parts.query))
            sslmode = query.pop("sslmode", None)

            async_q = dict(query)
            if sslmode in {"require", "verify-ca", "verify-full"}:
                async_q["ssl"] = "true"  # asyncpg uses ssl=, not sslmode=
            self.DATABASE_URL = urlunsplit(
                ("postgresql+asyncpg", parts.netloc, parts.path, urlencode(async_q), "")
            )

            sync_q = dict(query)
            if sslmode:
                sync_q["sslmode"] = sslmode
            self.DATABASE_SYNC_URL = urlunsplit(
                ("postgresql+psycopg2", parts.netloc, parts.path, urlencode(sync_q), "")
            )
        return self

    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60
    JWT_REFRESH_EXPIRY_DAYS: int = 90

    CORS_ALLOWED_ORIGINS: str = "*"
    LOG_LEVEL: str = "INFO"

    OTP_FIXED: str = Field(default="123456", description="Dev mock OTP that always works")

    WHATSAPP_ENABLED: bool = False
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""

    SES_ENABLED: bool = False
    SES_FROM_EMAIL: str = "noreply@rentmanager.in"

    RAZORPAY_ENABLED: bool = False
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/personnapress"
    JWT_SECRET: str = "change-me-in-production"
    CREDENTIAL_ENCRYPTION_KEY: str = "change-me-32-bytes-key-for-prod!!"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    GEMINI_API_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""

    SENTRY_DSN: str = ""
    RESEND_API_KEY: str = ""

    APP_URL: str = "http://localhost:3000"

    TRIAL_DAYS: int = 14


settings = Settings()

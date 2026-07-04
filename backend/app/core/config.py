from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/personnapress"
    JWT_SECRET: str = "change-me-in-production"
    CREDENTIAL_ENCRYPTION_KEY: str = "change-me-32-bytes-key-for-prod!!"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    X_CLIENT_ID: str = ""
    X_CLIENT_SECRET: str = ""
    X_REDIRECT_URI: str = ""
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = ""

    WP_COM_CLIENT_ID: str = ""
    WP_COM_CLIENT_SECRET: str = ""
    WP_COM_REDIRECT_URI: str = ""  # e.g. http://localhost:3000/api/auth/wordpress-com/callback

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_GROWTH: str = ""
    STRIPE_PRICE_AGENCY: str = ""

    INTERNAL_API_URL: str = "http://localhost:8000"

    GEMINI_API_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""

    SENTRY_DSN: str = ""
    RESEND_API_KEY: str = ""

    APP_URL: str = "http://localhost:3000"

    TRIAL_DAYS: int = 14

    # Supabase Storage (for brand content files)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""


settings = Settings()

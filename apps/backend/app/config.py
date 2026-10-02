from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "dev-secret-change-me-in-production-please"


class Settings(BaseSettings):
    """All settings come from AGT_* environment variables (or apps/backend/.env)."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AGT_", extra="ignore")

    env: str = "dev"  # dev | test | prod
    database_url: str = "sqlite+aiosqlite:///./agritech.db"
    auto_create_schema: bool = True  # dev convenience; prod runs `alembic upgrade head`

    secret_key: str = DEFAULT_SECRET
    access_token_ttl_minutes: int = 60 * 12
    refresh_token_ttl_days: int = 90

    # Returns the OTP in the API response so the demo works without an SMS gateway. Ignored in prod.
    otp_echo: bool = True
    sms_provider: str = "console"  # console (stored in notifications table) | http (to be wired)

    payment_provider: str = "sandbox"  # sandbox | cinetpay
    payment_webhook_secret: str = "dev-webhook-secret"
    cinetpay_api_key: str = ""
    cinetpay_password: str = ""
    cinetpay_notify_url: str = ""

    ussd_key: str = "dev-ussd-key"
    upload_dir: str = "./uploads"
    max_upload_bytes: int = 5 * 1024 * 1024
    public_web_url: str = "http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @property
    def echo_otp(self) -> bool:
        return self.otp_echo and not self.is_prod

    def check(self) -> None:
        if self.is_prod and self.secret_key == DEFAULT_SECRET:
            raise RuntimeError("AGT_SECRET_KEY must be set in production")


settings = Settings()

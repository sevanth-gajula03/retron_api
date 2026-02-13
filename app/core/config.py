from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    cors_origins: str = ""
    sendgrid_api_key: str | None = None
    email_from: str | None = None
    frontend_base_url: str = "http://localhost:5173"
    password_setup_token_expire_minutes: int = 60

    # Bootstrap only: enable one-time admin creation via /auth/signup.
    # In production, set BOOTSTRAP_ADMIN_ENABLED=true and (optionally)
    # BOOTSTRAP_ADMIN_EMAIL=admin@gmail.com, create the admin, then unset.
    bootstrap_admin_enabled: bool = False
    bootstrap_admin_email: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

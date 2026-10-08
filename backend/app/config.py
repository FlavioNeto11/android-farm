from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8001
    server_debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/farm.db"

    # Secret Store
    secret_store_key_file: str = "./data/secret.key"
    secret_store_storage_path: str = "./data/secrets/"

    # Proxy Pool
    proxy_pool_size: int = 10
    proxy_rotation_strategy: str = "round_robin"
    proxy_sources: list = []

    # Browser
    browser_headless: bool = True
    browser_anti_detect: bool = True
    browser_user_agents: list = []

    # Platforms
    platform_outlook_enabled: bool = True
    platform_outlook_signup_url: str = "https://signup.live.com"
    platform_outlook_account_age_days: int = 365
    platform_outlook_timeout: int = 60

    platform_instagram_enabled: bool = True
    platform_instagram_signup_url: str = "https://www.instagram.com/accounts/emailsignup/"
    platform_instagram_account_age_days: int = 365
    platform_instagram_timeout: int = 90

    # Instagram Verification
    instagram_verify_accounts: bool = True
    instagram_verification_retries: int = 3
    instagram_verification_timeout: int = 10

    # Abuse Protection
    abuse_rate_limit_per_minute: int = 5
    abuse_max_wait_seconds: int = 300
    abuse_retry_attempts: int = 3

    # Logging
    logging_level: str = "INFO"
    logging_file: str = "./logs/farm.log"
    logging_max_size_mb: int = 10
    logging_backup_count: int = 5

    # API Token for integration with main project
    api_token: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

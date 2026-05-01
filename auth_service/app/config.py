from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)
    database_url: str
    migration_database_url: str
    jwt_secret: str
    jwt_algorithm: str = Field(default="HS256")
    redis_host: str = Field(default="redis_auth")
    redis_port: int = Field(default=6379)


settings = AuthSettings()

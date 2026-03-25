from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    vcenter_host: str
    vcenter_username: str
    vcenter_password: str
    vcenter_port: int = 443
    vcenter_ssl_verify: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

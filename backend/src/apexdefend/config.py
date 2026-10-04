from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]
HANDOFF = ROOT / "deliverables/apexvibe5-handoff-v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore", populate_by_name=True)
    data_dir: Path = Field(default=ROOT / "runtime", validation_alias="APEX_DATA_DIR")
    host: str = Field(default="127.0.0.1", validation_alias="APEX_HOST")
    port: int = Field(default=18080, validation_alias="APEX_PORT")
    cors_origins: list[str] = Field(default=["http://localhost:3000"], validation_alias="APEX_CORS_ORIGINS")
    teamrouter_base_url: str = "https://api.teamorouter.com/v1"
    teamrouter_api_key: SecretStr = SecretStr("")
    teamrouter_model: str = "gpt-6.1-sol"
    teamrouter_api_style: str = "chat"
    teamrouter_timeout_seconds: float = 90
    lease_seconds: int = 120
    max_file_bytes: int = 20 * 1024 * 1024
    max_files: int = 10

    @property
    def database_url(self):
        return f"sqlite:///{self.data_dir.resolve() / 'apex.sqlite3'}"

from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = Field(default="development", alias="LEMORIA_ENV")
    db_host: str = Field(default="localhost", alias="LEMORIA_DB_HOST")
    db_port: int = Field(default=5432, alias="LEMORIA_DB_PORT")
    db_name: str = Field(default="lemoria", alias="LEMORIA_DB_NAME")
    db_user: str = Field(default="lemoria", alias="LEMORIA_DB_USER")
    db_password: str = Field(default="lemoria", alias="LEMORIA_DB_PASSWORD")
    # The vault lives OUTSIDE any project repo by default. It holds private
    # memory (conversations, ADRs, PRDs) and must never end up in version control.
    # VaultService.protect_from_git() backstops custom LEMORIA_VAULT_PATH values.
    vault_path: Path = Field(default=Path.home() / ".lemoria" / "vault", alias="LEMORIA_VAULT_PATH")
    obsidian_path: Path | None = Field(default=None, alias="LEMORIA_OBSIDIAN_PATH")
    github_token: str | None = Field(default=None, alias="LEMORIA_GITHUB_TOKEN")
    opencode_agents_dir: Path = Field(default=Path("./.opencode/agents"), alias="LEMORIA_OPENCODE_AGENTS_DIR")

    @field_validator("vault_path", "obsidian_path", "opencode_agents_dir", mode="before")
    @classmethod
    def _expanduser(cls, value):
        """Resolve ``~`` in path settings. Path("~/x") does NOT expand by itself
        and would create a literal directory named ``~``."""
        if value is None or value == "":
            return value
        return Path(value).expanduser()

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

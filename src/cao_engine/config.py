"""Application configuration using pydantic-settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CAO_ENGINE_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Mistral API (reads MISTRAL_API_KEY directly, no prefix)
    mistral_api_key: str = Field(alias="MISTRAL_API_KEY")

    # Paths
    data_dir: Path = Path("./data")

    # OCR settings
    ocr_model: str = "mistral-ocr-latest"
    table_format: str = "html"
    extract_headers: bool = True
    extract_footers: bool = True
    include_image_base64: bool = False

    # Extraction settings
    extraction_model: str = "mistral-large-latest"

    # Logging
    log_level: str = "INFO"
    log_format: str = "console"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def ocr_dir(self) -> Path:
        return self.data_dir / "ocr"

    @property
    def structured_dir(self) -> Path:
        return self.data_dir / "structured"

    @property
    def momenten_dir(self) -> Path:
        return self.data_dir / "momenten"

    @property
    def pilot_dir(self) -> Path:
        return self.data_dir / "pilot"

    def ensure_dirs(self) -> None:
        """Create all data directories if they don't exist."""
        dirs = [self.raw_dir, self.ocr_dir, self.structured_dir,
                self.momenten_dir, self.pilot_dir]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

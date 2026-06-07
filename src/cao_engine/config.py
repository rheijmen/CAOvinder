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

    # API Keys (read directly without CAO_ENGINE_ prefix)
    mistral_api_key: str = Field(alias="MISTRAL_API_KEY")
    google_api_key: str = Field(alias="GOOGLE_API_KEY")

    # Paths
    data_dir: Path = Path("./data")

    # OCR settings
    ocr_model: str = "mistral-ocr-latest"
    table_format: str = "markdown"  # MUST be markdown - html returns broken references
    extract_headers: bool = True
    extract_footers: bool = True
    include_image_base64: bool = False

    # Extraction settings
    extraction_model: str = "mistral-large-latest"  # Reviewer model
    gemini_model: str = "gemini-3.5-flash"  # Primary extractor (Gemini 3.5 Flash GA, latest stable; thinking mode)
    gemini_thinking_level: str = "MEDIUM"  # Thinking level: MINIMAL, LOW, MEDIUM, or HIGH
    judge_model: str = "mistral-small-2506"  # Judge model for comparing outputs

    # Batch processing settings
    use_batch_api: bool = False  # Enable for production (50% cost savings)
    batch_check_interval: int = 300  # Check batch status every 5 minutes
    batch_max_wait_hours: int = 48  # Timeout after 48 hours

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

    @property
    def setu_dir(self) -> Path:
        return self.data_dir / "setu"

    @property
    def setu_raw_dir(self) -> Path:
        return self.data_dir / "setu_raw"

    @property
    def setu_reports_dir(self) -> Path:
        return self.data_dir / "setu_reports"

    @property
    def statutory_dir(self) -> Path:
        return self.data_dir / "statutory"

    def ensure_dirs(self) -> None:
        """Create all data directories if they don't exist."""
        dirs = [
            self.raw_dir, self.ocr_dir, self.structured_dir,
            self.momenten_dir, self.pilot_dir,
            self.setu_dir, self.setu_raw_dir, self.setu_reports_dir,
            self.statutory_dir,
            self.setu_raw_dir / "gemini",
            self.setu_raw_dir / "mistral",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    """Central place to manage paths and environment-backed settings."""

    base_dir: Path = BASE_DIR
    raw_data_dir: Path = Path(os.getenv("RAW_DATA_DIR", BASE_DIR / "data" / "raw"))
    cache_dir: Path = Path(os.getenv("CACHE_DIR", BASE_DIR / "data" / "cache"))
    public_data_dir: Path = Path(os.getenv("PUBLIC_DATA_DIR", BASE_DIR / "data" / "public"))
    image_root: Path = Path(os.getenv("IMAGE_ROOT", BASE_DIR / "images"))
    db_path: Path = Path(os.getenv("ASMR_DB_PATH", BASE_DIR / "data" / "cache" / "asmr.db"))
    affiliate_id: str = os.getenv("AFFILIATE_ID", "gentleman_dl")
    # Try affiliate tool page if main HTML does not expose chobit embed
    enable_chobit_affiliate_fallback: bool = (
        os.getenv("FETCH_CHOBIT_FALLBACK", "true").lower() == "true"
    )
    # Try chobit.cc search page to find embed codes
    enable_chobit_search: bool = os.getenv("FETCH_CHOBIT_SEARCH", "true").lower() == "true"

    @property
    def data_dir(self) -> Path:
        """Compatibility alias for previous single data directory."""
        return self.raw_data_dir


settings = Settings()

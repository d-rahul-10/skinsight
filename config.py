from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name)
    path = Path(value).expanduser() if value else default
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def _origins_from_env() -> tuple[str, ...]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    )
    return tuple(origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip())


@dataclass(frozen=True)
class Settings:
    database_url: str
    model_path: Path
    max_upload_bytes: int
    min_image_dimension: int
    max_image_dimension: int
    blur_threshold: float
    dark_threshold: float
    bright_threshold: float
    confidence_threshold: float
    cors_origins: tuple[str, ...]
    allow_image_retention: bool
    retained_image_dir: Path
    model_version: str

    @classmethod
    def from_env(cls) -> "Settings":
        db_default = (PROJECT_ROOT / "backend" / "data" / "history.db").as_posix()
        database_url = os.getenv("DATABASE_URL", f"sqlite:///{db_default}")
        threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.55"))
        if not 0.0 <= threshold <= 1.0:
            threshold = 0.55
        max_upload_mb = max(1, int(os.getenv("MAX_UPLOAD_MB", "8")))
        return cls(
            database_url=database_url,
            model_path=_path_from_env("MODEL_PATH", PROJECT_ROOT / "models" / "efficientnet_b0.pth"),
            max_upload_bytes=max_upload_mb * 1024 * 1024,
            min_image_dimension=max(32, int(os.getenv("MIN_IMAGE_DIMENSION", "128"))),
            max_image_dimension=max(512, int(os.getenv("MAX_IMAGE_DIMENSION", "8192"))),
            blur_threshold=max(0.0, float(os.getenv("BLUR_THRESHOLD", "35"))),
            dark_threshold=float(os.getenv("DARK_THRESHOLD", "35")),
            bright_threshold=float(os.getenv("BRIGHT_THRESHOLD", "220")),
            confidence_threshold=threshold,
            cors_origins=_origins_from_env(),
            allow_image_retention=os.getenv("ALLOW_IMAGE_RETENTION", "false").lower() in {"1", "true", "yes"},
            retained_image_dir=_path_from_env("RETAINED_IMAGE_DIR", PROJECT_ROOT / "backend" / "data" / "retained_images"),
            model_version=os.getenv("MODEL_VERSION", "unavailable"),
        )

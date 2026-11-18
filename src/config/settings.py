"""
Pengaturan konfigurasi global dan konstanta untuk PhotoFrameProcessor.
"""

import sys
from pathlib import Path
from typing import Final, Set

# Metadata Aplikasi
APP_NAME: Final[str] = "PhotoFrameProcessor"
APP_VERSION: Final[str] = "1.0.0"
APP_TITLE: Final[str] = f"{APP_NAME} v{APP_VERSION} - Batch Photo Framing Studio"

# Direktori Dasar Proyek & Resolusi Aset (Kompatibel dengan PyInstaller Frozen Mode)
if getattr(sys, "frozen", False):
    # Mode PyInstaller: folder executable untuk data pengguna, _MEIPASS untuk aset internal
    BASE_DIR: Final[Path] = Path(sys.executable).resolve().parent
    meipass_dir = Path(getattr(sys, "_MEIPASS", BASE_DIR))
    if (meipass_dir / "assets").exists():
        ASSETS_DIR: Final[Path] = meipass_dir / "assets"
    elif (BASE_DIR / "_internal" / "assets").exists():
        ASSETS_DIR: Final[Path] = BASE_DIR / "_internal" / "assets"
    else:
        ASSETS_DIR: Final[Path] = BASE_DIR / "assets"
else:
    # Mode Pengembangan Standar Python
    BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent.parent
    ASSETS_DIR: Final[Path] = BASE_DIR / "assets"

BORDERS_DIR: Final[Path] = ASSETS_DIR / "borders"
DEMO_BORDERS_DIR: Final[Path] = BORDERS_DIR / "demo"
FINAL_BORDERS_DIR: Final[Path] = BORDERS_DIR / "final"

# Format Citra yang Didukung
SUPPORTED_PHOTO_EXTENSIONS: Final[Set[str]] = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tiff",
}
SUPPORTED_FRAME_EXTENSIONS: Final[Set[str]] = {".png"}

# Batasan Batch Default
DEFAULT_PHOTOS_PER_BATCH: Final[int] = 250
MAX_RECOMMENDED_TOTAL_PHOTOS: Final[int] = 500

# Pengaturan Output Default
DEFAULT_OUTPUT_FORMAT: Final[str] = "PNG"  # "PNG" mempertahankan transparansi jika ada, "JPEG" untuk efisiensi
DEFAULT_OUTPUT_QUALITY: Final[int] = 95
DEFAULT_SUBFOLDER_BATCH_1: Final[str] = "batch_frame_1"
DEFAULT_SUBFOLDER_BATCH_2: Final[str] = "batch_frame_2"

# Pengaturan GUI CustomTkinter
GUI_APPEARANCE_MODE: Final[str] = "System"  # "System" | "Dark" | "Light"
GUI_COLOR_THEME: Final[str] = "blue"
GUI_DEFAULT_WINDOW_SIZE: Final[str] = "1320x860"
GUI_MIN_WINDOW_SIZE: Final[tuple[int, int]] = (1080, 700)

# Format Logging
LOG_FORMAT: Final[str] = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
